from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

FAKE_CLAIMS = {
    "sub": "cognito-sub-gdpr",
    "email": "gdpr@example.com",
    "custom:role": "user",
    "custom:subscription_tier": "trial",
}


@pytest.mark.asyncio
async def test_export_returns_user_data_as_json(client: AsyncClient) -> None:
    with patch(
        "hireloop.integrations.cognito.CognitoJwtVerifier.verify",
        new=AsyncMock(return_value=FAKE_CLAIMS),
    ):
        await client.get("/api/v1/profile", headers={"Authorization": "Bearer fake"})

        response = await client.post(
            "/api/v1/profile/export",
            headers={"Authorization": "Bearer fake"},
        )

    assert response.status_code == 200
    body = response.json()["data"]
    assert "user" in body
    assert "profile" in body
    assert body["user"]["email"] == "gdpr@example.com"


@pytest.mark.asyncio
async def test_delete_account_removes_user(client: AsyncClient) -> None:
    with patch(
        "hireloop.integrations.cognito.CognitoJwtVerifier.verify",
        new=AsyncMock(return_value=FAKE_CLAIMS),
    ):
        await client.get("/api/v1/profile", headers={"Authorization": "Bearer fake"})
        response = await client.delete(
            "/api/v1/profile",
            headers={"Authorization": "Bearer fake"},
        )

    assert response.status_code == 204
