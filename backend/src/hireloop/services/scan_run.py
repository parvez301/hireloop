"""ScanRun CRUD helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hireloop.models.scan_run import ScanResult, ScanRun


class ScanRunService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_pending(
        self,
        *,
        user_id: UUID,
        scan_config_id: UUID,
        inngest_event_id: str | None = None,
    ) -> ScanRun:
        run = ScanRun(
            user_id=user_id,
            scan_config_id=scan_config_id,
            inngest_event_id=inngest_event_id,
            status="pending",
        )
        self.session.add(run)
        await self.session.flush()
        return run

    async def get_for_user(self, user_id: UUID, run_id: UUID) -> ScanRun | None:
        stmt = select(ScanRun).where(ScanRun.id == run_id, ScanRun.user_id == user_id)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def list_for_user(
        self, user_id: UUID, *, limit: int = 20, status: str | None = None
    ) -> list[ScanRun]:
        stmt = (
            select(ScanRun)
            .where(ScanRun.user_id == user_id)
            .order_by(ScanRun.started_at.desc())
            .limit(limit)
        )
        if status:
            stmt = stmt.where(ScanRun.status == status)
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_results(self, run_id: UUID, *, limit: int = 50) -> list[ScanResult]:
        stmt = (
            select(ScanResult)
            .where(ScanResult.scan_run_id == run_id)
            .order_by(ScanResult.relevance_score.desc().nullslast())
            .limit(limit)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def mark_running(self, run: ScanRun) -> None:
        run.status = "running"
        await self.session.flush()

    async def mark_completed(
        self,
        run: ScanRun,
        *,
        jobs_found: int,
        jobs_new: int,
        truncated: bool,
    ) -> None:
        run.status = "completed"
        run.jobs_found = jobs_found
        run.jobs_new = jobs_new
        run.truncated = truncated
        run.completed_at = datetime.now(UTC)
        await self.session.flush()

    async def mark_failed(self, run: ScanRun, error: str) -> None:
        run.status = "failed"
        run.error = error[:2000]
        run.completed_at = datetime.now(UTC)
        await self.session.flush()
