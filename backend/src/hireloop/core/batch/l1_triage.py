"""L1 triage — Gemini relevance scoring wrapper for batch use."""

from __future__ import annotations

import asyncio
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hireloop.config import get_settings
from hireloop.core.scanner.relevance import score_relevance
from hireloop.models.job import Job
from hireloop.models.profile import Profile


async def score_jobs_relevance(
    session: AsyncSession,
    *,
    user_id: UUID,
    job_ids: list[UUID],
) -> dict[str, float]:
    """Return {str(job_id): relevance_score} for the given jobs."""
    if not job_ids:
        return {}

    profile = (
        await session.execute(select(Profile).where(Profile.user_id == user_id))
    ).scalar_one_or_none()
    profile_summary: dict[str, Any] = {}
    if profile is not None:
        parsed = profile.parsed_resume_json or {}
        profile_summary = {
            "skills": list(parsed.get("skills", []))[:20],
            "years_experience": parsed.get("total_years_experience"),
            "target_roles": list(profile.target_roles or []),
            "target_locations": list(profile.target_locations or []),
        }

    jobs = (await session.execute(select(Job).where(Job.id.in_(job_ids)))).scalars().all()

    settings = get_settings()
    sem = asyncio.Semaphore(max(1, settings.scan_l1_concurrency))

    async def _one(job: Job) -> tuple[str, float]:
        async with sem:
            score = await score_relevance(job=job, profile_summary=profile_summary)
        return str(job.id), score

    pairs = await asyncio.gather(*(_one(j) for j in jobs))
    return dict(pairs)
