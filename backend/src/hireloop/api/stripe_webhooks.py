"""Stripe webhooks — subscription sync (source of truth)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

import stripe
from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from hireloop.config import Settings, get_settings
from hireloop.db import get_session_factory
from hireloop.integrations import stripe_client
from hireloop.models.stripe_webhook_event import StripeWebhookEvent
from hireloop.models.subscription import Subscription
from hireloop.models.user import User
from hireloop.services.subscription import ensure_subscription

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def _stripe_field(obj: Any, key: str) -> Any:
    if isinstance(obj, dict):
        return obj.get(key)
    return getattr(obj, key, None)


async def _handle_checkout_completed(db: AsyncSession, obj: Any, settings: Settings) -> None:
    raw_uid = _stripe_field(obj, "client_reference_id")
    sub_id = _stripe_field(obj, "subscription")
    customer_id = _stripe_field(obj, "customer")
    if not raw_uid or not sub_id or not customer_id:
        return
    try:
        user_id = UUID(str(raw_uid))
    except ValueError:
        return
    ur = await db.execute(select(User).where(User.id == user_id))
    user = ur.scalar_one_or_none()
    if user is None:
        return
    sub_row = await ensure_subscription(db, user_id, settings)
    sub_row.stripe_customer_id = str(customer_id)
    stripe_sub = stripe_client.retrieve_subscription(str(sub_id), settings)
    stripe_client.apply_stripe_subscription_to_row(sub_row, stripe_sub)


async def _handle_subscription_updated(db: AsyncSession, obj: Any, settings: Settings) -> None:
    sid = _stripe_field(obj, "id")
    if not sid:
        return
    stripe_sub = stripe_client.retrieve_subscription(str(sid), settings)
    r = await db.execute(
        select(Subscription).where(Subscription.stripe_subscription_id == stripe_sub.id)
    )
    row = r.scalar_one_or_none()
    if row is None:
        cust = stripe_sub.customer
        cust_id = cust if isinstance(cust, str) else getattr(cust, "id", None)
        if cust_id:
            r2 = await db.execute(
                select(Subscription).where(Subscription.stripe_customer_id == cust_id)
            )
            row = r2.scalar_one_or_none()
    if row is None:
        return
    stripe_client.apply_stripe_subscription_to_row(row, stripe_sub)


async def _handle_subscription_deleted(db: AsyncSession, obj: Any) -> None:
    sid = _stripe_field(obj, "id")
    if not sid:
        return
    r = await db.execute(select(Subscription).where(Subscription.stripe_subscription_id == sid))
    row = r.scalar_one_or_none()
    if row is None:
        return
    row.status = "canceled"
    row.past_due_since = None


async def _row_for_invoice(db: AsyncSession, obj: Any) -> Subscription | None:
    """Look up the subscription row referenced by an invoice event."""
    sub_id = _stripe_field(obj, "subscription")
    if sub_id:
        r = await db.execute(
            select(Subscription).where(Subscription.stripe_subscription_id == str(sub_id))
        )
        row = r.scalar_one_or_none()
        if row is not None:
            return row
    cust_id = _stripe_field(obj, "customer")
    if cust_id:
        r2 = await db.execute(
            select(Subscription).where(Subscription.stripe_customer_id == str(cust_id))
        )
        return r2.scalar_one_or_none()
    return None


async def _handle_invoice_paid(db: AsyncSession, obj: Any, settings: Settings) -> None:
    """Flip to pro/active, clear past_due_since, refresh period_end from Stripe."""
    row = await _row_for_invoice(db, obj)
    if row is None:
        return
    row.past_due_since = None
    sid = _stripe_field(obj, "subscription")
    if sid:
        stripe_sub = stripe_client.retrieve_subscription(str(sid), settings)
        stripe_client.apply_stripe_subscription_to_row(row, stripe_sub)
    else:
        # No subscription id on the invoice — still mark active so user recovers.
        if row.status == "past_due":
            row.status = "active"


async def _handle_invoice_payment_failed(db: AsyncSession, obj: Any) -> None:
    """Mark past_due and stamp past_due_since (if not already stamped).

    Idempotent across Stripe retries — we only stamp on the first failure so
    the grace window counts from when trouble started, not from the latest retry.
    """
    row = await _row_for_invoice(db, obj)
    if row is None:
        return
    row.status = "past_due"
    if row.past_due_since is None:
        from hireloop.services.subscription import utc_now

        row.past_due_since = utc_now()


@router.post("/stripe")
async def stripe_webhook(request: Request) -> dict[str, Any]:
    settings = get_settings()
    secret = settings.stripe_webhook_secret
    if not secret:
        return {"received": True}

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    if not sig_header:
        raise HTTPException(status_code=400, detail="Missing Stripe-Signature")

    try:
        event = stripe.Webhook.construct_event(  # type: ignore[no-untyped-call]
            payload, sig_header, secret
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid payload") from e
    except stripe.SignatureVerificationError as e:
        raise HTTPException(status_code=400, detail="Invalid signature") from e

    factory = get_session_factory()
    async with factory() as db:
        try:
            wh = StripeWebhookEvent(
                stripe_event_id=str(event.id),
                event_type=str(event.type),
            )
            db.add(wh)
            await db.flush()
        except IntegrityError:
            await db.rollback()
            return {"received": True}

        try:
            data_object = event.data.object
            evt_type = str(event.type)
            if evt_type == "checkout.session.completed":
                await _handle_checkout_completed(db, data_object, settings)
            elif evt_type == "customer.subscription.updated":
                await _handle_subscription_updated(db, data_object, settings)
            elif evt_type == "customer.subscription.deleted":
                await _handle_subscription_deleted(db, data_object)
            elif evt_type == "invoice.paid":
                await _handle_invoice_paid(db, data_object, settings)
            elif evt_type == "invoice.payment_failed":
                await _handle_invoice_payment_failed(db, data_object)
            # customer.subscription.trial_will_end intentionally ignored
            # (Phase 2b does not use Stripe-managed trials — see spec §D2).
            await db.commit()
        except Exception:
            await db.rollback()
            raise

    return {"received": True}
