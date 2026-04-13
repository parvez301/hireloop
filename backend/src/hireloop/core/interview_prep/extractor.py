"""Extract STAR stories from a master resume using Claude (cached prompts)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from hireloop.config import get_settings
from hireloop.core.llm.anthropic_client import CompletionUsage, complete_with_cache
from hireloop.schemas.star_story import StarStoryCreate


@dataclass
class StarExtractionResult:
    stories: list[StarStoryCreate]
    model: str
    usage: CompletionUsage


_SYSTEM = """You are an expert career coach. Extract STAR stories from the resume below.

For each distinct achievement or project, produce one STAR object with:
- title: short label (max 255 chars)
- situation: context
- task: what had to be done
- action: what the candidate did (use first person)
- result: measurable outcome if possible
- reflection: optional one-line lesson
- tags: optional list of short strings (skills, domains)

Return ONLY valid JSON: {"stories": [ ... ]} with no markdown fences."""

_JSON_FENCE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)


def _parse_stories_json(text: str) -> list[dict[str, Any]]:
    raw = text.strip()
    m = _JSON_FENCE.search(raw)
    if m:
        raw = m.group(1).strip()
    data = json.loads(raw)
    if not isinstance(data, dict) or "stories" not in data:
        raise ValueError("Expected JSON object with 'stories' array")
    stories = data["stories"]
    if not isinstance(stories, list):
        raise ValueError("'stories' must be an array")
    return [s for s in stories if isinstance(s, dict)]


async def extract_star_stories_from_resume(master_resume_md: str) -> StarExtractionResult:
    """Call Claude with cached system + resume; return validated STAR drafts + usage."""
    settings = get_settings()
    user_block = f"RESUME:\n{master_resume_md}\n\nReturn JSON only."

    result = await complete_with_cache(
        system=_SYSTEM,
        cacheable_blocks=[master_resume_md],
        user_block=user_block,
        model=settings.claude_model,
        max_tokens=4096,
        temperature=0.2,
        timeout_s=settings.llm_evaluation_timeout_s,
    )

    raw_list = _parse_stories_json(result.text)
    out: list[StarStoryCreate] = []
    for item in raw_list:
        try:
            out.append(StarStoryCreate.model_validate(item))
        except Exception:
            continue
    return StarExtractionResult(stories=out, model=result.model, usage=result.usage)
