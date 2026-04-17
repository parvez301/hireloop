# Replace pdf-render with in-process WeasyPrint — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Delete the separate `pdf-render/` Fastify+Playwright service and replace it with in-process WeasyPrint inside the backend Python Lambda, without breaking any caller contracts.

**Architecture:** Backend Lambda gains `pdf_renderer.py` (markdown → Jinja2 → WeasyPrint → S3 via existing `StorageService`). The HTTP client in `render_client.py` is deleted; the `CvOptimizerService` calls `render_pdf` directly. The `pdf-render/` workspace, CI Playwright steps, docker-compose service, and related CDK secrets/env vars are all removed.

**Tech Stack:** Python 3.12, FastAPI, WeasyPrint 63+, markdown-it-py, Jinja2, boto3 (via existing `StorageService`), pytest + moto for tests, AWS Lambda container image, Hatchling for Python packaging.

**Spec:** `docs/superpowers/specs/2026-04-17-replace-pdf-render-with-weasyprint-design.md` @ HEAD `f71c897`

---

## File structure (what gets created, modified, deleted)

**Created:**
- `backend/src/hireloop/core/cv_optimizer/pdf_renderer.py` — in-process PDF renderer
- `backend/src/hireloop/core/cv_optimizer/templates/` (moved from `pdf-render/src/templates/`)
- `backend/src/hireloop/core/cv_optimizer/templates/cover_letter.html` — new first-pass template
- `backend/tests/unit/test_pdf_renderer.py` — replacement test suite

**Modified:**
- `backend/pyproject.toml` — add `weasyprint`, `markdown-it-py`; add wheel force-include for `templates/`
- `backend/Dockerfile` — add Cairo/Pango/fontconfig to both `lambda` and `ec2` stages; bake fontconfig cache
- `backend/src/hireloop/config.py` — remove `pdf_render_url`, `pdf_render_api_key`, `pdf_render_timeout_s`
- `backend/src/hireloop/core/cv_optimizer/service.py` — delete `render_client` DI seam; use `render_pdf` directly
- `backend/src/hireloop/core/cv_optimizer/__init__.py` — drop "pdf-render client" from docstring
- `backend/.env.example` — remove `PDF_RENDER_URL`, `PDF_RENDER_API_KEY`
- `backend/tests/conftest.py:41` — remove `os.environ.setdefault("PDF_RENDER_URL", ...)`
- `backend/src/hireloop/core/cv_optimizer/templates/resume.html` — 2 Jinja edits (post-move)
- `.github/workflows/ci.yml` — remove Playwright cache/install + pdf-render test step (lines ~97-112)
- `docker-compose.yml` — remove `pdf-render` service and any `depends_on` references
- `pnpm-workspace.yaml` — remove `pdf-render` entry
- `Justfile:63` — update `up` target comment
- `infrastructure/cdk/lib/app-stack.ts:42,51,201` — remove `PDF_RENDER_SHARED_SECRET`, `PDF_RENDER_URL`, secret grant
- `infrastructure/cdk/lib/config-stack.ts:34` — remove `pdf-render-shared-secret` seed
- `infrastructure/scripts/populate-dev-secrets.sh` — drop `PDF_RENDER_SHARED_SECRET` require + put_json_key
- `infrastructure/.env.deploy.local.example` — drop `PDF_RENDER_SHARED_SECRET`
- `infrastructure/.env.deploy.local` (local file, not committed) — drop the same

**Deleted:**
- `pdf-render/` (entire workspace: src, test, Dockerfile, package.json, node_modules, dist, playwright.config.ts, vitest.config.ts, tsconfig.json)
- `backend/src/hireloop/integrations/pdf_render.py`
- `backend/src/hireloop/core/cv_optimizer/render_client.py`
- `backend/tests/unit/test_pdf_render_client.py`

---

### Task 1: Add Python dependencies

**Files:**
- Modify: `backend/pyproject.toml`

- [ ] **Step 1: Add `weasyprint` and `markdown-it-py` to the `[project].dependencies` array**

Edit `backend/pyproject.toml` — inside the `dependencies = [...]` list (currently ending at line 34 with `"mangum>=0.17,<0.20",`), append:

```toml
    "weasyprint>=63,<64",
    "markdown-it-py>=3,<4",
    "jinja2>=3.1,<4",
```

`jinja2` is already transitive via FastAPI but pin it explicitly so mypy strict resolves the import.

- [ ] **Step 2: Refresh the lockfile**

```bash
cd backend
uv lock
```

