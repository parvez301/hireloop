"""Agent tools: evaluate_job, optimize_cv, start_job_scan, start_batch_evaluation.

Wrappers over services — they accept an injected runtime context."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hireloop.api.errors import AppError
from hireloop.core.cv_optimizer.service import (
    CvOptimizerContext,
    CvOptimizerService,
    EvaluationRequiredError,
)
from hireloop.core.evaluation.job_parser import JobParseError
from hireloop.core.evaluation.service import EvaluationContext, EvaluationService
from hireloop.models.job import Job
from hireloop.models.scan_config import ScanConfig
from hireloop.services.scan_run import ScanRunService
from hireloop.services.usage_event import UsageEventService


@dataclass
class ToolRuntime:
    """Runtime dependencies available to tool handlers."""

    user_id: UUID
    session: AsyncSession

    @property
    def usage(self) -> UsageEventService:
        return UsageEventService(self.session)


async def evaluate_job_tool(
    runtime: ToolRuntime,
    *,
    job_url: str | None = None,
    job_description: str | None = None,
) -> dict[str, Any]:
    """Evaluate a single job. Returns {ok, card} or {ok: False, error_code, message}."""
    if not job_url and not job_description:
        return {
            "ok": False,
            "error_code": "JOB_PARSE_FAILED",
            "message": "Provide either job_url or job_description",
        }

    context = EvaluationContext(
        user_id=runtime.user_id, session=runtime.session, usage=runtime.usage
    )
    service = EvaluationService(context)
    try:
        evaluation = await service.evaluate(job_url=job_url, job_description=job_description)
    except JobParseError as e:
        return {"ok": False, "error_code": "JOB_PARSE_FAILED", "message": str(e)}

    job = (
        await runtime.session.execute(select(Job).where(Job.id == evaluation.job_id))
    ).scalar_one()

    salary_range = None
    if job.salary_min and job.salary_max:
        salary_range = f"${job.salary_min:,} - ${job.salary_max:,}"

    return {
        "ok": True,
        "card": {
            "type": "evaluation",
            "data": {
                "evaluation_id": str(evaluation.id),
                "job_id": str(evaluation.job_id),
                "job_title": job.title,
                "company": job.company,
                "location": job.location,
                "salary_range": salary_range,
                "overall_grade": evaluation.overall_grade,
                "match_score": evaluation.match_score,
                "recommendation": evaluation.recommendation,
                "dimension_scores": evaluation.dimension_scores,
                "reasoning": evaluation.reasoning,
                "red_flags": evaluation.red_flags or [],
                "personalization": evaluation.personalization,
                "cached": evaluation.cached,
            },
        },
    }


async def optimize_cv_tool(
    runtime: ToolRuntime,
    *,
    job_id: str,
) -> dict[str, Any]:
    """Generate a tailored resume PDF for a previously-evaluated job."""
    try:
        job_uuid = UUID(str(job_id))
    except ValueError:
        return {
            "ok": False,
            "error_code": "JOB_PARSE_FAILED",
            "message": "Invalid job_id format",
        }

    context = CvOptimizerContext(
        user_id=runtime.user_id, session=runtime.session, usage=runtime.usage
    )
    service = CvOptimizerService(context)
    try:
        cv = await service.optimize(job_id=job_uuid)
    except EvaluationRequiredError as e:
        return {
            "ok": False,
            "error_code": "EVALUATION_REQUIRES_JOB",
            "message": str(e),
        }

    job = (await runtime.session.execute(select(Job).where(Job.id == cv.job_id))).scalar_one()

    return {
        "ok": True,
        "card": {
            "type": "cv_output",
            "data": {
                "cv_output_id": str(cv.id),
                "job_id": str(cv.job_id),
                "job_title": job.title,
                "company": job.company,
                "changes_summary": cv.changes_summary,
                "keywords_injected": [],
                "pdf_url": f"/api/v1/cv-outputs/{cv.id}/pdf",
            },
        },
    }


async def start_job_scan_tool(
    runtime: ToolRuntime,
    *,
    scan_config_id: str | None = None,
) -> dict[str, Any]:
    """Start an async scan. If scan_config_id is None, use user's default config."""
    import inngest

    from hireloop.core.scanner.default_config import DEFAULT_SCAN_CONFIG_NAME
    from hireloop.inngest.client import get_inngest_client

    # Resolve the config
    if scan_config_id is not None:
        try:
            cfg_uuid = UUID(scan_config_id)
        except ValueError:
            return {
                "ok": False,
                "error_code": "SCAN_CONFIG_NOT_FOUND",
                "message": "Invalid scan_config_id",
            }
        stmt = select(ScanConfig).where(
            ScanConfig.id == cfg_uuid, ScanConfig.user_id == runtime.user_id
        )
    else:
        stmt = select(ScanConfig).where(
            ScanConfig.user_id == runtime.user_id,
            ScanConfig.name == DEFAULT_SCAN_CONFIG_NAME,
        )
    config = (await runtime.session.execute(stmt)).scalar_one_or_none()
    if config is None:
        return {
            "ok": False,
            "error_code": "SCAN_CONFIG_NOT_FOUND",
            "message": "No scan config found. Complete onboarding to get the default one.",
        }

    runs = ScanRunService(runtime.session)
    scan_run = await runs.create_pending(user_id=runtime.user_id, scan_config_id=config.id)

    client = get_inngest_client()
    try:
        sent_ids = await client.send(
            inngest.Event(
                name="scan/started",
                data={
                    "scan_config_id": str(config.id),
                    "user_id": str(runtime.user_id),
                    "scan_run_id": str(scan_run.id),
                },
            )
        )
    except Exception as e:
        await runs.mark_failed(scan_run, f"Inngest send failed: {e}")
        return {
            "ok": False,
            "error_code": "INNGEST_UNAVAILABLE",
            "message": "Background worker is unavailable — try again in a moment.",
        }
    if sent_ids:
        scan_run.inngest_event_id = str(sent_ids[0])
        await runtime.session.flush()

    return {
        "ok": True,
        "card": {
            "type": "scan_progress",
            "data": {
                "scan_run_id": str(scan_run.id),
                "scan_name": config.name,
                "status": scan_run.status,
                "companies_count": len(config.companies),
            },
        },
    }


