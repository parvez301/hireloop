"""Paywall: expired trial blocks paywalled routes."""

import os
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from hireloop.config import get_settings
from hireloop.db import get_session_factory
from hireloop.main import app
from hireloop.models.subscription import Subscription
from hireloop.models.user import User
from tests.conftest import FAKE_CLAIMS
from tests.fixtures.fake_gemini import fake_gemini

_FAKE_JSON = (
    '{"title": "Staff Engineer", "company": "Acme", "location": "Remote", '
    '"salary_min": 180000, "salary_max": 220000, "employment_type": "full_time", '
    '"seniority": "staff", "description_md": "...", '
    '"requirements": {"skills": ["python", "go"], "years_experience": 8, "nice_to_haves": []}}'
)


@pytest.mark.asyncio
async def test_jobs_parse_403_when_trial_expired(auth_headers):
    """Paywalled route returns TRIAL_EXPIRED when in-app trial ended and no Stripe sub."""
    factory = get_session_factory()
    try:
        async with factory() as session:
            ur = await session.execute(select(User).where(User.cognito_sub == FAKE_CLAIMS["sub"]))
            user = ur.scalar_one()
            sr = await session.execute(select(Subscription).where(Subscription.user_id == user.id))
            sub = sr.scalar_one_or_none()
            if sub is None:
                sub = Subscription(user_id=user.id, plan="trial", status="active")
                session.add(sub)
                await session.flush()
            sub.trial_ends_at = datetime.now(UTC) - timedelta(days=1)
            sub.stripe_subscription_id = None
            sub.status = "active"
            await session.commit()

        with patch(
            "hireloop.integrations.cognito.CognitoJwtVerifier.verify",
            new=AsyncMock(return_value=FAKE_CLAIMS),
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/v1/jobs/parse",
                    json={"description_md": "Staff Engineer at Acme. Remote. Python required." * 5},
                    headers=auth_headers,
                )
        assert resp.status_code == 403
        body = resp.json()
        assert body["error"]["code"] == "TRIAL_EXPIRED"
    finally:
        async with factory() as session:
            ur = await session.execute(select(User).where(User.cognito_sub == FAKE_CLAIMS["sub"]))
            user = ur.scalar_one()
            sr = await session.execute(select(Subscription).where(Subscription.user_id == user.id))
            sub = sr.scalar_one_or_none()
            if sub is not None:
                sub.trial_ends_at = datetime.now(UTC) + timedelta(days=30)
                await session.commit()


async def _force_expired_trial(user_id):
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
        sub.status = "active"
        sub.past_due_since = None
        await session.commit()


async def _restore_trial(user_id):
    factory = get_session_factory()
    async with factory() as session:
        sr = await session.execute(select(Subscription).where(Subscription.user_id == user_id))
        sub = sr.scalar_one_or_none()
        if sub is not None:
            sub.trial_ends_at = datetime.now(UTC) + timedelta(days=30)
            await session.commit()


