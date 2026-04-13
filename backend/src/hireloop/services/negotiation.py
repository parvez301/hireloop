"""Negotiation CRUD helpers — thin wrapper for API layer."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hireloop.models.negotiation import Negotiation


async def get_for_user(
    session: AsyncSession, user_id: UUID, negotiation_id: UUID
) -> Negotiation | None:
    stmt = select(Negotiation).where(
        Negotiation.id == negotiation_id,
        Negotiation.user_id == user_id,
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def list_for_user(
    session: AsyncSession, user_id: UUID, *, limit: int = 20
) -> list[Negotiation]:
    stmt = (
        select(Negotiation)
        .where(Negotiation.user_id == user_id)
        .order_by(Negotiation.created_at.desc())
        .limit(limit)
    )
    return list((await session.execute(stmt)).scalars().all())
