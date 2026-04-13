"""Normalized LLM error taxonomy."""

from typing import Any


class LLMError(Exception):
    """Base class for all LLM-related errors."""

    def __init__(
        self,
        message: str,
        *,
        provider: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.provider = provider
        self.details: dict[str, Any] = details or {}


class LLMTimeoutError(LLMError):
    """The provider did not respond before the timeout."""


class LLMQuotaError(LLMError):
    """The provider returned a quota/rate-limit error (HTTP 429)."""


class LLMParseError(LLMError):
    """The provider responded but the response could not be parsed."""
