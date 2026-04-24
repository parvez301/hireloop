"""Evaluation orchestrator — parse → upsert job → cache/score → persist evaluation."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hireloop.config import get_settings
from hireloop.core.evaluation.cache import EvaluationCache
from hireloop.core.evaluation.claude_scorer import ClaudeScorer
from hireloop.core.evaluation.grader import EvaluationResult, Grader
from hireloop.core.evaluation.job_parser import (
    JobParseError,
    ParsedJob,
    parse_description,
    parse_url,
)
from hireloop.core.evaluation.rule_scorer import (
    SKIPPED,
    DimensionResult,
    RuleScorer,
    ScoringContext,
)
from hireloop.core.llm.anthropic_client import CallRoute
from hireloop.models.evaluation import Evaluation
from hireloop.models.job import Job
from hireloop.models.profile import Profile
from hireloop.services.usage_event import UsageEventService


@dataclass
class EvaluationContext:
    user_id: uuid.UUID
    session: AsyncSession
    usage: UsageEventService
    # Routing for the Claude scorer call. User-facing eval uses "realtime"
    # (direct API, fast TTFT). Background L2 batch eval uses "batch" (bridge
    # = Claude Max savings) with "realtime" as a fallback if the bridge fails.
    claude_route: CallRoute = "realtime"
    claude_fallback_route: CallRoute | None = None


class EvaluationService:
    def __init__(self, context: EvaluationContext):
        self.context = context
        self.cache = EvaluationCache(context.session)
        self.rule_scorer = RuleScorer()
        self.claude_scorer = ClaudeScorer()
        self.grader = Grader()

    async def evaluate(
        self,
        *,
        job_url: str | None = None,
        job_description: str | None = None,
    ) -> Evaluation:
        parsed = await self._parse(job_url=job_url, job_description=job_description)
        return await self.evaluate_parsed(parsed)

    async def evaluate_parsed(self, parsed: ParsedJob) -> Evaluation:
        """Run the scoring pipeline against an already-parsed job.

        Splits out the work downstream of parsing so callers that have already
        paid the parse cost (e.g. the onboarding first-evaluation endpoint)
        don't double-call the LLM parser.
        """
        profile = await self._load_profile()

        job = await self._upsert_job(parsed)

        scoring_context = self._build_scoring_context(profile)
        job_skills = set(parsed.requirements_json.get("skills", []))
        rule_dims: dict[str, Any] = {
            "skills_match": self.rule_scorer.score_skills_match(job_skills, scoring_context),
            "experience_fit": self.rule_scorer.score_experience_fit(
                required_years=parsed.requirements_json.get("years_experience"),
                context=scoring_context,
            ),
            "location_fit": self.rule_scorer.score_location_fit(parsed.location, scoring_context),
            "salary_fit": self.rule_scorer.score_salary_fit(
                salary_min=parsed.salary_min,
                salary_max=parsed.salary_max,
                context=scoring_context,
            ),
        }
        rule_text = self._rule_results_text(rule_dims)

        cached_claude = await self.cache.get(parsed.content_hash)
        was_cached = cached_claude is not None

        if cached_claude is not None:
            claude_dims = cached_claude["dimensions"]
            overall_reasoning = cached_claude.get("overall_reasoning", "")
            red_flag_items = cached_claude.get("red_flag_items", [])
            personalization_notes = cached_claude.get("personalization_notes")
            tokens_used = 0
            model_used = cached_claude.get("model_used", get_settings().claude_model)
        else:
            scored = await self.claude_scorer.score(
                job_markdown=parsed.description_md,
                profile_summary=self._compact_profile(profile),
                rule_results_text=rule_text,
                route=self.context.claude_route,
                fallback_route=self.context.claude_fallback_route,
            )
            claude_dims = scored.dimensions
            overall_reasoning = scored.overall_reasoning
            red_flag_items = scored.red_flag_items
            personalization_notes = scored.personalization_notes
            tokens_used = scored.usage.total_tokens
            model_used = scored.model

            await self.cache.put(
                content_hash=parsed.content_hash,
                base_evaluation={
                    "dimensions": claude_dims,
                    "overall_reasoning": overall_reasoning,
                    "red_flag_items": red_flag_items,
                    "personalization_notes": personalization_notes,
                    "model_used": model_used,
                },
                requirements_json=parsed.requirements_json,
                model_used=model_used,
            )
            await self.context.usage.record(
                user_id=self.context.user_id,
                event_type="evaluate",
                module="evaluation",
                model=model_used,
                tokens_used=tokens_used,
                cost_cents=scored.usage.cost_cents(model_used),
            )

        aggregate = self.grader.aggregate(
            rule_dims=rule_dims,
            claude_dims=claude_dims,
            overall_reasoning=overall_reasoning,
            red_flag_items=red_flag_items,
            personalization_notes=personalization_notes,
        )

        return await self._persist(job, aggregate, model_used, tokens_used, was_cached)

    async def _parse(self, *, job_url: str | None, job_description: str | None) -> ParsedJob:
        try:
            if job_url:
                return await parse_url(job_url)
            if job_description:
                return await parse_description(job_description)
            raise JobParseError("Provide either job_url or job_description")
        except JobParseError:
            raise

    async def _load_profile(self) -> Profile:
        stmt = select(Profile).where(Profile.user_id == self.context.user_id)
        profile = (await self.context.session.execute(stmt)).scalar_one_or_none()
        if profile is None:
            raise JobParseError("User has no profile — complete onboarding first")
        return profile

    def _build_scoring_context(self, profile: Profile) -> ScoringContext:
        parsed = profile.parsed_resume_json or {}
        skills = set(parsed.get("skills", []))
        years = int(parsed.get("total_years_experience", 0) or 0)
        return ScoringContext(
            profile_skills=skills,
            profile_years_experience=years,
            profile_target_locations=list(profile.target_locations or []),
            profile_min_salary=profile.min_salary,
        )

    def _compact_profile(self, profile: Profile) -> dict[str, Any]:
        parsed = profile.parsed_resume_json or {}
        return {
            "skills": list(parsed.get("skills", []))[:20],
            "years_experience": parsed.get("total_years_experience"),
            "target_roles": list(profile.target_roles or []),
            "target_locations": list(profile.target_locations or []),
            "recent_roles": parsed.get("recent_roles", [])[:3],
        }

    def _rule_results_text(self, rule_dims: dict[str, Any]) -> str:
        lines = []
        for name, result in rule_dims.items():
            if result is SKIPPED:
                lines.append(f"- {name}: SKIPPED (not applicable)")
            else:
                assert isinstance(result, DimensionResult)
                lines.append(f"- {name}: {result.score:.2f} ({result.details})")
        return "\n".join(lines)

    async def _upsert_job(self, parsed: ParsedJob) -> Job:
        stmt = select(Job).where(Job.content_hash == parsed.content_hash)
        existing = (await self.context.session.execute(stmt)).scalar_one_or_none()
        if existing is not None:
            return existing

        job = Job(
            content_hash=parsed.content_hash,
            url=parsed.url,
            title=parsed.title,
            company=parsed.company,
            location=parsed.location,
            salary_min=parsed.salary_min,
            salary_max=parsed.salary_max,
            employment_type=parsed.employment_type,
            seniority=parsed.seniority,
            description_md=parsed.description_md,
            requirements_json=parsed.requirements_json,
            source="manual",
        )
        self.context.session.add(job)
        await self.context.session.flush()
        return job

    async def _persist(
        self,
        job: Job,
        aggregate: EvaluationResult,
        model_used: str,
        tokens_used: int,
        was_cached: bool,
    ) -> Evaluation:
        stmt = select(Evaluation).where(
            Evaluation.user_id == self.context.user_id,
            Evaluation.job_id == job.id,
        )
        existing = (await self.context.session.execute(stmt)).scalar_one_or_none()

        if existing is not None:
            existing.overall_grade = aggregate.overall_grade
            existing.dimension_scores = aggregate.dimension_scores
            existing.reasoning = aggregate.reasoning
            existing.red_flags = aggregate.red_flags
            existing.personalization = aggregate.personalization
            existing.match_score = aggregate.match_score
            existing.recommendation = aggregate.recommendation
            existing.model_used = model_used
            existing.tokens_used = tokens_used
            existing.cached = was_cached
            row = existing
        else:
            row = Evaluation(
                user_id=self.context.user_id,
                job_id=job.id,
                overall_grade=aggregate.overall_grade,
                dimension_scores=aggregate.dimension_scores,
                reasoning=aggregate.reasoning,
                red_flags=aggregate.red_flags,
                personalization=aggregate.personalization,
                match_score=aggregate.match_score,
                recommendation=aggregate.recommendation,
                model_used=model_used,
                tokens_used=tokens_used,
                cached=was_cached,
            )
            self.context.session.add(row)

        await self.context.session.flush()
        return row
