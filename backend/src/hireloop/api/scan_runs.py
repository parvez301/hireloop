"""Scan runs API — trigger + list + get detail."""

from __future__ import annotations

from typing import Any
from uuid import UUID

import inngest
from fastapi import APIRouter, Query

from hireloop.api.deps import CurrentDbUser, DbSession, EntitledDbUser
from hireloop.api.errors import AppError
from hireloop.inngest.client import get_inngest_client
from hireloop.schemas.scan_run import ScanResultOut, ScanRunDetail, ScanRunOut
from hireloop.services.scan_config import ScanConfigService
from hireloop.services.scan_run import ScanRunService

router = APIRouter(tags=["scan-runs"])


@router.post("/scan-configs/{config_id}/run", status_code=202)
async def trigger_scan(
    config_id: UUID,
    user: EntitledDbUser,
    session: DbSession,
) -> dict[str, Any]:
    config = await ScanConfigService(session).get(user.id, config_id)
    if config is None:
        raise AppError(404, "SCAN_CONFIG_NOT_FOUND", "Scan config not found")

    runs = ScanRunService(session)
    scan_run = await runs.create_pending(user_id=user.id, scan_config_id=config.id)
    await session.commit()

    client = get_inngest_client()
    try:
        sent_ids = await client.send(
            inngest.Event(
                name="scan/started",
                data={
                    "scan_config_id": str(config.id),
                    "user_id": str(user.id),
                    "scan_run_id": str(scan_run.id),
                },
            )
        )
    except Exception as e:
        await runs.mark_failed(scan_run, f"Inngest send failed: {e}")
        await session.commit()
        raise AppError(503, "INNGEST_UNAVAILABLE", "Background worker is unavailable") from e

    if sent_ids:
        scan_run.inngest_event_id = str(sent_ids[0])
        await session.commit()

    return {
        "data": {
            "scan_run_id": str(scan_run.id),
            "status": scan_run.status,
        }
    }


@router.get("/scan-runs")
async def list_scan_runs(
    user: CurrentDbUser,
    session: DbSession,
    limit: int = Query(default=20, ge=1, le=100),
    status: str | None = Query(default=None),
) -> dict[str, Any]:
    runs = await ScanRunService(session).list_for_user(user.id, limit=limit, status=status)
    return {"data": [ScanRunOut.model_validate(r).model_dump(mode="json") for r in runs]}


@router.get("/scan-runs/{scan_run_id}")
async def get_scan_run(
    scan_run_id: UUID,
    user: CurrentDbUser,
    session: DbSession,
) -> dict[str, Any]:
    svc = ScanRunService(session)
    run = await svc.get_for_user(user.id, scan_run_id)
    if run is None:
        raise AppError(404, "SCAN_RUN_NOT_FOUND", "Scan run not found")
    results = await svc.list_results(run.id, limit=50)
    detail = ScanRunDetail(
        scan_run=ScanRunOut.model_validate(run),
        results=[ScanResultOut.model_validate(r) for r in results],
    )
    return {"data": detail.model_dump(mode="json")}
