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


class ResumeTextRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=50_000)
