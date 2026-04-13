"""Lever postings API adapter."""

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


class LeverAdapter(BoardAdapter):
    platform = "lever"

    async def fetch_listings(self, board_slug: str) -> list[ListingPayload]:
        url = f"https://api.lever.co/v0/postings/{board_slug}?mode=json"
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
            postings = response.json()
        except ValueError as e:
            raise BoardAdapterError(
                platform=self.platform,
                slug=board_slug,
                message=f"Invalid JSON: {e}",
            ) from e

        if not isinstance(postings, list):
            raise BoardAdapterError(
                platform=self.platform,
                slug=board_slug,
                message="Expected JSON array of postings",
            )

        return [self._normalize(p, board_slug) for p in postings]

    def _normalize(self, posting: dict[str, Any], board_slug: str) -> ListingPayload:
        categories = posting.get("categories") or {}
        title = str(posting.get("text") or "Untitled")
        description_plain = str(posting.get("descriptionPlain") or "")
        # Flatten "lists" (requirements, benefits, etc.) into the description
        lists = posting.get("lists") or []
        extras = "\n\n".join(
            f"### {item.get('text', 'Details')}\n\n{md(str(item.get('content', ''))).strip()}"
            for item in lists
            if isinstance(item, dict)
        )
        description_md = (description_plain + "\n\n" + extras).strip()

        return ListingPayload(
            title=title,
            company=board_slug,
            location=categories.get("location"),
            salary_min=None,
            salary_max=None,
            employment_type=self._normalize_commitment(categories.get("commitment")),
            seniority=self._guess_seniority(title),
            description_md=description_md,
            requirements_json={},
            source_url=str(posting.get("hostedUrl") or ""),
        )

    @staticmethod
    def _normalize_commitment(value: Any) -> str | None:
        if not isinstance(value, str):
            return None
        v = value.lower()
        if "full" in v:
            return "full_time"
        if "part" in v:
            return "part_time"
        if "contract" in v or "intern" in v:
            return "contract"
        return None

    @staticmethod
    def _guess_seniority(title: str) -> str | None:
        t = title.lower()
        for key in ("principal", "staff", "senior", "mid", "junior"):
            if key in t:
                return key
        return None
