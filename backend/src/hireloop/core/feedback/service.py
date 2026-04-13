"""Feedback service — generic upsert with per-resource ownership validation.

Ownership is polymorphic: the feedback row carries `resource_type` and
`resource_id` but no FK; we validate ownership in the service layer via a
dispatch dict mapping resource_type to an async validator that loads the
resource and checks the user_id match.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from hireloop.models.cv_output import CvOutput
from hireloop.models.evaluation import Evaluation
from hireloop.models.feedback import Feedback
from hireloop.models.interview_prep import InterviewPrep
from hireloop.models.negotiation import Negotiation


class FeedbackResourceNotFound(Exception):  # noqa: N818
    """Raised when the resource doesn't exist or belongs to another user."""


class InvalidFeedback(Exception):  # noqa: N818
    """Raised when the rating is out of 1–5 range (Pydantic should catch this first)."""


Validator = Callable[[AsyncSession, UUID, UUID], Awaitable[bool]]


async def _validate_evaluation_ownership(
    session: AsyncSession, user_id: UUID, resource_id: UUID
) -> bool:
    stmt = select(Evaluation).where(Evaluation.id == resource_id, Evaluation.user_id == user_id)
    return (await session.execute(stmt)).scalar_one_or_none() is not None


async def _validate_cv_output_ownership(
    session: AsyncSession, user_id: UUID, resource_id: UUID
) -> bool:
    stmt = select(CvOutput).where(CvOutput.id == resource_id, CvOutput.user_id == user_id)
    return (await session.execute(stmt)).scalar_one_or_none() is not None


async def _validate_interview_prep_ownership(
    session: AsyncSession, user_id: UUID, resource_id: UUID
) -> bool:
    stmt = select(InterviewPrep).where(
        InterviewPrep.id == resource_id, InterviewPrep.user_id == user_id
    )
    return (await session.execute(stmt)).scalar_one_or_none() is not None


async def _validate_negotiation_ownership(
    session: AsyncSession, user_id: UUID, resource_id: UUID
) -> bool:
    stmt = select(Negotiation).where(Negotiation.id == resource_id, Negotiation.user_id == user_id)
    return (await session.execute(stmt)).scalar_one_or_none() is not None


_RESOURCE_VALIDATORS: dict[str, Validator] = {
    "evaluation": _validate_evaluation_ownership,
    "cv_output": _validate_cv_output_ownership,
    "interview_prep": _validate_interview_prep_ownership,
    "negotiation": _validate_negotiation_ownership,
}


class FeedbackService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def record(
        self,
        *,
        user_id: UUID,
        resource_type: str,
        resource_id: UUID,
        rating: int,
        correction_notes: str | None,
    ) -> Feedback:
        """Upsert feedback for a resource.

        Validates rating range, then ownership, then performs a Postgres
        ON CONFLICT upsert on (user_id, resource_type, resource_id).
        """
        if not (1 <= rating <= 5):
            raise InvalidFeedback(f"rating must be 1–5, got {rating}")

        validator = _RESOURCE_VALIDATORS.get(resource_type)
        if validator is None:
            raise FeedbackResourceNotFound(f"unknown resource_type: {resource_type}")
        owns = await validator(self.session, user_id, resource_id)
        if not owns:
            raise FeedbackResourceNotFound(
                f"{resource_type} {resource_id} not found or not owned by user"
            )

        stmt = (
            pg_insert(Feedback)
            .values(
                id=uuid4(),
                user_id=user_id,
                resource_type=resource_type,
                resource_id=resource_id,
                rating=rating,
                correction_notes=correction_notes,
            )
            .on_conflict_do_update(
                constraint="uq_feedback_user_resource",
                set_={
                    "rating": rating,
                    "correction_notes": correction_notes,
                },
            )
            .returning(Feedback)
        )
        result = await self.session.execute(stmt)
        row = result.scalar_one()
        await self.session.flush()
        return row

    async def get(
        self,
        *,
        user_id: UUID,
        resource_type: str,
        resource_id: UUID,
    ) -> Feedback | None:
        stmt = select(Feedback).where(
            Feedback.user_id == user_id,
            Feedback.resource_type == resource_type,
            Feedback.resource_id == resource_id,
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()
