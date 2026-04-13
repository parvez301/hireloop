"""Score the 6 reasoning dimensions with Claude Sonnet + prompt caching."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from hireloop.config import get_settings
from hireloop.core.llm.anthropic_client import CompletionResult, complete_with_cache
from hireloop.core.llm.errors import LLMParseError

_FRAMEWORK = """You are an expert job evaluator for HireLoop. You score jobs against a candidate
profile across 6 reasoning dimensions. 4 other dimensions are pre-scored by rules
and provided as context.

SCORING DIMENSIONS (you score these 6):
1. Domain Relevance (weight 0.15) — Does past industry map to this company's domain?
2. Role Responsibility Match (weight 0.15) — Do past responsibilities align with JD duties?
3. Career Trajectory Fit (weight 0.10) — Lateral/promotion/step-back? Good for user's goals?
4. Culture & Values Signal (weight 0.08) — JD tone/values match user's preferences?
5. Red Flag Detection (weight 0.10) — Unrealistic reqs, vague duties, burnout language, etc.
6. Growth Potential (weight 0.07) — Room to learn and advance?

FOR EACH DIMENSION, OUTPUT:
- score: float 0.0 to 1.0
- grade: letter (A/A-/B+/B/B-/C+/C/D/F)
- reasoning: 1-2 sentences, specific, cite evidence from JD and profile
- signals: array of 2-4 specific evidence strings

RED FLAGS TO WATCH FOR:
- "Rockstar/Ninja" terminology (culture smell)
- "Fast-paced" + "wear many hats" (burnout)
- Senior title with junior responsibilities (title inflation)
- No salary posted + "competitive" language
- Unrealistic experience requirements (e.g., 10 years React)
- Equity-heavy with low base
- Vague job description
- Outdated tech stack + "innovative" claims

OUTPUT FORMAT: Valid JSON matching the schema in the final message. No prose outside JSON."""

_SYSTEM = "You are a precise, JSON-emitting career evaluator. Never include prose outside JSON."


@dataclass
class ClaudeScoringResult:
    dimensions: dict[str, dict[str, Any]]
    overall_reasoning: str
    red_flag_items: list[str]
    personalization_notes: str | None
    usage: Any
    model: str


class ClaudeScorer:
    async def score(
        self,
        *,
        job_markdown: str,
        profile_summary: dict[str, Any],
        rule_results_text: str,
    ) -> ClaudeScoringResult:
        settings = get_settings()
        user_block = self._build_user_block(job_markdown, profile_summary, rule_results_text)

        result = await complete_with_cache(
            system=_SYSTEM,
            cacheable_blocks=[_FRAMEWORK],
            user_block=user_block,
            model=settings.claude_model,
            max_tokens=2000,
            timeout_s=settings.llm_evaluation_timeout_s,
        )
        parsed = self._parse(result)
        return ClaudeScoringResult(
            dimensions=parsed["dimensions"],
            overall_reasoning=parsed.get("overall_reasoning", ""),
            red_flag_items=list(parsed.get("red_flag_items", [])),
            personalization_notes=parsed.get("personalization_notes"),
            usage=result.usage,
            model=result.model,
        )

    @staticmethod
    def _build_user_block(
        job_markdown: str,
        profile_summary: dict[str, Any],
        rule_results_text: str,
    ) -> str:
        return (
            "USER PROFILE:\n"
            f"{json.dumps(profile_summary, indent=2)}\n\n"
            "JOB DESCRIPTION:\n"
            f"{job_markdown}\n\n"
            "RULE-BASED DIMENSION RESULTS:\n"
            f"{rule_results_text}\n\n"
            "Evaluate the 6 reasoning dimensions. Output JSON matching this schema:\n"
            "{\n"
            '  "dimensions": {\n'
            '    "domain_relevance": { "score": 0.0, "grade": "X", "reasoning": "...", "signals": [] },\n'
            '    "role_match": { ... },\n'
            '    "trajectory_fit": { ... },\n'
            '    "culture_signal": { ... },\n'
            '    "red_flags": { ... },\n'
            '    "growth_potential": { ... }\n'
            "  },\n"
            '  "overall_reasoning": "2-3 sentence summary of why this is a fit or not",\n'
            '  "red_flag_items": ["specific flag 1", "specific flag 2"],\n'
            '  "personalization_notes": "1-2 sentences specific to this user\'s situation"\n'
            "}"
        )

    @staticmethod
    def _parse(result: CompletionResult) -> dict[str, Any]:
        raw = result.text.strip()
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.MULTILINE)
        try:
            data: dict[str, Any] = json.loads(raw)
        except json.JSONDecodeError as e:
            raise LLMParseError(
                "Claude scorer returned invalid JSON",
                provider="anthropic",
                details={"raw": raw[:500]},
            ) from e

        if "dimensions" not in data:
            raise LLMParseError("Missing 'dimensions' field in scorer response")
        return data
