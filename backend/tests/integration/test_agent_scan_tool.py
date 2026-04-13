from unittest.mock import patch

import pytest
from sqlalchemy import select

from hireloop.core.agent.tools import ToolRuntime, start_job_scan_tool
from hireloop.core.scanner.default_config import DEFAULT_COMPANIES, DEFAULT_SCAN_CONFIG_NAME
from hireloop.db import get_session_factory
from hireloop.models.scan_config import ScanConfig
from hireloop.models.user import User
from tests.conftest import FAKE_CLAIMS


class _FakeClient:
    def __init__(self) -> None:
        self.sent: list = []

    async def send(self, event):  # noqa: ANN001
        self.sent.append(event)
        return ["evt_tool_1"]


@pytest.mark.asyncio
async def test_start_job_scan_tool_uses_default_config():
    factory = get_session_factory()
    async with factory() as session:
        user = (
            await session.execute(select(User).where(User.cognito_sub == FAKE_CLAIMS["sub"]))
        ).scalar_one()
        cfg = (
            await session.execute(
                select(ScanConfig).where(
                    ScanConfig.user_id == user.id,
                    ScanConfig.name == DEFAULT_SCAN_CONFIG_NAME,
                )
            )
        ).scalar_one_or_none()
        if cfg is None:
            cfg = ScanConfig(
                user_id=user.id,
                name=DEFAULT_SCAN_CONFIG_NAME,
                companies=list(DEFAULT_COMPANIES),
                schedule="manual",
                is_active=True,
            )
            session.add(cfg)
            await session.commit()
        uid = user.id

    fake = _FakeClient()
    async with factory() as session:
        with patch("hireloop.inngest.client.get_inngest_client", return_value=fake):
            runtime = ToolRuntime(user_id=uid, session=session)
            result = await start_job_scan_tool(runtime)
            await session.commit()

    assert result["ok"] is True
    assert result["card"]["type"] == "scan_progress"
    assert result["card"]["data"]["companies_count"] == len(DEFAULT_COMPANIES)
    assert len(fake.sent) == 1
