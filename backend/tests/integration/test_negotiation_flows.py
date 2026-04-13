"""Negotiation API: playbook generation, regenerate, paywall."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select

from hireloop.db import get_session_factory
from hireloop.main import app
from hireloop.models.negotiation import Negotiation
from hireloop.models.user import User
from tests.conftest import FAKE_CLAIMS
from tests.fixtures.fake_anthropic import fake_anthropic
from tests.integration._phase2d_fakes import anthropic_responses_negotiation_only


async def _user_id() -> UUID:
    factory = get_session_factory()
    async with factory() as session:
        r = await session.execute(select(User).where(User.cognito_sub == FAKE_CLAIMS["sub"]))
        return r.scalar_one().id


async def _clear_negotiations(user_id: UUID) -> None:
    factory = get_session_factory()
    async with factory() as session:
        await session.execute(delete(Negotiation).where(Negotiation.user_id == user_id))
        await session.commit()


@pytest.mark.asyncio
async def test_negotiation_full_playbook(auth_headers, seed_profile, seeded_evaluation_for_user_a):
    user_id = await _user_id()
    await _clear_negotiations(user_id)

    job_id = str(seeded_evaluation_for_user_a.job_id)
    with (
        patch(
            "hireloop.integrations.cognito.CognitoJwtVerifier.verify",
            new=AsyncMock(return_value=FAKE_CLAIMS),
        ),
        fake_anthropic(anthropic_responses_negotiation_only()),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.post(
                "/api/v1/negotiations",
                json={
                    "job_id": job_id,
                    "offer_details": {
                        "base": 185000,
                        "equity": "0.08%",
                        "signing_bonus": 20000,
                        "location": "Remote",
                    },
                },
                headers=auth_headers,
            )
    assert r.status_code == 201
    body = r.json()["data"]
    assert body["market_research"]["range_mid"] == 200000
    assert "email_template" in body["scripts"]


@pytest.mark.asyncio
async def test_negotiation_regenerate(auth_headers, seed_profile, seeded_evaluation_for_user_a):
    user_id = await _user_id()
    await _clear_negotiations(user_id)
    job_id = str(seeded_evaluation_for_user_a.job_id)

    with (
        patch(
            "hireloop.integrations.cognito.CognitoJwtVerifier.verify",
            new=AsyncMock(return_value=FAKE_CLAIMS),
        ),
        fake_anthropic(anthropic_responses_negotiation_only()),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r0 = await client.post(
                "/api/v1/negotiations",
                json={"job_id": job_id, "offer_details": {"base": 180000}},
                headers=auth_headers,
            )
            neg_id = r0.json()["data"]["id"]
            r1 = await client.post(
                f"/api/v1/negotiations/{neg_id}/regenerate",
                json={"feedback": "Emphasize remote market"},
                headers=auth_headers,
            )
    assert r1.status_code == 201
    assert r1.json()["data"]["id"] != neg_id


@pytest.mark.asyncio
async def test_negotiation_paywalled_when_trial_expired(
    auth_headers, seed_profile, seeded_evaluation_for_user_a
):
    from datetime import UTC, datetime, timedelta

    from hireloop.models.subscription import Subscription

    user_id = await _user_id()
    await _clear_negotiations(user_id)
    job_id = str(seeded_evaluation_for_user_a.job_id)

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
            fake_anthropic(anthropic_responses_negotiation_only()),
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                r = await client.post(
                    "/api/v1/negotiations",
                    json={"job_id": job_id, "offer_details": {"base": 180000}},
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
async def test_negotiation_invalid_offer_rejected(
    auth_headers, seed_profile, seeded_evaluation_for_user_a
):
    """Negative base fails Pydantic validation."""
    with patch(
        "hireloop.integrations.cognito.CognitoJwtVerifier.verify",
        new=AsyncMock(return_value=FAKE_CLAIMS),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.post(
                "/api/v1/negotiations",
                json={
                    "job_id": str(seeded_evaluation_for_user_a.job_id),
                    "offer_details": {"base": -1},
                },
                headers=auth_headers,
            )
    assert r.status_code == 422