@pytest.mark.asyncio
async def test_all_gated_endpoints_return_403_when_expired(
    auth_headers, seed_conversation, seeded_evaluation_for_user_a
):
    """Every endpoint wired to EntitledDbUser rejects with TRIAL_EXPIRED when expired."""
    factory = get_session_factory()
    async with factory() as session:
        ur = await session.execute(select(User).where(User.cognito_sub == FAKE_CLAIMS["sub"]))
        user = ur.scalar_one()
        user_id = user.id

    try:
        await _force_expired_trial(user_id)

        with patch(
            "hireloop.integrations.cognito.CognitoJwtVerifier.verify",
            new=AsyncMock(return_value=FAKE_CLAIMS),
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                gated_calls = [
                    (
                        "POST",
                        f"/api/v1/conversations/{seed_conversation.id}/messages",
                        {"content": "hi"},
                    ),
                    (
                        "POST",
                        "/api/v1/evaluations",
                        {"job_description": "long" * 50},
                    ),
                    (
                        "POST",
                        "/api/v1/cv-outputs",
                        {"job_id": "00000000-0000-0000-0000-000000000000"},
                    ),
                    (
                        "POST",
                        "/api/v1/jobs/parse",
                        {"description_md": "Staff Engineer. Python." * 5},
                    ),
                    (
                        "POST",
                        "/api/v1/interview-preps",
                        {"custom_role": "Staff Backend Engineer"},
                    ),
                    (
                        "POST",
                        "/api/v1/negotiations",
                        {
                            "job_id": str(seeded_evaluation_for_user_a.job_id),
                            "offer_details": {"base": 180000},
                        },
                    ),
                ]
                for method, path, body in gated_calls:
                    resp = await client.request(method, path, json=body, headers=auth_headers)
                    assert (
                        resp.status_code == 403
                    ), f"{method} {path} returned {resp.status_code}, expected 403"
                    err = resp.json()["error"]
                    assert err["code"] == "TRIAL_EXPIRED", f"{method} {path} returned {err['code']}"
    finally:
        await _restore_trial(user_id)


@pytest.mark.asyncio
async def test_past_due_within_grace_is_allowed(auth_headers):
    """A past_due subscription within 3-day grace passes the paywall."""
    factory = get_session_factory()
    async with factory() as session:
        ur = await session.execute(select(User).where(User.cognito_sub == FAKE_CLAIMS["sub"]))
        user = ur.scalar_one()
        user_id = user.id

    try:
        async with factory() as session:
            sr = await session.execute(select(Subscription).where(Subscription.user_id == user_id))
            sub = sr.scalar_one_or_none()
            if sub is None:
                sub = Subscription(user_id=user_id, plan="pro", status="past_due")
                session.add(sub)
                await session.flush()
            sub.trial_ends_at = datetime.now(UTC) - timedelta(days=30)
            sub.stripe_subscription_id = "sub_test_123"
            sub.status = "past_due"
            sub.past_due_since = datetime.now(UTC) - timedelta(days=1)
            sub.plan = "pro"
            await session.commit()

        with (
            patch(
                "hireloop.integrations.cognito.CognitoJwtVerifier.verify",
                new=AsyncMock(return_value=FAKE_CLAIMS),
            ),
            fake_gemini({"Staff": _FAKE_JSON}),
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/v1/jobs/parse",
                    json={"description_md": "Staff Engineer at Acme. Remote. Python required." * 5},
                    headers=auth_headers,
                )
        assert resp.status_code == 200
    finally:
        await _restore_trial(user_id)


@pytest.mark.asyncio
async def test_past_due_beyond_grace_is_blocked(auth_headers):
    """A past_due subscription 4 days in is paywalled."""
    factory = get_session_factory()
    async with factory() as session:
        ur = await session.execute(select(User).where(User.cognito_sub == FAKE_CLAIMS["sub"]))
        user = ur.scalar_one()
        user_id = user.id

    try:
        async with factory() as session:
            sr = await session.execute(select(Subscription).where(Subscription.user_id == user_id))
            sub = sr.scalar_one_or_none()
            if sub is None:
                sub = Subscription(user_id=user_id, plan="pro", status="past_due")
                session.add(sub)
                await session.flush()
            sub.trial_ends_at = datetime.now(UTC) - timedelta(days=30)
            sub.stripe_subscription_id = "sub_test_456"
            sub.status = "past_due"
            sub.past_due_since = datetime.now(UTC) - timedelta(days=4)
            sub.plan = "pro"
            await session.commit()

        with patch(
            "hireloop.integrations.cognito.CognitoJwtVerifier.verify",
            new=AsyncMock(return_value=FAKE_CLAIMS),
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/v1/jobs/parse",
                    json={"description_md": "Staff Engineer at Acme. Remote. Python required." * 5},
                    headers=auth_headers,
                )
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "TRIAL_EXPIRED"
    finally:
        await _restore_trial(user_id)


@pytest.mark.asyncio
async def test_disable_paywall_skips_check(auth_headers):
    """When DISABLE_PAYWALL is true, expired trial does not block."""
    get_settings.cache_clear()
    prev = os.environ.get("DISABLE_PAYWALL")
    os.environ["DISABLE_PAYWALL"] = "true"
    get_settings.cache_clear()

    factory = get_session_factory()
    async with factory() as session:
        ur = await session.execute(select(User).where(User.cognito_sub == FAKE_CLAIMS["sub"]))
        user = ur.scalar_one()
        sr = await session.execute(select(Subscription).where(Subscription.user_id == user.id))
        sub = sr.scalar_one_or_none()
        if sub is None:
            sub = Subscription(user_id=user.id, plan="trial", status="active")
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
            fake_gemini({"Staff": _FAKE_JSON}),
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/v1/jobs/parse",
                    json={"description_md": "Staff Engineer at Acme. Remote. Python required." * 5},
                    headers=auth_headers,
                )
        assert resp.status_code == 200
    finally:
        if prev is None:
            os.environ.pop("DISABLE_PAYWALL", None)
        else:
            os.environ["DISABLE_PAYWALL"] = prev
        get_settings.cache_clear()
        factory = get_session_factory()
        async with factory() as session:
            ur = await session.execute(select(User).where(User.cognito_sub == FAKE_CLAIMS["sub"]))
            user = ur.scalar_one()
            sr = await session.execute(select(Subscription).where(Subscription.user_id == user.id))
            sub = sr.scalar_one_or_none()
            if sub is not None:
                sub.trial_ends_at = datetime.now(UTC) + timedelta(days=30)
                await session.commit()
