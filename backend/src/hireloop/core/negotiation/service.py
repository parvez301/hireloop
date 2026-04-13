"""NegotiationService — orchestrator."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hireloop.api.errors import AppError
from hireloop.core.llm.errors import LLMError
from hireloop.core.negotiation.playbook import generate_negotiation_playbook
from hireloop.models.application import Application
from hireloop.models.job import Job
from hireloop.models.negotiation import Negotiation
from hireloop.models.profile import Profile
from hireloop.services.usage_event import UsageEventService


@dataclass
class NegotiationContext:
    user_id: UUID
    session: AsyncSession
    usage: UsageEventService


class NegotiationService:
    def __init__(self, context: NegotiationContext):
        self.context = context

    async def create(
        self,
        *,
        job_id: UUID,
        offer_details: dict[str, Any],
        feedback: str | None = None,
    ) -> Negotiation:
        job = (
            await self.context.session.execute(select(Job).where(Job.id == job_id))
        ).scalar_one_or_none()
        if job is None:
            raise AppError(404, "JOB_NOT_FOUND", "Job not found")

        profile = (
            await self.context.session.execute(
                select(Profile).where(Profile.user_id == self.context.user_id)
            )
        ).scalar_one_or_none()
        experience_summary = self._build_experience_summary(profile)
        current_comp = self._build_current_comp(profile)

        try:
            generated = await generate_negotiation_playbook(
                title=job.title,
                company=job.company or "the company",
                location=job.location,
                offer_details=offer_details,
                current_comp=current_comp,
                experience_summary=experience_summary,
                feedback=feedback,
            )
        except LLMError as e:
            raise AppError(502, "LLM_ERROR", f"Playbook generation failed: {e}") from e

        row = Negotiation(
            user_id=self.context.user_id,
            job_id=job_id,
            offer_details=offer_details,
            market_research=generated.market_research,
            counter_offer=generated.counter_offer,
            scripts=generated.scripts,
            model_used=generated.model,
            tokens_used=generated.usage.total_tokens,
        )
        self.context.session.add(row)
        await self.context.session.flush()

        existing_app_stmt = select(Application).where(
            Application.user_id == self.context.user_id,
            Application.job_id == job_id,
        )
        app_row = (await self.context.session.execute(existing_app_stmt)).scalar_one_or_none()
        if app_row is not None:
            app_row.negotiation_id = row.id
            await self.context.session.flush()

        await self.context.usage.record(
            user_id=self.context.user_id,
            event_type="negotiation_generate",
            module="negotiation",
            model=generated.model,
            tokens_used=generated.usage.total_tokens,
            cost_cents=generated.usage.cost_cents(generated.model),
        )

        return row

    async def regenerate(
        self,
        *,
        negotiation_id: UUID,
        feedback: str | None,
    ) -> Negotiation:
        stmt = select(Negotiation).where(
            Negotiation.id == negotiation_id,
            Negotiation.user_id == self.context.user_id,
        )
        original = (await self.context.session.execute(stmt)).scalar_one_or_none()
        if original is None:
            raise AppError(
                404,
                "NEGOTIATION_NOT_FOUND",
                "Negotiation not found",
            )
        return await self.create(
            job_id=original.job_id,
            offer_details=original.offer_details,
            feedback=feedback,
        )

    @staticmethod
    def _build_experience_summary(profile: Profile | None) -> str:
        if profile is None:
            return "Not provided"
        parsed = profile.parsed_resume_json or {}
        years = parsed.get("total_years_experience")
        skills = (parsed.get("skills") or [])[:10]
        parts: list[str] = []
        if years:
            parts.append(f"{years} years total experience")
        if skills:
            parts.append("skills: " + ", ".join(skills))
        return ". ".join(parts) if parts else "Not provided"

    @staticmethod
    def _build_current_comp(profile: Profile | None) -> dict[str, Any] | None:
        _ = profile
        return None
