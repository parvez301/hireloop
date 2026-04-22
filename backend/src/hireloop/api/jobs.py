"""Jobs API — POST /jobs/parse (transient; does not persist)."""

from typing import Any

from fastapi import APIRouter

from hireloop.api.deps import EntitledDbUser
from hireloop.core.evaluation.job_parser import parse_description, parse_url
from hireloop.schemas.job import JobCreate, JobParseTextRequest

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/parse")
async def parse_job(payload: JobCreate, current_user: EntitledDbUser) -> dict[str, Any]:
    _ = current_user
    if payload.url:
        parsed = await parse_url(payload.url)
    else:
        assert payload.description_md is not None
        parsed = await parse_description(payload.description_md)

    return {
        "data": {
            "content_hash": parsed.content_hash,
            "url": parsed.url,
            "title": parsed.title,
            "company": parsed.company,
            "location": parsed.location,
            "salary_min": parsed.salary_min,
            "salary_max": parsed.salary_max,
            "employment_type": parsed.employment_type,
            "seniority": parsed.seniority,
            "description_md": parsed.description_md,
            "requirements_json": parsed.requirements_json,
        }
    }


@router.post("/parse-text")
async def parse_job_text(
    payload: JobParseTextRequest, current_user: EntitledDbUser
) -> dict[str, Any]:
    _ = current_user
    parsed = await parse_description(payload.text)
    return {
        "data": {
            "content_hash": parsed.content_hash,
            "url": payload.source_url or parsed.url,
            "title": parsed.title,
            "company": parsed.company,
            "location": parsed.location,
            "salary_min": parsed.salary_min,
            "salary_max": parsed.salary_max,
            "employment_type": parsed.employment_type,
            "seniority": parsed.seniority,
            "description_md": parsed.description_md,
            "requirements_json": parsed.requirements_json,
        }
    }
