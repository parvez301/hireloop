"""Phase 7c regression tests — interview prep dispatches to Gemini by default.

Per the model-routing strategy doc, Task.INTERVIEW_QUESTIONS is BALANCED tier
(Gemini Flash). The legacy Sonnet path stays available via provider="anthropic".
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from hireloop.core.interview_prep.generator import generate_interview_prep

_GEMINI_PAYLOAD = {
    "questions": [
        {
            "question": "Walk me through your largest billing pipeline migration.",
            "category": "behavioral",
            "suggested_story_title": "SMSA migration",
            "framework": "STAR. Lead with the constraint that drove the design.",
        }
    ],
    "red_flag_questions": [
        {
            "question": "How does the team handle prod incidents at 3am?",
            "what_to_listen_for": "Concrete on-call rotation, not 'we figure it out'.",
        }
    ],
}


@pytest.mark.asyncio
async def test_explicit_gemini_provider_dispatches_to_gemini() -> None:
    """Test conftest pins INTERVIEW_PREP_PROVIDER=anthropic for legacy fake_anthropic
    flows; we pass `provider="gemini"` explicitly here to exercise the Gemini path.
    Production default is "gemini" per the routing doc.
    """
    gemini_mock = AsyncMock(return_value=dict(_GEMINI_PAYLOAD))
    anthropic_mock = AsyncMock()
    with (
        patch(
            "hireloop.core.interview_prep.generator.gemini_client.extract_json",
            new=gemini_mock,
        ),
        patch(
            "hireloop.core.interview_prep.generator.complete_with_cache",
            new=anthropic_mock,
        ),
    ):
        result = await generate_interview_prep(
            existing_stories_summary="1. Stripe migration",
            job_markdown="# JD",
            custom_role=None,
            resume_md="# CV",
            provider="gemini",
        )

    assert gemini_mock.await_count == 1
    anthropic_mock.assert_not_called()
    assert len(result.questions) == 1
    assert result.model  # populated from settings.gemini_model
    assert result.questions[0]["category"] == "behavioral"


@pytest.mark.asyncio
async def test_explicit_anthropic_override_uses_sonnet() -> None:
    """Even when settings default to gemini, provider='anthropic' wins."""

    class _U:
        input_tokens = 0
        cache_creation_input_tokens = 0
        cache_read_input_tokens = 0
        output_tokens = 0

    class _R:
        text = (
            '{"questions": [{"question": "x", "category": "behavioral", '
            '"suggested_story_title": null, "framework": "y"}], '
            '"red_flag_questions": []}'
        )
        usage = _U()
        model = "claude-sonnet-4-6"
        stop_reason = "end_turn"

    gemini_mock = AsyncMock()
    anthropic_mock = AsyncMock(return_value=_R())
    with (
        patch(
            "hireloop.core.interview_prep.generator.gemini_client.extract_json",
            new=gemini_mock,
        ),
        patch(
            "hireloop.core.interview_prep.generator.complete_with_cache",
            new=anthropic_mock,
        ),
    ):
        result = await generate_interview_prep(
            existing_stories_summary="x",
            job_markdown="# JD",
            custom_role=None,
            resume_md="# CV",
            provider="anthropic",
        )

    assert anthropic_mock.await_count == 1
    gemini_mock.assert_not_called()
    assert len(result.questions) == 1
    assert result.model == "claude-sonnet-4-6"


@pytest.mark.asyncio
async def test_gemini_payload_missing_questions_raises() -> None:
    gemini_mock = AsyncMock(return_value={"red_flag_questions": []})
    with patch(
        "hireloop.core.interview_prep.generator.gemini_client.extract_json", new=gemini_mock
    ):
        from hireloop.core.llm.errors import LLMParseError

        with pytest.raises(LLMParseError):
            await generate_interview_prep(
                existing_stories_summary="x",
                job_markdown="# JD",
                custom_role=None,
                resume_md="# CV",
            )
