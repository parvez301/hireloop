"""Feedback POST for evaluations, cv outputs, interview preps, negotiations."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from hireloop.main import app
from tests.conftest import FAKE_CLAIMS
from tests.fixtures.fake_anthropic import fake_anthropic
from tests.integration._phase2d_fakes import (
    anthropic_responses_interview_prep_flow,
    anthropic_responses_negotiation_only,
)


@pytest.mark.asyncio
async def test_feedback_evaluation(auth_headers, seed_profile, seeded_evaluation_for_user_a):
    with patch(
        "hireloop.integrations.cognito.CognitoJwtVerifier.verify",
        new=AsyncMock(return_value=FAKE_CLAIMS),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.post(
                f"/api/v1/evaluations/{seeded_evaluation_for_user_a.id}/feedback",
                json={"rating": 4, "correction_notes": "Solid"},
                headers=auth_headers,
            )
    assert r.status_code == 201
    assert r.json()["data"]["resource_type"] == "evaluation"


@pytest.mark.asyncio
async def test_feedback_cv_output(auth_headers, seeded_cv_output):
    with patch(
        "hireloop.integrations.cognito.CognitoJwtVerifier.verify",
        new=AsyncMock(return_value=FAKE_CLAIMS),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.post(
                f"/api/v1/cv-outputs/{seeded_cv_output.id}/feedback",
                json={"rating": 5},
                headers=auth_headers,
            )
    assert r.status_code == 201
    assert r.json()["data"]["resource_type"] == "cv_output"


@pytest.mark.asyncio
async def test_feedback_interview_prep(auth_headers, seed_profile, seeded_evaluation_for_user_a):
    with (
        patch(
            "hireloop.integrations.cognito.CognitoJwtVerifier.verify",
            new=AsyncMock(return_value=FAKE_CLAIMS),
        ),
        fake_anthropic(anthropic_responses_interview_prep_flow()),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r0 = await client.post(
                "/api/v1/interview-preps",
                json={"job_id": str(seeded_evaluation_for_user_a.job_id)},
                headers=auth_headers,
            )
            prep_id = r0.json()["data"]["id"]
            r = await client.post(
                f"/api/v1/interview-preps/{prep_id}/feedback",
                json={"rating": 3, "correction_notes": "More behavioral"},
                headers=auth_headers,
            )
    assert r.status_code == 201
    assert r.json()["data"]["resource_type"] == "interview_prep"


@pytest.mark.asyncio
async def test_feedback_negotiation(auth_headers, seed_profile, seeded_evaluation_for_user_a):
    with (
        patch(
            "hireloop.integrations.cognito.CognitoJwtVerifier.verify",
            new=AsyncMock(return_value=FAKE_CLAIMS),
        ),
        fake_anthropic(anthropic_responses_negotiation_only()),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r0 = await client.post(
                "/api/v1/negotiations",
                json={
                    "job_id": str(seeded_evaluation_for_user_a.job_id),
                    "offer_details": {"base": 190000},
                },
                headers=auth_headers,
            )
            neg_id = r0.json()["data"]["id"]
            r = await client.post(
                f"/api/v1/negotiations/{neg_id}/feedback",
                json={"rating": 4},
                headers=auth_headers,
            )
    assert r.status_code == 201
    assert r.json()["data"]["resource_type"] == "negotiation"


@pytest.mark.asyncio
async def test_feedback_ownership_cross_user(
    second_test_user, seed_profile, seeded_evaluation_for_user_a
):
    """Another user cannot post feedback on someone else's evaluation."""
    from tests.conftest import _verify_token

    with patch(
        "hireloop.integrations.cognito.CognitoJwtVerifier.verify",
        new=AsyncMock(side_effect=_verify_token),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.post(
                f"/api/v1/evaluations/{seeded_evaluation_for_user_a.id}/feedback",
                json={"rating": 4},
                headers=second_test_user["headers"],
            )
    assert r.status_code == 404
