"""Shared fake LLM JSON for Phase 2d integration tests."""

from __future__ import annotations

import json

_FAKE_STAR_STORIES = json.dumps(
    {
        "stories": [
            {
                "title": "Shipped API",
                "situation": "Legacy system",
                "task": "Deliver REST API",
                "action": "I led design and rollout",
                "result": "99.9% uptime",
                "reflection": "Observability first",
                "tags": ["python", "fastapi"],
            }
        ]
    }
)

_FAKE_INTERVIEW_PREP = json.dumps(
    {
        "questions": [
            {
                "question": f"Question {i}?",
                "category": "behavioral",
                "suggested_story_title": "Shipped API",
                "framework": "STAR with metrics.",
            }
            for i in range(10)
        ],
        "red_flag_questions": [
            {"question": f"Red flag {j}?", "what_to_listen_for": "On-call load"}
            for j in range(5)
        ],
    }
)

_FAKE_PLAYBOOK = json.dumps(
    {
        "market_research": {
            "range_low": 180000,
            "range_mid": 200000,
            "range_high": 220000,
            "source_notes": "levels.fyi",
            "comparable_roles": ["PeerCo ~195k"],
        },
        "counter_offer": {
            "target": 210000,
            "minimum_acceptable": 195000,
            "equity_ask": "0.1%",
            "justification": "Scope and seniority",
        },
        "scripts": {
            "email_template": "Hi recruiter,",
            "call_script": "Thanks for the offer.",
            "fallback_positions": ["Signing bonus"],
            "pitfalls": ["Do not accept same day"],
        },
    }
)


def anthropic_responses_interview_prep_flow() -> dict[str, str]:
    """Map user prompt substrings → JSON (order matters: match generator before resume block)."""
    return {
        # Second call: full user block still contains "RESUME" from CANDIDATE RESUME section
        "Generate interview prep per the schema": _FAKE_INTERVIEW_PREP,
        # First call: extractor ends with this; must not appear in generator prompt
        "Return JSON only.": _FAKE_STAR_STORIES,
    }


def anthropic_responses_negotiation_only() -> dict[str, str]:
    return {"Generate a complete negotiation playbook": _FAKE_PLAYBOOK}
