from typing import Any

from pydantic import Field

from hireloop.schemas.common import ORMModel, TimestampedORM


class ProfileUpdate(ORMModel):
    target_roles: list[str] | None = None
    target_locations: list[str] | None = None
    min_salary: int | None = Field(default=None, ge=0)
    preferred_industries: list[str] | None = None
    linkedin_url: str | None = None
    github_url: str | None = None
    portfolio_url: str | None = None


class ProfileResponse(TimestampedORM):
    master_resume_md: str | None
    master_resume_s3: str | None
    parsed_resume_json: dict[str, Any] | None
    target_roles: list[str] | None
    target_locations: list[str] | None
    min_salary: int | None
    preferred_industries: list[str] | None
    linkedin_url: str | None
    github_url: str | None
    portfolio_url: str | None
    onboarding_state: str
