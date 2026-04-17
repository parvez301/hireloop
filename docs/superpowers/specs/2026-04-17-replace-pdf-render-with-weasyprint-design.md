# Replace pdf-render with in-process WeasyPrint

**Date:** 2026-04-17
**Phase:** 5a.3 (pdf-render scope only; Redis decision deferred)
**Status:** Draft — pending user review

## 1. Context

The original parent spec (`2026-04-10-careeragent-design.md`) and Phase 2a spec called for a separate Fastify + Playwright PDF rendering service, stated as:

> PDF rendering | Fastify + Playwright as a separate service on port 4000, called over HTTP with a shared-secret bearer token. **Can't run in Lambda (Chromium >250 MB).** Local dev: docker-compose service.

That premise was **based on an incorrect constraint**. Lambda's 250 MB limit applies to **ZIP package deployments only**. Lambda **container images support up to 10 GB**, and the current Phase 5a.2 architecture already deploys the backend as a Lambda container image. The "can't run in Lambda" reason therefore no longer holds — but the original cost model assumed a Fargate service always-on at ~$100/mo, introducing ongoing infra cost for a Chromium binary we do not actually need.

An audit of the existing template (`pdf-render/src/templates/resume.html`, 83 lines) shows the CSS uses only `@page`, `@font-face` with WOFF2, basic typography, and `position: fixed` for a footer. There is no flexbox, no grid, no complex layout. All of these features are **natively supported by WeasyPrint**, a free open-source (BSD-3) Python HTML-to-PDF library.

**Decision:** Delete the separate `pdf-render/` service entirely. Replace it with in-process WeasyPrint inside the backend Lambda. Result: one fewer service, one fewer container image, one fewer ECR repo, one fewer Lambda in the concurrency pool, one fewer shared-secret to rotate, and ~$100/mo prod savings vs. the original Fargate cost model.

## 2. Goals and non-goals

**Goals:**
- Eliminate the `pdf-render/` workspace and all associated infra references
- Move PDF generation into the backend Python process using WeasyPrint
- Preserve the existing `CvOutput` API contract (no caller breakage in `cv_outputs.py`)
- Ship a first-pass `cover_letter.html` template alongside the existing `resume.html`

**Non-goals:**
- Redis / ElastiCache decision (deferred to a separate brainstorm)
- Visual pixel-identical parity with the current Chromium output (Pango rendering produces sub-pixel differences; acceptable)
- Cover letter design polish beyond a working first-pass template

## 3. Architecture

**Before:**

```
backend Lambda (container)
      │ httpx POST /render  ──►  pdf-render Fargate/local container
      │                                │
      │                                ▼
      │                          Playwright + Chromium
      │                                │
      └────────────────  ◄──           └──► S3 PutObject
                     presigned key
```

**After:**

```
backend Lambda (container, + Cairo/Pango libs, + WeasyPrint)
      │
      │  markdown_to_html → jinja render → weasyprint.HTML().write_pdf()
      │
      └─────────────────────────────────────────►  S3 PutObject
```

No HTTP round-trip. No separate service. No shared secret. The backend Lambda container grows by ~40 MB of system libraries and one Python dependency.

## 4. Module layout changes

**New:**
- `backend/src/hireloop/core/cv_optimizer/pdf_renderer.py` — in-process renderer module
- `backend/src/hireloop/core/cv_optimizer/templates/resume.html` — ported from pdf-render
- `backend/src/hireloop/core/cv_optimizer/templates/cover_letter.html` — new first-pass template
- `backend/src/hireloop/core/cv_optimizer/templates/fonts/*.woff2` — 4 files copied verbatim
- `backend/tests/unit/test_pdf_renderer.py` — replacement test suite

**Deleted:**
- `pdf-render/` — entire workspace (src, test, Dockerfile, package.json, node_modules, dist, templates, fonts, .env.example)
- `backend/src/hireloop/integrations/pdf_render.py` — factory for old HTTP client
- `backend/src/hireloop/core/cv_optimizer/render_client.py` — old HTTP client
- `backend/tests/unit/test_pdf_render_client.py` — old HTTP-client tests

## 5. Rendering pipeline

**Public API** — keeps the same shape as the old HTTP client so callers don't change:

