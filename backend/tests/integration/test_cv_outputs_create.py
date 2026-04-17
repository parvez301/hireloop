import json
from unittest.mock import AsyncMock, patch

import boto3
import pytest
import respx
from httpx import ASGITransport, AsyncClient
from moto import mock_aws

from hireloop.config import get_settings
from hireloop.integrations.s3 import get_s3_client
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
    with mock_aws():
        get_settings.cache_clear()
        get_s3_client.cache_clear()
        settings = get_settings()
        boto3.client("s3", region_name=settings.aws_region).create_bucket(
            Bucket=settings.aws_s3_bucket
        )
        with (
            patch(
                "hireloop.integrations.cognito.CognitoJwtVerifier.verify",
                new=AsyncMock(side_effect=_verify_token),
            ),
            fake_anthropic({"MASTER RESUME": _RESPONSE}),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/v1/cv-outputs",
                    json={"job_id": str(seeded_evaluation_for_user_a.job_id)},
                    headers=auth_headers,
                )
    assert resp.status_code == 200
    assert resp.json()["data"]["tailored_md"].startswith("# Jane")
    assert "changes_summary" in resp.json()["data"]
