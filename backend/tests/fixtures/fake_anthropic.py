"""Fake Anthropic client for tests — monkey-patches the real client."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any
from unittest.mock import patch


@dataclass
class FakeUsage:
    input_tokens: int = 100
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0
    output_tokens: int = 50


@dataclass
class FakeContentBlock:
    type: str = "text"
    text: str = ""


@dataclass
class FakeMessage:
    content: list[FakeContentBlock] = field(default_factory=list)
    usage: FakeUsage = field(default_factory=FakeUsage)
    model: str = "claude-sonnet-4-6"
    stop_reason: str = "end_turn"


class FakeAnthropicClient:
    def __init__(self, responses: dict[str, str]):
        self._responses = responses
        self.calls: list[dict[str, Any]] = []

    async def messages_create(self, **kwargs: Any) -> FakeMessage:
        self.calls.append(kwargs)
        messages = kwargs.get("messages", [])
        last_user = ""
        for m in messages:
            if m.get("role") == "user":
                content = m.get("content", "")
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            last_user += block.get("text", "")
                else:
                    last_user += str(content)

        reply = "FAKE DEFAULT RESPONSE"
        for substr, response_text in self._responses.items():
            if substr in last_user:
                reply = response_text
                break

        return FakeMessage(content=[FakeContentBlock(type="text", text=reply)])


class _Messages:
    def __init__(self, inner: FakeAnthropicClient):
        self._inner = inner

    async def create(self, **kwargs: Any) -> FakeMessage:
        return await self._inner.messages_create(**kwargs)


class _Wrapper:
    def __init__(self, inner: FakeAnthropicClient):
        self._inner = inner

    @property
    def messages(self) -> _Messages:
        return _Messages(self._inner)


@contextmanager
def fake_anthropic(responses: dict[str, str]) -> Iterator[FakeAnthropicClient]:
    fake = FakeAnthropicClient(responses)
    wrapper = _Wrapper(fake)

    # Patch the internal `_get_client` — it's the function every code path
    # reaches through (get_client / get_batch_client / complete_with_cache
    # all route here). Patching only `get_client` misses complete_with_cache
    # which is how evaluation / CV / interview-prep / batch paths call Claude.
    # Also patch the lru_cache'd singleton so subsequent calls don't bypass us.
    with (
        patch(
            "hireloop.core.llm.anthropic_client._get_client",
            return_value=wrapper,
        ),
        patch(
            "hireloop.core.llm.anthropic_client.get_client",
            return_value=wrapper,
        ),
        patch(
            "hireloop.core.llm.anthropic_client.get_batch_client",
            return_value=wrapper,
        ),
    ):
        yield fake
