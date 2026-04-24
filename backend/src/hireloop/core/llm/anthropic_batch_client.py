"""Anthropic Batches API helpers (50% off Sonnet for background work).

Submit-and-poll wrapper around `client.messages.batches.create / retrieve /
results`. Use for asynchronous L2 evaluation, scheduled report generation, or
any other workload where end-to-end latency in the minutes-to-hours range is
acceptable.

Surface:
- `BatchRequest` — input dataclass (custom_id + Messages params)
- `BatchItemResult` — output dataclass (success/error/text/usage per request)
- `submit_batch(requests)` — fire-and-forget, returns batch id
- `retrieve_status(batch_id)` — current processing_status
- `iter_results(batch_id)` — async iterator over per-request outcomes
- `wait_and_collect(requests, ...)` — submit + poll + collect into dict[str, BatchItemResult]

Routes through the same `AsyncAnthropic` clients as the streaming path:
`route="realtime"` always hits api.anthropic.com; `route="batch"` honours
`ANTHROPIC_BASE_URL` (llm-bridge) when set. The bridge does not currently
proxy batch endpoints, so batch callers should generally pin `route="realtime"`.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator, Iterable
from dataclasses import dataclass
from typing import Any

import anthropic

from hireloop.core.llm.anthropic_client import CallRoute, CompletionUsage, _get_client
from hireloop.core.llm.errors import LLMError, LLMTimeoutError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BatchRequest:
    """One request in a batch.

    `params` is the body of `client.messages.create(**params)`: model,
    max_tokens, system, messages, tools, etc. `custom_id` is echoed back on
    each result so callers can reassociate.
    """

    custom_id: str
    params: dict[str, Any]


@dataclass(frozen=True)
class BatchItemResult:
    custom_id: str
    success: bool
    text: str | None
    error: str | None
    usage: CompletionUsage | None
    model: str | None


def _to_create_request(req: BatchRequest) -> dict[str, Any]:
    return {"custom_id": req.custom_id, "params": req.params}


async def submit_batch(requests: Iterable[BatchRequest], *, route: CallRoute = "realtime") -> str:
    """Submit a batch. Returns the batch id."""
    client = _get_client(route)
    payload = [_to_create_request(r) for r in requests]
    if not payload:
        raise LLMError("submit_batch called with no requests", provider="anthropic")
    try:
        # SDK types `requests` as Iterable[Request] (typed dict). Our payload
        # is the same shape but typed as dict[str, Any] so we can build it
        # generically — silence mypy here.
        batch = await client.messages.batches.create(requests=payload)  # type: ignore[arg-type]
    except anthropic.APIError as exc:
        raise LLMError(f"Batch submit failed: {exc}", provider="anthropic") from exc
    return batch.id


async def retrieve_status(batch_id: str, *, route: CallRoute = "realtime") -> str:
    """Return the current processing_status (in_progress | ended | canceling | ...)."""
    client = _get_client(route)
    try:
        batch = await client.messages.batches.retrieve(batch_id)
    except anthropic.APIError as exc:
        raise LLMError(f"Batch retrieve failed: {exc}", provider="anthropic") from exc
    return str(batch.processing_status)


def _block_text(blocks: list[Any]) -> str:
    return "".join(getattr(b, "text", "") for b in blocks if getattr(b, "type", "") == "text")


def _to_item_result(entry: Any) -> BatchItemResult:
    custom_id = getattr(entry, "custom_id", "") or ""
    result = getattr(entry, "result", None)
    result_type = getattr(result, "type", None) if result is not None else None
    if result_type == "succeeded":
        message = getattr(result, "message", None)
        text = _block_text(getattr(message, "content", []) or []) if message else ""
        usage_obj = getattr(message, "usage", None) if message else None
        usage = (
            CompletionUsage(
                input_tokens=getattr(usage_obj, "input_tokens", 0) or 0,
                cache_creation_input_tokens=getattr(usage_obj, "cache_creation_input_tokens", 0)
                or 0,
                cache_read_input_tokens=getattr(usage_obj, "cache_read_input_tokens", 0) or 0,
                output_tokens=getattr(usage_obj, "output_tokens", 0) or 0,
            )
            if usage_obj is not None
            else None
        )
        return BatchItemResult(
            custom_id=custom_id,
            success=True,
            text=text,
            error=None,
            usage=usage,
            model=getattr(message, "model", None) if message else None,
        )

    error = getattr(result, "error", None) if result is not None else None
    error_message = getattr(error, "message", None) if error is not None else None
    if error_message is None and result_type:
        error_message = result_type
    return BatchItemResult(
        custom_id=custom_id,
        success=False,
        text=None,
        error=error_message or "unknown_error",
        usage=None,
        model=None,
    )


async def iter_results(
    batch_id: str, *, route: CallRoute = "realtime"
) -> AsyncIterator[BatchItemResult]:
    client = _get_client(route)
    try:
        stream = await client.messages.batches.results(batch_id)
    except anthropic.APIError as exc:
        raise LLMError(f"Batch results fetch failed: {exc}", provider="anthropic") from exc
    async for entry in stream:
        yield _to_item_result(entry)


async def wait_and_collect(
    requests: Iterable[BatchRequest],
    *,
    poll_interval_s: float = 10.0,
    timeout_s: float = 3600.0,
    route: CallRoute = "realtime",
) -> dict[str, BatchItemResult]:
    """Submit a batch, poll until done, return {custom_id: BatchItemResult}.

    Raises LLMTimeoutError if the batch hasn't entered an `ended` state within
    `timeout_s`. Default 1 hour matches Anthropic's typical completion window
    for small-to-medium batches; raise for larger workloads.
    """
    batch_id = await submit_batch(requests, route=route)
    logger.info("batch submitted: %s", batch_id)

    deadline = asyncio.get_event_loop().time() + timeout_s
    while True:
        status = await retrieve_status(batch_id, route=route)
        if status == "ended":
            break
        if asyncio.get_event_loop().time() >= deadline:
            raise LLMTimeoutError(
                f"Batch {batch_id} did not finish within {timeout_s}s",
                provider="anthropic",
            )
        await asyncio.sleep(poll_interval_s)

    out: dict[str, BatchItemResult] = {}
    async for item in iter_results(batch_id, route=route):
        out[item.custom_id] = item
    return out
