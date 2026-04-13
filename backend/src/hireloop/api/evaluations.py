"""Evaluations API: POST /evaluations, GET /evaluations, GET /evaluations/:id."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Query
from sqlalchemy import select

from hireloop.api.deps import DbSession, EntitledDbUser, RedisClient
from hireloop.core.evaluation.service import EvaluationContext, EvaluationService
from hireloop.models.evaluation import Evaluation
from hireloop.schemas.evaluation import EvaluationCreate, EvaluationOut
from hireloop.services.idempotency import IdempotencyStore
from hireloop.services.usage_event import UsageEventService

router = APIRouter(prefix="/evaluations", tags=["evaluations"])


@router.post("")
async def create_evaluation(
    payload: EvaluationCreate,
    session: DbSession,
    current_user: EntitledDbUser,
    redis: RedisClient,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict[str, Any]:
    idem = IdempotencyStore(redis)

    if idempotency_key:
        cached = await idem.get(str(current_user.id), idempotency_key)
        if cached is not None:
            return cached

    usage = UsageEventService(session)
    context = EvaluationContext(user_id=current_user.id, session=session, usage=usage)
    service = EvaluationService(context)

    evaluation = await service.evaluate(
        job_url=payload.job_url,
        job_description=payload.job_description,
    )

    body: dict[str, Any] = {
        "data": EvaluationOut.model_validate(evaluation).model_dump(mode="json"),
        "meta": {
            "cached": evaluation.cached,
            "tokens_used": evaluation.tokens_used or 0,
        },
    }

    if idempotency_key:
        await idem.set(str(current_user.id), idempotency_key, body)

    return body


@router.get("")
async def list_evaluations(
    session: DbSession,
    current_user: EntitledDbUser,
    grade: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
) -> dict[str, Any]:
    stmt = (
        select(Evaluation)
        .where(Evaluation.user_id == current_user.id)
        .order_by(Evaluation.created_at.desc())
        .limit(limit)
    )
    if grade:
        stmt = stmt.where(Evaluation.overall_grade == grade)
    rows = (await session.execute(stmt)).scalars().all()
    return {
        "data": [EvaluationOut.model_validate(r).model_dump(mode="json") for r in rows],
    }


@router.get("/{evaluation_id}")
async def get_evaluation(
    evaluation_id: UUID,
    session: DbSession,
    current_user: EntitledDbUser,
) -> dict[str, Any]:
    stmt = select(Evaluation).where(
        Evaluation.id == evaluation_id,
        Evaluation.user_id == current_user.id,
    )
    row = (await session.execute(stmt)).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    return {"data": EvaluationOut.model_validate(row).model_dump(mode="json")}
