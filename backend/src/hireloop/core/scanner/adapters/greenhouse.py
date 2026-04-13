"""Greenhouse boards API adapter."""

from __future__ import annotations

from typing import Any

import httpx
from markdownify import markdownify as md

from hireloop.core.scanner.adapters.base import (
    BoardAdapter,
    BoardAdapterError,
    ListingPayload,
)
from hireloop.integrations.board_http import board_client, get_with_retry


class GreenhouseAdapter(BoardAdapter):
    platform = "greenhouse"

    async def fetch_listings(self, board_slug: str) -> list[ListingPayload]:
        url = f"https://boards-api.greenhouse.io/v1/boards/{board_slug}/jobs?content=true"
        try:
            async with board_client() as client:
                response = await get_with_retry(client, url, platform=self.platform)
        except httpx.HTTPError as e:
            raise BoardAdapterError(
                platform=self.platform,
                slug=board_slug,
                message=f"HTTP error: {e}",
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

        listings: list[ListingPayload] = []
        for job in data.get("jobs", []):
            listings.append(self._normalize(job, board_slug))
        return listings

    def _normalize(self, job: dict[str, Any], board_slug: str) -> ListingPayload:
        location_obj = job.get("location") or {}
        location = location_obj.get("name") if isinstance(location_obj, dict) else None

        description_html = job.get("content") or ""
        description_md = md(description_html).strip()

        metadata = {m.get("name", ""): m.get("value") for m in (job.get("metadata") or [])}
        employment_type = self._normalize_employment_type(metadata.get("Employment Type"))
        seniority = self._normalize_seniority(metadata.get("Seniority Level"))

        return ListingPayload(
            title=str(job.get("title") or "Untitled"),
            company=board_slug,
            location=location,
            salary_min=None,
            salary_max=None,
            employment_type=employment_type,
            seniority=seniority,
            description_md=description_md,
            requirements_json={},
            source_url=str(job.get("absolute_url") or ""),
        )

    @staticmethod
    def _normalize_employment_type(value: Any) -> str | None:
        if not isinstance(value, str):
            return None
        v = value.lower().strip()
        if "full" in v:
            return "full_time"
        if "part" in v:
            return "part_time"
        if "contract" in v:
            return "contract"
        return None

    @staticmethod
    def _normalize_seniority(value: Any) -> str | None:
        if not isinstance(value, str):
            return None
        v = value.lower().strip()
        for key in ("principal", "staff", "senior", "mid", "junior"):
            if key in v:
                return key
        return None
