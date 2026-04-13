"""L2 evaluate — full 10-dim Claude evaluation per surviving job."""

from __future__ import annotations

import asyncio
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hireloop.config import get_settings
from hireloop.core.evaluation.service import EvaluationContext, EvaluationService
from hireloop.db import get_session_factory
from hireloop.models.evaluation import Evaluation
from hireloop.models.job import Job
from hireloop.services.usage_event import UsageEventService


async def evaluate_job_for_user(
    session: AsyncSession,
    *,
    user_id: UUID,
    job_id: UUID,
) -> Evaluation | None:
    """Run the full evaluation pipeline for a single (user, job)."""
    job = (await session.execute(select(Job).where(Job.id == job_id))).scalar_one_or_none()
    if job is None:
        return None

    usage = UsageEventService(session)
    context = EvaluationContext(user_id=user_id, session=session, usage=usage)
    service = EvaluationService(context)
    return await service.evaluate(job_description=job.description_md)


async def evaluate_jobs_bounded(
    *,
    user_id: UUID,
    job_ids: list[UUID],
) -> list[tuple[UUID, Evaluation | None]]:
    """Fan-out L2 evaluation with configured concurrency.

    Each evaluation uses its own DB session so concurrent tasks do not share one
    async connection (asyncpg forbids overlapping operations on a single connection).
    """
    settings = get_settings()
    sem = asyncio.Semaphore(max(1, settings.batch_l2_concurrency))
    factory = get_session_factory()

    async def _one(jid: UUID) -> tuple[UUID, Evaluation | None]:
        async with sem:
            async with factory() as worker_session:
                result = await evaluate_job_for_user(worker_session, user_id=user_id, job_id=jid)
                await worker_session.commit()
        return jid, result

    return await asyncio.gather(*(_one(jid) for jid in job_ids))
