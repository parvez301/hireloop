"""Tests for FeedbackService — ownership validators and upsert (uses real DB)."""

from __future__ import annotations

import hashlib
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from hireloop.core.feedback.service import (
    FeedbackResourceNotFound,
    FeedbackService,
    InvalidFeedback,
)
from hireloop.db import get_session_factory
from hireloop.models.evaluation import Evaluation
from hireloop.models.feedback import Feedback
from hireloop.models.job import Job
from hireloop.models.user import User
from tests.conftest import FAKE_CLAIMS, SECOND_USER_CLAIMS


async def _get_user_id() -> UUID:
    factory = get_session_factory()
    async with factory() as session:
        r = await session.execute(select(User).where(User.cognito_sub == FAKE_CLAIMS["sub"]))
        return r.scalar_one().id


async def _seed_evaluation(user_id: UUID) -> UUID:
    factory = get_session_factory()
    async with factory() as session:
        h = hashlib.sha256(f"fb-test-{uuid4()}".encode()).hexdigest()
        job = Job(
            content_hash=h,
            title="Feedback test job",
            description_md="x",
            requirements_json={},
            source="manual",
        )
        session.add(job)
        await session.flush()
        ev = Evaluation(
            user_id=user_id,
            job_id=job.id,
            overall_grade="B+",
            dimension_scores={},
            reasoning="test",
            match_score=0.8,
            recommendation="worth_exploring",
            model_used="test",
            cached=False,
        )
        session.add(ev)
        await session.commit()
        return ev.id


@pytest.mark.asyncio
async def test_feedback_rejects_out_of_range_rating(seed_profile):
    factory = get_session_factory()
    uid = await _get_user_id()
    eval_id = await _seed_evaluation(uid)

    async with factory() as session:
        service = FeedbackService(session)
        with pytest.raises(InvalidFeedback):
            await service.record(
                user_id=uid,
                resource_type="evaluation",
                resource_id=eval_id,
                rating=6,
                correction_notes=None,
            )


@pytest.mark.asyncio
async def test_feedback_records_valid_rating(seed_profile):
    factory = get_session_factory()
    uid = await _get_user_id()
    eval_id = await _seed_evaluation(uid)

    async with factory() as session:
        service = FeedbackService(session)
        fb = await service.record(
            user_id=uid,
            resource_type="evaluation",
            resource_id=eval_id,
            rating=4,
            correction_notes="Good, small nit on trajectory",
        )
        await session.commit()

    assert fb.rating == 4
    assert fb.resource_type == "evaluation"


@pytest.mark.asyncio
async def test_feedback_upsert_replaces_existing(seed_profile):
    factory = get_session_factory()
    uid = await _get_user_id()
    eval_id = await _seed_evaluation(uid)

    async with factory() as session:
        service = FeedbackService(session)
        await service.record(
            user_id=uid,
            resource_type="evaluation",
            resource_id=eval_id,
            rating=3,
            correction_notes=None,
        )
        await service.record(
            user_id=uid,
            resource_type="evaluation",
            resource_id=eval_id,
            rating=5,
            correction_notes="Changed my mind",
        )
        await session.commit()
        rows = (
            await session.execute(select(Feedback).where(Feedback.resource_id == eval_id))
        ).scalars().all()

    assert len(rows) == 1
    assert rows[0].rating == 5
    assert rows[0].correction_notes == "Changed my mind"


@pytest.mark.asyncio
async def test_feedback_unknown_resource_type_raises(seed_profile):
    factory = get_session_factory()
    uid = await _get_user_id()

    async with factory() as session:
        service = FeedbackService(session)
        with pytest.raises(FeedbackResourceNotFound):
            await service.record(
                user_id=uid,
                resource_type="not_a_real_type",
                resource_id=uuid4(),
                rating=3,
                correction_notes=None,
            )


@pytest.mark.asyncio
async def test_feedback_wrong_owner_raises(seed_profile, second_test_user):
    """User B cannot feedback on user A's evaluation."""
    _ = second_test_user
    factory = get_session_factory()
    uid_a = await _get_user_id()
    eval_id = await _seed_evaluation(uid_a)

    async with factory() as session:
        r = await session.execute(select(User).where(User.cognito_sub == SECOND_USER_CLAIMS["sub"]))
        uid_b = r.scalar_one().id

    async with factory() as session:
        service = FeedbackService(session)
        with pytest.raises(FeedbackResourceNotFound):
            await service.record(
                user_id=uid_b,
                resource_type="evaluation",
                resource_id=eval_id,
                rating=4,
                correction_notes=None,
            )
