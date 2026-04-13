"""Subscription entitlement and agent-facing subscription display."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hireloop.config import Settings
from hireloop.models.subscription import Subscription

AgentSubscriptionStatus = Literal["trial", "active", "expired"]

PAST_DUE_GRACE_DAYS = 3


def utc_now() -> datetime:
    return datetime.now(UTC)


async def get_subscription_for_user(session: AsyncSession, user_id: UUID) -> Subscription | None:
    r = await session.execute(select(Subscription).where(Subscription.user_id == user_id))
    return r.scalar_one_or_none()


async def ensure_subscription(
    session: AsyncSession, user_id: UUID, settings: Settings
) -> Subscription:
    """Ensure a subscription row exists with an in-app trial window when missing."""
    sub = await get_subscription_for_user(session, user_id)
    if sub is not None:
        return sub
    now = utc_now()
    sub = Subscription(
        user_id=user_id,
        plan="trial",
        status="active",
        trial_ends_at=now + timedelta(days=settings.trial_period_days),
    )
    session.add(sub)
    await session.flush()
    return sub


def is_entitled(sub: Subscription, now: datetime) -> bool:
    """Whether the user may access paywalled (LLM) features.

    Rules:
    - in-app trial window is open → entitled
    - Stripe subscription is active/trialing → entitled
    - Stripe subscription is past_due, but within PAST_DUE_GRACE_DAYS of
      past_due_since → entitled (dunning grace window)
    - else → not entitled
    """
    if sub.trial_ends_at is not None and now < sub.trial_ends_at:
        return True
    if sub.stripe_subscription_id and sub.status in ("active", "trialing"):
        return True
    if (
        sub.stripe_subscription_id
        and sub.status == "past_due"
        and sub.past_due_since is not None
        and now < sub.past_due_since + timedelta(days=PAST_DUE_GRACE_DAYS)
    ):
        return True
    return False


def agent_subscription_fields(
    sub: Subscription, now: datetime
) -> tuple[AgentSubscriptionStatus, int | None]:
    """Map DB subscription to AgentState (user already passed paywall)."""
    if sub.trial_ends_at is not None and now < sub.trial_ends_at:
        return "trial", trial_days_remaining(sub.trial_ends_at, now)
    if sub.stripe_subscription_id:
        if sub.status == "trialing":
            return "trial", trial_days_remaining(sub.trial_ends_at, now)
        if sub.status == "active":
            return "active", None
    return "expired", None


def trial_days_remaining(trial_ends_at: datetime | None, now: datetime) -> int | None:
    if trial_ends_at is None or trial_ends_at <= now:
        return None
    delta = trial_ends_at - now
    return max(0, int(delta.total_seconds() // 86400))
