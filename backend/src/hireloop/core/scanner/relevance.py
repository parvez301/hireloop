"""L1 relevance scorer — fast-tier LLM, one call per job.

Uses `fast_client` so the provider (Claude-haiku via bridge vs. Gemini) is
picked by `settings.fast_llm_provider`.
"""

from __future__ import annotations

import asyncio
import re
from typing import Any

import anthropic

from hireloop.config import get_settings
from hireloop.core.llm import gemini_client
from hireloop.core.llm.anthropic_client import get_batch_client
from hireloop.models.job import Job


def _build_prompt(job: Job, profile_summary: dict[str, Any]) -> str:
    """Parent spec Appendix D.5 — relevance scoring prompt."""
    return (
        "Score this job listing's relevance to the candidate profile. "
        "Output ONLY a number between 0.0 and 1.0.\n\n"
        "Scoring guide:\n"
        "- 0.9-1.0: Strong match (right seniority, right skills, right location)\n"
        "- 0.7-0.9: Good match with minor gaps\n"
        "- 0.5-0.7: Partial match\n"
        "- 0.3-0.5: Weak match\n"
        "- 0.0-0.3: Poor match or wrong role entirely\n\n"
        "CANDIDATE:\n"
        f"Target roles: {profile_summary.get('target_roles', [])}\n"
        f"Skills: {profile_summary.get('skills', [])}\n"
        f"Seniority: {profile_summary.get('seniority', 'unknown')}\n"
        f"Location prefs: {profile_summary.get('target_locations', [])}\n\n"
        "JOB:\n"
        f"Title: {job.title}\n"
        f"Company: {job.company or 'unknown'}\n"
        f"Location: {job.location or 'unknown'}\n"
        f"Snippet: {(job.description_md or '')[:500]}\n\n"
        "Relevance score (0.0-1.0):"
    )


async def _claude_score(prompt: str, timeout_s: float) -> str:
    settings = get_settings()
    client = get_batch_client()
    try:
        msg = await asyncio.wait_for(
            client.messages.create(
                model=settings.claude_haiku_model,
                max_tokens=8,
                temperature=0,
                system=(
                    "You are a numeric scorer. Output exactly one decimal between 0 and 1 "
                    "and nothing else."
                ),
                messages=[{"role": "user", "content": prompt}],
            ),
            timeout=timeout_s,
        )
    except (TimeoutError, asyncio.TimeoutError):
        return ""
    except anthropic.APIError:
        return ""
    return "".join(
        block.text for block in msg.content if getattr(block, "type", "") == "text"
    )


async def _gemini_score(prompt: str, timeout_s: float) -> str:
    model = gemini_client._get_model()
    try:
        response = await asyncio.wait_for(
            model.generate_content_async(prompt),
            timeout=timeout_s,
        )
    except Exception:
        return ""
    return getattr(response, "text", "") or ""


async def score_relevance(
    *,
    job: Job,
    profile_summary: dict[str, Any],
    timeout_s: float = 5.0,
) -> float:
    """Return a 0.0–1.0 relevance score. 0.0 on any error."""
    prompt = _build_prompt(job, profile_summary)
    provider = get_settings().fast_llm_provider.lower()
    raw = (
        await _gemini_score(prompt, timeout_s)
        if provider == "gemini"
        else await _claude_score(prompt, timeout_s)
    )
    match = re.search(r"-?\d+(?:\.\d+)?", raw)
    if not match:
        return 0.0
    try:
        value = float(match.group(0))
    except ValueError:
        return 0.0
    return max(0.0, min(1.0, value))
