import hashlib
from unittest.mock import patch
from uuid import uuid4

import pytest
from sqlalchemy import select

from hireloop.core.agent.tools import ToolRuntime, start_batch_evaluation_tool
from hireloop.db import get_session_factory
from hireloop.models.job import Job
from hireloop.models.user import User
from tests.conftest import FAKE_CLAIMS


class _FakeClient:
    def __init__(self) -> None:
        self.sent: list = []

    async def send(self, event):  # noqa: ANN001
        self.sent.append(event)
        return ["evt_batch_tool_1"]


@pytest.mark.asyncio
async def test_start_batch_tool_with_job_ids(seed_profile):
    factory = get_session_factory()
    async with factory() as session:
        user = (
            await session.execute(select(User).where(User.cognito_sub == FAKE_CLAIMS["sub"]))
        ).scalar_one()
        h = hashlib.sha256(f"agent-batch-{uuid4()}".encode()).hexdigest()
        job = Job(
            content_hash=h,
            title="Test Job",
            description_md="x",
            requirements_json={},
            source="manual",
        )
        session.add(job)
        await session.commit()
        uid = user.id
        jid = job.id

    fake = _FakeClient()
    async with factory() as session:
        with patch("hireloop.inngest.client.get_inngest_client", return_value=fake):
            runtime = ToolRuntime(user_id=uid, session=session)
            result = await start_batch_evaluation_tool(runtime, job_ids=[str(jid)])
            await session.commit()

    assert result["ok"] is True
    assert result["card"]["type"] == "batch_progress"
    assert result["card"]["data"]["total"] == 1
    assert len(fake.sent) == 1


@pytest.mark.asyncio
async def test_start_batch_tool_rejects_multiple_inputs(seed_profile):
    factory = get_session_factory()
    async with factory() as session:
        user = (
            await session.execute(select(User).where(User.cognito_sub == FAKE_CLAIMS["sub"]))
        ).scalar_one()
        uid = user.id

    async with factory() as session:
        runtime = ToolRuntime(user_id=uid, session=session)
        result = await start_batch_evaluation_tool(
            runtime, job_ids=["abc"], job_urls=["https://x.com"]
        )
    assert result["ok"] is False
    assert result["error_code"] == "INVALID_BATCH_INPUT"
