"""Layer-6 output validator + auto-rewrite.

Per PERSONALISATION_STRATEGY.md lines 360-409, every personalised generator
output should pass through three checks before reaching the user:

1. Banned-phrase scan (uses the same `BANNED_PHRASES` constant the system
   prompt forbids — anything that slipped past Layer 5 enforcement gets
   caught here).
2. Company-name presence — output must reference the JD's company by name.
3. CV-fact specificity — output must mention at least 2 specific facts from
   the candidate's CV (companies, notable numbers).

Failures trigger an auto-rewrite via Sonnet (QUALITY tier per the routing
matrix), then re-validate. The audit row records both attempts so prompt
authors can see which generators misbehave most.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from hireloop.config import get_settings
from hireloop.core.llm.anthropic_client import complete_with_cache
from hireloop.core.llm.errors import LLMError
from hireloop.core.llm.personalisation import BANNED_PHRASES, with_personalisation
from hireloop.core.llm.tier import Task
from hireloop.models.personalisation_audit import PersonalisationAudit

logger = logging.getLogger(__name__)


_MIN_CV_FACTS_REQUIRED = 2


@dataclass
class ValidationReport:
    passed: bool
    generic_phrases_found: list[str] = field(default_factory=list)
    mentions_company: bool = True
    specific_cv_facts_referenced: int = 0


def _collect_cv_facts(cv_structure: dict[str, Any] | None) -> list[str]:
    """Pull discrete, specific strings from the CV structure for fact-counting.

    Currently uses role companies + notable_numbers per the spec. Each is
    something a generic output won't mention but a personalised one should.
    """
    if not cv_structure:
        return []
    facts: list[str] = []
    roles = cv_structure.get("roles") or []
    for role in roles:
        if isinstance(role, dict):
            company = role.get("company")
            if isinstance(company, str) and company.strip():
                facts.append(company.strip())
    numbers = cv_structure.get("notable_numbers") or []
    for number in numbers:
        if isinstance(number, str) and number.strip():
            facts.append(number.strip())
    return facts


def validate(
    output: str,
    cv_structure: dict[str, Any] | None,
    jd_structure: dict[str, Any] | None,
) -> ValidationReport:
    """Run the three Layer-6 checks. Pure function — no side effects."""
    lower_output = output.lower()

    violations = [phrase for phrase in BANNED_PHRASES if phrase in lower_output]

    company = ""
    if jd_structure:
        company_value = jd_structure.get("company")
        if isinstance(company_value, str):
            company = company_value.strip()
    mentions_company = (company.lower() in lower_output) if company else True

    cv_facts = _collect_cv_facts(cv_structure)
    fact_hits = sum(1 for fact in cv_facts if fact.lower() in lower_output)

    passed = not violations and mentions_company and fact_hits >= _MIN_CV_FACTS_REQUIRED
    return ValidationReport(
        passed=passed,
        generic_phrases_found=violations,
        mentions_company=mentions_company,
        specific_cv_facts_referenced=fact_hits,
    )


def _rewrite_prompt(
    output: str,
    report: ValidationReport,
    cv_structure: dict[str, Any] | None,
    jd_structure: dict[str, Any] | None,
) -> str:
    bullets: list[str] = []
    if report.generic_phrases_found:
        joined = ", ".join(f'"{p}"' for p in report.generic_phrases_found)
        bullets.append(f"Remove banned generic phrases: {joined}")
    if not report.mentions_company:
        company = ""
        if jd_structure:
            company_value = jd_structure.get("company")
            if isinstance(company_value, str):
                company = company_value.strip()
        if company:
            bullets.append(f"Reference {company} by name explicitly")
    if report.specific_cv_facts_referenced < _MIN_CV_FACTS_REQUIRED:
        bullets.append(
            f"Quote at least {_MIN_CV_FACTS_REQUIRED} specific facts from the candidate's "
            "CV (company names, achievements with numbers)"
        )

    instructions = "\n- " + "\n- ".join(bullets) if bullets else ""
    cv_block = f"\n\nCV STRUCTURE (for reference):\n{cv_structure}" if cv_structure else ""
    jd_block = f"\n\nJD STRUCTURE (for reference):\n{jd_structure}" if jd_structure else ""

    return (
        "Rewrite the following output to fix specific personalisation failures."
        f"{instructions}\n\nORIGINAL OUTPUT:\n{output}{cv_block}{jd_block}\n\n"
        "Return ONLY the rewritten output, no preamble or explanation."
    )


async def rewrite_for_specificity(
    output: str,
    report: ValidationReport,
    cv_structure: dict[str, Any] | None,
    jd_structure: dict[str, Any] | None,
    *,
    timeout_s: float = 45.0,
) -> str | None:
    """Ask Sonnet to rewrite an output that failed validation.

    Returns the rewritten string on success, None on LLM failure (caller
    keeps the original output rather than crashing).
    """
    settings = get_settings()
    system = with_personalisation(
        "You are a precise personalisation rewriter. Replace generic language "
        "with specific facts from the candidate's CV and the target JD."
    )
    try:
        result = await complete_with_cache(
            system=system,
            cacheable_blocks=[],
            user_block=_rewrite_prompt(output, report, cv_structure, jd_structure),
            model=settings.claude_model,
            max_tokens=2048,
            temperature=0.2,
            timeout_s=timeout_s,
            route="realtime",
        )
    except LLMError as exc:
        logger.warning("personalisation rewrite failed: %s", exc)
        return None
    except Exception as exc:  # noqa: BLE001 — best-effort path
        logger.exception("personalisation rewrite crashed: %s", exc)
        return None
    return result.text.strip() or None


@dataclass
class ValidationOutcome:
    output: str
    final_report: ValidationReport
    rewrite_attempted: bool
    rewrite_succeeded: bool


async def validate_and_persist(
    db: AsyncSession,
    *,
    output: str,
    cv_structure: dict[str, Any] | None,
    jd_structure: dict[str, Any] | None,
    task: Task,
    user_id: UUID | None = None,
    auto_rewrite: bool = True,
) -> ValidationOutcome:
    """End-to-end: validate, rewrite-on-fail, persist audit row, return outcome.

    The audit row reflects the FINAL state — if a rewrite succeeded, `passed`
    captures the post-rewrite verdict. `rewrite_attempted`/`rewrite_succeeded`
    let analytics distinguish "passed first time" from "saved by rewrite".
    """
    initial = validate(output, cv_structure, jd_structure)

    final_output = output
    final_report = initial
    rewrite_attempted = False
    rewrite_succeeded = False

    if not initial.passed and auto_rewrite:
        rewrite_attempted = True
        rewritten = await rewrite_for_specificity(output, initial, cv_structure, jd_structure)
        if rewritten:
            final_output = rewritten
            final_report = validate(rewritten, cv_structure, jd_structure)
            rewrite_succeeded = final_report.passed

    audit = PersonalisationAudit(
        user_id=user_id,
        task=task.value,
        passed=final_report.passed,
        generic_phrases_found=final_report.generic_phrases_found,
        mentions_company=final_report.mentions_company,
        specific_cv_facts_referenced=final_report.specific_cv_facts_referenced,
        rewrite_attempted=rewrite_attempted,
        rewrite_succeeded=rewrite_succeeded,
    )
    db.add(audit)
    await db.flush()

    return ValidationOutcome(
        output=final_output,
        final_report=final_report,
        rewrite_attempted=rewrite_attempted,
        rewrite_succeeded=rewrite_succeeded,
    )
