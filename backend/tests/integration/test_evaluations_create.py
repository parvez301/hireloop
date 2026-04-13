import json
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from hireloop.db import get_engine
from hireloop.main import app
from tests.conftest import _verify_token
from tests.fixtures.fake_anthropic import fake_anthropic
from tests.fixtures.fake_gemini import fake_gemini

_PARSED_JSON = (
    '{"title": "Senior Engineer", "company": "Stripe", "location": "Remote", '
    '"salary_min": 180000, "salary_max": 240000, "employment_type": "full_time", '
    '"seniority": "senior", "description_md": "Senior engineer role with Python and Postgres.", '
    '"requirements": {"skills": ["python", "postgres"], "years_experience": 5, '
    '"nice_to_haves": []}}'
)

_CLAUDE_JSON = json.dumps(
    {
        "dimensions": {
            "domain_relevance": {
                "score": 0.9,
                "grade": "A-",
                "reasoning": "strong fit",
                "signals": [],
            },
            "role_match": {"score": 0.85, "grade": "A-", "reasoning": "aligned", "signals": []},
            "trajectory_fit": {"score": 0.8, "grade": "B+", "reasoning": "lateral", "signals": []},
            "culture_signal": {"score": 0.75, "grade": "B", "reasoning": "neutral", "signals": []},
            "red_flags": {"score": 0.9, "grade": "A", "reasoning": "none", "signals": []},
            "growth_potential": {
                "score": 0.8,
                "grade": "B+",
                "reasoning": "team lead track",
                "signals": [],
            },
        },
        "overall_reasoning": "Good overall fit.",
        "red_flag_items": [],
        "personalization_notes": "Aligns with past work.",
    }
)


@pytest_asyncio.fixture
async def clear_evaluation_llm_cache() -> None:
    """fake_gemini returns fixed JSON → same content_hash; clear DB cache for a cold Claude path."""
    async with get_engine().begin() as conn:
        await conn.execute(text("DELETE FROM evaluation_cache"))


@pytest.mark.asyncio
async def test_evaluate_happy_path(clear_evaluation_llm_cache, auth_headers, seed_profile):
    with (
        patch(
            "hireloop.integrations.cognito.CognitoJwtVerifier.verify",
            new=AsyncMock(side_effect=_verify_token),
        ),
        fake_gemini({"Senior engineer": _PARSED_JSON}),
        fake_anthropic({"USER PROFILE": _CLAUDE_JSON}),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/evaluations",
                json={
                    "job_description": "Senior engineer role with Python and Postgres. "
                    "5+ years required." * 3
                },
                headers=auth_headers,
            )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["overall_grade"] in ("A", "A-", "B+", "B")
    assert data["cached"] is False
    assert "domain_relevance" in data["dimension_scores"]


@pytest.mark.asyncio
async def test_evaluate_uses_cache_on_second_call(
    clear_evaluation_llm_cache, auth_headers, seed_profile, second_test_user
):
    jd = "Senior engineer role with Python and Postgres. 5+ years required." * 3
    with (
        patch(
            "hireloop.integrations.cognito.CognitoJwtVerifier.verify",
            new=AsyncMock(side_effect=_verify_token),
        ),
        fake_gemini({"Senior engineer": _PARSED_JSON}),
        fake_anthropic({"USER PROFILE": _CLAUDE_JSON}),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r1 = await client.post(
                "/api/v1/evaluations",
                json={"job_description": jd},
                headers=auth_headers,
            )
            assert r1.status_code == 200
            assert r1.json()["data"]["cached"] is False

            r2 = await client.post(
                "/api/v1/evaluations",
                json={"job_description": jd},
                headers=second_test_user["headers"],
            )
            assert r2.status_code == 200
            assert r2.json()["data"]["cached"] is True


@pytest.mark.asyncio
async def test_evaluate_idempotency(auth_headers, seed_profile):
    jd = "Senior engineer role with Python and Postgres. 5+ years required." * 3
    with (
        patch(
            "hireloop.integrations.cognito.CognitoJwtVerifier.verify",
            new=AsyncMock(side_effect=_verify_token),
        ),
        fake_gemini({"Senior engineer": _PARSED_JSON}),
        fake_anthropic({"USER PROFILE": _CLAUDE_JSON}),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            headers = {**auth_headers, "Idempotency-Key": "key-abc"}
            r1 = await client.post(
                "/api/v1/evaluations",
                json={"job_description": jd},
                headers=headers,
            )
            r2 = await client.post(
                "/api/v1/evaluations",
                json={"job_description": jd},
                headers=headers,
            )
    assert r1.status_code == 200 and r2.status_code == 200
    assert r1.json()["data"]["id"] == r2.json()["data"]["id"]