async def start_batch_evaluation_tool(
    runtime: ToolRuntime,
    *,
    scan_run_id: str | None = None,
    job_urls: list[str] | None = None,
    job_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Start an async batch evaluation."""
    import inngest

    from hireloop.core.batch.service import BatchService
    from hireloop.inngest.client import get_inngest_client

    provided = [x is not None for x in (scan_run_id, job_urls, job_ids)]
    if sum(provided) != 1:
        return {
            "ok": False,
            "error_code": "INVALID_BATCH_INPUT",
            "message": "Provide exactly one of scan_run_id, job_urls, or job_ids",
        }

    service = BatchService(runtime.session)
    try:
        if scan_run_id is not None:
            srid = UUID(scan_run_id)
            resolved = await service.resolve_job_ids_from_scan(
                user_id=runtime.user_id, scan_run_id=srid
            )
            source_type = "scan_run_id"
            source_ref = scan_run_id
        elif job_urls is not None:
            resolved = await service.resolve_job_ids_from_urls(
                user_id=runtime.user_id, urls=job_urls
            )
            source_type = "job_urls"
            source_ref = None
        else:
            assert job_ids is not None
            parsed_ids = [UUID(j) for j in job_ids]
            resolved = await service.resolve_job_ids_from_ids(ids=parsed_ids)
            source_type = "job_ids"
            source_ref = None
    except AppError as e:
        return {
            "ok": False,
            "error_code": e.code,
            "message": e.message,
        }
    except (ValueError, TypeError) as e:
        return {
            "ok": False,
            "error_code": "INVALID_BATCH_INPUT",
            "message": str(e),
        }

    if not resolved:
        return {
            "ok": False,
            "error_code": "INVALID_BATCH_INPUT",
            "message": "No valid jobs resolved from input",
        }

    run = await service.start_batch(
        user_id=runtime.user_id,
        job_ids=resolved,
        source_type=source_type,
        source_ref=source_ref,
    )

    client = get_inngest_client()
    try:
        sent_ids = await client.send(
            inngest.Event(
                name="batch/started",
                data={"batch_run_id": str(run.id), "user_id": str(runtime.user_id)},
            )
        )
    except Exception:
        return {
            "ok": False,
            "error_code": "INNGEST_UNAVAILABLE",
            "message": "Background worker is unavailable",
        }
    if sent_ids:
        run.inngest_event_id = str(sent_ids[0])
        await runtime.session.flush()

    return {
        "ok": True,
        "card": {
            "type": "batch_progress",
            "data": {
                "batch_run_id": str(run.id),
                "status": run.status,
                "total": run.total_jobs,
                "l0_passed": 0,
                "l1_passed": 0,
                "l2_evaluated": 0,
            },
        },
    }


async def build_interview_prep_tool(
    runtime: ToolRuntime,
    *,
    job_id: str | None = None,
    custom_role: str | None = None,
) -> dict[str, Any]:
    """Build interview prep. Exactly one of job_id / custom_role required."""
    from hireloop.api.errors import AppError
    from hireloop.core.interview_prep.service import (
        InterviewPrepContext,
        InterviewPrepService,
    )

    if bool(job_id) == bool(custom_role):
        return {
            "ok": False,
            "error_code": "INVALID_INTERVIEW_PREP_INPUT",
            "message": "Provide exactly one of job_id or custom_role",
        }

    job_uuid: UUID | None = None
    if job_id is not None:
        try:
            job_uuid = UUID(str(job_id))
        except ValueError:
            return {
                "ok": False,
                "error_code": "INVALID_INTERVIEW_PREP_INPUT",
                "message": "Invalid job_id format",
            }

    ctx = InterviewPrepContext(
        user_id=runtime.user_id,
        session=runtime.session,
        usage=runtime.usage,
    )
    service = InterviewPrepService(ctx)
    try:
        prep = await service.create(job_id=job_uuid, custom_role=custom_role)
    except AppError as e:
        return {"ok": False, "error_code": e.code, "message": e.message}

    top_questions = [
        {
            "question": q.get("question", ""),
            "category": q.get("category", ""),
            "suggested_story_title": q.get("suggested_story_title"),
        }
        for q in (prep.questions or [])[:5]
    ]
    red_flags = [
        {
            "question": r.get("question", ""),
            "what_to_listen_for": r.get("what_to_listen_for", ""),
        }
        for r in (prep.red_flag_questions or [])
    ]
    return {
        "ok": True,
        "card": {
            "type": "interview_prep",
            "data": {
                "interview_prep_id": str(prep.id),
                "job_id": str(prep.job_id) if prep.job_id else None,
                "role": custom_role or "This job",
                "story_count": len(prep.questions or []),
                "question_count": len(prep.questions or []),
                "top_questions": top_questions,
                "red_flag_questions": red_flags,
            },
        },
    }


async def generate_negotiation_playbook_tool(
    runtime: ToolRuntime,
    *,
    job_id: str,
) -> dict[str, Any]:
    """Signal UI to collect offer details; direct API creates the playbook."""
    _ = runtime
    try:
        UUID(str(job_id))
    except ValueError:
        return {
            "ok": False,
            "error_code": "INVALID_BATCH_INPUT",
            "message": "Invalid job_id format",
        }
    return {
        "ok": False,
        "error_code": "OFFER_DETAILS_REQUIRED",
        "message": "Open the negotiation form to enter your offer details.",
        "offer_form_job_id": str(job_id),
    }
