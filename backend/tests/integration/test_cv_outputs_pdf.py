from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from hireloop.main import app
from tests.conftest import _verify_token


@pytest.mark.asyncio
async def test_get_pdf_returns_redirect(auth_headers, seeded_cv_output):
    with patch(
        "hireloop.integrations.cognito.CognitoJwtVerifier.verify",
        new=AsyncMock(side_effect=_verify_token),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test", follow_redirects=False
        ) as client:
            resp = await client.get(
                f"/api/v1/cv-outputs/{seeded_cv_output.id}/pdf",
                headers=auth_headers,
            )
    assert resp.status_code == 302
    loc = resp.headers["location"]
    assert "amazonaws.com" in loc or "localhost" in loc or "127.0.0.1" in loc
