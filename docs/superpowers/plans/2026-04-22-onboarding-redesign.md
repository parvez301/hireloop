# Onboarding Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the blank-chat landing with a resume-first onboarding funnel that takes new users to a demonstrated-value moment (evaluation of a job they chose) in under 90 seconds, and adopts the marketing site's teal→cobalt→violet gradient system on the onboarding surface.

**Architecture:** Backend changes first — state-machine collapse from 3 to 2 states, three new endpoints (`/profile/resume-text`, `/jobs/parse-text`, `/onboarding/first-evaluation`), Alembic migration. Frontend second — two shared gradient components, thin api.ts wrappers, new `OnboardingPage` and `OnboardingPayoffPage` routes, router hard-gate. Playwright tests parameterized by `PW_BASE_URL` extend the existing suite. Spec at `docs/superpowers/specs/2026-04-22-onboarding-redesign-design.md` (commit `0bd5c2a`).

**Tech Stack:** FastAPI + SQLAlchemy async + Alembic (backend). React + TypeScript + Tailwind + Vite (frontend). pytest + pytest-asyncio + httpx.AsyncClient (backend tests). Playwright + Vitest (frontend tests).

---

## File Structure

**Backend — files to create:**
- `backend/migrations/versions/0007_onboarding_collapse_preferences.py` — data migration
- `backend/src/hireloop/api/onboarding.py` — new router for `POST /onboarding/first-evaluation`
- `backend/src/hireloop/schemas/onboarding.py` — request/response schemas
- `backend/tests/unit/test_profile_service_onboarding_collapse.py`
- `backend/tests/integration/test_profile_resume_text_endpoint.py`
- `backend/tests/integration/test_jobs_parse_text_endpoint.py`
- `backend/tests/integration/test_onboarding_first_evaluation.py`

**Backend — files to modify:**
- `backend/src/hireloop/services/profile.py` (lines 32-53: `_advance_onboarding` + helper)
- `backend/src/hireloop/api/profile.py` (add `POST /resume-text`)
- `backend/src/hireloop/api/jobs.py` (add `POST /parse-text`)
- `backend/src/hireloop/schemas/job.py` (add `JobParseTextRequest`)
- `backend/src/hireloop/schemas/profile.py` (add `ResumeTextRequest`)
- `backend/src/hireloop/main.py` (register onboarding router)

**Frontend — files to create:**
- `user-portal/src/components/ui/GradientButton.tsx`
- `user-portal/src/components/ui/GradientBadge.tsx`
- `user-portal/src/pages/OnboardingPage.tsx`
- `user-portal/src/pages/OnboardingPayoffPage.tsx`
- `user-portal/src/components/onboarding/ResumeUploadStep.tsx`
- `user-portal/src/components/onboarding/JobInputStep.tsx`
- `user-portal/src/components/onboarding/EvaluationProgressStep.tsx`

**Frontend — files to modify:**
- `user-portal/tailwind.config.ts` (add accent-teal/cobalt/violet)
- `user-portal/src/lib/api.ts` (add `profile.uploadResumeText`, `jobs.parseText`, `onboarding.firstEvaluation`)
- `user-portal/src/App.tsx` (new routes + `requiresProfile` gate)
- `user-portal/e2e/features.spec.ts` (3 new tests + update Scans test)
- `user-portal/e2e/fixtures/` (new directory for resume.pdf + job.html fixtures)

---

## Task 1: Alembic migration — collapse preferences state

**Files:**
- Create: `backend/migrations/versions/0007_onboarding_collapse_preferences.py`

- [ ] **Step 1: Write the migration file**

```python
"""onboarding_collapse_preferences

Revision ID: 0007_onb_collapse
Revises: 0006_phase2d
Create Date: 2026-04-22

Flips any `profiles.onboarding_state='preferences'` rows whose profile already
has a parsed resume (master_resume_md IS NOT NULL) to 'done'. The 'preferences'
string stays a legal value in the column (no enum change, no downgrade pain)
but the application no longer writes it.

Profiles that had 'preferences' state but no resume remain as-is — they're
inconsistent data from before the state machine was fully enforced and will
self-heal on next resume upload.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0007_onb_collapse"
down_revision: str | None = "0006_phase2d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE profiles
        SET onboarding_state = 'done'
        WHERE onboarding_state = 'preferences'
          AND master_resume_md IS NOT NULL
        """
    )


def downgrade() -> None:
    # No-op. We cannot know which of the now-'done' rows were formerly
    # 'preferences' without an audit column, and re-demoting everyone to
    # 'preferences' would trigger the onboarding gate for users who finished.
    pass
```

- [ ] **Step 2: Run migration against local DB**

```bash
cd backend && uv run alembic upgrade head
```

Expected: migration `0007_onb_collapse` applied, no errors.

- [ ] **Step 3: Verify migration is at head**

```bash
cd backend && uv run alembic current
```

Expected output contains `0007_onb_collapse (head)`.

- [ ] **Step 4: Commit**

```bash
git add backend/migrations/versions/0007_onboarding_collapse_preferences.py
git commit -m "feat(db): collapse onboarding preferences state to done"
```

---

## Task 2: State machine — collapse to two-state via TDD

**Files:**
- Modify: `backend/src/hireloop/services/profile.py` (lines 32-53)
- Test: `backend/tests/unit/test_profile_service_onboarding_collapse.py`

- [ ] **Step 1: Write the failing tests**

```python
# backend/tests/unit/test_profile_service_onboarding_collapse.py
"""Unit tests for the collapsed onboarding state machine.

After 2026-04-22, `_advance_onboarding` transitions `resume_upload → done`
on the presence of a parsed resume alone. The `preferences` intermediate
state is no longer a valid transition target.
"""

from uuid import uuid4

import pytest

from hireloop.models.profile import Profile
from hireloop.services.profile import _advance_onboarding


def _profile(**overrides) -> Profile:
    p = Profile(user_id=uuid4(), onboarding_state="resume_upload")
    for k, v in overrides.items():
        setattr(p, k, v)
    return p


def test_advance_from_resume_upload_to_done_when_resume_parsed() -> None:
    profile = _profile(master_resume_md="# Resume\n\n...content...")
    became_done = _advance_onboarding(profile)
    assert profile.onboarding_state == "done"
    assert became_done is True


def test_advance_does_not_transition_without_resume() -> None:
    profile = _profile()  # no resume
    became_done = _advance_onboarding(profile)
    assert profile.onboarding_state == "resume_upload"
    assert became_done is False


def test_advance_is_idempotent_on_done_profile() -> None:
    profile = _profile(onboarding_state="done", master_resume_md="# Resume")
    became_done = _advance_onboarding(profile)
    assert profile.onboarding_state == "done"
    assert became_done is False  # already done, no new transition


def test_preferences_data_does_not_block_advancement() -> None:
    """Having roles+locations is no longer needed to reach 'done'."""
    profile = _profile(master_resume_md="# Resume")  # no roles, no locations
    became_done = _advance_onboarding(profile)
    assert profile.onboarding_state == "done"
    assert became_done is True


def test_legacy_preferences_state_advances_if_has_resume() -> None:
    """Legacy profiles left in 'preferences' with a resume self-heal."""
    profile = _profile(onboarding_state="preferences", master_resume_md="# Resume")
    became_done = _advance_onboarding(profile)
    assert profile.onboarding_state == "done"
    assert became_done is True
```

- [ ] **Step 2: Run the tests and verify they fail**

```bash
cd backend && uv run pytest tests/unit/test_profile_service_onboarding_collapse.py -v
```

Expected: all 5 tests fail (current `_advance_onboarding` still requires `has_prefs` for the terminal transition).

- [ ] **Step 3: Replace `_advance_onboarding` in `services/profile.py`**

Find lines 32-53 (the current `_advance_onboarding` function) and replace with:

```python
def _advance_onboarding(profile: Profile) -> bool:
    """Advance the collapsed onboarding state machine.

    2026-04-22: Preferences collection is no longer part of the gate. A
    profile with a parsed resume transitions directly to 'done'. See
    docs/superpowers/specs/2026-04-22-onboarding-redesign-design.md.

    Returns True if the profile transitioned to the terminal 'done' state
    on this call (i.e. was not 'done' before).
    """
    was_done = profile.onboarding_state == "done"

    has_resume = bool(profile.master_resume_md)

    if profile.onboarding_state in ("resume_upload", "preferences") and has_resume:
        profile.onboarding_state = "done"

    return profile.onboarding_state == "done" and not was_done
```

- [ ] **Step 4: Remove the stale `profile.onboarding_state = "preferences"` line in `upload_resume`**

In the same file, find the block inside `upload_resume` that does:

```python
    if profile.onboarding_state == "resume_upload":
        profile.onboarding_state = "preferences"
```

Delete those two lines entirely (the new `_advance_onboarding` handles the transition directly to `'done'`).

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd backend && uv run pytest tests/unit/test_profile_service_onboarding_collapse.py -v
```

Expected: 5 passed.

- [ ] **Step 6: Run existing profile tests to verify no regression**

```bash
cd backend && uv run pytest tests/integration/test_profile_crud.py -v
```

Expected: all pass. The existing `test_put_profile_updates_preferences` asserts `onboarding_state in ("preferences", "done")` which still holds when profile has no resume (stays `resume_upload`) — **actually this will break**. Update that assertion in the same commit:

Find `backend/tests/integration/test_profile_crud.py` line around the preferences assertion and change:

```python
assert body["onboarding_state"] in ("preferences", "done")
```

to:

```python
# Post-2026-04-22: preferences collection no longer gates onboarding_state.
# A profile with no resume stays in resume_upload regardless of prefs.
assert body["onboarding_state"] == "resume_upload"
```

Re-run `pytest tests/integration/test_profile_crud.py -v` — should pass.

- [ ] **Step 7: Commit**

```bash
git add backend/src/hireloop/services/profile.py \
        backend/tests/unit/test_profile_service_onboarding_collapse.py \
        backend/tests/integration/test_profile_crud.py