```python
# backend/src/hireloop/core/cv_optimizer/pdf_renderer.py
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
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


class PdfRenderError(Exception):
    def __init__(self, message: str, *, details: dict | None = None):
        super().__init__(message)
        self.details = details or {}


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
    template: Literal["resume", "cover_letter"],
    user_id: UUID,  # retained for symmetry with the old HTTP API; see §13
    output_key: str,
) -> RenderResult:
    start = datetime.now(timezone.utc)
    try:
        html_body = _md.render(markdown)
    except Exception as e:
        raise PdfRenderError(f"markdown parse failed: {e}", details={"cause": repr(e)}) from e

    try:
        tmpl = _env.get_template(f"{template}.html")
    except TemplateNotFound as e:
        raise PdfRenderError(
            f"template not found: {template}",
            details={"template": template, "cause": repr(e)},
        ) from e

    html_doc = tmpl.render(
        body=html_body,
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
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
    elapsed_ms = int((datetime.now(timezone.utc) - start).total_seconds() * 1000)
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
```

**Key decisions inside the module:**
- **S3 uploads go through `StorageService.upload_bytes`** (in `backend/src/hireloop/services/storage.py`) rather than a new helper in `integrations/s3.py`. `StorageService` already wraps `put_object` with `asyncio.to_thread` and applies `ServerSideEncryption="AES256"`; reusing it preserves that invariant. The bucket is owned by `StorageService` so callers don't pass it.
- `asyncio.to_thread` wraps the sync WeasyPrint call so it doesn't block the event loop
- `PdfRenderError` is preserved (same class name, same `details` contract) so the API layer's `PDF_RENDER_FAILED` 502 mapping in `backend/src/hireloop/api/cv_outputs.py:51,83` continues to work unchanged. Every raise site attaches structured `details` (template name, repr of underlying exception) to preserve debuggability parity with the old HTTP client.
- `TemplateNotFound` from Jinja is explicitly caught and remapped to `PdfRenderError` so the test rule (`test_render_pdf_raises_on_template_not_found`) is unambiguous.
- Markdown parser and Jinja env are module-scope singletons
- `base_url=str(TEMPLATES_DIR)` makes relative `url("fonts/...")` references in the CSS resolve to the packaged fonts

**Caller change** — `backend/src/hireloop/core/cv_optimizer/service.py` currently imports `PdfRenderClient` from `render_client`. Update to:

```python
from hireloop.core.cv_optimizer.pdf_renderer import render_pdf, PdfRenderError, RenderResult

# inside optimize():
render_result = await render_pdf(
    markdown=result.tailored_md,
    template="resume",
    user_id=user_id,
    output_key=pdf_key,
)
```

## 6. Templates

### 6.1 resume.html — port from pdf-render

Two edits to the existing 83-line file:

| Change | Before (Handlebars) | After (Jinja2) |
|---|---|---|
| 1 | `{{{body}}}` | `{{ body \| safe }}` |
| 2 | `{{generatedAt}}` | `{{ generated_at }}` |

The `@font-face` relative URL `url("fonts/SpaceGrotesk-Regular.woff2")` carries over unchanged — `base_url=str(TEMPLATES_DIR)` in the WeasyPrint call resolves it. Everything else (`@page` A4 + margin, typography rules, `position: fixed` footer) carries over verbatim.

### 6.2 cover_letter.html — new first-pass template

Mirrors `resume.html`'s page setup and font stack, but adjusted for letter conventions:

- Same `@page { size: A4; margin: 0.5in }`, same `@font-face` block (4 fonts, imported once per template file for now; dedup can be a later refactor)
- `h1` for the writer's name/header block
- No uppercase `h2` with bottom border (too aggressive for a letter; use normal-case with spacing)
- Line-height `1.55` (vs. resume's `1.45`) for more readable prose
- No fixed footer; page number only if multi-page: `@page { @bottom-right { content: counter(page) } }`
- Same `{{ body | safe }}` + `{{ generated_at }}` contract

Rough shape (~50 lines of CSS, same template variable contract):

```html
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>Cover Letter</title>
  <style>
    @page {
      size: A4;
      margin: 0.75in;
      @bottom-right { content: counter(page); font-family: "DM Sans"; font-size: 8pt; color: #787774; }
    }
    /* @font-face block identical to resume.html */
    html, body {
      font-family: "DM Sans", -apple-system, sans-serif;
      font-size: 11pt;
      line-height: 1.55;
      color: #37352f;
    }
    h1 {
      font-family: "Space Grotesk", sans-serif;
      font-size: 18pt;
      margin: 0 0 4pt 0;
    }
    p { margin: 0 0 10pt 0; }
  </style>
</head>
<body>
  {{ body | safe }}
</body>
</html>
```

## 7. Backend Dockerfile changes

WeasyPrint depends on Cairo, Pango, and HarfBuzz system libraries. Add to the backend Lambda Dockerfile (AWS Lambda Python base image):

```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    libcairo2 \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libharfbuzz0b \
    libfontconfig1 \
    shared-mime-info \
 && rm -rf /var/lib/apt/lists/*
```

**Size impact:** ~40 MB added to the backend image (~1 GB → ~1.04 GB). Still orders of magnitude under Lambda's 10 GB container limit.

**Cold start impact:** negligible (<100 ms). These libraries are lightweight and the font files are read lazily on first render.

**Deferred apt packages:** `libgdk-pixbuf-2.0-0` (raster image decoding for `<img>` tags and CSS `background-image`) is **not** included. The current resume.html + cover_letter.html have no images. Add it if and when a template embeds raster images via data URL or file:// URL.

## 8. Python dependency changes

Add to `backend/pyproject.toml`:

```toml
weasyprint = "^63.0"        # stable; pangoft2-based backend
markdown-it-py = "^3.0"     # CommonMark parser matching the JS `marked` behavior
# jinja2 — confirm presence (likely transitively via FastAPI/Starlette; add explicitly if not)
```

Run `uv lock` to refresh `uv.lock`.

## 9. Tests

**New: `backend/tests/unit/test_pdf_renderer.py`**

- `test_render_pdf_produces_valid_pdf` — ASCII markdown fixture → bytes start with `%PDF-` → `page_count ≥ 1`
- `test_render_pdf_with_unicode` — markdown with emoji, accented chars, CJK → no exceptions, bytes are valid PDF
- `test_render_pdf_multi_page` — long markdown → `page_count ≥ 2`
- `test_render_pdf_cover_letter_template` — both template literals resolve and render
- `test_render_pdf_uploads_to_s3` — `moto`-mocked S3, assert `put_object` called with the correct `bucket`, `key`, and `body`
- `test_render_pdf_raises_on_template_not_found` — bogus template name → `PdfRenderError`

**Deleted:**
- `backend/tests/unit/test_pdf_render_client.py`
- `pdf-render/test/` (entire directory, alongside the workspace deletion)

No integration tests against real AWS; `moto` is already in the backend dev deps.

## 10. Deletion and config cleanup checklist

**Filesystem deletions:**
- `pdf-render/` (workspace root)
- `backend/src/hireloop/integrations/pdf_render.py`
- `backend/src/hireloop/core/cv_optimizer/render_client.py`
- `backend/tests/unit/test_pdf_render_client.py`

**Config edits:**
- `backend/src/hireloop/config.py` — remove `pdf_render_url`, `pdf_render_api_key`, `pdf_render_timeout_s` settings
- `backend/.env.example` — remove `PDF_RENDER_URL`, `PDF_RENDER_API_KEY` lines
- `pdf-render/.env.example` — deleted with workspace
- `infrastructure/.env.deploy.local.example` — remove `PDF_RENDER_SHARED_SECRET` line
- `infrastructure/.env.deploy.local` (local file) — remove `PDF_RENDER_SHARED_SECRET` export
- `infrastructure/scripts/populate-dev-secrets.sh` — remove `require PDF_RENDER_SHARED_SECRET` + the `put_json_key "hireloop/dev/pdf-render-shared-secret"` call (7 secrets → 6)
- `infrastructure/cdk/lib/config-stack.ts` — remove the `pdf-render-shared-secret` Secret construct + related SSM params
- `infrastructure/cdk/lib/app-stack.ts` — remove `PDF_RENDER_SHARED_SECRET` from `buildApiEnv`; remove `PDF_RENDER_URL: ''` placeholder (lines 340, 349 per grep)
- `docker-compose.yml` — remove the `pdf-render` service and any references in other services' `depends_on`
- `pnpm-workspace.yaml` — remove `"pdf-render"` entry
- Root `package.json` — remove any workspace references to `pdf-render`

**Post-merge, post-deploy AWS cleanup:**
- `aws secretsmanager delete-secret --secret-id hireloop/dev/pdf-render-shared-secret --recovery-window-in-days 7`
- `aws ecr describe-repositories --repository-names hireloop-pdf-render` — if the repo was created by `ensure-ecr-repos.sh` in an earlier draft, delete it: `aws ecr delete-repository --repository-name hireloop-pdf-render --force`. If it was never created, no-op.

## 11. Implementation sequence

1. Add `weasyprint` + `markdown-it-py` to `backend/pyproject.toml`; run `uv lock`
2. Create `pdf_renderer.py` with the full module above
3. `git mv pdf-render/src/templates backend/src/hireloop/core/cv_optimizer/templates` to preserve history
4. Apply the 2 edits to `resume.html` (§6.1)
5. Write `cover_letter.html` (first-pass)
6. Write `test_pdf_renderer.py` (the 6 tests above)
7. Update `backend/src/hireloop/core/cv_optimizer/service.py` — switch `PdfRenderClient` → `render_pdf` import
8. Update backend Dockerfile — add the apt-get block
9. Local smoke test:
   - `docker-compose up backend`, hit `POST /cv-outputs` with a realistic markdown fixture
   - Verify the returned PDF opens, text extracts correctly, and uses Space Grotesk + DM Sans fonts
   - **Markdown parity check (golden fixture):** render one representative CV markdown through both `marked` (via the still-present pdf-render dev container) and `markdown-it-py`, diff the normalized HTML output, confirm no surprise layout shifts. This is a one-time check before deletion; no need to keep the fixture afterward.
10. Delete `pdf-render/` workspace (`git rm -r pdf-render/`)
11. Run all config/CDK/docker-compose/pnpm-workspace cleanup edits from Section 10
12. `pytest backend/` — all green
13. `ruff check backend && black --check backend && mypy backend/src` — all clean
14. Commit as a focused series (~8–10 commits): `feat(backend): add in-process WeasyPrint renderer`, `feat(backend): add cover_letter template`, `refactor(backend): switch cv_optimizer to in-process render_pdf`, `chore: add Cairo/Pango to backend Dockerfile`, `test(backend): replace pdf_render_client tests with pdf_renderer tests`, `chore(infra): remove PDF_RENDER_* config + secret references`, `chore: remove pdf-render workspace`
15. Push to `main` (or PR, depending on user preference)
16. After next backend deploy: run the AWS cleanup from Section 10 (Secrets Manager delete + optional ECR repo delete)

## 12. Rollback plan

If WeasyPrint output is unacceptable on real CV content after deployment:

1. `git revert` the commit series (one revert-of-merge or a range revert if landed as multiple commits)
2. Restore `pdf-render/` workspace from the reverted commit (already handled by the revert)
3. Restore `PDF_RENDER_SHARED_SECRET` in `infrastructure/.env.deploy.local`
4. Run `populate-dev-secrets.sh` to restore the Secrets Manager entry
5. Redeploy backend

Estimated rollback time: **~15 minutes**. The secret recovery window (7 days) means step 3–4 may not be needed if the Secrets Manager secret still exists in pending-deletion state.

## 13. Assumptions and open questions

- **Assumption:** The existing resume.html template renders acceptably in WeasyPrint with only the 2 Jinja edits from §6.1. If WeasyPrint's Pango font rendering produces output that looks clearly worse than Chromium's output, we may need to tune font weights, add `-weasy-*` vendor extensions, or switch to a different font stack. Mitigation: Step 9 (local smoke test) runs before any CDK / deployment work.
- **Open:** Does the markdown-it-py CommonMark renderer's output match `marked`'s output closely enough that no template changes are needed? The Step 9 golden-fixture diff will answer this.
- **Open (YAGNI-flagged):** The `user_id` parameter in the old HTTP API is never actually used by the renderer (S3 key construction happens in the caller). The new `render_pdf` signature keeps it for symmetry and to avoid caller churn. If ruff or mypy flag it as unused inside `pdf_renderer.py`, rename to `_user_id` or add a single `# noqa: ARG` comment rather than dropping the parameter and updating every caller.
- **Risk (Lambda sizing):** Heavy CVs or pathological markdown (thousands of bullet points, large tables) could push WeasyPrint render time up. Not changing Lambda memory / timeout in v1 — but after the first prod-like runs, inspect `render_ms` metrics on `usage_events`. If p95 exceeds ~5 s or OOM errors appear, bump Lambda memory from the current setting (which also scales CPU) or increase timeout. No action needed up front.
- **Deferred:** `libgdk-pixbuf-2.0-0` in the backend Dockerfile — add when a template first embeds a raster image.
