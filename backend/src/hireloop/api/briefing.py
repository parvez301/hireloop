"""`GET /api/v1/me/briefing` — morning aggregate for the Dashboard module.

Returns top-graded recent jobs + pipeline counts by stage + next upcoming
interview in one round trip so the dashboard can render with a single call.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter
from sqlalchemy import func, select

from hireloop.api.deps import CurrentDbUser, DbSession
from hireloop.models.application import Application
from hireloop.models.evaluation import Evaluation
from hireloop.models.interview_prep import InterviewPrep
from hireloop.models.job import Job
from hireloop.schemas.common import Envelope

router = APIRouter(prefix="/me", tags=["briefing"])


@router.get("/briefing")
async def get_briefing(
    user: CurrentDbUser,
    db: DbSession,
) -> Envelope[dict[str, Any]]:
    since = datetime.now(UTC) - timedelta(days=7)

    # Top 3 evaluations by match_score from the last 7 days.
    top_stmt = (
        select(Evaluation, Job)
        .join(Job, Evaluation.job_id == Job.id)
        .where(
            Evaluation.user_id == user.id,
            Evaluation.created_at >= since,
        )
        .order_by(Evaluation.match_score.desc())
        .limit(3)
    )
    top_rows = (await db.execute(top_stmt)).all()
    top_jobs = [
        {
            "evaluation_id": str(evaluation.id),
            "job_id": str(job.id),
            "title": job.title,
            "company": job.company,
            "location": job.location,
            "overall_grade": evaluation.overall_grade,
            "match_score": evaluation.match_score,
            "created_at": evaluation.created_at.isoformat(),
        }
        for evaluation, job in top_rows
    ]

    # Pipeline stage counts.
    stage_stmt = (
        select(Application.status, func.count(Application.id))
        .where(Application.user_id == user.id)
        .group_by(Application.status)
    )
    stage_rows = (await db.execute(stage_stmt)).all()
    stage_counts = {status: count for status, count in stage_rows}

    # Next upcoming interview prep (by created_at desc; schema has no scheduled_at).
    next_prep_stmt = (
        select(InterviewPrep)
        .where(InterviewPrep.user_id == user.id)
        .order_by(InterviewPrep.created_at.desc())
        .limit(1)
    )
    next_prep = (await db.execute(next_prep_stmt)).scalar_one_or_none()
    next_prep_summary: dict[str, Any] | None = None
    if next_prep is not None:
        next_prep_summary = {
            "id": str(next_prep.id),
            "job_id": str(next_prep.job_id) if next_prep.job_id else None,
            "custom_role": next_prep.custom_role,
            "created_at": next_prep.created_at.isoformat(),
        }

    return Envelope(
        data={
            "top_jobs": top_jobs,
            "pipeline_counts": stage_counts,
            "next_prep": next_prep_summary,
            "generated_at": datetime.now(UTC).isoformat(),
        }
    )