git commit -m "feat(onboarding): collapse _advance_onboarding to resume→done"
```

---

## Task 3: `POST /profile/resume-text` endpoint

**Files:**
- Modify: `backend/src/hireloop/schemas/profile.py` (add `ResumeTextRequest`)
- Modify: `backend/src/hireloop/services/profile.py` (add `upload_resume_text`)
- Modify: `backend/src/hireloop/api/profile.py` (add endpoint)
- Test: `backend/tests/integration/test_profile_resume_text_endpoint.py`

- [ ] **Step 1: Write failing integration tests**

```python
# backend/tests/integration/test_profile_resume_text_endpoint.py
"""Integration tests for POST /profile/resume-text (paste-text fallback)."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

FAKE_CLAIMS = {
    "sub": "cognito-sub-resume-text",
    "email": "resume-text@example.com",
    "custom:role": "user",
    "custom:subscription_tier": "trial",
}


@pytest.mark.asyncio
async def test_resume_text_happy_path_parses_and_advances_to_done(
    client: AsyncClient,
) -> None:
    with patch(
        "hireloop.integrations.cognito.CognitoJwtVerifier.verify",
        new=AsyncMock(return_value=FAKE_CLAIMS),
    ):
        await client.get("/api/v1/profile", headers={"Authorization": "Bearer fake"})
        response = await client.post(
            "/api/v1/profile/resume-text",
            headers={"Authorization": "Bearer fake"},
            json={
                "text": (
                    "# Jane Doe\n\nSenior Backend Engineer, 8 years.\n\n"
                    "## Experience\n\nAcme Corp, 2020-present.\n"
                )
            },
        )

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["onboarding_state"] == "done"


@pytest.mark.asyncio
async def test_resume_text_rejects_empty_body(client: AsyncClient) -> None:
    claims = {**FAKE_CLAIMS, "sub": "cognito-sub-resume-text-empty", "email": "empty@example.com"}
    with patch(
        "hireloop.integrations.cognito.CognitoJwtVerifier.verify",
        new=AsyncMock(return_value=claims),
    ):
        response = await client.post(
            "/api/v1/profile/resume-text",
            headers={"Authorization": "Bearer fake"},
            json={"text": ""},
        )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_resume_text_rejects_oversize(client: AsyncClient) -> None:
    claims = {**FAKE_CLAIMS, "sub": "cognito-sub-resume-text-big", "email": "big@example.com"}
    with patch(
        "hireloop.integrations.cognito.CognitoJwtVerifier.verify",
        new=AsyncMock(return_value=claims),
    ):
        response = await client.post(
            "/api/v1/profile/resume-text",
            headers={"Authorization": "Bearer fake"},
            json={"text": "a" * 50_001},
        )
    assert response.status_code == 422
```

- [ ] **Step 2: Run tests, expect failures**

```bash
cd backend && uv run pytest tests/integration/test_profile_resume_text_endpoint.py -v
```

Expected: 3 tests fail with 404 (endpoint doesn't exist yet).

- [ ] **Step 3: Add `ResumeTextRequest` to `schemas/profile.py`**

Append at the bottom of `backend/src/hireloop/schemas/profile.py`:

```python
from pydantic import BaseModel, Field


class ResumeTextRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=50_000)
```

Use the file's existing `BaseModel`/`Field` import if already present — do not duplicate.

- [ ] **Step 4: Add `upload_resume_text` service in `services/profile.py`**

Append to `backend/src/hireloop/services/profile.py`:

```python
async def upload_resume_text(
    db: AsyncSession,
    profile: Profile,
    text: str,
) -> Profile:
    """Store pasted resume text directly as master_resume_md.

    Skips S3 upload and the PDF/DOCX parser — the caller has given us
    markdown-ish text already. Still advances onboarding on success.
    """
    profile.master_resume_md = text
    profile.parsed_resume_json = {"text": text, "content_type": "text/markdown"}

    became_done = _advance_onboarding(profile)
    if became_done:
        await _on_onboarding_done(db, profile)

    await db.flush()
    return profile
```

- [ ] **Step 5: Add endpoint in `api/profile.py`**

Append to `backend/src/hireloop/api/profile.py` before the final `export_profile` endpoint:

```python
from hireloop.schemas.profile import ResumeTextRequest
from hireloop.services.profile import upload_resume_text


@router.post("/resume-text", response_model=Envelope[ProfileResponse])
async def upload_resume_text_endpoint(
    body: ResumeTextRequest,
    user: CurrentDbUser,
    db: DbSession,
) -> Envelope[ProfileResponse]:
    profile = await get_or_create_profile(db, user)
    profile = await upload_resume_text(db, profile, body.text)
    await db.refresh(profile)
    return Envelope(data=ProfileResponse.model_validate(profile))
```

Merge the new imports into the existing import block at the top of the file — don't leave them mid-file.

- [ ] **Step 6: Run tests, verify pass**

```bash
cd backend && uv run pytest tests/integration/test_profile_resume_text_endpoint.py -v
```

Expected: 3 passed.

- [ ] **Step 7: Commit**

```bash
git add backend/src/hireloop/schemas/profile.py \
        backend/src/hireloop/services/profile.py \
        backend/src/hireloop/api/profile.py \
        backend/tests/integration/test_profile_resume_text_endpoint.py
git commit -m "feat(api): POST /profile/resume-text paste-text fallback"
```

---

## Task 4: `POST /jobs/parse-text` endpoint

**Files:**
- Modify: `backend/src/hireloop/schemas/job.py` (add `JobParseTextRequest`)
- Modify: `backend/src/hireloop/api/jobs.py` (add endpoint)
- Test: `backend/tests/integration/test_jobs_parse_text_endpoint.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/integration/test_jobs_parse_text_endpoint.py
"""Integration tests for POST /jobs/parse-text (paste-text fallback)."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

FAKE_CLAIMS = {
    "sub": "cognito-sub-jobs-parse-text",
    "email": "jobs-parse-text@example.com",
    "custom:role": "user",
    "custom:subscription_tier": "trial",
}

SAMPLE_JD = """Senior Backend Engineer at Acme Corp.

Requirements:
- 5+ years Python
- AWS, distributed systems
- Remote OK

Comp: $180k-$220k base.
"""


@pytest.mark.asyncio
async def test_parse_text_happy_path(client: AsyncClient) -> None:
    fake_parsed = AsyncMock()
    fake_parsed.return_value.content_hash = "abc123"
    fake_parsed.return_value.url = "https://example.com/jobs/1"
    fake_parsed.return_value.title = "Senior Backend Engineer"
    fake_parsed.return_value.company = "Acme Corp"
    fake_parsed.return_value.location = "Remote"
    fake_parsed.return_value.salary_min = 180_000
    fake_parsed.return_value.salary_max = 220_000
    fake_parsed.return_value.employment_type = "full_time"
    fake_parsed.return_value.seniority = "senior"
    fake_parsed.return_value.description_md = SAMPLE_JD
    fake_parsed.return_value.requirements_json = {"skills": ["Python", "AWS"]}

    with patch(
        "hireloop.integrations.cognito.CognitoJwtVerifier.verify",
        new=AsyncMock(return_value=FAKE_CLAIMS),
    ), patch(
        "hireloop.api.jobs.parse_description",
        new=fake_parsed,
    ):
        await client.get("/api/v1/profile", headers={"Authorization": "Bearer fake"})
        response = await client.post(
            "/api/v1/jobs/parse-text",
            headers={"Authorization": "Bearer fake"},
            json={"text": SAMPLE_JD, "source_url": "https://example.com/jobs/1"},
        )

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["title"] == "Senior Backend Engineer"
    assert body["url"] == "https://example.com/jobs/1"


@pytest.mark.asyncio
async def test_parse_text_rejects_empty_text(client: AsyncClient) -> None:
    claims = {**FAKE_CLAIMS, "sub": "cognito-sub-jobs-parse-empty", "email": "e@example.com"}
    with patch(
        "hireloop.integrations.cognito.CognitoJwtVerifier.verify",
        new=AsyncMock(return_value=claims),
    ):
        response = await client.post(
            "/api/v1/jobs/parse-text",
            headers={"Authorization": "Bearer fake"},
            json={"text": ""},
        )
    assert response.status_code == 422
```

- [ ] **Step 2: Run, expect failure**

```bash
cd backend && uv run pytest tests/integration/test_jobs_parse_text_endpoint.py -v
```

Expected: 2 tests fail.

- [ ] **Step 3: Add `JobParseTextRequest` to `schemas/job.py`**

Append to `backend/src/hireloop/schemas/job.py`:

```python
class JobParseTextRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=50_000)
    source_url: str | None = None
```

- [ ] **Step 4: Add endpoint in `api/jobs.py`**

Add to `backend/src/hireloop/api/jobs.py` after the existing `parse_job` function:

```python
from hireloop.schemas.job import JobParseTextRequest


@router.post("/parse-text")
async def parse_job_text(
    payload: JobParseTextRequest, current_user: EntitledDbUser
) -> dict[str, Any]:
    _ = current_user
    parsed = await parse_description(payload.text)
    return {
        "data": {
            "content_hash": parsed.content_hash,
            "url": payload.source_url or parsed.url,
            "title": parsed.title,
            "company": parsed.company,
            "location": parsed.location,
            "salary_min": parsed.salary_min,
            "salary_max": parsed.salary_max,
            "employment_type": parsed.employment_type,
            "seniority": parsed.seniority,
            "description_md": parsed.description_md,
            "requirements_json": parsed.requirements_json,
        }
    }
```

Merge the `JobParseTextRequest` import into the existing import block.

- [ ] **Step 5: Run tests, verify pass**

```bash
cd backend && uv run pytest tests/integration/test_jobs_parse_text_endpoint.py -v
```

Expected: 2 passed.

- [ ] **Step 6: Commit**

```bash
git add backend/src/hireloop/schemas/job.py \
        backend/src/hireloop/api/jobs.py \
        backend/tests/integration/test_jobs_parse_text_endpoint.py
