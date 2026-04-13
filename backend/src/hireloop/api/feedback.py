"""Feedback endpoints for all 4 LLM-generated resources."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter

from hireloop.api.deps import CurrentDbUser, DbSession
from hireloop.api.errors import AppError
from hireloop.core.feedback.service import (
    FeedbackResourceNotFound,
    FeedbackService,
    InvalidFeedback,
)
from hireloop.schemas.feedback import FeedbackCreate, FeedbackOut

router = APIRouter(tags=["feedback"])


async def _record_feedback(
    *,
    resource_type: str,
    resource_id: UUID,
    payload: FeedbackCreate,
    user: Any,
    session: Any,
) -> dict[str, Any]:
    service = FeedbackService(session)
    try:
        row = await service.record(
            user_id=user.id,
            resource_type=resource_type,
            resource_id=resource_id,
            rating=payload.rating,
            correction_notes=payload.correction_notes,
        )
    except InvalidFeedback as e:
        raise AppError(422, "INVALID_FEEDBACK", str(e)) from e
    except FeedbackResourceNotFound as e:
        raise AppError(404, "FEEDBACK_RESOURCE_NOT_FOUND", str(e)) from e
    await session.commit()
    return {"data": FeedbackOut.model_validate(row).model_dump(mode="json")}


@router.post("/evaluations/{resource_id}/feedback", status_code=201)
async def feedback_evaluation(
    resource_id: UUID,
    payload: FeedbackCreate,
    user: CurrentDbUser,
    session: DbSession,
) -> dict[str, Any]:
    return await _record_feedback(
        resource_type="evaluation",
        resource_id=resource_id,
        payload=payload,
        user=user,
        session=session,
    )


@router.post("/cv-outputs/{resource_id}/feedback", status_code=201)
async def feedback_cv_output(
    resource_id: UUID,
    payload: FeedbackCreate,
    user: CurrentDbUser,
    session: DbSession,
) -> dict[str, Any]:
    return await _record_feedback(
        resource_type="cv_output",
        resource_id=resource_id,
        payload=payload,
        user=user,
        session=session,
    )


@router.post("/interview-preps/{resource_id}/feedback", status_code=201)
async def feedback_interview_prep(
    resource_id: UUID,
    payload: FeedbackCreate,
    user: CurrentDbUser,
    session: DbSession,
) -> dict[str, Any]:
    return await _record_feedback(
        resource_type="interview_prep",
        resource_id=resource_id,
        payload=payload,
        user=user,
        session=session,
    )


@router.post("/negotiations/{resource_id}/feedback", status_code=201)
async def feedback_negotiation(
    resource_id: UUID,
    payload: FeedbackCreate,
    user: CurrentDbUser,
    session: DbSession,
) -> dict[str, Any]:
    return await _record_feedback(
        resource_type="negotiation",
        resource_id=resource_id,
        payload=payload,
        user=user,
        session=session,
    )
