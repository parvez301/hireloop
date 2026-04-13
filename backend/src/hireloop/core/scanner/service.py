"""ScannerService — orchestrator called from scan_boards_fn Inngest function."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hireloop.config import get_settings
from hireloop.core.scanner.adapters import BoardAdapter, BoardAdapterError, ListingPayload
from hireloop.core.scanner.adapters.ashby import AshbyAdapter
from hireloop.core.scanner.adapters.greenhouse import GreenhouseAdapter
from hireloop.core.scanner.adapters.lever import LeverAdapter
from hireloop.core.scanner.dedup import upsert_jobs_from_listings
from hireloop.core.scanner.relevance import score_relevance
from hireloop.models.job import Job
from hireloop.models.profile import Profile
from hireloop.models.scan_config import ScanConfig
from hireloop.models.scan_run import ScanResult, ScanRun
from hireloop.services.scan_run import ScanRunService

_ADAPTERS: dict[str, BoardAdapter] = {
    "greenhouse": GreenhouseAdapter(),
    "ashby": AshbyAdapter(),
    "lever": LeverAdapter(),
}


@dataclass
class ScanRunOutcome:
    jobs_found: int
    jobs_new: int
    truncated: bool


class ScannerService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.runs = ScanRunService(session)

    async def run_scan(self, scan_run_id: UUID) -> ScanRunOutcome:
        """Execute a scan run end-to-end."""
        run = (
            await self.session.execute(select(ScanRun).where(ScanRun.id == scan_run_id))
        ).scalar_one()
        config = (
            await self.session.execute(
                select(ScanConfig).where(ScanConfig.id == run.scan_config_id)
            )
        ).scalar_one()
        profile = (
            await self.session.execute(select(Profile).where(Profile.user_id == run.user_id))
        ).scalar_one_or_none()

        await self.runs.mark_running(run)

        try:
            all_listings = await self._scrape_all_boards(config.companies)
        except Exception as e:
            await self.runs.mark_failed(run, f"Scrape failed: {e}")
            raise

        if not all_listings:
            await self.runs.mark_completed(run, jobs_found=0, jobs_new=0, truncated=False)
            return ScanRunOutcome(jobs_found=0, jobs_new=0, truncated=False)

        settings = get_settings()
        rows_with_flags: list[tuple[Job, bool]] = []
        all_truncated = False
        grouped: dict[tuple[str, str], list[ListingPayload]] = {}
        for listing, platform, company in all_listings:
            grouped.setdefault((platform, company), []).append(listing)

        for (platform, company), listings in grouped.items():
            rows, truncated = await upsert_jobs_from_listings(
                self.session,
                listings,
                platform=platform,
                company_pretty_name=company,
                max_listings=settings.scan_max_listings_per_run,
            )
            rows_with_flags.extend(rows)
            if truncated:
                all_truncated = True

        if len(rows_with_flags) > settings.scan_max_listings_per_run:
            rows_with_flags = rows_with_flags[: settings.scan_max_listings_per_run]
            all_truncated = True

        profile_summary = self._compact_profile(profile)
        new_jobs = [(j, is_new) for (j, is_new) in rows_with_flags if is_new]

        sem = asyncio.Semaphore(max(1, settings.scan_l1_concurrency))

        async def _score(job: Job) -> float:
            async with sem:
                return await score_relevance(job=job, profile_summary=profile_summary)

        new_scores = await asyncio.gather(*(_score(j) for (j, _) in new_jobs))
        new_score_map = {nj.id: sc for (nj, _), sc in zip(new_jobs, new_scores, strict=True)}

        for job, is_new in rows_with_flags:
            result = ScanResult(
                scan_run_id=run.id,
                job_id=job.id,
                relevance_score=new_score_map.get(job.id),
                is_new=is_new,
            )
            self.session.add(result)
        await self.session.flush()

        await self.runs.mark_completed(
            run,
            jobs_found=len(rows_with_flags),
            jobs_new=sum(1 for _, is_new in rows_with_flags if is_new),
            truncated=all_truncated,
        )
        return ScanRunOutcome(
            jobs_found=len(rows_with_flags),
            jobs_new=len(new_jobs),
            truncated=all_truncated,
        )

    async def _scrape_all_boards(
        self, companies: list[dict[str, Any]]
    ) -> list[tuple[ListingPayload, str, str]]:
        """Scrape all configured companies in parallel."""

        async def _one(company: dict[str, Any]) -> list[tuple[ListingPayload, str, str]]:
            platform = str(company.get("platform") or "")
            slug = str(company.get("board_slug") or "")
            pretty = str(company.get("name") or slug)
            adapter = _ADAPTERS.get(platform)
            if adapter is None:
                return []
            try:
                listings = await adapter.fetch_listings(slug)
            except BoardAdapterError:
                return []
            return [(lst, platform, pretty) for lst in listings]

        results = await asyncio.gather(*(_one(c) for c in companies))
        return [item for sub in results for item in sub]

    @staticmethod
    def _compact_profile(profile: Profile | None) -> dict[str, Any]:
        if profile is None:
            return {}
        parsed = profile.parsed_resume_json or {}
        return {
            "skills": list(parsed.get("skills", []))[:20],
            "years_experience": parsed.get("total_years_experience"),
            "target_roles": list(profile.target_roles or []),
            "target_locations": list(profile.target_locations or []),
        }
