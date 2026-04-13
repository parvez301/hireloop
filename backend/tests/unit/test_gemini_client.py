import pytest

from hireloop.core.llm.gemini_client import classify_intent
from tests.fixtures.fake_gemini import fake_gemini


@pytest.mark.asyncio
async def test_classify_intent_returns_category():
    with fake_gemini({"evaluate this": "EVALUATE_JOB"}):
        result = await classify_intent("Can you evaluate this job for me?")
    assert result == "EVALUATE_JOB"


@pytest.mark.asyncio
async def test_classify_intent_defaults_on_empty_response():
    with fake_gemini({"nothing matches": "bogus response not in enum"}):
        result = await classify_intent("unrelated message")
    assert result == "CAREER_GENERAL"
