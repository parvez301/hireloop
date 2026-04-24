"""Tests for complete_with_cache_with_fallback + scorer/batch threading.

The spec: backend (L2) evaluation runs on the Claude Max bridge first; if the
bridge returns an LLMError (timeout, quota, API error, parse), fall through to
direct api.anthropic.com. User-facing paths default to direct with no fallback.
"""

from __future__ import annotations

import inspect
from unittest.mock import AsyncMock, patch

import pytest

from hireloop.core.llm.anthropic_client import (
    CompletionResult,
    CompletionUsage,
    complete_with_cache_with_fallback,
)
from hireloop.core.llm.errors import LLMError, LLMQuotaError


def _ok_result(text: str = "ok") -> CompletionResult:
    return CompletionResult(
        text=text,
        usage=CompletionUsage(
            input_tokens=10,
            cache_creation_input_tokens=0,
            cache_read_input_tokens=0,
            output_tokens=10,
        ),
        model="claude-sonnet-4-6",
        stop_reason="end_turn",
    )


@pytest.mark.asyncio
async def test_primary_success_does_not_invoke_fallback() -> None:
    primary_result = _ok_result("primary")

    async def _fake(**kwargs: object) -> CompletionResult:
        assert kwargs["route"] == "batch"
        return primary_result

    fake = AsyncMock(side_effect=_fake)
    with patch("hireloop.core.llm.anthropic_client.complete_with_cache", new=fake):
        out = await complete_with_cache_with_fallback(
            system="s",
            cacheable_blocks=["c"],
            user_block="u",
            model="claude-sonnet-4-6",
            max_tokens=100,
            primary_route="batch",
            fallback_route="realtime",
        )
    assert out.text == "primary"
    assert fake.await_count == 1


@pytest.mark.asyncio
async def test_primary_llm_error_triggers_fallback() -> None:
    primary = LLMError("bridge down", provider="anthropic")
    success = _ok_result("fallback")

    calls: list[str] = []

    async def _fake(**kwargs: object) -> CompletionResult:
        route = kwargs["route"]
        calls.append(str(route))
        if route == "batch":
            raise primary
        return success

    with patch(
        "hireloop.core.llm.anthropic_client.complete_with_cache", new=AsyncMock(side_effect=_fake)
    ):
        out = await complete_with_cache_with_fallback(
            system="s",
            cacheable_blocks=["c"],
            user_block="u",
            model="claude-sonnet-4-6",
            max_tokens=100,
            primary_route="batch",
            fallback_route="realtime",
        )
    assert out.text == "fallback"
    assert calls == ["batch", "realtime"]


@pytest.mark.asyncio
async def test_primary_quota_error_also_triggers_fallback() -> None:
    """LLMQuotaError subclasses LLMError — bridge quota exhaustion must fall over."""

    calls: list[str] = []

    async def _fake(**kwargs: object) -> CompletionResult:
        calls.append(str(kwargs["route"]))
        if kwargs["route"] == "batch":
            raise LLMQuotaError("bridge rate limit", provider="anthropic")
        return _ok_result("direct")

    with patch(
        "hireloop.core.llm.anthropic_client.complete_with_cache", new=AsyncMock(side_effect=_fake)
    ):
        out = await complete_with_cache_with_fallback(
            system="s",
            cacheable_blocks=["c"],
            user_block="u",
            model="claude-sonnet-4-6",
            max_tokens=100,
            primary_route="batch",
            fallback_route="realtime",
        )
    assert out.text == "direct"
    assert calls == ["batch", "realtime"]


@pytest.mark.asyncio
async def test_non_llm_error_does_not_trigger_fallback() -> None:
    """Programming errors (e.g. ValueError) must propagate, not silently fall through."""

    async def _fake(**kwargs: object) -> CompletionResult:
        raise ValueError("coding bug")

    with (
        patch(
            "hireloop.core.llm.anthropic_client.complete_with_cache",
            new=AsyncMock(side_effect=_fake),
        ),
        pytest.raises(ValueError),
    ):
        await complete_with_cache_with_fallback(
            system="s",
            cacheable_blocks=["c"],
            user_block="u",
            model="claude-sonnet-4-6",
            max_tokens=100,
            primary_route="batch",
            fallback_route="realtime",
        )


@pytest.mark.asyncio
async def test_identical_routes_skip_fallback_wrapper() -> None:
    """No fallback when primary == fallback — avoid a duplicate call on failure."""
    calls: list[str] = []

    async def _fake(**kwargs: object) -> CompletionResult:
        calls.append(str(kwargs["route"]))
        raise LLMError("down", provider="anthropic")

    with (
        patch(
            "hireloop.core.llm.anthropic_client.complete_with_cache",
            new=AsyncMock(side_effect=_fake),
        ),
        pytest.raises(LLMError),
    ):
        await complete_with_cache_with_fallback(
            system="s",
            cacheable_blocks=["c"],
            user_block="u",
            model="claude-sonnet-4-6",
            max_tokens=100,
            primary_route="realtime",
            fallback_route="realtime",
        )
    assert calls == ["realtime"]


# ---------------------------------------------------------------------------
# claude_scorer + evaluate_job_for_user thread the routing args through
# ---------------------------------------------------------------------------


def test_evaluate_job_for_user_defaults_to_bridge_with_direct_fallback() -> None:
    """Signature-level assertion — the batch entry point must default to the
    spec'd routing (bridge primary, realtime fallback) so callers don't have
    to remember to opt in.
    """
    from hireloop.core.batch.l2_evaluate import evaluate_job_for_user

    sig = inspect.signature(evaluate_job_for_user)
    assert sig.parameters["claude_route"].default == "batch"
    assert sig.parameters["claude_fallback_route"].default == "realtime"


def test_evaluation_context_default_is_direct_only() -> None:
    """User-facing evaluation keeps the pre-existing direct-realtime default."""
    from hireloop.core.evaluation.service import EvaluationContext

    sig = inspect.signature(EvaluationContext)
    assert sig.parameters["claude_route"].default == "realtime"
    assert sig.parameters["claude_fallback_route"].default is None
