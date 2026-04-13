from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from hireloop.main import app
from tests.conftest import FAKE_CLAIMS
from tests.fixtures.fake_gemini import fake_gemini

_FAKE = (
    '{"title": "Staff Engineer", "company": "Acme", "location": "Remote", '
    '"salary_min": 180000, "salary_max": 220000, "employment_type": "full_time", '
    '"seniority": "staff", "description_md": "...", '
    '"requirements": {"skills": ["python", "go"], "years_experience": 8, "nice_to_haves": []}}'
)


@pytest.mark.asyncio
async def test_jobs_parse_from_description(auth_headers):
    with (
        patch(
            "hireloop.integrations.cognito.CognitoJwtVerifier.verify",
            new=AsyncMock(return_value=FAKE_CLAIMS),
        ),
        fake_gemini({"Staff": _FAKE}),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/jobs/parse",
                json={"description_md": "Staff Engineer at Acme. Remote. Python required." * 5},
                headers=auth_headers,
            )
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["title"] == "Staff Engineer"
    assert body["data"]["company"] == "Acme"


@pytest.mark.asyncio
async def test_jobs_parse_requires_exactly_one(auth_headers):
    with patch(
        "hireloop.integrations.cognito.CognitoJwtVerifier.verify",
        new=AsyncMock(return_value=FAKE_CLAIMS),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/jobs/parse",
                json={"description_md": "x", "url": "https://y.com"},
                headers=auth_headers,
            )
    assert resp.status_code == 422
