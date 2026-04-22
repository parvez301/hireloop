"""First-evaluation helper used only by the onboarding endpoint.

Wraps the regular evaluation pipeline with a single responsibility: given a
ParsedJob (the endpoint has already parsed the input), run scoring and return
a JSON-serializable dict ready for the frontend card. Keeps the onboarding
payload shape decoupled from EvaluationOut so we can tune it independently.
"""

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from hireloop.core.evaluation.job_parser import ParsedJob
from hireloop.core.evaluation.service import EvaluationContext, EvaluationService
from hireloop.services.usage_event import UsageEventService


async def run_first_evaluation(
    *,
    db: AsyncSession,
    user_id: UUID,
    parsed_job: ParsedJob,
) -> dict[str, Any]:
    context = EvaluationContext(
        user_id=user_id, session=db, usage=UsageEventService(db)
    )
    service = EvaluationService(context)
    evaluation = await service.evaluate_parsed(parsed_job)

    return {
        "id": str(evaluation.id),
        "overall_grade": evaluation.overall_grade,
        "match_score": evaluation.match_score,
        "dimension_scores": evaluation.dimension_scores,
        "reasoning": evaluation.reasoning,
        "recommendation": evaluation.recommendation,
        "red_flags": evaluation.red_flags,
        "personalization": evaluation.personalization,
        "cached": evaluation.cached,
        "job_id": str(evaluation.job_id) if evaluation.job_id else None,
    }
