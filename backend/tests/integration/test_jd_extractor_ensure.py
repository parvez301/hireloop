"""Integration tests for jd_extractor.ensure_jd_structure().

Covers idempotency (skip when already populated), happy-path persistence,
and the fail-soft path where a Groq error leaves parsed_jd_json null.
"""

from __future__ import annotations

import hashlib
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from hireloop.core.llm.errors import LLMError
from hireloop.db import get_session_factory
from hireloop.models.job import Job
from hireloop.services.jd_extractor import ensure_jd_structure


async def _make_job(description: str, parsed_jd_json: dict | None = None) -> Job:
    factory = get_session_factory()
    async with factory() as session:
        h = hashlib.sha256(f"jd-{uuid4()}".encode()).hexdigest()
        job = Job(
            content_hash=h,
            title="Staff Engineer",
            description_md=description,
            requirements_json={},
            parsed_jd_json=parsed_jd_json,
            source="manual",
        )
        session.add(job)
        await session.commit()
        await session.refresh(job)
        return job


_PAYLOAD = {
    "title": "Staff Backend Engineer",
    "company": "Stripe",
    "seniority": "senior",
    "must_have_skills": ["Python"],
    "nice_to_have_skills": [],
    "years_experience_required": 7,
    "management_required": False,
    "key_responsibilities": [],
    "red_flag_requirements": [],
    "company_stage": "scaleup",
    "remote_policy": "hybrid",
    "salary_range": "",
    "application_questions": [],
}


@pytest.mark.asyncio
async def test_ensure_extracts_and_persists_when_null() -> None:
    job = await _make_job("Senior backend role at Stripe...")

    factory = get_session_factory()
    async with factory() as session:
        live = await session.get(Job, job.id)
        assert live is not None and live.parsed_jd_json is None
        with patch(
            "hireloop.services.jd_extractor.groq_client.complete_json",
            new=AsyncMock(return_value=dict(_PAYLOAD)),
        ):
            result = await ensure_jd_structure(session, live)
        await session.commit()
        assert result is not None
        assert result["company"] == "Stripe"
        assert live.parsed_jd_json is not None
        assert live.parsed_jd_json["seniority"] == "senior"


@pytest.mark.asyncio
async def test_ensure_is_idempotent_when_already_populated() -> None:
    existing = {"title": "cached", "must_have_skills": ["go"]}
    job = await _make_job("JD text", parsed_jd_json=existing)

    factory = get_session_factory()
    async with factory() as session:
        live = await session.get(Job, job.id)
        assert live is not None
        mock_call = AsyncMock()
        with patch("hireloop.services.jd_extractor.groq_client.complete_json", new=mock_call):
            result = await ensure_jd_structure(session, live)
        assert result == existing
        mock_call.assert_not_called()


@pytest.mark.asyncio
async def test_ensure_returns_none_on_llm_failure() -> None:
    job = await _make_job("JD text")

    factory = get_session_factory()
    async with factory() as session:
        live = await session.get(Job, job.id)
        assert live is not None
        with patch(
            "hireloop.services.jd_extractor.groq_client.complete_json",
            new=AsyncMock(side_effect=LLMError("groq down", provider="groq")),
        ):
            result = await ensure_jd_structure(session, live)
        assert result is None
        assert live.parsed_jd_json is None
