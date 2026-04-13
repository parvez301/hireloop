"""Unit tests for subscription entitlement helpers."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from hireloop.models.subscription import Subscription
from hireloop.services.subscription import (
    agent_subscription_fields,
    is_entitled,
    trial_days_remaining,
)


def _sub(**kwargs: object) -> Subscription:
    uid = uuid4()
    sub = Subscription(
        user_id=uid,
        plan="trial",
        status="active",
    )
    for k, v in kwargs.items():
        setattr(sub, k, v)
    return sub


def test_is_entitled_in_app_trial() -> None:
    now = datetime(2026, 4, 10, 12, 0, tzinfo=UTC)
    sub = _sub(trial_ends_at=now + timedelta(days=1))
    assert is_entitled(sub, now) is True


def test_is_entitled_trial_expired_no_stripe() -> None:
    now = datetime(2026, 4, 10, 12, 0, tzinfo=UTC)
    sub = _sub(trial_ends_at=now - timedelta(days=1))
    assert is_entitled(sub, now) is False


def test_is_entitled_stripe_active() -> None:
    now = datetime(2026, 4, 10, 12, 0, tzinfo=UTC)
    sub = _sub(
        trial_ends_at=now - timedelta(days=10),
        stripe_subscription_id="sub_123",
        status="active",
    )
    assert is_entitled(sub, now) is True


def test_agent_subscription_fields_active() -> None:
    now = datetime(2026, 4, 10, 12, 0, tzinfo=UTC)
    sub = _sub(
        trial_ends_at=now - timedelta(days=1),
        stripe_subscription_id="sub_123",
        status="active",
    )
    st, days = agent_subscription_fields(sub, now)
    assert st == "active"
    assert days is None


def test_trial_days_remaining_midnight_utc() -> None:
    end = datetime(2026, 4, 12, 0, 0, tzinfo=UTC)
    now = datetime(2026, 4, 10, 12, 0, tzinfo=UTC)
    assert trial_days_remaining(end, now) == 1


def test_is_entitled_past_due_within_grace() -> None:
    """A paying user whose card declined is still entitled for 3 days."""
    now = datetime(2026, 4, 10, 12, 0, tzinfo=UTC)
    sub = _sub(
        trial_ends_at=now - timedelta(days=10),
        stripe_subscription_id="sub_123",
        status="past_due",
        past_due_since=now - timedelta(days=2),
    )
    assert is_entitled(sub, now) is True


def test_is_entitled_past_due_beyond_grace() -> None:
    """A paying user 4 days into past_due is revoked."""
    now = datetime(2026, 4, 10, 12, 0, tzinfo=UTC)
    sub = _sub(
        trial_ends_at=now - timedelta(days=10),
        stripe_subscription_id="sub_123",
        status="past_due",
        past_due_since=now - timedelta(days=4),
    )
    assert is_entitled(sub, now) is False


def test_is_entitled_past_due_without_stamp_is_denied() -> None:
    """past_due without past_due_since stamp cannot use grace — hard deny."""
    now = datetime(2026, 4, 10, 12, 0, tzinfo=UTC)
    sub = _sub(
        trial_ends_at=now - timedelta(days=10),
        stripe_subscription_id="sub_123",
        status="past_due",
        past_due_since=None,
    )
    assert is_entitled(sub, now) is False


def test_is_entitled_canceled_is_denied() -> None:
    now = datetime(2026, 4, 10, 12, 0, tzinfo=UTC)
    sub = _sub(
        trial_ends_at=now - timedelta(days=10),
        stripe_subscription_id="sub_123",
        status="canceled",
    )
    assert is_entitled(sub, now) is False
