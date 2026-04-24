"""Tests for the Groq client.

Uses respx to mock the OpenAI-compatible chat/completions endpoint. We assert
on request shape (model id, messages, response_format) and response parsing,
plus the LLMError taxonomy mapping (429 → quota, timeout → timeout, 5xx → error).
"""

from __future__ import annotations

import httpx
import pytest
import respx

from hireloop.config import get_settings
from hireloop.core.llm.errors import LLMError, LLMParseError, LLMQuotaError, LLMTimeoutError
from hireloop.core.llm.groq_client import complete_json, complete_text


def _ok_body(text: str) -> dict[str, object]:
    return {
        "id": "chatcmpl-test",
        "model": "llama-3.1-8b-instant",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": text},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 12, "completion_tokens": 8, "total_tokens": 20},
    }


@pytest.mark.asyncio
@respx.mock
async def test_complete_text_parses_assistant_content() -> None:
    settings = get_settings()
    route = respx.post(f"{settings.groq_base_url}/chat/completions").mock(
        return_value=httpx.Response(200, json=_ok_body("hello there"))
    )
    out = await complete_text(user="ping", system="You are pong.")
    assert out == "hello there"
    assert route.called
    sent = route.calls.last.request
    payload = sent.read().decode()
    assert "llama-3.1-8b-instant" in payload
    assert '"role":"system"' in payload
    assert '"role":"user"' in payload


@pytest.mark.asyncio
@respx.mock
async def test_complete_json_parses_object_and_sets_response_format() -> None:
    settings = get_settings()
    route = respx.post(f"{settings.groq_base_url}/chat/completions").mock(
        return_value=httpx.Response(200, json=_ok_body('{"intent": "EVALUATE_JOB"}'))
    )
    out = await complete_json(user="classify: evaluate this job please")
    assert out == {"intent": "EVALUATE_JOB"}
    payload = route.calls.last.request.read().decode()
    assert '"response_format":' in payload
    assert '"json_object"' in payload


@pytest.mark.asyncio
@respx.mock
async def test_complete_json_strips_markdown_fences() -> None:
    settings = get_settings()
    respx.post(f"{settings.groq_base_url}/chat/completions").mock(
        return_value=httpx.Response(200, json=_ok_body('```json\n{"score": "A"}\n```'))
    )
    out = await complete_json(user="score this candidate")
    assert out == {"score": "A"}


@pytest.mark.asyncio
@respx.mock
async def test_429_maps_to_quota_error() -> None:
    settings = get_settings()
    respx.post(f"{settings.groq_base_url}/chat/completions").mock(
        return_value=httpx.Response(429, json={"error": "rate_limited"})
    )
    with pytest.raises(LLMQuotaError):
        await complete_text(user="hi")


@pytest.mark.asyncio
@respx.mock
async def test_5xx_maps_to_generic_llm_error() -> None:
    settings = get_settings()
    respx.post(f"{settings.groq_base_url}/chat/completions").mock(
        return_value=httpx.Response(503, text="upstream down")
    )
    with pytest.raises(LLMError):
        await complete_text(user="hi")


@pytest.mark.asyncio
@respx.mock
async def test_timeout_maps_to_timeout_error() -> None:
    settings = get_settings()
    respx.post(f"{settings.groq_base_url}/chat/completions").mock(
        side_effect=httpx.TimeoutException("read timeout")
    )
    with pytest.raises(LLMTimeoutError):
        await complete_text(user="hi", timeout_s=0.01)


@pytest.mark.asyncio
@respx.mock
async def test_invalid_json_maps_to_parse_error() -> None:
    settings = get_settings()
    respx.post(f"{settings.groq_base_url}/chat/completions").mock(
        return_value=httpx.Response(200, json=_ok_body("not json at all"))
    )
    with pytest.raises(LLMParseError):
        await complete_json(user="extract")
