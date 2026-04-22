"""Integration tests for POST /profile/resume-text (paste-text fallback)."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

FAKE_CLAIMS = {
    "sub": "cognito-sub-resume-text",
    "email": "resume-text@example.com",
    "custom:role": "user",
    "custom:subscription_tier": "trial",
}


@pytest.mark.asyncio
async def test_resume_text_happy_path_parses_and_advances_to_done(
    client: AsyncClient,
) -> None:
    with patch(
        "hireloop.integrations.cognito.CognitoJwtVerifier.verify",
        new=AsyncMock(return_value=FAKE_CLAIMS),
    ):
        await client.get("/api/v1/profile", headers={"Authorization": "Bearer fake"})
        response = await client.post(
            "/api/v1/profile/resume-text",
            headers={"Authorization": "Bearer fake"},
            json={
                "text": (
                    "# Jane Doe\n\nSenior Backend Engineer, 8 years.\n\n"
                    "## Experience\n\nAcme Corp, 2020-present.\n"
                )
            },
        )

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["onboarding_state"] == "done"


@pytest.mark.asyncio
async def test_resume_text_rejects_empty_body(client: AsyncClient) -> None:
    claims = {
        **FAKE_CLAIMS,
        "sub": "cognito-sub-resume-text-empty",
        "email": "empty@example.com",
    }
    with patch(
        "hireloop.integrations.cognito.CognitoJwtVerifier.verify",
        new=AsyncMock(return_value=claims),
    ):
        response = await client.post(
            "/api/v1/profile/resume-text",
            headers={"Authorization": "Bearer fake"},
            json={"text": ""},
        )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_resume_text_rejects_oversize(client: AsyncClient) -> None:
    claims = {
        **FAKE_CLAIMS,
        "sub": "cognito-sub-resume-text-big",
        "email": "big@example.com",
    }
    with patch(
        "hireloop.integrations.cognito.CognitoJwtVerifier.verify",
        new=AsyncMock(return_value=claims),
    ):
        response = await client.post(
            "/api/v1/profile/resume-text",
            headers={"Authorization": "Bearer fake"},
            json={"text": "a" * 50_001},
        )
    assert response.status_code == 422
