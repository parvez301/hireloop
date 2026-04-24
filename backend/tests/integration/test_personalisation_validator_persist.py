"""Integration tests for personalisation_validator.validate_and_persist().

Covers the audit-write contract and the auto-rewrite path with Sonnet mocked.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from sqlalchemy import select

from hireloop.core.llm.tier import Task
from hireloop.db import get_session_factory
from hireloop.models.personalisation_audit import PersonalisationAudit
from hireloop.models.user import User
from hireloop.services.personalisation_validator import (
    ValidationOutcome,
    validate_and_persist,
)

_CV: dict[str, Any] = {
    "roles": [
        {"title": "Senior Engineer", "company": "Stripe", "key_achievements": ["X"]},
        {"title": "Engineer", "company": "RSA Global", "key_achievements": ["Y"]},
    ],
    "notable_numbers": ["Reduced billing errors by 40%"],
}
_JD: dict[str, Any] = {"company": "Acme Corp", "title": "Staff Engineer"}

_PASSING_OUTPUT = (
    "Your Stripe and RSA Global work, including reducing billing errors by 40%, "
    "maps to what Acme Corp is hiring for."
)
_FAILING_OUTPUT = "You may want to highlight your strong background for this role."


async def _make_user() -> User:
    factory = get_session_factory()
    async with factory() as session:
        user = User(
            cognito_sub=f"audit-test-{uuid4()}",
            email=f"audit-{uuid4()}@example.com",
            name="Audit Test",
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


def _completion_result(text: str) -> Any:
    """Mock minimal CompletionResult shape used by rewrite_for_specificity."""

    class _R:
        def __init__(self, t: str) -> None:
            self.text = t

    return _R(text)


@pytest.mark.asyncio
async def test_passing_output_skips_rewrite_and_persists_audit() -> None:
    user = await _make_user()
    factory = get_session_factory()
    async with factory() as session:
        mock_rewrite = AsyncMock()
        with patch(
            "hireloop.services.personalisation_validator.complete_with_cache",
            new=mock_rewrite,
        ):
            outcome = await validate_and_persist(
                session,
                output=_PASSING_OUTPUT,
                cv_structure=_CV,
                jd_structure=_JD,
                task=Task.FULL_EVALUATION,
                user_id=user.id,
            )
        await session.commit()

        assert isinstance(outcome, ValidationOutcome)
        assert outcome.final_report.passed is True
        assert outcome.rewrite_attempted is False
        assert outcome.rewrite_succeeded is False
        assert outcome.output == _PASSING_OUTPUT
        mock_rewrite.assert_not_called()

        rows = (
            (
                await session.execute(
                    select(PersonalisationAudit).where(PersonalisationAudit.user_id == user.id)
                )
            )
            .scalars()
            .all()
        )
        assert len(rows) == 1
        assert rows[0].passed is True
        assert rows[0].task == Task.FULL_EVALUATION.value
        assert rows[0].rewrite_attempted is False


@pytest.mark.asyncio
async def test_failing_output_triggers_rewrite_and_audits_success() -> None:
    user = await _make_user()
    factory = get_session_factory()
    async with factory() as session:
        with patch(
            "hireloop.services.personalisation_validator.complete_with_cache",
            new=AsyncMock(return_value=_completion_result(_PASSING_OUTPUT)),
        ):
            outcome = await validate_and_persist(
                session,
                output=_FAILING_OUTPUT,
                cv_structure=_CV,
                jd_structure=_JD,
                task=Task.COVER_LETTER,
                user_id=user.id,
            )
        await session.commit()

        assert outcome.rewrite_attempted is True
        assert outcome.rewrite_succeeded is True
        assert outcome.final_report.passed is True
        assert outcome.output == _PASSING_OUTPUT

        row = (
            await session.execute(
                select(PersonalisationAudit).where(PersonalisationAudit.user_id == user.id)
            )
        ).scalar_one()
        assert row.passed is True
        assert row.rewrite_attempted is True
        assert row.rewrite_succeeded is True
        assert row.task == Task.COVER_LETTER.value


@pytest.mark.asyncio
async def test_rewrite_failure_keeps_original_and_audits_failed() -> None:
    """Sonnet down → keep the failing output but still write the audit."""
    user = await _make_user()
    factory = get_session_factory()
    async with factory() as session:
        with patch(
            "hireloop.services.personalisation_validator.complete_with_cache",
            new=AsyncMock(side_effect=Exception("sonnet down")),
        ):
            outcome = await validate_and_persist(
                session,
                output=_FAILING_OUTPUT,
                cv_structure=_CV,
                jd_structure=_JD,
                task=Task.STAR_STORY,
                user_id=user.id,
            )
        await session.commit()

        assert outcome.rewrite_attempted is True
        assert outcome.rewrite_succeeded is False
        assert outcome.output == _FAILING_OUTPUT
        assert outcome.final_report.passed is False

        row = (
            await session.execute(
                select(PersonalisationAudit).where(PersonalisationAudit.user_id == user.id)
            )
        ).scalar_one()
        assert row.passed is False
        assert row.rewrite_attempted is True
        assert row.rewrite_succeeded is False


@pytest.mark.asyncio
async def test_auto_rewrite_off_skips_rewrite_and_persists_failed_audit() -> None:
    user = await _make_user()
    factory = get_session_factory()
    async with factory() as session:
        mock_rewrite = AsyncMock()
        with patch(
            "hireloop.services.personalisation_validator.complete_with_cache",
            new=mock_rewrite,
        ):
            outcome = await validate_and_persist(
                session,
                output=_FAILING_OUTPUT,
                cv_structure=_CV,
                jd_structure=_JD,
                task=Task.FULL_EVALUATION,
                user_id=user.id,
                auto_rewrite=False,
            )
        await session.commit()

        assert outcome.rewrite_attempted is False
        assert outcome.output == _FAILING_OUTPUT
        mock_rewrite.assert_not_called()

        row = (
            await session.execute(
                select(PersonalisationAudit).where(PersonalisationAudit.user_id == user.id)
            )
        ).scalar_one()
        assert row.passed is False
        assert row.rewrite_attempted is False
