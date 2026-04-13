"""Base classes for job-board adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ListingPayload:
    """Normalized job listing across all platforms."""

    title: str
    company: str
    location: str | None
    salary_min: int | None
    salary_max: int | None
    employment_type: str | None
    seniority: str | None
    description_md: str
    requirements_json: dict[str, Any] = field(default_factory=dict)
    source_url: str = ""


class BoardAdapterError(Exception):
    """Raised when a board adapter fails to fetch or parse listings."""

    def __init__(self, *, platform: str, slug: str, message: str):
        super().__init__(f"[{platform}:{slug}] {message}")
        self.platform = platform
        self.slug = slug


class BoardAdapter(ABC):
    """Abstract base: one subclass per supported platform."""

    platform: str

    @abstractmethod
    async def fetch_listings(self, board_slug: str) -> list[ListingPayload]:
        """Fetch and normalize all open listings for a company slug."""
