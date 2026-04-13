import json

import pytest

from hireloop.core.interview_prep.extractor import extract_star_stories_from_resume
from tests.fixtures.fake_anthropic import fake_anthropic

_VALID_STORY = {
    "title": "Led migration",
    "situation": "Legacy monolith",
    "task": "Move to microservices",
    "action": "I designed and rolled out the plan",
    "result": "40% latency reduction",
    "reflection": "Stakeholder buy-in mattered",
    "tags": ["architecture", "migration"],
}

_FAKE_JSON = json.dumps({"stories": [_VALID_STORY, {"not": "a valid star story"}]})


@pytest.mark.asyncio
async def test_extractor_parses_json_and_validates_stories():
    with fake_anthropic({"RESUME": _FAKE_JSON}):
        result = await extract_star_stories_from_resume("# Jane\n\nEngineer.")

    assert len(result.stories) == 1
    assert result.stories[0].title == "Led migration"
    assert result.stories[0].tags == ["architecture", "migration"]


_FENCE = "```json\n" + _FAKE_JSON + "\n```"


@pytest.mark.asyncio
async def test_extractor_strips_markdown_fence():
    with fake_anthropic({"RESUME": _FENCE}):
        result = await extract_star_stories_from_resume("# R\n")
    assert len(result.stories) == 1
