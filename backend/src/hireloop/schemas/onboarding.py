"""Onboarding request/response schemas."""

from typing import Any, Literal

from pydantic import BaseModel, Field


class JobInput(BaseModel):
    type: Literal["url", "text"]
    value: str = Field(..., min_length=1, max_length=50_000)


class FirstEvaluationRequest(BaseModel):
    job_input: JobInput


class FirstEvaluationResponse(BaseModel):
    evaluation: dict[str, Any]
    job: dict[str, Any]
