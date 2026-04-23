import json
from pathlib import Path

import pytest
import respx
from httpx import Response

from hireloop.core.scanner.adapters.base import BoardAdapterError
from hireloop.core.scanner.adapters.greenhouse import GreenhouseAdapter

_FIXTURE = Path(__file__).parent.parent / "fixtures" / "boards" / "greenhouse" / "stripe.json"


@pytest.mark.asyncio
@respx.mock
async def test_greenhouse_adapter_fetches_and_normalizes() -> None:
    payload = json.loads(_FIXTURE.read_text())
    respx.get("https://boards-api.greenhouse.io/v1/boards/stripe/jobs?content=true").mock(
        return_value=Response(200, json=payload)
    )
    adapter = GreenhouseAdapter()
    listings = await adapter.fetch_listings("stripe")

    assert len(listings) >= 1
    first = listings[0]
    assert first.title
    assert first.company == "stripe"
    # Description should be rendered markdown, not raw HTML
    assert "<h3>" not in first.description_md


@pytest.mark.asyncio
@respx.mock
async def test_greenhouse_adapter_raises_on_500() -> None:
    respx.get("https://boards-api.greenhouse.io/v1/boards/unknown/jobs?content=true").mock(
        return_value=Response(500, text="server error")
    )
    adapter = GreenhouseAdapter()
    with pytest.raises(BoardAdapterError) as exc:
        await adapter.fetch_listings("unknown")
    assert exc.value.platform == "greenhouse"
    assert exc.value.slug == "unknown"


@pytest.mark.asyncio
@respx.mock
async def test_greenhouse_adapter_returns_empty_on_empty_board() -> None:
    respx.get("https://boards-api.greenhouse.io/v1/boards/empty/jobs?content=true").mock(
        return_value=Response(200, json={"jobs": []})
    )
    adapter = GreenhouseAdapter()
    listings = await adapter.fetch_listings("empty")
    assert listings == []
