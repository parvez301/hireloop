from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

FeedbackResourceType = Literal["evaluation", "cv_output", "interview_prep", "negotiation"]


class FeedbackCreate(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    correction_notes: str | None = None


class FeedbackOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    resource_type: FeedbackResourceType
    resource_id: UUID
    rating: int
    correction_notes: str | None
    created_at: datetime
