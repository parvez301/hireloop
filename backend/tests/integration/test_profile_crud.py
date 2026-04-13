from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

FAKE_CLAIMS = {
    "sub": "cognito-sub-xyz",
    "email": "crud@example.com",
    "custom:role": "user",
    "custom:subscription_tier": "trial",
}


@pytest.mark.asyncio
async def test_get_profile_creates_empty_profile_on_first_access(client: AsyncClient) -> None:
    fresh_claims = {
        **FAKE_CLAIMS,
        "sub": "cognito-sub-empty-profile-test",
        "email": "empty-profile-test@example.com",
    }
    with patch(
        "hireloop.integrations.cognito.CognitoJwtVerifier.verify",
        new=AsyncMock(return_value=fresh_claims),
    ):
        response = await client.get(
            "/api/v1/profile",
            headers={"Authorization": "Bearer fake"},
        )
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["onboarding_state"] == "resume_upload"
    assert body["target_roles"] is None


@pytest.mark.asyncio
async def test_put_profile_updates_preferences(client: AsyncClient) -> None:
    with patch(
        "hireloop.integrations.cognito.CognitoJwtVerifier.verify",
        new=AsyncMock(return_value=FAKE_CLAIMS),
    ):
        await client.get("/api/v1/profile", headers={"Authorization": "Bearer fake"})

        response = await client.put(
            "/api/v1/profile",
            headers={"Authorization": "Bearer fake"},
            json={
                "target_roles": ["Senior Backend Engineer"],
                "target_locations": ["Remote", "Dubai"],
                "min_salary": 120000,
                "linkedin_url": "https://linkedin.com/in/test",
            },
        )

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["target_roles"] == ["Senior Backend Engineer"]
    assert body["target_locations"] == ["Remote", "Dubai"]
    assert body["min_salary"] == 120000
    assert body["onboarding_state"] in ("preferences", "done")


@pytest.mark.asyncio
async def test_put_profile_rejects_negative_salary(client: AsyncClient) -> None:
    with patch(
        "hireloop.integrations.cognito.CognitoJwtVerifier.verify",
        new=AsyncMock(return_value=FAKE_CLAIMS),
    ):
        response = await client.put(
            "/api/v1/profile",
            headers={"Authorization": "Bearer fake"},
            json={"min_salary": -1},
        )
    assert response.status_code == 422
