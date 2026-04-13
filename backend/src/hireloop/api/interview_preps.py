"""Interview preps API — create, list, get, regenerate."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Query

from hireloop.api.deps import CurrentDbUser, DbSession, EntitledDbUser
from hireloop.api.errors import AppError
from hireloop.core.interview_prep.service import (
    InterviewPrepContext,
    InterviewPrepService,
)
from hireloop.schemas.interview_prep import (
    InterviewPrepCreate,
    InterviewPrepOut,
    InterviewPrepRegenerate,
)
from hireloop.services.interview_prep import get_for_user, list_for_user
from hireloop.services.usage_event import UsageEventService

router = APIRouter(prefix="/interview-preps", tags=["interview-preps"])


@router.post("", status_code=201)
async def create_interview_prep(
    payload: InterviewPrepCreate,
    user: EntitledDbUser,
    session: DbSession,
) -> dict[str, Any]:
    usage = UsageEventService(session)
    ctx = InterviewPrepContext(user_id=user.id, session=session, usage=usage)
    service = InterviewPrepService(ctx)
    prep = await service.create(
        job_id=payload.job_id,
        custom_role=payload.custom_role,
    )
    await session.commit()
    return {"data": InterviewPrepOut.model_validate(prep).model_dump(mode="json")}


@router.get("")
async def list_interview_preps(
    user: CurrentDbUser,
    session: DbSession,
    limit: int = Query(default=20, ge=1, le=100),
) -> dict[str, Any]:
    rows = await list_for_user(session, user.id, limit=limit)
    return {"data": [InterviewPrepOut.model_validate(r).model_dump(mode="json") for r in rows]}


@router.get("/{prep_id}")
async def get_interview_prep(
    prep_id: UUID,
    user: CurrentDbUser,
    session: DbSession,
) -> dict[str, Any]:
    row = await get_for_user(session, user.id, prep_id)
    if row is None:
        raise AppError(404, "INTERVIEW_PREP_NOT_FOUND", "Interview prep not found")
    return {"data": InterviewPrepOut.model_validate(row).model_dump(mode="json")}


@router.post("/{prep_id}/regenerate", status_code=201)
async def regenerate_interview_prep(
    prep_id: UUID,
    payload: InterviewPrepRegenerate,
    user: EntitledDbUser,
    session: DbSession,
) -> dict[str, Any]:
    usage = UsageEventService(session)
    ctx = InterviewPrepContext(user_id=user.id, session=session, usage=usage)
    service = InterviewPrepService(ctx)
    prep = await service.regenerate(interview_prep_id=prep_id, feedback=payload.feedback)
    await session.commit()
    return {"data": InterviewPrepOut.model_validate(prep).model_dump(mode="json")}
