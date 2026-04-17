"""CV optimization orchestrator.

Flow: load evaluation → load profile/resume → extract keywords → rewrite
      → render PDF in-process → persist cv_outputs row.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hireloop.core.cv_optimizer.optimizer import CvOptimizer
from hireloop.core.cv_optimizer.pdf_renderer import render_pdf
from hireloop.models.cv_output import CvOutput
from hireloop.models.evaluation import Evaluation
from hireloop.models.job import Job
from hireloop.models.profile import Profile
from hireloop.services.usage_event import UsageEventService


class EvaluationRequiredError(Exception):
    """User tried to optimize a CV for a job they haven't evaluated."""


@dataclass
class CvOptimizerContext:
    user_id: uuid.UUID
    session: AsyncSession
    usage: UsageEventService


class CvOptimizerService:
    def __init__(self, context: CvOptimizerContext):
        self.context = context
        self.optimizer = CvOptimizer()

    async def optimize(
        self,
        *,
        job_id: uuid.UUID,
        feedback: str | None = None,
    ) -> CvOutput:
        stmt = select(Evaluation).where(
            Evaluation.user_id == self.context.user_id,
            Evaluation.job_id == job_id,
        )
        evaluation = (await self.context.session.execute(stmt)).scalar_one_or_none()
        if evaluation is None:
            raise EvaluationRequiredError("Evaluate the job first before generating a tailored CV")

        job = (await self.context.session.execute(select(Job).where(Job.id == job_id))).scalar_one()
        profile = (
            await self.context.session.execute(
                select(Profile).where(Profile.user_id == self.context.user_id)
            )
        ).scalar_one()

        master_md = profile.master_resume_md or ""
        if not master_md.strip():
            raise EvaluationRequiredError("User has no master resume — upload one first")

        keywords = self._extract_keywords(evaluation.dimension_scores)

        rewritten = await self.optimizer.rewrite(
            master_resume_md=master_md,
            job_markdown=job.description_md,
            keywords=keywords,
            additional_feedback=feedback,
        )

        await self.context.usage.record(
            user_id=self.context.user_id,
            event_type="optimize_cv",
            module="cv_optimizer",
            model=rewritten.model,
            tokens_used=rewritten.usage.total_tokens,
            cost_cents=rewritten.usage.cost_cents(rewritten.model),
        )

        pdf_key = f"cv-outputs/{self.context.user_id}/{uuid.uuid4()}.pdf"
        await render_pdf(
            markdown=rewritten.tailored_md,
            template="resume",
            user_id=self.context.user_id,
            output_key=pdf_key,
        )

        row = CvOutput(
            user_id=self.context.user_id,
            job_id=job_id,
            tailored_md=rewritten.tailored_md,
            pdf_s3_key=pdf_key,
            changes_summary=rewritten.changes_summary,
            model_used=rewritten.model,
        )
        self.context.session.add(row)
        await self.context.session.flush()
        return row

    @staticmethod
    def _extract_keywords(dimension_scores: dict[str, Any]) -> list[str]:
        keywords: list[str] = []
        for dim in dimension_scores.values():
            keywords.extend(dim.get("signals", []) if isinstance(dim, dict) else [])
        seen: set[str] = set()
        out: list[str] = []
        for k in keywords:
            if k not in seen:
                seen.add(k)
                out.append(k)
        return out[:20]
