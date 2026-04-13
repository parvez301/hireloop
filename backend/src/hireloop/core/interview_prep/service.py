"""InterviewPrepService — orchestrator.

Flow:
  1. ensure_story_bank(user_id) — if empty, extract from master resume (with row lock)
  2. generate(user_id, job_id | custom_role, feedback?) — call generator
  3. persist to interview_preps
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hireloop.api.errors import AppError
from hireloop.core.interview_prep.extractor import extract_star_stories_from_resume
from hireloop.core.interview_prep.generator import generate_interview_prep
from hireloop.core.llm.errors import LLMError
from hireloop.models.interview_prep import InterviewPrep
from hireloop.models.job import Job
from hireloop.models.profile import Profile
from hireloop.models.star_story import StarStory
from hireloop.models.user import User
from hireloop.services.usage_event import UsageEventService


@dataclass
class InterviewPrepContext:
    user_id: UUID
    session: AsyncSession
    usage: UsageEventService


class InterviewPrepService:
    def __init__(self, context: InterviewPrepContext):
        self.context = context

    async def ensure_story_bank(self) -> list[StarStory]:
        """If the user has no star_stories, extract from their master resume."""
        await self.context.session.execute(
            select(User).where(User.id == self.context.user_id).with_for_update()
        )

        existing = (
            (
                await self.context.session.execute(
                    select(StarStory).where(StarStory.user_id == self.context.user_id)
                )
            )
            .scalars()
            .all()
        )
        if existing:
            return list(existing)

        profile = (
            await self.context.session.execute(
                select(Profile).where(Profile.user_id == self.context.user_id)
            )
        ).scalar_one_or_none()
        if profile is None or not profile.master_resume_md:
            raise AppError(
                422,
                "MISSING_MASTER_RESUME",
                "Upload your resume before building interview prep.",
            )

        try:
            extracted = await extract_star_stories_from_resume(
                master_resume_md=profile.master_resume_md
            )
        except LLMError as e:
            raise AppError(
                502,
                "LLM_ERROR",
                f"Story extraction failed: {e}",
            ) from e
        except ValueError as e:
            raise AppError(
                502,
                "LLM_ERROR",
                f"Story extraction failed: {e}",
            ) from e

        if not extracted.stories:
            raise AppError(
                422,
                "STORY_EXTRACTION_EMPTY",
                "Could not extract STAR stories from your resume. Try editing your resume.",
            )

        new_stories: list[StarStory] = []
        for s in extracted.stories:
            row = StarStory(
                user_id=self.context.user_id,
                title=s.title,
                situation=s.situation,
                task=s.task,
                action=s.action,
                result=s.result,
                reflection=s.reflection,
                tags=s.tags,
                source="ai_generated",
            )
            self.context.session.add(row)
            new_stories.append(row)
        await self.context.session.flush()

        await self.context.usage.record(
            user_id=self.context.user_id,
            event_type="interview_prep_extract",
            module="interview_prep",
            model=extracted.model,
            tokens_used=extracted.usage.total_tokens,
            cost_cents=extracted.usage.cost_cents(extracted.model),
        )

        return new_stories

    async def create(
        self,
        *,
        job_id: UUID | None = None,
        custom_role: str | None = None,
        feedback: str | None = None,
    ) -> InterviewPrep:
        if bool(job_id) == bool(custom_role):
            raise AppError(
                422,
                "INVALID_INTERVIEW_PREP_INPUT",
                "Provide exactly one of job_id or custom_role",
            )

        stories = await self.ensure_story_bank()
        stories_summary = "\n".join(f"- {s.title}" for s in stories)

        profile = (
            await self.context.session.execute(
                select(Profile).where(Profile.user_id == self.context.user_id)
            )
        ).scalar_one_or_none()
        if profile is None:
            raise AppError(422, "PROFILE_NOT_FOUND", "Complete your profile first.")
        resume_md = profile.master_resume_md or ""

        job_markdown: str | None = None
        if job_id is not None:
            job = (
                await self.context.session.execute(select(Job).where(Job.id == job_id))
            ).scalar_one_or_none()
            if job is None:
                raise AppError(404, "JOB_NOT_FOUND", "Job not found")
            job_markdown = job.description_md

        try:
            generated = await generate_interview_prep(
                existing_stories_summary=stories_summary,
                job_markdown=job_markdown,
                custom_role=custom_role,
                resume_md=resume_md,
                feedback=feedback,
            )
        except LLMError as e:
            raise AppError(502, "LLM_ERROR", f"Generation failed: {e}") from e

        row = InterviewPrep(
            user_id=self.context.user_id,
            job_id=job_id,
            custom_role=custom_role,
            questions=generated.questions,
            red_flag_questions=generated.red_flag_questions,
            model_used=generated.model,
            tokens_used=generated.usage.total_tokens,
        )
        self.context.session.add(row)
        await self.context.session.flush()

        await self.context.usage.record(
            user_id=self.context.user_id,
            event_type="interview_prep_generate",
            module="interview_prep",
            model=generated.model,
            tokens_used=generated.usage.total_tokens,
            cost_cents=generated.usage.cost_cents(generated.model),
        )

        return row

    async def regenerate(
        self,
        *,
        interview_prep_id: UUID,
        feedback: str | None,
    ) -> InterviewPrep:
        """Create a new interview_preps row using the original's job/role + new feedback."""
        stmt = select(InterviewPrep).where(
            InterviewPrep.id == interview_prep_id,
            InterviewPrep.user_id == self.context.user_id,
        )
        original = (await self.context.session.execute(stmt)).scalar_one_or_none()
        if original is None:
            raise AppError(
                404,
                "INTERVIEW_PREP_NOT_FOUND",
                "Interview prep not found",
            )
        return await self.create(
            job_id=original.job_id,
            custom_role=original.custom_role,
            feedback=feedback,
        )

    async def get_for_user(self, prep_id: UUID) -> InterviewPrep | None:
        stmt = select(InterviewPrep).where(
            InterviewPrep.id == prep_id,
            InterviewPrep.user_id == self.context.user_id,
        )
        return (await self.context.session.execute(stmt)).scalar_one_or_none()

    async def list_for_user(self, *, limit: int = 20) -> list[InterviewPrep]:
        stmt = (
            select(InterviewPrep)
            .where(InterviewPrep.user_id == self.context.user_id)
            .order_by(InterviewPrep.created_at.desc())
            .limit(limit)
        )
        return list((await self.context.session.execute(stmt)).scalars().all())
