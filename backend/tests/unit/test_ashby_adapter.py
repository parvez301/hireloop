import json
import re
from pathlib import Path

import pytest
import respx
from httpx import Response

from hireloop.core.scanner.adapters.ashby import AshbyAdapter
from hireloop.core.scanner.adapters.base import BoardAdapterError

_FIXTURE = Path(__file__).parent.parent / "fixtures" / "boards" / "ashby" / "linear.json"


@pytest.mark.asyncio
@respx.mock
async def test_ashby_adapter_fetches_and_normalizes() -> None:
    payload = json.loads(_FIXTURE.read_text())
    respx.get(re.compile(r"https://api\.ashbyhq\.com/posting-api/job-board/linear.*")).mock(
        return_value=Response(200, json=payload)
    )
    adapter = AshbyAdapter()
    listings = await adapter.fetch_listings("linear")

    assert len(listings) == 2
    first = listings[0]
    assert first.title == "Senior Backend Engineer"
    assert first.company == "linear"
    assert first.location == "Remote (Americas)"
    assert first.employment_type == "full_time"
    # Compensation tier was "$180K – $240K"
    assert first.salary_min == 180000
    assert first.salary_max == 240000
    assert "Linear" in first.description_md


@pytest.mark.asyncio
@respx.mock
async def test_ashby_adapter_handles_missing_compensation() -> None:
    payload = json.loads(_FIXTURE.read_text())
    respx.get(re.compile(r"https://api\.ashbyhq\.com/posting-api/job-board/linear.*")).mock(
        return_value=Response(200, json=payload)
    )
    adapter = AshbyAdapter()
    listings = await adapter.fetch_listings("linear")
    # second job has no compensation block
    assert listings[1].salary_min is None
    assert listings[1].salary_max is None


@pytest.mark.asyncio
@respx.mock
async def test_ashby_adapter_raises_on_500() -> None:
    respx.get(re.compile(r"https://api\.ashbyhq\.com/posting-api/job-board/broken.*")).mock(
        return_value=Response(500, text="boom")
    )
    adapter = AshbyAdapter()
    with pytest.raises(BoardAdapterError):
        await adapter.fetch_listings("broken")
