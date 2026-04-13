from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class EvaluationCreate(BaseModel):
    job_url: str | None = None
    job_description: str | None = None

    @model_validator(mode="after")
    def _exclusive(self) -> EvaluationCreate:
        if bool(self.job_url) == bool(self.job_description):
            raise ValueError("Provide exactly one of job_url or job_description")
        return self


class DimensionScore(BaseModel):
    score: float
    grade: str
    reasoning: str
    signals: list[str] = Field(default_factory=list)


class EvaluationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    job_id: UUID
    overall_grade: str
    dimension_scores: dict[str, DimensionScore]
    reasoning: str
    red_flags: list[str] | None = None
    personalization: str | None = None
    match_score: float
    recommendation: Literal["strong_match", "worth_exploring", "skip"]
    model_used: str
    tokens_used: int | None = None
    cached: bool
    created_at: datetime

    @field_validator("dimension_scores", mode="before")
    @classmethod
    def _coerce_dimension_scores(cls, v: Any) -> Any:
        if not isinstance(v, dict):
            return v
        out: dict[str, Any] = {}
        for key, val in v.items():
            if isinstance(val, DimensionScore):
                out[key] = val
            elif isinstance(val, dict):
                out[key] = DimensionScore(**val)
            else:
                out[key] = val
        return out


class EvaluationListFilters(BaseModel):
    grade: str | None = None
    since: datetime | None = None
    limit: int = Field(default=20, ge=1, le=100)
    cursor: str | None = None
