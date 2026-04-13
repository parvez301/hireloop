import pytest

from hireloop.core.llm.anthropic_client import complete_with_cache
from tests.fixtures.fake_anthropic import fake_anthropic


@pytest.mark.asyncio
async def test_complete_with_cache_returns_text_and_usage():
    with fake_anthropic({"hello": "world"}) as stub:
        result = await complete_with_cache(
            system="You are HireLoop.",
            cacheable_blocks=["FRAMEWORK"],
            user_block="hello",
            model="claude-sonnet-4-6",
            max_tokens=100,
        )
    assert result.text == "world"
    assert result.usage.input_tokens == 100
    assert result.usage.output_tokens == 50
    assert len(stub.calls) == 1
    sent_messages = stub.calls[0]["messages"]
    assert any(
        block.get("cache_control") == {"type": "ephemeral"}
        for msg in sent_messages
        for block in (msg["content"] if isinstance(msg["content"], list) else [])
    )
