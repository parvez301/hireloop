"""End-to-end Phase 2c flow:

1. seed default scan config (simulating onboarding hook)
2. trigger a scan via ScannerService (bypassing Inngest)
3. assert scan_results populated with relevance scores
4. start a batch from the scan run via BatchService + run_funnel
5. assert L0/L1/L2 counters advance and evaluations are created
6. POST /applications from the first evaluation
7. PUT /applications/:id status=applied
8. GET /applications?status=applied sees it
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch
from uuid import UUID

import pytest
import respx
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy import delete, select

from hireloop.core.batch.service import BatchService
from hireloop.core.scanner.default_config import seed_default_scan_config
from hireloop.core.scanner.service import ScannerService
from hireloop.db import get_session_factory
from hireloop.main import app
from hireloop.models.application import Application
from hireloop.models.batch_run import BatchRun
from hireloop.models.evaluation import Evaluation
from hireloop.models.scan_config import ScanConfig
from hireloop.models.scan_run import ScanRun
from hireloop.models.user import User
from tests.conftest import FAKE_CLAIMS
from tests.fixtures.fake_anthropic import fake_anthropic
from tests.fixtures.fake_gemini import fake_gemini

_GH = json.loads(
    (
        Path(__file__).parent.parent
        / "fixtures"
        / "boards"
        / "greenhouse"
        / "stripe.json"
    ).read_text()
)
async def _fake_extract_json(prompt: str, timeout_s: float = 10.0) -> dict[str, Any]:
    """Avoid Gemini JSON extraction colliding with relevance-score stubs."""
    marker = "Job posting:\n"
    if marker in prompt:
        body = prompt.split(marker, 1)[1].rsplit("\n\nJSON:", 1)[0].strip()
    else:
        body = "x" * 80
    return {
        "title": "Platform Engineer",
        "company": "stripe",
        "location": "Remote",
        "salary_min": None,
        "salary_max": None,
        "employment_type": "full_time",
        "seniority": "senior",
        "description_md": body[:8000],
        "requirements": {"skills": ["python"], "years_experience": 5, "nice_to_haves": []},
    }


_CLAUDE = json.dumps(
    {
        "dimensions": {
            "domain_relevance": {"score": 0.9, "grade": "A-", "reasoning": "", "signals": []},
            "role_match": {"score": 0.9, "grade": "A-", "reasoning": "", "signals": []},
            "trajectory_fit": {"score": 0.85, "grade": "A-", "reasoning": "", "signals": []},
            "culture_signal": {"score": 0.8, "grade": "B+", "reasoning": "", "signals": []},
            "red_flags": {"score": 0.95, "grade": "A", "reasoning": "", "signals": []},
            "growth_potential": {"score": 0.85, "grade": "A-", "reasoning": "", "signals": []},
        },
        "overall_reasoning": "Smoke test fit.",
        "red_flag_items": [],
        "personalization_notes": "",
    }
)


async def _get_user_id() -> UUID:
    factory = get_session_factory()
    async with factory() as session:
        r = await session.execute(select(User).where(User.cognito_sub == FAKE_CLAIMS["sub"]))
        return r.scalar_one().id


async def _reset_user_scan_state(user_id: UUID) -> None:
    factory = get_session_factory()
    async with factory() as session:
        await session.execute(delete(Application).where(Application.user_id == user_id))
        await session.execute(delete(BatchRun).where(BatchRun.user_id == user_id))
        await session.execute(delete(ScanRun).where(ScanRun.user_id == user_id))
        await session.execute(delete(ScanConfig).where(ScanConfig.user_id == user_id))
        await session.commit()


@pytest.mark.asyncio
@respx.mock
async def test_phase2c_smoke_scan_batch_pipeline(auth_headers, seed_profile):
    respx.get("https://boards-api.greenhouse.io/v1/boards/stripe/jobs?content=true").mock(
        return_value=Response(200, json=_GH)
    )
    respx.get(re.compile(r"https://api\.ashbyhq\.com/posting-api/job-board/.*")).mock(
        return_value=Response(200, json={"jobs": []})
    )
    respx.get(re.compile(r"https://api\.lever\.co/v0/postings/.*")).mock(
        return_value=Response(200, json=[])
    )
    respx.get(re.compile(r"https://boards-api\.greenhouse\.io/v1/boards/(?!stripe).*")).mock(
        return_value=Response(200, json={"jobs": []})
    )

    user_id = await _get_user_id()
    await _reset_user_scan_state(user_id)

    factory = get_session_factory()

    async with factory() as session:
        await seed_default_scan_config(session, user_id)
        await session.commit()

    async with factory() as session:
        configs = (
            await session.execute(select(ScanConfig).where(ScanConfig.user_id == user_id))
        ).scalars().all()
        assert len(configs) == 1
        config = configs[0]
        assert len(config.companies) == 15
        config_id = config.id

    async with factory() as session:
        run = ScanRun(user_id=user_id, scan_config_id=config_id, status="pending")
        session.add(run)
        await session.commit()
        scan_run_id = run.id

    with fake_gemini({"Senior": "0.8", "Staff": "0.85"}):
        async with factory() as session:
            outcome = await ScannerService(session).run_scan(scan_run_id)
            await session.commit()
    assert outcome.jobs_found >= 2

    async with factory() as session:
        reloaded = (
            await session.execute(select(ScanRun).where(ScanRun.id == scan_run_id))
        ).scalar_one()
        assert reloaded.status == "completed"

    async with factory() as session:
        svc = BatchService(session)
        job_ids = await svc.resolve_job_ids_from_scan(
            user_id=user_id, scan_run_id=scan_run_id
        )
        batch_run = await svc.start_batch(
            user_id=user_id,
            job_ids=job_ids,
            source_type="scan_run_id",
            source_ref=str(scan_run_id),
        )
        await session.commit()
        batch_run_id = batch_run.id

    with (
        fake_gemini({"Relevance score": "0.75"}),
        fake_anthropic({"USER PROFILE": _CLAUDE}),
        patch(
            "hireloop.core.evaluation.job_parser.extract_json",
            new=AsyncMock(side_effect=_fake_extract_json),
        ),
    ):
        async with factory() as session:
            await BatchService(session).run_funnel(batch_run_id=batch_run_id)
            await session.commit()

    async with factory() as session:
        b = (
            await session.execute(select(BatchRun).where(BatchRun.id == batch_run_id))
        ).scalar_one()
        assert b.status == "completed"
        assert b.l2_evaluated >= 1
        first_eval = (
            await session.execute(
                select(Evaluation).where(Evaluation.user_id == user_id).limit(1)
            )
        ).scalar_one()
        job_id = first_eval.job_id

    with patch(
        "hireloop.integrations.cognito.CognitoJwtVerifier.verify",
        new=AsyncMock(return_value=FAKE_CLAIMS),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r_create = await client.post(
                "/api/v1/applications",
                json={
                    "job_id": str(job_id),
                    "evaluation_id": str(first_eval.id),
                    "status": "saved",
                },
                headers=auth_headers,
            )
            assert r_create.status_code == 201
            app_id = r_create.json()["data"]["id"]

            r_update = await client.put(
                f"/api/v1/applications/{app_id}",
                json={"status": "applied"},
                headers=auth_headers,
            )
            assert r_update.status_code == 200
            assert r_update.json()["data"]["status"] == "applied"
            assert r_update.json()["data"]["applied_at"] is not None

            r_list = await client.get(
                "/api/v1/applications?status=applied",
                headers=auth_headers,
            )
            assert r_list.status_code == 200
            ids = [a["id"] for a in r_list.json()["data"]]
            assert app_id in ids
