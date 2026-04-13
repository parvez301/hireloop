"""InterviewPrepGenerator — Claude call to generate interview questions.

Uses parent spec Appendix D.6 prompt. Supports two modes:
1. Job-tied: `job_markdown` provided → questions tailored to the specific role
2. Custom role: `custom_role` provided → generic prep for that role description

Exactly one of the two must be set.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from hireloop.config import get_settings
from hireloop.core.llm.anthropic_client import complete_with_cache
from hireloop.core.llm.errors import LLMParseError

_CACHEABLE_INSTRUCTIONS = """You are an interview prep coach. Given a candidate's resume and a
target role,
generate interview questions and red-flag questions for the candidate to ask.

OUTPUT STRUCTURE:
1. 10 likely interview questions with suggested answer frameworks, each linked
   to a STAR story from the existing story bank when possible
2. 5 "red flag" questions the candidate should ask the interviewer to evaluate
   the company (with what to listen for)

QUESTION CATEGORIES (use all 4):
- behavioral — "Tell me about a time..."
- technical — role-specific technical knowledge
- situational — "How would you handle..."
- culture — values, motivation, fit

RULES:
- Each question should be specific to the role and seniority
- Suggested story title MUST reference an actual story from the provided bank, not invent one
- If no suitable story exists, set suggested_story_title to null
- Frameworks are 1-2 sentence hints, not full answers
- Red-flag questions should probe concrete concerns: team health, technical debt,
  hiring funnel, runway, management practices

OUTPUT JSON SCHEMA:
{
  "questions": [
    {
      "question": "...",
      "category": "behavioral" | "technical" | "situational" | "culture",
      "suggested_story_title": "string from story bank OR null",
      "framework": "1-2 sentence answer framework"
    }
  ],
  "red_flag_questions": [
    {
      "question": "...",
      "what_to_listen_for": "..."
    }
  ]
}

No prose outside JSON."""

_SYSTEM = "You are an interview prep coach. Output only strict JSON matching the schema."


@dataclass
class GeneratedInterviewPrep:
    questions: list[dict[str, Any]]
    red_flag_questions: list[dict[str, Any]]
    usage: Any
    model: str


async def generate_interview_prep(
    *,
    existing_stories_summary: str,
    job_markdown: str | None,
    custom_role: str | None,
    resume_md: str,
    feedback: str | None = None,
) -> GeneratedInterviewPrep:
    """Generate interview prep. Exactly one of job_markdown / custom_role must be set."""
    if bool(job_markdown) == bool(custom_role):
        raise ValueError("Exactly one of job_markdown or custom_role must be set")

    settings = get_settings()
    role_block = (
        f"TARGET JOB:\n{job_markdown}" if job_markdown else f"TARGET ROLE (custom):\n{custom_role}"
    )
    feedback_block = f"\n\nUSER FEEDBACK FROM PRIOR ATTEMPT:\n{feedback}" if feedback else ""
    user_block = (
        f"CANDIDATE RESUME:\n{resume_md}\n\n"
        f"{role_block}\n\n"
        f"EXISTING STORY BANK (reference these in suggested_story_title, do not duplicate):\n"
        f"{existing_stories_summary}{feedback_block}\n\n"
        "Generate interview prep per the schema. Output JSON only."
    )

    result = await complete_with_cache(
        system=_SYSTEM,
        cacheable_blocks=[_CACHEABLE_INSTRUCTIONS],
        user_block=user_block,
        model=settings.claude_model,
        max_tokens=3000,
        timeout_s=settings.llm_evaluation_timeout_s,
    )

    parsed = _parse(result.text)
    return GeneratedInterviewPrep(
        questions=list(parsed.get("questions", [])),
        red_flag_questions=list(parsed.get("red_flag_questions", [])),
        usage=result.usage,
        model=result.model,
    )


def _parse(text: str) -> dict[str, Any]:
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.MULTILINE)
    try:
        data: dict[str, Any] = json.loads(raw)
    except json.JSONDecodeError as e:
        raise LLMParseError(
            "Interview prep generator returned invalid JSON",
            provider="anthropic",
            details={"raw": raw[:500]},
        ) from e
    if "questions" not in data:
        raise LLMParseError(
            "Missing 'questions' field in generator response",
            provider="anthropic",
        )
    return data
