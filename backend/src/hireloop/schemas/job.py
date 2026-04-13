from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class JobRequirements(BaseModel):
    skills: list[str] = Field(default_factory=list)
    years_experience: int | None = None
    nice_to_haves: list[str] = Field(default_factory=list)
    other: dict[str, Any] = Field(default_factory=dict)


class JobCreate(BaseModel):
    """Payload for POST /jobs/parse — exactly one of url or description_md."""

    url: str | None = None
    description_md: str | None = None

    @model_validator(mode="after")
    def _exclusive(self) -> JobCreate:
        if bool(self.url) == bool(self.description_md):
            raise ValueError("Provide exactly one of url or description_md")
        return self


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    content_hash: str
    url: str | None = None
    title: str
    company: str | None = None
    location: str | None = None
    salary_min: int | None = None
    salary_max: int | None = None
    employment_type: str | None = None
    seniority: str | None = None
    description_md: str
    requirements_json: dict[str, Any] | None = None
    source: str
    board_company: str | None = None
    discovered_at: datetime
    expires_at: datetime | None = None
