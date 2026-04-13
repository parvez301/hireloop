"""Star stories CRUD — not paywalled."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from hireloop.main import app
from tests.conftest import FAKE_CLAIMS


@pytest.mark.asyncio
async def test_star_stories_crud(auth_headers, seed_profile):
    with patch(
        "hireloop.integrations.cognito.CognitoJwtVerifier.verify",
        new=AsyncMock(return_value=FAKE_CLAIMS),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r_create = await client.post(
                "/api/v1/star-stories",
                json={
                    "title": "Migrated DB",
                    "situation": "Oracle",
                    "task": "Move to Postgres",
                    "action": "Planned cutover",
                    "result": "Zero downtime",
                    "reflection": None,
                    "tags": ["postgres"],
                },
                headers=auth_headers,
            )
            assert r_create.status_code == 201
            sid = r_create.json()["data"]["id"]

            r_list = await client.get("/api/v1/star-stories", headers=auth_headers)
            assert r_list.status_code == 200
            assert any(x["id"] == sid for x in r_list.json()["data"])

            r_get = await client.get(f"/api/v1/star-stories/{sid}", headers=auth_headers)
            assert r_get.status_code == 200

            r_put = await client.put(
                f"/api/v1/star-stories/{sid}",
                json={"title": "Migrated DB v2"},
                headers=auth_headers,
            )
            assert r_put.status_code == 200
            assert r_put.json()["data"]["title"] == "Migrated DB v2"

            r_del = await client.delete(f"/api/v1/star-stories/{sid}", headers=auth_headers)
            assert r_del.status_code == 204

            r_gone = await client.get(f"/api/v1/star-stories/{sid}", headers=auth_headers)
            assert r_gone.status_code == 404


@pytest.mark.asyncio
async def test_star_stories_not_paywalled_when_trial_expired(auth_headers, seed_profile):
    from datetime import UTC, datetime, timedelta

    from sqlalchemy import select

    from hireloop.db import get_session_factory
    from hireloop.models.subscription import Subscription
    from hireloop.models.user import User

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
        with patch(
            "hireloop.integrations.cognito.CognitoJwtVerifier.verify",
            new=AsyncMock(return_value=FAKE_CLAIMS),
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                r = await client.get("/api/v1/star-stories", headers=auth_headers)
        assert r.status_code == 200
    finally:
        async with factory() as session:
            ur = await session.execute(select(User).where(User.cognito_sub == FAKE_CLAIMS["sub"]))
            user = ur.scalar_one()
            sr = await session.execute(select(Subscription).where(Subscription.user_id == user.id))
            sub = sr.scalar_one_or_none()
            if sub is not None:
                sub.trial_ends_at = datetime.now(UTC) + timedelta(days=30)
                await session.commit()
