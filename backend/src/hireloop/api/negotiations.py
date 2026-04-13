"""Negotiations API."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Query

from hireloop.api.deps import CurrentDbUser, DbSession, EntitledDbUser
from hireloop.api.errors import AppError
from hireloop.core.negotiation.service import NegotiationContext, NegotiationService
from hireloop.schemas.negotiation import (
    NegotiationCreate,
    NegotiationOut,
    NegotiationRegenerate,
)
from hireloop.services.negotiation import get_for_user, list_for_user
from hireloop.services.usage_event import UsageEventService

router = APIRouter(prefix="/negotiations", tags=["negotiations"])


@router.post("", status_code=201)
async def create_negotiation(
    payload: NegotiationCreate,
    user: EntitledDbUser,
    session: DbSession,
) -> dict[str, Any]:
    usage = UsageEventService(session)
    ctx = NegotiationContext(user_id=user.id, session=session, usage=usage)
    service = NegotiationService(ctx)
    neg = await service.create(
        job_id=payload.job_id,
        offer_details=payload.offer_details.model_dump(exclude_none=False),
    )
    await session.commit()
    return {"data": NegotiationOut.model_validate(neg).model_dump(mode="json")}


@router.get("")
async def list_negotiations(
    user: CurrentDbUser,
    session: DbSession,
    limit: int = Query(default=20, ge=1, le=100),
) -> dict[str, Any]:
    rows = await list_for_user(session, user.id, limit=limit)
    return {"data": [NegotiationOut.model_validate(r).model_dump(mode="json") for r in rows]}


@router.get("/{negotiation_id}")
async def get_negotiation(
    negotiation_id: UUID,
    user: CurrentDbUser,
    session: DbSession,
) -> dict[str, Any]:
    row = await get_for_user(session, user.id, negotiation_id)
    if row is None:
        raise AppError(404, "NEGOTIATION_NOT_FOUND", "Negotiation not found")
    return {"data": NegotiationOut.model_validate(row).model_dump(mode="json")}


@router.post("/{negotiation_id}/regenerate", status_code=201)
async def regenerate_negotiation(
    negotiation_id: UUID,
    payload: NegotiationRegenerate,
    user: EntitledDbUser,
    session: DbSession,
) -> dict[str, Any]:
    usage = UsageEventService(session)
    ctx = NegotiationContext(user_id=user.id, session=session, usage=usage)
    service = NegotiationService(ctx)
    neg = await service.regenerate(negotiation_id=negotiation_id, feedback=payload.feedback)
    await session.commit()
    return {"data": NegotiationOut.model_validate(neg).model_dump(mode="json")}
