from typing import Any

from pydantic import BaseModel, Field

from hireloop.schemas.common import ORMModel, TimestampedORM


class ProfileUpdate(ORMModel):
    full_name: str | None = Field(default=None, max_length=200)
    headline: str | None = Field(default=None, max_length=300)
    current_location: str | None = Field(default=None, max_length=200)
    target_roles: list[str] | None = None
    target_locations: list[str] | None = None
    min_salary: int | None = Field(default=None, ge=0)
    preferred_industries: list[str] | None = None
    work_arrangement: str | None = Field(default=None, max_length=32)
    linkedin_url: str | None = None
    github_url: str | None = None
    portfolio_url: str | None = None
    # Layer-1 personalisation fields. All optional — onboarding fills these
    # progressively, the CV extractor backfills what it can infer.
    years_experience: int | None = Field(default=None, ge=0, le=80)
    seniority_level: str | None = Field(default=None, max_length=32)
    industry: str | None = Field(default=None, max_length=120)
    specialisation: str | None = Field(default=None, max_length=255)
    salary_current: str | None = Field(default=None, max_length=120)
    salary_target: str | None = Field(default=None, max_length=120)
    notice_period: str | None = Field(default=None, max_length=64)
    deal_breakers: list[str] | None = None
    non_negotiables: list[str] | None = None
    top_strengths: list[str] | None = None
    known_gaps: list[str] | None = None
    certifications: list[str] | None = None
    languages: list[str] | None = None
    cv_tone: str | None = Field(default=None, max_length=32)
    preferred_length: str | None = Field(default=None, max_length=32)


class ProfileResponse(TimestampedORM):
    full_name: str | None
    headline: str | None
    current_location: str | None
    master_resume_md: str | None
    master_resume_s3: str | None
    parsed_resume_json: dict[str, Any] | None
    target_roles: list[str] | None
    target_locations: list[str] | None
    min_salary: int | None
    preferred_industries: list[str] | None
    work_arrangement: str | None
    linkedin_url: str | None
    github_url: str | None
    portfolio_url: str | None
    onboarding_state: str
    # Layer-1 personalisation fields.
    years_experience: int | None
    seniority_level: str | None
    industry: str | None
    specialisation: str | None
    salary_current: str | None
    salary_target: str | None
    notice_period: str | None
    deal_breakers: list[str] | None
    non_negotiables: list[str] | None
    top_strengths: list[str] | None
    known_gaps: list[str] | None
    certifications: list[str] | None
    languages: list[str] | None
    cv_tone: str | None
    preferred_length: str | None


class ResumeTextRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=50_000)
