"""Fast-tier LLM dispatcher.

Exposes `classify_intent()` and `extract_json()` — used for the L0 classifier,
structured-extraction in the job parser, and scanner relevance gating. Dispatches
on `settings.fast_llm_provider`:

- "claude"  → haiku via the Anthropic SDK (bridge-routed when configured).
- "gemini"  → legacy Google generativeai path (kept for fallback / cost comparison).

Public surface matches the old `gemini_client` module so callers don't need to
change when the provider flag flips.
"""

from __future__ import annotations

import asyncio
import json
import re
from typing import Any, Literal

import anthropic

from hireloop.config import get_settings
from hireloop.core.llm import gemini_client
from hireloop.core.llm.anthropic_client import get_batch_client
from hireloop.core.llm.errors import LLMError, LLMParseError, LLMTimeoutError

ClassifiedIntent = gemini_client.ClassifiedIntent
_VALID_INTENTS = gemini_client._VALID_INTENTS


async def classify_intent(message: str) -> ClassifiedIntent:
    provider = get_settings().fast_llm_provider.lower()
    if provider == "gemini":
        return await gemini_client.classify_intent(message)
    return await _claude_classify_intent(message)


async def extract_json(prompt: str, *, timeout_s: float = 8.0) -> dict[str, Any]:
    provider = get_settings().fast_llm_provider.lower()
    if provider == "gemini":
        return await gemini_client.extract_json(prompt, timeout_s=timeout_s)
    return await _claude_extract_json(prompt, timeout_s=timeout_s)


# ---------------------------------------------------------------------------
# Claude-haiku impls
# ---------------------------------------------------------------------------


def _claude_extract_text(msg: anthropic.types.Message) -> str:
    parts: list[str] = []
    for block in msg.content:
        if isinstance(block, anthropic.types.TextBlock):
            parts.append(block.text)
    return "".join(parts)


async def _claude_classify_intent(message: str) -> ClassifiedIntent:
    settings = get_settings()
    client = get_batch_client()
    prompt = gemini_client._build_classifier_prompt(message)
    try:
        msg = await asyncio.wait_for(
            client.messages.create(
                model=settings.claude_haiku_model,
                max_tokens=16,
                temperature=0,
                system=(
                    "You are a single-word classifier. Reply with exactly one of the "
                    "category tokens and nothing else."
                ),
                messages=[{"role": "user", "content": prompt}],
            ),
            timeout=settings.llm_classifier_timeout_s,
        )
    except TimeoutError:
        return "CAREER_GENERAL"
    except Exception:
        return "CAREER_GENERAL"

    raw = _claude_extract_text(msg).strip().upper()
    match = re.search(r"[A-Z_]+", raw)
    if not match:
        return "CAREER_GENERAL"
    token = match.group(0)
    if token not in _VALID_INTENTS:
        return "CAREER_GENERAL"
    return token  # type: ignore[return-value]


async def _claude_extract_json(prompt: str, *, timeout_s: float = 8.0) -> dict[str, Any]:
    settings = get_settings()
    client = get_batch_client()
    try:
        msg = await asyncio.wait_for(
            client.messages.create(
                model=settings.claude_haiku_model,
                max_tokens=2048,
                temperature=0,
                system=(
                    "You are a structured-extraction service. "
                    "Reply with exactly one JSON object and no prose."
                ),
                messages=[{"role": "user", "content": prompt}],
            ),
            timeout=timeout_s,
        )
    except TimeoutError as exc:
        raise LLMTimeoutError(f"Claude call exceeded {timeout_s}s", provider="anthropic") from exc
    except anthropic.APIError as exc:
        raise LLMError(f"Claude API error: {exc}", provider="anthropic") from exc

    raw = _claude_extract_text(msg).strip()
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.MULTILINE)
    try:
        parsed: dict[str, Any] = json.loads(raw)
        return parsed
    except json.JSONDecodeError as exc:
        raise LLMParseError(
            "Claude response was not valid JSON",
            provider="anthropic",
            details={"raw": raw[:500]},
        ) from exc


# Re-export provider metadata for usage-event logging.
def active_provider_model() -> tuple[Literal["claude", "gemini"], str]:
    settings = get_settings()
    provider = settings.fast_llm_provider.lower()
    if provider == "gemini":
        return "gemini", settings.gemini_model
    return "claude", settings.claude_haiku_model
