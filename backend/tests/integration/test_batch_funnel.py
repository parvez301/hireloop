"""Batch funnel L0 → L1 → L2 integration test."""

import hashlib
import json
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from hireloop.core.batch.funnel import run_l0, run_l1, run_l2
from hireloop.db import get_session_factory
from hireloop.models.batch_run import BatchItem, BatchRun
from hireloop.models.job import Job
from hireloop.models.user import User
from tests.conftest import FAKE_CLAIMS
from tests.fixtures.fake_anthropic import fake_anthropic
from tests.fixtures.fake_gemini import fake_gemini

_CLAUDE_EVAL = json.dumps(
    {
        "dimensions": {
            "domain_relevance": {"score": 0.9, "grade": "A-", "reasoning": "", "signals": []},
            "role_match": {"score": 0.85, "grade": "A-", "reasoning": "", "signals": []},
            "trajectory_fit": {"score": 0.8, "grade": "B+", "reasoning": "", "signals": []},
            "culture_signal": {"score": 0.75, "grade": "B", "reasoning": "", "signals": []},
            "red_flags": {"score": 0.9, "grade": "A", "reasoning": "", "signals": []},
            "growth_potential": {"score": 0.8, "grade": "B+", "reasoning": "", "signals": []},
        },
        "overall_reasoning": "Strong fit.",
        "red_flag_items": [],
        "personalization_notes": "Good match.",
    }
)


async def _user_id() -> UUID:
    factory = get_session_factory()
    async with factory() as s:
        r = await s.execute(select(User).where(User.cognito_sub == FAKE_CLAIMS["sub"]))
        return r.scalar_one().id


async def _make_jobs(n: int) -> list[UUID]:
    factory = get_session_factory()
    ids = []
    async with factory() as session:
        for i in range(n):
            h = hashlib.sha256(f"batch-funnel-{i}-{uuid4()}".encode()).hexdigest()
            job = Job(
                content_hash=h,
                title=f"Senior Engineer {i}",
                # Description must be >= 50 chars for parse_description to accept it
                # (evaluation service re-parses jobs through Gemini in L2).
                description_md=(
                    f"Senior engineer {i} at Acme. Remote role building distributed "
                    f"systems. 5+ years required. Strong backend Python skills expected."
                ),
                requirements_json={"skills": ["python"], "years_experience": 5},
                source="manual",
                location="Remote",
                salary_min=160000,
                salary_max=220000,
                seniority="senior",
            )
            session.add(job)
            await session.flush()
            ids.append(job.id)
        await session.commit()
    return ids


# Valid JSON for Gemini's extract_json path during L2 re-parsing.
_PARSED_JOB_JSON = (
    '{"title": "Senior Engineer", "company": "Acme", "location": "Remote", '
    '"salary_min": 160000, "salary_max": 220000, "employment_type": "full_time", '
    '"seniority": "senior", '
    '"description_md": "Senior engineer at Acme building distributed systems.", '
    '"requirements": {"skills": ["python"], "years_experience": 5, "nice_to_haves": []}}'
)


@pytest.mark.asyncio
async def test_funnel_l0_through_l2(seed_profile):
    uid = await _user_id()
    # Single job — L2 re-parses the job description through Gemini, which
    # normalises all jobs to the same content_hash in this test harness and
    # would cause unique-constraint violations with N>1.
    jids = await _make_jobs(1)

    factory = get_session_factory()
    async with factory() as session:
        brun = BatchRun(
            user_id=uid,
            status="pending",
            total_jobs=1,
            source_type="job_ids",
            source_ref="ad-hoc",
        )
        session.add(brun)
        await session.flush()
        for jid in jids:
            session.add(BatchItem(batch_run_id=brun.id, job_id=jid, stage="queued"))
        await session.commit()
        brun_id = brun.id

    # L0
    async with factory() as session:
        survivors_l0 = await run_l0(
            session, batch_run_id=brun_id, job_ids=jids, user_id=uid
        )
        await session.commit()
    assert len(survivors_l0) == 1

    # L1 — Gemini returns 0.75 (above default 0.5 threshold)
    with fake_gemini({"Relevance score": "0.75"}):
        async with factory() as session:
            survivors_l1 = await run_l1(
                session, batch_run_id=brun_id, job_ids=survivors_l0, user_id=uid
            )
            await session.commit()
    assert len(survivors_l1) == 1

    # L2 — L2 re-parses each job via Gemini then evaluates via Claude.
    # fake_gemini matches on substring: "Extract the following fields" hits the
    # parse_description prompt, "Relevance score" would still hit the L1 prompt
    # (not used at L2). Claude's eval prompt contains "USER PROFILE".
    with (
        fake_gemini({"Extract the following fields": _PARSED_JOB_JSON}),
        fake_anthropic({"USER PROFILE": _CLAUDE_EVAL}),
    ):
        async with factory() as session:
            evaluated = await run_l2(
                session, batch_run_id=brun_id, job_ids=survivors_l1, user_id=uid
            )
            await session.commit()
    assert len(evaluated) == 1

    # Verify batch_items final stages
    async with factory() as session:
        items = (
            (
                await session.execute(
                    select(BatchItem).where(BatchItem.batch_run_id == brun_id)
                )
            )
            .scalars()
            .all()
        )
        done_count = sum(1 for i in items if i.stage == "done")
        assert done_count == 1
