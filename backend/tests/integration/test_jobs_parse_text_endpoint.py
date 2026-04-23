"""Integration tests for POST /jobs/parse-text (paste-text fallback)."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

FAKE_CLAIMS = {
    "sub": "cognito-sub-jobs-parse-text",
    "email": "jobs-parse-text@example.com",
    "custom:role": "user",
    "custom:subscription_tier": "trial",
}

SAMPLE_JD = """Senior Backend Engineer at Acme Corp.

Requirements:
- 5+ years Python
- AWS, distributed systems
- Remote OK

Comp: $180k-$220k base.
"""


@pytest.mark.asyncio
async def test_parse_text_happy_path(client: AsyncClient) -> None:
    fake_parsed = AsyncMock()
    fake_parsed.return_value.content_hash = "abc123"
    fake_parsed.return_value.url = "https://example.com/jobs/1"
    fake_parsed.return_value.title = "Senior Backend Engineer"
    fake_parsed.return_value.company = "Acme Corp"
    fake_parsed.return_value.location = "Remote"
    fake_parsed.return_value.salary_min = 180_000
    fake_parsed.return_value.salary_max = 220_000
    fake_parsed.return_value.employment_type = "full_time"
    fake_parsed.return_value.seniority = "senior"
    fake_parsed.return_value.description_md = SAMPLE_JD
    fake_parsed.return_value.requirements_json = {"skills": ["Python", "AWS"]}

    with (
        patch(
            "hireloop.integrations.cognito.CognitoJwtVerifier.verify",
            new=AsyncMock(return_value=FAKE_CLAIMS),
        ),
        patch(
            "hireloop.api.jobs.parse_description",
            new=fake_parsed,
        ),
    ):
        await client.get("/api/v1/profile", headers={"Authorization": "Bearer fake"})
        response = await client.post(
            "/api/v1/jobs/parse-text",
            headers={"Authorization": "Bearer fake"},
            json={"text": SAMPLE_JD, "source_url": "https://example.com/jobs/1"},
        )

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["title"] == "Senior Backend Engineer"
    assert body["url"] == "https://example.com/jobs/1"


@pytest.mark.asyncio
async def test_parse_text_rejects_empty_text(client: AsyncClient) -> None:
    claims = {
        **FAKE_CLAIMS,
        "sub": "cognito-sub-jobs-parse-empty",
        "email": "jobs-parse-empty@example.com",
    }
    with patch(
        "hireloop.integrations.cognito.CognitoJwtVerifier.verify",
        new=AsyncMock(return_value=claims),
    ):
        response = await client.post(
            "/api/v1/jobs/parse-text",
            headers={"Authorization": "Bearer fake"},
            json={"text": ""},
        )
    assert response.status_code == 422
