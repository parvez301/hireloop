from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ScanRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    scan_config_id: UUID
    status: Literal["pending", "running", "completed", "failed"]
    jobs_found: int
    jobs_new: int
    truncated: bool
    error: str | None
    started_at: datetime
    completed_at: datetime | None


class ScanResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    job_id: UUID
    relevance_score: float | None
    is_new: bool
    created_at: datetime


class ScanRunDetail(BaseModel):
    scan_run: ScanRunOut
    results: list[ScanResultOut]
