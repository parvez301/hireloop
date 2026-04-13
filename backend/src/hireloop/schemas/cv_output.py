from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CvOutputCreate(BaseModel):
    job_id: UUID


class CvOutputRegenerate(BaseModel):
    feedback: str | None = None


class CvOutputOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    job_id: UUID
    tailored_md: str
    pdf_s3_key: str
    changes_summary: str | None = None
    model_used: str
    created_at: datetime
