"""Batch funnel orchestrator — L0 → L1 → L2 stages."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hireloop.config import get_settings
from hireloop.core.batch.l0_filter import l0_filter
from hireloop.core.batch.l1_triage import score_jobs_relevance
from hireloop.core.batch.l2_evaluate import evaluate_jobs_bounded
from hireloop.models.batch_run import BatchItem
from hireloop.models.job import Job
from hireloop.models.profile import Profile


async def run_l0(
    session: AsyncSession,
    *,
    batch_run_id: UUID,
    job_ids: list[UUID],
    user_id: UUID,
) -> list[UUID]:
    profile = (
        await session.execute(select(Profile).where(Profile.user_id == user_id))
    ).scalar_one_or_none()
    survivors: list[UUID] = []
    for jid in job_ids:
        job = (await session.execute(select(Job).where(Job.id == jid))).scalar_one_or_none()
        if job is None:
            continue
        stmt = select(BatchItem).where(
            BatchItem.batch_run_id == batch_run_id,
            BatchItem.job_id == jid,
        )
        item = (await session.execute(stmt)).scalar_one_or_none()
        if item is None:
            item = BatchItem(
                batch_run_id=batch_run_id,
                job_id=jid,
                stage="queued",
            )
            session.add(item)
            await session.flush()
        passes = True
        reason: str | None = None
        if profile is not None:
            passes, reason = l0_filter(job, profile)
        if passes:
            item.stage = "l0"
            item.filter_reason = None
            survivors.append(jid)
        else:
            item.stage = "filtered"
            item.filter_reason = reason
    await session.flush()
    return survivors


async def run_l1(
    session: AsyncSession,
    *,
    batch_run_id: UUID,
    job_ids: list[UUID],
    user_id: UUID,
) -> list[UUID]:
    if not job_ids:
        return []
    settings = get_settings()
    scores = await score_jobs_relevance(session, user_id=user_id, job_ids=job_ids)
    survivors: list[UUID] = []
    for jid in job_ids:
        score = scores.get(str(jid), 0.0)
        stmt = select(BatchItem).where(
            BatchItem.batch_run_id == batch_run_id, BatchItem.job_id == jid
        )
        item = (await session.execute(stmt)).scalar_one_or_none()
        if item is None:
            continue
        if score >= settings.batch_l1_relevance_threshold:
            item.stage = "l1"
            survivors.append(jid)
        else:
            item.stage = "filtered"
            item.filter_reason = "low_relevance"
    await session.flush()
    return survivors


async def run_l2(
    session: AsyncSession,
    *,
    batch_run_id: UUID,
    job_ids: list[UUID],
    user_id: UUID,
) -> list[UUID]:
    results = await evaluate_jobs_bounded(user_id=user_id, job_ids=job_ids)
    evaluated: list[UUID] = []
    for jid, evaluation in results:
        stmt = select(BatchItem).where(
            BatchItem.batch_run_id == batch_run_id, BatchItem.job_id == jid
        )
        item = (await session.execute(stmt)).scalar_one_or_none()
        if item is None:
            continue
        if evaluation is not None:
            item.stage = "done"
            item.evaluation_id = evaluation.id
            evaluated.append(jid)
        else:
            item.stage = "filtered"
            item.filter_reason = "l2_failed"
    await session.flush()
    return evaluated
