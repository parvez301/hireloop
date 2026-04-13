"""End-to-end ScannerService run against all 3 adapters with mocked HTTP."""

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
from hireloop.models.scan_run import ScanResult, ScanRun
from hireloop.models.user import User
from tests.conftest import FAKE_CLAIMS
from tests.fixtures.fake_gemini import fake_gemini

_GH = json.loads(
    (
        Path(__file__).parent.parent / "fixtures" / "boards" / "greenhouse" / "stripe.json"
    ).read_text()
)
_ASHBY = json.loads(
    (Path(__file__).parent.parent / "fixtures" / "boards" / "ashby" / "linear.json").read_text()
)
_LEVER = json.loads(
    (
        Path(__file__).parent.parent / "fixtures" / "boards" / "lever" / "shopify.json"
    ).read_text()
)


async def _get_user_id() -> UUID:
    factory = get_session_factory()
    async with factory() as session:
        r = await session.execute(select(User).where(User.cognito_sub == FAKE_CLAIMS["sub"]))
        user = r.scalar_one_or_none()
        if user is None:
            user = User(
                cognito_sub=FAKE_CLAIMS["sub"],
                email=FAKE_CLAIMS["email"],
                name="Test",
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
        return user.id


@pytest.mark.asyncio
@respx.mock
async def test_scanner_service_happy_path_all_three_platforms(seed_profile) -> None:
    respx.get(
        "https://boards-api.greenhouse.io/v1/boards/stripe/jobs?content=true"
    ).mock(return_value=Response(200, json=_GH))
    respx.get(
        re.compile(r"https://api\.ashbyhq\.com/posting-api/job-board/linear.*")
    ).mock(return_value=Response(200, json=_ASHBY))
    respx.get(re.compile(r"https://api\.lever\.co/v0/postings/shopify.*")).mock(
        return_value=Response(200, json=_LEVER)
    )

    user_id = await _get_user_id()
    factory = get_session_factory()
    async with factory() as session:
        config = ScanConfig(
            user_id=user_id,
            name="3-platform test",
            companies=[
                {"name": "Stripe", "platform": "greenhouse", "board_slug": "stripe"},
                {"name": "Linear", "platform": "ashby", "board_slug": "linear"},
                {"name": "Shopify", "platform": "lever", "board_slug": "shopify"},
            ],
            schedule="manual",
            is_active=True,
        )
        session.add(config)
        await session.flush()
        run = ScanRun(user_id=user_id, scan_config_id=config.id, status="pending")
        session.add(run)
        await session.commit()
        run_id = run.id

    with fake_gemini({"Staff": "0.85", "Senior": "0.75"}):
        async with factory() as session:
            service = ScannerService(session)
            outcome = await service.run_scan(run_id)
            await session.commit()

    # 2 greenhouse + 2 ashby + 2 lever = 6
    assert outcome.jobs_found >= 4
    assert outcome.truncated is False

    async with factory() as session:
        reloaded = (
            await session.execute(select(ScanRun).where(ScanRun.id == run_id))
        ).scalar_one()
        assert reloaded.status == "completed"
        results = (
            (
                await session.execute(
                    select(ScanResult).where(ScanResult.scan_run_id == run_id)
                )
            )
            .scalars()
            .all()
        )
        assert len(results) >= 4
