"""Applications CRUD + non-paywalled property."""

import hashlib
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select

from hireloop.db import get_session_factory
from hireloop.main import app
from hireloop.models.application import Application
from hireloop.models.job import Job
from hireloop.models.subscription import Subscription
from hireloop.models.user import User
from tests.conftest import FAKE_CLAIMS


async def _uid() -> UUID:
    factory = get_session_factory()
    async with factory() as s:
        r = await s.execute(select(User).where(User.cognito_sub == FAKE_CLAIMS["sub"]))
        return r.scalar_one().id


async def _seed_job() -> UUID:
    factory = get_session_factory()
    async with factory() as session:
        h = hashlib.sha256(f"app-test-{uuid4()}".encode()).hexdigest()
        job = Job(
            content_hash=h,
            title="Saved Job",
            description_md="x",
            requirements_json={},
            source="manual",
        )
        session.add(job)
        await session.commit()
        return job.id


async def _clear_apps() -> None:
    factory = get_session_factory()
    uid = await _uid()
    async with factory() as session:
        await session.execute(delete(Application).where(Application.user_id == uid))
        await session.commit()


@pytest.mark.asyncio
async def test_applications_crud_happy_path(auth_headers, seed_profile):
    await _clear_apps()
    jid = await _seed_job()

    with patch(
        "hireloop.integrations.cognito.CognitoJwtVerifier.verify",
        new=AsyncMock(return_value=FAKE_CLAIMS),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            r1 = await client.post(
                "/api/v1/applications",
                json={"job_id": str(jid), "notes": "looks good"},
                headers=auth_headers,
            )
            assert r1.status_code == 201
            app_id = r1.json()["data"]["id"]
            assert r1.json()["data"]["status"] == "saved"

            r2 = await client.put(
                f"/api/v1/applications/{app_id}",
                json={"status": "applied"},
                headers=auth_headers,
            )
            assert r2.status_code == 200
            body = r2.json()["data"]
            assert body["status"] == "applied"
            assert body["applied_at"] is not None

            r3 = await client.get("/api/v1/applications", headers=auth_headers)
            assert r3.status_code == 200
            assert any(a["id"] == app_id for a in r3.json()["data"])

            r4 = await client.delete(
                f"/api/v1/applications/{app_id}", headers=auth_headers
            )
            assert r4.status_code == 204


@pytest.mark.asyncio
async def test_applications_unique_on_job_per_user(auth_headers, seed_profile):
    await _clear_apps()
    jid = await _seed_job()

    with patch(
        "hireloop.integrations.cognito.CognitoJwtVerifier.verify",
        new=AsyncMock(return_value=FAKE_CLAIMS),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            r1 = await client.post(
                "/api/v1/applications",
                json={"job_id": str(jid)},
                headers=auth_headers,
            )
            assert r1.status_code == 201
            r2 = await client.post(
                "/api/v1/applications",
                json={"job_id": str(jid)},
                headers=auth_headers,
            )
            assert r2.status_code == 409


@pytest.mark.asyncio
async def test_applications_survive_expired_trial(auth_headers, seed_profile):
    """Trial-expired users can still CRUD applications (non-paywalled)."""
    await _clear_apps()
    jid = await _seed_job()

    factory = get_session_factory()
    uid = await _uid()
    async with factory() as session:
        sub = (
            await session.execute(
                select(Subscription).where(Subscription.user_id == uid)
            )
        ).scalar_one_or_none()
        if sub is None:
            sub = Subscription(user_id=uid, plan="trial", status="active")
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
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/v1/applications",
                    json={"job_id": str(jid)},
                    headers=auth_headers,
                )
        # Non-paywalled: must be 201, not 403
        assert resp.status_code == 201
    finally:
        async with factory() as session:
            sub = (
                await session.execute(
                    select(Subscription).where(Subscription.user_id == uid)
                )
            ).scalar_one_or_none()
            if sub is not None:
                sub.trial_ends_at = datetime.now(UTC) + timedelta(days=30)
                await session.commit()
