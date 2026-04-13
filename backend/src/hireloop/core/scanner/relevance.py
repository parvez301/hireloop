"""L1 relevance scorer — Gemini Flash, one call per job."""

from __future__ import annotations

import asyncio
import re
from typing import Any

from hireloop.core.llm import gemini_client
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


async def score_relevance(
    *,
    job: Job,
    profile_summary: dict[str, Any],
    timeout_s: float = 5.0,
) -> float:
    """Return a 0.0–1.0 relevance score. 0.0 on any error."""
    prompt = _build_prompt(job, profile_summary)
    model = gemini_client._get_model()
    try:
        response = await asyncio.wait_for(
            model.generate_content_async(prompt),
            timeout=timeout_s,
        )
    except Exception:
        return 0.0

    raw = getattr(response, "text", "") or ""
    match = re.search(r"-?\d+(?:\.\d+)?", raw)
    if not match:
        return 0.0
    try:
        value = float(match.group(0))
    except ValueError:
        return 0.0
    return max(0.0, min(1.0, value))
