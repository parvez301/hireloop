from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class BatchRunCreate(BaseModel):
    job_urls: list[str] | None = None
    job_ids: list[UUID] | None = None
    scan_run_id: UUID | None = None

    @model_validator(mode="after")
    def _exactly_one_input(self) -> BatchRunCreate:
        provided = [x is not None for x in (self.job_urls, self.job_ids, self.scan_run_id)]
        if sum(provided) != 1:
            raise ValueError("Provide exactly one of job_urls, job_ids, or scan_run_id")
        return self


class BatchRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    status: Literal["pending", "running", "completed", "failed"]
    total_jobs: int
    l0_passed: int
    l1_passed: int
    l2_evaluated: int
    source_type: str
    source_ref: str | None
    started_at: datetime
    completed_at: datetime | None


class BatchItemsSummary(BaseModel):
    queued: int = 0
    l0: int = 0
    l1: int = 0
    l2: int = 0
    done: int = 0
    filtered: int = 0


class BatchEvaluationSummary(BaseModel):
    evaluation_id: UUID
    job_id: UUID
    job_title: str
    company: str | None
    overall_grade: str
    match_score: float


class BatchRunDetail(BaseModel):
    batch_run: BatchRunOut
    items_summary: BatchItemsSummary
    top_results: list[BatchEvaluationSummary] = Field(default_factory=list)
