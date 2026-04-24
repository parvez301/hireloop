"""Tests for the Anthropic Batches API helpers (Phase 7d)."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import anthropic
import pytest

from hireloop.core.llm.anthropic_batch_client import (
    BatchItemResult,
    BatchRequest,
    iter_results,
    retrieve_status,
    submit_batch,
    wait_and_collect,
)
from hireloop.core.llm.errors import LLMError, LLMTimeoutError


def _fake_client_with_batches(batches_obj: object) -> MagicMock:
    """Build a mock matching `_get_client(route).messages.batches.<x>` shape."""
    client = MagicMock()
    client.messages.batches = batches_obj
    return client


def _ok_batch(id_: str = "batch_test", status: str = "in_progress") -> Any:
    batch = MagicMock()
    batch.id = id_
    batch.processing_status = status
    return batch


@pytest.mark.asyncio
async def test_submit_batch_returns_id() -> None:
    batches = MagicMock()
    batches.create = AsyncMock(return_value=_ok_batch("batch_abc"))
    with patch(
        "hireloop.core.llm.anthropic_batch_client._get_client",
        return_value=_fake_client_with_batches(batches),
    ):
        batch_id = await submit_batch(
            [
                BatchRequest(
                    custom_id="r1",
                    params={"model": "claude-sonnet-4-6", "max_tokens": 100, "messages": []},
                )
            ]
        )
    assert batch_id == "batch_abc"
    sent = batches.create.await_args.kwargs["requests"]
    assert sent[0]["custom_id"] == "r1"
    assert sent[0]["params"]["model"] == "claude-sonnet-4-6"


@pytest.mark.asyncio
async def test_submit_batch_with_no_requests_raises() -> None:
    batches = MagicMock()
    with patch(
        "hireloop.core.llm.anthropic_batch_client._get_client",
        return_value=_fake_client_with_batches(batches),
    ):
        with pytest.raises(LLMError):
            await submit_batch([])


@pytest.mark.asyncio
async def test_submit_batch_maps_anthropic_error_to_llm_error() -> None:
    batches = MagicMock()
    batches.create = AsyncMock(
        side_effect=anthropic.APIError(
            "boom", request=MagicMock(), body={"error": {"message": "boom"}}
        )
    )
    with patch(
        "hireloop.core.llm.anthropic_batch_client._get_client",
        return_value=_fake_client_with_batches(batches),
    ):
        with pytest.raises(LLMError):
            await submit_batch(
                [
                    BatchRequest(
                        custom_id="x", params={"model": "m", "max_tokens": 1, "messages": []}
                    )
                ]
            )


@pytest.mark.asyncio
async def test_retrieve_status_returns_processing_status() -> None:
    batches = MagicMock()
    batches.retrieve = AsyncMock(return_value=_ok_batch("b1", status="ended"))
    with patch(
        "hireloop.core.llm.anthropic_batch_client._get_client",
        return_value=_fake_client_with_batches(batches),
    ):
        status = await retrieve_status("b1")
    assert status == "ended"


def _make_succeeded_entry(custom_id: str, text: str) -> Any:
    """Mimic the SDK's batch result entry shape (succeeded)."""
    block = MagicMock()
    block.type = "text"
    block.text = text
    usage = MagicMock(
        input_tokens=10,
        cache_creation_input_tokens=0,
        cache_read_input_tokens=0,
        output_tokens=20,
    )
    message = MagicMock(content=[block], usage=usage, model="claude-sonnet-4-6")
    result = MagicMock()
    result.type = "succeeded"
    result.message = message
    entry = MagicMock()
    entry.custom_id = custom_id
    entry.result = result
    return entry


def _make_errored_entry(custom_id: str, message: str) -> Any:
    error = MagicMock()
    error.message = message
    result = MagicMock()
    result.type = "errored"
    result.error = error
    result.message = None
    entry = MagicMock()
    entry.custom_id = custom_id
    entry.result = result
    return entry


@pytest.mark.asyncio
async def test_iter_results_yields_per_item_outcomes() -> None:
    entries = [
        _make_succeeded_entry("r1", "ok one"),
        _make_errored_entry("r2", "rate limited"),
        _make_succeeded_entry("r3", "ok three"),
    ]

    async def _stream() -> Any:
        for e in entries:
            yield e

    batches = MagicMock()
    batches.results = AsyncMock(return_value=_stream())
    with patch(
        "hireloop.core.llm.anthropic_batch_client._get_client",
        return_value=_fake_client_with_batches(batches),
    ):
        collected: list[BatchItemResult] = []
        async for item in iter_results("b1"):
            collected.append(item)

    assert len(collected) == 3
    assert collected[0].success is True
    assert collected[0].text == "ok one"
    assert collected[0].usage is not None
    assert collected[0].usage.output_tokens == 20
    assert collected[1].success is False
    assert collected[1].error == "rate limited"
    assert collected[2].text == "ok three"


@pytest.mark.asyncio
async def test_wait_and_collect_polls_then_returns_dict() -> None:
    """submit → poll (in_progress, ended) → fetch results → dict."""
    entries = [_make_succeeded_entry("r1", "result one"), _make_succeeded_entry("r2", "result two")]

    async def _stream() -> Any:
        for e in entries:
            yield e

    statuses = iter(["in_progress", "ended"])

    def _retrieve(_: str) -> Any:
        return _ok_batch("b1", status=next(statuses))

    batches = MagicMock()
    batches.create = AsyncMock(return_value=_ok_batch("b1"))
    batches.retrieve = AsyncMock(side_effect=_retrieve)
    batches.results = AsyncMock(return_value=_stream())

    sleep_mock = AsyncMock()
    with (
        patch(
            "hireloop.core.llm.anthropic_batch_client._get_client",
            return_value=_fake_client_with_batches(batches),
        ),
        patch("hireloop.core.llm.anthropic_batch_client.asyncio.sleep", new=sleep_mock),
    ):
        out = await wait_and_collect(
            [
                BatchRequest(
                    custom_id="r1", params={"model": "m", "max_tokens": 1, "messages": []}
                ),
                BatchRequest(
                    custom_id="r2", params={"model": "m", "max_tokens": 1, "messages": []}
                ),
            ],
            poll_interval_s=0.0,
        )

    assert set(out.keys()) == {"r1", "r2"}
    assert out["r1"].text == "result one"
    assert out["r2"].text == "result two"
    assert sleep_mock.await_count == 1  # one in_progress → ended transition


@pytest.mark.asyncio
async def test_wait_and_collect_times_out_when_never_ends() -> None:
    batches = MagicMock()
    batches.create = AsyncMock(return_value=_ok_batch("b1"))
    batches.retrieve = AsyncMock(return_value=_ok_batch("b1", status="in_progress"))

    sleep_mock = AsyncMock()
    with (
        patch(
            "hireloop.core.llm.anthropic_batch_client._get_client",
            return_value=_fake_client_with_batches(batches),
        ),
        patch("hireloop.core.llm.anthropic_batch_client.asyncio.sleep", new=sleep_mock),
    ):
        with pytest.raises(LLMTimeoutError):
            await wait_and_collect(
                [
                    BatchRequest(
                        custom_id="r1", params={"model": "m", "max_tokens": 1, "messages": []}
                    )
                ],
                poll_interval_s=0.0,
                timeout_s=0.0,
            )
