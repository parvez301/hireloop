import json

import pytest

from hireloop.core.evaluation.claude_scorer import ClaudeScorer
from hireloop.core.llm.errors import LLMParseError
from tests.fixtures.fake_anthropic import fake_anthropic

_FAKE_RESPONSE = json.dumps(
    {
        "dimensions": {
            "domain_relevance": {
                "score": 0.9,
                "grade": "A-",
                "reasoning": "Fintech experience maps well",
                "signals": ["payments at Acme", "PCI compliance"],
            },
            "role_match": {
                "score": 0.85,
                "grade": "A-",
                "reasoning": "Past responsibilities align",
                "signals": ["led migration"],
            },
            "trajectory_fit": {
                "score": 0.8,
                "grade": "B+",
                "reasoning": "Lateral move",
                "signals": [],
            },
            "culture_signal": {
                "score": 0.7,
                "grade": "B",
                "reasoning": "Neutral tone",
                "signals": [],
            },
            "red_flags": {
                "score": 0.9,
                "grade": "A",
                "reasoning": "No major concerns",
                "signals": [],
            },
            "growth_potential": {
                "score": 0.8,
                "grade": "B+",
                "reasoning": "Senior role with team lead path",
                "signals": [],
            },
        },
        "overall_reasoning": "Strong fit overall with aligned experience.",
        "red_flag_items": [],
        "personalization_notes": "Candidate's fintech background is a direct match.",
    }
)


@pytest.mark.asyncio
async def test_claude_scorer_returns_6_dimensions():
    scorer = ClaudeScorer()
    with fake_anthropic({"payments": _FAKE_RESPONSE}):
        result = await scorer.score(
            job_markdown="Senior engineer at a payments company.",
            profile_summary={"skills": ["python"], "years": 6},
            rule_results_text="(rule results)",
        )
    assert set(result.dimensions.keys()) == {
        "domain_relevance",
        "role_match",
        "trajectory_fit",
        "culture_signal",
        "red_flags",
        "growth_potential",
    }
    assert result.dimensions["domain_relevance"]["score"] == 0.9
    assert result.overall_reasoning.startswith("Strong fit")
    assert result.personalization_notes is not None
    assert result.personalization_notes.startswith("Candidate")


@pytest.mark.asyncio
async def test_claude_scorer_retries_on_bad_json():
    scorer = ClaudeScorer()
    with fake_anthropic({"NOT_JSON": "this is not json at all"}):
        with pytest.raises(LLMParseError):
            await scorer.score(
                job_markdown="NOT_JSON body",
                profile_summary={},
                rule_results_text="",
            )
