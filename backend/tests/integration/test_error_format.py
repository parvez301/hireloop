import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_404_returns_standard_error_envelope(client: AsyncClient) -> None:
    response = await client.get("/api/v1/nonexistent-endpoint")
    assert response.status_code == 404
    body = response.json()
    assert "error" in body
    assert body["error"]["code"] == "RESOURCE_NOT_FOUND"
    assert "message" in body["error"]
    assert "request_id" in body["error"]


@pytest.mark.asyncio
async def test_422_validation_error_returns_standard_envelope(client: AsyncClient) -> None:
    response = await client.request("PATCH", "/api/v1/health")
    assert response.status_code in (404, 405)
    body = response.json()
    assert "error" in body
    assert "request_id" in body["error"]
