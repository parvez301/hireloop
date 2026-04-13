from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from hireloop.main import app
from tests.conftest import FAKE_CLAIMS
from tests.fixtures.fake_anthropic import fake_anthropic
from tests.fixtures.fake_gemini import fake_gemini


@pytest.mark.asyncio
async def test_stream_emits_classifier_and_done(auth_headers, seed_profile, seed_conversation):
    with (
        patch(
            "hireloop.integrations.cognito.CognitoJwtVerifier.verify",
            new=AsyncMock(return_value=FAKE_CLAIMS),
        ),
        fake_gemini({"hello": "CAREER_GENERAL"}),
        fake_anthropic({"User message": "Hello!"}),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            post_resp = await client.post(
                f"/api/v1/conversations/{seed_conversation.id}/messages",
                json={"content": "hello world"},
                headers=auth_headers,
            )
            assert post_resp.status_code == 200
            msg_id = post_resp.json()["data"]["id"]

            stream_resp = await client.get(
                f"/api/v1/conversations/{seed_conversation.id}/stream",
                params={"pending": msg_id},
                headers=auth_headers,
            )

    assert stream_resp.status_code == 200
    body = stream_resp.text
    assert "event: done" in body
