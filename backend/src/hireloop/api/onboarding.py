"""Onboarding-specific endpoints.

POST /onboarding/first-evaluation — orchestrates parse-job + evaluate in one
shot so the frontend can show a single loading state for the ~60s flow.
"""

from fastapi import APIRouter

from hireloop.api.deps import CurrentDbUser, DbSession
from hireloop.api.errors import AppError
from hireloop.core.evaluation.first_evaluation import run_first_evaluation
from hireloop.core.evaluation.job_parser import parse_description, parse_url
from hireloop.schemas.common import Envelope
from hireloop.schemas.onboarding import FirstEvaluationRequest, FirstEvaluationResponse
from hireloop.services.profile import get_or_create_profile

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


@router.post("/first-evaluation", response_model=Envelope[FirstEvaluationResponse])
async def first_evaluation(
    body: FirstEvaluationRequest,
    user: CurrentDbUser,
    db: DbSession,
) -> Envelope[FirstEvaluationResponse]:
    profile = await get_or_create_profile(db, user)
    if not profile.master_resume_md:
        raise AppError(409, "RESUME_REQUIRED", "Upload a resume before running an evaluation.")

    if body.job_input.type == "url":
        parsed = await parse_url(body.job_input.value)
    else:
        parsed = await parse_description(body.job_input.value)

    evaluation = await run_first_evaluation(db=db, user_id=user.id, parsed_job=parsed)

    return Envelope(
        data=FirstEvaluationResponse(
            evaluation=evaluation,
            job={
                "content_hash": parsed.content_hash,
                "url": parsed.url,
                "title": parsed.title,
                "company": parsed.company,
                "location": parsed.location,
                "description_md": parsed.description_md,
            },
        )
    )
