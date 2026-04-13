"""Content-hash dedup + jobs pool upsert."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hireloop.core.scanner.adapters.base import ListingPayload
from hireloop.models.job import Job


def compute_content_hash(listing: ListingPayload) -> str:
    """SHA256 of normalized description + requirements_json.

    Whitespace is normalized. Source URL is intentionally excluded so two boards
    hosting the same JD dedupe to one hash.
    """
    normalized_desc = " ".join(listing.description_md.split())
    normalized_reqs = json.dumps(listing.requirements_json, sort_keys=True)
    payload = normalized_desc + "|" + normalized_reqs
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


async def upsert_jobs_from_listings(
    session: AsyncSession,
    listings: Sequence[ListingPayload],
    *,
    platform: str,
    company_pretty_name: str,
    max_listings: int,
) -> tuple[list[tuple[Job, bool]], bool]:
    """Upsert listings into the jobs pool. Returns (rows, was_truncated).

    rows: list of (Job, is_new) tuples in the same order as the input listings
          that made the cut (up to `max_listings` after dedup).
    was_truncated: True when the input exceeded `max_listings`.
    """
    seen: set[str] = set()
    deduped: list[tuple[ListingPayload, str]] = []
    for listing in listings:
        h = compute_content_hash(listing)
        if h in seen:
            continue
        seen.add(h)
        deduped.append((listing, h))

    was_truncated = len(deduped) > max_listings
    if was_truncated:
        deduped = deduped[:max_listings]

    results: list[tuple[Job, bool]] = []
    for listing, content_hash in deduped:
        stmt = select(Job).where(Job.content_hash == content_hash)
        existing = (await session.execute(stmt)).scalar_one_or_none()
        if existing is not None:
            results.append((existing, False))
            continue

        job = Job(
            content_hash=content_hash,
            url=listing.source_url or None,
            title=listing.title,
            company=company_pretty_name,
            location=listing.location,
            salary_min=listing.salary_min,
            salary_max=listing.salary_max,
            employment_type=listing.employment_type,
            seniority=listing.seniority,
            description_md=listing.description_md,
            requirements_json=listing.requirements_json,
            source=platform,
            board_company=company_pretty_name,
        )
        session.add(job)
        await session.flush()
        results.append((job, True))

    return results, was_truncated
