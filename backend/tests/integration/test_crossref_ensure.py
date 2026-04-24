"""Integration tests for crossref.ensure_crossref_map().

Covers the lazy-build cache contract: idempotency, JD extraction cascade,
fail-soft when CV structure is missing or LLM calls fail.
"""

from __future__ import annotations

import hashlib
from typing import Any
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from sqlalchemy import select

from hireloop.db import get_session_factory
from hireloop.models.crossref_map import CrossrefMap
from hireloop.models.job import Job
from hireloop.models.profile import Profile
from hireloop.models.user import User
from hireloop.services.crossref import ensure_crossref_map

_CV_STRUCTURE = {
    "roles": [{"title": "Senior Engineer", "company": "Stripe", "key_achievements": ["X"]}],
    "hard_skills": ["python"],
}
_JD_STRUCTURE = {
    "title": "Staff Engineer",
    "must_have_skills": ["python"],
    "company_stage": "scaleup",
}
_CROSSREF_BODY: dict[str, Any] = {
    "strong_matches": [{"jd_requirement": "Python", "cv_evidence": "Stripe", "strength": "strong"}],
    "gaps": [],
    "unique_angles": ["Cross-border payments"],
    "overall_fit_score": "A",
    "fit_summary": "Strong match.",
}


async def _seed_user_profile_job(
    *,
    cv_structure: dict[str, Any] | None = None,
    parsed_jd_json: dict[str, Any] | None = None,
) -> tuple[User, Profile, Job]:
    factory = get_session_factory()
    async with factory() as session:
        user = User(
            cognito_sub=f"crossref-test-{uuid4()}",
            email=f"crossref-{uuid4()}@example.com",
            name="Test",
        )
        session.add(user)
        await session.flush()

        parsed_resume_json: dict[str, Any] = {"text": "raw cv", "content_type": "text/markdown"}
        if cv_structure is not None:
            parsed_resume_json["structure"] = cv_structure
        profile = Profile(
            user_id=user.id,
            onboarding_state="done",
            master_resume_md="# CV",
            parsed_resume_json=parsed_resume_json,
        )
        session.add(profile)

        h = hashlib.sha256(f"crossref-job-{uuid4()}".encode()).hexdigest()
        job = Job(
            content_hash=h,
            title="Staff Engineer",
            description_md="Job description text",
            requirements_json={},
            parsed_jd_json=parsed_jd_json,
            source="manual",
        )
        session.add(job)

        await session.commit()
        await session.refresh(user)
        await session.refresh(profile)
        await session.refresh(job)
        return user, profile, job


@pytest.mark.asyncio
async def test_ensure_extracts_persists_and_returns_row() -> None:
    user, profile, job = await _seed_user_profile_job(
        cv_structure=_CV_STRUCTURE, parsed_jd_json=_JD_STRUCTURE
    )

    factory = get_session_factory()
    async with factory() as session:
        live_profile = await session.get(Profile, profile.id)
        live_job = await session.get(Job, job.id)
        assert live_profile is not None and live_job is not None

        with patch(
            "hireloop.services.crossref.gemini_client.extract_json",
            new=AsyncMock(return_value=dict(_CROSSREF_BODY)),
        ):
            row = await ensure_crossref_map(session, live_profile, live_job)
        await session.commit()
        assert row is not None
        assert row.user_id == user.id
        assert row.job_id == job.id
        assert row.body["overall_fit_score"] == "A"
        assert row.model_used  # populated from settings.gemini_model


@pytest.mark.asyncio
async def test_ensure_is_idempotent_when_cached() -> None:
    user, profile, job = await _seed_user_profile_job(
        cv_structure=_CV_STRUCTURE, parsed_jd_json=_JD_STRUCTURE
    )

    factory = get_session_factory()
    async with factory() as session:
        live_profile = await session.get(Profile, profile.id)
        live_job = await session.get(Job, job.id)
        assert live_profile is not None and live_job is not None

        # First call extracts.
        with patch(
            "hireloop.services.crossref.gemini_client.extract_json",
            new=AsyncMock(return_value=dict(_CROSSREF_BODY)),
        ):
            first = await ensure_crossref_map(session, live_profile, live_job)
        await session.commit()
        assert first is not None

        # Second call must NOT hit the LLM.
        mock_call = AsyncMock()
        with patch("hireloop.services.crossref.gemini_client.extract_json", new=mock_call):
            second = await ensure_crossref_map(session, live_profile, live_job)
        assert second is not None
        assert second.id == first.id
        mock_call.assert_not_called()


@pytest.mark.asyncio
async def test_ensure_returns_none_when_cv_structure_missing() -> None:
    user, profile, job = await _seed_user_profile_job(
        cv_structure=None, parsed_jd_json=_JD_STRUCTURE
    )

    factory = get_session_factory()
    async with factory() as session:
        live_profile = await session.get(Profile, profile.id)
        live_job = await session.get(Job, job.id)
        assert live_profile is not None and live_job is not None

        mock_call = AsyncMock()
        with patch("hireloop.services.crossref.gemini_client.extract_json", new=mock_call):
            row = await ensure_crossref_map(session, live_profile, live_job)
        assert row is None
        # LLM not called — profile has no structure.
        mock_call.assert_not_called()
        # No row persisted.
        result = await session.execute(
            select(CrossrefMap).where(CrossrefMap.user_id == user.id, CrossrefMap.job_id == job.id)
        )
        assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_ensure_cascades_jd_extraction_when_missing() -> None:
    """When job.parsed_jd_json is None, the service should extract it transparently."""
    user, profile, job = await _seed_user_profile_job(
        cv_structure=_CV_STRUCTURE, parsed_jd_json=None
    )

    factory = get_session_factory()
    async with factory() as session:
        live_profile = await session.get(Profile, profile.id)
        live_job = await session.get(Job, job.id)
        assert live_profile is not None and live_job is not None

        # Two LLM calls expected — JD extraction (groq) then crossref (gemini).
        with (
            patch(
                "hireloop.services.jd_extractor.groq_client.complete_json",
                new=AsyncMock(
                    return_value={
                        "title": "Staff Engineer",
                        "must_have_skills": ["python"],
                    }
                ),
            ),
            patch(
                "hireloop.services.crossref.gemini_client.extract_json",
                new=AsyncMock(return_value=dict(_CROSSREF_BODY)),
            ),
        ):
            row = await ensure_crossref_map(session, live_profile, live_job)
        await session.commit()
        assert row is not None
        # JD was persisted as a side effect.
        await session.refresh(live_job)
        assert live_job.parsed_jd_json is not None
        assert live_job.parsed_jd_json["title"] == "Staff Engineer"
