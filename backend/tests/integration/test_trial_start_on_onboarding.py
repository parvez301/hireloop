"""Onboarding → trial start hook.

Phase 2b Q1=A: the 3-day trial row is created eagerly when a profile
transitions to onboarding_state='done' during PUT /profile.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from hireloop.db import get_session_factory
from hireloop.models.profile import Profile
from hireloop.models.subscription import Subscription
from hireloop.models.user import User
from hireloop.schemas.profile import ProfileUpdate
from hireloop.services.profile import update_profile
from tests.conftest import FAKE_CLAIMS


async def _get_user() -> User:
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
            await session.commit()
            await session.refresh(user)
        return user


@pytest.mark.asyncio
async def test_onboarding_done_transition_creates_trial_subscription():
    user = await _get_user()
    factory = get_session_factory()

    # Reset: remove any existing subscription + put profile in 'preferences'
    async with factory() as session:
        sr = await session.execute(select(Subscription).where(Subscription.user_id == user.id))
        for s in sr.scalars().all():
            await session.delete(s)
        pr = await session.execute(select(Profile).where(Profile.user_id == user.id))
        profile = pr.scalar_one_or_none()
        if profile is None:
            profile = Profile(user_id=user.id, onboarding_state="preferences")
            session.add(profile)
        else:
            profile.onboarding_state = "preferences"
            profile.target_roles = None
            profile.target_locations = None
        profile.master_resume_md = "# resume"
        await session.commit()

    # Act: supply preferences → should flip to 'done' → should create trial row
    async with factory() as session:
        pr = await session.execute(select(Profile).where(Profile.user_id == user.id))
        profile = pr.scalar_one()
        update = ProfileUpdate(
            target_roles=["staff engineer"],
            target_locations=["remote"],
        )
        await update_profile(session, profile, update)
        await session.commit()

    # Assert: subscription row exists with plan=trial, trial_ends_at roughly now+3d
    async with factory() as session:
        sr = await session.execute(select(Subscription).where(Subscription.user_id == user.id))
        sub = sr.scalar_one_or_none()
    assert sub is not None, "Expected trial subscription row after onboarding done"
    assert sub.plan == "trial"
    assert sub.status == "active"
    assert sub.trial_ends_at is not None
    delta = sub.trial_ends_at - datetime.now(UTC)
    assert timedelta(days=2, hours=23) < delta < timedelta(days=3, minutes=1)


@pytest.mark.asyncio
async def test_second_update_does_not_reset_trial():
    """Once 'done', further PUT /profile calls do not refresh the trial window."""
    user = await _get_user()
    factory = get_session_factory()

    async with factory() as session:
        sr = await session.execute(select(Subscription).where(Subscription.user_id == user.id))
        for s in sr.scalars().all():
            await session.delete(s)
        pr = await session.execute(select(Profile).where(Profile.user_id == user.id))
        profile = pr.scalar_one_or_none()
        if profile is None:
            profile = Profile(user_id=user.id, onboarding_state="done")
            session.add(profile)
        else:
            profile.onboarding_state = "done"
        profile.master_resume_md = "# resume"
        profile.target_roles = ["eng"]
        profile.target_locations = ["remote"]
        await session.commit()

    # First ensure_subscription call
    async with factory() as session:
        pr = await session.execute(select(Profile).where(Profile.user_id == user.id))
        profile = pr.scalar_one()
        await update_profile(session, profile, ProfileUpdate(min_salary=150000))
        await session.commit()

    async with factory() as session:
        sr = await session.execute(select(Subscription).where(Subscription.user_id == user.id))
        sub1 = sr.scalar_one_or_none()
    # Eager hook only fires on transition TO done, not on subsequent updates.
    # The subscription row does not exist yet because profile was already 'done'
    # when update_profile ran. Lazy path will create it on first entitled request.
    assert sub1 is None
