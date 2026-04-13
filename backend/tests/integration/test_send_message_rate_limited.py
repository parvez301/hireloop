from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from hireloop.main import app
from tests.conftest import FAKE_CLAIMS
from tests.fixtures.fake_anthropic import fake_anthropic
from tests.fixtures.fake_gemini import fake_gemini


@pytest.mark.asyncio
async def test_rate_limit_kicks_in_after_10_messages(auth_headers, seed_conversation):
    with (
        patch(
            "hireloop.integrations.cognito.CognitoJwtVerifier.verify",
            new=AsyncMock(return_value=FAKE_CLAIMS),
        ),
        fake_gemini({"hello": "CAREER_GENERAL"}),
        fake_anthropic({"User message": "Hi! How can I help with your career today?"}),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            for i in range(10):
                r = await client.post(
                    f"/api/v1/conversations/{seed_conversation.id}/messages",
                    json={"content": f"hello {i}"},
                    headers=auth_headers,
                )
                assert r.status_code == 200
            r = await client.post(
                f"/api/v1/conversations/{seed_conversation.id}/messages",
                json={"content": "hello 11"},
                headers=auth_headers,
            )
    assert r.status_code == 429
