"""Negotiation playbook cacheable instructions contain required structure hints."""

from hireloop.core.negotiation.playbook import _CACHEABLE_INSTRUCTIONS


def test_playbook_instructions_include_json_schema_markers():
    assert "market_research" in _CACHEABLE_INSTRUCTIONS
    assert "counter_offer" in _CACHEABLE_INSTRUCTIONS
    assert "scripts" in _CACHEABLE_INSTRUCTIONS
    assert "levels.fyi" in _CACHEABLE_INSTRUCTIONS or "Glassdoor" in _CACHEABLE_INSTRUCTIONS
