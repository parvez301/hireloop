"""CV outputs API."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Header, Query
from fastapi.responses import RedirectResponse
from sqlalchemy import select

from hireloop.api.deps import DbSession, EntitledDbUser, RedisClient
from hireloop.api.errors import AppError
from hireloop.core.cv_optimizer.pdf_renderer import PdfRenderError
from hireloop.core.cv_optimizer.service import (
    CvOptimizerContext,
    CvOptimizerService,
    EvaluationRequiredError,
)
from hireloop.integrations.s3 import get_presigned_url
from hireloop.models.cv_output import CvOutput
from hireloop.schemas.cv_output import CvOutputCreate, CvOutputOut, CvOutputRegenerate
from hireloop.services.idempotency import IdempotencyStore
from hireloop.services.usage_event import UsageEventService

router = APIRouter(prefix="/cv-outputs", tags=["cv-outputs"])


@router.post("")
async def create_cv_output(
    payload: CvOutputCreate,
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
    context = CvOptimizerContext(user_id=current_user.id, session=session, usage=usage)
    service = CvOptimizerService(context)
    try:
        cv = await service.optimize(job_id=payload.job_id)
    except EvaluationRequiredError as e:
        raise AppError(422, "EVALUATION_REQUIRED", str(e)) from e
    except PdfRenderError as e:
        raise AppError(502, "PDF_RENDER_FAILED", str(e), details=e.details) from e

    await session.refresh(cv)
    body: dict[str, Any] = {"data": CvOutputOut.model_validate(cv).model_dump(mode="json")}
    if idempotency_key:
        await idem.set(str(current_user.id), idempotency_key, body)
    return body


@router.post("/{cv_output_id}/regenerate")
async def regenerate_cv_output(
    cv_output_id: UUID,
    payload: CvOutputRegenerate,
    session: DbSession,
    current_user: EntitledDbUser,
) -> dict[str, Any]:
    stmt = select(CvOutput).where(
        CvOutput.id == cv_output_id,
        CvOutput.user_id == current_user.id,
    )
    existing = (await session.execute(stmt)).scalar_one_or_none()
    if existing is None:
        raise AppError(404, "RESOURCE_NOT_FOUND", "CV output not found")

    usage = UsageEventService(session)
    context = CvOptimizerContext(user_id=current_user.id, session=session, usage=usage)
    service = CvOptimizerService(context)
    try:
        cv = await service.optimize(job_id=existing.job_id, feedback=payload.feedback)
    except EvaluationRequiredError as e:
        raise AppError(422, "EVALUATION_REQUIRED", str(e)) from e
    except PdfRenderError as e:
        raise AppError(502, "PDF_RENDER_FAILED", str(e), details=e.details) from e

    await session.refresh(cv)
    return {"data": CvOutputOut.model_validate(cv).model_dump(mode="json")}


@router.get("")
async def list_cv_outputs(
    session: DbSession,
    current_user: EntitledDbUser,
    limit: int = Query(default=20, ge=1, le=100),
) -> dict[str, Any]:
    stmt = (
        select(CvOutput)
        .where(CvOutput.user_id == current_user.id)
        .order_by(CvOutput.created_at.desc())
        .limit(limit)
    )
    rows = (await session.execute(stmt)).scalars().all()
    return {"data": [CvOutputOut.model_validate(r).model_dump(mode="json") for r in rows]}


@router.get("/{cv_output_id}")
async def get_cv_output(
    cv_output_id: UUID,
    session: DbSession,
    current_user: EntitledDbUser,
) -> dict[str, Any]:
    stmt = select(CvOutput).where(
        CvOutput.id == cv_output_id,
        CvOutput.user_id == current_user.id,
    )
    row = (await session.execute(stmt)).scalar_one_or_none()
    if row is None:
        raise AppError(404, "RESOURCE_NOT_FOUND", "CV output not found")
    return {"data": CvOutputOut.model_validate(row).model_dump(mode="json")}


@router.get("/{cv_output_id}/pdf")
async def get_cv_output_pdf(
    cv_output_id: UUID,
    session: DbSession,
    current_user: EntitledDbUser,
) -> RedirectResponse:
    stmt = select(CvOutput).where(
        CvOutput.id == cv_output_id,
        CvOutput.user_id == current_user.id,
    )
    row = (await session.execute(stmt)).scalar_one_or_none()
    if row is None:
        raise AppError(404, "RESOURCE_NOT_FOUND", "CV output not found")
    url = get_presigned_url(row.pdf_s3_key, expires_in=900)
    return RedirectResponse(url=url, status_code=302)
