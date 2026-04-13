"""Billing: Checkout, Customer Portal, subscription read."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from hireloop.api.deps import CurrentDbUser, DbSession
from hireloop.api.errors import AppError
from hireloop.config import get_settings
from hireloop.integrations import stripe_client
from hireloop.schemas.billing import CheckoutSessionOut, PortalSessionOut, SubscriptionOut
from hireloop.services.subscription import ensure_subscription, is_entitled, utc_now

router = APIRouter(prefix="/billing", tags=["billing"])


def _billing_configured() -> bool:
    s = get_settings()
    return bool(s.stripe_secret_key and s.stripe_price_pro_monthly)


@router.post("/checkout")
async def create_checkout_session(
    session: DbSession,
    user: CurrentDbUser,
) -> dict[str, Any]:
    settings = get_settings()
    if not _billing_configured():
        raise AppError(
            503,
            "BILLING_NOT_CONFIGURED",
            "Stripe billing is not configured on this server.",
        )
    sub = await ensure_subscription(session, user.id, settings)
    stripe_client.ensure_stripe_customer(settings, user, sub)
    url = stripe_client.create_checkout_session(settings=settings, user=user, sub=sub)
    await session.commit()
    return {"data": CheckoutSessionOut(url=url).model_dump(mode="json")}


@router.post("/portal")
async def create_portal_session(
    session: DbSession,
    user: CurrentDbUser,
) -> dict[str, Any]:
    settings = get_settings()
    if not _billing_configured():
        raise AppError(
            503,
            "BILLING_NOT_CONFIGURED",
            "Stripe billing is not configured on this server.",
        )
    sub = await ensure_subscription(session, user.id, settings)
    if not sub.stripe_customer_id:
        raise AppError(
            422,
            "NO_STRIPE_CUSTOMER",
            "Complete checkout first or contact support.",
        )
    url = stripe_client.create_portal_session(
        settings=settings,
        stripe_customer_id=sub.stripe_customer_id,
    )
    return {"data": PortalSessionOut(url=url).model_dump(mode="json")}


@router.get("/subscription")
async def get_subscription(
    session: DbSession,
    user: CurrentDbUser,
) -> dict[str, Any]:
    settings = get_settings()
    sub = await ensure_subscription(session, user.id, settings)
    now = utc_now()
    out = SubscriptionOut(
        id=sub.id,
        user_id=sub.user_id,
        plan=sub.plan,
        status=sub.status,
        trial_ends_at=sub.trial_ends_at,
        current_period_end=sub.current_period_end,
        past_due_since=sub.past_due_since,
        cancel_at_period_end=sub.cancel_at_period_end,
        stripe_customer_id=sub.stripe_customer_id,
        has_active_entitlement=is_entitled(sub, now),
    )
    return {"data": out.model_dump(mode="json", by_alias=True)}
