from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator


class InterviewPrepCreate(BaseModel):
    job_id: UUID | None = None
    custom_role: str | None = None

    @model_validator(mode="after")
    def _exactly_one(self) -> InterviewPrepCreate:
        if bool(self.job_id) == bool(self.custom_role):
            raise ValueError("Provide exactly one of job_id or custom_role")
        return self


class InterviewPrepRegenerate(BaseModel):
    feedback: str | None = None


class InterviewPrepQuestion(BaseModel):
    question: str
    category: str
    suggested_story_title: str | None = None
    framework: str | None = None


class InterviewPrepRedFlagQuestion(BaseModel):
    question: str
    what_to_listen_for: str | None = None


class InterviewPrepOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    job_id: UUID | None
    custom_role: str | None
    questions: list[dict[str, Any]]
    red_flag_questions: list[dict[str, Any]] | None
    model_used: str
    tokens_used: int | None
    created_at: datetime
