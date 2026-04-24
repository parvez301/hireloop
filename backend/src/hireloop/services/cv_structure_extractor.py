"""Layer-2 structured CV extraction (PERSONALISATION_STRATEGY.md).

Takes the markdown CV produced by `resume_parser` and asks Gemini Flash to
parse it into the structured schema the downstream personalised generators
expect: roles[] with achievements + technologies, hard_skills, soft_skills,
notable_numbers, certifications, career_narrative.

Stored alongside the raw text on `profile.parsed_resume_json` under the
`structure` key so the existing text-only consumers keep working.

Fail-soft like profile_extractor: on any LLM error we return None and the
caller proceeds with raw text. Structured extraction is enrichment, not a
critical-path step — the raw markdown is always available.
"""

from __future__ import annotations

import logging
from typing import Any

from hireloop.core.llm import gemini_client
from hireloop.core.llm.errors import LLMError
from hireloop.core.llm.router import resolve
from hireloop.core.llm.tier import Provider, Task

logger = logging.getLogger(__name__)


def _build_prompt(cv_text: str) -> str:
    # Verbatim adaptation of PERSONALISATION_STRATEGY.md lines 173-213.
    return f"""Parse this CV into a structured format.
Return JSON only. Be extremely specific — use exact phrases,
numbers, company names, and technologies from the CV.
Do not paraphrase or generalise. If a field can't be inferred,
return an empty value (omit nothing).

CV:
{cv_text}

Return:
{{
  "roles": [
    {{
      "title": "",
      "company": "",
      "duration_months": 0,
      "start_year": 0,
      "end_year": 0,
      "key_achievements": [
        "Built X that resulted in Y measured by Z"
      ],
      "technologies": [],
      "team_size_managed": 0,
      "budget_managed": ""
    }}
  ],
  "education": [
    {{
      "degree": "",
      "institution": "",
      "year": 0
    }}
  ],
  "hard_skills": [],
  "soft_skills": [],
  "notable_numbers": [
    "Reduced billing errors by 40%",
    "Managed team of 12 across 3 countries"
  ],
  "certifications": [],
  "career_narrative": "One paragraph summary of trajectory"
}}
"""


def _coerce_str(value: object) -> str:
    if isinstance(value, str):
        return value.strip()
    return ""


def _coerce_int(value: object) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return value if value > 0 else 0
    if isinstance(value, float):
        return int(value) if value > 0 else 0
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return 0


def _coerce_str_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


def _normalise_role(raw: object) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    role = {
        "title": _coerce_str(raw.get("title")),
        "company": _coerce_str(raw.get("company")),
        "duration_months": _coerce_int(raw.get("duration_months")),
        "start_year": _coerce_int(raw.get("start_year")),
        "end_year": _coerce_int(raw.get("end_year")),
        "key_achievements": _coerce_str_list(raw.get("key_achievements")),
        "technologies": _coerce_str_list(raw.get("technologies")),
        "team_size_managed": _coerce_int(raw.get("team_size_managed")),
        "budget_managed": _coerce_str(raw.get("budget_managed")),
    }
    # Drop entirely-empty roles — they're prompt template placeholders that
    # the model echoed back when no real role was present.
    if not role["title"] and not role["company"] and not role["key_achievements"]:
        return None
    return role


def _normalise_education(raw: object) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    edu = {
        "degree": _coerce_str(raw.get("degree")),
        "institution": _coerce_str(raw.get("institution")),
        "year": _coerce_int(raw.get("year")),
    }
    if not edu["degree"] and not edu["institution"]:
        return None
    return edu


def _normalise(payload: dict[str, object]) -> dict[str, Any]:
    roles_raw = payload.get("roles")
    roles: list[dict[str, Any]] = []
    if isinstance(roles_raw, list):
        for raw in roles_raw:
            role = _normalise_role(raw)
            if role is not None:
                roles.append(role)

    education_raw = payload.get("education")
    education: list[dict[str, Any]] = []
    if isinstance(education_raw, list):
        for raw in education_raw:
            edu = _normalise_education(raw)
            if edu is not None:
                education.append(edu)

    return {
        "roles": roles,
        "education": education,
        "hard_skills": _coerce_str_list(payload.get("hard_skills")),
        "soft_skills": _coerce_str_list(payload.get("soft_skills")),
        "notable_numbers": _coerce_str_list(payload.get("notable_numbers")),
        "certifications": _coerce_str_list(payload.get("certifications")),
        "career_narrative": _coerce_str(payload.get("career_narrative")),
    }


async def extract_cv_structure(cv_text: str, *, timeout_s: float = 20.0) -> dict[str, Any] | None:
    """Run the Layer-2 structure extraction prompt and return normalised dict.

    Returns None on empty input or LLM failure — caller should treat absence
    as "structure unavailable" and fall back to raw markdown.
    """
    if not cv_text or not cv_text.strip():
        return None

    route = resolve(Task.CV_STRUCTURE_EXTRACT)
    if route.provider is not Provider.GEMINI:
        logger.warning(
            "cv_structure_extract routing returned %s but service uses gemini directly",
            route.provider,
        )

    try:
        payload = await gemini_client.extract_json(_build_prompt(cv_text), timeout_s=timeout_s)
    except LLMError as exc:
        logger.warning("CV structure extraction failed: %s", exc)
        return None
    except Exception as exc:  # noqa: BLE001 — best-effort path
        logger.exception("CV structure extraction crashed: %s", exc)
        return None

    return _normalise(payload)
