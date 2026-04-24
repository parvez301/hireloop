"""Tests for the Layer-4 cross-reference map extractor."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from hireloop.core.llm.errors import LLMError
from hireloop.services.crossref import extract_crossref_map

_CV = {
    "roles": [{"title": "Senior Engineer", "company": "Stripe", "key_achievements": ["X"]}],
    "hard_skills": ["python", "go"],
}
_JD = {
    "title": "Staff Engineer",
    "must_have_skills": ["python"],
    "nice_to_have_skills": ["kubernetes"],
}


_FULL_PAYLOAD = {
    "strong_matches": [
        {
            "jd_requirement": "Python proficiency",
            "cv_evidence": "Senior Engineer at Stripe (Python)",
            "strength": "strong",
        }
    ],
    "gaps": [
        {
            "jd_requirement": "Kubernetes",
            "gap_severity": "minor",
            "mitigation": "AWS ECS background as a bridge",
        }
    ],
    "unique_angles": ["Cross-border payments experience"],
    "overall_fit_score": "B+",
    "fit_summary": "Strong Python match with one minor gap.",
}


@pytest.mark.asyncio
async def test_extracts_full_map() -> None:
    with patch(
        "hireloop.services.crossref.gemini_client.extract_json",
        new=AsyncMock(return_value=dict(_FULL_PAYLOAD)),
    ):
        result = await extract_crossref_map(_CV, _JD)
    assert result is not None
    assert result["overall_fit_score"] == "B+"
    assert result["strong_matches"][0]["strength"] == "strong"
    assert result["gaps"][0]["gap_severity"] == "minor"
    assert result["unique_angles"] == ["Cross-border payments experience"]


@pytest.mark.asyncio
async def test_invalid_enums_drop_to_empty() -> None:
    payload = {
        "strong_matches": [{"jd_requirement": "X", "cv_evidence": "Y", "strength": "incredible"}],
        "gaps": [{"jd_requirement": "Z", "gap_severity": "moderate-ish"}],
        "overall_fit_score": "A++",
    }
    with patch(
        "hireloop.services.crossref.gemini_client.extract_json",
        new=AsyncMock(return_value=payload),
    ):
        result = await extract_crossref_map(_CV, _JD)
    assert result is not None
    assert result["strong_matches"][0]["strength"] == ""
    assert result["gaps"][0]["gap_severity"] == ""
    assert result["overall_fit_score"] == ""


@pytest.mark.asyncio
async def test_drops_match_without_jd_or_cv_text() -> None:
    payload = {
        "strong_matches": [
            {"jd_requirement": "", "cv_evidence": "", "strength": "strong"},
            {"jd_requirement": "Python", "cv_evidence": "Stripe role", "strength": "strong"},
        ]
    }
    with patch(
        "hireloop.services.crossref.gemini_client.extract_json",
        new=AsyncMock(return_value=payload),
    ):
        result = await extract_crossref_map(_CV, _JD)
    assert result is not None
    assert len(result["strong_matches"]) == 1
    assert result["strong_matches"][0]["jd_requirement"] == "Python"


@pytest.mark.asyncio
async def test_empty_inputs_short_circuit() -> None:
    mock_call = AsyncMock()
    with patch("hireloop.services.crossref.gemini_client.extract_json", new=mock_call):
        assert await extract_crossref_map({}, _JD) is None
        assert await extract_crossref_map(_CV, {}) is None
    mock_call.assert_not_called()


@pytest.mark.asyncio
async def test_llm_failure_returns_none() -> None:
    with patch(
        "hireloop.services.crossref.gemini_client.extract_json",
        new=AsyncMock(side_effect=LLMError("gemini down", provider="gemini")),
    ):
        result = await extract_crossref_map(_CV, _JD)
    assert result is None


@pytest.mark.asyncio
async def test_grade_uppercased() -> None:
    payload = dict(_FULL_PAYLOAD)
    payload["overall_fit_score"] = "b+"
    with patch(
        "hireloop.services.crossref.gemini_client.extract_json",
        new=AsyncMock(return_value=payload),
    ):
        result = await extract_crossref_map(_CV, _JD)
    assert result is not None
    assert result["overall_fit_score"] == "B+"