Expected: `uv.lock` is updated to include the three new packages and their transitive deps (Pango-python bindings come in as part of `weasyprint`'s wheel on Linux x86_64).

- [ ] **Step 3: Install locally for subsequent tasks to run**

```bash
cd backend
uv sync
```

Expected: venv now has weasyprint + markdown-it-py. Quick verify:
```bash
uv run python -c "import weasyprint, markdown_it; print(weasyprint.__version__, markdown_it.__version__)"
```

- [ ] **Step 4: Commit**

```bash
git add backend/pyproject.toml backend/uv.lock
git commit -m "feat(backend): add weasyprint + markdown-it-py deps"
```

---

### Task 2: Scaffold `pdf_renderer.py` with the first failing test

This task drives the module skeleton via TDD. We start with the simplest test (template-not-found) because it exercises the error-mapping path without needing a working Cairo/Pango install yet.

**Files:**
- Create: `backend/src/hireloop/core/cv_optimizer/pdf_renderer.py`
- Create: `backend/tests/unit/test_pdf_renderer.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/unit/test_pdf_renderer.py`:

```python
"""Tests for in-process WeasyPrint PDF renderer."""

from __future__ import annotations

import uuid

import pytest

from hireloop.core.cv_optimizer.pdf_renderer import PdfRenderError, render_pdf


@pytest.mark.asyncio
async def test_render_pdf_raises_on_template_not_found() -> None:
    with pytest.raises(PdfRenderError) as excinfo:
        await render_pdf(
            markdown="# anything",
            template="bogus_template",  # type: ignore[arg-type]
            user_id=uuid.uuid4(),
            output_key="test/key.pdf",
        )
    assert excinfo.value.details["template"] == "bogus_template"
    assert "template not found" in str(excinfo.value)
```

- [ ] **Step 2: Run the test and confirm it fails with import error**

```bash
cd backend
uv run pytest tests/unit/test_pdf_renderer.py -v
```

Expected: `ModuleNotFoundError: No module named 'hireloop.core.cv_optimizer.pdf_renderer'`

- [ ] **Step 3: Create the module with the minimal surface to make this one test pass**

Create `backend/src/hireloop/core/cv_optimizer/pdf_renderer.py`:

```python
"""In-process WeasyPrint PDF renderer.

Replaces the HTTP-based `render_client.PdfRenderClient` with a direct
markdown → Jinja2 → WeasyPrint → S3 pipeline. The public `PdfRenderError`
class and `RenderResult` dataclass keep the same shape as the old client
so callers (cv_outputs API, cv_optimizer service) require minimal changes.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
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
    start = datetime.now(timezone.utc)

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

- [ ] **Step 4: Re-run the test**

```bash
cd backend
uv run pytest tests/unit/test_pdf_renderer.py::test_render_pdf_raises_on_template_not_found -v
```

Expected: PASS. The test runs through the template-loading branch and hits the `TemplateNotFound` remap before touching WeasyPrint or storage, so it passes even with no templates or S3 mock yet.

If the test fails with a different error (e.g. `ImportError: cannot import name 'get_storage_service'`), confirm the import path matches `backend/src/hireloop/services/storage.py`.

- [ ] **Step 5: Commit**

```bash
git add backend/src/hireloop/core/cv_optimizer/pdf_renderer.py backend/tests/unit/test_pdf_renderer.py
git commit -m "feat(backend): scaffold pdf_renderer with TemplateNotFound mapping"
```

---

### Task 3: Move templates directory + port resume.html to Jinja2

**Files:**
- Moved: `pdf-render/src/templates/` → `backend/src/hireloop/core/cv_optimizer/templates/`
- Modify: `backend/src/hireloop/core/cv_optimizer/templates/resume.html`

- [ ] **Step 1: Move the templates directory with git mv**

```bash
cd /Users/parvez/projects/personal/career-agent
mkdir -p backend/src/hireloop/core/cv_optimizer
git mv pdf-render/src/templates backend/src/hireloop/core/cv_optimizer/templates
```

Expected: `backend/src/hireloop/core/cv_optimizer/templates/` now contains `resume.html` + `fonts/` with 4 `.woff2` files. Git tracks this as renames (not add+delete) preserving history.

Verify:
```bash
ls backend/src/hireloop/core/cv_optimizer/templates/
# resume.html  fonts/
ls backend/src/hireloop/core/cv_optimizer/templates/fonts/
# DMSans-Bold.woff2  DMSans-Regular.woff2  SpaceGrotesk-Bold.woff2  SpaceGrotesk-Regular.woff2
```

- [ ] **Step 2: Edit resume.html — swap 2 Handlebars expressions for Jinja2**

In `backend/src/hireloop/core/cv_optimizer/templates/resume.html`:

Change line ~80 (inside `<body>`):
```html
  {{{body}}}
```
to:
```html
  {{ body | safe }}
```

Change line ~81 (inside `<div class="generated-at">`):
```html
  <div class="generated-at">Generated {{generatedAt}}</div>
```
to:
```html
  <div class="generated-at">Generated {{ generated_at }}</div>
```

No other changes — `@page`, `@font-face`, typography, `position: fixed` footer all carry over verbatim.

- [ ] **Step 3: Verify by loading the template in Python**

```bash
cd backend
uv run python -c "
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
tdir = Path('src/hireloop/core/cv_optimizer/templates')
env = Environment(loader=FileSystemLoader(str(tdir)))
out = env.get_template('resume.html').render(body='<h1>Hi</h1>', generated_at='2026-04-17')
assert '<h1>Hi</h1>' in out
assert '2026-04-17' in out
print('template renders OK, length =', len(out))
"
```

Expected: `template renders OK, length = <something around 2200-2500>`

- [ ] **Step 4: Commit**

```bash
git add -A backend/src/hireloop/core/cv_optimizer/templates pdf-render/src/templates
git commit -m "refactor(backend): move resume.html into cv_optimizer + port to Jinja2"
```

Note: the git-mv creates deletion entries under `pdf-render/src/templates/` — those are expected and part of the rename tracking. The rest of the `pdf-render/` workspace is deleted later in Task 12.

---

### Task 4: Add cover_letter.html first-pass template

**Files:**
- Create: `backend/src/hireloop/core/cv_optimizer/templates/cover_letter.html`

- [ ] **Step 1: Create the template file**

Create `backend/src/hireloop/core/cv_optimizer/templates/cover_letter.html`:

```html
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>Cover Letter</title>
  <style>
    @font-face {
      font-family: "Space Grotesk";
      font-weight: 400;
      src: url("fonts/SpaceGrotesk-Regular.woff2") format("woff2");
    }
    @font-face {
      font-family: "Space Grotesk";
      font-weight: 700;
      src: url("fonts/SpaceGrotesk-Bold.woff2") format("woff2");
    }
    @font-face {
      font-family: "DM Sans";
      font-weight: 400;
      src: url("fonts/DMSans-Regular.woff2") format("woff2");
    }
    @font-face {
      font-family: "DM Sans";
      font-weight: 700;
      src: url("fonts/DMSans-Bold.woff2") format("woff2");
    }
    @page {
      size: A4;
      margin: 0.75in;
      @bottom-right {
        content: counter(page);
        font-family: "DM Sans", sans-serif;
        font-size: 8pt;
        color: #787774;
      }
    }
    html, body {
      margin: 0;
      padding: 0;
      font-family: "DM Sans", -apple-system, BlinkMacSystemFont, sans-serif;
      font-size: 11pt;
      color: #37352f;
      line-height: 1.55;
    }
    h1 {
      font-family: "Space Grotesk", sans-serif;
      font-size: 18pt;
      margin: 0 0 4pt 0;
      color: #37352f;
    }
    h2 {
      font-family: "Space Grotesk", sans-serif;
      font-size: 12pt;
      margin: 14pt 0 4pt 0;
    }
    p {
      margin: 0 0 10pt 0;
    }
    a {
      color: #2383e2;
      text-decoration: none;
    }
  </style>
</head>
<body>
  {{ body | safe }}
</body>
</html>
```

- [ ] **Step 2: Smoke-test the template loads**

```bash
cd backend
uv run python -c "
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
tdir = Path('src/hireloop/core/cv_optimizer/templates')
env = Environment(loader=FileSystemLoader(str(tdir)))
for name in ('resume', 'cover_letter'):
    out = env.get_template(f'{name}.html').render(body='<p>x</p>', generated_at='2026-04-17')
    print(name, 'len=', len(out))
"
```

Expected output:
```
resume len= <~2400>
cover_letter len= <~1700>
```

- [ ] **Step 3: Commit**

```bash
git add backend/src/hireloop/core/cv_optimizer/templates/cover_letter.html
git commit -m "feat(backend): add first-pass cover_letter template"
```

---

### Task 5: Full TDD test suite for pdf_renderer

With the module + templates in place, add the remaining 5 tests from the spec. All except one of these need a working Cairo/Pango install on the dev machine. If your dev machine is macOS, ensure `brew install pango cairo` is done once; if Linux, `apt-get install libpango-1.0-0 libcairo2 libpangoft2-1.0-0`.

**Files:**
- Modify: `backend/tests/unit/test_pdf_renderer.py`

- [ ] **Step 1: Add the 5 remaining tests**

Replace the file contents with:

```python
"""Tests for in-process WeasyPrint PDF renderer."""

from __future__ import annotations

import uuid

import boto3
import pytest
from moto import mock_aws

from hireloop.config import get_settings
from hireloop.core.cv_optimizer.pdf_renderer import (
    PdfRenderError,
    RenderResult,
    render_pdf,
)
from hireloop.integrations.s3 import get_s3_client
from hireloop.services.storage import get_storage_service


@pytest.fixture(autouse=True)
def _reset_caches() -> None:
    """Reset lru_cache on singletons so each test sees the current env/mock."""
    get_settings.cache_clear()
    get_s3_client.cache_clear()


@pytest.fixture
def _s3_mock() -> object:
    """Moto-mocked S3 with the configured bucket pre-created."""
    with mock_aws():
        settings = get_settings()
        client = boto3.client("s3", region_name=settings.aws_region)
        client.create_bucket(Bucket=settings.aws_s3_bucket)
        yield client


SAMPLE_MARKDOWN = """# Jane Candidate

Senior engineer with 10 years of experience.

## Experience

- **Company A** — Staff Engineer (2020–present)
  - Shipped large-scale platform X
  - Mentored 5 engineers
- **Company B** — Senior Engineer (2015–2020)

## Education

- BS Computer Science, University Y
"""


@pytest.mark.asyncio
async def test_render_pdf_raises_on_template_not_found() -> None:
    with pytest.raises(PdfRenderError) as excinfo:
        await render_pdf(
            markdown="# anything",
            template="bogus_template",  # type: ignore[arg-type]
            user_id=uuid.uuid4(),
            output_key="test/key.pdf",
        )
    assert excinfo.value.details["template"] == "bogus_template"
    assert "template not found" in str(excinfo.value)


@pytest.mark.asyncio
async def test_render_pdf_produces_valid_pdf(_s3_mock: object) -> None:
    result = await render_pdf(
        markdown=SAMPLE_MARKDOWN,
        template="resume",
        user_id=uuid.uuid4(),
        output_key="cv-outputs/test/resume.pdf",
    )
    assert isinstance(result, RenderResult)
    assert result.page_count >= 1
    assert result.size_bytes > 1000  # a real PDF is at least 1 KB
    assert result.render_ms >= 0

    # Fetch the uploaded object and verify it's a real PDF
    settings = get_settings()
    client = boto3.client("s3", region_name=settings.aws_region)
    obj = client.get_object(Bucket=settings.aws_s3_bucket, Key="cv-outputs/test/resume.pdf")
    body = obj["Body"].read()
    assert body.startswith(b"%PDF-"), f"expected PDF header, got {body[:8]!r}"


@pytest.mark.asyncio
async def test_render_pdf_with_unicode(_s3_mock: object) -> None:
    md = """# 候選人 — Résumé

## Expérience

- Emoji: 🚀 ✨
- Accented: café, naïve, Zürich
- CJK: 日本語, 中文, 한국어
"""
    result = await render_pdf(
        markdown=md,
        template="resume",
        user_id=uuid.uuid4(),
        output_key="cv-outputs/test/unicode.pdf",
    )
    assert result.size_bytes > 1000


@pytest.mark.asyncio
async def test_render_pdf_multi_page(_s3_mock: object) -> None:
    # Build markdown with enough content to span 2+ pages
    big_md = "# Multi-page CV\n\n" + "\n\n".join(
        f"## Section {i}\n\n" + ("This is a filler paragraph. " * 40)
        for i in range(20)
    )
    result = await render_pdf(
        markdown=big_md,
        template="resume",
        user_id=uuid.uuid4(),
        output_key="cv-outputs/test/multi.pdf",
    )
    assert result.page_count >= 2


@pytest.mark.asyncio
async def test_render_pdf_cover_letter_template(_s3_mock: object) -> None:
    result = await render_pdf(
        markdown="# Dear Hiring Manager\n\nI am writing to apply...",
        template="cover_letter",
        user_id=uuid.uuid4(),
        output_key="cv-outputs/test/letter.pdf",
    )
    assert result.page_count >= 1
    assert result.size_bytes > 500


@pytest.mark.asyncio
async def test_render_pdf_uploads_to_s3(_s3_mock: object) -> None:
    # Confirms StorageService.upload_bytes is actually called with expected args
    key = "cv-outputs/test/upload-probe.pdf"
    result = await render_pdf(
        markdown="# probe",
        template="resume",
        user_id=uuid.uuid4(),
        output_key=key,
    )
    assert result.s3_key == key

    # Verify object exists in mocked S3
    settings = get_settings()
    client = boto3.client("s3", region_name=settings.aws_region)
    head = client.head_object(Bucket=settings.aws_s3_bucket, Key=key)
    assert head["ContentType"] == "application/pdf"
    assert head["ServerSideEncryption"] == "AES256"
```

- [ ] **Step 2: Run the full suite**

```bash
cd backend
uv run pytest tests/unit/test_pdf_renderer.py -v
```

Expected: all 6 tests PASS. If any WeasyPrint-dependent test fails with `OSError: cannot load library 'libpango-1.0-0'` or similar, install system libs:
- macOS: `brew install pango cairo`
- Ubuntu/Debian: `sudo apt-get install -y libpango-1.0-0 libpangoft2-1.0-0 libcairo2 libharfbuzz0b libfontconfig1`

- [ ] **Step 3: Commit**

```bash
git add backend/tests/unit/test_pdf_renderer.py
git commit -m "test(backend): comprehensive pdf_renderer test suite"
```

---

### Task 6: Update backend Dockerfile with Cairo/Pango + fontconfig cache

**Files:**
- Modify: `backend/Dockerfile`

- [ ] **Step 1: Read the current Dockerfile to understand the stages**

```bash
cat backend/Dockerfile
```

Current: `builder` stage (python:3.12-slim) → `lambda` (AWS Lambda base) or `ec2` (python:3.12-slim). The runtime libs need to be in both `lambda` and `ec2` stages — not `builder`.

- [ ] **Step 2: Update the `lambda` stage**

Replace the `lambda` stage block in `backend/Dockerfile`:

```dockerfile
FROM public.ecr.aws/lambda/python:3.12 AS lambda
# WeasyPrint runtime deps: Cairo, Pango, HarfBuzz, fontconfig + shared-mime-info.
# microdnf is the package manager on AWS Lambda's AL2023-based image.
RUN microdnf install -y \
      cairo \
      pango \
      harfbuzz \
      fontconfig \
      shared-mime-info \
 && microdnf clean all

WORKDIR /var/task
COPY --from=builder /build/.venv /var/task/.venv
COPY --from=builder /build/src ./src
COPY --from=builder /build/migrations ./migrations
COPY --from=builder /build/alembic.ini ./

# fontconfig needs a writable cache; Lambda's $HOME is read-only at runtime.
# Bake the cache at image build time pointing at /tmp so the first cold start
# doesn't spend time regenerating it (and doesn't fail on read-only paths).
ENV XDG_CACHE_HOME=/tmp/fontconfig
RUN mkdir -p /tmp/fontconfig && fc-cache -f 2>/dev/null || true

# PYTHONPATH must include .venv site-packages — the Lambda runtime's python
# doesn't read PATH for module imports, only PYTHONPATH.
ENV PYTHONPATH=/var/task/src:/var/task/.venv/lib/python3.12/site-packages
ENV PATH="/var/task/.venv/bin:${PATH}"
CMD ["hireloop.aws_lambda_adapter.handler"]
```

Note: the AWS Lambda Python base image (`public.ecr.aws/lambda/python:3.12`) is AL2023-based and uses `microdnf`, not `apt-get`. Package names are `cairo`, `pango`, `harfbuzz`, `fontconfig` (not `libcairo2` etc. — those are Debian package names).

- [ ] **Step 3: Update the `ec2` stage**

Replace the `ec2` stage block:

```dockerfile
FROM python:3.12-slim AS ec2
# WeasyPrint runtime deps (Debian package names for python:3.12-slim).
RUN apt-get update && apt-get install -y --no-install-recommends \
      libcairo2 \
      libpango-1.0-0 \
      libpangoft2-1.0-0 \
      libharfbuzz0b \
      libfontconfig1 \
      fontconfig \
      shared-mime-info \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /build/.venv /app/.venv
COPY --from=builder /build/src ./src
COPY --from=builder /build/migrations ./migrations
COPY --from=builder /build/alembic.ini ./
COPY scripts/entrypoint.sh ./scripts/entrypoint.sh
RUN chmod +x ./scripts/entrypoint.sh

ENV XDG_CACHE_HOME=/tmp/fontconfig
RUN mkdir -p /tmp/fontconfig && fc-cache -f 2>/dev/null || true

ENV PYTHONPATH=/app/src
ENV PATH="/app/.venv/bin:${PATH}"
ENTRYPOINT ["./scripts/entrypoint.sh"]
```

- [ ] **Step 4: Build both stages locally to verify**

```bash
cd backend
podman build --target lambda -t hireloop-backend:lambda-test .
podman build --target ec2 -t hireloop-backend:ec2-test .
```

Expected: both builds succeed. If `microdnf` package names are wrong on the lambda stage, the error will be `error: no package matches 'cairo'` or similar — adjust package names (`cairo-devel` is for build; `cairo` is the runtime lib).

- [ ] **Step 5: Verify WeasyPrint import works in the built images**

```bash
podman run --rm hireloop-backend:lambda-test python3 -c "import weasyprint; print('OK', weasyprint.__version__)"
podman run --rm hireloop-backend:ec2-test python -c "import weasyprint; print('OK', weasyprint.__version__)"
```

Expected: both print `OK 63.x`. A Pango/Cairo load failure would manifest as `OSError: cannot load library 'libpango-1.0-0.so.0': /lib/...: cannot open shared object file`.

- [ ] **Step 6: Commit**

```bash
git add backend/Dockerfile
git commit -m "chore(backend): add Cairo/Pango/fontconfig to Dockerfile stages"
```

---

### Task 7: Configure Hatchling to ship templates + fonts in the wheel

`backend/pyproject.toml` uses Hatchling (`build-backend = "hatchling.build"`). By default Hatchling includes only `.py` files under `packages = [...]`. The `.html` + `.woff2` files need to be explicitly included, otherwise `uv sync` in the Docker `builder` stage installs the wheel and silently drops the templates, and the Lambda renders blank PDFs at runtime.

**Files:**
- Modify: `backend/pyproject.toml`

- [ ] **Step 1: Add wheel include configuration**

At the end of `backend/pyproject.toml` (after the existing `[tool.hatch.build.targets.wheel]` block at line 106-107), the file currently ends with:

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/hireloop"]
```

Extend this by adding a sibling block and an artifacts line:

```toml
[tool.hatch.build.targets.wheel]
packages = ["src/hireloop"]
artifacts = [
    "src/hireloop/core/cv_optimizer/templates/**/*.html",
    "src/hireloop/core/cv_optimizer/templates/**/*.woff2",
]

[tool.hatch.build.targets.sdist]
include = [
    "src/hireloop/**/*.html",
    "src/hireloop/**/*.woff2",
]
```

- [ ] **Step 2: Build the wheel locally and inspect**

```bash
cd backend
uv build --wheel
```

Expected: `dist/hireloop-0.1.0-py3-none-any.whl` is produced.

- [ ] **Step 3: Verify the woff2 files are inside the wheel**

```bash
unzip -l backend/dist/hireloop-0.1.0-py3-none-any.whl | grep -E "(\.woff2|\.html)"
```

Expected output contains:
```
        ...  hireloop/core/cv_optimizer/templates/resume.html
        ...  hireloop/core/cv_optimizer/templates/cover_letter.html
        ...  hireloop/core/cv_optimizer/templates/fonts/DMSans-Bold.woff2
        ...  hireloop/core/cv_optimizer/templates/fonts/DMSans-Regular.woff2
        ...  hireloop/core/cv_optimizer/templates/fonts/SpaceGrotesk-Bold.woff2
        ...  hireloop/core/cv_optimizer/templates/fonts/SpaceGrotesk-Regular.woff2
```

If any are missing, adjust the `artifacts` globs. The most common gotcha is that Hatchling's glob matcher doesn't traverse symlinked dirs — confirm the templates directory isn't a symlink.

- [ ] **Step 4: Clean up the local dist dir and commit**

```bash
rm -rf backend/dist
git add backend/pyproject.toml
git commit -m "chore(backend): ship templates + fonts in the wheel"
```

---

### Task 8: Switch CvOptimizerService to call render_pdf directly

**Files:**
- Modify: `backend/src/hireloop/core/cv_optimizer/service.py`

This task deletes the `render_client` dependency-injection seam and calls `render_pdf` in-process. The old DI was used to inject test stubs; we'll rely on `monkeypatch` of `pdf_renderer.render_pdf` for those cases (or let the full renderer run with a moto-mocked S3, which is simpler).

- [ ] **Step 1: Read the current file**

```bash
cat backend/src/hireloop/core/cv_optimizer/service.py
```

Note the imports, the `CvOptimizerContext` dataclass (has `render_client: PdfRenderClient | None = None`), the `CvOptimizerService.__init__` (has `self.render_client = context.render_client or get_pdf_render_client()`), and the `optimize()` method's render call (`await self.render_client.render(...)`).

- [ ] **Step 2: Remove PdfRenderClient import + integration factory**

In `backend/src/hireloop/core/cv_optimizer/service.py`:

Remove these import lines at the top:
```python
from hireloop.core.cv_optimizer.render_client import PdfRenderClient
from hireloop.integrations.pdf_render import get_pdf_render_client
```

Add:
```python
from hireloop.core.cv_optimizer.pdf_renderer import render_pdf
```

- [ ] **Step 3: Delete `render_client` field from the context dataclass**

Change:
```python
@dataclass
class CvOptimizerContext:
    user_id: uuid.UUID
    session: AsyncSession
    usage: UsageEventService
    render_client: PdfRenderClient | None = None
```

To:
```python
@dataclass
class CvOptimizerContext:
    user_id: uuid.UUID
    session: AsyncSession
    usage: UsageEventService
```

- [ ] **Step 4: Remove the render_client init in CvOptimizerService**

In `CvOptimizerService.__init__`, change:
```python
def __init__(self, context: CvOptimizerContext):
    self.context = context
    self.optimizer = CvOptimizer()
    self.render_client = context.render_client or get_pdf_render_client()
```

To:
```python
def __init__(self, context: CvOptimizerContext):
    self.context = context
    self.optimizer = CvOptimizer()
```

- [ ] **Step 5: Replace the render call in optimize()**

Find the block (around line 88-94):
```python
pdf_key = f"cv-outputs/{self.context.user_id}/{uuid.uuid4()}.pdf"
await self.render_client.render(
    markdown=rewritten.tailored_md,
    template="resume",
    user_id=str(self.context.user_id),
    output_key=pdf_key,
)
```

Replace with:
```python
pdf_key = f"cv-outputs/{self.context.user_id}/{uuid.uuid4()}.pdf"
await render_pdf(
    markdown=rewritten.tailored_md,
    template="resume",
    user_id=self.context.user_id,
    output_key=pdf_key,
)
```

The `user_id=str(...)` cast is dropped because the new `render_pdf` signature takes `UUID` directly.

- [ ] **Step 6: Audit callers of CvOptimizerContext for removed kwarg**

```bash
grep -rn "CvOptimizerContext(" backend/src backend/tests
```

Confirm no caller passes `render_client=`. From the earlier grep, the call sites are `backend/src/hireloop/api/cv_outputs.py:44,76` and `backend/src/hireloop/core/agent/tools.py:110` — none passes `render_client` at present. If a test does, update it to `monkeypatch.setattr("hireloop.core.cv_optimizer.service.render_pdf", fake_fn)` instead.

- [ ] **Step 7: Run existing cv_optimizer tests**

```bash
cd backend
uv run pytest tests/unit/ tests/integration/ -k "cv_optimizer or cv_output" -v
```

Expected: all tests related to cv_optimizer pass. If any test previously relied on `context.render_client = FakeRenderClient()` for stubbing, it now fails. Fix those by either:
1. Using moto to intercept the actual S3 upload, or
2. `monkeypatch.setattr("hireloop.core.cv_optimizer.service.render_pdf", async_fake)`

- [ ] **Step 8: Run the full backend test suite**

```bash
cd backend
uv run pytest tests/ -v --timeout 60
```

Expected: all green. Any remaining red comes from the old `test_pdf_render_client.py` which is deleted in Task 9.

- [ ] **Step 9: Commit**

```bash
git add backend/src/hireloop/core/cv_optimizer/service.py
git commit -m "refactor(backend): switch cv_optimizer to in-process render_pdf"
```

---

### Task 9: Delete old HTTP client + integration factory + associated tests

**Files:**
- Delete: `backend/src/hireloop/integrations/pdf_render.py`
- Delete: `backend/src/hireloop/core/cv_optimizer/render_client.py`
- Delete: `backend/tests/unit/test_pdf_render_client.py`

- [ ] **Step 1: Remove the three files**

```bash
git rm backend/src/hireloop/integrations/pdf_render.py
git rm backend/src/hireloop/core/cv_optimizer/render_client.py
git rm backend/tests/unit/test_pdf_render_client.py
```

- [ ] **Step 2: Confirm no remaining imports reference them**

```bash
grep -rn "from hireloop.integrations.pdf_render\|from hireloop.core.cv_optimizer.render_client\|PdfRenderClient" backend/src backend/tests
```

Expected: no matches (or only matches inside the files we're about to delete via the step above, which no longer exist).

If any file still imports these, update it. The most likely candidate is `backend/src/hireloop/core/agent/tools.py` — if that file has a stray import, remove the import line.

- [ ] **Step 3: Run the full test suite**

```bash
cd backend
uv run pytest tests/ -v --timeout 60
```

Expected: all green. No collection errors from the deleted test file.

- [ ] **Step 4: Commit**

```bash
git commit -m "chore(backend): remove old HTTP-based pdf-render client"
```

---

### Task 10: Remove pdf_render_* config + backend env references

**Files:**
- Modify: `backend/src/hireloop/config.py`
- Modify: `backend/.env.example`
- Modify: `backend/tests/conftest.py`

- [ ] **Step 1: Remove three settings from config.py**

Open `backend/src/hireloop/config.py`. Find lines 46-48:
```python
pdf_render_url: str = "http://localhost:4000"
pdf_render_api_key: str = "local-dev-key"
pdf_render_timeout_s: float = 60.0
```

Delete all three lines.

- [ ] **Step 2: Remove from backend/.env.example**

Find and remove the two lines:
```
PDF_RENDER_URL=http://localhost:4000
PDF_RENDER_API_KEY=local-dev-key
```

- [ ] **Step 3: Remove from tests/conftest.py:41**

Open `backend/tests/conftest.py`. Find line 41:
```python
os.environ.setdefault("PDF_RENDER_URL", "http://localhost:4000")
```

Delete that line.

- [ ] **Step 4: Run tests and config import check**

```bash
cd backend
uv run python -c "from hireloop.config import get_settings; s = get_settings(); print('ok', not hasattr(s, 'pdf_render_url'))"
uv run pytest tests/ -v --timeout 60
```

Expected: the python one-liner prints `ok True`. Full test suite is green.

- [ ] **Step 5: Commit**

```bash
git add backend/src/hireloop/config.py backend/.env.example backend/tests/conftest.py
git commit -m "chore(backend): drop pdf_render_* config entries"
```

---

### Task 11: Local smoke test + markdown parity golden fixture (manual)

Before deleting the `pdf-render/` workspace, verify WeasyPrint output is acceptable against a real CV and that `markdown-it-py` parses equivalently to `marked`.

This task is **manual / human-in-the-loop**. There are no automated assertions beyond what `test_pdf_renderer.py` already enforces.

- [ ] **Step 1: Run backend locally**

```bash
cd /Users/parvez/projects/personal/career-agent
docker-compose up -d postgres redis localstack  # keep pdf-render OFF this round
cd backend
uv run uvicorn hireloop.main:app --reload
```

- [ ] **Step 2: Call the cv-outputs endpoint with a representative resume**

Authenticate via the dev-bypass auth (see `Justfile` / `local_dev_setup.md` memory if unsure), evaluate a job, then:

```bash
# From the local-dev tools or API
curl -X POST http://localhost:8000/cv-outputs \
  -H "Authorization: Bearer $DEV_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"job_id": "<real-job-uuid>"}'
```

- [ ] **Step 3: Download the generated PDF and inspect**

```bash
curl -L "http://localhost:8000/cv-outputs/$CV_OUTPUT_ID/pdf" -o /tmp/weasyprint-sample.pdf
open /tmp/weasyprint-sample.pdf  # macOS preview
```

**Visual check:**
- Fonts are Space Grotesk (headings) + DM Sans (body) — NOT Helvetica/Arial fallback
- A4 page size
- Footer "Generated YYYY-MM-DD" in bottom-right
- Typography is readable, no overflow, no font-loading errors

**Text extraction check** (sanity for ATS parsers):
```bash
uv run python -c "
import pypdf
reader = pypdf.PdfReader('/tmp/weasyprint-sample.pdf')
print('pages:', len(reader.pages))
print('---')
print(reader.pages[0].extract_text())
"
```

Expected: text extracts clean (no garbled characters, preserves list structure, no font-encoding issues).

- [ ] **Step 4: Markdown parity golden fixture (optional but recommended)**

Render the same markdown through both parsers and diff the HTML:

```bash
# Start pdf-render so we can compare
docker-compose up -d pdf-render
curl -sX POST http://localhost:4000/render \
  -H "Authorization: Bearer local-dev-key" \
  -H "Content-Type: application/json" \
  -d '{"markdown":"# Hi\n\n- a\n- b","template":"resume","user_id":"test","output_key":"x"}' \
  | jq .

# Now render the same markdown via markdown-it-py
cd backend
uv run python -c "
from markdown_it import MarkdownIt
md = MarkdownIt('commonmark')
print(md.render('# Hi\n\n- a\n- b'))
"
```

Compare the HTML output. Differences are acceptable if they don't affect rendering (e.g. whitespace, escaped vs. raw chars in safe zones). Layout-affecting differences (different tag choices, different nesting) need template tweaks.

- [ ] **Step 5: Stop the backend**

```bash
# Ctrl-C the uvicorn
docker-compose stop pdf-render
```

No commit for this task — it's a checkpoint.

**If the smoke test reveals a blocker** (e.g. fonts render as system fallback, or WeasyPrint layout is materially broken), STOP and iterate on the template (probably Task 3) before proceeding. Do not push task 12's workspace deletion until smoke test passes.

---

### Task 12: Delete pdf-render workspace + CI workflow + docker-compose + pnpm-workspace (atomic)

These four changes MUST land in the same commit — deleting the workspace without updating CI will break the `test-node` job on the very commit that removes the code it's supposed to test.

**Files:**
- Delete: `pdf-render/` (entire directory)
- Modify: `.github/workflows/ci.yml`
- Modify: `docker-compose.yml`
- Modify: `pnpm-workspace.yaml`
- Modify: Root `package.json` (if it references `pdf-render`)

- [ ] **Step 1: Delete the workspace directory**

```bash
git rm -r pdf-render/
```

- [ ] **Step 2: Update .github/workflows/ci.yml**

In `.github/workflows/ci.yml`, inside the `test-node` job, delete the three steps around lines 97-112 (exact line numbers may drift; match by content):

```yaml
      - name: Cache Playwright browsers
        uses: actions/cache@v4
        with:
          path: ~/.cache/ms-playwright
          key: playwright-${{ runner.os }}-${{ hashFiles('pnpm-lock.yaml') }}
      - name: Install Playwright (Chromium + system deps)
        working-directory: pdf-render
        run: pnpm exec playwright install --with-deps chromium
```

And:

```yaml
      - name: Test pdf-render (Playwright API)
        working-directory: pdf-render
        env:
          CI: true
        run: pnpm test
```

Keep the "Test user-portal (Vitest)" step and other surrounding steps.

- [ ] **Step 3: Update docker-compose.yml**

Remove the `pdf-render:` service block entirely. Check any other service with `depends_on:` listing `pdf-render` and remove that entry too (most likely `backend:` depends on it).

Verify:
```bash
grep -n "pdf-render\|pdf_render" docker-compose.yml
```

Expected: no matches.

- [ ] **Step 4: Update pnpm-workspace.yaml**

Remove the `pdf-render` entry. Final content likely looks like:

```yaml
packages:
  - "marketing"
  - "user-portal"
  - "admin-ui"
  - "infrastructure/cdk"
```

(Adjust based on what's actually there — just remove the `pdf-render` line.)

- [ ] **Step 5: Check root package.json**

```bash
grep -n "pdf-render" package.json 2>/dev/null
```

If any `scripts` reference `pdf-render` (e.g. `"build:pdf-render": "pnpm --filter @hireloop/pdf-render build"`), remove those script entries.

- [ ] **Step 6: Verify CI workflow syntax**

If `actionlint` is available:
```bash
actionlint .github/workflows/ci.yml
```

Otherwise at minimum open the file and confirm YAML indentation is valid around the removed block.

- [ ] **Step 7: Run what's runnable to confirm nothing immediately breaks**

```bash
pnpm install  # refreshes lockfile without pdf-render
cd backend && uv run pytest tests/ --timeout 60
```

Expected: pnpm install succeeds (lockfile regenerates without pdf-render deps); backend tests pass.

- [ ] **Step 8: Commit**

```bash
git add -A pdf-render/ .github/workflows/ci.yml docker-compose.yml pnpm-workspace.yaml package.json pnpm-lock.yaml
git commit -m "chore: delete pdf-render workspace (replaced by in-process WeasyPrint)"
```

---

### Task 13: CDK infrastructure cleanup

**Files:**
- Modify: `infrastructure/cdk/lib/app-stack.ts`
- Modify: `infrastructure/cdk/lib/config-stack.ts`

- [ ] **Step 1: Remove secret grant + env vars from app-stack.ts**

In `infrastructure/cdk/lib/app-stack.ts`:

At line ~42, remove the `PDF_RENDER_SHARED_SECRET` entry from the `buildApiEnv` return object:
```typescript
PDF_RENDER_SHARED_SECRET: readJson(`hireloop/${env}/pdf-render-shared-secret`, 'key'),
```

At line ~51, remove the `PDF_RENDER_URL: ""` placeholder:
```typescript
PDF_RENDER_URL: "",
```

At line ~201, remove the `hireloop/${env}/pdf-render-shared-secret` entry from the list of secrets the Lambda role has `grantRead` access to.

Find the surrounding context with:
```bash
grep -n "pdf-render-shared-secret\|PDF_RENDER" infrastructure/cdk/lib/app-stack.ts
```

Ensure all three references are removed.

- [ ] **Step 2: Remove seed from config-stack.ts**

In `infrastructure/cdk/lib/config-stack.ts` at line ~34, remove:
```typescript
emptyJson("pdf-render-shared-secret"),
```

(The surrounding array of `emptyJson(...)` calls seeds the 7 `hireloop/<env>/*` secrets. Removing this entry means next CDK deploy won't try to create the empty secret — the existing secret in AWS will still be deleted via the post-deploy cleanup in Task 17.)

- [ ] **Step 3: Synth the stack locally to verify no TypeScript errors**

```bash
cd infrastructure/cdk
npx cdk synth HireLoop-App-dev HireLoop-Config-dev 2>&1 | head -40
```

Expected: CDK synth completes without "Cannot find name" or type errors. It may still fail the deploy-time AWS API calls (if AWS_PROFILE isn't set), but synth should pass.

- [ ] **Step 4: Commit**

```bash
git add infrastructure/cdk/lib/app-stack.ts infrastructure/cdk/lib/config-stack.ts
git commit -m "chore(infra): remove PDF_RENDER_* secret + env var from CDK"
```

---

### Task 14: Infrastructure scripts + env examples

**Files:**
- Modify: `infrastructure/scripts/populate-dev-secrets.sh`
- Modify: `infrastructure/.env.deploy.local.example`

- [ ] **Step 1: Remove PDF_RENDER_SHARED_SECRET from populate-dev-secrets.sh**

In `infrastructure/scripts/populate-dev-secrets.sh`:

1. Remove line `require PDF_RENDER_SHARED_SECRET` (currently line ~33)
2. Remove line `put_json_key "hireloop/dev/pdf-render-shared-secret" "$PDF_RENDER_SHARED_SECRET"` (currently line ~54)
3. Update the final echo from `"Updated 7 manual secrets..."` to `"Updated 6 manual secrets..."`

- [ ] **Step 2: Remove from infrastructure/.env.deploy.local.example**

Delete the line:
```
export PDF_RENDER_SHARED_SECRET=
```

- [ ] **Step 3: (Local only, not committed) Remove from your .env.deploy.local**

```bash
sed -i.bak '/^export PDF_RENDER_SHARED_SECRET=/d' infrastructure/.env.deploy.local
rm infrastructure/.env.deploy.local.bak
```

- [ ] **Step 4: Dry-run the script to catch errors**

```bash
AWS_PROFILE=hireloop bash -n infrastructure/scripts/populate-dev-secrets.sh
echo "syntax OK"
```

Expected: `syntax OK`.

- [ ] **Step 5: Run the script (idempotent — safe to re-run)**

```bash
AWS_PROFILE=hireloop bash infrastructure/scripts/populate-dev-secrets.sh 2>&1 | tail -5
```

Expected: "Updated 6 manual secrets under hireloop/dev/*". The `hireloop/dev/pdf-render-shared-secret` secret is NOT touched here (it still exists in AWS; Task 17 deletes it).

- [ ] **Step 6: Commit**

```bash
git add infrastructure/scripts/populate-dev-secrets.sh infrastructure/.env.deploy.local.example
git commit -m "chore(infra): drop PDF_RENDER_SHARED_SECRET from populate script"
```

---

### Task 15: Cosmetic cleanup (Justfile comment + docstring)

**Files:**
- Modify: `Justfile`
- Modify: `backend/src/hireloop/core/cv_optimizer/__init__.py`

- [ ] **Step 1: Update Justfile up target comment**

In `Justfile`, change line ~63 from:
```
# Docker compose up (postgres, redis, inngest, localstack, pdf-render)
```
to:
```
# Docker compose up (postgres, redis, inngest, localstack)
```

- [ ] **Step 2: Update cv_optimizer __init__.py docstring**

In `backend/src/hireloop/core/cv_optimizer/__init__.py`, change line 1:

From:
```python
"""CV optimizer module — Claude rewriter + pdf-render client + service."""
```

To:
```python
"""CV optimizer module — Claude rewriter + in-process PDF renderer + service."""
```

- [ ] **Step 3: Commit**

```bash
git add Justfile backend/src/hireloop/core/cv_optimizer/__init__.py
git commit -m "chore: update stale pdf-render comments + docstrings"
```

---

### Task 16: Full verification + push

- [ ] **Step 1: Run the full backend test suite**

```bash
cd backend
uv run pytest tests/ -v --timeout 60
```

Expected: all tests green, no collection errors, no deprecation warnings from any pdf-render import.

- [ ] **Step 2: Run ruff + black + mypy**

```bash
cd backend
uv run ruff check src/
uv run black --check src/
uv run mypy src/
```

Expected: all three exit 0. If mypy complains about `weasyprint` or `markdown_it` stubs, add to `pyproject.toml`'s `[[tool.mypy.overrides]]` block (following the existing pattern at line 78-80):

```toml
[[tool.mypy.overrides]]
module = ["weasyprint.*", "markdown_it.*"]
ignore_missing_imports = true
```

If you need this change, commit it as:
```bash
git add backend/pyproject.toml
git commit -m "chore(backend): mypy stubs ignore for weasyprint + markdown_it"
```

- [ ] **Step 3: Build the backend Lambda image one more time**

```bash
cd backend
podman build --target lambda -t hireloop-backend:final-check .
podman run --rm hireloop-backend:final-check python3 -c "
import weasyprint
from hireloop.core.cv_optimizer.pdf_renderer import render_pdf, PdfRenderError
print('all imports OK')
"
```

Expected: `all imports OK`.

- [ ] **Step 4: Push all commits**

```bash
cd /Users/parvez/projects/personal/career-agent
git push origin main
```

Expected: pushed to `github.com/parvez301/hireloop`, CI kicks off, all green.

- [ ] **Step 5: Watch CI**

```bash
gh run watch --exit-status
```

Expected: `test-node`, `test-python`, `cdk-synth`, `lint` all green. If `test-python` fails with `ModuleNotFoundError: weasyprint` during collection, the wheel isn't shipping the system libs — this is a CI-runner issue (CI runs tests outside the Docker image); add the `apt-get install` for Cairo/Pango to the `test-python` job as a one-liner.

---

### Task 17: Post-deploy AWS cleanup (deferred — run after next backend deploy)

Only do this task **after** the backend with WeasyPrint has been deployed to AWS and is serving traffic successfully. The secret lingering in AWS Secrets Manager costs $0.40/month and the ECR repo (if created) is free — neither is urgent.

**Files/resources touched (AWS, not repo):**
- AWS Secrets Manager: `hireloop/dev/pdf-render-shared-secret`
- AWS ECR (optional): `hireloop-pdf-render` (if ever created)

- [ ] **Step 1: Confirm backend is running in AWS and generating PDFs correctly**

After HireLoop-App-dev is deployed with the new Dockerfile:
```bash
# Using DEV_SMOKE_TOKEN (see phase_5a2_brainstorm.md memory)
curl -sX POST "https://api.dev.hireloop.xyz/cv-outputs" \
  -H "Authorization: Bearer $DEV_SMOKE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"job_id":"<real-uuid>"}' | jq .

# Download the PDF
curl -L "https://api.dev.hireloop.xyz/cv-outputs/$ID/pdf" -o /tmp/prod-sample.pdf
file /tmp/prod-sample.pdf  # expect: PDF document, version 1.7
```

If this succeeds, continue. If it fails, investigate (most likely fontconfig cache or Cairo lib not found in Lambda) before deleting the legacy secret.

- [ ] **Step 2: Delete the Secrets Manager secret**

```bash
AWS_PROFILE=hireloop aws secretsmanager delete-secret \
  --secret-id hireloop/dev/pdf-render-shared-secret \
  --recovery-window-in-days 7 \
  --region us-east-1
```

Expected: JSON response with `DeletionDate` 7 days out. The secret is recoverable for 7 days — leave it in pending-deletion state as a safety net.

- [ ] **Step 3: Check if hireloop-pdf-render ECR repo exists**

```bash
AWS_PROFILE=hireloop aws ecr describe-repositories \
  --repository-names hireloop-pdf-render \
  --region us-east-1 2>&1
```

Two possible outcomes:
- `RepositoryNotFoundException` — no repo was ever created (the workspace was never deployed). No action.
- Returns the repo description — continue to step 4.

- [ ] **Step 4 (conditional): Delete the ECR repo**

```bash
AWS_PROFILE=hireloop aws ecr delete-repository \
  --repository-name hireloop-pdf-render \
  --force \
  --region us-east-1
```

- [ ] **Step 5: Update `infrastructure/scripts/ensure-ecr-repos.sh` if it references hireloop-pdf-render**

```bash
grep -n "hireloop-pdf-render" infrastructure/scripts/ensure-ecr-repos.sh 2>/dev/null
```

If the script tries to create this repo, remove the relevant lines, then:
```bash
git add infrastructure/scripts/ensure-ecr-repos.sh
git commit -m "chore(infra): drop hireloop-pdf-render from ECR ensure script"
git push origin main
```

Otherwise, no code change needed.

---

## Self-review checklist (run before handing off)

Before kicking off execution, skim the plan against the spec:

- [ ] §4 "Module layout changes" — every created/deleted path has a task? ✅ (Tasks 2, 3, 4, 9, 12)
- [ ] §5 "Rendering pipeline" — the full `pdf_renderer.py` module is written verbatim in Task 2 step 3? ✅
- [ ] §6 templates — resume.html port covered in Task 3? ✅ — cover_letter.html in Task 4? ✅
- [ ] §7 Dockerfile — Cairo/Pango + fontconfig cache + Hatchling artifacts all addressed? ✅ (Tasks 6, 7)
- [ ] §9 tests — all 6 tests explicit? ✅ (Task 5)
- [ ] §10 deletion checklist — every item has a task? ✅ (Tasks 9, 10, 12, 13, 14, 15)
- [ ] §11 implementation sequence — numbered steps roughly match? ✅
- [ ] §12 rollback — not in plan (it's a "break glass" procedure, not a planned task) — documented in spec, fine

**Placeholder scan:** No `TBD`, no `TODO`, no vague "add error handling", no "similar to task N" — all code blocks present. ✅

**Type consistency:** `PdfRenderError`, `RenderResult`, `render_pdf` signature (`markdown: str, template: TemplateName, user_id: UUID, output_key: str`) consistent across tasks 2, 5, 8. ✅
