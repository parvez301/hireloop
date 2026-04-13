"""Batch runs API — create + list + get detail."""

from __future__ import annotations

from typing import Any
from uuid import UUID

import inngest
from fastapi import APIRouter, Query
from sqlalchemy import select

from hireloop.api.deps import CurrentDbUser, DbSession, EntitledDbUser
from hireloop.api.errors import AppError
from hireloop.core.batch.service import BatchService
from hireloop.inngest.client import get_inngest_client
from hireloop.models.batch_run import BatchItem
from hireloop.models.evaluation import Evaluation
from hireloop.models.job import Job
from hireloop.schemas.batch_run import (
    BatchEvaluationSummary,
    BatchItemsSummary,
    BatchRunCreate,
    BatchRunDetail,
    BatchRunOut,
)
from hireloop.services.batch_run import BatchRunService

router = APIRouter(prefix="/batch-runs", tags=["batch-runs"])


@router.post("", status_code=201)
async def create_batch_run(
    payload: BatchRunCreate,
    user: EntitledDbUser,
    session: DbSession,
) -> dict[str, Any]:
    service = BatchService(session)
    source_ref: str | None = None

    if payload.job_urls:
        job_ids = await service.resolve_job_ids_from_urls(user_id=user.id, urls=payload.job_urls)
        source_type = "job_urls"
        source_ref = ",".join(payload.job_urls[:3])
    elif payload.scan_run_id:
        job_ids = await service.resolve_job_ids_from_scan(
            user_id=user.id, scan_run_id=payload.scan_run_id
        )
        source_type = "scan_run_id"
        source_ref = str(payload.scan_run_id)
    elif payload.job_ids:
        job_ids = await service.resolve_job_ids_from_ids(ids=payload.job_ids)
        source_type = "job_ids"
        source_ref = None
    else:
        raise AppError(422, "INVALID_BATCH_INPUT", "No input provided")

    if not job_ids:
        raise AppError(422, "INVALID_BATCH_INPUT", "No valid jobs resolved from input")

    run = await service.start_batch(
        user_id=user.id,
        job_ids=job_ids,
        source_type=source_type,
        source_ref=source_ref,
    )
    await session.commit()

    client = get_inngest_client()
    try:
        sent_ids = await client.send(
            inngest.Event(
                name="batch/started",
                data={
                    "batch_run_id": str(run.id),
                    "user_id": str(user.id),
                },
            )
        )
    except Exception as e:
        runs_svc = BatchRunService(session)
        await runs_svc.mark_failed(run, f"Inngest send failed: {e}")
        await session.commit()
        raise AppError(503, "INNGEST_UNAVAILABLE", "Background worker is unavailable") from e

    if sent_ids:
        run.inngest_event_id = str(sent_ids[0])
        await session.commit()

    return {"data": BatchRunOut.model_validate(run).model_dump(mode="json")}


@router.get("")
async def list_batch_runs(
    user: CurrentDbUser,
    session: DbSession,
    limit: int = Query(default=20, ge=1, le=100),
) -> dict[str, Any]:
    runs = await BatchRunService(session).list_for_user(user.id, limit=limit)
    return {"data": [BatchRunOut.model_validate(r).model_dump(mode="json") for r in runs]}


@router.get("/{batch_run_id}")
async def get_batch_run(
    batch_run_id: UUID,
    user: CurrentDbUser,
    session: DbSession,
) -> dict[str, Any]:
    svc = BatchRunService(session)
    run = await svc.get_for_user(user.id, batch_run_id)
    if run is None:
        raise AppError(404, "BATCH_RUN_NOT_FOUND", "Batch run not found")

    summary_raw = await svc.items_summary(run.id)
    summary = BatchItemsSummary(**summary_raw)

    done_items = (
        (
            await session.execute(
                select(BatchItem).where(
                    BatchItem.batch_run_id == run.id,
                    BatchItem.stage == "done",
                    BatchItem.evaluation_id.isnot(None),
                )
            )
        )
        .scalars()
        .all()
    )
    eval_ids = [i.evaluation_id for i in done_items if i.evaluation_id is not None]
    evaluations: list[Evaluation] = []
    if eval_ids:
        evaluations = list(
            (
                await session.execute(
                    select(Evaluation)
                    .where(Evaluation.id.in_(eval_ids))
                    .order_by(Evaluation.match_score.desc())
                    .limit(10)
                )
            )
            .scalars()
            .all()
        )

    top_results: list[BatchEvaluationSummary] = []
    for ev in evaluations:
        job = (await session.execute(select(Job).where(Job.id == ev.job_id))).scalar_one()
        top_results.append(
            BatchEvaluationSummary(
                evaluation_id=ev.id,
                job_id=ev.job_id,
                job_title=job.title,
                company=job.company,
                overall_grade=ev.overall_grade,
                match_score=ev.match_score,
            )
        )

    detail = BatchRunDetail(
        batch_run=BatchRunOut.model_validate(run),
        items_summary=summary,
        top_results=top_results,
    )
    return {"data": detail.model_dump(mode="json")}
