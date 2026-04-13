"""Scan configs API — CRUD. POST / PUT / run paywalled; GET / DELETE not."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter

from hireloop.api.deps import CurrentDbUser, DbSession, EntitledDbUser
from hireloop.api.errors import AppError
from hireloop.schemas.scan_config import (
    ScanConfigCreate,
    ScanConfigOut,
    ScanConfigUpdate,
)
from hireloop.services.scan_config import ScanConfigService

router = APIRouter(prefix="/scan-configs", tags=["scan-configs"])


@router.get("")
async def list_scan_configs(
    user: CurrentDbUser,
    session: DbSession,
) -> dict[str, Any]:
    configs = await ScanConfigService(session).list_for_user(user.id)
    return {"data": [ScanConfigOut.model_validate(c).model_dump(mode="json") for c in configs]}


@router.post("", status_code=201)
async def create_scan_config(
    payload: ScanConfigCreate,
    user: EntitledDbUser,
    session: DbSession,
) -> dict[str, Any]:
    config = await ScanConfigService(session).create(user.id, payload)
    await session.commit()
    return {"data": ScanConfigOut.model_validate(config).model_dump(mode="json")}


@router.get("/{config_id}")
async def get_scan_config(
    config_id: UUID,
    user: CurrentDbUser,
    session: DbSession,
) -> dict[str, Any]:
    config = await ScanConfigService(session).get(user.id, config_id)
    if config is None:
        raise AppError(404, "SCAN_CONFIG_NOT_FOUND", "Scan config not found")
    return {"data": ScanConfigOut.model_validate(config).model_dump(mode="json")}


@router.put("/{config_id}")
async def update_scan_config(
    config_id: UUID,
    payload: ScanConfigUpdate,
    user: EntitledDbUser,
    session: DbSession,
) -> dict[str, Any]:
    config = await ScanConfigService(session).update(user.id, config_id, payload)
    if config is None:
        raise AppError(404, "SCAN_CONFIG_NOT_FOUND", "Scan config not found")
    await session.commit()
    return {"data": ScanConfigOut.model_validate(config).model_dump(mode="json")}


@router.delete("/{config_id}", status_code=204)
async def delete_scan_config(
    config_id: UUID,
    user: CurrentDbUser,
    session: DbSession,
) -> None:
    ok = await ScanConfigService(session).delete(user.id, config_id)
    if not ok:
        raise AppError(404, "SCAN_CONFIG_NOT_FOUND", "Scan config not found")
    await session.commit()
