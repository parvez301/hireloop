from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class StarStoryCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    situation: str = Field(..., min_length=1)
    task: str = Field(..., min_length=1)
    action: str = Field(..., min_length=1)
    result: str = Field(..., min_length=1)
    reflection: str | None = None
    tags: list[str] | None = None


class StarStoryUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    situation: str | None = None
    task: str | None = None
    action: str | None = None
    result: str | None = None
    reflection: str | None = None
    tags: list[str] | None = None


class StarStoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    title: str
    situation: str
    task: str
    action: str
    result: str
    reflection: str | None
    tags: list[str] | None
    source: Literal["ai_generated", "user_created"]
    created_at: datetime
