"""Onboarding hook seeds the default 15-company scan config."""

import pytest
from sqlalchemy import delete, select

from hireloop.core.scanner.default_config import DEFAULT_SCAN_CONFIG_NAME
from hireloop.db import get_session_factory
from hireloop.models.profile import Profile
from hireloop.models.scan_config import ScanConfig
from hireloop.models.user import User
from hireloop.schemas.profile import ProfileUpdate
from hireloop.services.profile import update_profile
from tests.conftest import FAKE_CLAIMS


async def _user():
    factory = get_session_factory()
    async with factory() as session:
        r = await session.execute(
            select(User).where(User.cognito_sub == FAKE_CLAIMS["sub"])
        )
        return r.scalar_one_or_none()


@pytest.mark.asyncio
async def test_onboarding_done_seeds_default_scan_config():
    user = await _user()
    assert user is not None
    factory = get_session_factory()

    async with factory() as session:
        await session.execute(delete(ScanConfig).where(ScanConfig.user_id == user.id))
        pr = await session.execute(
            select(Profile).where(Profile.user_id == user.id)
        )
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

    async with factory() as session:
        pr = await session.execute(
            select(Profile).where(Profile.user_id == user.id)
        )
        profile = pr.scalar_one()
        await update_profile(
            session,
            profile,
            ProfileUpdate(target_roles=["senior engineer"], target_locations=["remote"]),
        )
        await session.commit()

    async with factory() as session:
        configs = (
            (
                await session.execute(
                    select(ScanConfig).where(
                        ScanConfig.user_id == user.id,
                        ScanConfig.name == DEFAULT_SCAN_CONFIG_NAME,
                    )
                )
            )
            .scalars()
            .all()
        )
    assert len(configs) == 1
    config = configs[0]
    assert len(config.companies) == 15
    assert config.schedule == "manual"
