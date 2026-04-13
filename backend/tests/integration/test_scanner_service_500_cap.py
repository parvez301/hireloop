"""Scanner truncates at the 500-listing hard cap."""

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


def _fake_greenhouse_with_n_listings(n: int) -> dict:
    jobs = []
    for i in range(n):
        jobs.append(
            {
                "id": 1000 + i,
                "title": f"Job {i}",
                "absolute_url": f"https://boards.greenhouse.io/huge/jobs/{i}",
                "location": {"name": "Remote"},
                "content": f"<p>Unique description for job {i}</p>",
                "metadata": [],
                "offices": [],
            }
        )
    return {"jobs": jobs}


async def _user_id() -> UUID:
    factory = get_session_factory()
    async with factory() as s:
        r = await s.execute(select(User).where(User.cognito_sub == FAKE_CLAIMS["sub"]))
        return r.scalar_one().id


@pytest.mark.asyncio
@respx.mock
async def test_scan_truncates_at_500(seed_profile) -> None:
    respx.get(
        "https://boards-api.greenhouse.io/v1/boards/huge/jobs?content=true"
    ).mock(return_value=Response(200, json=_fake_greenhouse_with_n_listings(600)))

    uid = await _user_id()
    factory = get_session_factory()
    async with factory() as session:
        config = ScanConfig(
            user_id=uid,
            name="Huge",
            companies=[
                {"name": "Huge", "platform": "greenhouse", "board_slug": "huge"}
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

    with fake_gemini({"Job": "0.5"}):
        async with factory() as session:
            outcome = await ScannerService(session).run_scan(run_id)
            await session.commit()

    assert outcome.truncated is True
    assert outcome.jobs_found == 500
