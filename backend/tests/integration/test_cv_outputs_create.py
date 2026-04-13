import json
from unittest.mock import AsyncMock, patch

import pytest
import respx
from httpx import ASGITransport, AsyncClient, Response

from hireloop.main import app
from tests.conftest import _verify_token
from tests.fixtures.fake_anthropic import fake_anthropic

_RESPONSE = json.dumps(
    {
        "tailored_md": "# Jane\n\n## Summary\nPayments engineer.",
        "changes_summary": "- Rewrote summary",
        "keywords_injected": ["payments"],
        "sections_reordered": [],
    }
)


@pytest.mark.asyncio
@respx.mock
async def test_cv_output_requires_prior_evaluation(auth_headers, seed_profile, random_job_id):
    with patch(
        "hireloop.integrations.cognito.CognitoJwtVerifier.verify",
        new=AsyncMock(side_effect=_verify_token),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/cv-outputs",
                json={"job_id": str(random_job_id)},
                headers=auth_headers,
            )
    assert resp.status_code == 422
    body = resp.json()
    assert "Evaluate" in body["error"]["message"] or body["error"]["code"] in (
        "JOB_PARSE_FAILED",
        "EVALUATION_REQUIRED",
    )


@pytest.mark.asyncio
@respx.mock
async def test_cv_output_happy_path(auth_headers, seed_profile, seeded_evaluation_for_user_a):
    respx.post("http://localhost:4000/render").mock(
        return_value=Response(
            200,
            json={
                "success": True,
                "s3_key": "cv-outputs/test/abc.pdf",
                "s3_bucket": "hireloop-dev-assets",
                "page_count": 1,
                "size_bytes": 50000,
                "render_ms": 900,
            },
        )
    )
    with (
        patch(
            "hireloop.integrations.cognito.CognitoJwtVerifier.verify",
            new=AsyncMock(side_effect=_verify_token),
        ),
        fake_anthropic({"MASTER RESUME": _RESPONSE}),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/cv-outputs",
                json={"job_id": str(seeded_evaluation_for_user_a.job_id)},
                headers=auth_headers,
            )
    assert resp.status_code == 200
    assert resp.json()["data"]["tailored_md"].startswith("# Jane")
    assert "changes_summary" in resp.json()["data"]
