import pytest
import respx
from httpx import Response

from hireloop.core.cv_optimizer.render_client import PdfRenderClient, PdfRenderError


@pytest.mark.asyncio
@respx.mock
async def test_render_client_success():
    respx.post("http://localhost:4000/render").mock(
        return_value=Response(
            200,
            json={
                "success": True,
                "s3_key": "cv-outputs/u/1.pdf",
                "s3_bucket": "hireloop-dev-assets",
                "page_count": 2,
                "size_bytes": 123456,
                "render_ms": 1500,
            },
        )
    )
    client = PdfRenderClient(
        base_url="http://localhost:4000",
        api_key="test-key",
        timeout_s=10.0,
    )
    result = await client.render(
        markdown="# Jane",
        template="resume",
        user_id="usr_test",
        output_key="cv-outputs/u/1.pdf",
    )
    assert result.s3_key == "cv-outputs/u/1.pdf"
    assert result.page_count == 2


@pytest.mark.asyncio
@respx.mock
async def test_render_client_failure_raises():
    respx.post("http://localhost:4000/render").mock(
        return_value=Response(500, json={"success": False, "error": "CHROMIUM_CRASH"})
    )
    client = PdfRenderClient(
        base_url="http://localhost:4000",
        api_key="test-key",
        timeout_s=10.0,
    )
    with pytest.raises(PdfRenderError):
        await client.render(
            markdown="x",
            template="resume",
            user_id="u",
            output_key="k",
        )
