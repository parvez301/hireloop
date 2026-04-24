"""Layer-4 cross-reference map (PERSONALISATION_STRATEGY.md).

Per the spec doc:
    This cross-reference map is the most important personalisation input.
    Every downstream task — evaluation, CV rewrite, cover letter — receives it.

Maps the candidate's structured CV evidence against the structured JD
requirements: strong_matches[], gaps[], unique_angles[], overall_fit_score,
fit_summary. Built per (user, job) and cached in the `crossref_maps` table
so a single Gemini Flash call powers every downstream personalised generator.

Routing: Task.CROSSREF_MAP → BALANCED → Gemini Flash.
"""

from __future__ import annotations

import json
import logging
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hireloop.config import get_settings
from hireloop.core.llm import gemini_client
from hireloop.core.llm.errors import LLMError
from hireloop.core.llm.router import resolve
from hireloop.core.llm.tier import Provider, Task
from hireloop.models.crossref_map import CrossrefMap
from hireloop.models.job import Job
from hireloop.models.profile import Profile
from hireloop.services.jd_extractor import ensure_jd_structure

logger = logging.getLogger(__name__)


_VALID_STRENGTH = {"strong", "moderate", "weak"}
_VALID_GAP_SEVERITY = {"critical", "moderate", "minor"}
_VALID_GRADES = {"A", "B+", "B", "C+", "C", "D", "F"}


def _build_prompt(cv_structure: dict[str, Any], jd_structure: dict[str, Any]) -> str:
    # Verbatim adaptation of PERSONALISATION_STRATEGY.md lines 264-301.
    return f"""Map this candidate's CV evidence against the job requirements.
Be specific — quote exact phrases from both documents.
Return JSON only, no preamble.

CV Structure:
{json.dumps(cv_structure)}

JD Structure:
{json.dumps(jd_structure)}

Return:
{{
  "strong_matches": [
    {{
      "jd_requirement": "exact phrase from JD",
      "cv_evidence": "exact phrase/achievement from CV",
      "strength": "strong|moderate|weak"
    }}
  ],
  "gaps": [
    {{
      "jd_requirement": "exact phrase from JD",
      "gap_severity": "critical|moderate|minor",
      "mitigation": "how candidate can address this"
    }}
  ],
  "unique_angles": [
    "Something in CV that is not required but highly relevant"
  ],
  "overall_fit_score": "A|B+|B|C+|C|D|F",
  "fit_summary": "One sentence specific to this candidate and role"
}}
"""


def _coerce_str(value: object) -> str:
    if isinstance(value, str):
        return value.strip()
    return ""


def _coerce_str_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


def _coerce_enum(value: object, allowed: set[str]) -> str:
    if isinstance(value, str):
        cleaned = value.strip().lower()
        if cleaned in allowed:
            return cleaned
    return ""


def _coerce_grade(value: object) -> str:
    if isinstance(value, str):
        cleaned = value.strip().upper()
        if cleaned in _VALID_GRADES:
            return cleaned
    return ""


def _normalise_match(raw: object) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    match = {
        "jd_requirement": _coerce_str(raw.get("jd_requirement")),
        "cv_evidence": _coerce_str(raw.get("cv_evidence")),
        "strength": _coerce_enum(raw.get("strength"), _VALID_STRENGTH),
    }
    if not match["jd_requirement"] and not match["cv_evidence"]:
        return None
    return match


def _normalise_gap(raw: object) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    gap = {
        "jd_requirement": _coerce_str(raw.get("jd_requirement")),
        "gap_severity": _coerce_enum(raw.get("gap_severity"), _VALID_GAP_SEVERITY),
        "mitigation": _coerce_str(raw.get("mitigation")),
    }
    if not gap["jd_requirement"]:
        return None
    return gap


def _normalise(payload: dict[str, object]) -> dict[str, Any]:
    matches_raw = payload.get("strong_matches")
    matches: list[dict[str, Any]] = []
    if isinstance(matches_raw, list):
        for raw in matches_raw:
            match = _normalise_match(raw)
            if match is not None:
                matches.append(match)

    gaps_raw = payload.get("gaps")
    gaps: list[dict[str, Any]] = []
    if isinstance(gaps_raw, list):
        for raw in gaps_raw:
            gap = _normalise_gap(raw)
            if gap is not None:
                gaps.append(gap)

    return {
        "strong_matches": matches,
        "gaps": gaps,
        "unique_angles": _coerce_str_list(payload.get("unique_angles")),
        "overall_fit_score": _coerce_grade(payload.get("overall_fit_score")),
        "fit_summary": _coerce_str(payload.get("fit_summary")),
    }


async def extract_crossref_map(
    cv_structure: dict[str, Any],
    jd_structure: dict[str, Any],
    *,
    timeout_s: float = 25.0,
) -> dict[str, Any] | None:
    """Run the cross-reference prompt and return the normalised map.

    Returns None on LLM failure — caller should treat absence as "no map yet"
    and either skip personalisation or fall back to a less-rich generator.
    """
    if not cv_structure or not jd_structure:
        return None

    route = resolve(Task.CROSSREF_MAP)
    if route.provider is not Provider.GEMINI:
        logger.warning(
            "crossref_map routing returned %s but service uses gemini directly",
            route.provider,
        )

    try:
        payload = await gemini_client.extract_json(
            _build_prompt(cv_structure, jd_structure), timeout_s=timeout_s
        )
    except LLMError as exc:
        logger.warning("crossref map extraction failed: %s", exc)
        return None
    except Exception as exc:  # noqa: BLE001 — best-effort path
        logger.exception("crossref map extraction crashed: %s", exc)
        return None

    return _normalise(payload)


async def get_crossref_map(db: AsyncSession, user_id: UUID, job_id: UUID) -> CrossrefMap | None:
    result = await db.execute(
        select(CrossrefMap).where(CrossrefMap.user_id == user_id, CrossrefMap.job_id == job_id)
    )
    return result.scalar_one_or_none()


async def ensure_crossref_map(db: AsyncSession, profile: Profile, job: Job) -> CrossrefMap | None:
    """Ensure a crossref map exists for (user, job), extracting if not.

    Idempotent: returns the cached row when present. On miss:
    1. Ensures `job.parsed_jd_json` is populated (cascades to jd_extractor).
    2. Reads `profile.parsed_resume_json["structure"]` (Layer-2 CV structure).
    3. Calls Gemini Flash to build the map.
    4. Persists into `crossref_maps` and returns the row.

    Returns None on any extraction failure or missing inputs (no CV structure
    on profile, JD extraction failed, etc.) — callers should fall back to
    raw text rather than crash.
    """
    cached = await get_crossref_map(db, profile.user_id, job.id)
    if cached is not None:
        return cached

    cv_structure = (
        profile.parsed_resume_json.get("structure") if profile.parsed_resume_json else None
    )
    if not cv_structure:
        logger.info("crossref skipped: no CV structure on profile %s", profile.user_id)
        return None

    jd_structure = await ensure_jd_structure(db, job)
    if not jd_structure:
        logger.info("crossref skipped: JD extraction failed for job %s", job.id)
        return None

    body = await extract_crossref_map(cv_structure, jd_structure)
    if body is None:
        return None

    settings = get_settings()
    row = CrossrefMap(
        user_id=profile.user_id,
        job_id=job.id,
        body=body,
        model_used=settings.gemini_model,
    )
    db.add(row)
    await db.flush()
    return row
