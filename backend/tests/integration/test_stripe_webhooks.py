"""Stripe webhook handler integration tests.

These tests bypass signature verification by monkey-patching
`stripe.Webhook.construct_event` to return a hand-built event object, and
monkey-patch `stripe_client.retrieve_subscription` so we never touch the
real Stripe API. The rest of the handler — DB writes, idempotency ledger,
`apply_stripe_subscription_to_row`, past_due grace stamping — runs for real
against the test Postgres.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import patch
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from hireloop.db import get_session_factory
from hireloop.main import app
from hireloop.models.stripe_webhook_event import StripeWebhookEvent
from hireloop.models.subscription import Subscription
from hireloop.models.user import User
from tests.conftest import FAKE_CLAIMS

# ---------- fakes ----------


@dataclass
class _FakeEventData:
    object: Any


@dataclass
class _FakeEvent:
    id: str
    type: str
    data: _FakeEventData


@dataclass
class _FakeStripeSubscription:
    id: str
    status: str
    current_period_end: int
    trial_end: int | None = None
    cancel_at_period_end: bool = False
    customer: str | None = None


def _ts(dt: datetime) -> int:
    return int(dt.timestamp())


def _construct(event: _FakeEvent):
    def _fake_construct_event(payload, sig_header, secret):
        return event

    return _fake_construct_event


def _retrieve(stripe_sub: _FakeStripeSubscription):
    def _fake_retrieve(sid, settings):
        return stripe_sub

    return _fake_retrieve


# ---------- shared helpers ----------


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
            await session.flush()
            await session.commit()
            await session.refresh(user)
        return user.id


async def _get_or_create_sub(
    user_id: UUID,
    *,
    stripe_customer_id: str | None = None,
    stripe_subscription_id: str | None = None,
    status: str = "active",
    plan: str = "pro",
    past_due_since: datetime | None = None,
) -> Subscription:
    factory = get_session_factory()
    async with factory() as session:
        r = await session.execute(select(Subscription).where(Subscription.user_id == user_id))
        sub = r.scalar_one_or_none()
        if sub is None:
            sub = Subscription(
                user_id=user_id,
                plan=plan,
                status=status,
                trial_ends_at=datetime.now(UTC) + timedelta(days=30),
            )
            session.add(sub)
            await session.flush()
        sub.stripe_customer_id = stripe_customer_id
        sub.stripe_subscription_id = stripe_subscription_id
        sub.status = status
        sub.plan = plan
        sub.past_due_since = past_due_since
        await session.commit()
        await session.refresh(sub)
        return sub


async def _reload_sub(user_id: UUID) -> Subscription:
    factory = get_session_factory()
    async with factory() as session:
        r = await session.execute(select(Subscription).where(Subscription.user_id == user_id))
        return r.scalar_one()


async def _cleanup_webhook_events() -> None:
    factory = get_session_factory()
    async with factory() as session:
        from sqlalchemy import delete

        await session.execute(delete(StripeWebhookEvent))
        await session.commit()


async def _post_webhook(event: _FakeEvent, retrieve_sub: _FakeStripeSubscription | None = None):
    patches = [
        patch("stripe.Webhook.construct_event", _construct(event)),
    ]
    if retrieve_sub is not None:
        patches.append(
            patch(
                "hireloop.integrations.stripe_client.retrieve_subscription",
                _retrieve(retrieve_sub),
            )
        )

    with patches[0]:
        if len(patches) > 1:
            with patches[1]:
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    return await client.post(
                        "/api/v1/webhooks/stripe",
                        content=b"{}",
                        headers={"stripe-signature": "t=1,v1=fake"},
                    )
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post(
                "/api/v1/webhooks/stripe",
                content=b"{}",
                headers={"stripe-signature": "t=1,v1=fake"},
            )


# ---------- tests ----------


@pytest.mark.asyncio
async def test_webhook_idempotency_dupe_returns_ok_without_mutation():
    user_id = await _get_user_id()
    await _get_or_create_sub(
        user_id,
        stripe_customer_id="cus_idem",
        stripe_subscription_id="sub_idem",
        status="active",
    )
    await _cleanup_webhook_events()
    try:
        stripe_sub = _FakeStripeSubscription(
            id="sub_idem",
            status="past_due",
            current_period_end=_ts(datetime.now(UTC) + timedelta(days=5)),
            customer="cus_idem",
        )
        event = _FakeEvent(
            id="evt_dedupe_1",
            type="customer.subscription.updated",
            data=_FakeEventData(object=stripe_sub),
        )
        r1 = await _post_webhook(event, stripe_sub)
        assert r1.status_code == 200

        after_first = await _reload_sub(user_id)
        assert after_first.status == "past_due"

        # Second delivery: same event id → handler should skip mutation
        # Mutate the row first so we can detect non-mutation on dupe
        factory = get_session_factory()
        async with factory() as session:
            r = await session.execute(select(Subscription).where(Subscription.user_id == user_id))
            s = r.scalar_one()
            s.status = "marker"
            await session.commit()

        r2 = await _post_webhook(event, stripe_sub)
        assert r2.status_code == 200

        after_dupe = await _reload_sub(user_id)
        assert after_dupe.status == "marker"  # not overwritten
    finally:
        await _cleanup_webhook_events()
        await _get_or_create_sub(user_id, status="active", plan="trial")


@pytest.mark.asyncio
async def test_webhook_invoice_payment_failed_stamps_past_due_since():
    user_id = await _get_user_id()
    await _get_or_create_sub(
        user_id,
        stripe_customer_id="cus_pf",
        stripe_subscription_id="sub_pf",
        status="active",
        plan="pro",
    )
    await _cleanup_webhook_events()
    try:
        invoice = {"subscription": "sub_pf", "customer": "cus_pf"}
        event = _FakeEvent(
            id="evt_pf_1",
            type="invoice.payment_failed",
            data=_FakeEventData(object=invoice),
        )
        resp = await _post_webhook(event)
        assert resp.status_code == 200

        after = await _reload_sub(user_id)
        assert after.status == "past_due"
        assert after.past_due_since is not None
        first_stamp = after.past_due_since

        # Retry: different event id, same payload — past_due_since must NOT change
        event2 = _FakeEvent(
            id="evt_pf_2",
            type="invoice.payment_failed",
            data=_FakeEventData(object=invoice),
        )
        resp2 = await _post_webhook(event2)
        assert resp2.status_code == 200

        after2 = await _reload_sub(user_id)
        assert after2.past_due_since == first_stamp  # idempotent grace start
    finally:
        await _cleanup_webhook_events()
        await _get_or_create_sub(user_id, status="active", plan="trial")


@pytest.mark.asyncio
async def test_webhook_invoice_paid_clears_past_due():
    user_id = await _get_user_id()
    await _get_or_create_sub(
        user_id,
        stripe_customer_id="cus_ip",
        stripe_subscription_id="sub_ip",
        status="past_due",
        plan="pro",
        past_due_since=datetime.now(UTC) - timedelta(days=1),
    )
    await _cleanup_webhook_events()
    try:
        invoice = {"subscription": "sub_ip", "customer": "cus_ip"}
        event = _FakeEvent(
            id="evt_ip_1",
            type="invoice.paid",
            data=_FakeEventData(object=invoice),
        )
        stripe_sub = _FakeStripeSubscription(
            id="sub_ip",
            status="active",
            current_period_end=_ts(datetime.now(UTC) + timedelta(days=30)),
            customer="cus_ip",
        )
        resp = await _post_webhook(event, stripe_sub)
        assert resp.status_code == 200

        after = await _reload_sub(user_id)
        assert after.status == "active"
        assert after.past_due_since is None
        assert after.plan == "pro"
    finally:
        await _cleanup_webhook_events()
        await _get_or_create_sub(user_id, status="active", plan="trial")


@pytest.mark.asyncio
async def test_webhook_subscription_deleted_cancels():
    user_id = await _get_user_id()
    await _get_or_create_sub(
        user_id,
        stripe_customer_id="cus_del",
        stripe_subscription_id="sub_del",
        status="active",
        plan="pro",
    )
    await _cleanup_webhook_events()
    try:
        stripe_sub_obj = _FakeStripeSubscription(
            id="sub_del",
            status="canceled",
            current_period_end=_ts(datetime.now(UTC)),
            customer="cus_del",
        )
        event = _FakeEvent(
            id="evt_del_1",
            type="customer.subscription.deleted",
            data=_FakeEventData(object=stripe_sub_obj),
        )
        resp = await _post_webhook(event)
        assert resp.status_code == 200

        after = await _reload_sub(user_id)
        assert after.status == "canceled"
        assert after.past_due_since is None
    finally:
        await _cleanup_webhook_events()
        await _get_or_create_sub(user_id, status="active", plan="trial")


@pytest.mark.asyncio
async def test_webhook_subscription_updated_mirrors_cancel_at_period_end():
    user_id = await _get_user_id()
    await _get_or_create_sub(
        user_id,
        stripe_customer_id="cus_cape",
        stripe_subscription_id="sub_cape",
        status="active",
        plan="pro",
    )
    await _cleanup_webhook_events()
    try:
        stripe_sub = _FakeStripeSubscription(
            id="sub_cape",
            status="active",
            current_period_end=_ts(datetime.now(UTC) + timedelta(days=10)),
            cancel_at_period_end=True,
            customer="cus_cape",
        )
        event = _FakeEvent(
            id="evt_cape_1",
            type="customer.subscription.updated",
            data=_FakeEventData(object=stripe_sub),
        )
        resp = await _post_webhook(event, stripe_sub)
        assert resp.status_code == 200

        after = await _reload_sub(user_id)
        assert after.cancel_at_period_end is True
        assert after.status == "active"  # still entitled until period_end
    finally:
        await _cleanup_webhook_events()
        await _get_or_create_sub(user_id, status="active", plan="trial")
