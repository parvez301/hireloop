from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any
from unittest.mock import patch


@dataclass
class _FakeResponse:
    text: str


class FakeGeminiModel:
    def __init__(self, responses: dict[str, str]):
        self._responses = responses
        self.calls: list[str] = []

    async def generate_content_async(self, prompt: str, **kwargs: Any) -> _FakeResponse:
        self.calls.append(prompt)
        for substr, out in self._responses.items():
            if substr in prompt:
                return _FakeResponse(text=out)
        return _FakeResponse(text="CAREER_GENERAL")


@contextmanager
def fake_gemini(responses: dict[str, str]) -> Iterator[FakeGeminiModel]:
    fake = FakeGeminiModel(responses)
    with patch(
        "hireloop.core.llm.gemini_client._get_model",
        return_value=fake,
    ):
        yield fake
