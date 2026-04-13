"""Ashby posting API adapter."""

from __future__ import annotations

import re
from typing import Any

import httpx
from markdownify import markdownify as md

from hireloop.core.scanner.adapters.base import (
    BoardAdapter,
    BoardAdapterError,
    ListingPayload,
)
from hireloop.integrations.board_http import board_client, get_with_retry


class AshbyAdapter(BoardAdapter):
    platform = "ashby"

    async def fetch_listings(self, board_slug: str) -> list[ListingPayload]:
        url = (
            f"https://api.ashbyhq.com/posting-api/job-board/{board_slug}"
            "?includeCompensation=true"
        )
        try:
            async with board_client() as client:
                response = await get_with_retry(client, url, platform=self.platform)
        except httpx.HTTPError as e:
            raise BoardAdapterError(
                platform=self.platform, slug=board_slug, message=f"HTTP error: {e}"
            ) from e

        if response.status_code != 200:
            raise BoardAdapterError(
                platform=self.platform,
                slug=board_slug,
                message=f"API returned {response.status_code}",
            )

        try:
            data = response.json()
        except ValueError as e:
            raise BoardAdapterError(
                platform=self.platform,
                slug=board_slug,
                message=f"Invalid JSON: {e}",
            ) from e

        return [self._normalize(j, board_slug) for j in data.get("jobs", [])]

    def _normalize(self, job: dict[str, Any], board_slug: str) -> ListingPayload:
        description_html = job.get("descriptionHtml") or ""
        description_md = md(description_html).strip()
        employment_type = self._normalize_employment_type(job.get("employmentType"))
        comp = job.get("compensation") or {}
        salary_min, salary_max = self._parse_comp_tier(comp.get("compensationTierSummary"))

        return ListingPayload(
            title=str(job.get("title") or "Untitled"),
            company=board_slug,
            location=job.get("locationName"),
            salary_min=salary_min,
            salary_max=salary_max,
            employment_type=employment_type,
            seniority=self._guess_seniority(job.get("title")),
            description_md=description_md,
            requirements_json={},
            source_url=str(job.get("jobUrl") or ""),
        )

    @staticmethod
    def _normalize_employment_type(value: Any) -> str | None:
        if not isinstance(value, str):
            return None
        v = value.lower()
        if "full" in v:
            return "full_time"
        if "part" in v:
            return "part_time"
        if "contract" in v or "temp" in v:
            return "contract"
        return None

    @staticmethod
    def _parse_comp_tier(summary: Any) -> tuple[int | None, int | None]:
        """Parse "$180K – $240K" → (180000, 240000). Returns (None, None) on failure."""
        if not isinstance(summary, str):
            return (None, None)
        numbers = re.findall(r"\$?([\d,]+)\s*[Kk]?", summary)
        values: list[int] = []
        for raw in numbers:
            clean = raw.replace(",", "")
            try:
                n = int(clean)
            except ValueError:
                continue
            if "K" in summary.upper() and n < 10000:
                n *= 1000
            values.append(n)
        if len(values) >= 2:
            return (min(values[:2]), max(values[:2]))
        if len(values) == 1:
            return (values[0], None)
        return (None, None)

    @staticmethod
    def _guess_seniority(title: Any) -> str | None:
        if not isinstance(title, str):
            return None
        t = title.lower()
        for key in ("principal", "staff", "senior", "mid", "junior"):
            if key in t:
                return key
        return None
