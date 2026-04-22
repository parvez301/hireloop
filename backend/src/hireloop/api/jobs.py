"""Jobs API — POST /jobs/parse (transient; does not persist), GET /jobs/:id."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from hireloop.api.deps import CurrentDbUser, DbSession, EntitledDbUser
from hireloop.core.evaluation.job_parser import parse_description, parse_url
from hireloop.models.evaluation import Evaluation
from hireloop.models.job import Job
from hireloop.schemas.job import JobCreate, JobParseTextRequest

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}")
async def get_job(
    job_id: UUID,
    user: CurrentDbUser,
    session: DbSession,
) -> dict[str, Any]:
    job = (
        await session.execute(select(Job).where(Job.id == job_id))
    ).scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    evaluation = (
        await session.execute(
            select(Evaluation).where(
                Evaluation.job_id == job_id,
                Evaluation.user_id == user.id,
            )
        )
    ).scalar_one_or_none()

    return {
        "data": {
            "job": {
                "id": str(job.id),
                "content_hash": job.content_hash,
                "url": job.url,
                "title": job.title,
                "company": job.company,
                "location": job.location,
                "salary_min": job.salary_min,
                "salary_max": job.salary_max,
                "employment_type": job.employment_type,
                "seniority": job.seniority,
                "description_md": job.description_md,
                "requirements_json": job.requirements_json,
                "source": job.source,
                "discovered_at": job.discovered_at.isoformat()
                if job.discovered_at
                else None,
            },
            "evaluation": (
                {
                    "id": str(evaluation.id),
                    "overall_grade": evaluation.overall_grade,
                    "match_score": evaluation.match_score,
                    "reasoning": evaluation.reasoning,
                    "dimension_scores": evaluation.dimension_scores,
                    "red_flags": evaluation.red_flags,
                    "recommendation": evaluation.recommendation,
                }
                if evaluation is not None
                else None
            ),
        }
    }


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
