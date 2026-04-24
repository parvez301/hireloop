"""Tests for Layer-1 profile extraction (services/profile_extractor.py).

Verifies the extraction prompt structure, normalisation rules (drop empty /
zero / invalid values), and the merge-into-profile guard that preserves
user-supplied onboarding answers.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from hireloop.core.llm.errors import LLMError
from hireloop.models.profile import Profile
from hireloop.services.profile_extractor import (
    ExtractedProfile,
    extract_profile_from_cv,
    merge_extracted_into_profile,
)


def _profile(**overrides: object) -> Profile:
    profile = Profile(user_id=uuid4(), onboarding_state="resume_upload")
    for key, value in overrides.items():
        setattr(profile, key, value)
    return profile


# ---------------------------------------------------------------------------
# Normalisation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_extracts_all_inferable_fields() -> None:
    payload = {
        "headline": "Head of Logistics Technology",
        "years_experience": 9,
        "seniority_level": "senior",
        "industry": "logistics",
        "specialisation": "platform integrations, billing systems",
        "top_strengths": ["API integration", "team leadership"],
        "certifications": ["AWS SAA", "PMP"],
        "languages": ["English", "Urdu", "Arabic (basic)"],
    }
    with patch(
        "hireloop.services.profile_extractor.gemini_client.extract_json",
        new=AsyncMock(return_value=payload),
    ):
        result = await extract_profile_from_cv("# CV\n\n...")
    assert result.headline == "Head of Logistics Technology"
    assert result.years_experience == 9
    assert result.seniority_level == "senior"
    assert result.industry == "logistics"
    assert result.top_strengths == ["API integration", "team leadership"]
    assert result.certifications == ["AWS SAA", "PMP"]
    assert result.languages == ["English", "Urdu", "Arabic (basic)"]


@pytest.mark.asyncio
async def test_drops_empty_strings_and_zero_years() -> None:
    payload = {
        "headline": "  ",
        "years_experience": 0,
        "seniority_level": "junior|mid|senior|exec",  # template echoed back
        "industry": "",
        "specialisation": "",
        "top_strengths": ["", "  "],
        "certifications": [],
        "languages": None,
    }
    with patch(
        "hireloop.services.profile_extractor.gemini_client.extract_json",
        new=AsyncMock(return_value=payload),
    ):
        result = await extract_profile_from_cv("# CV")
    # Empty extraction — every field should round-trip as None.
    assert result == ExtractedProfile()


@pytest.mark.asyncio
async def test_invalid_seniority_level_is_dropped() -> None:
    payload = {"seniority_level": "principal", "years_experience": 4}
    with patch(
        "hireloop.services.profile_extractor.gemini_client.extract_json",
        new=AsyncMock(return_value=payload),
    ):
        result = await extract_profile_from_cv("# CV")
    assert result.seniority_level is None
    assert result.years_experience == 4


@pytest.mark.asyncio
async def test_empty_cv_text_short_circuits_without_calling_llm() -> None:
    mock_call = AsyncMock()
    with patch(
        "hireloop.services.profile_extractor.gemini_client.extract_json", new=mock_call
    ):
        result = await extract_profile_from_cv("   ")
    assert result == ExtractedProfile()
    mock_call.assert_not_called()


@pytest.mark.asyncio
async def test_llm_failure_returns_empty_extraction_not_raises() -> None:
    with patch(
        "hireloop.services.profile_extractor.gemini_client.extract_json",
        new=AsyncMock(side_effect=LLMError("gemini down", provider="gemini")),
    ):
        result = await extract_profile_from_cv("# CV")
    assert result == ExtractedProfile()


# ---------------------------------------------------------------------------
# Merge guard — user input always wins
# ---------------------------------------------------------------------------


def test_merge_only_fills_empty_fields() -> None:
    profile = _profile(headline="Existing headline", industry=None)
    extracted = ExtractedProfile(
        headline="Inferred headline",
        industry="logistics",
        years_experience=9,
    )
    updated = merge_extracted_into_profile(profile, extracted)
    assert profile.headline == "Existing headline"  # user input wins
    assert profile.industry == "logistics"
    assert profile.years_experience == 9
    assert "industry" in updated
    assert "years_experience" in updated
    assert "headline" not in updated


def test_merge_treats_empty_list_as_unset() -> None:
    profile = _profile(top_strengths=[])
    extracted = ExtractedProfile(top_strengths=["leadership"])
    merge_extracted_into_profile(profile, extracted)
    assert profile.top_strengths == ["leadership"]


def test_merge_returns_empty_when_extraction_is_empty() -> None:
    profile = _profile()
    updated = merge_extracted_into_profile(profile, ExtractedProfile())
    assert updated == []
