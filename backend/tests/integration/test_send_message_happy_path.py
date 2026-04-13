import json
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from hireloop.main import app
from tests.conftest import FAKE_CLAIMS
from tests.fixtures.fake_anthropic import fake_anthropic
from tests.fixtures.fake_gemini import fake_gemini

_JD = (
    "Senior engineer role with Python, FastAPI, and Postgres. "
    "Building APIs and distributed systems for cloud platforms. "
    "Remote friendly team with strong engineering culture."
)

_PARSED = json.dumps(
    {
        "title": "SWE",
        "company": "Acme",
        "location": "Remote",
        "salary_min": 180000,
        "salary_max": 220000,
        "employment_type": "full_time",
        "seniority": "senior",
        "description_md": _JD,
        "requirements": {"skills": ["python"], "years_experience": 5, "nice_to_haves": []},
    }
)

_CLAUDE_EVAL = json.dumps(
    {
        "dimensions": {
            "domain_relevance": {"score": 0.9, "grade": "A-", "reasoning": "", "signals": []},
            "role_match": {"score": 0.9, "grade": "A-", "reasoning": "", "signals": []},
            "trajectory_fit": {"score": 0.9, "grade": "A-", "reasoning": "", "signals": []},
            "culture_signal": {"score": 0.9, "grade": "A-", "reasoning": "", "signals": []},
            "red_flags": {"score": 0.9, "grade": "A-", "reasoning": "", "signals": []},
            "growth_potential": {"score": 0.9, "grade": "A-", "reasoning": "", "signals": []},
        },
        "overall_reasoning": "Strong fit.",
        "red_flag_items": [],
        "personalization_notes": "Good match.",
    }
)

_CLAUDE_ROUTE = "TOOL_CALL: " + json.dumps(
    {"call": "evaluate_job", "args": {"job_description": _JD}}
)


@pytest.mark.asyncio
async def test_send_message_triggers_evaluate_tool(auth_headers, seed_profile, seed_conversation):
    with (
        patch(
            "hireloop.integrations.cognito.CognitoJwtVerifier.verify",
            new=AsyncMock(return_value=FAKE_CLAIMS),
        ),
        fake_gemini(
            {
                "evaluate": "EVALUATE_JOB",
                "Senior engineer": _PARSED,
            }
        ),
        fake_anthropic({"Available tools": _CLAUDE_ROUTE, "USER PROFILE": _CLAUDE_EVAL}),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                f"/api/v1/conversations/{seed_conversation.id}/messages",
                json={"content": "Please evaluate this job: Senior engineer role."},
                headers=auth_headers,
            )

    assert resp.status_code == 200
    body = resp.json()["data"]
    assert body["role"] == "assistant"
    assert body["cards"] is not None
    assert any(c["type"] == "evaluation" for c in body["cards"])
