"""Thin async wrapper around anthropic.AsyncAnthropic with prompt caching."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import anthropic
from anthropic import AsyncAnthropic

from hireloop.config import get_settings
from hireloop.core.llm.errors import LLMError, LLMParseError, LLMQuotaError, LLMTimeoutError


@dataclass
class CompletionUsage:
    input_tokens: int
    cache_creation_input_tokens: int
    cache_read_input_tokens: int
    output_tokens: int

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    def cost_cents(self, model: str) -> int:
        """Approximate cost in cents. Sonnet 4.6 ≈ $3/$15 per 1M in/out."""
        if "sonnet" in model.lower():
            in_c = self.input_tokens * 0.0003 / 10
            cache_read_c = self.cache_read_input_tokens * 0.00003 / 10
            out_c = self.output_tokens * 0.0015 / 10
            return max(1, round(in_c + cache_read_c + out_c))
        return max(1, round(self.total_tokens * 0.0005 / 10))


@dataclass
class CompletionResult:
    text: str
    usage: CompletionUsage
    model: str
    stop_reason: str


@lru_cache(maxsize=1)
def get_client() -> AsyncAnthropic:
    settings = get_settings()
    return AsyncAnthropic(api_key=settings.anthropic_api_key or "dummy-for-tests")


def _build_user_content(
    cacheable_blocks: list[str],
    user_block: str,
    enable_caching: bool,
) -> list[dict[str, Any]]:
    """Build the content array, attaching cache_control to the last cacheable block."""
    content: list[dict[str, Any]] = []
    for i, block in enumerate(cacheable_blocks):
        entry: dict[str, Any] = {"type": "text", "text": block}
        if enable_caching and i == len(cacheable_blocks) - 1:
            entry["cache_control"] = {"type": "ephemeral"}
        content.append(entry)
    content.append({"type": "text", "text": user_block})
    return content


async def complete_with_cache(
    *,
    system: str,
    cacheable_blocks: list[str],
    user_block: str,
    model: str,
    max_tokens: int,
    temperature: float = 0.2,
    tools: list[dict[str, Any]] | None = None,
    timeout_s: float = 60.0,
) -> CompletionResult:
    """Call Claude with prompt caching enabled on the cacheable blocks."""
    settings = get_settings()
    client = get_client()
    content = _build_user_content(cacheable_blocks, user_block, settings.enable_prompt_caching)

    create_kwargs: dict[str, Any] = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "system": system,
        "messages": [{"role": "user", "content": content}],
    }
    if tools is not None:
        create_kwargs["tools"] = tools

    try:
        msg = await asyncio.wait_for(
            client.messages.create(**create_kwargs),
            timeout=timeout_s,
        )
    except TimeoutError as e:
        raise LLMTimeoutError(f"Claude call exceeded {timeout_s}s", provider="anthropic") from e
    except anthropic.RateLimitError as e:
        raise LLMQuotaError("Claude rate limit", provider="anthropic") from e
    except anthropic.APIError as e:
        raise LLMError(f"Claude API error: {e}", provider="anthropic") from e

    text = "".join(block.text for block in msg.content if getattr(block, "type", "") == "text")
    if not text:
        raise LLMParseError("Claude returned no text content", provider="anthropic")

    usage = CompletionUsage(
        input_tokens=getattr(msg.usage, "input_tokens", 0) or 0,
        cache_creation_input_tokens=getattr(msg.usage, "cache_creation_input_tokens", 0) or 0,
        cache_read_input_tokens=getattr(msg.usage, "cache_read_input_tokens", 0) or 0,
        output_tokens=getattr(msg.usage, "output_tokens", 0) or 0,
    )
    return CompletionResult(
        text=text,
        usage=usage,
        model=getattr(msg, "model", model),
        stop_reason=getattr(msg, "stop_reason", "end_turn") or "end_turn",
    )
