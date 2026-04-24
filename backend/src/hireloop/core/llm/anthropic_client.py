"""Thin async wrapper around anthropic.AsyncAnthropic with prompt caching."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Literal

import anthropic
from anthropic import AsyncAnthropic

from hireloop.config import get_settings
from hireloop.core.llm.errors import LLMError, LLMParseError, LLMQuotaError, LLMTimeoutError

# "realtime" — interactive chat / agent graph. MUST hit api.anthropic.com for
# streaming latency; never routed through llm-bridge.
# "batch" — async generators (interview prep, negotiation, CV optimizer, L2
# evaluation). Routed through llm-bridge when ANTHROPIC_BASE_URL is set, else
# falls back to api.anthropic.com transparently.
CallRoute = Literal["realtime", "batch"]


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


@lru_cache(maxsize=2)
def _get_client(route: CallRoute) -> AsyncAnthropic:
    settings = get_settings()
    kwargs: dict[str, Any] = {
        "api_key": settings.anthropic_api_key or "dummy-for-tests",
    }
    if route == "batch" and settings.anthropic_base_url:
        kwargs["base_url"] = settings.anthropic_base_url
        if settings.anthropic_bridge_secret:
            kwargs["default_headers"] = {"x-bridge-secret": settings.anthropic_bridge_secret}
    return AsyncAnthropic(**kwargs)


def get_client() -> AsyncAnthropic:
    """Realtime client. Always hits api.anthropic.com — used by chat/agent graph."""
    return _get_client("realtime")


def get_batch_client() -> AsyncAnthropic:
    """Batch client. Routes through llm-bridge when ANTHROPIC_BASE_URL is set."""
    return _get_client("batch")


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
    route: CallRoute = "realtime",
) -> CompletionResult:
    """Call Claude with prompt caching enabled on the cacheable blocks.

    `route` selects the client pool — "realtime" always uses api.anthropic.com
    (required for chat streaming latency), "batch" uses llm-bridge when
    configured and falls back to the real API otherwise.
    """
    settings = get_settings()
    client = _get_client(route)
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


async def complete_with_cache_with_fallback(
    *,
    system: str,
    cacheable_blocks: list[str],
    user_block: str,
    model: str,
    max_tokens: int,
    temperature: float = 0.2,
    tools: list[dict[str, Any]] | None = None,
    timeout_s: float = 60.0,
    primary_route: CallRoute = "batch",
    fallback_route: CallRoute = "realtime",
) -> CompletionResult:
    """Try `primary_route` first; on LLMError fall through to `fallback_route`.

    Designed for the L2 batch eval path: prefer the bridge (Claude Max savings)
    when it's healthy, but never let bridge instability block evaluation. The
    fallback only triggers on LLMError (timeout / quota / API error / parse).
    Programming errors propagate as-is.

    Same-route retry is not attempted — if the primary path raises a transient
    upstream error the bridge would have served cached, the fallback covers it.
    """
    if primary_route == fallback_route:
        return await complete_with_cache(
            system=system,
            cacheable_blocks=cacheable_blocks,
            user_block=user_block,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            tools=tools,
            timeout_s=timeout_s,
            route=primary_route,
        )

    import logging

    logger = logging.getLogger(__name__)
    try:
        return await complete_with_cache(
            system=system,
            cacheable_blocks=cacheable_blocks,
            user_block=user_block,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            tools=tools,
            timeout_s=timeout_s,
            route=primary_route,
        )
    except LLMError as exc:
        logger.warning(
            "anthropic primary route %s failed (%s); falling back to %s",
            primary_route,
            exc,
            fallback_route,
        )
        return await complete_with_cache(
            system=system,
            cacheable_blocks=cacheable_blocks,
            user_block=user_block,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            tools=tools,
            timeout_s=timeout_s,
            route=fallback_route,
        )
