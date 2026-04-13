"""Thin Stripe Checkout / Portal helpers."""

from __future__ import annotations

from datetime import UTC, datetime

import stripe

from hireloop.config import Settings
from hireloop.models.subscription import Subscription
from hireloop.models.user import User


def _configure(settings: Settings) -> None:
    if not settings.stripe_secret_key:
        raise ValueError("STRIPE_SECRET_KEY is not set")
    stripe.api_key = settings.stripe_secret_key


def ensure_stripe_customer(
    settings: Settings,
    user: User,
    sub: Subscription,
) -> str:
    """Return Stripe customer id, creating and persisting when missing."""
    _configure(settings)
    if sub.stripe_customer_id:
        return sub.stripe_customer_id
    customer = stripe.Customer.create(
        email=user.email,
        metadata={"user_id": str(user.id)},
    )
    sub.stripe_customer_id = customer.id
    return customer.id


def create_checkout_session(
    *,
    settings: Settings,
    user: User,
    sub: Subscription,
    success_path: str = "/billing/success",
    cancel_path: str = "/billing/cancel",
) -> str:
    _configure(settings)
    if not settings.stripe_price_pro_monthly:
        raise ValueError("STRIPE_PRICE_PRO_MONTHLY is not set")
    cust_id = sub.stripe_customer_id
    if not cust_id:
        raise ValueError("Stripe customer must exist before checkout")
    session = stripe.checkout.Session.create(
        mode="subscription",
        customer=cust_id,
        client_reference_id=str(user.id),
        line_items=[{"price": settings.stripe_price_pro_monthly, "quantity": 1}],
        success_url=f"{settings.app_url.rstrip('/')}{success_path}?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{settings.app_url.rstrip('/')}{cancel_path}",
        subscription_data={
            "metadata": {"user_id": str(user.id)},
        },
    )
    url = session.url
    if not url:
        raise RuntimeError("Stripe Checkout Session missing redirect URL")
    return url


def create_portal_session(
    *,
    settings: Settings,
    stripe_customer_id: str,
    return_path: str = "/",
) -> str:
    _configure(settings)
    session = stripe.billing_portal.Session.create(
        customer=stripe_customer_id,
        return_url=f"{settings.app_url.rstrip('/')}{return_path}",
    )
    url = session.url
    if not url:
        raise RuntimeError("Stripe Portal Session missing URL")
    return url


def retrieve_subscription(subscription_id: str, settings: Settings) -> stripe.Subscription:
    _configure(settings)
    return stripe.Subscription.retrieve(subscription_id)


def dt_from_stripe_ts(ts: int | None) -> datetime | None:
    if ts is None:
        return None
    return datetime.fromtimestamp(int(ts), tz=UTC)


def apply_stripe_subscription_to_row(
    sub_row: Subscription, stripe_sub: stripe.Subscription
) -> None:
    """Mutate ORM row from a Stripe Subscription object."""
    sub_row.stripe_subscription_id = stripe_sub.id
    sub_row.status = str(stripe_sub.status)
    cpe = getattr(stripe_sub, "current_period_end", None)
    if cpe:
        sub_row.current_period_end = dt_from_stripe_ts(int(cpe))
    te = getattr(stripe_sub, "trial_end", None)
    if te:
        sub_row.trial_ends_at = dt_from_stripe_ts(int(te))
    cape = getattr(stripe_sub, "cancel_at_period_end", None)
    if cape is not None:
        sub_row.cancel_at_period_end = bool(cape)
    if stripe_sub.status in ("active", "trialing"):
        sub_row.plan = "pro"
        # Any healthy state clears the past_due tracker.
        sub_row.past_due_since = None
    elif stripe_sub.status == "canceled":
        sub_row.plan = "canceled"
        sub_row.past_due_since = None
