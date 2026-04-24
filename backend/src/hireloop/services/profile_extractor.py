"""Layer-1 profile extraction from CV text (PERSONALISATION_STRATEGY.md).

Runs the Gemini Flash (BALANCED-tier) prompt from the spec doc against a
candidate's CV markdown and returns the inferable profile fields. Caller is
expected to merge the result onto the Profile row, only overwriting fields
that are currently null (don't clobber user-supplied onboarding answers).

Fields NOT extracted (collected via onboarding instead):
- salary_current / salary_target / notice_period — the model can't see them
- deal_breakers / non_negotiables — preference, not fact
- cv_tone / preferred_length — user style choice
- known_gaps — accumulated from evaluation history, not a single CV
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from hireloop.core.llm import gemini_client
from hireloop.core.llm.errors import LLMError
from hireloop.core.llm.router import resolve
from hireloop.core.llm.tier import Provider, Task

logger = logging.getLogger(__name__)

_VALID_SENIORITY = {"junior", "mid", "senior", "exec"}


@dataclass(frozen=True)
class ExtractedProfile:
    """Layer-1 fields the model can infer from CV text alone."""

    headline: str | None = None
    years_experience: int | None = None
    seniority_level: str | None = None
    industry: str | None = None
    specialisation: str | None = None
    top_strengths: list[str] | None = None
    certifications: list[str] | None = None
    languages: list[str] | None = None

    def as_assignments(self) -> dict[str, object]:
        """Return only the fields that have a non-empty value."""
        result: dict[str, object] = {}
        if self.headline:
            result["headline"] = self.headline
        if self.years_experience and self.years_experience > 0:
            result["years_experience"] = self.years_experience
        if self.seniority_level:
            result["seniority_level"] = self.seniority_level
        if self.industry:
            result["industry"] = self.industry
        if self.specialisation:
            result["specialisation"] = self.specialisation
        if self.top_strengths:
            result["top_strengths"] = self.top_strengths
        if self.certifications:
            result["certifications"] = self.certifications
        if self.languages:
            result["languages"] = self.languages
        return result


def _build_prompt(cv_text: str) -> str:
    # Verbatim from PERSONALISATION_STRATEGY.md lines 121-145, with the
    # `current_title` field renamed to `headline` to match our Profile model.
    return f"""Extract a structured profile from this CV.
Return JSON only, no preamble. Be specific — use exact phrases from the CV.
Do not invent facts: if a field can't be inferred, return an empty value.

CV:
{cv_text}

Return exactly:
{{
  "headline": "",
  "years_experience": 0,
  "seniority_level": "junior|mid|senior|exec",
  "industry": "",
  "specialisation": "",
  "top_strengths": [],
  "certifications": [],
  "languages": []
}}
"""


def _coerce_int(value: object) -> int | None:
    """Coerce to int. Treats 0 as 'not provided' — the spec doc uses 0 as the
    placeholder in the prompt template, so LLMs echo it back when they can't
    infer a number. We don't want to persist that as a real years count.
    """
    if isinstance(value, bool):
        return None
    candidate: int | None = None
    if isinstance(value, int):
        candidate = value
    elif isinstance(value, float):
        candidate = int(value)
    elif isinstance(value, str) and value.strip().isdigit():
        candidate = int(value.strip())
    return candidate if candidate and candidate > 0 else None


def _coerce_str_list(value: object) -> list[str] | None:
    if not isinstance(value, list):
        return None
    out = [item.strip() for item in value if isinstance(item, str) and item.strip()]
    return out or None


def _coerce_seniority(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip().lower()
    return cleaned if cleaned in _VALID_SENIORITY else None


def _coerce_str(value: object) -> str | None:
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None
    return None


def _normalise(payload: dict[str, object]) -> ExtractedProfile:
    return ExtractedProfile(
        headline=_coerce_str(payload.get("headline")),
        years_experience=_coerce_int(payload.get("years_experience")),
        seniority_level=_coerce_seniority(payload.get("seniority_level")),
        industry=_coerce_str(payload.get("industry")),
        specialisation=_coerce_str(payload.get("specialisation")),
        top_strengths=_coerce_str_list(payload.get("top_strengths")),
        certifications=_coerce_str_list(payload.get("certifications")),
        languages=_coerce_str_list(payload.get("languages")),
    )


async def extract_profile_from_cv(cv_text: str, *, timeout_s: float = 12.0) -> ExtractedProfile:
    """Run the Layer-1 extraction prompt and parse the response.

    Failures are logged and return an empty `ExtractedProfile` rather than
    raising — extraction is best-effort enrichment, not a critical-path step.
    A failed extraction still leaves the parsed CV available; the user can
    always backfill profile fields manually.
    """
    if not cv_text or not cv_text.strip():
        return ExtractedProfile()

    route = resolve(Task.PROFILE_EXTRACT)
    if route.provider is not Provider.GEMINI:
        # Phase 7 will introduce a unified Provider client. Until then this
        # service hard-pins Gemini for BALANCED tier — keeps the cutover
        # surface to one file when the abstraction lands.
        logger.warning(
            "profile_extract routing returned %s but service uses gemini directly",
            route.provider,
        )

    try:
        payload = await gemini_client.extract_json(_build_prompt(cv_text), timeout_s=timeout_s)
    except LLMError as exc:
        logger.warning("profile extraction failed: %s", exc)
        return ExtractedProfile()
    except Exception as exc:  # noqa: BLE001 — best-effort path
        logger.exception("profile extraction crashed: %s", exc)
        return ExtractedProfile()

    return _normalise(payload)


def merge_extracted_into_profile(profile: object, extracted: ExtractedProfile) -> list[str]:
    """Apply extracted fields to a Profile row, preserving any user input.

    Only overwrites attributes that are currently None/empty so that
    user-supplied onboarding answers always win over LLM inference.
    Returns the list of attribute names that were updated, useful for logging.
    """
    updated: list[str] = []
    for field, value in extracted.as_assignments().items():
        current = getattr(profile, field, None)
        if current in (None, "", []):
            setattr(profile, field, value)
            updated.append(field)
    return updated
