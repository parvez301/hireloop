import json
from unittest.mock import AsyncMock, patch

import pytest
import respx
from httpx import ASGITransport, AsyncClient, Response

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
    respx.post("http://localhost:4000/render").mock(
        return_value=Response(
            200,
            json={
                "success": True,
                "s3_key": "cv-outputs/t/new.pdf",
                "s3_bucket": "b",
                "page_count": 1,
                "size_bytes": 5,
                "render_ms": 1,
            },
        )
    )
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
