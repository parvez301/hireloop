"""L0 rule filter — pure Python, no I/O, no LLM.

Parent spec Appendix D.8. Returns (passes, reason_if_filtered).
"""

from __future__ import annotations

from typing import Any

from hireloop.models.job import Job
from hireloop.models.profile import Profile

_LOCATION_ALIASES = {
    "nyc": "new york",
    "ny": "new york",
    "sf": "san francisco",
    "la": "los angeles",
}


def _normalize_location(loc: str) -> str:
    loc = loc.strip().lower()
    for short, full in _LOCATION_ALIASES.items():
        if short in loc.split():
            loc = loc.replace(short, full)
    return loc


def _location_match(job_location: str | None, targets: list[str]) -> bool:
    if not job_location:
        return True  # unknown → pass
    normalized = _normalize_location(job_location)
    if "remote" in normalized:
        return True
    for target in targets:
        if _normalize_location(target) in normalized:
            return True
        if normalized in _normalize_location(target):
            return True
    return False


_SENIORITY_RANK = {
    "junior": 1,
    "mid": 2,
    "senior": 3,
    "staff": 4,
    "principal": 5,
}


def _seniority_from_years(years: int) -> str:
    if years < 2:
        return "junior"
    if years < 5:
        return "mid"
    if years < 8:
        return "senior"
    if years < 12:
        return "staff"
    return "principal"


def l0_filter(job: Job, profile: Profile) -> tuple[bool, str | None]:
    """Returns (passes, reason_if_filtered)."""
    targets: list[str] = list(profile.target_locations or [])
    if not _location_match(job.location, targets):
        return False, "location_mismatch"

    if profile.min_salary is not None:
        posted_max = job.salary_max
        if posted_max is not None and posted_max < profile.min_salary:
            return False, "below_min_salary"

    if job.seniority:
        parsed: dict[str, Any] = profile.parsed_resume_json or {}
        years = int(parsed.get("total_years_experience") or 0)
        profile_seniority = _seniority_from_years(years)
        profile_rank = _SENIORITY_RANK.get(profile_seniority, 3)
        job_rank = _SENIORITY_RANK.get(job.seniority.lower(), profile_rank)
        if abs(job_rank - profile_rank) > 1:
            return False, "seniority_mismatch"

    return True, None
