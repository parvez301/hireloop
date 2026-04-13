import pytest

from hireloop.core.agent.classifier import classify_node
from hireloop.core.agent.state import AgentState
from tests.fixtures.fake_gemini import fake_gemini


def _make_state(content: str) -> AgentState:
    from langchain_core.messages import HumanMessage

    return {
        "messages": [HumanMessage(content=content)],
        "user_id": "u",
        "conversation_id": "c",
        "profile_summary": {},
        "subscription_status": "trial",
        "trial_days_remaining": None,
        "classified_intent": None,
        "cards": [],
        "model_calls": [],
        "tokens_used": 0,
    }


@pytest.mark.asyncio
async def test_classify_node_sets_intent():
    with fake_gemini({"evaluate this": "EVALUATE_JOB"}):
        out = await classify_node(_make_state("Can you evaluate this job?"))
    assert out["classified_intent"] == "EVALUATE_JOB"


@pytest.mark.asyncio
async def test_classify_node_defaults_to_career_general_on_error():
    with fake_gemini({"nothing": "not_a_valid_intent_string"}):
        out = await classify_node(_make_state("I have a weird career question"))
    assert out["classified_intent"] == "CAREER_GENERAL"
