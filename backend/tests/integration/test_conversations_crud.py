from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from hireloop.main import app
from tests.conftest import FAKE_CLAIMS


@pytest.mark.asyncio
async def test_create_list_get_delete(auth_headers):
    with patch(
        "hireloop.integrations.cognito.CognitoJwtVerifier.verify",
        new=AsyncMock(return_value=FAKE_CLAIMS),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r1 = await client.post(
                "/api/v1/conversations", json={"title": "Test chat"}, headers=auth_headers
            )
            assert r1.status_code == 200
            conv_id = r1.json()["data"]["id"]

            r2 = await client.get("/api/v1/conversations", headers=auth_headers)
            assert r2.status_code == 200
            ids = [c["id"] for c in r2.json()["data"]]
            assert conv_id in ids

            r3 = await client.get(f"/api/v1/conversations/{conv_id}", headers=auth_headers)
            assert r3.status_code == 200
            assert r3.json()["data"]["conversation"]["id"] == conv_id

            r4 = await client.delete(f"/api/v1/conversations/{conv_id}", headers=auth_headers)
            assert r4.status_code == 204

            r5 = await client.get(f"/api/v1/conversations/{conv_id}", headers=auth_headers)
            assert r5.status_code == 404
