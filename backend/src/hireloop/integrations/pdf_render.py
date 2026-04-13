"""Factory that produces a configured PdfRenderClient from settings."""

from functools import lru_cache

from hireloop.config import get_settings
from hireloop.core.cv_optimizer.render_client import PdfRenderClient


@lru_cache(maxsize=1)
def get_pdf_render_client() -> PdfRenderClient:
    settings = get_settings()
    return PdfRenderClient(
        base_url=settings.pdf_render_url,
        api_key=settings.pdf_render_api_key,
        timeout_s=settings.pdf_render_timeout_s,
    )