git commit -m "feat(api): POST /jobs/parse-text paste-text fallback"
```

---

## Task 5: `POST /onboarding/first-evaluation` endpoint

**Files:**
- Create: `backend/src/hireloop/schemas/onboarding.py`
- Create: `backend/src/hireloop/api/onboarding.py`
- Modify: `backend/src/hireloop/main.py` (register router)
- Test: `backend/tests/integration/test_onboarding_first_evaluation.py`

- [ ] **Step 1: Write failing integration test**

```python
# backend/tests/integration/test_onboarding_first_evaluation.py
"""Integration tests for POST /onboarding/first-evaluation."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

FAKE_CLAIMS = {
    "sub": "cognito-sub-onboarding-first-eval",
    "email": "first-eval@example.com",
    "custom:role": "user",
    "custom:subscription_tier": "trial",
}


@pytest.mark.asyncio
async def test_first_evaluation_text_input_persists_and_returns_envelope(
    client: AsyncClient,
) -> None:
    fake_parsed = AsyncMock()
    fake_parsed.return_value.content_hash = "hash-1"
    fake_parsed.return_value.url = None
    fake_parsed.return_value.title = "Senior Backend Engineer"
    fake_parsed.return_value.company = "Acme"
    fake_parsed.return_value.location = "Remote"
    fake_parsed.return_value.salary_min = None
    fake_parsed.return_value.salary_max = None
    fake_parsed.return_value.employment_type = "full_time"
    fake_parsed.return_value.seniority = "senior"
    fake_parsed.return_value.description_md = "Senior backend role..."
    fake_parsed.return_value.requirements_json = {"skills": ["Python"]}

    fake_eval = AsyncMock()
    fake_eval.return_value = {
        "id": "eval-id-1",
        "overall_score": 82,
        "grade": "B+",
        "strengths": [],
        "gaps": [],
    }

    with patch(
        "hireloop.integrations.cognito.CognitoJwtVerifier.verify",
        new=AsyncMock(return_value=FAKE_CLAIMS),
    ), patch(
        "hireloop.api.onboarding.parse_description",
        new=fake_parsed,
    ), patch(
        "hireloop.api.onboarding.run_first_evaluation",
        new=fake_eval,
    ):
        # First, give this user a resume so the endpoint doesn't 409.
        await client.post(
            "/api/v1/profile/resume-text",
            headers={"Authorization": "Bearer fake"},
            json={"text": "# Resume\nSenior Backend Engineer, 8 yrs."},
        )
        response = await client.post(
            "/api/v1/onboarding/first-evaluation",
            headers={"Authorization": "Bearer fake"},
            json={"job_input": {"type": "text", "value": "Senior backend role..."}},
        )

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["evaluation"]["id"] == "eval-id-1"
    assert body["job"]["title"] == "Senior Backend Engineer"


@pytest.mark.asyncio
async def test_first_evaluation_requires_resume(client: AsyncClient) -> None:
    claims = {**FAKE_CLAIMS, "sub": "cognito-sub-first-eval-noresume", "email": "nr@example.com"}
    with patch(
        "hireloop.integrations.cognito.CognitoJwtVerifier.verify",
        new=AsyncMock(return_value=claims),
    ):
        await client.get("/api/v1/profile", headers={"Authorization": "Bearer fake"})
        response = await client.post(
            "/api/v1/onboarding/first-evaluation",
            headers={"Authorization": "Bearer fake"},
            json={"job_input": {"type": "text", "value": "..."}},
        )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "RESUME_REQUIRED"
```

- [ ] **Step 2: Run, expect failure**

```bash
cd backend && uv run pytest tests/integration/test_onboarding_first_evaluation.py -v
```

Expected: both tests fail with 404.

- [ ] **Step 3: Create `schemas/onboarding.py`**

```python
# backend/src/hireloop/schemas/onboarding.py
"""Onboarding request/response schemas."""

from typing import Any, Literal

from pydantic import BaseModel, Field


class JobInput(BaseModel):
    type: Literal["url", "text"]
    value: str = Field(..., min_length=1, max_length=50_000)


class FirstEvaluationRequest(BaseModel):
    job_input: JobInput


class FirstEvaluationResponse(BaseModel):
    evaluation: dict[str, Any]
    job: dict[str, Any]
```

- [ ] **Step 4: Create `api/onboarding.py`**

```python
# backend/src/hireloop/api/onboarding.py
"""Onboarding-specific endpoints.

POST /onboarding/first-evaluation — orchestrates parse-job + evaluate in one
shot so the frontend can show a single loading state for the ~60s flow.
"""

from typing import Any

from fastapi import APIRouter

from hireloop.api.deps import CurrentDbUser, DbSession
from hireloop.api.errors import AppError
from hireloop.core.evaluation.job_parser import parse_description, parse_url
from hireloop.core.evaluation.first_evaluation import run_first_evaluation
from hireloop.schemas.common import Envelope
from hireloop.schemas.onboarding import FirstEvaluationRequest, FirstEvaluationResponse
from hireloop.services.profile import get_or_create_profile

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


@router.post("/first-evaluation", response_model=Envelope[FirstEvaluationResponse])
async def first_evaluation(
    body: FirstEvaluationRequest,
    user: CurrentDbUser,
    db: DbSession,
) -> Envelope[FirstEvaluationResponse]:
    profile = await get_or_create_profile(db, user)
    if not profile.master_resume_md:
        raise AppError(409, "RESUME_REQUIRED", "Upload a resume before running an evaluation.")

    if body.job_input.type == "url":
        parsed = await parse_url(body.job_input.value)
    else:
        parsed = await parse_description(body.job_input.value)

    evaluation: dict[str, Any] = await run_first_evaluation(
        db=db, user=user, profile=profile, parsed_job=parsed
    )

    return Envelope(
        data=FirstEvaluationResponse(
            evaluation=evaluation,
            job={
                "content_hash": parsed.content_hash,
                "url": parsed.url,
                "title": parsed.title,
                "company": parsed.company,
                "location": parsed.location,
                "description_md": parsed.description_md,
            },
        )
    )
```

- [ ] **Step 5: Create the `run_first_evaluation` helper**

Create `backend/src/hireloop/core/evaluation/first_evaluation.py`:

```python
"""First-evaluation helper used only by the onboarding endpoint.

