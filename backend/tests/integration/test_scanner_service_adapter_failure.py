"""Scanner service completes even when one adapter fails."""

import json
import re
from pathlib import Path
from uuid import UUID

import pytest
import respx
from httpx import Response
from sqlalchemy import select

from hireloop.core.scanner.service import ScannerService
from hireloop.db import get_session_factory
from hireloop.models.scan_config import ScanConfig
from hireloop.models.scan_run import ScanRun
from hireloop.models.user import User
from tests.conftest import FAKE_CLAIMS
from tests.fixtures.fake_gemini import fake_gemini

_GH = json.loads(
    (
        Path(__file__).parent.parent / "fixtures" / "boards" / "greenhouse" / "stripe.json"
    ).read_text()
)


async def _user_id() -> UUID:
    factory = get_session_factory()
    async with factory() as s:
        r = await s.execute(select(User).where(User.cognito_sub == FAKE_CLAIMS["sub"]))
        return r.scalar_one().id


@pytest.mark.asyncio
@respx.mock
async def test_scan_completes_when_one_adapter_fails(seed_profile) -> None:
    """Greenhouse works; Ashby returns 500 on every attempt; scan still finishes."""
    respx.get("https://boards-api.greenhouse.io/v1/boards/stripe/jobs?content=true").mock(
        return_value=Response(200, json=_GH)
    )
    respx.get(re.compile(r"https://api\.ashbyhq\.com/posting-api/job-board/linear.*")).mock(
        return_value=Response(500, text="boom")
    )

    uid = await _user_id()
    factory = get_session_factory()
    async with factory() as session:
        config = ScanConfig(
            user_id=uid,
            name="Half-broken",
            companies=[
                {"name": "Stripe", "platform": "greenhouse", "board_slug": "stripe"},
                {"name": "Linear", "platform": "ashby", "board_slug": "linear"},
            ],
            schedule="manual",
            is_active=True,
        )
        session.add(config)
        await session.flush()
        run = ScanRun(user_id=uid, scan_config_id=config.id, status="pending")
        session.add(run)
        await session.commit()
        run_id = run.id

    with fake_gemini({"Staff": "0.6", "Senior": "0.55"}):
        async with factory() as session:
            outcome = await ScannerService(session).run_scan(run_id)
            await session.commit()

    # Greenhouse returned 2 listings; one-adapter-fail doesn't kill the run
    assert outcome.jobs_found >= 2
    async with factory() as session:
        reloaded = (await session.execute(select(ScanRun).where(ScanRun.id == run_id))).scalar_one()
        assert reloaded.status == "completed"
