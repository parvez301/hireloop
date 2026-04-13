"""BatchRun CRUD helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hireloop.models.batch_run import BatchItem, BatchRun


class BatchRunService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_pending(
        self,
        *,
        user_id: UUID,
        total_jobs: int,
        source_type: str,
        source_ref: str | None,
    ) -> BatchRun:
        run = BatchRun(
            user_id=user_id,
            status="pending",
            total_jobs=total_jobs,
            source_type=source_type,
            source_ref=source_ref,
        )
        self.session.add(run)
        await self.session.flush()
        return run

    async def get_for_user(self, user_id: UUID, run_id: UUID) -> BatchRun | None:
        stmt = select(BatchRun).where(BatchRun.id == run_id, BatchRun.user_id == user_id)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def list_for_user(self, user_id: UUID, *, limit: int = 20) -> list[BatchRun]:
        stmt = (
            select(BatchRun)
            .where(BatchRun.user_id == user_id)
            .order_by(BatchRun.started_at.desc())
            .limit(limit)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def items_summary(self, run_id: UUID) -> dict[str, int]:
        stmt = select(BatchItem).where(BatchItem.batch_run_id == run_id)
        items = (await self.session.execute(stmt)).scalars().all()
        summary: dict[str, int] = {
            "queued": 0,
            "l0": 0,
            "l1": 0,
            "l2": 0,
            "done": 0,
            "filtered": 0,
        }
        for item in items:
            stage = item.stage or "queued"
            if stage in summary:
                summary[stage] += 1
        return summary

    async def mark_running(self, run: BatchRun) -> None:
        run.status = "running"
        await self.session.flush()

    async def mark_completed(
        self,
        run: BatchRun,
        *,
        l0_passed: int,
        l1_passed: int,
        l2_evaluated: int,
    ) -> None:
        run.status = "completed"
        run.l0_passed = l0_passed
        run.l1_passed = l1_passed
        run.l2_evaluated = l2_evaluated
        run.completed_at = datetime.now(UTC)
        await self.session.flush()

    async def mark_failed(self, run: BatchRun, error: str) -> None:
        _ = error
        run.status = "failed"
        run.completed_at = datetime.now(UTC)
        await self.session.flush()
