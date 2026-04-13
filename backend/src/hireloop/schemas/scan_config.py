from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CompanyRef(BaseModel):
    name: str
    platform: Literal["greenhouse", "ashby", "lever"]
    board_slug: str


class ScanConfigCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    companies: list[CompanyRef] = Field(..., min_length=1)
    keywords: list[str] | None = None
    exclude_keywords: list[str] | None = None
    schedule: Literal["manual", "daily", "weekly"] = "manual"


class ScanConfigUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    companies: list[CompanyRef] | None = None
    keywords: list[str] | None = None
    exclude_keywords: list[str] | None = None
    schedule: Literal["manual", "daily", "weekly"] | None = None
    is_active: bool | None = None


class ScanConfigOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    name: str
    companies: list[dict[str, Any]]
    keywords: list[str] | None
    exclude_keywords: list[str] | None
    schedule: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
