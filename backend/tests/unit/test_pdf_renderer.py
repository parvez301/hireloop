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


@pytest.fixture(autouse=True)
def _reset_caches() -> None:
    """Reset lru_cache on singletons so each test sees the current env/mock."""
    get_settings.cache_clear()
    get_s3_client.cache_clear()


@pytest.fixture
def _s3_mock(monkeypatch: pytest.MonkeyPatch) -> object:
    """Moto-mocked S3 with the configured bucket pre-created."""
    # If .env points boto3 at LocalStack, moto's mock is bypassed. `delenv` alone is not
    # enough: pydantic-settings would still read AWS_ENDPOINT_URL from the env file.
    monkeypatch.setenv("AWS_ENDPOINT_URL", "")
    get_settings.cache_clear()
    get_s3_client.cache_clear()
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
