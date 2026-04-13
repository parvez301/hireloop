import json
import re
from pathlib import Path

import pytest
import respx
from httpx import Response

from hireloop.core.scanner.adapters.base import BoardAdapterError
from hireloop.core.scanner.adapters.lever import LeverAdapter

_FIXTURE = (
    Path(__file__).parent.parent / "fixtures" / "boards" / "lever" / "shopify.json"
)


@pytest.mark.asyncio
@respx.mock
async def test_lever_adapter_fetches_and_normalizes() -> None:
    payload = json.loads(_FIXTURE.read_text())
    respx.get(re.compile(r"https://api\.lever\.co/v0/postings/shopify.*")).mock(
        return_value=Response(200, json=payload)
    )
    adapter = LeverAdapter()
    listings = await adapter.fetch_listings("shopify")

    assert len(listings) == 2
    first = listings[0]
    assert first.title == "Staff Engineer, Platform"
    assert first.company == "shopify"
    assert first.location == "Remote - Canada"
    assert first.employment_type == "full_time"
    assert first.seniority == "staff"
    assert "Shopify" in first.description_md


@pytest.mark.asyncio
@respx.mock
async def test_lever_adapter_handles_empty_array() -> None:
    respx.get(re.compile(r"https://api\.lever\.co/v0/postings/empty.*")).mock(
        return_value=Response(200, json=[])
    )
    adapter = LeverAdapter()
    listings = await adapter.fetch_listings("empty")
    assert listings == []


@pytest.mark.asyncio
@respx.mock
async def test_lever_adapter_raises_on_500() -> None:
    respx.get(re.compile(r"https://api\.lever\.co/v0/postings/broken.*")).mock(
        return_value=Response(500, text="server error")
    )
    adapter = LeverAdapter()
    with pytest.raises(BoardAdapterError):
        await adapter.fetch_listings("broken")
