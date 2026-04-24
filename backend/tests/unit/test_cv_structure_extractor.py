"""Tests for Layer-2 structured CV extraction."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from hireloop.core.llm.errors import LLMError
from hireloop.services.cv_structure_extractor import extract_cv_structure


@pytest.mark.asyncio
async def test_extracts_full_structure_from_payload() -> None:
    payload = {
        "roles": [
            {
                "title": "Head of Logistics Technology",
                "company": "RSA Global",
                "duration_months": 48,
                "start_year": 2022,
                "end_year": 2026,
                "key_achievements": [
                    "Built SMSA Express integration that reduced billing errors by 40%",
                    "Led 3-country team of 12 engineers",
                ],
                "technologies": ["AWS ECS", "Python", "Greenhouse API"],
                "team_size_managed": 12,
                "budget_managed": "$2M",
            }
        ],
        "education": [{"degree": "BS Computer Science", "institution": "MIT", "year": 2015}],
        "hard_skills": ["python", "aws", "kubernetes"],
        "soft_skills": ["leadership", "negotiation"],
        "notable_numbers": [
            "Reduced billing errors by 40%",
            "Managed team of 12 across 3 countries",
        ],
        "certifications": ["AWS SAA"],
        "career_narrative": "Engineer turned platform leader at logistics scaleup.",
    }
    with patch(
        "hireloop.services.cv_structure_extractor.gemini_client.extract_json",
        new=AsyncMock(return_value=payload),
    ):
        result = await extract_cv_structure("# CV\n\n...")
    assert result is not None
    assert len(result["roles"]) == 1
    assert result["roles"][0]["company"] == "RSA Global"
    assert result["roles"][0]["team_size_managed"] == 12
    assert result["education"][0]["degree"] == "BS Computer Science"
    assert "python" in result["hard_skills"]
    assert len(result["notable_numbers"]) == 2
    assert result["career_narrative"].startswith("Engineer")


@pytest.mark.asyncio
async def test_drops_empty_template_role() -> None:
    """Roles with empty title/company/achievements are template echoes — drop them."""
    payload = {
        "roles": [
            {"title": "", "company": "", "key_achievements": []},
            {"title": "Senior Engineer", "company": "Stripe", "key_achievements": ["X"]},
        ]
    }
    with patch(
        "hireloop.services.cv_structure_extractor.gemini_client.extract_json",
        new=AsyncMock(return_value=payload),
    ):
        result = await extract_cv_structure("# CV")
    assert result is not None
    assert len(result["roles"]) == 1
    assert result["roles"][0]["company"] == "Stripe"


@pytest.mark.asyncio
async def test_empty_cv_short_circuits_without_calling_llm() -> None:
    mock_call = AsyncMock()
    with patch(
        "hireloop.services.cv_structure_extractor.gemini_client.extract_json", new=mock_call
    ):
        result = await extract_cv_structure("   ")
    assert result is None
    mock_call.assert_not_called()


@pytest.mark.asyncio
async def test_llm_failure_returns_none() -> None:
    with patch(
        "hireloop.services.cv_structure_extractor.gemini_client.extract_json",
        new=AsyncMock(side_effect=LLMError("gemini down", provider="gemini")),
    ):
        result = await extract_cv_structure("# CV")
    assert result is None


@pytest.mark.asyncio
async def test_normalises_missing_top_level_fields() -> None:
    """Partial payload should still produce a complete normalised dict."""
    with patch(
        "hireloop.services.cv_structure_extractor.gemini_client.extract_json",
        new=AsyncMock(return_value={"hard_skills": ["python"]}),
    ):
        result = await extract_cv_structure("# CV")
    assert result is not None
    assert result["roles"] == []
    assert result["education"] == []
    assert result["hard_skills"] == ["python"]
    assert result["career_narrative"] == ""


@pytest.mark.asyncio
async def test_drops_non_string_skills() -> None:
    payload = {"hard_skills": ["python", 42, None, "  ", "aws"]}
    with patch(
        "hireloop.services.cv_structure_extractor.gemini_client.extract_json",
        new=AsyncMock(return_value=payload),
    ):
        result = await extract_cv_structure("# CV")
    assert result is not None
    assert result["hard_skills"] == ["python", "aws"]
