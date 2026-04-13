"""Lightweight smoke: new Phase 2d list routes respond."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from hireloop.main import app
from tests.conftest import FAKE_CLAIMS


@pytest.mark.asyncio
async def test_phase2d_list_routes_ok(auth_headers, seed_profile):
    with patch(
        "hireloop.integrations.cognito.CognitoJwtVerifier.verify",
        new=AsyncMock(return_value=FAKE_CLAIMS),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r1 = await client.get("/api/v1/interview-preps", headers=auth_headers)
            r2 = await client.get("/api/v1/negotiations", headers=auth_headers)
            r3 = await client.get("/api/v1/star-stories", headers=auth_headers)
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r3.status_code == 200
