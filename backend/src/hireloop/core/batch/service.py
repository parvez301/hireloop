"""BatchService — resolves input, runs funnel, finalizes."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hireloop.api.errors import AppError
from hireloop.core.batch.funnel import run_l0, run_l1, run_l2
from hireloop.core.evaluation.job_parser import JobParseError, parse_url
from hireloop.models.batch_run import BatchItem, BatchRun
from hireloop.models.job import Job
from hireloop.models.scan_run import ScanResult, ScanRun
from hireloop.services.batch_run import BatchRunService


class BatchService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.runs = BatchRunService(session)

    async def resolve_job_ids_from_scan(self, *, user_id: UUID, scan_run_id: UUID) -> list[UUID]:
        run = (
            await self.session.execute(
                select(ScanRun).where(ScanRun.id == scan_run_id, ScanRun.user_id == user_id)
            )
        ).scalar_one_or_none()
        if run is None:
            raise AppError(404, "SCAN_RUN_NOT_FOUND", "Scan run not found")
        if run.status != "completed":
            raise AppError(409, "SCAN_RUN_STILL_RUNNING", "Scan run not yet complete")
        results = (
            (
                await self.session.execute(
                    select(ScanResult).where(ScanResult.scan_run_id == scan_run_id)
                )
            )
            .scalars()
            .all()
        )
        return [r.job_id for r in results]

    async def resolve_job_ids_from_urls(self, *, user_id: UUID, urls: list[str]) -> list[UUID]:
        """Parse each URL through the Phase 2a job parser. Dedupes into jobs pool."""
        _ = user_id
        job_ids: list[UUID] = []
        for url in urls:
            try:
                parsed = await parse_url(url)
            except JobParseError:
                continue
            h = parsed.content_hash
            existing = (
                await self.session.execute(select(Job).where(Job.content_hash == h))
            ).scalar_one_or_none()
            if existing is not None:
                job_ids.append(existing.id)
                continue
            job = Job(
                content_hash=h,
                url=parsed.url,
                title=parsed.title,
                company=parsed.company,
                location=parsed.location,
                salary_min=parsed.salary_min,
                salary_max=parsed.salary_max,
                employment_type=parsed.employment_type,
                seniority=parsed.seniority,
                description_md=parsed.description_md,
                requirements_json=parsed.requirements_json,
                source="manual",
            )
            self.session.add(job)
            await self.session.flush()
            job_ids.append(job.id)
        return job_ids

    async def resolve_job_ids_from_ids(self, *, ids: list[UUID]) -> list[UUID]:
        stmt = select(Job.id).where(Job.id.in_(ids))
        existing = (await self.session.execute(stmt)).scalars().all()
        return list(existing)

    async def start_batch(
        self,
        *,
        user_id: UUID,
        job_ids: list[UUID],
        source_type: str,
        source_ref: str | None,
    ) -> BatchRun:
        run = await self.runs.create_pending(
            user_id=user_id,
            total_jobs=len(job_ids),
            source_type=source_type,
            source_ref=source_ref,
        )
        for jid in job_ids:
            self.session.add(BatchItem(batch_run_id=run.id, job_id=jid, stage="queued"))
        await self.session.flush()
        return run

    async def run_funnel(self, *, batch_run_id: UUID) -> None:
        run = (
            await self.session.execute(select(BatchRun).where(BatchRun.id == batch_run_id))
        ).scalar_one()
        await self.runs.mark_running(run)
        item_rows = (
            (await self.session.execute(select(BatchItem).where(BatchItem.batch_run_id == run.id)))
            .scalars()
            .all()
        )
        job_ids: list[UUID] = [i.job_id for i in item_rows]

        try:
            l0_survivors = await run_l0(
                self.session,
                batch_run_id=run.id,
                job_ids=job_ids,
                user_id=run.user_id,
            )
            l1_survivors = await run_l1(
                self.session,
                batch_run_id=run.id,
                job_ids=l0_survivors,
                user_id=run.user_id,
            )
            evaluated = await run_l2(
                self.session,
                batch_run_id=run.id,
                job_ids=l1_survivors,
                user_id=run.user_id,
            )
        except Exception as e:
            await self.runs.mark_failed(run, str(e))
            raise

        await self.runs.mark_completed(
            run,
            l0_passed=len(l0_survivors),
            l1_passed=len(l1_survivors),
            l2_evaluated=len(evaluated),
        )
