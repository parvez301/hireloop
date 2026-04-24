"""Phase 7 cutover regression tests.

Two pieces:
1. QUALITY-tier generators now default to route="realtime" (direct API), not
   "batch" (bridge). The 22s-TTFT bridge bottleneck from the Apr 2026 benchmark
   is the reason — user-facing paths must hit api.anthropic.com directly. The
   tests assert the default makes it through to complete_with_cache.
2. fast_client now dispatches to Groq Llama 8B when settings.fast_llm_provider
   is "groq". Tests assert the dispatcher hits groq_client (not gemini_client
   or anthropic_client) under that flag.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

# ---------------------------------------------------------------------------
# Phase 7a — route=realtime defaults
# ---------------------------------------------------------------------------


def _completion_result(text: str = '{"changes_summary": ""}') -> object:
    class _U:
        input_tokens = 0
        cache_creation_input_tokens = 0
        cache_read_input_tokens = 0
        output_tokens = 0

    class _R:
        def __init__(self) -> None:
            self.text = text
            self.usage = _U()
            self.model = "claude-sonnet-4-6"
            self.stop_reason = "end_turn"

    return _R()


@pytest.mark.asyncio
async def test_cv_optimizer_defaults_to_realtime_route() -> None:
    from hireloop.core.cv_optimizer.optimizer import CvOptimizer

    captured: dict[str, object] = {}

    async def _fake(**kwargs: object) -> object:
        captured.update(kwargs)
        return _completion_result(
            '{"tailored_md": "x", "changes_summary": "", "keywords_injected": [], '
            '"sections_reordered": []}'
        )

    with patch(
        "hireloop.core.cv_optimizer.optimizer.complete_with_cache", new=AsyncMock(side_effect=_fake)
    ):
        await CvOptimizer().rewrite(
            master_resume_md="# Resume",
            job_markdown="# Job",
            keywords=["x"],
            additional_feedback=None,
        )
    assert captured["route"] == "realtime"


@pytest.mark.asyncio
async def test_cv_optimizer_accepts_explicit_batch_route() -> None:
    from hireloop.core.cv_optimizer.optimizer import CvOptimizer

    captured: dict[str, object] = {}

    async def _fake(**kwargs: object) -> object:
        captured.update(kwargs)
        return _completion_result(
            '{"tailored_md": "x", "changes_summary": "", "keywords_injected": [], '
            '"sections_reordered": []}'
        )

    with patch(
        "hireloop.core.cv_optimizer.optimizer.complete_with_cache", new=AsyncMock(side_effect=_fake)
    ):
        await CvOptimizer().rewrite(
            master_resume_md="# Resume",
            job_markdown="# Job",
            keywords=["x"],
            additional_feedback=None,
            route="batch",
        )
    assert captured["route"] == "batch"


@pytest.mark.asyncio
async def test_claude_scorer_defaults_to_realtime_route() -> None:
    from hireloop.core.evaluation.claude_scorer import ClaudeScorer

    captured: dict[str, object] = {}

    async def _fake(**kwargs: object) -> object:
        captured.update(kwargs)
        return _completion_result(
            '{"dimensions": {}, "overall_reasoning": "", "red_flag_items": [], '
            '"personalization_notes": null}'
        )

    with patch(
        "hireloop.core.evaluation.claude_scorer.complete_with_cache",
        new=AsyncMock(side_effect=_fake),
    ):
        await ClaudeScorer().score(job_markdown="# Job", profile_summary={}, rule_results_text="")
    assert captured["route"] == "realtime"


@pytest.mark.asyncio
async def test_negotiation_defaults_to_realtime_route() -> None:
    from hireloop.core.negotiation.playbook import generate_negotiation_playbook

    captured: dict[str, object] = {}

    async def _fake(**kwargs: object) -> object:
        captured.update(kwargs)
        return _completion_result('{"market_research": {}, "counter_offer": {}, "scripts": {}}')

    with patch(
        "hireloop.core.negotiation.playbook.complete_with_cache",
        new=AsyncMock(side_effect=_fake),
    ):
        await generate_negotiation_playbook(
            title="Eng",
            company="Acme",
            location=None,
            offer_details={},
            current_comp=None,
            experience_summary="",
        )
    assert captured["route"] == "realtime"


@pytest.mark.asyncio
async def test_interview_extractor_defaults_to_realtime_route() -> None:
    from hireloop.core.interview_prep.extractor import extract_star_stories_from_resume

    captured: dict[str, object] = {}

    async def _fake(**kwargs: object) -> object:
        captured.update(kwargs)
        return _completion_result('{"stories": []}')

    with patch(
        "hireloop.core.interview_prep.extractor.complete_with_cache",
        new=AsyncMock(side_effect=_fake),
    ):
        await extract_star_stories_from_resume("# Resume")
    assert captured["route"] == "realtime"


@pytest.mark.asyncio
async def test_interview_generator_defaults_to_realtime_route() -> None:
    from hireloop.core.interview_prep.generator import generate_interview_prep

    captured: dict[str, object] = {}

    async def _fake(**kwargs: object) -> object:
        captured.update(kwargs)
        return _completion_result(
            '{"questions": [], "red_flag_questions": [], "personalization_notes": null}'
        )

    with patch(
        "hireloop.core.interview_prep.generator.complete_with_cache",
        new=AsyncMock(side_effect=_fake),
    ):
        await generate_interview_prep(
            existing_stories_summary="",
            job_markdown="# Job",
            custom_role=None,
            resume_md="# Resume",
        )
    assert captured["route"] == "realtime"


# ---------------------------------------------------------------------------
# Phase 7b — fast_client dispatches to Groq when configured
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fast_client_classify_intent_uses_groq_under_groq_provider() -> None:
    from hireloop.core.llm import fast_client

    # Patch settings provider + groq impl, assert groq is hit and gemini/claude are not.
    fake_get_settings = lambda: type(  # noqa: E731
        "S",
        (),
        {
            "fast_llm_provider": "groq",
            "llm_classifier_timeout_s": 3.0,
            "groq_model": "llama-3.1-8b-instant",
            "claude_haiku_model": "claude-haiku-4-5-20251001",
            "gemini_model": "gemini-2.0-flash",
        },
    )()

    groq_call = AsyncMock(return_value="EVALUATE_JOB")
    gemini_call = AsyncMock()
    with (
        patch("hireloop.core.llm.fast_client.get_settings", new=fake_get_settings),
        patch("hireloop.core.llm.fast_client.groq_client.complete_text", new=groq_call),
        patch("hireloop.core.llm.fast_client.gemini_client.classify_intent", new=gemini_call),
    ):
        result = await fast_client.classify_intent("Evaluate this job please")
    assert result == "EVALUATE_JOB"
    assert groq_call.await_count == 1
    gemini_call.assert_not_called()


@pytest.mark.asyncio
async def test_fast_client_extract_json_uses_groq_under_groq_provider() -> None:
    from hireloop.core.llm import fast_client

    fake_get_settings = lambda: type(  # noqa: E731
        "S",
        (),
        {
            "fast_llm_provider": "groq",
            "llm_classifier_timeout_s": 3.0,
            "groq_model": "llama-3.1-8b-instant",
            "claude_haiku_model": "claude-haiku-4-5-20251001",
            "gemini_model": "gemini-2.0-flash",
        },
    )()

    groq_call = AsyncMock(return_value={"extracted": True})
    gemini_call = AsyncMock()
    with (
        patch("hireloop.core.llm.fast_client.get_settings", new=fake_get_settings),
        patch("hireloop.core.llm.fast_client.groq_client.complete_json", new=groq_call),
        patch("hireloop.core.llm.fast_client.gemini_client.extract_json", new=gemini_call),
    ):
        out = await fast_client.extract_json("extract me")
    assert out == {"extracted": True}
    assert groq_call.await_count == 1
    gemini_call.assert_not_called()


def test_fast_client_active_provider_model_reports_groq() -> None:
    from hireloop.core.llm import fast_client

    fake_get_settings = lambda: type(  # noqa: E731
        "S",
        (),
        {
            "fast_llm_provider": "groq",
            "groq_model": "llama-3.1-8b-instant",
            "gemini_model": "gemini-2.0-flash",
            "claude_haiku_model": "claude-haiku-4-5-20251001",
        },
    )()
    with patch("hireloop.core.llm.fast_client.get_settings", new=fake_get_settings):
        provider, model = fast_client.active_provider_model()
    assert provider == "groq"
    assert model == "llama-3.1-8b-instant"
