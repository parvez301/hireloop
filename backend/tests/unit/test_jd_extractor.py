"""Tests for Layer-3 structured JD extraction (services/jd_extractor.py)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from hireloop.core.llm.errors import LLMError
from hireloop.services.jd_extractor import extract_jd_structure

_FULL_PAYLOAD = {
    "title": "Staff Backend Engineer",
    "company": "Stripe",
    "seniority": "senior",
    "must_have_skills": ["Python", "PostgreSQL", "distributed systems"],
    "nice_to_have_skills": ["Kubernetes", "Greenhouse API"],
    "years_experience_required": 7,
    "management_required": False,
    "key_responsibilities": [
        "Own the billing pipeline end-to-end",
        "Mentor mid-level engineers",
    ],
    "red_flag_requirements": ["10+ years React"],
    "company_stage": "scaleup",
    "remote_policy": "hybrid",
    "salary_range": "$200k–$260k base",
    "application_questions": ["Why Stripe?"],
}


@pytest.mark.asyncio
async def test_extracts_full_jd_structure() -> None:
    with patch(
        "hireloop.services.jd_extractor.groq_client.complete_json",
        new=AsyncMock(return_value=dict(_FULL_PAYLOAD)),
    ):
        result = await extract_jd_structure("Senior Engineer at Stripe...")
    assert result is not None
    assert result["title"] == "Staff Backend Engineer"
    assert result["seniority"] == "senior"
    assert result["company_stage"] == "scaleup"
    assert result["remote_policy"] == "hybrid"
    assert result["years_experience_required"] == 7
    assert "Python" in result["must_have_skills"]
    assert result["management_required"] is False


@pytest.mark.asyncio
async def test_invalid_enum_values_drop_to_empty() -> None:
    payload = dict(_FULL_PAYLOAD)
    payload["seniority"] = "principal"
    payload["company_stage"] = "soonicorn"
    payload["remote_policy"] = "anywhere"
    with patch(
        "hireloop.services.jd_extractor.groq_client.complete_json",
        new=AsyncMock(return_value=payload),
    ):
        result = await extract_jd_structure("JD")
    assert result is not None
    assert result["seniority"] == ""
    assert result["company_stage"] == ""
    assert result["remote_policy"] == ""


@pytest.mark.asyncio
async def test_empty_jd_short_circuits_without_calling_llm() -> None:
    mock_call = AsyncMock()
    with patch("hireloop.services.jd_extractor.groq_client.complete_json", new=mock_call):
        result = await extract_jd_structure("")
    assert result is None
    mock_call.assert_not_called()


@pytest.mark.asyncio
async def test_llm_failure_returns_none_not_raises() -> None:
    with patch(
        "hireloop.services.jd_extractor.groq_client.complete_json",
        new=AsyncMock(side_effect=LLMError("groq 503", provider="groq")),
    ):
        result = await extract_jd_structure("JD content")
    assert result is None


@pytest.mark.asyncio
async def test_partial_payload_still_normalises() -> None:
    with patch(
        "hireloop.services.jd_extractor.groq_client.complete_json",
        new=AsyncMock(return_value={"title": "Engineer"}),
    ):
        result = await extract_jd_structure("JD")
    assert result is not None
    assert result["title"] == "Engineer"
    assert result["must_have_skills"] == []
    assert result["years_experience_required"] == 0
    assert result["management_required"] is False


@pytest.mark.asyncio
async def test_management_required_coerces_string_truthy() -> None:
    payload = dict(_FULL_PAYLOAD)
    payload["management_required"] = "yes"
    with patch(
        "hireloop.services.jd_extractor.groq_client.complete_json",
        new=AsyncMock(return_value=payload),
    ):
        result = await extract_jd_structure("JD")
    assert result is not None
    assert result["management_required"] is True
