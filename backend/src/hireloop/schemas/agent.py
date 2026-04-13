"""Card payloads matching parent spec Appendix G."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class EvaluationCardData(BaseModel):
    evaluation_id: str
    job_id: str
    job_title: str
    company: str | None
    location: str | None
    salary_range: str | None
    overall_grade: str
    match_score: float
    recommendation: Literal["strong_match", "worth_exploring", "skip"]
    dimension_scores: dict[str, dict[str, Any]]
    reasoning: str
    red_flags: list[str] = Field(default_factory=list)
    personalization: str | None = None
    cached: bool = False


class CvOutputCardData(BaseModel):
    cv_output_id: str
    job_id: str
    job_title: str
    company: str | None
    changes_summary: str | None
    keywords_injected: list[str] = Field(default_factory=list)
    pdf_url: str


class Card(BaseModel):
    type: Literal["evaluation", "cv_output"]
    data: dict[str, Any]


class SseEvent(BaseModel):
    """One SSE event: `event: {event_type}\ndata: {json}\n\n`"""

    event_type: Literal["classifier", "token", "tool_start", "tool_end", "card", "done", "error"]
    data: dict[str, Any]
