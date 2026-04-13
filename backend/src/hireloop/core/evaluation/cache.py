"""Evaluation cache — stores only the 6 Claude dimensions, keyed by content_hash."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hireloop.models.evaluation import EvaluationCache as EvaluationCacheRow

_TTL_DAYS = 30


class EvaluationCache:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, content_hash: str) -> dict[str, Any] | None:
        stmt = select(EvaluationCacheRow).where(EvaluationCacheRow.content_hash == content_hash)
        row = (await self.session.execute(stmt)).scalar_one_or_none()
        if row is None:
            return None
        if row.created_at < datetime.now(UTC) - timedelta(days=_TTL_DAYS):
            return None
        row.hit_count += 1
        await self.session.flush()
        return dict(row.base_evaluation)

    async def put(
        self,
        *,
        content_hash: str,
        base_evaluation: dict[str, Any],
        requirements_json: dict[str, Any],
        model_used: str,
    ) -> None:
        stmt = select(EvaluationCacheRow).where(EvaluationCacheRow.content_hash == content_hash)
        existing = (await self.session.execute(stmt)).scalar_one_or_none()
        if existing:
            existing.base_evaluation = base_evaluation
            existing.requirements_json = requirements_json
            existing.model_used = model_used
            existing.created_at = datetime.now(UTC)
            existing.hit_count = 0
            return

        row = EvaluationCacheRow(
            content_hash=content_hash,
            base_evaluation=base_evaluation,
            requirements_json=requirements_json,
            model_used=model_used,
            hit_count=0,
        )
        self.session.add(row)
