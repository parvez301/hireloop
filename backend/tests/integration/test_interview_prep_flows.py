"""Interview prep API: story bank extraction, job vs custom role, regenerate, paywall."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select

from hireloop.db import get_session_factory
from hireloop.main import app
from hireloop.models.interview_prep import InterviewPrep
from hireloop.models.star_story import StarStory
from hireloop.models.user import User
from tests.conftest import FAKE_CLAIMS
from tests.fixtures.fake_anthropic import fake_anthropic
from tests.integration._phase2d_fakes import anthropic_responses_interview_prep_flow


async def _user_id() -> UUID:
    factory = get_session_factory()
    async with factory() as session:
        r = await session.execute(select(User).where(User.cognito_sub == FAKE_CLAIMS["sub"]))
        return r.scalar_one().id


async def _clear_star_stories(user_id: UUID) -> None:
    factory = get_session_factory()
    async with factory() as session:
        await session.execute(delete(StarStory).where(StarStory.user_id == user_id))
        await session.execute(delete(InterviewPrep).where(InterviewPrep.user_id == user_id))
        await session.commit()


@pytest.mark.asyncio
async def test_interview_prep_auto_populates_story_bank(
    auth_headers, seed_profile, seeded_evaluation_for_user_a
):
    user_id = await _user_id()
    await _clear_star_stories(user_id)

    with (
        patch(
            "hireloop.integrations.cognito.CognitoJwtVerifier.verify",
            new=AsyncMock(return_value=FAKE_CLAIMS),
        ),
        fake_anthropic(anthropic_responses_interview_prep_flow()),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.post(
                "/api/v1/interview-preps",
                json={"job_id": str(seeded_evaluation_for_user_a.job_id)},
                headers=auth_headers,
            )
    assert r.status_code == 201
    data = r.json()["data"]
    assert len(data["questions"]) == 10
    assert data["red_flag_questions"] is not None
    assert len(data["red_flag_questions"]) == 5

    factory = get_session_factory()
    async with factory() as session:
        stories = (
            (await session.execute(select(StarStory).where(StarStory.user_id == user_id)))
            .scalars()
            .all()
        )
        assert len(stories) >= 1


@pytest.mark.asyncio
async def test_interview_prep_custom_role(auth_headers, seed_profile):
    user_id = await _user_id()
    await _clear_star_stories(user_id)

    with (
        patch(
            "hireloop.integrations.cognito.CognitoJwtVerifier.verify",
            new=AsyncMock(return_value=FAKE_CLAIMS),
        ),
        fake_anthropic(anthropic_responses_interview_prep_flow()),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.post(
                "/api/v1/interview-preps",
                json={"custom_role": "Staff Platform Engineer — Kubernetes & Go"},
                headers=auth_headers,
            )
    assert r.status_code == 201
    assert r.json()["data"]["custom_role"] is not None
    assert r.json()["data"]["job_id"] is None


@pytest.mark.asyncio
async def test_interview_prep_job_id_list_get(
    auth_headers, seed_profile, seeded_evaluation_for_user_a
):
    user_id = await _user_id()
    await _clear_star_stories(user_id)

    with (
        patch(
            "hireloop.integrations.cognito.CognitoJwtVerifier.verify",
            new=AsyncMock(return_value=FAKE_CLAIMS),
        ),
        fake_anthropic(anthropic_responses_interview_prep_flow()),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r_create = await client.post(
                "/api/v1/interview-preps",
                json={"job_id": str(seeded_evaluation_for_user_a.job_id)},
                headers=auth_headers,
            )
            prep_id = r_create.json()["data"]["id"]
            r_list = await client.get("/api/v1/interview-preps", headers=auth_headers)
            r_one = await client.get(f"/api/v1/interview-preps/{prep_id}", headers=auth_headers)

    assert r_list.status_code == 200
    ids = [x["id"] for x in r_list.json()["data"]]
    assert prep_id in ids
    assert r_one.status_code == 200
    assert r_one.json()["data"]["id"] == prep_id


@pytest.mark.asyncio
async def test_interview_prep_regenerate(auth_headers, seed_profile, seeded_evaluation_for_user_a):
    user_id = await _user_id()
    await _clear_star_stories(user_id)

    with (
        patch(
            "hireloop.integrations.cognito.CognitoJwtVerifier.verify",
            new=AsyncMock(return_value=FAKE_CLAIMS),
        ),
        fake_anthropic(anthropic_responses_interview_prep_flow()),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r0 = await client.post(
                "/api/v1/interview-preps",
                json={"job_id": str(seeded_evaluation_for_user_a.job_id)},
                headers=auth_headers,
            )
            prep_id = r0.json()["data"]["id"]
            r1 = await client.post(
                f"/api/v1/interview-preps/{prep_id}/regenerate",
                json={"feedback": "More system-design depth please"},
                headers=auth_headers,
            )
    assert r1.status_code == 201
    new_id = r1.json()["data"]["id"]
    assert new_id != prep_id


@pytest.mark.asyncio
async def test_interview_prep_paywalled_when_trial_expired(
    auth_headers, seed_profile, seeded_evaluation_for_user_a
):
    from datetime import UTC, datetime, timedelta

    from hireloop.models.subscription import Subscription

    user_id = await _user_id()
    await _clear_star_stories(user_id)

    factory = get_session_factory()
    async with factory() as session:
        sr = await session.execute(select(Subscription).where(Subscription.user_id == user_id))
        sub = sr.scalar_one_or_none()
        if sub is None:
            sub = Subscription(user_id=user_id, plan="trial", status="active")
            session.add(sub)
            await session.flush()
        sub.trial_ends_at = datetime.now(UTC) - timedelta(days=1)
        sub.stripe_subscription_id = None
        await session.commit()

    try:
        with (
            patch(
                "hireloop.integrations.cognito.CognitoJwtVerifier.verify",
                new=AsyncMock(return_value=FAKE_CLAIMS),
            ),
            fake_anthropic(anthropic_responses_interview_prep_flow()),
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                r = await client.post(
                    "/api/v1/interview-preps",
                    json={"job_id": str(seeded_evaluation_for_user_a.job_id)},
                    headers=auth_headers,
                )
        assert r.status_code == 403
        assert r.json()["error"]["code"] == "TRIAL_EXPIRED"
    finally:
        async with factory() as session:
            sr = await session.execute(select(Subscription).where(Subscription.user_id == user_id))
            sub = sr.scalar_one_or_none()
            if sub is not None:
                sub.trial_ends_at = datetime.now(UTC) + timedelta(days=30)
                await session.commit()


@pytest.mark.asyncio
async def test_interview_prep_get_still_allowed_when_expired(auth_headers, seed_profile):
    """GET interview prep is not paywalled (CurrentDbUser)."""
    from datetime import UTC, datetime, timedelta

    from hireloop.models.subscription import Subscription

    user_id = await _user_id()
    factory = get_session_factory()
    async with factory() as session:
        sr = await session.execute(select(Subscription).where(Subscription.user_id == user_id))
        sub = sr.scalar_one_or_none()
        if sub is None:
            sub = Subscription(user_id=user_id, plan="trial", status="active")
            session.add(sub)
            await session.flush()
        sub.trial_ends_at = datetime.now(UTC) - timedelta(days=1)
        sub.stripe_subscription_id = None
        await session.commit()

    try:
        with patch(
            "hireloop.integrations.cognito.CognitoJwtVerifier.verify",
            new=AsyncMock(return_value=FAKE_CLAIMS),
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                r = await client.get(f"/api/v1/interview-preps/{uuid4()}", headers=auth_headers)
        assert r.status_code == 404
    finally:
        async with factory() as session:
            sr = await session.execute(select(Subscription).where(Subscription.user_id == user_id))
            sub = sr.scalar_one_or_none()
            if sub is not None:
                sub.trial_ends_at = datetime.now(UTC) + timedelta(days=30)
                await session.commit()
