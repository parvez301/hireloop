"""Integration tests for POST /onboarding/first-evaluation."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

FAKE_CLAIMS = {
    "sub": "cognito-sub-onboarding-first-eval",
    "email": "first-eval@example.com",
    "custom:role": "user",
    "custom:subscription_tier": "trial",
}


@pytest.mark.asyncio
async def test_first_evaluation_text_input_persists_and_returns_envelope(
    client: AsyncClient,
) -> None:
    fake_parsed_ret = AsyncMock()
    fake_parsed_ret.content_hash = "hash-1"
    fake_parsed_ret.url = None
    fake_parsed_ret.title = "Senior Backend Engineer"
    fake_parsed_ret.company = "Acme"
    fake_parsed_ret.location = "Remote"
    fake_parsed_ret.salary_min = None
    fake_parsed_ret.salary_max = None
    fake_parsed_ret.employment_type = "full_time"
    fake_parsed_ret.seniority = "senior"
    fake_parsed_ret.description_md = "Senior backend role..."
    fake_parsed_ret.requirements_json = {"skills": ["Python"]}

    fake_parsed = AsyncMock(return_value=fake_parsed_ret)

    fake_eval = AsyncMock(
        return_value={
            "id": "eval-id-1",
            "overall_score": 82,
            "grade": "B+",
            "strengths": [],
            "gaps": [],
            "job_id": None,
        }
    )

    with (
        patch(
            "hireloop.integrations.cognito.CognitoJwtVerifier.verify",
            new=AsyncMock(return_value=FAKE_CLAIMS),
        ),
        patch(
            "hireloop.api.onboarding.parse_description",
            new=fake_parsed,
        ),
        patch(
            "hireloop.api.onboarding.run_first_evaluation",
            new=fake_eval,
        ),
    ):
        # First, give this user a resume so the endpoint doesn't 409.
        await client.post(
            "/api/v1/profile/resume-text",
            headers={"Authorization": "Bearer fake"},
            json={"text": "# Resume\nSenior Backend Engineer, 8 yrs."},
        )
        response = await client.post(
            "/api/v1/onboarding/first-evaluation",
            headers={"Authorization": "Bearer fake"},
            json={"job_input": {"type": "text", "value": "Senior backend role..."}},
        )

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["evaluation"]["id"] == "eval-id-1"
    assert body["job"]["title"] == "Senior Backend Engineer"


@pytest.mark.asyncio
async def test_first_evaluation_requires_resume(client: AsyncClient) -> None:
    claims = {
        **FAKE_CLAIMS,
        "sub": "cognito-sub-first-eval-noresume",
        "email": "nr@example.com",
    }
    with patch(
        "hireloop.integrations.cognito.CognitoJwtVerifier.verify",
        new=AsyncMock(return_value=claims),
    ):
        await client.get("/api/v1/profile", headers={"Authorization": "Bearer fake"})
        response = await client.post(
            "/api/v1/onboarding/first-evaluation",
            headers={"Authorization": "Bearer fake"},
            json={"job_input": {"type": "text", "value": "..."}},
        )
    assert response.status_code == 409
    body = response.json()
    # The project uses either envelope {"error": {...}} or FastAPI {"detail": ...}; accept either.
    code = body.get("error", {}).get("code") or body.get("detail")
    assert code == "RESUME_REQUIRED"
