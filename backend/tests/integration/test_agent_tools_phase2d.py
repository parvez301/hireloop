"""Agent tools: interview prep (full) and negotiation (offer gate)."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from hireloop.core.agent.tools import (
    ToolRuntime,
    build_interview_prep_tool,
    generate_negotiation_playbook_tool,
)
from hireloop.db import get_session_factory
from hireloop.models.user import User
from tests.conftest import FAKE_CLAIMS
from tests.fixtures.fake_anthropic import fake_anthropic
from tests.integration._phase2d_fakes import anthropic_responses_interview_prep_flow


async def _primary_user_id():
    factory = get_session_factory()
    async with factory() as session:
        r = await session.execute(select(User).where(User.cognito_sub == FAKE_CLAIMS["sub"]))
        return r.scalar_one().id


@pytest.mark.asyncio
async def test_build_interview_prep_tool_returns_card(seed_profile, seeded_evaluation_for_user_a):
    from sqlalchemy import delete

    from hireloop.models.interview_prep import InterviewPrep
    from hireloop.models.star_story import StarStory

    uid = await _primary_user_id()
    factory = get_session_factory()
    async with factory() as session:
        await session.execute(delete(StarStory).where(StarStory.user_id == uid))
        await session.execute(delete(InterviewPrep).where(InterviewPrep.user_id == uid))
        await session.commit()

    with fake_anthropic(anthropic_responses_interview_prep_flow()):
        async with factory() as session:
            rt = ToolRuntime(user_id=uid, session=session)
            result = await build_interview_prep_tool(
                rt, job_id=str(seeded_evaluation_for_user_a.job_id), custom_role=None
            )
            await session.commit()

    assert result["ok"] is True
    assert result["card"]["type"] == "interview_prep"
    assert result["card"]["data"]["interview_prep_id"]


@pytest.mark.asyncio
async def test_generate_negotiation_playbook_tool_requires_offer_form():
    uid = await _primary_user_id()
    factory = get_session_factory()
    async with factory() as session:
        rt = ToolRuntime(user_id=uid, session=session)
        result = await generate_negotiation_playbook_tool(
            rt, job_id="00000000-0000-0000-0000-000000000001"
        )

    assert result["ok"] is False
    assert result["error_code"] == "OFFER_DETAILS_REQUIRED"
    assert result.get("offer_form_job_id")
