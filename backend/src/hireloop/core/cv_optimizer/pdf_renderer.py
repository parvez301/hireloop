"""In-process WeasyPrint PDF renderer.

Replaces the HTTP-based `render_client.PdfRenderClient` with a direct
markdown → Jinja2 → WeasyPrint → S3 pipeline. The public `PdfRenderError`
class and `RenderResult` dataclass keep the same shape as the old client
so callers (cv_outputs API, cv_optimizer service) require minimal changes.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal
from uuid import UUID

from jinja2 import Environment, FileSystemLoader, TemplateNotFound, select_autoescape
from markdown_it import MarkdownIt
from weasyprint import HTML

from hireloop.services.storage import get_storage_service

TEMPLATES_DIR = Path(__file__).parent / "templates"

_md = MarkdownIt("commonmark")
_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(["html"]),
)

TemplateName = Literal["resume", "cover_letter"]


class PdfRenderError(Exception):
    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.details: dict[str, Any] = details or {}


@dataclass
class RenderResult:
    s3_key: str
    s3_bucket: str
    page_count: int
    size_bytes: int
    render_ms: int


async def render_pdf(
    *,
    markdown: str,
    template: TemplateName,
    user_id: UUID,
    output_key: str,
) -> RenderResult:
    """Render markdown → PDF using the given template, upload to S3, return metadata."""
    _ = user_id  # retained for symmetry with the old HTTP API; see spec §13
    start = datetime.now(UTC)

    try:
        html_body = _md.render(markdown)
    except Exception as e:
        raise PdfRenderError(
            f"markdown parse failed: {e}",
            details={"cause": repr(e)},
        ) from e

    try:
        tmpl = _env.get_template(f"{template}.html")
    except TemplateNotFound as e:
        raise PdfRenderError(
            f"template not found: {template}",
            details={"template": template, "cause": repr(e)},
        ) from e

    html_doc = tmpl.render(
        body=html_body,
        generated_at=datetime.now(UTC).strftime("%Y-%m-%d"),
    )

    try:
        pdf_bytes, page_count = await asyncio.to_thread(_render_sync, html_doc)
    except Exception as e:
        raise PdfRenderError(
            f"WeasyPrint render failed: {e}",
            details={"cause": repr(e), "template": template},
        ) from e

    storage = get_storage_service()
    await storage.upload_bytes(output_key, pdf_bytes, content_type="application/pdf")
    elapsed_ms = int((datetime.now(UTC) - start).total_seconds() * 1000)

    return RenderResult(
        s3_key=output_key,
        s3_bucket=storage.bucket,
        page_count=page_count,
        size_bytes=len(pdf_bytes),
        render_ms=elapsed_ms,
    )


def _render_sync(html_doc: str) -> tuple[bytes, int]:
    doc = HTML(string=html_doc, base_url=str(TEMPLATES_DIR)).render()
    pdf_bytes = doc.write_pdf()
    return pdf_bytes, len(doc.pages)
