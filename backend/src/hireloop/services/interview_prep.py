"""InterviewPrep CRUD helpers — thin wrapper for API layer."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hireloop.models.interview_prep import InterviewPrep


async def get_for_user(session: AsyncSession, user_id: UUID, prep_id: UUID) -> InterviewPrep | None:
    stmt = select(InterviewPrep).where(
        InterviewPrep.id == prep_id,
        InterviewPrep.user_id == user_id,
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def list_for_user(
    session: AsyncSession, user_id: UUID, *, limit: int = 20
) -> list[InterviewPrep]:
    stmt = (
        select(InterviewPrep)
        .where(InterviewPrep.user_id == user_id)
        .order_by(InterviewPrep.created_at.desc())
        .limit(limit)
    )
    return list((await session.execute(stmt)).scalars().all())
