"""Layer-3 structured JD extraction (PERSONALISATION_STRATEGY.md).

Uses Groq Llama 3.1 8B (FAST tier) per the routing matrix — JD parsing is
high-volume, structured, doesn't need reasoning depth. Output goes into
`Job.parsed_jd_json`.

Lazy-by-design: scanner ingestion stays fast (no LLM call per scraped job).
The first downstream consumer that needs structured JD facts (Phase 4 cross-
reference map, Phase 5b refactored generators) calls `ensure_jd_structure(job)`
which extracts on first use and persists for everyone after.

Schema verbatim from PERSONALISATION_STRATEGY.md lines 234-251.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from hireloop.core.llm import groq_client
from hireloop.core.llm.errors import LLMError
from hireloop.core.llm.router import resolve
from hireloop.core.llm.tier import Provider, Task
from hireloop.models.job import Job

logger = logging.getLogger(__name__)


def _build_prompt(jd_text: str) -> str:
    return f"""Parse this job description into structured requirements.
Return JSON only, no preamble. Use exact phrases from the JD.
If a field can't be inferred, return an empty value of the right type.

JD:
{jd_text}

Return:
{{
  "title": "",
  "company": "",
  "seniority": "junior|mid|senior|exec",
  "must_have_skills": [],
  "nice_to_have_skills": [],
  "years_experience_required": 0,
  "management_required": false,
  "key_responsibilities": [],
  "red_flag_requirements": [],
  "company_stage": "startup|scaleup|enterprise",
  "remote_policy": "remote|hybrid|onsite",
  "salary_range": "",
  "application_questions": []
}}
"""


_VALID_SENIORITY = {"junior", "mid", "senior", "exec"}
_VALID_COMPANY_STAGE = {"startup", "scaleup", "enterprise"}
_VALID_REMOTE_POLICY = {"remote", "hybrid", "onsite"}


def _coerce_str(value: object) -> str:
    if isinstance(value, str):
        return value.strip()
    return ""


def _coerce_str_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


def _coerce_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ("true", "yes", "1")
    return False


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


def _coerce_enum(value: object, allowed: set[str]) -> str:
    if isinstance(value, str):
        cleaned = value.strip().lower()
        if cleaned in allowed:
            return cleaned
    return ""


def _normalise(payload: dict[str, object]) -> dict[str, Any]:
    return {
        "title": _coerce_str(payload.get("title")),
        "company": _coerce_str(payload.get("company")),
        "seniority": _coerce_enum(payload.get("seniority"), _VALID_SENIORITY),
        "must_have_skills": _coerce_str_list(payload.get("must_have_skills")),
        "nice_to_have_skills": _coerce_str_list(payload.get("nice_to_have_skills")),
        "years_experience_required": _coerce_int(payload.get("years_experience_required")),
        "management_required": _coerce_bool(payload.get("management_required")),
        "key_responsibilities": _coerce_str_list(payload.get("key_responsibilities")),
        "red_flag_requirements": _coerce_str_list(payload.get("red_flag_requirements")),
        "company_stage": _coerce_enum(payload.get("company_stage"), _VALID_COMPANY_STAGE),
        "remote_policy": _coerce_enum(payload.get("remote_policy"), _VALID_REMOTE_POLICY),
        "salary_range": _coerce_str(payload.get("salary_range")),
        "application_questions": _coerce_str_list(payload.get("application_questions")),
    }


async def extract_jd_structure(jd_text: str, *, timeout_s: float = 12.0) -> dict[str, Any] | None:
    """Run the Layer-3 structure extraction prompt and return normalised dict.

    Returns None on empty input or LLM failure. Caller should treat absence
    as "structure unavailable" and fall back to raw description_md.
    """
    if not jd_text or not jd_text.strip():
        return None

    route = resolve(Task.JD_ENTITY_EXTRACT)
    if route.provider is not Provider.GROQ:
        logger.warning(
            "jd_extract routing returned %s but service uses groq directly",
            route.provider,
        )

    try:
        payload = await groq_client.complete_json(user=_build_prompt(jd_text), timeout_s=timeout_s)
    except LLMError as exc:
        logger.warning("JD extraction failed: %s", exc)
        return None
    except Exception as exc:  # noqa: BLE001 — best-effort path
        logger.exception("JD extraction crashed: %s", exc)
        return None

    return _normalise(payload)


async def ensure_jd_structure(db: AsyncSession, job: Job) -> dict[str, Any] | None:
    """Ensure `job.parsed_jd_json` is populated, extracting + persisting if not.

    Idempotent: a non-None `parsed_jd_json` is returned as-is. Failures leave
    the column null and return None — callers should fall back to raw text.

    Persists via `db.flush()` so the value is visible to subsequent queries
    in the same session, but commit/rollback responsibility stays with the
    caller's outer transaction boundary.
    """
    if job.parsed_jd_json is not None:
        return job.parsed_jd_json

    structure = await extract_jd_structure(job.description_md or "")
    if structure is None:
        return None

    job.parsed_jd_json = structure
    await db.flush()
    return structure
