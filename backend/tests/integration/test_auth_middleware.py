from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_auth_me_requires_token(client: AsyncClient) -> None:
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "UNAUTHENTICATED"


@pytest.mark.asyncio
async def test_auth_me_returns_user_when_token_valid(client: AsyncClient) -> None:
    fake_claims = {
        "sub": "cognito-sub-abc",
        "email": "test@example.com",
        "custom:user_id": "",
        "custom:role": "user",
        "custom:subscription_tier": "trial",
    }

    with patch(
        "hireloop.integrations.cognito.CognitoJwtVerifier.verify",
        new=AsyncMock(return_value=fake_claims),
    ):
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer fake-token"},
        )

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["email"] == "test@example.com"
    assert body["cognito_sub"] == "cognito-sub-abc"
