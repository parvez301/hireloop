"""Inngest function: scan/started → scrape + classify + persist.

In unit/integration tests the real Inngest runtime is bypassed — tests call
`run_scan_boards(scan_run_id)` directly, which is the sync entry point the
Inngest wrapper delegates to.
"""

from __future__ import annotations

from uuid import UUID

import inngest

from hireloop.core.scanner.service import ScannerService
from hireloop.db import get_session_factory
from hireloop.inngest.client import get_inngest_client


async def run_scan_boards(scan_run_id: UUID) -> dict[str, int | bool]:
    """Pure-Python entry point. Opens its own DB session."""
    factory = get_session_factory()
    async with factory() as session:
        outcome = await ScannerService(session).run_scan(scan_run_id)
        await session.commit()
    return {
        "jobs_found": outcome.jobs_found,
        "jobs_new": outcome.jobs_new,
        "truncated": outcome.truncated,
    }


def register() -> inngest.Function:
    """Register the scan_boards function with the Inngest client."""
    client = get_inngest_client()

    @client.create_function(
        fn_id="scan-boards",
        trigger=inngest.TriggerEvent(event="scan/started"),
        concurrency=[
            inngest.Concurrency(limit=5, key="event.data.user_id"),
            inngest.Concurrency(limit=50),
        ],
        retries=3,
    )
    async def scan_boards_fn(ctx: inngest.Context) -> dict[str, int | bool]:
        scan_run_id = UUID(str(ctx.event.data["scan_run_id"]))
        return await ctx.step.run("run-scan", run_scan_boards, scan_run_id)

    return scan_boards_fn
