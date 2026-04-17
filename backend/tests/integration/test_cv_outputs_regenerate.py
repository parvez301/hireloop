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

_R2 = json.dumps(
    {
        "tailored_md": "v2",
        "changes_summary": "v2",
        "keywords_injected": [],
        "sections_reordered": [],
    }
)


@pytest.mark.asyncio
@respx.mock
async def test_regenerate_produces_new_row(auth_headers, seeded_cv_output):
    with mock_aws():
        get_settings.cache_clear()
        get_s3_client.cache_clear()
        settings = get_settings()
        boto3.client("s3", region_name=settings.aws_region).create_bucket(Bucket=settings.aws_s3_bucket)
        with (
            patch(
                "hireloop.integrations.cognito.CognitoJwtVerifier.verify",
                new=AsyncMock(side_effect=_verify_token),
            ),
            fake_anthropic({"MASTER RESUME": _R2}),
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post(
                    f"/api/v1/cv-outputs/{seeded_cv_output.id}/regenerate",
                    json={"feedback": "emphasize leadership"},
                    headers=auth_headers,
                )
    assert resp.status_code == 200
    body = resp.json()["data"]
    assert body["id"] != str(seeded_cv_output.id)
    assert body["pdf_s3_key"] != seeded_cv_output.pdf_s3_key
