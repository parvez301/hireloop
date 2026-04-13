"""Applications API — pipeline CRUD. Non-paywalled (trial-expired users can still manage)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Query
from sqlalchemy import select

from hireloop.api.deps import CurrentDbUser, DbSession
from hireloop.api.errors import AppError
from hireloop.models.evaluation import Evaluation
from hireloop.schemas.application import (
    ApplicationCreate,
    ApplicationOut,
    ApplicationUpdate,
)
from hireloop.services.application import ApplicationService

router = APIRouter(prefix="/applications", tags=["applications"])


@router.get("")
async def list_applications(
    user: CurrentDbUser,
    session: DbSession,
    status: str | None = Query(default=None),
    min_grade: str | None = Query(default=None),
) -> dict[str, Any]:
    apps = await ApplicationService(session).list_for_user(user.id, status=status)

    if min_grade:
        grade_order = ["F", "D", "C", "C+", "B-", "B", "B+", "A-", "A"]
        threshold_idx = grade_order.index(min_grade) if min_grade in grade_order else 0
        filtered: list[Any] = []
        for a in apps:
            if a.evaluation_id is None:
                continue
            ev = (
                await session.execute(select(Evaluation).where(Evaluation.id == a.evaluation_id))
            ).scalar_one_or_none()
            if ev is None:
                continue
            in_order = ev.overall_grade in grade_order
            idx_ok = in_order and grade_order.index(ev.overall_grade) >= threshold_idx
            if idx_ok:
                filtered.append(a)
        apps = filtered

    return {"data": [ApplicationOut.model_validate(a).model_dump(mode="json") for a in apps]}


@router.post("", status_code=201)
async def create_application(
    payload: ApplicationCreate,
    user: CurrentDbUser,
    session: DbSession,
) -> dict[str, Any]:
    row = await ApplicationService(session).create(user.id, payload)
    if row is None:
        raise AppError(
            409, "APPLICATION_ALREADY_EXISTS", "An application already exists for this job"
        )
    await session.commit()
    return {"data": ApplicationOut.model_validate(row).model_dump(mode="json")}


@router.get("/{app_id}")
async def get_application(
    app_id: UUID,
    user: CurrentDbUser,
    session: DbSession,
) -> dict[str, Any]:
    row = await ApplicationService(session).get(user.id, app_id)
    if row is None:
        raise AppError(404, "APPLICATION_NOT_FOUND", "Application not found")
    return {"data": ApplicationOut.model_validate(row).model_dump(mode="json")}


@router.put("/{app_id}")
async def update_application(
    app_id: UUID,
    payload: ApplicationUpdate,
    user: CurrentDbUser,
    session: DbSession,
) -> dict[str, Any]:
    row = await ApplicationService(session).update(user.id, app_id, payload)
    if row is None:
        raise AppError(404, "APPLICATION_NOT_FOUND", "Application not found")
    await session.commit()
    return {"data": ApplicationOut.model_validate(row).model_dump(mode="json")}


@router.delete("/{app_id}", status_code=204)
async def delete_application(
    app_id: UUID,
    user: CurrentDbUser,
    session: DbSession,
) -> None:
    ok = await ApplicationService(session).delete(user.id, app_id)
    if not ok:
        raise AppError(404, "APPLICATION_NOT_FOUND", "Application not found")
    await session.commit()