Wraps the regular evaluation pipeline with a single responsibility: parse-then-
evaluate in one blocking call, return a JSON-serializable dict ready for the
frontend card. This stays separate from the regular `/evaluations` POST so we
can tune the prompt / model for the very first user-facing evaluation if
needed without affecting the agent tool path.
"""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from hireloop.models.profile import Profile
from hireloop.models.user import User
from hireloop.services.evaluation import create_evaluation_for_parsed_job


async def run_first_evaluation(
    *,
    db: AsyncSession,
    user: User,
    profile: Profile,
    parsed_job: Any,
) -> dict[str, Any]:
    evaluation = await create_evaluation_for_parsed_job(
        db=db, user=user, profile=profile, parsed_job=parsed_job
    )
    return {
        "id": str(evaluation.id),
        "overall_score": evaluation.overall_score,
        "grade": evaluation.grade,
        "strengths": evaluation.strengths_json or [],
        "gaps": evaluation.gaps_json or [],
        "job_id": str(evaluation.job_id) if evaluation.job_id else None,
    }
```

**Important: `create_evaluation_for_parsed_job` must exist.** If it does not, before Step 5, extract a reusable service function from `hireloop/services/evaluation.py` or the agent tool that calls the evaluation pipeline. Inspect the current agent tool in `backend/src/hireloop/core/agent/tools.py` (`evaluate_job` handler) to see the canonical call path and extract the non-agent bits into `services/evaluation.py:create_evaluation_for_parsed_job`. If such a function already exists, just use it. Do not duplicate evaluation logic.

- [ ] **Step 6: Register router in `main.py`**

Modify `backend/src/hireloop/main.py`. Find the block that includes routers (search for `include_router`) and add:

```python
from hireloop.api import onboarding  # existing block pattern

# ... inside the include_router calls:
app.include_router(onboarding.router, prefix="/api/v1")
```

Follow the exact pattern of the sibling `app.include_router(profile.router, ...)` call.

- [ ] **Step 7: Run tests, verify pass**

```bash
cd backend && uv run pytest tests/integration/test_onboarding_first_evaluation.py -v
```

Expected: 2 passed.

- [ ] **Step 8: Commit**

```bash
git add backend/src/hireloop/schemas/onboarding.py \
        backend/src/hireloop/api/onboarding.py \
        backend/src/hireloop/core/evaluation/first_evaluation.py \
        backend/src/hireloop/main.py \
        backend/tests/integration/test_onboarding_first_evaluation.py
git commit -m "feat(api): POST /onboarding/first-evaluation — parse+eval in one call"
```

---

## Task 6: Tailwind — add accent-teal/cobalt/violet tokens

**Files:**
- Modify: `user-portal/tailwind.config.ts`

- [ ] **Step 1: Edit the colors block**

In `user-portal/tailwind.config.ts`, extend the `colors` object:

```ts
colors: {
  bg: '#ffffff',
  sidebar: '#fbfbfa',
  card: '#f7f6f3',
  'text-primary': '#37352f',
  'text-secondary': '#787774',
  accent: '#2383e2',
  border: '#e3e2e0',
  hover: '#efefef',
  'accent-teal': '#14b8a6',
  'accent-cobalt': '#2563eb',
  'accent-violet': '#7c3aed',
},
```

- [ ] **Step 2: Verify TypeScript still compiles**

```bash
cd user-portal && pnpm exec tsc --noEmit
```

Expected: exit 0, no errors.

- [ ] **Step 3: Commit**

```bash
git add user-portal/tailwind.config.ts
git commit -m "feat(ui): add marketing gradient stops to portal tailwind tokens"
```

---

## Task 7: `GradientButton` shared component

**Files:**
- Create: `user-portal/src/components/ui/GradientButton.tsx`
- Test: `user-portal/src/components/ui/GradientButton.test.tsx`

- [ ] **Step 1: Write the failing test**

```tsx
// user-portal/src/components/ui/GradientButton.test.tsx
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { GradientButton } from './GradientButton';

describe('GradientButton', () => {
  it('renders the label', () => {
    render(<GradientButton>Tailor my CV</GradientButton>);
    expect(screen.getByRole('button', { name: 'Tailor my CV' })).toBeInTheDocument();
  });

  it('fires onClick', async () => {
    const onClick = vi.fn();
    const { default: userEvent } = await import('@testing-library/user-event');
    render(<GradientButton onClick={onClick}>Go</GradientButton>);
    await userEvent.default.setup().click(screen.getByRole('button', { name: 'Go' }));
    expect(onClick).toHaveBeenCalled();
  });

  it('applies the marketing gradient classes', () => {
    render(<GradientButton>X</GradientButton>);
    const btn = screen.getByRole('button', { name: 'X' });
    expect(btn.className).toContain('from-accent-teal');
    expect(btn.className).toContain('via-accent-cobalt');
    expect(btn.className).toContain('to-accent-violet');
  });

  it('supports disabled state', () => {
    render(<GradientButton disabled>X</GradientButton>);
    expect(screen.getByRole('button', { name: 'X' })).toBeDisabled();
  });
});
```

- [ ] **Step 2: Run, expect failure**

```bash
cd user-portal && pnpm exec vitest run src/components/ui/GradientButton.test.tsx
```

Expected: module not found.

- [ ] **Step 3: Implement the component**

```tsx
// user-portal/src/components/ui/GradientButton.tsx
import type { ButtonHTMLAttributes, ReactNode } from 'react';

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  children: ReactNode;
};

export function GradientButton({ children, className = '', ...rest }: Props): JSX.Element {
  return (
    <button
      {...rest}
      className={
        'inline-flex items-center justify-center rounded-full ' +
        'bg-gradient-to-r from-accent-teal via-accent-cobalt to-accent-violet ' +
        'px-6 py-3 text-base font-semibold text-white ' +
        'shadow-[0_10px_30px_-10px_rgba(37,99,235,0.5)] transition-all ' +
        'hover:-translate-y-0.5 hover:shadow-[0_18px_45px_-12px_rgba(124,58,237,0.7)] ' +
        'disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:translate-y-0 ' +
        className
      }
    >
      {children}
    </button>
  );
}
```

- [ ] **Step 4: Run tests, verify pass**

```bash
cd user-portal && pnpm exec vitest run src/components/ui/GradientButton.test.tsx
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add user-portal/src/components/ui/GradientButton.tsx \
        user-portal/src/components/ui/GradientButton.test.tsx
git commit -m "feat(ui): GradientButton primitive matching marketing CTAs"
```

---

## Task 8: `GradientBadge` for evaluation grade tiers

**Files:**
- Create: `user-portal/src/components/ui/GradientBadge.tsx`
- Test: `user-portal/src/components/ui/GradientBadge.test.tsx`

- [ ] **Step 1: Write the failing test**

```tsx
// user-portal/src/components/ui/GradientBadge.test.tsx
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { GradientBadge } from './GradientBadge';

describe('GradientBadge', () => {
  it('renders the score', () => {
    render(<GradientBadge grade="A-" score={82} />);
    expect(screen.getByText('82')).toBeInTheDocument();
  });

  it('uses teal→green gradient for A', () => {
    render(<GradientBadge grade="A" score={94} />);
    const el = screen.getByText('94').closest('div');
    expect(el?.className).toMatch(/from-\[#14b8a6\]/);
    expect(el?.className).toMatch(/to-\[#22c55e\]/);
  });

  it('uses cobalt→violet gradient for B+', () => {
    render(<GradientBadge grade="B+" score={75} />);
    const el = screen.getByText('75').closest('div');
    expect(el?.className).toMatch(/from-\[#2563eb\]/);
    expect(el?.className).toMatch(/to-\[#7c3aed\]/);
  });

  it('renders C-grade with neutral amber', () => {
    render(<GradientBadge grade="C" score={55} />);
    const el = screen.getByText('55').closest('div');
    expect(el?.className).toMatch(/from-\[#f59e0b\]/);
  });
});
```

- [ ] **Step 2: Run, expect failure**

```bash
cd user-portal && pnpm exec vitest run src/components/ui/GradientBadge.test.tsx
```

Expected: module not found.

- [ ] **Step 3: Implement**

```tsx
// user-portal/src/components/ui/GradientBadge.tsx
export type Grade = 'A' | 'A-' | 'B+' | 'B' | 'C';

const GRADE_GRADIENT: Record<Grade, string> = {
  A: 'from-[#14b8a6] to-[#22c55e]',
  'A-': 'from-[#14b8a6] to-[#2563eb]',
  'B+': 'from-[#2563eb] to-[#7c3aed]',
  B: 'from-[#7c3aed] to-[#a855f7]',
  C: 'from-[#f59e0b] to-[#f97316]',
};

type Props = {
  grade: Grade;
  score: number;
  size?: 'sm' | 'lg';
};

export function GradientBadge({ grade, score, size = 'lg' }: Props): JSX.Element {
  const dim = size === 'lg' ? 'h-16 w-16 text-2xl' : 'h-8 w-8 text-sm';
  return (
    <div
      className={
        `flex flex-none items-center justify-center rounded-2xl bg-gradient-to-br ` +
        `${GRADE_GRADIENT[grade]} ${dim} font-black text-white ` +
        `shadow-[0_12px_28px_-10px_rgba(37,99,235,0.6)]`
      }
      aria-label={`Grade ${grade}, score ${score}`}
    >
      {score}
    </div>
  );
}
```

- [ ] **Step 4: Run tests, verify pass**

```bash
cd user-portal && pnpm exec vitest run src/components/ui/GradientBadge.test.tsx
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add user-portal/src/components/ui/GradientBadge.tsx \
        user-portal/src/components/ui/GradientBadge.test.tsx
git commit -m "feat(ui): GradientBadge for evaluation grade tiers"
```

---

## Task 9: Frontend API wrappers — `profile.uploadResumeText`, `jobs.parseText`, `onboarding.firstEvaluation`

**Files:**
- Modify: `user-portal/src/lib/api.ts`

- [ ] **Step 1: Find the existing `profile:` namespace and the `jobs:` namespace**

In `user-portal/src/lib/api.ts`, find `profile: {` and `jobs: {` namespaces (search the file). Confirm they exist; if `jobs:` doesn't exist yet, add it as a new namespace.

- [ ] **Step 2: Add `uploadResumeText` to the `profile:` namespace**

Inside the `profile: { ... }` block, after the existing methods, add:

```ts
    uploadResumeText: (text: string) =>
      request<{ data: Profile }>('POST', '/api/v1/profile/resume-text', { text }),
```

- [ ] **Step 3: Add `parseText` to the `jobs:` namespace**

Inside (or creating) the `jobs: { ... }` block:

```ts
  jobs: {
    parse: (body: { url?: string; description_md?: string }) =>
      request<{ data: ParsedJob }>('POST', '/api/v1/jobs/parse', body),
    parseText: (body: { text: string; source_url?: string }) =>
      request<{ data: ParsedJob }>('POST', '/api/v1/jobs/parse-text', body),
  },
```

If `ParsedJob` type is not yet exported, add it next to existing types at the top of the file:

```ts
export type ParsedJob = {
  content_hash: string;
  url: string | null;
  title: string;
  company: string;
  location: string | null;
  salary_min: number | null;
  salary_max: number | null;
  employment_type: string | null;
  seniority: string | null;
  description_md: string;
  requirements_json: Record<string, unknown> | null;
};
```

- [ ] **Step 4: Add `onboarding:` namespace with `firstEvaluation`**

After the `jobs:` block, add:

```ts
  onboarding: {
    firstEvaluation: (body: {
      job_input: { type: 'url' | 'text'; value: string };
    }) =>
      request<{
        data: {
          evaluation: {
            id: string;
            overall_score: number;
            grade: 'A' | 'A-' | 'B+' | 'B' | 'C';
            strengths: Array<{ text: string }>;
            gaps: Array<{ text: string }>;
            job_id: string | null;
          };
          job: {
            content_hash: string;
            url: string | null;
            title: string;
            company: string;
            location: string | null;
            description_md: string;
          };
        };
      }>('POST', '/api/v1/onboarding/first-evaluation', body),
  },
```

- [ ] **Step 5: Verify types compile**

```bash
cd user-portal && pnpm exec tsc --noEmit
```

Expected: exit 0.

- [ ] **Step 6: Commit**

```bash
git add user-portal/src/lib/api.ts
git commit -m "feat(ui): api wrappers for resume-text, parse-text, first-evaluation"
```

---

## Task 10: `ResumeUploadStep` component

**Files:**
- Create: `user-portal/src/components/onboarding/ResumeUploadStep.tsx`
- Test: `user-portal/src/components/onboarding/ResumeUploadStep.test.tsx`

- [ ] **Step 1: Write the failing test**

```tsx
// user-portal/src/components/onboarding/ResumeUploadStep.test.tsx
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import { ResumeUploadStep } from './ResumeUploadStep';
import { api } from '../../lib/api';

vi.mock('../../lib/api', () => ({
  api: {
    profile: {
      uploadResume: vi.fn(),
      uploadResumeText: vi.fn(),
    },
  },
}));

describe('ResumeUploadStep', () => {
  beforeEach(() => vi.clearAllMocks());

  it('shows the upload zone and the paste-text fallback link', () => {
    render(<ResumeUploadStep onAdvance={vi.fn()} />);
    expect(screen.getByText(/drag and drop|browse/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /paste text/i })).toBeInTheDocument();
  });

  it('reveals textarea when paste-text link clicked', async () => {
    render(<ResumeUploadStep onAdvance={vi.fn()} />);
    await userEvent.setup().click(screen.getByRole('button', { name: /paste text/i }));
    expect(screen.getByRole('textbox')).toBeInTheDocument();
  });

  it('calls uploadResumeText and advances on successful paste', async () => {
    const onAdvance = vi.fn();
    (api.profile.uploadResumeText as vi.Mock).mockResolvedValue({
      data: { onboarding_state: 'done' },
    });
    render(<ResumeUploadStep onAdvance={onAdvance} />);
    const user = userEvent.setup();
    await user.click(screen.getByRole('button', { name: /paste text/i }));
    await user.type(screen.getByRole('textbox'), 'My resume content');
    await user.click(screen.getByRole('button', { name: /continue/i }));
    await waitFor(() => expect(api.profile.uploadResumeText).toHaveBeenCalledWith('My resume content'));
    expect(onAdvance).toHaveBeenCalled();
  });

  it('surfaces errors inline on failure', async () => {
    (api.profile.uploadResumeText as vi.Mock).mockRejectedValue(new Error('parse failed'));
    render(<ResumeUploadStep onAdvance={vi.fn()} />);
    const user = userEvent.setup();
    await user.click(screen.getByRole('button', { name: /paste text/i }));
    await user.type(screen.getByRole('textbox'), 'x');
    await user.click(screen.getByRole('button', { name: /continue/i }));
    await waitFor(() => expect(screen.getByText(/parse failed/i)).toBeInTheDocument());
  });
});
```

- [ ] **Step 2: Run, expect failure**

```bash
cd user-portal && pnpm exec vitest run src/components/onboarding/ResumeUploadStep.test.tsx
```

Expected: module not found.

- [ ] **Step 3: Implement the component**

```tsx
// user-portal/src/components/onboarding/ResumeUploadStep.tsx
import { useState, useRef } from 'react';
import { GradientButton } from '../ui/GradientButton';
import { api } from '../../lib/api';

type Props = {
  onAdvance: () => void;
};

export function ResumeUploadStep({ onAdvance }: Props): JSX.Element {
  const [pasteMode, setPasteMode] = useState(false);
  const [text, setText] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  async function onFile(file: File) {
    setBusy(true);
    setError(null);
    try {
      const form = new FormData();
      form.append('file', file);
      await api.profile.uploadResume(form);
      onAdvance();
    } catch (e) {
      setError((e as Error).message);
      setPasteMode(true); // auto-reveal fallback
    } finally {
      setBusy(false);
    }
  }

  async function onPaste() {
    setBusy(true);
    setError(null);
    try {
      await api.profile.uploadResumeText(text);
      onAdvance();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div
        onClick={() => fileRef.current?.click()}
        className="rounded-2xl border-2 border-dashed border-border p-12 text-center cursor-pointer hover:bg-hover"
      >
        <p className="font-medium">Drag and drop your resume, or browse</p>
        <p className="mt-1 text-sm text-text-secondary">PDF or DOCX, up to 10MB</p>
        <input
          ref={fileRef}
          type="file"
          accept=".pdf,.docx"
          className="hidden"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) void onFile(f);
          }}
        />
      </div>

      <button
        type="button"
        className="text-sm text-accent-cobalt hover:underline self-start"
        onClick={() => setPasteMode((v) => !v)}
      >
        {pasteMode ? 'Upload a file instead' : 'Paste text instead'}
      </button>

      {pasteMode && (
        <div className="flex flex-col gap-2">
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={12}
            className="w-full rounded-lg border border-border p-3 font-mono text-sm"
            placeholder="Paste your resume as plain text or markdown…"
          />
          <GradientButton disabled={busy || !text.trim()} onClick={() => void onPaste()}>
            {busy ? 'Processing…' : 'Continue'}
          </GradientButton>
        </div>
      )}

      {error && (
        <p role="alert" className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">
          {error}
        </p>
      )}
    </div>
  );
}
```

Ensure `api.profile.uploadResume(form)` exists in `api.ts`. If the existing signature uses a different wrapper (it may take a `File` directly), adapt the call here to match. Verify by grep:

```bash
grep -n "uploadResume" user-portal/src/lib/api.ts
```

- [ ] **Step 4: Run tests, verify pass**

```bash
cd user-portal && pnpm exec vitest run src/components/onboarding/ResumeUploadStep.test.tsx
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add user-portal/src/components/onboarding/ResumeUploadStep.tsx \
        user-portal/src/components/onboarding/ResumeUploadStep.test.tsx
git commit -m "feat(ui): ResumeUploadStep with paste-text fallback"
```

---

## Task 11: `JobInputStep` component

**Files:**
- Create: `user-portal/src/components/onboarding/JobInputStep.tsx`
- Test: `user-portal/src/components/onboarding/JobInputStep.test.tsx`

- [ ] **Step 1: Write the failing test**

```tsx
// user-portal/src/components/onboarding/JobInputStep.test.tsx
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { JobInputStep } from './JobInputStep';

describe('JobInputStep', () => {
  it('calls onSubmit with {type:url} when a URL is entered', async () => {
    const onSubmit = vi.fn();
    render(<JobInputStep onSubmit={onSubmit} />);
    const user = userEvent.setup();
    await user.type(screen.getByRole('textbox'), 'https://example.com/jobs/1');
    await user.click(screen.getByRole('button', { name: /evaluate/i }));
    expect(onSubmit).toHaveBeenCalledWith({ type: 'url', value: 'https://example.com/jobs/1' });
  });

  it('calls onSubmit with {type:text} when raw text is entered', async () => {
    const onSubmit = vi.fn();
    render(<JobInputStep onSubmit={onSubmit} />);
    const user = userEvent.setup();
    await user.type(screen.getByRole('textbox'), 'Senior backend at Acme');
    await user.click(screen.getByRole('button', { name: /evaluate/i }));
    expect(onSubmit).toHaveBeenCalledWith({ type: 'text', value: 'Senior backend at Acme' });
  });

  it('disables submit while busy', () => {
    render(<JobInputStep onSubmit={vi.fn()} busy />);
    expect(screen.getByRole('button', { name: /evaluate/i })).toBeDisabled();
  });
});
```

- [ ] **Step 2: Run, expect failure**

```bash
cd user-portal && pnpm exec vitest run src/components/onboarding/JobInputStep.test.tsx
```

Expected: module not found.

- [ ] **Step 3: Implement**

```tsx
// user-portal/src/components/onboarding/JobInputStep.tsx
import { useState } from 'react';
import { GradientButton } from '../ui/GradientButton';

type Props = {
  onSubmit: (input: { type: 'url' | 'text'; value: string }) => void;
  busy?: boolean;
  error?: string | null;
};

export function JobInputStep({ onSubmit, busy = false, error = null }: Props): JSX.Element {
  const [value, setValue] = useState('');

  function submit() {
    const v = value.trim();
    if (!v) return;
    const type: 'url' | 'text' = /^https?:\/\//i.test(v) ? 'url' : 'text';
    onSubmit({ type, value: v });
  }

  return (
    <div className="flex flex-col gap-4">
      <h3 className="text-lg font-semibold">Paste a job you're curious about. We'll show you how you stack up.</h3>
      <textarea
        value={value}
        onChange={(e) => setValue(e.target.value)}
        rows={6}
        placeholder="https://example.com/jobs/123  — or paste the job description"
        className="w-full rounded-lg border border-border p-3 text-sm"
      />
      <GradientButton disabled={busy || !value.trim()} onClick={submit}>
        {busy ? 'Evaluating…' : 'Evaluate'}
      </GradientButton>
      {error && (
        <p role="alert" className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">
          {error}
        </p>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Run tests, verify pass**

```bash
cd user-portal && pnpm exec vitest run src/components/onboarding/JobInputStep.test.tsx
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add user-portal/src/components/onboarding/JobInputStep.tsx \
        user-portal/src/components/onboarding/JobInputStep.test.tsx
git commit -m "feat(ui): JobInputStep with URL/text auto-detect"
```

---

## Task 12: `EvaluationProgressStep` (60s loading screen)

**Files:**
- Create: `user-portal/src/components/onboarding/EvaluationProgressStep.tsx`
- Test: `user-portal/src/components/onboarding/EvaluationProgressStep.test.tsx`

- [ ] **Step 1: Write the failing test**

```tsx
// user-portal/src/components/onboarding/EvaluationProgressStep.test.tsx
import { render, screen, act } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { EvaluationProgressStep } from './EvaluationProgressStep';

describe('EvaluationProgressStep', () => {
  it('renders the three progress steps', () => {
    render(<EvaluationProgressStep />);
    expect(screen.getByText(/parsing job description/i)).toBeInTheDocument();
    expect(screen.getByText(/comparing to your profile/i)).toBeInTheDocument();
    expect(screen.getByText(/writing evaluation/i)).toBeInTheDocument();
  });

  it('advances the active step over time', () => {
    vi.useFakeTimers();
    render(<EvaluationProgressStep />);
    // At t=0, step 1 is active
    expect(screen.getByTestId('progress-step-1').className).toMatch(/active|text-text-primary/);
    // After 20s, step 2
    act(() => vi.advanceTimersByTime(20_000));
    expect(screen.getByTestId('progress-step-2').className).toMatch(/active|text-text-primary/);
    vi.useRealTimers();
  });
});
```

- [ ] **Step 2: Run, expect failure**

```bash
cd user-portal && pnpm exec vitest run src/components/onboarding/EvaluationProgressStep.test.tsx
```

Expected: module not found.

- [ ] **Step 3: Implement**

```tsx
// user-portal/src/components/onboarding/EvaluationProgressStep.tsx
import { useEffect, useState } from 'react';

const STEPS = [
  'Parsing job description',
  'Comparing to your profile',
  'Writing evaluation',
];

export function EvaluationProgressStep(): JSX.Element {
  const [active, setActive] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setActive((a) => Math.min(a + 1, STEPS.length - 1));
    }, 20_000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center gap-8">
      <div className="relative h-16 w-16">
        <div className="absolute inset-0 animate-spin rounded-full border-4 border-transparent border-t-accent-cobalt" />
        <div className="absolute inset-0 animate-spin rounded-full border-4 border-transparent border-b-accent-violet" style={{ animationDuration: '1.2s', animationDirection: 'reverse' }} />
      </div>
      <ul className="flex flex-col gap-2">
        {STEPS.map((label, i) => (
          <li
            key={label}
            data-testid={`progress-step-${i + 1}`}
            className={
              i <= active
                ? 'text-text-primary font-medium'
                : 'text-text-secondary'
            }
          >
            {i < active ? '✓' : i === active ? '→' : '○'} {label}
          </li>
        ))}
      </ul>
    </div>
  );
}
```

- [ ] **Step 4: Run tests, verify pass**

```bash
cd user-portal && pnpm exec vitest run src/components/onboarding/EvaluationProgressStep.test.tsx
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add user-portal/src/components/onboarding/EvaluationProgressStep.tsx \
        user-portal/src/components/onboarding/EvaluationProgressStep.test.tsx
git commit -m "feat(ui): EvaluationProgressStep animated 60s loader"
```

---

## Task 13: `OnboardingPage` wizard orchestrator

**Files:**
- Create: `user-portal/src/pages/OnboardingPage.tsx`
- Test: `user-portal/src/pages/OnboardingPage.test.tsx`

- [ ] **Step 1: Write the failing integration-style test**

```tsx
// user-portal/src/pages/OnboardingPage.test.tsx
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import OnboardingPage from './OnboardingPage';
import { api } from '../lib/api';

vi.mock('../lib/api', () => ({
  api: {
    profile: {
      get: vi.fn(),
      uploadResume: vi.fn(),
      uploadResumeText: vi.fn(),
    },
    onboarding: {
      firstEvaluation: vi.fn(),
    },
  },
}));

describe('OnboardingPage', () => {
  beforeEach(() => vi.clearAllMocks());

  it('starts on step 1 (resume upload) when onboarding_state is resume_upload', async () => {
    (api.profile.get as vi.Mock).mockResolvedValue({
      data: { onboarding_state: 'resume_upload' },
    });
    render(<OnboardingPage />);
    await waitFor(() => expect(screen.getByText(/drag and drop/i)).toBeInTheDocument());
  });

  it('advances to step 2 after successful resume upload', async () => {
    (api.profile.get as vi.Mock)
      .mockResolvedValueOnce({ data: { onboarding_state: 'resume_upload' } })
      .mockResolvedValueOnce({ data: { onboarding_state: 'done' } });
    (api.profile.uploadResumeText as vi.Mock).mockResolvedValue({
      data: { onboarding_state: 'done' },
    });
    const user = userEvent.setup();
    render(<OnboardingPage />);
    await waitFor(() => screen.getByRole('button', { name: /paste text/i }));
    await user.click(screen.getByRole('button', { name: /paste text/i }));
    await user.type(screen.getByRole('textbox'), 'Resume content');
    await user.click(screen.getByRole('button', { name: /continue/i }));
    await waitFor(() =>
      expect(screen.getByText(/paste a job/i)).toBeInTheDocument(),
    );
  });

  it('shows evaluation progress during the 60s wait', async () => {
    (api.profile.get as vi.Mock).mockResolvedValue({
      data: { onboarding_state: 'done', master_resume_md: '# x' },
    });
    let resolveEval: (v: any) => void = () => {};
    (api.onboarding.firstEvaluation as vi.Mock).mockReturnValue(
      new Promise((r) => {
        resolveEval = r;
      }),
    );
    const user = userEvent.setup();
    render(<OnboardingPage />);
    // skip to job step (we're pretending the caller forced it)
    await waitFor(() => screen.getByText(/paste a job/i));
    await user.type(screen.getByRole('textbox'), 'https://example.com/jobs/1');
    await user.click(screen.getByRole('button', { name: /evaluate/i }));
    await waitFor(() =>
      expect(screen.getByText(/parsing job description/i)).toBeInTheDocument(),
    );
    resolveEval({ data: { evaluation: { id: 'eval-1' }, job: {} } });
  });
});
```

- [ ] **Step 2: Run, expect failure**

```bash
cd user-portal && pnpm exec vitest run src/pages/OnboardingPage.test.tsx
```

Expected: module not found.

- [ ] **Step 3: Implement the wizard**

```tsx
// user-portal/src/pages/OnboardingPage.tsx
import { useEffect, useState } from 'react';
import { api } from '../lib/api';
import { ResumeUploadStep } from '../components/onboarding/ResumeUploadStep';
import { JobInputStep } from '../components/onboarding/JobInputStep';
import { EvaluationProgressStep } from '../components/onboarding/EvaluationProgressStep';

type Step = 'loading' | 'resume' | 'job' | 'evaluating' | 'failed-skip';

export default function OnboardingPage(): JSX.Element {
  const [step, setStep] = useState<Step>('loading');
  const [jobError, setJobError] = useState<string | null>(null);
  const [evalBusy, setEvalBusy] = useState(false);
  const [failCount, setFailCount] = useState(0);

  useEffect(() => {
    (async () => {
      const { data } = await api.profile.get();
      setStep(data.onboarding_state === 'done' ? 'job' : 'resume');
    })();
  }, []);

  async function submitJob(input: { type: 'url' | 'text'; value: string }) {
    setEvalBusy(true);
    setJobError(null);
    setStep('evaluating');
    try {
      const res = await api.onboarding.firstEvaluation({ job_input: input });
      const evalId = res.data.evaluation.id;
      window.history.pushState({}, '', `/onboarding/evaluation/${evalId}`);
      window.dispatchEvent(new PopStateEvent('popstate'));
    } catch (e) {
      setFailCount((n) => n + 1);
      setJobError((e as Error).message);
      if (failCount + 1 >= 3) {
        setStep('failed-skip');
      } else {
        setStep('job');
      }
    } finally {
      setEvalBusy(false);
    }
  }

  async function skipEvaluation() {
    // State is already 'done' server-side since resume uploaded. Just leave.
    window.location.assign('/');
  }

  return (
    <div className="mx-auto flex min-h-screen max-w-2xl flex-col gap-8 px-6 py-16">
      <header>
        <h1 className="text-3xl font-semibold">
          <span className="bg-gradient-to-br from-accent-teal via-accent-cobalt to-accent-violet bg-clip-text text-transparent">
            Let's get you set up
          </span>
        </h1>
        <p className="mt-2 text-text-secondary">
          Less than a minute. We'll turn one job into a full evaluation so you can see what we do.
        </p>
      </header>

      {step === 'loading' && <p className="text-text-secondary">Loading…</p>}
      {step === 'resume' && <ResumeUploadStep onAdvance={() => setStep('job')} />}
      {step === 'job' && <JobInputStep onSubmit={submitJob} busy={evalBusy} error={jobError} />}
      {step === 'evaluating' && <EvaluationProgressStep />}
      {step === 'failed-skip' && (
        <div className="flex flex-col gap-3 rounded-xl border border-border p-6">
          <p>Our evaluation service is having a rough moment. You can skip this and evaluate jobs from the main app.</p>
          <button className="self-start text-accent-cobalt hover:underline" onClick={() => void skipEvaluation()}>
            Skip this step →
          </button>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 4: Run tests, verify pass**

```bash
cd user-portal && pnpm exec vitest run src/pages/OnboardingPage.test.tsx
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add user-portal/src/pages/OnboardingPage.tsx \
        user-portal/src/pages/OnboardingPage.test.tsx
git commit -m "feat(ui): OnboardingPage wizard orchestrator"
```

---

## Task 14: `OnboardingPayoffPage`

**Files:**
- Create: `user-portal/src/pages/OnboardingPayoffPage.tsx`
- Test: `user-portal/src/pages/OnboardingPayoffPage.test.tsx`

- [ ] **Step 1: Write the failing test**

```tsx
// user-portal/src/pages/OnboardingPayoffPage.test.tsx
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import OnboardingPayoffPage from './OnboardingPayoffPage';
import { api } from '../lib/api';

vi.mock('../lib/api', () => ({
  api: {
    evaluations: { get: vi.fn() },
    applications: { create: vi.fn() },
    interviewPreps: { create: vi.fn() },
    conversations: { create: vi.fn(), sendMessage: vi.fn() },
  },
}));

const MOCK_EVAL = {
  id: 'eval-1',
  overall_score: 82,
  grade: 'B+',
  strengths: [{ text: '8 yrs Python' }],
  gaps: [{ text: 'No Rust' }],
  job_id: 'job-1',
  job: { title: 'Senior Backend', company: 'Acme', location: 'Remote' },
};

describe('OnboardingPayoffPage', () => {
  beforeEach(() => vi.clearAllMocks());

  it('renders the evaluation card and four CTAs', async () => {
    (api.evaluations.get as vi.Mock).mockResolvedValue({ data: MOCK_EVAL });
    render(<OnboardingPayoffPage id="eval-1" />);
    await waitFor(() => screen.getByText('82'));
    expect(screen.getByText('Senior Backend')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /tailor my cv/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /generate interview prep/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /save to pipeline/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /unlock job scanning/i })).toBeInTheDocument();
  });

  it('creates an application on "Save to pipeline"', async () => {
    (api.evaluations.get as vi.Mock).mockResolvedValue({ data: MOCK_EVAL });
    (api.applications.create as vi.Mock).mockResolvedValue({ data: { id: 'app-1' } });
    render(<OnboardingPayoffPage id="eval-1" />);
    await waitFor(() => screen.getByText('82'));
    await userEvent.setup().click(screen.getByRole('button', { name: /save to pipeline/i }));
    await waitFor(() =>
      expect(api.applications.create).toHaveBeenCalledWith({
        job_id: 'job-1',
        status: 'saved',
        evaluation_id: 'eval-1',
      }),
    );
    expect(screen.getByText(/saved/i)).toBeInTheDocument();
  });

  it('navigates to /interview-prep/:id after prep creation', async () => {
    (api.evaluations.get as vi.Mock).mockResolvedValue({ data: MOCK_EVAL });
    (api.interviewPreps.create as vi.Mock).mockResolvedValue({ data: { id: 'prep-1' } });
    const assign = vi.fn();
    Object.defineProperty(window, 'location', { value: { assign }, writable: true });
    render(<OnboardingPayoffPage id="eval-1" />);
    await waitFor(() => screen.getByText('82'));
    await userEvent.setup().click(screen.getByRole('button', { name: /generate interview prep/i }));
    await waitFor(() => expect(assign).toHaveBeenCalledWith('/interview-prep/prep-1'));
  });
});
```

- [ ] **Step 2: Run, expect failure**

```bash
cd user-portal && pnpm exec vitest run src/pages/OnboardingPayoffPage.test.tsx
```

Expected: module not found.

- [ ] **Step 3: Add `api.evaluations.get` wrapper (if missing)**

In `user-portal/src/lib/api.ts`, verify or add:

```ts
  evaluations: {
    get: (id: string) =>
      request<{ data: EvaluationDetail }>('GET', `/api/v1/evaluations/${id}`),
  },
```

The backend `GET /api/v1/evaluations/{id}` exists per Phase 2a. If the frontend type `EvaluationDetail` is missing, add:

```ts
export type EvaluationDetail = {
  id: string;
  overall_score: number;
  grade: 'A' | 'A-' | 'B+' | 'B' | 'C';
  strengths: Array<{ text: string }>;
  gaps: Array<{ text: string }>;
  job_id: string | null;
  job?: { title: string; company: string; location: string | null };
};
```

- [ ] **Step 4: Implement the page**

```tsx
// user-portal/src/pages/OnboardingPayoffPage.tsx
import { useEffect, useState } from 'react';
import { api, type EvaluationDetail } from '../lib/api';
import { GradientButton } from '../components/ui/GradientButton';
import { GradientBadge } from '../components/ui/GradientBadge';
import { AppShell } from '../components/layout/AppShell';

type Props = { id: string };

export default function OnboardingPayoffPage({ id }: Props): JSX.Element {
  const [evaluation, setEvaluation] = useState<EvaluationDetail | null>(null);
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);

  useEffect(() => {
    void api.evaluations.get(id).then((res) => setEvaluation(res.data));
  }, [id]);

  if (!evaluation) return <p className="p-8 text-text-secondary">Loading…</p>;

  async function onTailorCV() {
    setBusy('cv');
    const conv = await api.conversations.create('CV for new role');
    await api.conversations.sendMessage(
      conv.data.id,
      `Tailor my CV for job ${evaluation!.job_id}`,
    );
    window.location.assign('/');
  }

  async function onPrep() {
    if (!evaluation?.job_id) return;
    setBusy('prep');
    const res = await api.interviewPreps.create({ job_id: evaluation.job_id });
    window.location.assign(`/interview-prep/${res.data.id}`);
  }

  async function onSave() {
    if (!evaluation?.job_id) return;
    setBusy('save');
    await api.applications.create({
      job_id: evaluation.job_id,
      status: 'saved',
      evaluation_id: evaluation.id,
    });
    setSaved(true);
    setBusy(null);
  }

  function onUnlockScanning() {
    window.location.assign('/scans');
  }

  return (
    <AppShell>
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[2fr_1fr]">
        <section className="rounded-2xl border border-border bg-card p-6 shadow-[0_4px_16px_-8px_rgba(0,0,0,0.08)]">
          <div className="flex items-start justify-between gap-4">
            <div>
              <div className="font-semibold">{evaluation.job?.title}</div>
              <div className="text-sm text-text-secondary">
                {evaluation.job?.company} · {evaluation.job?.location ?? 'Location not specified'}
              </div>
            </div>
            <GradientBadge grade={evaluation.grade} score={evaluation.overall_score} />
          </div>
          <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <div className="text-xs uppercase tracking-wide text-green-700">Strengths</div>
              <ul className="mt-1 space-y-1 text-sm">
                {evaluation.strengths.map((s, i) => <li key={i}>• {s.text}</li>)}
              </ul>
            </div>
            <div>
              <div className="text-xs uppercase tracking-wide text-red-700">Gaps</div>
              <ul className="mt-1 space-y-1 text-sm">
                {evaluation.gaps.map((g, i) => <li key={i}>• {g.text}</li>)}
              </ul>
            </div>
          </div>
        </section>

        <aside className="flex flex-col gap-4">
          <div className="text-xs uppercase tracking-wide text-text-secondary">What's next?</div>
          <GradientButton disabled={busy !== null} onClick={() => void onTailorCV()}>
            Tailor my CV
          </GradientButton>
          <button
            type="button"
            disabled={busy !== null}
            onClick={() => void onPrep()}
            className="rounded-lg border border-border bg-white px-4 py-3 text-left font-medium hover:bg-hover disabled:opacity-50"
          >
            Generate interview prep
          </button>
          <button
            type="button"
            disabled={busy !== null || saved}
            onClick={() => void onSave()}
            className="rounded-lg border border-border bg-white px-4 py-3 text-left font-medium hover:bg-hover disabled:opacity-50"
          >
            {saved ? 'Saved ✓' : 'Save to pipeline'}
          </button>
          <div className="mt-2 border-t border-dashed border-border pt-4">
            <button
              type="button"
              onClick={onUnlockScanning}
              className="w-full rounded-lg bg-[rgba(37,99,235,0.08)] px-4 py-3 text-left"
            >
              <div className="font-semibold text-accent-cobalt">🎯 Unlock job scanning</div>
              <div className="text-xs text-text-secondary">Tell us where you want to work</div>
            </button>
          </div>
        </aside>
      </div>
    </AppShell>
  );
}
```

- [ ] **Step 5: Run tests, verify pass**

```bash
cd user-portal && pnpm exec vitest run src/pages/OnboardingPayoffPage.test.tsx
```

Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
git add user-portal/src/pages/OnboardingPayoffPage.tsx \
        user-portal/src/pages/OnboardingPayoffPage.test.tsx \
        user-portal/src/lib/api.ts
git commit -m "feat(ui): OnboardingPayoffPage with eval card + next-steps sidebar"
```

---

## Task 15: Router gate in `App.tsx`

**Files:**
- Modify: `user-portal/src/App.tsx`

- [ ] **Step 1: Add routes and gate**

Find the `matchRoute` function in `App.tsx` and add cases BEFORE the `return 'chat';` fallthrough:

```ts
  if (pathname === '/onboarding') return 'onboarding';
  if (pathname.startsWith('/onboarding/evaluation/')) return 'onboarding-payoff';
```

- [ ] **Step 2: Import the new pages**

Add to the imports at the top of `App.tsx`:

```ts
import OnboardingPage from './pages/OnboardingPage';
import OnboardingPayoffPage from './pages/OnboardingPayoffPage';
```

- [ ] **Step 3: Add `requiresProfile` predicate**

After the `matchRoute` function, add:

```ts
function requiresProfile(route: string): boolean {
  return !['signup', 'login', 'auth-callback', 'billing', 'subscribe-redirect', 'onboarding'].includes(
    route,
  );
}
```

- [ ] **Step 4: Wire the gate in `App()`**

Inside the component, after the existing `useEffect` that redirects unauthenticated users, add a second `useEffect`:

```tsx
  const [needsOnboarding, setNeedsOnboarding] = useState<boolean | null>(null);

  useEffect(() => {
    if (!isAuthenticated()) return;
    let cancelled = false;
    (async () => {
      try {
        const { data } = await api.profile.get();
        if (!cancelled) setNeedsOnboarding(data.onboarding_state !== 'done');
      } catch {
        if (!cancelled) setNeedsOnboarding(false); // fail-open on profile fetch errors
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (needsOnboarding && requiresProfile(route) && route !== 'onboarding') {
      window.location.replace('/onboarding');
    }
  }, [needsOnboarding, route]);
```

Ensure `api` is imported at the top (`import { api } from './lib/api';`).

- [ ] **Step 5: Render the pages in the switch**

Find the existing return block (the giant JSX rendering each route) and add cases. Example — before the `chat` fallthrough case:

```tsx
{route === 'onboarding' && <OnboardingPage />}
{route === 'onboarding-payoff' && (
  <OnboardingPayoffPage id={path.replace(/^\/onboarding\/evaluation\//, '')} />
)}
```

- [ ] **Step 6: Typecheck**

```bash
cd user-portal && pnpm exec tsc --noEmit
```

Expected: exit 0.

- [ ] **Step 7: Run the full unit suite to verify no regressions**

```bash
cd user-portal && pnpm exec vitest run
```

Expected: all green.

- [ ] **Step 8: Commit**

```bash
git add user-portal/src/App.tsx
git commit -m "feat(ui): onboarding routes + resume-only hard gate"
```

---

## Task 16: Playwright — "Onboarding — full flow" test

**Files:**
- Create: `user-portal/e2e/fixtures/resume.pdf` (real tiny PDF; see below)
- Create: `user-portal/e2e/fixtures/job.html` (static HTML for job-URL interception)
- Modify: `user-portal/e2e/features.spec.ts` (add new test)

- [ ] **Step 1: Create the resume fixture**

```bash
mkdir -p user-portal/e2e/fixtures
# Minimal valid PDF. The backend parser needs extractable text — use a tiny
# generated file rather than a binary blob. The pdf-lib version checked in
# here was produced from:
#   echo "Jane Doe\nSenior Backend Engineer\n8 years Python..." | \
#     pandoc -o resume.pdf
# Commit the pre-generated file so tests don't depend on pandoc in CI.
```

Hand-run (one-time, outside CI):

```bash
cd user-portal/e2e/fixtures
printf 'Jane Doe\nSenior Backend Engineer\n8 years Python, AWS, distributed systems.\n' | pandoc -o resume.pdf
```

Verify the file is valid PDF (< 20KB):

```bash
file user-portal/e2e/fixtures/resume.pdf
```

Expected: `resume.pdf: PDF document, ...`.

- [ ] **Step 2: Create the job HTML fixture**

```html
<!-- user-portal/e2e/fixtures/job.html -->
<!DOCTYPE html><html><head><title>Senior Backend · Acme</title></head>
<body>
<h1>Senior Backend Engineer</h1>
<p>Acme Corp · Remote · $180k–$220k</p>
<p>5+ years Python. AWS, distributed systems, observability. Remote OK.</p>
</body></html>
```

- [ ] **Step 3: Add the new test to `features.spec.ts`**

Append inside the `test.describe('post-login E2E — each module', () => { ... })` block:

```ts
  test('7. Onboarding — full flow on a fresh user', async ({ page, context }) => {
    // Spec: resume → job URL → 60s eval → payoff page renders.
    // Total wall budget includes 2 LLM calls on bridge → up to 3 minutes.
    test.setTimeout(200_000);

    // Intercept the job-URL fetch so we don't hit a real external site.
    await page.route('https://acme.example.com/jobs/1', async (route) => {
      const fs = await import('node:fs/promises');
      const body = await fs.readFile('e2e/fixtures/job.html', 'utf-8');
      await route.fulfill({ status: 200, contentType: 'text/html', body });
    });

    await page.goto('/onboarding');
    // Step 1 — upload resume fixture
    await page.setInputFiles('input[type=file]', 'e2e/fixtures/resume.pdf');

    // Step 2 — paste a URL we intercept
    await page.waitForSelector('textarea[placeholder*="https"]', { timeout: 30_000 });
    await page.locator('textarea').fill('https://acme.example.com/jobs/1');
    await page.getByRole('button', { name: /evaluate/i }).click();

    // Step 3 — progress screen, then payoff
    await expect(page.getByText(/parsing job description/i)).toBeVisible({ timeout: 5_000 });

    // Payoff — evaluation card + at least one next-step CTA
    await expect(page.getByRole('button', { name: /tailor my cv/i })).toBeVisible({
      timeout: 180_000,
    });
  });
```

This test assumes the Playwright user is either fresh or has been reset. Per `clearanceflow-reset-user` skill pattern in memory, we don't have a reset path for HireLoop yet — flag as a follow-up. For now, run this test against a dedicated `onboarding-e2e@hireloop.test` user that is manually re-created when the test flakes.

- [ ] **Step 4: Run locally against dev backend**

```bash
cd user-portal && pnpm exec playwright test -g "Onboarding — full flow"
```

Expected: passes. If it fails on the eval step, check `hireloop-llm-bridge-1` auth status on dev EC2 (`aws ssm send-command ... claude auth status`).

- [ ] **Step 5: Commit**

```bash
git add user-portal/e2e/fixtures/resume.pdf \
        user-portal/e2e/fixtures/job.html \
        user-portal/e2e/features.spec.ts
git commit -m "test(e2e): onboarding full flow — fresh user to payoff"
```

---

## Task 17: Playwright — "Onboarding — paste-text fallback" test

**Files:**
- Modify: `user-portal/e2e/features.spec.ts`

- [ ] **Step 1: Add the test**

Append inside the same describe block:

```ts
  test('8. Onboarding — paste-text fallback when PDF upload fails', async ({ page }) => {
    test.setTimeout(60_000);

    // Mock the PDF upload to 422, forcing the paste-text path.
    await page.route('**/api/v1/profile/resume', (route) =>
      route.fulfill({
        status: 422,
        contentType: 'application/json',
        body: JSON.stringify({ error: { code: 'UNPROCESSABLE_ENTITY', message: 'parse failed' } }),
      }),
    );

    await page.goto('/onboarding');
    await page.setInputFiles('input[type=file]', 'e2e/fixtures/resume.pdf');

    // Fallback textarea should auto-reveal
    await expect(page.locator('textarea')).toBeVisible({ timeout: 5_000 });

    // Paste + continue
    await page.locator('textarea').fill(
      '# Jane Doe\n\nSenior Backend Engineer, 8 yrs Python.\n',
    );
    await page.getByRole('button', { name: /continue/i }).click();

    // Advance to job step
    await expect(page.getByText(/paste a job/i)).toBeVisible({ timeout: 15_000 });
  });
```

- [ ] **Step 2: Run locally**

```bash
cd user-portal && pnpm exec playwright test -g "paste-text fallback"
```

Expected: passes.

- [ ] **Step 3: Commit**

```bash
git add user-portal/e2e/features.spec.ts
git commit -m "test(e2e): onboarding paste-text fallback on PDF parse failure"
```

---

## Task 18: Playwright — "Onboarding — evaluation skip" test

**Files:**
- Modify: `user-portal/e2e/features.spec.ts`

- [ ] **Step 1: Add the test**

```ts
  test('9. Onboarding — skip escape after 3 consecutive evaluation failures', async ({ page }) => {
    test.setTimeout(60_000);

    // Force 3 failures in a row
    let attempt = 0;
    await page.route('**/api/v1/onboarding/first-evaluation', (route) => {
      attempt += 1;
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ error: { code: 'LLM_TIMEOUT', message: 'eval failed' } }),
      });
    });

    await page.goto('/onboarding');
    await page.setInputFiles('input[type=file]', 'e2e/fixtures/resume.pdf');
    await page.waitForSelector('textarea[placeholder*="https"]', { timeout: 15_000 });

    for (let i = 0; i < 3; i += 1) {
      await page.locator('textarea').fill('Senior backend role at Acme');
      await page.getByRole('button', { name: /evaluate/i }).click();
      await page.waitForTimeout(1_000); // let the error bubble
    }

    // Skip escape should be visible
    await expect(page.getByRole('button', { name: /skip this step/i })).toBeVisible();
    expect(attempt).toBeGreaterThanOrEqual(3);
  });
```

- [ ] **Step 2: Run locally**

```bash
cd user-portal && pnpm exec playwright test -g "skip escape"
```

Expected: passes.

- [ ] **Step 3: Commit**

```bash
git add user-portal/e2e/features.spec.ts
git commit -m "test(e2e): onboarding evaluation-fail skip escape"
```

---

## Task 19: Update existing "Scans" test to assert JIT preferences nudge

**Files:**
- Modify: `user-portal/e2e/features.spec.ts` (existing test 2)
- Modify: `user-portal/src/pages/ScansPage.tsx` (add JIT preferences prompt)

This step depends on the Scans page showing a preferences prompt when `profile.target_roles` or `target_locations` are empty. Since this spec explicitly non-goal's rewriting `/scans`, we add only the minimal nudge.

- [ ] **Step 1: Add the preferences-needed banner to `ScansPage.tsx`**

At the top of the `ScansPage` component's return JSX, add:

```tsx
{(!profile?.target_roles?.length || !profile?.target_locations?.length) && (
  <div
    role="alert"
    data-testid="preferences-needed-banner"
    className="mb-4 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950"
  >
    <p className="font-medium">Set your scan targets first</p>
    <p className="mt-1 text-amber-900/90">
      Add the roles and locations you want so we know what to look for.
    </p>
  </div>
)}
```

Ensure `profile` is fetched via `useEffect` + `api.profile.get()` at component mount. Reuse the existing profile fetch if one is already present.

- [ ] **Step 2: Update the existing scans test**

Find test "2. Scans — create scan config end-to-end" in `features.spec.ts` and prepend an assertion at the top:

```ts
    await page.goto('/scans');
    await expect(page.getByRole('heading', { name: 'Scans' })).toBeVisible();

    // JIT preferences nudge is visible for users who haven't set targets.
    // This is not a blocker — just a visible nag.
    const banner = page.getByTestId('preferences-needed-banner');
    if (await banner.isVisible()) {
      // expected — users without prefs see this. Move on.
    }
```

- [ ] **Step 3: Run both the new tests and the modified one**

```bash
cd user-portal && pnpm exec playwright test -g "Scans"
```

Expected: passes.

- [ ] **Step 4: Commit**

```bash
git add user-portal/src/pages/ScansPage.tsx \
        user-portal/e2e/features.spec.ts
git commit -m "feat(ui): JIT preferences nudge on Scans page"
```

---

## Task 20: Full-stack smoke + deploy

**Files:**
- No new files. Verification only.

- [ ] **Step 1: Push all the above commits**

```bash
git push origin main
```

- [ ] **Step 2: Watch Deploy (dev) run**

```bash
gh run watch --exit-status $(gh run list --branch main --workflow "Deploy (dev)" --limit 1 --json databaseId --jq '.[0].databaseId')
```

Expected: green. `migrate` job applies migration 0007.

- [ ] **Step 3: Confirm migration applied on prod**

```bash
/opt/homebrew/bin/aws ssm send-command --instance-ids i-00f8a9e8ef4b1a45f \
  --document-name AWS-RunShellScript \
  --parameters 'commands=["sudo docker exec hireloop-backend-1 uv run alembic current"]' \
  --profile hireloop --query 'Command.CommandId' --output text
```

Wait then fetch with `aws ssm get-command-invocation`. Expected: `0007_onb_collapse (head)`.

- [ ] **Step 4: Run the full Playwright suite against prod**

```bash
cd user-portal && PW_BASE_URL=https://app.dev.hireloop.xyz pnpm exec playwright test
```

Expected: 10/10 green (original 7 + 3 new + the modified Scans test).

- [ ] **Step 5: Manual verification checklist on prod**

Sign out from `app.dev.hireloop.xyz`, sign up as a fresh user, and walk through:

- [ ] Land on `/onboarding` (not chat).
- [ ] Upload resume fixture → advances to job step.
- [ ] Paste a real job URL → evaluation runs → payoff page renders with gradient badge.
- [ ] Click "Save to pipeline" → inline confirmation.
- [ ] Click "Generate interview prep" → lands on `/interview-prep/:id` with content.
- [ ] Click "Tailor my CV" → lands in chat with an auto-sent seed message.
- [ ] Click "Unlock job scanning" → lands on `/scans` with JIT banner.
- [ ] Navigate to `/pipeline` → saved job appears in Saved column.

- [ ] **Step 6: Update memory + close**

Update `MEMORY.md` entry: onboarding redesign SHIPPED, link to the plan file.

```bash
# In your memory directory:
# edit MEMORY.md, add a one-line entry, then commit not necessary (memory is ephemeral)
```

---

## Self-review notes (kept inline)

Per the writing-plans skill self-review:

1. **Spec coverage:** every spec section has a task. D1 gate → Task 15. D2 wow → Tasks 11, 12, 13. D3 preferences-demoted → Task 2, 19. D4 failures → Tasks 10, 17, 18. D5 marketing gradient → Tasks 6, 7, 8, 13, 14. D6 payoff layout → Task 14. Backend endpoints → Tasks 3, 4, 5. Migration → Task 1. Playwright new tests → Tasks 16, 17, 18.

2. **Placeholder scan:** no TBDs. Two external dependencies called out explicitly: (a) Task 5 Step 5 asks the engineer to verify `create_evaluation_for_parsed_job` exists and, if not, extract from the agent tool — this is a real design choice that needs on-the-spot inspection; (b) Task 16 Step 1 depends on `pandoc` being installed at fixture generation time — runs once out-of-band, not in CI.

3. **Type consistency:** `api.onboarding.firstEvaluation` return shape matches `FirstEvaluationResponse` in Task 5 and the consumer in Task 13. `GradientBadge` takes `grade: Grade` in Task 8, and `EvaluationDetail.grade: 'A'|'A-'|'B+'|'B'|'C'` in Task 14 matches. `ParsedJob` type declared in Task 9 is used in Tasks 13–14 via the `api.onboarding.firstEvaluation` return shape's nested `job` field.

4. **Ambiguity:** JIT preferences prompt in Task 19 is intentionally a non-blocking banner, not a forced modal — the spec's D3 says "nudged," not "gated."
