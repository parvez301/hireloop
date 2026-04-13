import json

import pytest

from hireloop.core.interview_prep.generator import generate_interview_prep
from tests.fixtures.fake_anthropic import fake_anthropic

_FAKE_RESPONSE = json.dumps(
    {
        "questions": [
            {
                "question": "Tell me about a time you led a difficult migration.",
                "category": "behavioral",
                "suggested_story_title": "Led payments migration at Acme",
                "framework": "Use STAR. Emphasize dual-write strategy and how you managed risk.",
            },
            {
                "question": "How would you design a rate limiter for 1M QPS?",
                "category": "technical",
                "suggested_story_title": None,
                "framework": "Discuss token bucket vs sliding window, Redis Lua for atomicity.",
            },
        ],
        "red_flag_questions": [
            {
                "question": "What's the team's current on-call burden look like?",
                "what_to_listen_for": (
                    "Specific numbers (pages per week, avg response time). "
                    "Vague answers are a warning sign."
                ),
            }
        ],
    }
)


@pytest.mark.asyncio
async def test_generator_job_mode():
    with fake_anthropic({"CANDIDATE RESUME": _FAKE_RESPONSE}):
        result = await generate_interview_prep(
            existing_stories_summary=(
                "1. Led payments migration at Acme\n2. Fixed production outage"
            ),
            job_markdown="Senior Engineer at Stripe working on payment infrastructure.",
            custom_role=None,
            resume_md="## Jane Doe\n\nSenior engineer with payments experience.",
        )
    assert len(result.questions) == 2
    assert result.questions[0]["suggested_story_title"] == "Led payments migration at Acme"
    assert len(result.red_flag_questions) == 1


@pytest.mark.asyncio
async def test_generator_custom_role_mode():
    with fake_anthropic({"CANDIDATE RESUME": _FAKE_RESPONSE}):
        result = await generate_interview_prep(
            existing_stories_summary="1. Led payments migration at Acme",
            job_markdown=None,
            custom_role="Staff SRE at any FAANG — focus on incident response and reliability",
            resume_md="## Jane Doe\n\nReliability engineering background.",
        )
    assert len(result.questions) >= 1


@pytest.mark.asyncio
async def test_generator_rejects_both_job_and_custom_role():
    with pytest.raises(ValueError):
        await generate_interview_prep(
            existing_stories_summary="",
            job_markdown="job",
            custom_role="role",
            resume_md="resume",
        )


@pytest.mark.asyncio
async def test_generator_rejects_neither_job_nor_custom_role():
    with pytest.raises(ValueError):
        await generate_interview_prep(
            existing_stories_summary="",
            job_markdown=None,
            custom_role=None,
            resume_md="resume",
        )
