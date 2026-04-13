"""HTTP client for the pdf-render Fastify service."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


class PdfRenderError(Exception):
    def __init__(self, message: str, *, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.details: dict[str, Any] = details or {}


@dataclass
class RenderResult:
    s3_key: str
    s3_bucket: str
    page_count: int
    size_bytes: int
    render_ms: int


class PdfRenderClient:
    def __init__(self, base_url: str, api_key: str, timeout_s: float):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout_s = timeout_s

    async def render(
        self,
        *,
        markdown: str,
        template: str,
        user_id: str,
        output_key: str,
    ) -> RenderResult:
        url = f"{self.base_url}/render"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "markdown": markdown,
            "template": template,
            "user_id": user_id,
            "output_key": output_key,
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout_s) as client:
                resp = await client.post(url, json=payload, headers=headers)
        except httpx.HTTPError as e:
            raise PdfRenderError(f"Network error: {e}") from e

        if resp.status_code >= 400:
            raise PdfRenderError(
                f"pdf-render returned HTTP {resp.status_code}",
                details={"body": resp.text[:500]},
            )

        body = resp.json()
        if not body.get("success"):
            raise PdfRenderError(
                f"pdf-render reported failure: {body.get('error', 'unknown')}",
                details=body,
            )

        return RenderResult(
            s3_key=body["s3_key"],
            s3_bucket=body["s3_bucket"],
            page_count=body["page_count"],
            size_bytes=body["size_bytes"],
            render_ms=body["render_ms"],
        )
