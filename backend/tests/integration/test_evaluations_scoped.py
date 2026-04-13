from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from hireloop.main import app
from tests.conftest import _verify_token


@pytest.mark.asyncio
async def test_user_cannot_read_other_users_evaluation(
    second_test_user, seeded_evaluation_for_user_a
):
    with patch(
        "hireloop.integrations.cognito.CognitoJwtVerifier.verify",
        new=AsyncMock(side_effect=_verify_token),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(
                f"/api/v1/evaluations/{seeded_evaluation_for_user_a.id}",
                headers=second_test_user["headers"],
            )
    assert resp.status_code == 404
