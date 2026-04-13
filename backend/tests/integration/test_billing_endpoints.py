"""Integration tests for /api/v1/billing endpoints.

All Stripe SDK calls are mocked at the stripe_client module boundary so
these tests never hit the real Stripe API.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from hireloop.db import get_session_factory
from hireloop.main import app
from hireloop.models.subscription import Subscription
from hireloop.models.user import User
from tests.conftest import FAKE_CLAIMS


def _fake_customer_create(*, email: str, metadata: dict) -> SimpleNamespace:
    return SimpleNamespace(id="cus_fake_created")


def _fake_checkout_create(**kwargs):
    return SimpleNamespace(
        id="cs_fake_1",
        url="https://checkout.stripe.com/fake",
    )


def _fake_portal_create(**kwargs):
    return SimpleNamespace(
        id="bps_fake_1",
        url="https://billing.stripe.com/fake",
    )


@pytest.mark.asyncio
async def test_get_subscription_bootstraps_trial(auth_headers):
    """GET /billing/subscription materializes a trial row for a new user."""
    factory = get_session_factory()
    async with factory() as session:
        r = await session.execute(select(User).where(User.cognito_sub == FAKE_CLAIMS["sub"]))
        user = r.scalar_one()
        sr = await session.execute(select(Subscription).where(Subscription.user_id == user.id))
        for existing in sr.scalars().all():
            await session.delete(existing)
        await session.commit()

    with patch(
        "hireloop.integrations.cognito.CognitoJwtVerifier.verify",
        new=AsyncMock(return_value=FAKE_CLAIMS),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/api/v1/billing/subscription", headers=auth_headers)

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["plan"] == "trial"
    assert data["status"] == "active"
    assert data["has_active_entitlement"] is True
    assert data["cancel_at_period_end"] is False
    assert data["past_due_since"] is None


@pytest.mark.asyncio
async def test_post_checkout_returns_stripe_url(auth_headers):
    """POST /billing/checkout creates a Customer if missing and returns Stripe URL."""
    factory = get_session_factory()
    async with factory() as session:
        r = await session.execute(select(User).where(User.cognito_sub == FAKE_CLAIMS["sub"]))
        user = r.scalar_one()
        sr = await session.execute(select(Subscription).where(Subscription.user_id == user.id))
        sub = sr.scalar_one_or_none()
        if sub is None:
            sub = Subscription(
                user_id=user.id,
                plan="trial",
                status="active",
                trial_ends_at=datetime.now(UTC) + timedelta(days=3),
            )
            session.add(sub)
        sub.stripe_customer_id = None
        sub.stripe_subscription_id = None
        await session.commit()

    with (
        patch(
            "hireloop.integrations.cognito.CognitoJwtVerifier.verify",
            new=AsyncMock(return_value=FAKE_CLAIMS),
        ),
        patch("stripe.api_key", "sk_test_fake"),
        patch("stripe.Customer.create", side_effect=_fake_customer_create),
        patch("stripe.checkout.Session.create", side_effect=_fake_checkout_create),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/v1/billing/checkout", headers=auth_headers)

    assert resp.status_code == 200
    assert resp.json()["data"]["url"] == "https://checkout.stripe.com/fake"

    # Verify the customer id was persisted
    async with factory() as session:
        r = await session.execute(select(User).where(User.cognito_sub == FAKE_CLAIMS["sub"]))
        user = r.scalar_one()
        sr = await session.execute(select(Subscription).where(Subscription.user_id == user.id))
        sub = sr.scalar_one()
        assert sub.stripe_customer_id == "cus_fake_created"


@pytest.mark.asyncio
async def test_post_portal_requires_stripe_customer(auth_headers):
    """POST /billing/portal 422s when no stripe_customer_id exists."""
    factory = get_session_factory()
    async with factory() as session:
        r = await session.execute(select(User).where(User.cognito_sub == FAKE_CLAIMS["sub"]))
        user = r.scalar_one()
        sr = await session.execute(select(Subscription).where(Subscription.user_id == user.id))
        sub = sr.scalar_one_or_none()
        if sub is None:
            sub = Subscription(
                user_id=user.id,
                plan="trial",
                status="active",
                trial_ends_at=datetime.now(UTC) + timedelta(days=3),
            )
            session.add(sub)
        sub.stripe_customer_id = None
        await session.commit()

    with patch(
        "hireloop.integrations.cognito.CognitoJwtVerifier.verify",
        new=AsyncMock(return_value=FAKE_CLAIMS),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/v1/billing/portal", headers=auth_headers)

    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "NO_STRIPE_CUSTOMER"


@pytest.mark.asyncio
async def test_post_portal_returns_stripe_url(auth_headers):
    """POST /billing/portal returns the Stripe Portal URL when customer exists."""
    factory = get_session_factory()
    async with factory() as session:
        r = await session.execute(select(User).where(User.cognito_sub == FAKE_CLAIMS["sub"]))
        user = r.scalar_one()
        sr = await session.execute(select(Subscription).where(Subscription.user_id == user.id))
        sub = sr.scalar_one_or_none()
        if sub is None:
            sub = Subscription(
                user_id=user.id,
                plan="pro",
                status="active",
                trial_ends_at=datetime.now(UTC) - timedelta(days=10),
            )
            session.add(sub)
        sub.stripe_customer_id = "cus_portal_existing"
        sub.stripe_subscription_id = "sub_portal_existing"
        sub.status = "active"
        sub.plan = "pro"
        await session.commit()

    with (
        patch(
            "hireloop.integrations.cognito.CognitoJwtVerifier.verify",
            new=AsyncMock(return_value=FAKE_CLAIMS),
        ),
        patch("stripe.api_key", "sk_test_fake"),
        patch("stripe.billing_portal.Session.create", side_effect=_fake_portal_create),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/api/v1/billing/portal", headers=auth_headers)

    assert resp.status_code == 200
    assert resp.json()["data"]["url"] == "https://billing.stripe.com/fake"
