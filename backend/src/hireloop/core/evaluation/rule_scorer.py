"""Pure-Python deterministic scoring for 4 of the 10 dimensions.

These dimensions are recomputed per user on every evaluation because they
depend on the user's profile, not the job alone.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

SKIPPED: Any = object()

_LOCATION_ALIASES = {
    "nyc": "new york",
    "ny": "new york",
    "sf": "san francisco",
    "la": "los angeles",
}


@dataclass
class DimensionResult:
    score: float
    details: str = ""
    signals: list[str] = field(default_factory=list)


@dataclass
class ScoringContext:
    profile_skills: set[str]
    profile_years_experience: int
    profile_target_locations: list[str]
    profile_min_salary: int | None


def _normalize_skill(s: str) -> str:
    return s.strip().lower().replace("-", " ").replace("_", " ")


def _normalize_location(loc: str) -> str:
    loc = loc.strip().lower()
    for short, long_form in _LOCATION_ALIASES.items():
        if short in loc.split():
            loc = loc.replace(short, long_form)
    return loc


class RuleScorer:
    """Score 4 rule-based dimensions. No I/O, no LLM calls."""

    def score_skills_match(self, job_skills: set[str], context: ScoringContext) -> DimensionResult:
        if not job_skills:
            return DimensionResult(score=1.0, details="No required skills listed")

        job_normalized = {_normalize_skill(s) for s in job_skills}
        profile_normalized = {_normalize_skill(s) for s in context.profile_skills}
        matches = job_normalized & profile_normalized

        score = len(matches) / len(job_normalized)
        matched_list = ", ".join(sorted(matches))
        return DimensionResult(
            score=round(score, 3),
            details=f"Matched {len(matches)} of {len(job_normalized)}: {matched_list}",
            signals=sorted(matches),
        )

    def score_experience_fit(
        self, *, required_years: int | None, context: ScoringContext
    ) -> DimensionResult:
        if required_years is None:
            return DimensionResult(score=1.0, details="No experience requirement stated")
        if context.profile_years_experience >= required_years:
            return DimensionResult(
                score=1.0,
                details=(
                    f"{context.profile_years_experience} years meets "
                    f"{required_years}+ requirement"
                ),
            )
        ratio = context.profile_years_experience / required_years
        return DimensionResult(
            score=round(ratio, 3),
            details=f"{context.profile_years_experience}/{required_years} years",
        )

    def score_location_fit(
        self, job_location: str | None, context: ScoringContext
    ) -> DimensionResult:
        if not job_location:
            return DimensionResult(score=1.0, details="No location specified")
        normalized = _normalize_location(job_location)
        if "remote" in normalized:
            return DimensionResult(score=1.0, details="Remote")
        for target in context.profile_target_locations:
            nt = _normalize_location(target)
            if nt in normalized or normalized in nt:
                return DimensionResult(score=1.0, details=f"Matches target: {target}")
        return DimensionResult(score=0.0, details=f"{job_location} not in targets")

    def score_salary_fit(
        self,
        *,
        salary_min: int | None,
        salary_max: int | None,
        context: ScoringContext,
    ) -> Any:
        if salary_min is None and salary_max is None:
            return SKIPPED
        if context.profile_min_salary is None:
            return DimensionResult(score=1.0, details="No minimum salary set")
        compare = salary_max if salary_max is not None else salary_min
        if compare is None or compare >= context.profile_min_salary:
            return DimensionResult(
                score=1.0,
                details=f"${compare:,} meets ${context.profile_min_salary:,} floor",
            )
        return DimensionResult(
            score=0.0,
            details=f"${compare:,} below ${context.profile_min_salary:,} floor",
        )
