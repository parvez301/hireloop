from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

ApplicationStatus = Literal["saved", "applied", "interviewing", "offered", "rejected", "withdrawn"]


class ApplicationCreate(BaseModel):
    job_id: UUID
    status: ApplicationStatus = "saved"
    evaluation_id: UUID | None = None
    cv_output_id: UUID | None = None
    notes: str | None = None


class ApplicationUpdate(BaseModel):
    status: ApplicationStatus | None = None
    notes: str | None = None
    applied_at: datetime | None = None
    cv_output_id: UUID | None = None


class ApplicationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    job_id: UUID
    status: ApplicationStatus
    applied_at: datetime | None
    notes: str | None
    evaluation_id: UUID | None
    cv_output_id: UUID | None
    negotiation_id: UUID | None
    updated_at: datetime
