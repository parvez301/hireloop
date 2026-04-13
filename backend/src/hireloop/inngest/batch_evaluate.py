"""Inngest function: batch/started → run funnel.

Tests call `run_batch_evaluate(batch_run_id)` directly, bypassing Inngest's
runtime. The Inngest wrapper only adds durability + retries in production.
"""

from __future__ import annotations

from uuid import UUID

import inngest

from hireloop.core.batch.service import BatchService
from hireloop.db import get_session_factory
from hireloop.inngest.client import get_inngest_client


async def run_batch_evaluate(batch_run_id: UUID) -> dict[str, str]:
    factory = get_session_factory()
    async with factory() as session:
        await BatchService(session).run_funnel(batch_run_id=batch_run_id)
        await session.commit()
    return {"batch_run_id": str(batch_run_id)}


def register() -> inngest.Function:
    client = get_inngest_client()

    @client.create_function(
        fn_id="batch-evaluate",
        trigger=inngest.TriggerEvent(event="batch/started"),
        concurrency=[
            inngest.Concurrency(limit=5, key="event.data.user_id"),
            inngest.Concurrency(limit=50),
        ],
        retries=3,
    )
    async def batch_evaluate_fn(ctx: inngest.Context) -> dict[str, str]:
        batch_run_id = UUID(str(ctx.event.data["batch_run_id"]))
        return await ctx.step.run("run-funnel", run_batch_evaluate, batch_run_id)

    return batch_evaluate_fn
