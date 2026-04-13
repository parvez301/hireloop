from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from hireloop.main import app
from tests.conftest import FAKE_CLAIMS
from tests.fixtures.fake_gemini import fake_gemini


@pytest.mark.asyncio
async def test_off_topic_short_circuits(auth_headers, seed_conversation):
    with (
        patch(
            "hireloop.integrations.cognito.CognitoJwtVerifier.verify",
            new=AsyncMock(return_value=FAKE_CLAIMS),
        ),
        fake_gemini({"pasta": "OFF_TOPIC"}),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                f"/api/v1/conversations/{seed_conversation.id}/messages",
                json={"content": "How do I cook pasta?"},
                headers=auth_headers,
            )
    assert resp.status_code == 200
    body = resp.json()["data"]
    assert "hireloop" in body["content"].lower()
    assert body["cards"] in (None, [])
