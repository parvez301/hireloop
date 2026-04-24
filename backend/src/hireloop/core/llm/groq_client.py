"""Async Groq client (OpenAI-compatible REST).

Groq exposes /openai/v1/chat/completions, so we hit it with httpx directly to
avoid pulling in the openai SDK as a dep. Public surface mirrors fast_client:
`complete_text` for free-form output, `complete_json` for structured extraction.
"""

from __future__ import annotations

import json
import re
from typing import Any

import httpx

from hireloop.config import get_settings
from hireloop.core.llm.errors import LLMError, LLMParseError, LLMQuotaError, LLMTimeoutError

_PROVIDER_NAME = "groq"


def _client(timeout_s: float) -> httpx.AsyncClient:
    settings = get_settings()
    return httpx.AsyncClient(
        base_url=settings.groq_base_url,
        headers={
            "Authorization": f"Bearer {settings.groq_api_key or 'dummy-for-tests'}",
            "Content-Type": "application/json",
        },
        timeout=timeout_s,
    )


def _build_payload(
    *,
    model: str,
    system: str | None,
    user: str,
    max_tokens: int,
    temperature: float,
    response_json: bool,
) -> dict[str, Any]:
    messages: list[dict[str, str]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": user})
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    if response_json:
        payload["response_format"] = {"type": "json_object"}
    return payload


async def _post(payload: dict[str, Any], timeout_s: float) -> dict[str, Any]:
    try:
        async with _client(timeout_s) as client:
            response = await client.post("/chat/completions", json=payload)
    except httpx.TimeoutException as exc:
        raise LLMTimeoutError(f"Groq call exceeded {timeout_s}s", provider=_PROVIDER_NAME) from exc
    except httpx.HTTPError as exc:
        raise LLMError(f"Groq transport error: {exc}", provider=_PROVIDER_NAME) from exc

    if response.status_code == 429:
        raise LLMQuotaError("Groq rate limit", provider=_PROVIDER_NAME)
    if response.status_code >= 400:
        raise LLMError(
            f"Groq HTTP {response.status_code}: {response.text[:300]}",
            provider=_PROVIDER_NAME,
        )

    try:
        body: dict[str, Any] = response.json()
    except ValueError as exc:
        raise LLMParseError("Groq returned non-JSON body", provider=_PROVIDER_NAME) from exc
    return body


def _extract_text(body: dict[str, Any]) -> str:
    choices = body.get("choices") or []
    if not choices:
        raise LLMParseError("Groq response had no choices", provider=_PROVIDER_NAME)
    message = choices[0].get("message") or {}
    text = message.get("content") or ""
    if not text:
        raise LLMParseError("Groq response was empty", provider=_PROVIDER_NAME)
    return text


async def complete_text(
    *,
    user: str,
    system: str | None = None,
    model: str | None = None,
    max_tokens: int = 1024,
    temperature: float = 0.2,
    timeout_s: float = 15.0,
) -> str:
    settings = get_settings()
    payload = _build_payload(
        model=model or settings.groq_model,
        system=system,
        user=user,
        max_tokens=max_tokens,
        temperature=temperature,
        response_json=False,
    )
    body = await _post(payload, timeout_s)
    return _extract_text(body)


async def complete_json(
    *,
    user: str,
    system: str | None = None,
    model: str | None = None,
    max_tokens: int = 2048,
    temperature: float = 0.0,
    timeout_s: float = 15.0,
) -> dict[str, Any]:
    settings = get_settings()
    payload = _build_payload(
        model=model or settings.groq_model,
        system=system
        or (
            "You are a structured-extraction service. "
            "Reply with exactly one JSON object and no prose."
        ),
        user=user,
        max_tokens=max_tokens,
        temperature=temperature,
        response_json=True,
    )
    body = await _post(payload, timeout_s)
    raw = _extract_text(body).strip()
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.MULTILINE)
    try:
        parsed: dict[str, Any] = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise LLMParseError(
            "Groq response was not valid JSON",
            provider=_PROVIDER_NAME,
            details={"raw": raw[:500]},
        ) from exc
    return parsed
