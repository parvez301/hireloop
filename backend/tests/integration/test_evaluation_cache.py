from datetime import UTC, datetime, timedelta

import pytest

from hireloop.core.evaluation.cache import EvaluationCache


@pytest.mark.asyncio
async def test_cache_miss_then_hit(db_session):
    cache = EvaluationCache(db_session)
    hit = await cache.get("hash_abc")
    assert hit is None

    await cache.put(
        content_hash="hash_abc",
        base_evaluation={"dimensions": {"x": {"score": 0.9}}},
        requirements_json={"skills": ["python"]},
        model_used="claude-sonnet-4-6",
    )
    await db_session.commit()

    hit = await cache.get("hash_abc")
    assert hit is not None
    assert hit["dimensions"]["x"]["score"] == 0.9


@pytest.mark.asyncio
async def test_cache_30day_expiry(db_session):
    from hireloop.models.evaluation import EvaluationCache as CacheRow

    stale_row = CacheRow(
        content_hash="hash_stale",
        base_evaluation={"dimensions": {}},
        requirements_json={},
        model_used="claude-sonnet-4-6",
        created_at=datetime.now(UTC) - timedelta(days=31),
    )
    db_session.add(stale_row)
    await db_session.commit()

    cache = EvaluationCache(db_session)
    hit = await cache.get("hash_stale")
    assert hit is None
