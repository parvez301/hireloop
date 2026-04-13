# CareerAgent Phase 2d — Interview Prep + Negotiation + Feedback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the final two feature modules (Interview Prep + Negotiation) from the parent spec's 6-module roster, plus a generic feedback loop telemetering all 4 LLM-generated artifacts, plus the `star_stories` CRUD API missing since Phase 1. After this phase, the agent has its full 6-tool set and `NOT_YET_AVAILABLE_TEMPLATES` is empty.

**Architecture:** Two new backend core modules (`core/interview_prep/`, `core/negotiation/`) following the Phase 2a pattern (extractor/generator + service orchestrator + Claude prompt caching). One cross-cutting `core/feedback/` service with per-resource ownership validators dispatched by `resource_type`. Frontend gets 5 new pages, 9 new components, and a shared `FeedbackWidget` mounted on 4 existing cards and 2 new detail pages. Migration `0006` creates 3 tables and adds the `applications.negotiation_id` FK that Phase 2c deferred.

**Tech Stack:** Python 3.12 + FastAPI + SQLAlchemy 2.0 async + Alembic + anthropic SDK (direct, for prompt caching) + pytest + respx. React 18 + Vite + TypeScript 5 + Tailwind. No new runtime dependencies.

**Reference spec:** [`docs/superpowers/specs/2026-04-11-phase2d-interview-prep-negotiation-feedback-design.md`](../specs/2026-04-11-phase2d-interview-prep-negotiation-feedback-design.md) — **read it first**. This plan operationalizes that spec; the spec is the source of truth for any ambiguity.

**Parent spec:** [`docs/superpowers/specs/2026-04-10-careeragent-design.md`](../specs/2026-04-10-careeragent-design.md) — especially Appendix D.6 (interview prep Claude prompt), Appendix D.7 (negotiation playbook Claude prompt), Appendix G (card payload schemas).

**Phase 2d scope (what's IN):**

- Migration `0006_phase2d_interview_prep_negotiation_feedback` — 3 new tables (`interview_preps`, `negotiations`, `feedback`) + FK constraint on `applications.negotiation_id`
- `core/interview_prep/` — extractor (resume → STAR stories) + generator (role → questions) + service orchestrator
- `core/negotiation/` — playbook generator (Claude via Appendix D.7) + service orchestrator
- `core/feedback/` — generic write-path with 4 ownership validators
- New API routers: `/interview-preps`, `/negotiations`, `/star-stories`, plus feedback sub-routes on `/evaluations/:id/feedback`, `/cv-outputs/:id/feedback`, `/interview-preps/:id/feedback`, `/negotiations/:id/feedback`
- Agent tool additions: `build_interview_prep_tool`, `generate_negotiation_playbook_tool`, graph dispatch updates, prompt updates. `NOT_YET_AVAILABLE_TEMPLATES` becomes `{}`
- Star stories CRUD API (Phase 1 backfill — table exists, API didn't)
- Full frontend: InterviewPrepListPage, InterviewPrepDetailPage, StoryBankPage, NegotiationListPage, NegotiationDetailPage, OfferForm modal, InterviewPrepCard + NegotiationCard chat cards, shared FeedbackWidget mounted on 4 cards + 2 detail pages
- `applications.negotiation_id` auto-linking from the negotiation service
- ~18 new backend tests + ~9 new frontend tests

**Phase 2d scope (what's OUT):**

- Multi-round negotiation chaining (link new negotiation to previous one with context) — Phase 5
- Interview prep / negotiation PDF export — Phase 5
- Mock interview chat mode (multi-turn Q&A with Claude playing interviewer) — Phase 5
- Calendar integration, scheduled interview reminders
- Admin feedback review UI — Phase 5
- Live compensation data API (levels.fyi, Glassdoor) — Phase 5 if needed
- `POST /conversations/:id/actions` card action routing — Phase 5
- Voice/video coaching

### Implementation notes (gaps addressed, 2026-04-11)

1. **Preflight baselines** — Re-run Task 1 commands before each milestone; expected backend test count is **~133** and frontend **16** as of Phase 2c completion (update the “Expected:” lines if these drift).
2. **Feedback API routing (single pattern)** — All feedback posts hit **`FeedbackService`** from thin handlers. Implement **`POST /evaluations/:id/feedback`** and **`POST /cv-outputs/:id/feedback`** as **new routes on the existing `evaluations` and `cv_outputs` routers**; implement **`POST /interview-preps/:id/feedback`** and **`POST /negotiations/:id/feedback`** on those routers. **Do not** add a second duplicate path via a standalone router for the same action. Optional: `api/feedback.py` only if it re-exports shared dependency wiring—not parallel URL trees.
3. **Story bank concurrency (`ensure_story_bank`)** — Run extraction inside a **single DB transaction**: `SELECT count(*) FROM star_stories WHERE user_id = ? FOR UPDATE` on the user row (or equivalent **advisory lock** / serializable transaction). If count is 0 after lock, run extractor and insert; else commit and return. Prevents duplicate AI extractions when two interview-prep requests race.
4. **Classifier + tools checkpoint (Task 19)** — After wiring tools, verify **Gemini intent labels** (`INTERVIEW_PREP`, `NEGOTIATE`) match **`tool_manifest` / `route_node` tool names** (`build_interview_prep`, `generate_negotiation_playbook`) exactly—same class of bug as Phase 2c stub collisions.

### Git note

The project directory was not a git repo at the time prior plans were written. Every task ends with a **Checkpoint** step. If you have initialized git, run `git add` + `git commit`. If not, treat the checkpoint as a pause point to review what you built.

### Execution order and mergeability

Tasks are ordered so each one leaves the system in a working state. T1–T5 establish shared primitives (deps check, migration, models, schemas, feedback service scaffold). T6–T11 deliver the Interview Prep module end-to-end. T12–T16 deliver the Negotiation module. T17 delivers the Star Stories CRUD backfill. T18 delivers the feedback endpoints on existing Phase 2a resources. T19 wires both new tools into the agent. T20–T25 deliver the frontend in slices (API client, FeedbackWidget, story bank, interview prep pages, negotiation pages + OfferForm, chat cards). T26 covers frontend tests. T27 is an end-to-end smoke test. T28 is final verification.

You should be able to run `pytest backend/tests/` successfully after every task from T4 onward.

### Existing baseline (as of Phase 2c completion)

- **Backend:** ~133 tests passing (re-verify in Task 1), mypy strict clean, ruff clean, black clean
- **Frontend:** 16 tests passing (re-verify in Task 1), tsc clean
- **pdf-render:** 4 tests passing
- **Agent tool count:** 4 (evaluate_job, optimize_cv, start_job_scan, start_batch_evaluation)
- **`NOT_YET_AVAILABLE_TEMPLATES`** contains: `INTERVIEW_PREP`, `NEGOTIATE`. Will be empty after T19.

---

## File Structure Plan

```
career-agent/
├── backend/
│   ├── migrations/versions/
│   │   └── 0006_phase2d_interview_prep_negotiation_feedback.py  [CREATE T2]
│   ├── src/career_agent/
│   │   ├── main.py                                                [MODIFY T11, T16, T17, T18]
│   │   ├── models/
│   │   │   ├── interview_prep.py                                  [CREATE T3]
│   │   │   ├── negotiation.py                                     [CREATE T3]
│   │   │   ├── feedback.py                                        [CREATE T3]
│   │   │   └── __init__.py                                        [MODIFY T3]
│   │   ├── schemas/
│   │   │   ├── interview_prep.py                                  [CREATE T4]
│   │   │   ├── negotiation.py                                     [CREATE T4]
│   │   │   ├── star_story.py                                      [CREATE T4]
│   │   │   └── feedback.py                                        [CREATE T4]
│   │   ├── core/
│   │   │   ├── interview_prep/
│   │   │   │   ├── __init__.py                                    [CREATE T6]
│   │   │   │   ├── extractor.py                                   [CREATE T6]
│   │   │   │   ├── generator.py                                   [CREATE T7]
│   │   │   │   └── service.py                                     [CREATE T8]
│   │   │   ├── negotiation/
│   │   │   │   ├── __init__.py                                    [CREATE T12]
│   │   │   │   ├── playbook.py                                    [CREATE T12]
│   │   │   │   └── service.py                                     [CREATE T13]
│   │   │   ├── feedback/
│   │   │   │   ├── __init__.py                                    [CREATE T5]
│   │   │   │   └── service.py                                     [CREATE T5]
│   │   │   └── agent/
│   │   │       ├── tools.py                                       [MODIFY T19]
│   │   │       ├── graph.py                                       [MODIFY T19]
│   │   │       └── prompts.py                                     [MODIFY T19]
│   │   ├── services/
│   │   │   ├── interview_prep.py                                  [CREATE T9]
│   │   │   ├── negotiation.py                                     [CREATE T14]
│   │   │   └── star_story.py                                      [CREATE T17]
│   │   └── api/
│   │       ├── interview_preps.py                                 [CREATE T10, T11]
│   │       ├── negotiations.py                                    [CREATE T15, T16]
│   │       ├── star_stories.py                                    [CREATE T17]
│   │       ├── feedback.py                                        [CREATE T18]
│   │       ├── evaluations.py                                     [MODIFY T18 — +feedback endpoint]
│   │       └── cv_outputs.py                                      [MODIFY T18 — +feedback endpoint]
│   └── tests/
│       ├── unit/
│       │   ├── test_interview_prep_extractor_prompt.py            [CREATE T6]
│       │   ├── test_interview_prep_generator_prompt.py            [CREATE T7]
│       │   ├── test_negotiation_playbook_prompt.py                [CREATE T12]
│       │   └── test_feedback_service_validators.py                [CREATE T5]
│       └── integration/
│           ├── test_interview_prep_auto_populates_story_bank.py   [CREATE T8]
│           ├── test_interview_prep_custom_role.py                 [CREATE T8]
│           ├── test_interview_prep_job_id_mode.py                 [CREATE T9]
│           ├── test_interview_prep_regenerate.py                  [CREATE T11]
│           ├── test_interview_prep_paywalled.py                   [CREATE T11]
│           ├── test_negotiation_requires_offer_details.py         [CREATE T15]
│           ├── test_negotiation_full_playbook.py                  [CREATE T14]
│           ├── test_negotiation_regenerate.py                     [CREATE T16]
│           ├── test_negotiation_paywalled.py                      [CREATE T16]
│           ├── test_star_stories_crud.py                          [CREATE T17]
│           ├── test_star_stories_not_paywalled.py                 [CREATE T17]
│           ├── test_feedback_evaluation.py                        [CREATE T18]
│           ├── test_feedback_cv_output.py                         [CREATE T18]
│           ├── test_feedback_interview_prep.py                    [CREATE T18]
│           ├── test_feedback_negotiation.py                       [CREATE T18]
│           ├── test_feedback_ownership_cross_user.py              [CREATE T18]
│           ├── test_agent_interview_prep_tool.py                  [CREATE T19]
│           ├── test_agent_negotiation_tool_requires_offer.py      [CREATE T19]
│           └── test_phase2d_smoke.py                              [CREATE T27]
│
├── user-portal/
│   ├── src/
│   │   ├── App.tsx                                                [MODIFY T23]
│   │   ├── components/layout/AppShell.tsx                         [MODIFY T23]
│   │   ├── lib/api.ts                                             [MODIFY T20]
│   │   ├── components/
│   │   │   ├── shared/
│   │   │   │   └── FeedbackWidget.tsx                             [CREATE T21]
│   │   │   ├── interview-prep/
│   │   │   │   ├── StarStoryCard.tsx                              [CREATE T22]
│   │   │   │   ├── StarStoryEditor.tsx                            [CREATE T22]
│   │   │   │   └── QuestionListItem.tsx                           [CREATE T23]
│   │   │   ├── negotiation/
│   │   │   │   ├── OfferForm.tsx                                  [CREATE T24]
│   │   │   │   ├── MarketRangeChart.tsx                           [CREATE T24]
│   │   │   │   └── ScriptBlock.tsx                                [CREATE T24]
│   │   │   ├── chat/cards/
│   │   │   │   ├── InterviewPrepCard.tsx                          [CREATE T25]
│   │   │   │   ├── NegotiationCard.tsx                            [CREATE T25]
│   │   │   │   ├── EvaluationCard.tsx                             [MODIFY T21 — add FeedbackWidget]
│   │   │   │   └── CvOutputCard.tsx                               [MODIFY T21 — add FeedbackWidget]
│   │   │   └── chat/MessageList.tsx                               [MODIFY T25]
│   │   └── pages/
│   │       ├── StoryBankPage.tsx                                  [CREATE T22]
│   │       ├── InterviewPrepListPage.tsx                          [CREATE T23]
│   │       ├── InterviewPrepDetailPage.tsx                        [CREATE T23]
│   │       ├── NegotiationListPage.tsx                            [CREATE T24]
│   │       └── NegotiationDetailPage.tsx                          [CREATE T24]
│   └── src/                                                       [test files in T26]
│       ├── components/shared/FeedbackWidget.test.tsx              [CREATE T26]
│       ├── components/chat/cards/InterviewPrepCard.test.tsx       [CREATE T26]
│       ├── components/chat/cards/NegotiationCard.test.tsx         [CREATE T26]
│       ├── components/negotiation/OfferForm.test.tsx              [CREATE T26]
│       └── pages/
│           ├── StoryBankPage.test.tsx                             [CREATE T26]
│           ├── InterviewPrepDetailPage.test.tsx                   [CREATE T26]
│           └── NegotiationDetailPage.test.tsx                     [CREATE T26]
│
└── docs/superpowers/plans/
    └── 2026-04-11-phase2d-interview-prep-negotiation-feedback.md  [THIS FILE]
```

---

## Task 1: Preflight — Baseline Verification

**Files:** None — this task only runs checks to confirm you're starting from a clean Phase 2c baseline.

- [ ] **Step 1: Run the full backend suite**

```bash
cd backend
uv run pytest tests/ 2>&1 | tail -5
```

Expected: `133 passed, 3 warnings` (Phase 2c baseline).

- [ ] **Step 2: Lint + format + type check**

```bash
uv run ruff check src/ 2>&1 | tail -3
uv run black --check src/ 2>&1 | tail -3
uv run mypy src/ 2>&1 | tail -3
```

Expected: `All checks passed!`, `119 files would be left unchanged`, `Success: no issues found in 119 source files`.

- [ ] **Step 3: Frontend baseline**

```bash
cd ../user-portal
./node_modules/.bin/vitest run 2>&1 | tail -5
./node_modules/.bin/tsc --noEmit 2>&1 | tail -3
```

Expected: `16 tests passed`, no type errors.

- [ ] **Step 4: Verify Phase 2c deliverables are on disk**

```bash
cd ..
ls backend/src/career_agent/core/scanner/adapters/ | grep -E "greenhouse|ashby|lever" | wc -l
ls backend/src/career_agent/core/batch/ | grep -E "l0_filter|l1_triage|l2_evaluate|funnel|service" | wc -l
ls backend/src/career_agent/inngest/ | grep -E "scan_boards|batch_evaluate|client|functions" | wc -l
```

Expected: `3`, `5`, `4` (three adapters, five batch files, four inngest files).

- [ ] **Step 5: Verify the `NOT_YET_AVAILABLE_TEMPLATES` dict currently contains exactly `INTERVIEW_PREP` and `NEGOTIATE`**

```bash
grep -A 15 "NOT_YET_AVAILABLE_TEMPLATES" backend/src/career_agent/core/agent/prompts.py
```

Expected: the dict contains entries for `INTERVIEW_PREP` and `NEGOTIATE` and nothing else. If it has other keys, Phase 2c didn't finish cleanly — stop and investigate.

- [ ] **Step 6: Verify `applications.negotiation_id` column exists as nullable without FK**

Start the backend + docker-compose if not already running, then from `backend/`:

```bash
uv run python -c "
import asyncio
from career_agent.db import get_engine
from sqlalchemy import text

async def main():
    async with get_engine().connect() as conn:
        result = await conn.execute(text('''
            SELECT column_name, is_nullable, data_type
            FROM information_schema.columns
            WHERE table_name = 'applications' AND column_name = 'negotiation_id'
        '''))
        for row in result:
            print(row)

asyncio.run(main())
" 2>&1
```

Expected: one row showing `negotiation_id | YES | uuid`.

Also verify no FK constraint yet:

```bash
uv run python -c "
import asyncio
from career_agent.db import get_engine
from sqlalchemy import text

async def main():
    async with get_engine().connect() as conn:
        result = await conn.execute(text('''
            SELECT constraint_name FROM information_schema.table_constraints
            WHERE table_name = 'applications' AND constraint_type = 'FOREIGN KEY'
                AND constraint_name LIKE '%negotiation%'
        '''))
        rows = list(result)
        print('FK constraint count:', len(rows))
        for row in rows:
            print(row)

asyncio.run(main())
" 2>&1
```

Expected: `FK constraint count: 0`.

- [ ] **Step 7: Checkpoint**

Checkpoint message: `chore(phase2d): preflight verified — Phase 2c baseline clean`

---

## Task 2: Alembic Migration 0006

**Files:**
- Create: `backend/migrations/versions/0006_phase2d_interview_prep_negotiation_feedback.py`

- [ ] **Step 1: Create the migration file**

```python
"""phase2d_interview_prep_negotiation_feedback

Revision ID: 0006_phase2d
Revises: 0005_phase2c
Create Date: 2026-04-11

Adds interview_preps, negotiations, feedback tables + the FK constraint
on applications.negotiation_id (column was added nullable without FK in
Phase 2c migration 0005).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006_phase2d"
down_revision: Union[str, None] = "0005_phase2c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ---------- interview_preps ----------
    op.create_table(
        "interview_preps",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("custom_role", sa.String(255), nullable=True),
        sa.Column(
            "questions",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "red_flag_questions",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("model_used", sa.String(64), nullable=False),
        sa.Column("tokens_used", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "(job_id IS NOT NULL) OR (custom_role IS NOT NULL)",
            name="ck_interview_preps_job_or_role",
        ),
    )
    op.create_index("idx_interview_preps_user_id", "interview_preps", ["user_id"])
    op.create_index(
        "idx_interview_preps_user_created",
        "interview_preps",
        ["user_id", sa.text("created_at DESC")],
    )

    # ---------- negotiations ----------
    op.create_table(
        "negotiations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "offer_details",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "market_research",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "counter_offer",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "scripts",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("model_used", sa.String(64), nullable=False),
        sa.Column("tokens_used", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_negotiations_user_id", "negotiations", ["user_id"])
    op.create_index(
        "idx_negotiations_user_created",
        "negotiations",
        ["user_id", sa.text("created_at DESC")],
    )
    op.create_index("idx_negotiations_job_id", "negotiations", ["job_id"])

    # ---------- feedback ----------
    op.create_table(
        "feedback",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("resource_type", sa.String(32), nullable=False),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("correction_notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "rating >= 1 AND rating <= 5", name="ck_feedback_rating_range"
        ),
        sa.UniqueConstraint(
            "user_id",
            "resource_type",
            "resource_id",
            name="uq_feedback_user_resource",
        ),
    )
    op.create_index("idx_feedback_user_id", "feedback", ["user_id"])
    op.create_index(
        "idx_feedback_resource",
        "feedback",
        ["resource_type", "resource_id"],
    )
    op.create_index(
        "idx_feedback_created", "feedback", [sa.text("created_at DESC")]
    )

    # ---------- applications.negotiation_id FK ----------
    op.create_foreign_key(
        "fk_applications_negotiation_id",
        "applications",
        "negotiations",
        ["negotiation_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_applications_negotiation_id", "applications", type_="foreignkey"
    )

    op.drop_index("idx_feedback_created", table_name="feedback")
    op.drop_index("idx_feedback_resource", table_name="feedback")
    op.drop_index("idx_feedback_user_id", table_name="feedback")
    op.drop_table("feedback")

    op.drop_index("idx_negotiations_job_id", table_name="negotiations")
    op.drop_index("idx_negotiations_user_created", table_name="negotiations")
    op.drop_index("idx_negotiations_user_id", table_name="negotiations")
    op.drop_table("negotiations")

    op.drop_index("idx_interview_preps_user_created", table_name="interview_preps")
    op.drop_index("idx_interview_preps_user_id", table_name="interview_preps")
    op.drop_table("interview_preps")
```

- [ ] **Step 2: Run migration up / down / up round-trip**

Use the same env var incantation from prior plans (required because alembic loads Settings which needs all env vars):

```bash
cd backend
ENVIRONMENT=test \
COGNITO_USER_POOL_ID=us-east-1_test COGNITO_CLIENT_ID=testclient \
COGNITO_REGION=us-east-1 COGNITO_JWKS_URL=http://localhost/jwks \
ANTHROPIC_API_KEY=test GOOGLE_API_KEY=test \
CORS_ORIGINS=http://localhost:5173 \
DATABASE_URL=postgresql+asyncpg://$(whoami)@localhost:5432/career_agent \
REDIS_URL=redis://localhost:6379/0 APP_URL=http://localhost:5173 \
STRIPE_SECRET_KEY=sk_test STRIPE_WEBHOOK_SECRET=whsec \
STRIPE_PRICE_PRO_MONTHLY=price_test \
uv run alembic upgrade head
```

Then down then up again (copy the env var prefix). Expected each: `Running upgrade/downgrade 0005_phase2c <-> 0006_phase2d`.

- [ ] **Step 3: Checkpoint**

Checkpoint message: `feat(db): add Phase 2d tables (interview_preps, negotiations, feedback) + applications.negotiation_id FK`

---

## Task 3: SQLAlchemy Models for Phase 2d

**Files:**
- Create: `backend/src/career_agent/models/interview_prep.py`
- Create: `backend/src/career_agent/models/negotiation.py`
- Create: `backend/src/career_agent/models/feedback.py`
- Modify: `backend/src/career_agent/models/__init__.py`

- [ ] **Step 1: Create `backend/src/career_agent/models/interview_prep.py`**

```python
"""InterviewPrep — per-user, per-job or per-custom-role prep session."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from career_agent.models.base import Base


class InterviewPrep(Base):
    __tablename__ = "interview_preps"
    __table_args__ = (
        CheckConstraint(
            "(job_id IS NOT NULL) OR (custom_role IS NOT NULL)",
            name="ck_interview_preps_job_or_role",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    job_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="SET NULL"),
        nullable=True,
    )
    custom_role: Mapped[str | None] = mapped_column(String(255), nullable=True)
    questions: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    red_flag_questions: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSONB, nullable=True
    )
    model_used: Mapped[str] = mapped_column(String(64), nullable=False)
    tokens_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
```

- [ ] **Step 2: Create `backend/src/career_agent/models/negotiation.py`**

```python
"""Negotiation — per-user, per-job offer playbook."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from career_agent.models.base import Base


class Negotiation(Base):
    __tablename__ = "negotiations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    offer_details: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    market_research: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    counter_offer: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    scripts: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    model_used: Mapped[str] = mapped_column(String(64), nullable=False)
    tokens_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
```

- [ ] **Step 3: Create `backend/src/career_agent/models/feedback.py`**

```python
"""Feedback — polymorphic rating + notes for LLM-generated artifacts.

resource_type discriminates between 'evaluation', 'cv_output', 'interview_prep',
'negotiation'. No FK on resource_id because it's polymorphic; ownership is
validated in the service layer via per-resource-type validators.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from career_agent.models.base import Base


class Feedback(Base):
    __tablename__ = "feedback"
    __table_args__ = (
        CheckConstraint("rating >= 1 AND rating <= 5", name="ck_feedback_rating_range"),
        UniqueConstraint(
            "user_id", "resource_type", "resource_id",
            name="uq_feedback_user_resource",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    resource_type: Mapped[str] = mapped_column(String(32), nullable=False)
    resource_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    correction_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
```

- [ ] **Step 4: Update `backend/src/career_agent/models/__init__.py`**

Append the three new imports (preserve existing ones):

```python
from career_agent.models.interview_prep import InterviewPrep  # noqa: F401
from career_agent.models.negotiation import Negotiation  # noqa: F401
from career_agent.models.feedback import Feedback  # noqa: F401
```

- [ ] **Step 5: Verify imports**

```bash
uv run python -c "from career_agent.models import InterviewPrep, Negotiation, Feedback; print('ok')"
```

Expected: `ok`

- [ ] **Step 6: Run full suite**

```bash
uv run pytest tests/ 2>&1 | tail -3
```

Expected: `133 passed` (no regressions; no new tests yet).

- [ ] **Step 7: Checkpoint**

Checkpoint message: `feat(models): add Phase 2d SQLAlchemy models`

---

## Task 4: Pydantic Schemas for Phase 2d

**Files:**
- Create: `backend/src/career_agent/schemas/interview_prep.py`
- Create: `backend/src/career_agent/schemas/negotiation.py`
- Create: `backend/src/career_agent/schemas/star_story.py`
- Create: `backend/src/career_agent/schemas/feedback.py`

- [ ] **Step 1: Create `backend/src/career_agent/schemas/interview_prep.py`**

```python
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator


class InterviewPrepCreate(BaseModel):
    job_id: UUID | None = None
    custom_role: str | None = None

    @model_validator(mode="after")
    def _exactly_one(self) -> "InterviewPrepCreate":
        if bool(self.job_id) == bool(self.custom_role):
            raise ValueError("Provide exactly one of job_id or custom_role")
        return self


class InterviewPrepRegenerate(BaseModel):
    feedback: str | None = None


class InterviewPrepQuestion(BaseModel):
    question: str
    category: str
    suggested_story_title: str | None = None
    framework: str | None = None


class InterviewPrepRedFlagQuestion(BaseModel):
    question: str
    what_to_listen_for: str | None = None


class InterviewPrepOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    job_id: UUID | None
    custom_role: str | None
    questions: list[dict[str, Any]]
    red_flag_questions: list[dict[str, Any]] | None
    model_used: str
    tokens_used: int | None
    created_at: datetime
```

- [ ] **Step 2: Create `backend/src/career_agent/schemas/negotiation.py`**

```python
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class OfferDetails(BaseModel):
    base: int = Field(..., ge=0, description="Base salary in USD")
    equity: str | None = None
    signing_bonus: int | None = None
    total_comp: int | None = None
    location: str | None = None
    start_date: str | None = None


class NegotiationCreate(BaseModel):
    job_id: UUID
    offer_details: OfferDetails


class NegotiationRegenerate(BaseModel):
    feedback: str | None = None


class NegotiationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    job_id: UUID
    offer_details: dict[str, Any]
    market_research: dict[str, Any]
    counter_offer: dict[str, Any]
    scripts: dict[str, Any]
    model_used: str
    tokens_used: int | None
    created_at: datetime
```

- [ ] **Step 3: Create `backend/src/career_agent/schemas/star_story.py`**

```python
from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class StarStoryCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    situation: str = Field(..., min_length=1)
    task: str = Field(..., min_length=1)
    action: str = Field(..., min_length=1)
    result: str = Field(..., min_length=1)
    reflection: str | None = None
    tags: list[str] | None = None


class StarStoryUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    situation: str | None = None
    task: str | None = None
    action: str | None = None
    result: str | None = None
    reflection: str | None = None
    tags: list[str] | None = None


class StarStoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    title: str
    situation: str
    task: str
    action: str
    result: str
    reflection: str | None
    tags: list[str] | None
    source: Literal["ai_generated", "user_created"] | None
    created_at: datetime
```

- [ ] **Step 4: Create `backend/src/career_agent/schemas/feedback.py`**

```python
from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

FeedbackResourceType = Literal[
    "evaluation", "cv_output", "interview_prep", "negotiation"
]


class FeedbackCreate(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    correction_notes: str | None = None


class FeedbackOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    resource_type: FeedbackResourceType
    resource_id: UUID
    rating: int
    correction_notes: str | None
    created_at: datetime
```

- [ ] **Step 5: Verify schemas import**

```bash
uv run python -c "from career_agent.schemas.interview_prep import InterviewPrepCreate, InterviewPrepOut; from career_agent.schemas.negotiation import NegotiationCreate, OfferDetails; from career_agent.schemas.star_story import StarStoryOut; from career_agent.schemas.feedback import FeedbackCreate; print('ok')"
```

Expected: `ok`

- [ ] **Step 6: Run full suite + lint + mypy**

```bash
uv run pytest tests/ 2>&1 | tail -3
uv run ruff check src/ 2>&1 | tail -3
uv run mypy src/ 2>&1 | tail -3
```

Expected: `133 passed`, clean ruff, clean mypy.

- [ ] **Step 7: Checkpoint**

Checkpoint message: `feat(schemas): add Phase 2d Pydantic schemas`

---

## Task 5: Feedback Service with Per-Resource Ownership Validators

**Files:**
- Create: `backend/src/career_agent/core/feedback/__init__.py`
- Create: `backend/src/career_agent/core/feedback/service.py`
- Create: `backend/tests/unit/test_feedback_service_validators.py`

- [ ] **Step 1: Create `backend/src/career_agent/core/feedback/__init__.py`**

```python
"""Feedback service — generic write-path with per-resource ownership validators."""
from career_agent.core.feedback.service import (
    FeedbackResourceNotFound,
    FeedbackService,
    InvalidFeedback,
)

__all__ = ["FeedbackService", "FeedbackResourceNotFound", "InvalidFeedback"]
```

- [ ] **Step 2: Create `backend/src/career_agent/core/feedback/service.py`**

```python
"""Feedback service — generic upsert with per-resource ownership validation.

Ownership is polymorphic: the feedback row carries `resource_type` and
`resource_id` but no FK; we validate ownership in the service layer via a
dispatch dict mapping resource_type to an async validator that loads the
resource and checks the user_id match.
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from career_agent.models.cv_output import CvOutput
from career_agent.models.evaluation import Evaluation
from career_agent.models.feedback import Feedback
from career_agent.models.interview_prep import InterviewPrep
from career_agent.models.negotiation import Negotiation


class FeedbackResourceNotFound(Exception):
    """Raised when the resource doesn't exist or belongs to another user."""


class InvalidFeedback(Exception):
    """Raised when the rating is out of 1–5 range (Pydantic should catch this first)."""


Validator = Callable[[AsyncSession, UUID, UUID], Awaitable[bool]]


async def _validate_evaluation_ownership(
    session: AsyncSession, user_id: UUID, resource_id: UUID
) -> bool:
    stmt = select(Evaluation).where(
        Evaluation.id == resource_id, Evaluation.user_id == user_id
    )
    return (await session.execute(stmt)).scalar_one_or_none() is not None


async def _validate_cv_output_ownership(
    session: AsyncSession, user_id: UUID, resource_id: UUID
) -> bool:
    stmt = select(CvOutput).where(
        CvOutput.id == resource_id, CvOutput.user_id == user_id
    )
    return (await session.execute(stmt)).scalar_one_or_none() is not None


async def _validate_interview_prep_ownership(
    session: AsyncSession, user_id: UUID, resource_id: UUID
) -> bool:
    stmt = select(InterviewPrep).where(
        InterviewPrep.id == resource_id, InterviewPrep.user_id == user_id
    )
    return (await session.execute(stmt)).scalar_one_or_none() is not None


async def _validate_negotiation_ownership(
    session: AsyncSession, user_id: UUID, resource_id: UUID
) -> bool:
    stmt = select(Negotiation).where(
        Negotiation.id == resource_id, Negotiation.user_id == user_id
    )
    return (await session.execute(stmt)).scalar_one_or_none() is not None


_RESOURCE_VALIDATORS: dict[str, Validator] = {
    "evaluation": _validate_evaluation_ownership,
    "cv_output": _validate_cv_output_ownership,
    "interview_prep": _validate_interview_prep_ownership,
    "negotiation": _validate_negotiation_ownership,
}


class FeedbackService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def record(
        self,
        *,
        user_id: UUID,
        resource_type: str,
        resource_id: UUID,
        rating: int,
        correction_notes: str | None,
    ) -> Feedback:
        """Upsert feedback for a resource.

        Validates rating range, then ownership, then performs a Postgres
        ON CONFLICT upsert on (user_id, resource_type, resource_id).
        """
        if not (1 <= rating <= 5):
            raise InvalidFeedback(f"rating must be 1–5, got {rating}")

        validator = _RESOURCE_VALIDATORS.get(resource_type)
        if validator is None:
            raise FeedbackResourceNotFound(
                f"unknown resource_type: {resource_type}"
            )
        owns = await validator(self.session, user_id, resource_id)
        if not owns:
            raise FeedbackResourceNotFound(
                f"{resource_type} {resource_id} not found or not owned by user"
            )

        stmt = (
            pg_insert(Feedback)
            .values(
                user_id=user_id,
                resource_type=resource_type,
                resource_id=resource_id,
                rating=rating,
                correction_notes=correction_notes,
            )
            .on_conflict_do_update(
                index_elements=["user_id", "resource_type", "resource_id"],
                set_={
                    "rating": rating,
                    "correction_notes": correction_notes,
                },
            )
            .returning(Feedback)
        )
        result = await self.session.execute(stmt)
        row = result.scalar_one()
        await self.session.flush()
        return row

    async def get(
        self,
        *,
        user_id: UUID,
        resource_type: str,
        resource_id: UUID,
    ) -> Feedback | None:
        stmt = select(Feedback).where(
            Feedback.user_id == user_id,
            Feedback.resource_type == resource_type,
            Feedback.resource_id == resource_id,
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()
```

- [ ] **Step 3: Write the failing unit test**

`backend/tests/unit/test_feedback_service_validators.py`:

```python
"""Unit tests for the ownership validators — pure async functions."""

import hashlib
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from career_agent.core.feedback.service import (
    FeedbackResourceNotFound,
    FeedbackService,
    InvalidFeedback,
)
from career_agent.db import get_session_factory
from career_agent.models.evaluation import Evaluation
from career_agent.models.job import Job
from career_agent.models.user import User
from tests.conftest import FAKE_CLAIMS


async def _get_user_id() -> UUID:
    factory = get_session_factory()
    async with factory() as session:
        r = await session.execute(
            select(User).where(User.cognito_sub == FAKE_CLAIMS["sub"])
        )
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
        from career_agent.models.feedback import Feedback
        from sqlalchemy import select
        rows = (
            await session.execute(
                select(Feedback).where(Feedback.resource_id == eval_id)
            )
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
    factory = get_session_factory()
    uid_a = await _get_user_id()
    eval_id = await _seed_evaluation(uid_a)

    from career_agent.models.user import User
    from tests.conftest import SECOND_USER_CLAIMS
    async with factory() as session:
        r = await session.execute(
            select(User).where(User.cognito_sub == SECOND_USER_CLAIMS["sub"])
        )
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
```

- [ ] **Step 4: Run the tests**

```bash
uv run pytest tests/unit/test_feedback_service_validators.py -v 2>&1 | tail -20
```

Expected: all 5 tests PASS.

- [ ] **Step 5: Checkpoint**

Checkpoint message: `feat(feedback): add generic feedback service with per-resource ownership validators`

---

## Task 6: Interview Prep Extractor (Claude story extraction)

**Files:**
- Create: `backend/src/career_agent/core/interview_prep/__init__.py`
- Create: `backend/src/career_agent/core/interview_prep/extractor.py`
- Create: `backend/tests/unit/test_interview_prep_extractor_prompt.py`

- [ ] **Step 1: Create `backend/src/career_agent/core/interview_prep/__init__.py`**

```python
"""Interview prep module — extractor + generator + service orchestrator."""
```

- [ ] **Step 2: Create `backend/src/career_agent/core/interview_prep/extractor.py`**

```python
"""InterviewPrepExtractor — Claude call that extracts STAR stories from a resume.

Runs exactly once per user (lazy): the service layer only calls this when
the user's star_stories table is empty. Subsequent prep calls reuse the bank.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from career_agent.config import get_settings
from career_agent.core.llm.anthropic_client import complete_with_cache
from career_agent.core.llm.errors import LLMParseError


_CACHEABLE_INSTRUCTIONS = """You are a career coach extracting STAR+Reflection stories from a candidate's resume.

Your job is to identify 5-10 concrete accomplishments that could anchor interview answers.
Each story must be grounded in the actual resume content — do NOT fabricate metrics, roles,
companies, or outcomes. If the resume is thin, return fewer stories rather than inventing.

STAR+REFLECTION FORMAT:
- title: Short descriptive title (e.g. "Led payments migration at Acme")
- situation: Context and background (1-2 sentences)
- task: What needed to be done (1-2 sentences)
- action: What the candidate specifically did (2-4 sentences, verbs in past tense)
- result: Measurable outcome (cite real numbers from the resume when available)
- reflection: What was learned or what would be done differently (1-2 sentences)
- tags: array of 1-3 competency themes from: leadership, technical, conflict, scale,
  migration, architecture, cross-functional, ownership, mentorship, ambiguity, launch

RULES:
1. Extract only from what's on the resume — no inferred or embellished details
2. Prefer stories with measurable outcomes over process descriptions
3. Cover a mix of competencies across the stories (not all "leadership")
4. If the resume has <3 substantial accomplishments, return just those, not 5
5. Output valid JSON only — no prose outside the JSON

OUTPUT SCHEMA:
{
  "stories": [
    {
      "title": "...",
      "situation": "...",
      "task": "...",
      "action": "...",
      "result": "...",
      "reflection": "...",
      "tags": ["..."]
    }
  ]
}"""

_SYSTEM = "You extract STAR+Reflection stories from resumes into strict JSON. Never add prose outside JSON."


@dataclass
class ExtractedStory:
    title: str
    situation: str
    task: str
    action: str
    result: str
    reflection: str | None
    tags: list[str]


@dataclass
class ExtractionResult:
    stories: list[ExtractedStory]
    usage: Any
    model: str


async def extract_star_stories_from_resume(
    *, master_resume_md: str
) -> ExtractionResult:
    """One-shot Claude call. Uses prompt caching on the instructions block."""
    settings = get_settings()
    user_block = f"RESUME:\n{master_resume_md}\n\nExtract 5-10 STAR+Reflection stories. Output JSON."

    result = await complete_with_cache(
        system=_SYSTEM,
        cacheable_blocks=[_CACHEABLE_INSTRUCTIONS],
        user_block=user_block,
        model=settings.claude_model,
        max_tokens=3000,
        timeout_s=settings.llm_evaluation_timeout_s,
    )

    parsed = _parse(result.text)
    stories = [
        ExtractedStory(
            title=str(s.get("title", "Untitled")),
            situation=str(s.get("situation", "")),
            task=str(s.get("task", "")),
            action=str(s.get("action", "")),
            result=str(s.get("result", "")),
            reflection=s.get("reflection"),
            tags=list(s.get("tags", [])),
        )
        for s in parsed.get("stories", [])
    ]
    return ExtractionResult(stories=stories, usage=result.usage, model=result.model)


def _parse(text: str) -> dict[str, Any]:
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.MULTILINE)
    try:
        data: dict[str, Any] = json.loads(raw)
    except json.JSONDecodeError as e:
        raise LLMParseError(
            "Interview prep extractor returned invalid JSON",
            provider="anthropic",
            details={"raw": raw[:500]},
        ) from e
    if "stories" not in data:
        raise LLMParseError(
            "Missing 'stories' field in extractor response",
            provider="anthropic",
        )
    return data
```

- [ ] **Step 3: Write the unit test**

`backend/tests/unit/test_interview_prep_extractor_prompt.py`:

```python
import json

import pytest

from career_agent.core.interview_prep.extractor import (
    extract_star_stories_from_resume,
)
from tests.fixtures.fake_anthropic import fake_anthropic


_FAKE_RESPONSE = json.dumps(
    {
        "stories": [
            {
                "title": "Led payments migration at Acme",
                "situation": "Legacy monolith handling $200M/yr",
                "task": "Migrate to microservices without downtime",
                "action": "Designed strangler pattern, led 6 engineers, ran dual-write for 3 months",
                "result": "Zero-downtime cutover; p99 latency dropped 40%",
                "reflection": "Would have invested in observability earlier",
                "tags": ["leadership", "migration", "scale"],
            },
            {
                "title": "Fixed production outage",
                "situation": "3am page, database connection pool exhausted",
                "task": "Restore service",
                "action": "Bounced app servers, added connection timeout, wrote postmortem",
                "result": "Service restored in 18 minutes",
                "reflection": "Better alerting on pool saturation",
                "tags": ["ownership", "technical"],
            },
        ]
    }
)


@pytest.mark.asyncio
async def test_extractor_returns_structured_stories():
    resume = (
        "# Jane Doe\n\n## Experience\n\n"
        "- Senior Engineer at Acme (2020-2024): led payments migration, "
        "zero-downtime cutover, p99 latency -40%"
    )
    with fake_anthropic({"RESUME": _FAKE_RESPONSE}):
        result = await extract_star_stories_from_resume(master_resume_md=resume)

    assert len(result.stories) == 2
    first = result.stories[0]
    assert first.title == "Led payments migration at Acme"
    assert "leadership" in first.tags
    assert first.result.startswith("Zero-downtime")


@pytest.mark.asyncio
async def test_extractor_raises_on_garbage_json():
    from career_agent.core.llm.errors import LLMParseError

    with fake_anthropic({"RESUME": "not json at all"}):
        with pytest.raises(LLMParseError):
            await extract_star_stories_from_resume(
                master_resume_md="## summary\n\nTest resume content."
            )


@pytest.mark.asyncio
async def test_extractor_raises_on_missing_stories_key():
    from career_agent.core.llm.errors import LLMParseError

    with fake_anthropic({"RESUME": json.dumps({"other_key": []})}):
        with pytest.raises(LLMParseError):
            await extract_star_stories_from_resume(
                master_resume_md="## summary\n\nTest resume content."
            )
```

- [ ] **Step 4: Run the tests**

```bash
uv run pytest tests/unit/test_interview_prep_extractor_prompt.py -v 2>&1 | tail -15
```

Expected: all 3 tests PASS.

- [ ] **Step 5: Checkpoint**

Checkpoint message: `feat(interview-prep): add extractor — Claude call for STAR story extraction`

---

## Task 7: Interview Prep Generator (Claude question generation via Appendix D.6)

**Files:**
- Create: `backend/src/career_agent/core/interview_prep/generator.py`
- Create: `backend/tests/unit/test_interview_prep_generator_prompt.py`

- [ ] **Step 1: Create `backend/src/career_agent/core/interview_prep/generator.py`**

```python
"""InterviewPrepGenerator — Claude call to generate interview questions.

Uses parent spec Appendix D.6 prompt. Supports two modes:
1. Job-tied: `job_markdown` provided → questions tailored to the specific role
2. Custom role: `custom_role` provided → generic prep for that role description

Exactly one of the two must be set.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from career_agent.config import get_settings
from career_agent.core.llm.anthropic_client import complete_with_cache
from career_agent.core.llm.errors import LLMParseError


_CACHEABLE_INSTRUCTIONS = """You are an interview prep coach. Given a candidate's resume and a target role,
generate interview questions and red-flag questions for the candidate to ask.

OUTPUT STRUCTURE:
1. 10 likely interview questions with suggested answer frameworks, each linked
   to a STAR story from the existing story bank when possible
2. 5 "red flag" questions the candidate should ask the interviewer to evaluate
   the company (with what to listen for)

QUESTION CATEGORIES (use all 4):
- behavioral — "Tell me about a time..."
- technical — role-specific technical knowledge
- situational — "How would you handle..."
- culture — values, motivation, fit

RULES:
- Each question should be specific to the role and seniority
- Suggested story title MUST reference an actual story from the provided bank, not invent one
- If no suitable story exists, set suggested_story_title to null
- Frameworks are 1-2 sentence hints, not full answers
- Red-flag questions should probe concrete concerns: team health, technical debt,
  hiring funnel, runway, management practices

OUTPUT JSON SCHEMA:
{
  "questions": [
    {
      "question": "...",
      "category": "behavioral" | "technical" | "situational" | "culture",
      "suggested_story_title": "string from story bank OR null",
      "framework": "1-2 sentence answer framework"
    }
  ],
  "red_flag_questions": [
    {
      "question": "...",
      "what_to_listen_for": "..."
    }
  ]
}

No prose outside JSON."""

_SYSTEM = (
    "You are an interview prep coach. Output only strict JSON matching the schema."
)


@dataclass
class GeneratedInterviewPrep:
    questions: list[dict[str, Any]]
    red_flag_questions: list[dict[str, Any]]
    usage: Any
    model: str


async def generate_interview_prep(
    *,
    existing_stories_summary: str,
    job_markdown: str | None,
    custom_role: str | None,
    resume_md: str,
    feedback: str | None = None,
) -> GeneratedInterviewPrep:
    """Generate interview prep. Exactly one of job_markdown / custom_role must be set."""
    if bool(job_markdown) == bool(custom_role):
        raise ValueError("Exactly one of job_markdown or custom_role must be set")

    settings = get_settings()
    role_block = (
        f"TARGET JOB:\n{job_markdown}"
        if job_markdown
        else f"TARGET ROLE (custom):\n{custom_role}"
    )
    feedback_block = (
        f"\n\nUSER FEEDBACK FROM PRIOR ATTEMPT:\n{feedback}" if feedback else ""
    )
    user_block = (
        f"CANDIDATE RESUME:\n{resume_md}\n\n"
        f"{role_block}\n\n"
        f"EXISTING STORY BANK (reference these in suggested_story_title, do not duplicate):\n"
        f"{existing_stories_summary}{feedback_block}\n\n"
        "Generate interview prep per the schema. Output JSON only."
    )

    result = await complete_with_cache(
        system=_SYSTEM,
        cacheable_blocks=[_CACHEABLE_INSTRUCTIONS],
        user_block=user_block,
        model=settings.claude_model,
        max_tokens=3000,
        timeout_s=settings.llm_evaluation_timeout_s,
    )

    parsed = _parse(result.text)
    return GeneratedInterviewPrep(
        questions=list(parsed.get("questions", [])),
        red_flag_questions=list(parsed.get("red_flag_questions", [])),
        usage=result.usage,
        model=result.model,
    )


def _parse(text: str) -> dict[str, Any]:
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.MULTILINE)
    try:
        data: dict[str, Any] = json.loads(raw)
    except json.JSONDecodeError as e:
        raise LLMParseError(
            "Interview prep generator returned invalid JSON",
            provider="anthropic",
            details={"raw": raw[:500]},
        ) from e
    if "questions" not in data:
        raise LLMParseError(
            "Missing 'questions' field in generator response",
            provider="anthropic",
        )
    return data
```

- [ ] **Step 2: Write the unit test**

`backend/tests/unit/test_interview_prep_generator_prompt.py`:

```python
import json

import pytest

from career_agent.core.interview_prep.generator import generate_interview_prep
from tests.fixtures.fake_anthropic import fake_anthropic


_FAKE_RESPONSE = json.dumps(
    {
        "questions": [
            {
                "question": "Tell me about a time you led a difficult migration.",
                "category": "behavioral",
                "suggested_story_title": "Led payments migration at Acme",
                "framework": "Use STAR. Emphasize dual-write strategy and how you managed risk.",
            },
            {
                "question": "How would you design a rate limiter for 1M QPS?",
                "category": "technical",
                "suggested_story_title": None,
                "framework": "Discuss token bucket vs sliding window, Redis Lua for atomicity.",
            },
        ],
        "red_flag_questions": [
            {
                "question": "What's the team's current on-call burden look like?",
                "what_to_listen_for": "Specific numbers (pages per week, avg response time). Vague answers are a warning sign.",
            }
        ],
    }
)


@pytest.mark.asyncio
async def test_generator_job_mode():
    with fake_anthropic({"CANDIDATE RESUME": _FAKE_RESPONSE}):
        result = await generate_interview_prep(
            existing_stories_summary="1. Led payments migration at Acme\n2. Fixed production outage",
            job_markdown="Senior Engineer at Stripe working on payment infrastructure.",
            custom_role=None,
            resume_md="## Jane Doe\n\nSenior engineer with payments experience.",
        )
    assert len(result.questions) == 2
    assert result.questions[0]["suggested_story_title"] == "Led payments migration at Acme"
    assert len(result.red_flag_questions) == 1


@pytest.mark.asyncio
async def test_generator_custom_role_mode():
    with fake_anthropic({"CANDIDATE RESUME": _FAKE_RESPONSE}):
        result = await generate_interview_prep(
            existing_stories_summary="1. Led payments migration at Acme",
            job_markdown=None,
            custom_role="Staff SRE at any FAANG — focus on incident response and reliability",
            resume_md="## Jane Doe\n\nReliability engineering background.",
        )
    assert len(result.questions) >= 1


@pytest.mark.asyncio
async def test_generator_rejects_both_job_and_custom_role():
    with pytest.raises(ValueError):
        await generate_interview_prep(
            existing_stories_summary="",
            job_markdown="job",
            custom_role="role",
            resume_md="resume",
        )


@pytest.mark.asyncio
async def test_generator_rejects_neither_job_nor_custom_role():
    with pytest.raises(ValueError):
        await generate_interview_prep(
            existing_stories_summary="",
            job_markdown=None,
            custom_role=None,
            resume_md="resume",
        )
```

- [ ] **Step 3: Run the tests**

```bash
uv run pytest tests/unit/test_interview_prep_generator_prompt.py -v 2>&1 | tail -15
```

Expected: all 4 tests PASS.

- [ ] **Step 4: Checkpoint**

Checkpoint message: `feat(interview-prep): add generator — Claude call for questions via Appendix D.6`

---

## Task 8: Interview Prep Service (Orchestrator)

**Files:**
- Create: `backend/src/career_agent/core/interview_prep/service.py`
- Create: `backend/tests/integration/test_interview_prep_auto_populates_story_bank.py`
- Create: `backend/tests/integration/test_interview_prep_custom_role.py`

- [ ] **Step 1: Create `backend/src/career_agent/core/interview_prep/service.py`**

```python
"""InterviewPrepService — orchestrator.

Flow:
  1. ensure_story_bank(user_id) — if empty, extract from master resume
  2. generate(user_id, job_id | custom_role, feedback?) — call generator
  3. persist to interview_preps
  4. return InterviewPrep row
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from career_agent.api.errors import AppError
from career_agent.core.interview_prep.extractor import extract_star_stories_from_resume
from career_agent.core.interview_prep.generator import generate_interview_prep
from career_agent.core.llm.errors import LLMError
from career_agent.models.interview_prep import InterviewPrep
from career_agent.models.job import Job
from career_agent.models.profile import Profile
from career_agent.models.star_story import StarStory
from career_agent.services.usage_event import UsageEventService


@dataclass
class InterviewPrepContext:
    user_id: UUID
    session: AsyncSession
    usage: UsageEventService


class InterviewPrepService:
    def __init__(self, context: InterviewPrepContext):
        self.context = context

    async def ensure_story_bank(self) -> list[StarStory]:
        """If the user has no star_stories, extract from their master resume."""
        existing = (
            await self.context.session.execute(
                select(StarStory).where(StarStory.user_id == self.context.user_id)
            )
        ).scalars().all()
        if existing:
            return list(existing)

        profile = (
            await self.context.session.execute(
                select(Profile).where(Profile.user_id == self.context.user_id)
            )
        ).scalar_one_or_none()
        if profile is None or not profile.master_resume_md:
            raise AppError(
                422,
                "MISSING_MASTER_RESUME",
                "Upload your resume before building interview prep.",
            )

        try:
            result = await extract_star_stories_from_resume(
                master_resume_md=profile.master_resume_md
            )
        except LLMError as e:
            raise AppError(
                502,
                "LLM_ERROR",
                f"Story extraction failed: {e}",
            ) from e

        new_stories: list[StarStory] = []
        for s in result.stories:
            row = StarStory(
                user_id=self.context.user_id,
                title=s.title,
                situation=s.situation,
                task=s.task,
                action=s.action,
                result=s.result,
                reflection=s.reflection,
                tags=s.tags,
                source="ai_generated",
            )
            self.context.session.add(row)
            new_stories.append(row)
        await self.context.session.flush()

        await self.context.usage.record(
            user_id=self.context.user_id,
            event_type="interview_prep_extract",
            module="interview_prep",
            model=result.model,
            tokens_used=result.usage.total_tokens,
            cost_cents=result.usage.cost_cents(result.model),
        )

        return new_stories

    async def create(
        self,
        *,
        job_id: UUID | None = None,
        custom_role: str | None = None,
        feedback: str | None = None,
    ) -> InterviewPrep:
        if bool(job_id) == bool(custom_role):
            raise AppError(
                422,
                "INVALID_INTERVIEW_PREP_INPUT",
                "Provide exactly one of job_id or custom_role",
            )

        stories = await self.ensure_story_bank()
        stories_summary = "\n".join(
            f"- {s.title}" for s in stories
        )

        profile = (
            await self.context.session.execute(
                select(Profile).where(Profile.user_id == self.context.user_id)
            )
        ).scalar_one()
        resume_md = profile.master_resume_md or ""

        job_markdown: str | None = None
        if job_id is not None:
            job = (
                await self.context.session.execute(
                    select(Job).where(Job.id == job_id)
                )
            ).scalar_one_or_none()
            if job is None:
                raise AppError(404, "JOB_NOT_FOUND", "Job not found")
            job_markdown = job.description_md

        try:
            generated = await generate_interview_prep(
                existing_stories_summary=stories_summary,
                job_markdown=job_markdown,
                custom_role=custom_role,
                resume_md=resume_md,
                feedback=feedback,
            )
        except LLMError as e:
            raise AppError(502, "LLM_ERROR", f"Generation failed: {e}") from e

        row = InterviewPrep(
            user_id=self.context.user_id,
            job_id=job_id,
            custom_role=custom_role,
            questions=generated.questions,
            red_flag_questions=generated.red_flag_questions,
            model_used=generated.model,
            tokens_used=generated.usage.total_tokens,
        )
        self.context.session.add(row)
        await self.context.session.flush()

        await self.context.usage.record(
            user_id=self.context.user_id,
            event_type="interview_prep_generate",
            module="interview_prep",
            model=generated.model,
            tokens_used=generated.usage.total_tokens,
            cost_cents=generated.usage.cost_cents(generated.model),
        )

        return row

    async def regenerate(
        self,
        *,
        interview_prep_id: UUID,
        feedback: str | None,
    ) -> InterviewPrep:
        """Create a new interview_preps row using the original's job/role + new feedback."""
        stmt = select(InterviewPrep).where(
            InterviewPrep.id == interview_prep_id,
            InterviewPrep.user_id == self.context.user_id,
        )
        original = (await self.context.session.execute(stmt)).scalar_one_or_none()
        if original is None:
            raise AppError(
                404,
                "INTERVIEW_PREP_NOT_FOUND",
                "Interview prep not found",
            )
        return await self.create(
            job_id=original.job_id,
            custom_role=original.custom_role,
            feedback=feedback,
        )

    async def get_for_user(self, prep_id: UUID) -> InterviewPrep | None:
        stmt = select(InterviewPrep).where(
            InterviewPrep.id == prep_id,
            InterviewPrep.user_id == self.context.user_id,
        )
        return (
            await self.context.session.execute(stmt)
        ).scalar_one_or_none()

    async def list_for_user(self, *, limit: int = 20) -> list[InterviewPrep]:
        stmt = (
            select(InterviewPrep)
            .where(InterviewPrep.user_id == self.context.user_id)
            .order_by(InterviewPrep.created_at.desc())
            .limit(limit)
        )
        return list(
            (await self.context.session.execute(stmt)).scalars().all()
        )
```

- [ ] **Step 2: Write integration test — auto-populate story bank**

`backend/tests/integration/test_interview_prep_auto_populates_story_bank.py`:

```python
import json
from uuid import UUID

import pytest
from sqlalchemy import delete, select

from career_agent.core.interview_prep.service import (
    InterviewPrepContext,
    InterviewPrepService,
)
from career_agent.db import get_session_factory
from career_agent.models.star_story import StarStory
from career_agent.models.user import User
from career_agent.services.usage_event import UsageEventService
from tests.conftest import FAKE_CLAIMS
from tests.fixtures.fake_anthropic import fake_anthropic


_EXTRACT_RESPONSE = json.dumps(
    {
        "stories": [
            {
                "title": "Led payments migration at Acme",
                "situation": "Legacy monolith",
                "task": "Migrate",
                "action": "Designed strangler pattern",
                "result": "Zero downtime",
                "reflection": "Earlier observability",
                "tags": ["leadership", "migration"],
            }
        ]
    }
)

_GEN_RESPONSE = json.dumps(
    {
        "questions": [
            {
                "question": "Tell me about a migration you led.",
                "category": "behavioral",
                "suggested_story_title": "Led payments migration at Acme",
                "framework": "STAR",
            }
        ],
        "red_flag_questions": [
            {
                "question": "On-call burden?",
                "what_to_listen_for": "Specific numbers",
            }
        ],
    }
)


async def _uid() -> UUID:
    factory = get_session_factory()
    async with factory() as s:
        r = await s.execute(select(User).where(User.cognito_sub == FAKE_CLAIMS["sub"]))
        return r.scalar_one().id


async def _clear_stories(user_id: UUID) -> None:
    factory = get_session_factory()
    async with factory() as session:
        await session.execute(
            delete(StarStory).where(StarStory.user_id == user_id)
        )
        await session.commit()


@pytest.mark.asyncio
async def test_first_call_extracts_stories_then_generates_prep(seed_profile):
    """First call with empty story bank: extraction runs, then generation runs."""
    uid = await _uid()
    await _clear_stories(uid)

    factory = get_session_factory()
    with fake_anthropic(
        {
            "RESUME": _EXTRACT_RESPONSE,
            "CANDIDATE RESUME": _GEN_RESPONSE,
        }
    ):
        async with factory() as session:
            usage = UsageEventService(session)
            ctx = InterviewPrepContext(user_id=uid, session=session, usage=usage)
            service = InterviewPrepService(ctx)
            prep = await service.create(custom_role="Staff Engineer")
            await session.commit()

    # Story bank populated
    async with factory() as session:
        stories = (
            (
                await session.execute(
                    select(StarStory).where(StarStory.user_id == uid)
                )
            )
            .scalars()
            .all()
        )
    assert len(stories) == 1
    assert stories[0].source == "ai_generated"
    assert stories[0].title == "Led payments migration at Acme"

    # Prep created
    assert prep.custom_role == "Staff Engineer"
    assert len(prep.questions) == 1
    assert prep.red_flag_questions is not None


@pytest.mark.asyncio
async def test_second_call_skips_extraction(seed_profile):
    """When story bank is non-empty, extractor is NOT called."""
    uid = await _uid()

    # Ensure a story exists
    factory = get_session_factory()
    async with factory() as session:
        await session.execute(delete(StarStory).where(StarStory.user_id == uid))
        session.add(
            StarStory(
                user_id=uid,
                title="Pre-seeded story",
                situation="x",
                task="x",
                action="x",
                result="x",
                reflection=None,
                tags=["leadership"],
                source="user_created",
            )
        )
        await session.commit()

    # Only provide generator response, NOT extractor response.
    # If extraction runs, the test will fail because RESUME fake isn't configured.
    with fake_anthropic({"CANDIDATE RESUME": _GEN_RESPONSE}) as fake_client:
        async with factory() as session:
            usage = UsageEventService(session)
            ctx = InterviewPrepContext(user_id=uid, session=session, usage=usage)
            service = InterviewPrepService(ctx)
            prep = await service.create(custom_role="Staff Engineer")
            await session.commit()

        # Verify only ONE Claude call was made (generator, not extractor)
        assert len(fake_client.calls) == 1
    assert prep is not None
```

- [ ] **Step 3: Write integration test — custom role mode**

`backend/tests/integration/test_interview_prep_custom_role.py`:

```python
import json
from uuid import UUID

import pytest
from sqlalchemy import delete, select

from career_agent.core.interview_prep.service import (
    InterviewPrepContext,
    InterviewPrepService,
)
from career_agent.db import get_session_factory
from career_agent.models.star_story import StarStory
from career_agent.models.user import User
from career_agent.services.usage_event import UsageEventService
from tests.conftest import FAKE_CLAIMS
from tests.fixtures.fake_anthropic import fake_anthropic


_GEN_RESPONSE = json.dumps(
    {
        "questions": [
            {
                "question": "Describe your on-call approach.",
                "category": "situational",
                "suggested_story_title": None,
                "framework": "Describe runbooks + postmortem habit",
            }
        ],
        "red_flag_questions": [],
    }
)


async def _uid() -> UUID:
    factory = get_session_factory()
    async with factory() as s:
        r = await s.execute(select(User).where(User.cognito_sub == FAKE_CLAIMS["sub"]))
        return r.scalar_one().id


@pytest.mark.asyncio
async def test_custom_role_mode_no_job_id(seed_profile):
    uid = await _uid()
    factory = get_session_factory()
    async with factory() as session:
        # ensure at least one story exists so extraction is skipped
        await session.execute(delete(StarStory).where(StarStory.user_id == uid))
        session.add(
            StarStory(
                user_id=uid,
                title="SRE incident response",
                situation="Prod outage",
                task="Restore",
                action="Mitigate + postmortem",
                result="MTTR cut in half",
                reflection=None,
                tags=["ownership"],
                source="user_created",
            )
        )
        await session.commit()

    with fake_anthropic({"CANDIDATE RESUME": _GEN_RESPONSE}):
        async with factory() as session:
            usage = UsageEventService(session)
            ctx = InterviewPrepContext(user_id=uid, session=session, usage=usage)
            service = InterviewPrepService(ctx)
            prep = await service.create(custom_role="Staff SRE at FAANG")
            await session.commit()

    assert prep.custom_role == "Staff SRE at FAANG"
    assert prep.job_id is None
    assert len(prep.questions) == 1


@pytest.mark.asyncio
async def test_rejects_both_job_id_and_custom_role(seed_profile):
    from uuid import uuid4

    from career_agent.api.errors import AppError

    uid = await _uid()
    factory = get_session_factory()
    async with factory() as session:
        usage = UsageEventService(session)
        ctx = InterviewPrepContext(user_id=uid, session=session, usage=usage)
        service = InterviewPrepService(ctx)
        with pytest.raises(AppError) as exc:
            await service.create(job_id=uuid4(), custom_role="x")
    assert exc.value.code == "INVALID_INTERVIEW_PREP_INPUT"
```

- [ ] **Step 4: Run the tests**

```bash
uv run pytest tests/integration/test_interview_prep_auto_populates_story_bank.py tests/integration/test_interview_prep_custom_role.py -v 2>&1 | tail -15
```

Expected: all 4 tests PASS.

- [ ] **Step 5: Checkpoint**

Checkpoint message: `feat(interview-prep): add service orchestrator with lazy story bank extraction`

---

## Task 9: Interview Prep CRUD Service + Job-Id Mode Integration Test

**Files:**
- Create: `backend/src/career_agent/services/interview_prep.py`
- Create: `backend/tests/integration/test_interview_prep_job_id_mode.py`

- [ ] **Step 1: Create `backend/src/career_agent/services/interview_prep.py`**

```python
"""InterviewPrep CRUD helpers — thin wrapper for API layer."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from career_agent.models.interview_prep import InterviewPrep


async def get_for_user(
    session: AsyncSession, user_id: UUID, prep_id: UUID
) -> InterviewPrep | None:
    stmt = select(InterviewPrep).where(
        InterviewPrep.id == prep_id,
        InterviewPrep.user_id == user_id,
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def list_for_user(
    session: AsyncSession, user_id: UUID, *, limit: int = 20
) -> list[InterviewPrep]:
    stmt = (
        select(InterviewPrep)
        .where(InterviewPrep.user_id == user_id)
        .order_by(InterviewPrep.created_at.desc())
        .limit(limit)
    )
    return list((await session.execute(stmt)).scalars().all())
```

- [ ] **Step 2: Write integration test — job-id mode**

`backend/tests/integration/test_interview_prep_job_id_mode.py`:

```python
import hashlib
import json
from uuid import UUID, uuid4

import pytest
from sqlalchemy import delete, select

from career_agent.core.interview_prep.service import (
    InterviewPrepContext,
    InterviewPrepService,
)
from career_agent.db import get_session_factory
from career_agent.models.job import Job
from career_agent.models.star_story import StarStory
from career_agent.models.user import User
from career_agent.services.usage_event import UsageEventService
from tests.conftest import FAKE_CLAIMS
from tests.fixtures.fake_anthropic import fake_anthropic


_GEN_RESPONSE = json.dumps(
    {
        "questions": [
            {
                "question": "Tell me about a payments system you built.",
                "category": "behavioral",
                "suggested_story_title": "Pre-seeded story",
                "framework": "STAR — emphasize scale + reliability",
            }
        ],
        "red_flag_questions": [],
    }
)


async def _uid() -> UUID:
    factory = get_session_factory()
    async with factory() as s:
        r = await s.execute(select(User).where(User.cognito_sub == FAKE_CLAIMS["sub"]))
        return r.scalar_one().id


@pytest.mark.asyncio
async def test_job_id_mode_loads_job_description(seed_profile):
    uid = await _uid()
    factory = get_session_factory()

    # Seed a job + at least one story (so extraction is skipped)
    async with factory() as session:
        await session.execute(delete(StarStory).where(StarStory.user_id == uid))
        session.add(
            StarStory(
                user_id=uid,
                title="Pre-seeded story",
                situation="x",
                task="x",
                action="x",
                result="x",
                reflection=None,
                tags=["leadership"],
                source="user_created",
            )
        )
        h = hashlib.sha256(f"prep-job-{uuid4()}".encode()).hexdigest()
        job = Job(
            content_hash=h,
            title="Senior Payments Engineer at Stripe",
            description_md="Build payments infrastructure at scale.",
            requirements_json={"skills": ["python", "distributed systems"]},
            source="manual",
        )
        session.add(job)
        await session.commit()
        jid = job.id

    with fake_anthropic({"CANDIDATE RESUME": _GEN_RESPONSE}):
        async with factory() as session:
            usage = UsageEventService(session)
            ctx = InterviewPrepContext(user_id=uid, session=session, usage=usage)
            service = InterviewPrepService(ctx)
            prep = await service.create(job_id=jid)
            await session.commit()

    assert prep.job_id == jid
    assert prep.custom_role is None
    assert len(prep.questions) >= 1
```

- [ ] **Step 3: Run the test**

```bash
uv run pytest tests/integration/test_interview_prep_job_id_mode.py -v 2>&1 | tail -10
```

Expected: 1 test PASSES.

- [ ] **Step 4: Checkpoint**

Checkpoint message: `feat(interview-prep): add CRUD helpers + job-id mode integration test`

---

## Task 10: Interview Preps API — POST Create

**Files:**
- Create: `backend/src/career_agent/api/interview_preps.py`
- Modify: `backend/src/career_agent/main.py`

- [ ] **Step 1: Create `backend/src/career_agent/api/interview_preps.py`**

```python
"""Interview preps API — create, list, get, regenerate, feedback."""
from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Query

from career_agent.api.deps import CurrentDbUser, DbSession, EntitledDbUser
from career_agent.api.errors import AppError
from career_agent.core.interview_prep.service import (
    InterviewPrepContext,
    InterviewPrepService,
)
from career_agent.schemas.interview_prep import (
    InterviewPrepCreate,
    InterviewPrepOut,
    InterviewPrepRegenerate,
)
from career_agent.services.interview_prep import get_for_user, list_for_user
from career_agent.services.usage_event import UsageEventService

router = APIRouter(prefix="/interview-preps", tags=["interview-preps"])


@router.post("", status_code=201)
async def create_interview_prep(
    payload: InterviewPrepCreate,
    user: EntitledDbUser,
    session: DbSession,
) -> dict[str, Any]:
    usage = UsageEventService(session)
    ctx = InterviewPrepContext(user_id=user.id, session=session, usage=usage)
    service = InterviewPrepService(ctx)
    prep = await service.create(
        job_id=payload.job_id,
        custom_role=payload.custom_role,
    )
    await session.commit()
    return {"data": InterviewPrepOut.model_validate(prep).model_dump(mode="json")}


@router.get("")
async def list_interview_preps(
    user: CurrentDbUser,
    session: DbSession,
    limit: int = Query(default=20, ge=1, le=100),
) -> dict[str, Any]:
    rows = await list_for_user(session, user.id, limit=limit)
    return {
        "data": [InterviewPrepOut.model_validate(r).model_dump(mode="json") for r in rows]
    }


@router.get("/{prep_id}")
async def get_interview_prep(
    prep_id: UUID,
    user: CurrentDbUser,
    session: DbSession,
) -> dict[str, Any]:
    row = await get_for_user(session, user.id, prep_id)
    if row is None:
        raise AppError(404, "INTERVIEW_PREP_NOT_FOUND", "Interview prep not found")
    return {"data": InterviewPrepOut.model_validate(row).model_dump(mode="json")}


@router.post("/{prep_id}/regenerate", status_code=201)
async def regenerate_interview_prep(
    prep_id: UUID,
    payload: InterviewPrepRegenerate,
    user: EntitledDbUser,
    session: DbSession,
) -> dict[str, Any]:
    usage = UsageEventService(session)
    ctx = InterviewPrepContext(user_id=user.id, session=session, usage=usage)
    service = InterviewPrepService(ctx)
    prep = await service.regenerate(
        interview_prep_id=prep_id, feedback=payload.feedback
    )
    await session.commit()
    return {"data": InterviewPrepOut.model_validate(prep).model_dump(mode="json")}
```

- [ ] **Step 2: Register router in `main.py`**

Find the existing `include_router` calls and add:

```python
from career_agent.api import interview_preps
app.include_router(interview_preps.router, prefix="/api/v1")
```

- [ ] **Step 3: Run full backend suite + lint + mypy**

```bash
uv run pytest tests/ 2>&1 | tail -3
uv run ruff check src/ 2>&1 | tail -3
uv run mypy src/ 2>&1 | tail -3
```

Expected: all passing + clean.

- [ ] **Step 4: Checkpoint**

Checkpoint message: `feat(api): add interview preps create/list/get/regenerate endpoints`

---

## Task 11: Interview Prep Regenerate + Paywall Integration Tests

**Files:**
- Create: `backend/tests/integration/test_interview_prep_regenerate.py`
- Create: `backend/tests/integration/test_interview_prep_paywalled.py`

- [ ] **Step 1: Write the regenerate test**

`backend/tests/integration/test_interview_prep_regenerate.py`:

```python
import json
from unittest.mock import AsyncMock, patch
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select

from career_agent.db import get_session_factory
from career_agent.main import app
from career_agent.models.interview_prep import InterviewPrep
from career_agent.models.star_story import StarStory
from career_agent.models.user import User
from tests.conftest import FAKE_CLAIMS
from tests.fixtures.fake_anthropic import fake_anthropic


_GEN_V1 = json.dumps(
    {
        "questions": [
            {
                "question": "v1 question",
                "category": "behavioral",
                "suggested_story_title": "Pre-seeded story",
                "framework": "v1 framework",
            }
        ],
        "red_flag_questions": [],
    }
)

_GEN_V2 = json.dumps(
    {
        "questions": [
            {
                "question": "v2 question (harder)",
                "category": "technical",
                "suggested_story_title": None,
                "framework": "v2 framework",
            }
        ],
        "red_flag_questions": [],
    }
)


async def _uid() -> UUID:
    factory = get_session_factory()
    async with factory() as s:
        r = await s.execute(select(User).where(User.cognito_sub == FAKE_CLAIMS["sub"]))
        return r.scalar_one().id


@pytest.mark.asyncio
async def test_regenerate_creates_new_row(auth_headers, seed_profile):
    uid = await _uid()
    factory = get_session_factory()

    async with factory() as session:
        await session.execute(delete(StarStory).where(StarStory.user_id == uid))
        session.add(
            StarStory(
                user_id=uid,
                title="Pre-seeded story",
                situation="x",
                task="x",
                action="x",
                result="x",
                reflection=None,
                tags=["leadership"],
                source="user_created",
            )
        )
        await session.commit()

    with (
        patch(
            "career_agent.integrations.cognito.CognitoJwtVerifier.verify",
            new=AsyncMock(return_value=FAKE_CLAIMS),
        ),
        fake_anthropic({"CANDIDATE RESUME": _GEN_V1}),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            r1 = await client.post(
                "/api/v1/interview-preps",
                json={"custom_role": "Staff Engineer"},
                headers=auth_headers,
            )
    assert r1.status_code == 201
    prep_v1_id = r1.json()["data"]["id"]

    with (
        patch(
            "career_agent.integrations.cognito.CognitoJwtVerifier.verify",
            new=AsyncMock(return_value=FAKE_CLAIMS),
        ),
        fake_anthropic({"CANDIDATE RESUME": _GEN_V2}),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            r2 = await client.post(
                f"/api/v1/interview-preps/{prep_v1_id}/regenerate",
                json={"feedback": "Make questions harder"},
                headers=auth_headers,
            )
    assert r2.status_code == 201
    prep_v2_id = r2.json()["data"]["id"]

    # v2 is a NEW row, not a mutation of v1
    assert prep_v2_id != prep_v1_id

    # Both rows should still exist
    async with factory() as session:
        rows = (
            (await session.execute(select(InterviewPrep).where(InterviewPrep.user_id == uid)))
            .scalars()
            .all()
        )
    assert len([r for r in rows if str(r.id) in (prep_v1_id, prep_v2_id)]) == 2
```

- [ ] **Step 2: Write the paywall test**

`backend/tests/integration/test_interview_prep_paywalled.py`:

```python
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from career_agent.db import get_session_factory
from career_agent.main import app
from career_agent.models.subscription import Subscription
from career_agent.models.user import User
from tests.conftest import FAKE_CLAIMS


async def _uid() -> UUID:
    factory = get_session_factory()
    async with factory() as s:
        r = await s.execute(select(User).where(User.cognito_sub == FAKE_CLAIMS["sub"]))
        return r.scalar_one().id


@pytest.mark.asyncio
async def test_interview_prep_post_requires_entitlement(auth_headers, seed_profile):
    """POST /interview-preps returns 403 when trial expired and no Stripe sub."""
    uid = await _uid()
    factory = get_session_factory()
    async with factory() as session:
        sub = (
            await session.execute(
                select(Subscription).where(Subscription.user_id == uid)
            )
        ).scalar_one_or_none()
        if sub is None:
            sub = Subscription(user_id=uid, plan="trial", status="active")
            session.add(sub)
            await session.flush()
        sub.trial_ends_at = datetime.now(UTC) - timedelta(days=1)
        sub.stripe_subscription_id = None
        await session.commit()

    try:
        with patch(
            "career_agent.integrations.cognito.CognitoJwtVerifier.verify",
            new=AsyncMock(return_value=FAKE_CLAIMS),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/v1/interview-preps",
                    json={"custom_role": "Staff Engineer"},
                    headers=auth_headers,
                )
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "TRIAL_EXPIRED"
    finally:
        async with factory() as session:
            sub = (
                await session.execute(
                    select(Subscription).where(Subscription.user_id == uid)
                )
            ).scalar_one_or_none()
            if sub is not None:
                sub.trial_ends_at = datetime.now(UTC) + timedelta(days=30)
                await session.commit()


@pytest.mark.asyncio
async def test_interview_prep_get_not_paywalled(auth_headers, seed_profile):
    """GET /interview-preps is accessible even on expired trial."""
    uid = await _uid()
    factory = get_session_factory()
    async with factory() as session:
        sub = (
            await session.execute(
                select(Subscription).where(Subscription.user_id == uid)
            )
        ).scalar_one_or_none()
        if sub is None:
            sub = Subscription(user_id=uid, plan="trial", status="active")
            session.add(sub)
            await session.flush()
        sub.trial_ends_at = datetime.now(UTC) - timedelta(days=1)
        sub.stripe_subscription_id = None
        await session.commit()

    try:
        with patch(
            "career_agent.integrations.cognito.CognitoJwtVerifier.verify",
            new=AsyncMock(return_value=FAKE_CLAIMS),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get("/api/v1/interview-preps", headers=auth_headers)
        assert resp.status_code == 200
    finally:
        async with factory() as session:
            sub = (
                await session.execute(
                    select(Subscription).where(Subscription.user_id == uid)
                )
            ).scalar_one_or_none()
            if sub is not None:
                sub.trial_ends_at = datetime.now(UTC) + timedelta(days=30)
                await session.commit()
```

- [ ] **Step 3: Run the tests**

```bash
uv run pytest tests/integration/test_interview_prep_regenerate.py tests/integration/test_interview_prep_paywalled.py -v 2>&1 | tail -15
```

Expected: all 3 tests PASS.

- [ ] **Step 4: Checkpoint**

Checkpoint message: `feat(interview-prep): wire API, verify regenerate + paywall behavior`

---

## Task 12: Negotiation Playbook (Claude call via Appendix D.7)

**Files:**
- Create: `backend/src/career_agent/core/negotiation/__init__.py`
- Create: `backend/src/career_agent/core/negotiation/playbook.py`
- Create: `backend/tests/unit/test_negotiation_playbook_prompt.py`

- [ ] **Step 1: Create `backend/src/career_agent/core/negotiation/__init__.py`**

```python
"""Negotiation module — playbook generator + service orchestrator."""
```

- [ ] **Step 2: Create `backend/src/career_agent/core/negotiation/playbook.py`**

```python
"""NegotiationPlaybook — Claude call using parent spec Appendix D.7 prompt.

Market context is pulled from Claude's training data (e.g. "based on levels.fyi
and Glassdoor data for staff engineer in SF..."). No live market API in 2d.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from career_agent.config import get_settings
from career_agent.core.llm.anthropic_client import complete_with_cache
from career_agent.core.llm.errors import LLMParseError


_CACHEABLE_INSTRUCTIONS = """You are a salary negotiation coach. Generate a complete negotiation playbook for
an offer based on the candidate's situation and the market.

OUTPUT STRUCTURE:
- market_research: low/mid/high range + source notes + comparable roles
- counter_offer: target, minimum acceptable, equity ask, justification
- scripts: email template, call script, fallback positions, pitfalls
- Pull market data from levels.fyi, glassdoor, blind, and comparable role postings
  you know about. Cite sources in source_notes.
- Counter target should be 10-20% above the offer's base by default, adjusted for
  the candidate's experience and market signal.
- Scripts must use the offer details verbatim — don't substitute placeholder numbers.

OUTPUT JSON SCHEMA:
{
  "market_research": {
    "range_low": 180000,
    "range_mid": 205000,
    "range_high": 240000,
    "source_notes": "Based on levels.fyi and Glassdoor for {role} at {seniority} in {location}",
    "comparable_roles": ["Company A ~200k", "Company B ~215k"]
  },
  "counter_offer": {
    "target": 220000,
    "minimum_acceptable": 200000,
    "equity_ask": "0.15% or $30k additional RSU",
    "justification": "Based on market data and experience with distributed systems..."
  },
  "scripts": {
    "email_template": "Hi {recruiter},\\n\\nThanks so much for the offer...",
    "call_script": "Opening: '...'\\nCounter: '...'\\nIf pushback: '...'\\nClose: '...'",
    "fallback_positions": [
      "If salary is firm, ask for signing bonus of $X",
      "If total comp is firm, ask for earlier review cycle"
    ],
    "pitfalls": [
      "Don't accept the first counter without asking for 48 hours",
      "Don't negotiate over text — voice or video only"
    ]
  }
}

No prose outside JSON."""

_SYSTEM = "You are a salary negotiation coach. Output only strict JSON matching the schema."


@dataclass
class GeneratedPlaybook:
    market_research: dict[str, Any]
    counter_offer: dict[str, Any]
    scripts: dict[str, Any]
    usage: Any
    model: str


async def generate_negotiation_playbook(
    *,
    title: str,
    company: str,
    location: str | None,
    offer_details: dict[str, Any],
    current_comp: dict[str, Any] | None,
    experience_summary: str,
    feedback: str | None = None,
) -> GeneratedPlaybook:
    """One-shot Claude call. Uses prompt caching on the instructions block."""
    settings = get_settings()
    feedback_block = (
        f"\n\nUSER FEEDBACK FROM PRIOR ATTEMPT:\n{feedback}" if feedback else ""
    )
    user_block = (
        f"INPUT:\n"
        f"Role: {title} at {company}\n"
        f"Location: {location or 'not specified'}\n"
        f"Offer Details: {json.dumps(offer_details)}\n"
        f"Current Comp: {json.dumps(current_comp) if current_comp else 'not provided'}\n"
        f"Candidate Experience: {experience_summary}"
        f"{feedback_block}\n\n"
        "Generate a complete negotiation playbook. Output JSON only."
    )

    result = await complete_with_cache(
        system=_SYSTEM,
        cacheable_blocks=[_CACHEABLE_INSTRUCTIONS],
        user_block=user_block,
        model=settings.claude_model,
        max_tokens=3000,
        timeout_s=settings.llm_evaluation_timeout_s,
    )
    parsed = _parse(result.text)
    return GeneratedPlaybook(
        market_research=parsed["market_research"],
        counter_offer=parsed["counter_offer"],
        scripts=parsed["scripts"],
        usage=result.usage,
        model=result.model,
    )


def _parse(text: str) -> dict[str, Any]:
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.MULTILINE)
    try:
        data: dict[str, Any] = json.loads(raw)
    except json.JSONDecodeError as e:
        raise LLMParseError(
            "Negotiation playbook returned invalid JSON",
            provider="anthropic",
            details={"raw": raw[:500]},
        ) from e
    for required in ("market_research", "counter_offer", "scripts"):
        if required not in data:
            raise LLMParseError(
                f"Missing '{required}' field in playbook response",
                provider="anthropic",
            )
    return data
```

- [ ] **Step 3: Write the unit test**

`backend/tests/unit/test_negotiation_playbook_prompt.py`:

```python
import json

import pytest

from career_agent.core.llm.errors import LLMParseError
from career_agent.core.negotiation.playbook import generate_negotiation_playbook
from tests.fixtures.fake_anthropic import fake_anthropic


_FAKE_PLAYBOOK = json.dumps(
    {
        "market_research": {
            "range_low": 180000,
            "range_mid": 205000,
            "range_high": 240000,
            "source_notes": "Based on levels.fyi for staff engineer in SF",
            "comparable_roles": ["Stripe ~210k", "Airtable ~200k"],
        },
        "counter_offer": {
            "target": 225000,
            "minimum_acceptable": 205000,
            "equity_ask": "0.12% or $40k additional RSU",
            "justification": "Market data supports top of range for payments experience",
        },
        "scripts": {
            "email_template": "Hi Recruiter,\n\nThanks for the offer...",
            "call_script": "Opening: I'm excited...",
            "fallback_positions": ["Ask for signing bonus if base is firm"],
            "pitfalls": ["Don't accept first counter immediately"],
        },
    }
)


@pytest.mark.asyncio
async def test_playbook_generates_all_three_sections():
    with fake_anthropic({"INPUT:": _FAKE_PLAYBOOK}):
        result = await generate_negotiation_playbook(
            title="Senior Payments Engineer",
            company="Stripe",
            location="SF",
            offer_details={"base": 195000, "equity": "0.08%"},
            current_comp={"base": 170000},
            experience_summary="6 years payments backend",
        )
    assert result.market_research["range_mid"] == 205000
    assert result.counter_offer["target"] == 225000
    assert "email_template" in result.scripts


@pytest.mark.asyncio
async def test_playbook_raises_on_missing_market_research():
    bad_payload = json.dumps(
        {
            "counter_offer": {"target": 200000},
            "scripts": {"email_template": "x"},
        }
    )
    with fake_anthropic({"INPUT:": bad_payload}):
        with pytest.raises(LLMParseError):
            await generate_negotiation_playbook(
                title="t",
                company="c",
                location=None,
                offer_details={"base": 100000},
                current_comp=None,
                experience_summary="x",
            )


@pytest.mark.asyncio
async def test_playbook_passes_feedback_to_prompt():
    with fake_anthropic({"INPUT:": _FAKE_PLAYBOOK}) as stub:
        await generate_negotiation_playbook(
            title="t",
            company="c",
            location=None,
            offer_details={"base": 100000},
            current_comp=None,
            experience_summary="x",
            feedback="Counter is too aggressive, scale back",
        )
    sent = stub.calls[0]["messages"]
    user_text = ""
    for msg in sent:
        if msg["role"] == "user":
            content = msg["content"]
            if isinstance(content, list):
                for block in content:
                    if block.get("type") == "text":
                        user_text += block.get("text", "")
    assert "FEEDBACK" in user_text
    assert "too aggressive" in user_text
```

- [ ] **Step 4: Run the tests**

```bash
uv run pytest tests/unit/test_negotiation_playbook_prompt.py -v 2>&1 | tail -15
```

Expected: all 3 tests PASS.

- [ ] **Step 5: Checkpoint**

Checkpoint message: `feat(negotiation): add playbook generator using Appendix D.7 prompt`

---

## Task 13: Negotiation Service (Orchestrator) + Full Playbook Integration Test

**Files:**
- Create: `backend/src/career_agent/core/negotiation/service.py`
- Create: `backend/tests/integration/test_negotiation_full_playbook.py`

- [ ] **Step 1: Create `backend/src/career_agent/core/negotiation/service.py`**

```python
"""NegotiationService — orchestrator.

Flow:
  1. Load job + profile + existing application (if any)
  2. Call playbook generator
  3. Persist negotiations row
  4. If an application exists for (user, job), link its negotiation_id
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from career_agent.api.errors import AppError
from career_agent.core.llm.errors import LLMError
from career_agent.core.negotiation.playbook import generate_negotiation_playbook
from career_agent.models.application import Application
from career_agent.models.job import Job
from career_agent.models.negotiation import Negotiation
from career_agent.models.profile import Profile
from career_agent.services.usage_event import UsageEventService


@dataclass
class NegotiationContext:
    user_id: UUID
    session: AsyncSession
    usage: UsageEventService


class NegotiationService:
    def __init__(self, context: NegotiationContext):
        self.context = context

    async def create(
        self,
        *,
        job_id: UUID,
        offer_details: dict[str, Any],
        feedback: str | None = None,
    ) -> Negotiation:
        job = (
            await self.context.session.execute(
                select(Job).where(Job.id == job_id)
            )
        ).scalar_one_or_none()
        if job is None:
            raise AppError(404, "JOB_NOT_FOUND", "Job not found")

        profile = (
            await self.context.session.execute(
                select(Profile).where(Profile.user_id == self.context.user_id)
            )
        ).scalar_one_or_none()
        experience_summary = self._build_experience_summary(profile)
        current_comp = self._build_current_comp(profile)

        try:
            generated = await generate_negotiation_playbook(
                title=job.title,
                company=job.company or "the company",
                location=job.location,
                offer_details=offer_details,
                current_comp=current_comp,
                experience_summary=experience_summary,
                feedback=feedback,
            )
        except LLMError as e:
            raise AppError(
                502, "LLM_ERROR", f"Playbook generation failed: {e}"
            ) from e

        row = Negotiation(
            user_id=self.context.user_id,
            job_id=job_id,
            offer_details=offer_details,
            market_research=generated.market_research,
            counter_offer=generated.counter_offer,
            scripts=generated.scripts,
            model_used=generated.model,
            tokens_used=generated.usage.total_tokens,
        )
        self.context.session.add(row)
        await self.context.session.flush()

        # Link to existing application if any
        existing_app_stmt = select(Application).where(
            Application.user_id == self.context.user_id,
            Application.job_id == job_id,
        )
        app_row = (
            await self.context.session.execute(existing_app_stmt)
        ).scalar_one_or_none()
        if app_row is not None:
            app_row.negotiation_id = row.id
            await self.context.session.flush()

        await self.context.usage.record(
            user_id=self.context.user_id,
            event_type="negotiation_generate",
            module="negotiation",
            model=generated.model,
            tokens_used=generated.usage.total_tokens,
            cost_cents=generated.usage.cost_cents(generated.model),
        )

        return row

    async def regenerate(
        self,
        *,
        negotiation_id: UUID,
        feedback: str | None,
    ) -> Negotiation:
        """Create a new negotiation row with feedback-guided regeneration."""
        stmt = select(Negotiation).where(
            Negotiation.id == negotiation_id,
            Negotiation.user_id == self.context.user_id,
        )
        original = (
            await self.context.session.execute(stmt)
        ).scalar_one_or_none()
        if original is None:
            raise AppError(
                404, "NEGOTIATION_NOT_FOUND", "Negotiation not found"
            )
        return await self.create(
            job_id=original.job_id,
            offer_details=original.offer_details,
            feedback=feedback,
        )

    @staticmethod
    def _build_experience_summary(profile: Profile | None) -> str:
        if profile is None:
            return "Not provided"
        parsed = profile.parsed_resume_json or {}
        years = parsed.get("total_years_experience")
        skills = parsed.get("skills", [])[:10]
        parts: list[str] = []
        if years:
            parts.append(f"{years} years total experience")
        if skills:
            parts.append("skills: " + ", ".join(skills))
        return ". ".join(parts) if parts else "Not provided"

    @staticmethod
    def _build_current_comp(profile: Profile | None) -> dict[str, Any] | None:
        # Phase 1 profile doesn't store current comp; return None. Phase 5
        # may extend the profile schema to capture this.
        _ = profile
        return None
```

- [ ] **Step 2: Write the full-flow integration test**

`backend/tests/integration/test_negotiation_full_playbook.py`:

```python
import hashlib
import json
from uuid import UUID, uuid4

import pytest
from sqlalchemy import delete, select

from career_agent.core.negotiation.service import NegotiationContext, NegotiationService
from career_agent.db import get_session_factory
from career_agent.models.application import Application
from career_agent.models.job import Job
from career_agent.models.user import User
from career_agent.services.usage_event import UsageEventService
from tests.conftest import FAKE_CLAIMS
from tests.fixtures.fake_anthropic import fake_anthropic


_PLAYBOOK_JSON = json.dumps(
    {
        "market_research": {
            "range_low": 180000,
            "range_mid": 210000,
            "range_high": 240000,
            "source_notes": "levels.fyi",
            "comparable_roles": ["Stripe ~215k"],
        },
        "counter_offer": {
            "target": 225000,
            "minimum_acceptable": 205000,
            "equity_ask": "+$20k RSU",
            "justification": "market data + experience",
        },
        "scripts": {
            "email_template": "Thanks for the offer...",
            "call_script": "Opening: ...",
            "fallback_positions": ["signing bonus if base firm"],
            "pitfalls": ["don't accept first counter"],
        },
    }
)


async def _uid() -> UUID:
    factory = get_session_factory()
    async with factory() as s:
        r = await s.execute(select(User).where(User.cognito_sub == FAKE_CLAIMS["sub"]))
        return r.scalar_one().id


@pytest.mark.asyncio
async def test_negotiation_full_flow_with_application_linking(seed_profile):
    uid = await _uid()
    factory = get_session_factory()

    # Seed job + existing application for the user
    async with factory() as session:
        await session.execute(delete(Application).where(Application.user_id == uid))
        h = hashlib.sha256(f"neg-test-{uuid4()}".encode()).hexdigest()
        job = Job(
            content_hash=h,
            title="Senior Payments Engineer",
            description_md="Payments role",
            requirements_json={},
            source="manual",
            company="Stripe",
            location="SF",
        )
        session.add(job)
        await session.flush()
        app_row = Application(
            user_id=uid,
            job_id=job.id,
            status="offered",
        )
        session.add(app_row)
        await session.commit()
        jid = job.id
        app_id = app_row.id

    with fake_anthropic({"INPUT:": _PLAYBOOK_JSON}):
        async with factory() as session:
            usage = UsageEventService(session)
            ctx = NegotiationContext(user_id=uid, session=session, usage=usage)
            service = NegotiationService(ctx)
            neg = await service.create(
                job_id=jid,
                offer_details={"base": 195000, "equity": "0.08%", "location": "SF"},
            )
            await session.commit()

    # Playbook fields populated
    assert neg.market_research["range_mid"] == 210000
    assert neg.counter_offer["target"] == 225000
    assert "email_template" in neg.scripts

    # Application linked
    async with factory() as session:
        app_refreshed = (
            await session.execute(
                select(Application).where(Application.id == app_id)
            )
        ).scalar_one()
    assert app_refreshed.negotiation_id == neg.id


@pytest.mark.asyncio
async def test_negotiation_without_application_still_succeeds(seed_profile):
    """If no application exists for (user, job), negotiation is still created."""
    uid = await _uid()
    factory = get_session_factory()

    async with factory() as session:
        await session.execute(delete(Application).where(Application.user_id == uid))
        h = hashlib.sha256(f"neg-no-app-{uuid4()}".encode()).hexdigest()
        job = Job(
            content_hash=h,
            title="Staff Engineer",
            description_md="Staff role",
            requirements_json={},
            source="manual",
            company="Acme",
        )
        session.add(job)
        await session.commit()
        jid = job.id

    with fake_anthropic({"INPUT:": _PLAYBOOK_JSON}):
        async with factory() as session:
            usage = UsageEventService(session)
            ctx = NegotiationContext(user_id=uid, session=session, usage=usage)
            neg = await NegotiationService(ctx).create(
                job_id=jid,
                offer_details={"base": 200000},
            )
            await session.commit()

    assert neg is not None
    assert neg.job_id == jid
```

- [ ] **Step 3: Run the tests**

```bash
uv run pytest tests/integration/test_negotiation_full_playbook.py -v 2>&1 | tail -15
```

Expected: both tests PASS.

- [ ] **Step 4: Checkpoint**

Checkpoint message: `feat(negotiation): add service orchestrator with application auto-linking`

---

## Task 14: Negotiation CRUD Helpers

**Files:**
- Create: `backend/src/career_agent/services/negotiation.py`

- [ ] **Step 1: Create `backend/src/career_agent/services/negotiation.py`**

```python
"""Negotiation CRUD helpers — thin wrapper for API layer."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from career_agent.models.negotiation import Negotiation


async def get_for_user(
    session: AsyncSession, user_id: UUID, negotiation_id: UUID
) -> Negotiation | None:
    stmt = select(Negotiation).where(
        Negotiation.id == negotiation_id,
        Negotiation.user_id == user_id,
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def list_for_user(
    session: AsyncSession, user_id: UUID, *, limit: int = 20
) -> list[Negotiation]:
    stmt = (
        select(Negotiation)
        .where(Negotiation.user_id == user_id)
        .order_by(Negotiation.created_at.desc())
        .limit(limit)
    )
    return list((await session.execute(stmt)).scalars().all())
```

- [ ] **Step 2: Verify import**

```bash
uv run python -c "from career_agent.services.negotiation import get_for_user, list_for_user; print('ok')"
```

Expected: `ok`

- [ ] **Step 3: Checkpoint**

Checkpoint message: `feat(negotiation): add CRUD helpers`

---

## Task 15: Negotiations API — POST Create + List + Get + Offer Validation

**Files:**
- Create: `backend/src/career_agent/api/negotiations.py`
- Modify: `backend/src/career_agent/main.py`
- Create: `backend/tests/integration/test_negotiation_requires_offer_details.py`

- [ ] **Step 1: Create `backend/src/career_agent/api/negotiations.py`**

```python
"""Negotiations API."""
from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Query

from career_agent.api.deps import CurrentDbUser, DbSession, EntitledDbUser
from career_agent.api.errors import AppError
from career_agent.core.negotiation.service import (
    NegotiationContext,
    NegotiationService,
)
from career_agent.schemas.negotiation import (
    NegotiationCreate,
    NegotiationOut,
    NegotiationRegenerate,
)
from career_agent.services.negotiation import get_for_user, list_for_user
from career_agent.services.usage_event import UsageEventService

router = APIRouter(prefix="/negotiations", tags=["negotiations"])


@router.post("", status_code=201)
async def create_negotiation(
    payload: NegotiationCreate,
    user: EntitledDbUser,
    session: DbSession,
) -> dict[str, Any]:
    usage = UsageEventService(session)
    ctx = NegotiationContext(user_id=user.id, session=session, usage=usage)
    service = NegotiationService(ctx)
    neg = await service.create(
        job_id=payload.job_id,
        offer_details=payload.offer_details.model_dump(exclude_none=False),
    )
    await session.commit()
    return {"data": NegotiationOut.model_validate(neg).model_dump(mode="json")}


@router.get("")
async def list_negotiations(
    user: CurrentDbUser,
    session: DbSession,
    limit: int = Query(default=20, ge=1, le=100),
) -> dict[str, Any]:
    rows = await list_for_user(session, user.id, limit=limit)
    return {
        "data": [NegotiationOut.model_validate(r).model_dump(mode="json") for r in rows]
    }


@router.get("/{negotiation_id}")
async def get_negotiation(
    negotiation_id: UUID,
    user: CurrentDbUser,
    session: DbSession,
) -> dict[str, Any]:
    row = await get_for_user(session, user.id, negotiation_id)
    if row is None:
        raise AppError(404, "NEGOTIATION_NOT_FOUND", "Negotiation not found")
    return {"data": NegotiationOut.model_validate(row).model_dump(mode="json")}


@router.post("/{negotiation_id}/regenerate", status_code=201)
async def regenerate_negotiation(
    negotiation_id: UUID,
    payload: NegotiationRegenerate,
    user: EntitledDbUser,
    session: DbSession,
) -> dict[str, Any]:
    usage = UsageEventService(session)
    ctx = NegotiationContext(user_id=user.id, session=session, usage=usage)
    service = NegotiationService(ctx)
    neg = await service.regenerate(
        negotiation_id=negotiation_id, feedback=payload.feedback
    )
    await session.commit()
    return {"data": NegotiationOut.model_validate(neg).model_dump(mode="json")}
```

- [ ] **Step 2: Register router in `main.py`**

```python
from career_agent.api import negotiations
app.include_router(negotiations.router, prefix="/api/v1")
```

- [ ] **Step 3: Write the offer-validation test**

`backend/tests/integration/test_negotiation_requires_offer_details.py`:

```python
import hashlib
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from career_agent.db import get_session_factory
from career_agent.main import app
from career_agent.models.job import Job
from tests.conftest import FAKE_CLAIMS


async def _seed_job() -> str:
    factory = get_session_factory()
    async with factory() as session:
        h = hashlib.sha256(f"neg-offer-{uuid4()}".encode()).hexdigest()
        job = Job(
            content_hash=h,
            title="Test",
            description_md="x",
            requirements_json={},
            source="manual",
        )
        session.add(job)
        await session.commit()
        return str(job.id)


@pytest.mark.asyncio
async def test_negotiation_rejects_missing_offer_details(auth_headers, seed_profile):
    jid = await _seed_job()

    with patch(
        "career_agent.integrations.cognito.CognitoJwtVerifier.verify",
        new=AsyncMock(return_value=FAKE_CLAIMS),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/v1/negotiations",
                json={"job_id": jid},  # missing offer_details
                headers=auth_headers,
            )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_negotiation_rejects_base_below_zero(auth_headers, seed_profile):
    jid = await _seed_job()

    with patch(
        "career_agent.integrations.cognito.CognitoJwtVerifier.verify",
        new=AsyncMock(return_value=FAKE_CLAIMS),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/v1/negotiations",
                json={
                    "job_id": jid,
                    "offer_details": {"base": -1},
                },
                headers=auth_headers,
            )
    assert resp.status_code == 422
```

- [ ] **Step 4: Run the tests**

```bash
uv run pytest tests/integration/test_negotiation_requires_offer_details.py -v 2>&1 | tail -15
```

Expected: both tests PASS.

- [ ] **Step 5: Checkpoint**

Checkpoint message: `feat(api): add negotiations API — create/list/get/regenerate with validation`

---

## Task 16: Negotiation Regenerate + Paywall Integration Tests

**Files:**
- Create: `backend/tests/integration/test_negotiation_regenerate.py`
- Create: `backend/tests/integration/test_negotiation_paywalled.py`

- [ ] **Step 1: Write the regenerate test**

`backend/tests/integration/test_negotiation_regenerate.py`:

```python
import hashlib
import json
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from career_agent.db import get_session_factory
from career_agent.main import app
from career_agent.models.job import Job
from career_agent.models.negotiation import Negotiation
from career_agent.models.user import User
from tests.conftest import FAKE_CLAIMS
from tests.fixtures.fake_anthropic import fake_anthropic


def _playbook(target: int) -> str:
    return json.dumps(
        {
            "market_research": {
                "range_low": 180000,
                "range_mid": 210000,
                "range_high": 240000,
                "source_notes": "x",
                "comparable_roles": [],
            },
            "counter_offer": {
                "target": target,
                "minimum_acceptable": 200000,
                "equity_ask": "x",
                "justification": "x",
            },
            "scripts": {
                "email_template": "x",
                "call_script": "x",
                "fallback_positions": [],
                "pitfalls": [],
            },
        }
    )


async def _uid() -> UUID:
    factory = get_session_factory()
    async with factory() as s:
        r = await s.execute(select(User).where(User.cognito_sub == FAKE_CLAIMS["sub"]))
        return r.scalar_one().id


async def _seed_job() -> str:
    factory = get_session_factory()
    async with factory() as session:
        h = hashlib.sha256(f"neg-regen-{uuid4()}".encode()).hexdigest()
        job = Job(
            content_hash=h,
            title="Staff Engineer",
            description_md="x",
            requirements_json={},
            source="manual",
            company="Acme",
            location="Remote",
        )
        session.add(job)
        await session.commit()
        return str(job.id)


@pytest.mark.asyncio
async def test_regenerate_creates_new_row(auth_headers, seed_profile):
    jid = await _seed_job()
    uid = await _uid()

    with (
        patch(
            "career_agent.integrations.cognito.CognitoJwtVerifier.verify",
            new=AsyncMock(return_value=FAKE_CLAIMS),
        ),
        fake_anthropic({"INPUT:": _playbook(225000)}),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            r1 = await client.post(
                "/api/v1/negotiations",
                json={
                    "job_id": jid,
                    "offer_details": {"base": 195000},
                },
                headers=auth_headers,
            )
    assert r1.status_code == 201
    v1_id = r1.json()["data"]["id"]

    with (
        patch(
            "career_agent.integrations.cognito.CognitoJwtVerifier.verify",
            new=AsyncMock(return_value=FAKE_CLAIMS),
        ),
        fake_anthropic({"INPUT:": _playbook(215000)}),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            r2 = await client.post(
                f"/api/v1/negotiations/{v1_id}/regenerate",
                json={"feedback": "Counter was too aggressive, scale back"},
                headers=auth_headers,
            )
    assert r2.status_code == 201
    v2_id = r2.json()["data"]["id"]
    assert v2_id != v1_id

    # Both rows exist
    factory = get_session_factory()
    async with factory() as session:
        rows = (
            (
                await session.execute(
                    select(Negotiation).where(Negotiation.user_id == uid)
                )
            )
            .scalars()
            .all()
        )
    user_row_ids = {str(r.id) for r in rows}
    assert v1_id in user_row_ids
    assert v2_id in user_row_ids
```

- [ ] **Step 2: Write the paywall test**

`backend/tests/integration/test_negotiation_paywalled.py`:

```python
import hashlib
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from career_agent.db import get_session_factory
from career_agent.main import app
from career_agent.models.job import Job
from career_agent.models.subscription import Subscription
from career_agent.models.user import User
from tests.conftest import FAKE_CLAIMS


async def _uid() -> UUID:
    factory = get_session_factory()
    async with factory() as s:
        r = await s.execute(select(User).where(User.cognito_sub == FAKE_CLAIMS["sub"]))
        return r.scalar_one().id


@pytest.mark.asyncio
async def test_negotiation_post_requires_entitlement(auth_headers, seed_profile):
    uid = await _uid()
    factory = get_session_factory()

    # Seed job
    async with factory() as session:
        h = hashlib.sha256(f"neg-pw-{uuid4()}".encode()).hexdigest()
        job = Job(
            content_hash=h,
            title="Test",
            description_md="x",
            requirements_json={},
            source="manual",
        )
        session.add(job)
        await session.commit()
        jid = job.id

    # Expire trial
    async with factory() as session:
        sub = (
            await session.execute(
                select(Subscription).where(Subscription.user_id == uid)
            )
        ).scalar_one_or_none()
        if sub is None:
            sub = Subscription(user_id=uid, plan="trial", status="active")
            session.add(sub)
            await session.flush()
        sub.trial_ends_at = datetime.now(UTC) - timedelta(days=1)
        sub.stripe_subscription_id = None
        await session.commit()

    try:
        with patch(
            "career_agent.integrations.cognito.CognitoJwtVerifier.verify",
            new=AsyncMock(return_value=FAKE_CLAIMS),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/v1/negotiations",
                    json={
                        "job_id": str(jid),
                        "offer_details": {"base": 200000},
                    },
                    headers=auth_headers,
                )
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "TRIAL_EXPIRED"
    finally:
        async with factory() as session:
            sub = (
                await session.execute(
                    select(Subscription).where(Subscription.user_id == uid)
                )
            ).scalar_one_or_none()
            if sub is not None:
                sub.trial_ends_at = datetime.now(UTC) + timedelta(days=30)
                await session.commit()
```

- [ ] **Step 3: Run the tests**

```bash
uv run pytest tests/integration/test_negotiation_regenerate.py tests/integration/test_negotiation_paywalled.py -v 2>&1 | tail -15
```

Expected: both tests PASS.

- [ ] **Step 4: Checkpoint**

Checkpoint message: `feat(negotiation): verify regenerate + paywall behavior`

---

## Task 17: Star Stories CRUD API (Phase 1 Backfill)

**Files:**
- Create: `backend/src/career_agent/services/star_story.py`
- Create: `backend/src/career_agent/api/star_stories.py`
- Modify: `backend/src/career_agent/main.py`
- Create: `backend/tests/integration/test_star_stories_crud.py`
- Create: `backend/tests/integration/test_star_stories_not_paywalled.py`

- [ ] **Step 1: Create `backend/src/career_agent/services/star_story.py`**

```python
"""Star story CRUD helpers — Phase 1 model, Phase 2d API."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from career_agent.models.star_story import StarStory
from career_agent.schemas.star_story import StarStoryCreate, StarStoryUpdate


class StarStoryService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_for_user(
        self, user_id: UUID, *, tags: list[str] | None = None
    ) -> list[StarStory]:
        stmt = (
            select(StarStory)
            .where(StarStory.user_id == user_id)
            .order_by(StarStory.created_at.desc())
        )
        rows = list((await self.session.execute(stmt)).scalars().all())
        if tags:
            rows = [
                r
                for r in rows
                if r.tags and any(t in r.tags for t in tags)
            ]
        return rows

    async def get(self, user_id: UUID, story_id: UUID) -> StarStory | None:
        stmt = select(StarStory).where(
            StarStory.id == story_id,
            StarStory.user_id == user_id,
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def create(
        self, user_id: UUID, payload: StarStoryCreate
    ) -> StarStory:
        row = StarStory(
            user_id=user_id,
            title=payload.title,
            situation=payload.situation,
            task=payload.task,
            action=payload.action,
            result=payload.result,
            reflection=payload.reflection,
            tags=payload.tags,
            source="user_created",
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def update(
        self, user_id: UUID, story_id: UUID, payload: StarStoryUpdate
    ) -> StarStory | None:
        row = await self.get(user_id, story_id)
        if row is None:
            return None
        data = payload.model_dump(exclude_unset=True)
        for k, v in data.items():
            setattr(row, k, v)
        await self.session.flush()
        return row

    async def delete(self, user_id: UUID, story_id: UUID) -> bool:
        row = await self.get(user_id, story_id)
        if row is None:
            return False
        await self.session.delete(row)
        await self.session.flush()
        return True
```

- [ ] **Step 2: Create `backend/src/career_agent/api/star_stories.py`**

```python
"""Star stories API — non-paywalled CRUD.

Users manage their own life/career data regardless of billing state.
Consistent with applications in Phase 2c.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Query

from career_agent.api.deps import CurrentDbUser, DbSession
from career_agent.api.errors import AppError
from career_agent.schemas.star_story import (
    StarStoryCreate,
    StarStoryOut,
    StarStoryUpdate,
)
from career_agent.services.star_story import StarStoryService

router = APIRouter(prefix="/star-stories", tags=["star-stories"])


@router.get("")
async def list_star_stories(
    user: CurrentDbUser,
    session: DbSession,
    tags: str | None = Query(default=None, description="Comma-separated tag filter"),
) -> dict[str, Any]:
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None
    rows = await StarStoryService(session).list_for_user(user.id, tags=tag_list)
    return {
        "data": [StarStoryOut.model_validate(r).model_dump(mode="json") for r in rows]
    }


@router.post("", status_code=201)
async def create_star_story(
    payload: StarStoryCreate,
    user: CurrentDbUser,
    session: DbSession,
) -> dict[str, Any]:
    row = await StarStoryService(session).create(user.id, payload)
    await session.commit()
    return {"data": StarStoryOut.model_validate(row).model_dump(mode="json")}


@router.get("/{story_id}")
async def get_star_story(
    story_id: UUID,
    user: CurrentDbUser,
    session: DbSession,
) -> dict[str, Any]:
    row = await StarStoryService(session).get(user.id, story_id)
    if row is None:
        raise AppError(404, "STAR_STORY_NOT_FOUND", "Star story not found")
    return {"data": StarStoryOut.model_validate(row).model_dump(mode="json")}


@router.put("/{story_id}")
async def update_star_story(
    story_id: UUID,
    payload: StarStoryUpdate,
    user: CurrentDbUser,
    session: DbSession,
) -> dict[str, Any]:
    row = await StarStoryService(session).update(user.id, story_id, payload)
    if row is None:
        raise AppError(404, "STAR_STORY_NOT_FOUND", "Star story not found")
    await session.commit()
    return {"data": StarStoryOut.model_validate(row).model_dump(mode="json")}


@router.delete("/{story_id}", status_code=204)
async def delete_star_story(
    story_id: UUID,
    user: CurrentDbUser,
    session: DbSession,
) -> None:
    ok = await StarStoryService(session).delete(user.id, story_id)
    if not ok:
        raise AppError(404, "STAR_STORY_NOT_FOUND", "Star story not found")
    await session.commit()
```

- [ ] **Step 3: Register in `main.py`**

```python
from career_agent.api import star_stories
app.include_router(star_stories.router, prefix="/api/v1")
```

- [ ] **Step 4: Write the CRUD test**

`backend/tests/integration/test_star_stories_crud.py`:

```python
from unittest.mock import AsyncMock, patch
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select

from career_agent.db import get_session_factory
from career_agent.main import app
from career_agent.models.star_story import StarStory
from career_agent.models.user import User
from tests.conftest import FAKE_CLAIMS


async def _uid() -> UUID:
    factory = get_session_factory()
    async with factory() as s:
        r = await s.execute(select(User).where(User.cognito_sub == FAKE_CLAIMS["sub"]))
        return r.scalar_one().id


async def _clear() -> None:
    uid = await _uid()
    factory = get_session_factory()
    async with factory() as session:
        await session.execute(delete(StarStory).where(StarStory.user_id == uid))
        await session.commit()


@pytest.mark.asyncio
async def test_star_stories_full_crud(auth_headers, seed_profile):
    await _clear()

    with patch(
        "career_agent.integrations.cognito.CognitoJwtVerifier.verify",
        new=AsyncMock(return_value=FAKE_CLAIMS),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # Create
            r1 = await client.post(
                "/api/v1/star-stories",
                json={
                    "title": "Led payments migration",
                    "situation": "Legacy monolith",
                    "task": "Migrate",
                    "action": "Strangler pattern",
                    "result": "Zero downtime",
                    "reflection": "Earlier observability",
                    "tags": ["leadership", "migration"],
                },
                headers=auth_headers,
            )
            assert r1.status_code == 201
            story_id = r1.json()["data"]["id"]
            assert r1.json()["data"]["source"] == "user_created"

            # Get
            r2 = await client.get(
                f"/api/v1/star-stories/{story_id}", headers=auth_headers
            )
            assert r2.status_code == 200
            assert r2.json()["data"]["title"] == "Led payments migration"

            # List with tag filter
            r3 = await client.get(
                "/api/v1/star-stories?tags=leadership", headers=auth_headers
            )
            assert r3.status_code == 200
            ids = [s["id"] for s in r3.json()["data"]]
            assert story_id in ids

            # List with non-matching tag
            r4 = await client.get(
                "/api/v1/star-stories?tags=nonexistent", headers=auth_headers
            )
            assert r4.status_code == 200
            assert len(r4.json()["data"]) == 0

            # Update
            r5 = await client.put(
                f"/api/v1/star-stories/{story_id}",
                json={"reflection": "Updated reflection"},
                headers=auth_headers,
            )
            assert r5.status_code == 200
            assert r5.json()["data"]["reflection"] == "Updated reflection"

            # Delete
            r6 = await client.delete(
                f"/api/v1/star-stories/{story_id}", headers=auth_headers
            )
            assert r6.status_code == 204

            r7 = await client.get(
                f"/api/v1/star-stories/{story_id}", headers=auth_headers
            )
            assert r7.status_code == 404
```

- [ ] **Step 5: Write the non-paywall test**

`backend/tests/integration/test_star_stories_not_paywalled.py`:

```python
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select

from career_agent.db import get_session_factory
from career_agent.main import app
from career_agent.models.star_story import StarStory
from career_agent.models.subscription import Subscription
from career_agent.models.user import User
from tests.conftest import FAKE_CLAIMS


async def _uid() -> UUID:
    factory = get_session_factory()
    async with factory() as s:
        r = await s.execute(select(User).where(User.cognito_sub == FAKE_CLAIMS["sub"]))
        return r.scalar_one().id


@pytest.mark.asyncio
async def test_star_stories_crud_survives_expired_trial(auth_headers, seed_profile):
    uid = await _uid()
    factory = get_session_factory()

    async with factory() as session:
        await session.execute(delete(StarStory).where(StarStory.user_id == uid))
        await session.commit()

    # Expire trial
    async with factory() as session:
        sub = (
            await session.execute(
                select(Subscription).where(Subscription.user_id == uid)
            )
        ).scalar_one_or_none()
        if sub is None:
            sub = Subscription(user_id=uid, plan="trial", status="active")
            session.add(sub)
            await session.flush()
        sub.trial_ends_at = datetime.now(UTC) - timedelta(days=1)
        sub.stripe_subscription_id = None
        await session.commit()

    try:
        with patch(
            "career_agent.integrations.cognito.CognitoJwtVerifier.verify",
            new=AsyncMock(return_value=FAKE_CLAIMS),
        ):
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/v1/star-stories",
                    json={
                        "title": "Test story",
                        "situation": "x",
                        "task": "x",
                        "action": "x",
                        "result": "x",
                    },
                    headers=auth_headers,
                )
        # Not paywalled — must be 201, not 403
        assert resp.status_code == 201
    finally:
        async with factory() as session:
            sub = (
                await session.execute(
                    select(Subscription).where(Subscription.user_id == uid)
                )
            ).scalar_one_or_none()
            if sub is not None:
                sub.trial_ends_at = datetime.now(UTC) + timedelta(days=30)
                await session.commit()
```

- [ ] **Step 6: Run the tests**

```bash
uv run pytest tests/integration/test_star_stories_crud.py tests/integration/test_star_stories_not_paywalled.py -v 2>&1 | tail -15
```

Expected: both test modules PASS.

- [ ] **Step 7: Checkpoint**

Checkpoint message: `feat(api): add star stories CRUD (Phase 1 backfill, non-paywalled)`

---

## Task 18: Feedback Endpoints on All 4 LLM-Generated Resources

**Files:**
- Create: `backend/src/career_agent/api/feedback.py`
- Modify: `backend/src/career_agent/main.py`
- Create: `backend/tests/integration/test_feedback_evaluation.py`
- Create: `backend/tests/integration/test_feedback_cv_output.py`
- Create: `backend/tests/integration/test_feedback_interview_prep.py`
- Create: `backend/tests/integration/test_feedback_negotiation.py`
- Create: `backend/tests/integration/test_feedback_ownership_cross_user.py`

**Note on routing:** rather than defining 4 separate routers (one per resource) or editing the existing `evaluations.py` / `cv_outputs.py`, we define all 4 feedback endpoints in a single new `api/feedback.py` module mounted on 4 different parent paths. This keeps the ownership logic in one place.

- [ ] **Step 1: Create `backend/src/career_agent/api/feedback.py`**

```python
"""Feedback endpoints for all 4 LLM-generated resources.

Exposes:
  POST /api/v1/evaluations/:id/feedback
  POST /api/v1/cv-outputs/:id/feedback
  POST /api/v1/interview-preps/:id/feedback
  POST /api/v1/negotiations/:id/feedback

All 4 routes share the same handler template with a resource_type
parameter. Ownership validation happens inside FeedbackService via the
per-resource dispatch dict.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter

from career_agent.api.deps import CurrentDbUser, DbSession
from career_agent.api.errors import AppError
from career_agent.core.feedback.service import (
    FeedbackResourceNotFound,
    FeedbackService,
    InvalidFeedback,
)
from career_agent.schemas.feedback import FeedbackCreate, FeedbackOut

router = APIRouter(tags=["feedback"])


async def _record_feedback(
    *,
    resource_type: str,
    resource_id: UUID,
    payload: FeedbackCreate,
    user: Any,
    session: Any,
) -> dict[str, Any]:
    service = FeedbackService(session)
    try:
        row = await service.record(
            user_id=user.id,
            resource_type=resource_type,
            resource_id=resource_id,
            rating=payload.rating,
            correction_notes=payload.correction_notes,
        )
    except InvalidFeedback as e:
        raise AppError(422, "INVALID_FEEDBACK", str(e)) from e
    except FeedbackResourceNotFound as e:
        raise AppError(404, "FEEDBACK_RESOURCE_NOT_FOUND", str(e)) from e
    await session.commit()
    return {"data": FeedbackOut.model_validate(row).model_dump(mode="json")}


@router.post("/evaluations/{resource_id}/feedback", status_code=201)
async def feedback_evaluation(
    resource_id: UUID,
    payload: FeedbackCreate,
    user: CurrentDbUser,
    session: DbSession,
) -> dict[str, Any]:
    return await _record_feedback(
        resource_type="evaluation",
        resource_id=resource_id,
        payload=payload,
        user=user,
        session=session,
    )


@router.post("/cv-outputs/{resource_id}/feedback", status_code=201)
async def feedback_cv_output(
    resource_id: UUID,
    payload: FeedbackCreate,
    user: CurrentDbUser,
    session: DbSession,
) -> dict[str, Any]:
    return await _record_feedback(
        resource_type="cv_output",
        resource_id=resource_id,
        payload=payload,
        user=user,
        session=session,
    )


@router.post("/interview-preps/{resource_id}/feedback", status_code=201)
async def feedback_interview_prep(
    resource_id: UUID,
    payload: FeedbackCreate,
    user: CurrentDbUser,
    session: DbSession,
) -> dict[str, Any]:
    return await _record_feedback(
        resource_type="interview_prep",
        resource_id=resource_id,
        payload=payload,
        user=user,
        session=session,
    )


@router.post("/negotiations/{resource_id}/feedback", status_code=201)
async def feedback_negotiation(
    resource_id: UUID,
    payload: FeedbackCreate,
    user: CurrentDbUser,
    session: DbSession,
) -> dict[str, Any]:
    return await _record_feedback(
        resource_type="negotiation",
        resource_id=resource_id,
        payload=payload,
        user=user,
        session=session,
    )
```

- [ ] **Step 2: Register router in `main.py`**

```python
from career_agent.api import feedback
app.include_router(feedback.router, prefix="/api/v1")
```

**Note:** the feedback router uses non-prefixed routes (full paths like `/evaluations/{id}/feedback`). Combined with the `/api/v1` prefix at mount time, the final paths are `/api/v1/evaluations/{id}/feedback` etc. — matching the parent spec.

- [ ] **Step 3: Write the 4 resource-specific feedback tests**

`backend/tests/integration/test_feedback_evaluation.py`:

```python
import hashlib
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from career_agent.db import get_session_factory
from career_agent.main import app
from career_agent.models.evaluation import Evaluation
from career_agent.models.job import Job
from career_agent.models.user import User
from tests.conftest import FAKE_CLAIMS


async def _uid() -> UUID:
    factory = get_session_factory()
    async with factory() as s:
        r = await s.execute(select(User).where(User.cognito_sub == FAKE_CLAIMS["sub"]))
        return r.scalar_one().id


async def _seed_evaluation(uid: UUID) -> UUID:
    factory = get_session_factory()
    async with factory() as session:
        h = hashlib.sha256(f"fb-ev-{uuid4()}".encode()).hexdigest()
        job = Job(
            content_hash=h, title="x", description_md="x",
            requirements_json={}, source="manual",
        )
        session.add(job)
        await session.flush()
        ev = Evaluation(
            user_id=uid, job_id=job.id, overall_grade="B",
            dimension_scores={}, reasoning="", match_score=0.7,
            recommendation="worth_exploring", model_used="test", cached=False,
        )
        session.add(ev)
        await session.commit()
        return ev.id


@pytest.mark.asyncio
async def test_feedback_evaluation_happy_path(auth_headers, seed_profile):
    uid = await _uid()
    eid = await _seed_evaluation(uid)
    with patch(
        "career_agent.integrations.cognito.CognitoJwtVerifier.verify",
        new=AsyncMock(return_value=FAKE_CLAIMS),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            r = await client.post(
                f"/api/v1/evaluations/{eid}/feedback",
                json={"rating": 4, "correction_notes": "Pretty good"},
                headers=auth_headers,
            )
    assert r.status_code == 201
    body = r.json()["data"]
    assert body["rating"] == 4
    assert body["resource_type"] == "evaluation"


@pytest.mark.asyncio
async def test_feedback_evaluation_rejects_out_of_range(auth_headers, seed_profile):
    uid = await _uid()
    eid = await _seed_evaluation(uid)
    with patch(
        "career_agent.integrations.cognito.CognitoJwtVerifier.verify",
        new=AsyncMock(return_value=FAKE_CLAIMS),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            r = await client.post(
                f"/api/v1/evaluations/{eid}/feedback",
                json={"rating": 6},
                headers=auth_headers,
            )
    # Pydantic schema rejects this before reaching the service (422)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_feedback_evaluation_upserts_on_repeat(auth_headers, seed_profile):
    uid = await _uid()
    eid = await _seed_evaluation(uid)
    with patch(
        "career_agent.integrations.cognito.CognitoJwtVerifier.verify",
        new=AsyncMock(return_value=FAKE_CLAIMS),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            r1 = await client.post(
                f"/api/v1/evaluations/{eid}/feedback",
                json={"rating": 3},
                headers=auth_headers,
            )
            assert r1.status_code == 201
            id1 = r1.json()["data"]["id"]

            r2 = await client.post(
                f"/api/v1/evaluations/{eid}/feedback",
                json={"rating": 5, "correction_notes": "better now"},
                headers=auth_headers,
            )
            assert r2.status_code == 201
            id2 = r2.json()["data"]["id"]

    # Same row (upsert), updated rating
    assert id1 == id2
    assert r2.json()["data"]["rating"] == 5
```

`backend/tests/integration/test_feedback_cv_output.py`:

```python
import hashlib
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from career_agent.db import get_session_factory
from career_agent.main import app
from career_agent.models.cv_output import CvOutput
from career_agent.models.job import Job
from career_agent.models.user import User
from tests.conftest import FAKE_CLAIMS


async def _uid() -> UUID:
    factory = get_session_factory()
    async with factory() as s:
        r = await s.execute(select(User).where(User.cognito_sub == FAKE_CLAIMS["sub"]))
        return r.scalar_one().id


@pytest.mark.asyncio
async def test_feedback_cv_output_happy_path(auth_headers, seed_profile):
    uid = await _uid()
    factory = get_session_factory()
    async with factory() as session:
        h = hashlib.sha256(f"fb-cv-{uuid4()}".encode()).hexdigest()
        job = Job(
            content_hash=h, title="x", description_md="x",
            requirements_json={}, source="manual",
        )
        session.add(job)
        await session.flush()
        cv = CvOutput(
            user_id=uid, job_id=job.id,
            tailored_md="# Jane", pdf_s3_key=f"cv/{uid}/x.pdf",
            changes_summary="ok", model_used="test",
        )
        session.add(cv)
        await session.commit()
        cvid = cv.id

    with patch(
        "career_agent.integrations.cognito.CognitoJwtVerifier.verify",
        new=AsyncMock(return_value=FAKE_CLAIMS),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            r = await client.post(
                f"/api/v1/cv-outputs/{cvid}/feedback",
                json={"rating": 5},
                headers=auth_headers,
            )
    assert r.status_code == 201
    assert r.json()["data"]["resource_type"] == "cv_output"
```

`backend/tests/integration/test_feedback_interview_prep.py`:

```python
from unittest.mock import AsyncMock, patch
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from career_agent.db import get_session_factory
from career_agent.main import app
from career_agent.models.interview_prep import InterviewPrep
from career_agent.models.user import User
from tests.conftest import FAKE_CLAIMS


async def _uid() -> UUID:
    factory = get_session_factory()
    async with factory() as s:
        r = await s.execute(select(User).where(User.cognito_sub == FAKE_CLAIMS["sub"]))
        return r.scalar_one().id


@pytest.mark.asyncio
async def test_feedback_interview_prep_happy_path(auth_headers, seed_profile):
    uid = await _uid()
    factory = get_session_factory()
    async with factory() as session:
        prep = InterviewPrep(
            user_id=uid,
            custom_role="Staff Engineer",
            questions=[{"question": "x", "category": "behavioral"}],
            red_flag_questions=None,
            model_used="test",
            tokens_used=100,
        )
        session.add(prep)
        await session.commit()
        pid = prep.id

    with patch(
        "career_agent.integrations.cognito.CognitoJwtVerifier.verify",
        new=AsyncMock(return_value=FAKE_CLAIMS),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            r = await client.post(
                f"/api/v1/interview-preps/{pid}/feedback",
                json={"rating": 4},
                headers=auth_headers,
            )
    assert r.status_code == 201
    assert r.json()["data"]["resource_type"] == "interview_prep"
```

`backend/tests/integration/test_feedback_negotiation.py`:

```python
import hashlib
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from career_agent.db import get_session_factory
from career_agent.main import app
from career_agent.models.job import Job
from career_agent.models.negotiation import Negotiation
from career_agent.models.user import User
from tests.conftest import FAKE_CLAIMS


async def _uid() -> UUID:
    factory = get_session_factory()
    async with factory() as s:
        r = await s.execute(select(User).where(User.cognito_sub == FAKE_CLAIMS["sub"]))
        return r.scalar_one().id


@pytest.mark.asyncio
async def test_feedback_negotiation_happy_path(auth_headers, seed_profile):
    uid = await _uid()
    factory = get_session_factory()
    async with factory() as session:
        h = hashlib.sha256(f"fb-neg-{uuid4()}".encode()).hexdigest()
        job = Job(
            content_hash=h, title="x", description_md="x",
            requirements_json={}, source="manual",
        )
        session.add(job)
        await session.flush()
        neg = Negotiation(
            user_id=uid, job_id=job.id,
            offer_details={"base": 200000},
            market_research={"range_low": 180000, "range_mid": 210000, "range_high": 240000},
            counter_offer={"target": 225000},
            scripts={"email_template": "x"},
            model_used="test",
            tokens_used=100,
        )
        session.add(neg)
        await session.commit()
        nid = neg.id

    with patch(
        "career_agent.integrations.cognito.CognitoJwtVerifier.verify",
        new=AsyncMock(return_value=FAKE_CLAIMS),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            r = await client.post(
                f"/api/v1/negotiations/{nid}/feedback",
                json={"rating": 5, "correction_notes": "Excellent scripts"},
                headers=auth_headers,
            )
    assert r.status_code == 201
    assert r.json()["data"]["resource_type"] == "negotiation"
```

`backend/tests/integration/test_feedback_ownership_cross_user.py`:

```python
import hashlib
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from career_agent.db import get_session_factory
from career_agent.main import app
from career_agent.models.evaluation import Evaluation
from career_agent.models.job import Job
from career_agent.models.user import User
from tests.conftest import FAKE_CLAIMS


async def _uid_a() -> UUID:
    factory = get_session_factory()
    async with factory() as s:
        r = await s.execute(select(User).where(User.cognito_sub == FAKE_CLAIMS["sub"]))
        return r.scalar_one().id


@pytest.mark.asyncio
async def test_user_b_cannot_feedback_user_a_evaluation(
    auth_headers, seed_profile, second_test_user
):
    """User B cannot leave feedback on user A's evaluation (ownership validation)."""
    uid_a = await _uid_a()
    factory = get_session_factory()

    async with factory() as session:
        h = hashlib.sha256(f"fb-cross-{uuid4()}".encode()).hexdigest()
        job = Job(
            content_hash=h, title="x", description_md="x",
            requirements_json={}, source="manual",
        )
        session.add(job)
        await session.flush()
        ev = Evaluation(
            user_id=uid_a, job_id=job.id, overall_grade="B",
            dimension_scores={}, reasoning="", match_score=0.7,
            recommendation="worth_exploring", model_used="test", cached=False,
        )
        session.add(ev)
        await session.commit()
        eid = ev.id

    # Now impersonate user B (second_test_user fixture returns their auth headers)
    with patch(
        "career_agent.integrations.cognito.CognitoJwtVerifier.verify",
        new=AsyncMock(side_effect=lambda token: _verify_by_token(token)),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            r = await client.post(
                f"/api/v1/evaluations/{eid}/feedback",
                json={"rating": 1},
                headers=second_test_user["headers"],
            )
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "FEEDBACK_RESOURCE_NOT_FOUND"


async def _verify_by_token(token):
    from tests.conftest import SECOND_USER_CLAIMS
    if token == "fake-b":
        return SECOND_USER_CLAIMS
    return FAKE_CLAIMS
```

- [ ] **Step 4: Run the tests**

```bash
uv run pytest tests/integration/test_feedback_evaluation.py tests/integration/test_feedback_cv_output.py tests/integration/test_feedback_interview_prep.py tests/integration/test_feedback_negotiation.py tests/integration/test_feedback_ownership_cross_user.py -v 2>&1 | tail -20
```

Expected: all ~8 tests PASS.

- [ ] **Step 5: Checkpoint**

Checkpoint message: `feat(api): add feedback endpoints for all 4 LLM-generated resources`

---

## Task 19: Agent Tool Wiring — `build_interview_prep_tool` + `generate_negotiation_playbook_tool`

**Files:**
- Modify: `backend/src/career_agent/core/agent/tools.py`
- Modify: `backend/src/career_agent/core/agent/graph.py`
- Modify: `backend/src/career_agent/core/agent/prompts.py`
- Create: `backend/tests/integration/test_agent_interview_prep_tool.py`
- Create: `backend/tests/integration/test_agent_negotiation_tool_requires_offer.py`

- [ ] **Step 1: Empty `NOT_YET_AVAILABLE_TEMPLATES` in `prompts.py`**

Replace the dict with an empty dict:

```python
NOT_YET_AVAILABLE_TEMPLATES: dict[str, str] = {}
```

Also update `SYSTEM_PROMPT`: change the tool count phrasing from "FOUR" to "SIX" and remove the "other capabilities are coming soon" paragraph. The TOOL USAGE section should now read:

```python
TOOL USAGE:
- You have SIX tools available: evaluate_job, optimize_cv, start_job_scan,
  start_batch_evaluation, build_interview_prep, generate_negotiation_playbook.
  The full product surface is live.
- When calling a tool, briefly tell the user what you're doing
- After a tool returns, summarize the result in 1-2 sentences, then let the
  embedded card speak for itself (the UI renders it automatically)
- Never expose internal IDs or raw JSON in chat text
```

- [ ] **Step 2: Append the 2 new tools to `core/agent/tools.py`**

```python
async def build_interview_prep_tool(
    runtime: ToolRuntime,
    *,
    job_id: str | None = None,
    custom_role: str | None = None,
) -> dict[str, Any]:
    """Build interview prep. Exactly one of job_id / custom_role required."""
    from career_agent.api.errors import AppError
    from career_agent.core.interview_prep.service import (
        InterviewPrepContext,
        InterviewPrepService,
    )

    if bool(job_id) == bool(custom_role):
        return {
            "ok": False,
            "error_code": "INVALID_INTERVIEW_PREP_INPUT",
            "message": "Provide exactly one of job_id or custom_role",
        }

    job_uuid: UUID | None = None
    if job_id is not None:
        try:
            job_uuid = UUID(str(job_id))
        except ValueError:
            return {
                "ok": False,
                "error_code": "INVALID_INTERVIEW_PREP_INPUT",
                "message": "Invalid job_id format",
            }

    ctx = InterviewPrepContext(
        user_id=runtime.user_id,
        session=runtime.session,
        usage=runtime.usage,
    )
    service = InterviewPrepService(ctx)
    try:
        prep = await service.create(job_id=job_uuid, custom_role=custom_role)
    except AppError as e:
        return {"ok": False, "error_code": e.code, "message": str(e.message)}

    top_questions = [
        {
            "question": q.get("question", ""),
            "category": q.get("category", ""),
            "suggested_story_title": q.get("suggested_story_title"),
        }
        for q in (prep.questions or [])[:5]
    ]
    red_flags = [
        {
            "question": r.get("question", ""),
            "what_to_listen_for": r.get("what_to_listen_for", ""),
        }
        for r in (prep.red_flag_questions or [])
    ]
    return {
        "ok": True,
        "card": {
            "type": "interview_prep",
            "data": {
                "interview_prep_id": str(prep.id),
                "job_id": str(prep.job_id) if prep.job_id else None,
                "role": custom_role or "This job",
                "story_count": len(prep.questions or []),
                "question_count": len(prep.questions or []),
                "top_questions": top_questions,
                "red_flag_questions": red_flags,
            },
        },
    }


async def generate_negotiation_playbook_tool(
    runtime: ToolRuntime,
    *,
    job_id: str,
) -> dict[str, Any]:
    """Generate negotiation playbook for a job.

    This tool always returns OFFER_DETAILS_REQUIRED because the agent is poor
    at multi-turn form collection — the frontend interprets this as a signal
    to render the OfferForm modal and make a direct POST /negotiations call.
    """
    _ = runtime
    try:
        UUID(str(job_id))
    except ValueError:
        return {
            "ok": False,
            "error_code": "INVALID_BATCH_INPUT",
            "message": "Invalid job_id format",
        }
    return {
        "ok": False,
        "error_code": "OFFER_DETAILS_REQUIRED",
        "message": "Open the negotiation form to enter your offer details.",
        # The frontend uses this field to render OfferForm with job_id pre-filled
        "offer_form_job_id": str(job_id),
    }
```

- [ ] **Step 3: Update `core/agent/graph.py` — extend tool manifest + dispatch**

Update the `tool_manifest` string in `route_node`:

```python
    tool_manifest = """Available tools (you may call at most ONE):

{"call": "evaluate_job", "args": {"job_url": "..."}} — when the user pastes a URL
{"call": "evaluate_job", "args": {"job_description": "..."}} — when the user pastes raw JD text
{"call": "optimize_cv", "args": {"job_id": "<uuid>"}} — when the user wants a tailored CV for a prior evaluation
{"call": "start_job_scan", "args": {}} — when the user wants to find/discover jobs
{"call": "start_batch_evaluation", "args": {"scan_run_id": "<uuid>"}} — to evaluate all results from a scan
{"call": "start_batch_evaluation", "args": {"job_urls": ["https://...", ...]}} — to evaluate URLs
{"call": "start_batch_evaluation", "args": {"job_ids": ["<uuid>", ...]}} — to evaluate existing jobs
{"call": "build_interview_prep", "args": {"job_id": "<uuid>"}} — to prep for a specific job interview
{"call": "build_interview_prep", "args": {"custom_role": "<role description>"}} — generic prep for a role
{"call": "generate_negotiation_playbook", "args": {"job_id": "<uuid>"}} — when the user has an offer to negotiate

If no tool is needed (career_general questions, follow-ups), respond naturally.

To call a tool, reply with EXACTLY this structure and nothing else:
TOOL_CALL: {"call": "...", "args": {...}}

Otherwise, reply normally with conversational text."""
```

Extend the dispatch block in `route_node` (after the existing `start_batch_evaluation` branch):

```python
        elif tool_name == "build_interview_prep":
            tool_result = await build_interview_prep_tool(runtime, **args)
        elif tool_name == "generate_negotiation_playbook":
            tool_result = await generate_negotiation_playbook_tool(runtime, **args)
```

Add the imports at the top of `graph.py`:

```python
from career_agent.core.agent.tools import (
    ToolRuntime,
    build_interview_prep_tool,
    evaluate_job_tool,
    generate_negotiation_playbook_tool,
    optimize_cv_tool,
    start_batch_evaluation_tool,
    start_job_scan_tool,
)
```

Update `_summary_for_card` to handle the two new card types:

```python
def _summary_for_card(card: dict[str, Any]) -> str:
    if card["type"] == "evaluation":
        d = card["data"]
        return (
            f"I evaluated **{d['job_title']}** at {d.get('company') or 'the company'}. "
            f"Overall grade: **{d['overall_grade']}** "
            f"({d['recommendation'].replace('_', ' ')})."
        )
    if card["type"] == "cv_output":
        d = card["data"]
        return f"I tailored your CV for **{d['job_title']}**. The PDF is ready to download."
    if card["type"] == "scan_progress":
        d = card["data"]
        return (
            f"Starting a scan across {d.get('companies_count', '?')} companies. "
            f"I'll let you know when it's done — check the progress card below."
        )
    if card["type"] == "batch_progress":
        d = card["data"]
        return (
            f"Starting batch evaluation on {d.get('total', '?')} jobs. "
            f"L0 → L1 → L2 funnel — watch the progress card below."
        )
    if card["type"] == "interview_prep":
        d = card["data"]
        count = d.get("question_count", 0)
        return (
            f"I prepared **{count} interview questions** for {d.get('role', 'your target role')}. "
            f"Check the card below for top questions + suggested STAR stories."
        )
    return "Done."
```

**Note:** `generate_negotiation_playbook_tool` always returns `ok=False` with code `OFFER_DETAILS_REQUIRED`, so the existing error-handling branch in `route_node` (which builds the "I ran into an issue..." reply) will catch it. The frontend inspects the error code on the tool result and renders the OfferForm modal.

- [ ] **Step 4: Write the interview prep agent tool test**

`backend/tests/integration/test_agent_interview_prep_tool.py`:

```python
import json
from uuid import UUID

import pytest
from sqlalchemy import delete, select

from career_agent.core.agent.tools import ToolRuntime, build_interview_prep_tool
from career_agent.db import get_session_factory
from career_agent.models.star_story import StarStory
from career_agent.models.user import User
from career_agent.services.usage_event import UsageEventService
from tests.conftest import FAKE_CLAIMS
from tests.fixtures.fake_anthropic import fake_anthropic


_GEN_RESPONSE = json.dumps(
    {
        "questions": [
            {
                "question": "Tell me about a migration you led",
                "category": "behavioral",
                "suggested_story_title": "Pre-seeded story",
                "framework": "STAR",
            }
        ],
        "red_flag_questions": [
            {
                "question": "On-call burden?",
                "what_to_listen_for": "Specific numbers",
            }
        ],
    }
)


async def _uid() -> UUID:
    factory = get_session_factory()
    async with factory() as s:
        r = await s.execute(select(User).where(User.cognito_sub == FAKE_CLAIMS["sub"]))
        return r.scalar_one().id


@pytest.mark.asyncio
async def test_build_interview_prep_tool_custom_role(seed_profile):
    uid = await _uid()
    factory = get_session_factory()

    # Seed a story so extraction is skipped
    async with factory() as session:
        await session.execute(delete(StarStory).where(StarStory.user_id == uid))
        session.add(
            StarStory(
                user_id=uid,
                title="Pre-seeded story",
                situation="x", task="x", action="x", result="x",
                reflection=None, tags=["leadership"], source="user_created",
            )
        )
        await session.commit()

    with fake_anthropic({"CANDIDATE RESUME": _GEN_RESPONSE}):
        async with factory() as session:
            usage = UsageEventService(session)

            class _Runtime:
                user_id = uid
                session_ref = session

                @property
                def usage(self):
                    return usage

            # Build a real ToolRuntime (usage is computed via property in Phase 2a pattern)
            runtime = ToolRuntime(user_id=uid, session=session)
            result = await build_interview_prep_tool(
                runtime, custom_role="Staff Engineer"
            )
            await session.commit()

    assert result["ok"] is True
    assert result["card"]["type"] == "interview_prep"
    assert result["card"]["data"]["role"] == "Staff Engineer"


@pytest.mark.asyncio
async def test_build_interview_prep_tool_rejects_both_modes(seed_profile):
    uid = await _uid()
    factory = get_session_factory()
    async with factory() as session:
        runtime = ToolRuntime(user_id=uid, session=session)
        result = await build_interview_prep_tool(
            runtime, job_id="00000000-0000-0000-0000-000000000001", custom_role="x"
        )
    assert result["ok"] is False
    assert result["error_code"] == "INVALID_INTERVIEW_PREP_INPUT"
```

- [ ] **Step 5: Write the negotiation tool test**

`backend/tests/integration/test_agent_negotiation_tool_requires_offer.py`:

```python
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from career_agent.core.agent.tools import (
    ToolRuntime,
    generate_negotiation_playbook_tool,
)
from career_agent.db import get_session_factory
from career_agent.models.user import User
from tests.conftest import FAKE_CLAIMS


async def _uid() -> UUID:
    factory = get_session_factory()
    async with factory() as s:
        r = await s.execute(select(User).where(User.cognito_sub == FAKE_CLAIMS["sub"]))
        return r.scalar_one().id


@pytest.mark.asyncio
async def test_negotiation_tool_always_returns_offer_details_required(seed_profile):
    """The tool always defers to the OfferForm modal via OFFER_DETAILS_REQUIRED."""
    uid = await _uid()
    factory = get_session_factory()
    async with factory() as session:
        runtime = ToolRuntime(user_id=uid, session=session)
        result = await generate_negotiation_playbook_tool(
            runtime, job_id=str(uuid4())
        )

    assert result["ok"] is False
    assert result["error_code"] == "OFFER_DETAILS_REQUIRED"
    assert "offer_form_job_id" in result


@pytest.mark.asyncio
async def test_negotiation_tool_rejects_invalid_job_id(seed_profile):
    uid = await _uid()
    factory = get_session_factory()
    async with factory() as session:
        runtime = ToolRuntime(user_id=uid, session=session)
        result = await generate_negotiation_playbook_tool(
            runtime, job_id="not-a-uuid"
        )
    assert result["ok"] is False
    assert result["error_code"] == "INVALID_BATCH_INPUT"
```

- [ ] **Step 6: Run the tests**

```bash
uv run pytest tests/integration/test_agent_interview_prep_tool.py tests/integration/test_agent_negotiation_tool_requires_offer.py -v 2>&1 | tail -15
```

Expected: all 4 tests PASS.

- [ ] **Step 7: Run the full backend suite + lint + mypy**

```bash
uv run pytest tests/ 2>&1 | tail -5
uv run ruff check src/ 2>&1 | tail -3
uv run black --check src/ 2>&1 | tail -3
uv run mypy src/ 2>&1 | tail -3
```

Expected: all passing + clean.

- [ ] **Step 8: Checkpoint**

Checkpoint message: `feat(agent): wire interview_prep + negotiation tools — 6-tool set complete`

---

## Task 20: Frontend API Client Additions

**Files:**
- Modify: `user-portal/src/lib/api.ts`

- [ ] **Step 1: Add Phase 2d types above the `api` export in `user-portal/src/lib/api.ts`**

```typescript
// ----- Phase 2d types -----

export interface InterviewPrepQuestion {
  question: string;
  category: string;
  suggested_story_title: string | null;
  framework: string | null;
}

export interface InterviewPrepRedFlagQuestion {
  question: string;
  what_to_listen_for: string;
}

export interface InterviewPrep {
  id: string;
  user_id: string;
  job_id: string | null;
  custom_role: string | null;
  questions: InterviewPrepQuestion[];
  red_flag_questions: InterviewPrepRedFlagQuestion[] | null;
  model_used: string;
  tokens_used: number | null;
  created_at: string;
}

export interface StarStory {
  id: string;
  user_id: string;
  title: string;
  situation: string;
  task: string;
  action: string;
  result: string;
  reflection: string | null;
  tags: string[] | null;
  source: 'ai_generated' | 'user_created' | null;
  created_at: string;
}

export interface OfferDetailsInput {
  base: number;
  equity?: string | null;
  signing_bonus?: number | null;
  total_comp?: number | null;
  location?: string | null;
  start_date?: string | null;
}

export interface Negotiation {
  id: string;
  user_id: string;
  job_id: string;
  offer_details: Record<string, unknown>;
  market_research: {
    range_low: number;
    range_mid: number;
    range_high: number;
    source_notes: string;
    comparable_roles: string[];
  };
  counter_offer: {
    target: number;
    minimum_acceptable: number;
    equity_ask: string;
    justification: string;
  };
  scripts: {
    email_template: string;
    call_script: string;
    fallback_positions: string[];
    pitfalls: string[];
  };
  model_used: string;
  tokens_used: number | null;
  created_at: string;
}

export type FeedbackResourceType =
  | 'evaluation'
  | 'cv_output'
  | 'interview_prep'
  | 'negotiation';

export interface Feedback {
  id: string;
  user_id: string;
  resource_type: FeedbackResourceType;
  resource_id: string;
  rating: number;
  correction_notes: string | null;
  created_at: string;
}
```

- [ ] **Step 2: Extend the `api` export with new namespaces**

Merge into the existing `api` const (keep existing methods):

```typescript
  interviewPreps: {
    list: () => request<{ data: InterviewPrep[] }>('GET', '/api/v1/interview-preps'),
    get: (id: string) =>
      request<{ data: InterviewPrep }>('GET', `/api/v1/interview-preps/${id}`),
    create: (body: { job_id?: string; custom_role?: string }) =>
      request<{ data: InterviewPrep }>('POST', '/api/v1/interview-preps', body),
    regenerate: (id: string, feedback?: string) =>
      request<{ data: InterviewPrep }>(
        'POST',
        `/api/v1/interview-preps/${id}/regenerate`,
        { feedback },
      ),
  },
  starStories: {
    list: (tags?: string[]) => {
      const qs = tags?.length ? `?tags=${tags.join(',')}` : '';
      return request<{ data: StarStory[] }>('GET', `/api/v1/star-stories${qs}`);
    },
    create: (body: {
      title: string;
      situation: string;
      task: string;
      action: string;
      result: string;
      reflection?: string;
      tags?: string[];
    }) => request<{ data: StarStory }>('POST', '/api/v1/star-stories', body),
    update: (id: string, body: Partial<StarStory>) =>
      request<{ data: StarStory }>('PUT', `/api/v1/star-stories/${id}`, body),
    delete: (id: string) => request<void>('DELETE', `/api/v1/star-stories/${id}`),
  },
  negotiations: {
    list: () => request<{ data: Negotiation[] }>('GET', '/api/v1/negotiations'),
    get: (id: string) =>
      request<{ data: Negotiation }>('GET', `/api/v1/negotiations/${id}`),
    create: (body: { job_id: string; offer_details: OfferDetailsInput }) =>
      request<{ data: Negotiation }>('POST', '/api/v1/negotiations', body),
    regenerate: (id: string, feedback?: string) =>
      request<{ data: Negotiation }>(
        'POST',
        `/api/v1/negotiations/${id}/regenerate`,
        { feedback },
      ),
  },
  feedback: {
    submit: (
      resourceType: FeedbackResourceType,
      resourceId: string,
      body: { rating: number; correction_notes?: string },
    ) => {
      const pathPart =
        resourceType === 'evaluation'
          ? 'evaluations'
          : resourceType === 'cv_output'
            ? 'cv-outputs'
            : resourceType === 'interview_prep'
              ? 'interview-preps'
              : 'negotiations';
      return request<{ data: Feedback }>(
        'POST',
        `/api/v1/${pathPart}/${resourceId}/feedback`,
        body,
      );
    },
  },
```

- [ ] **Step 3: Type check**

```bash
cd ../user-portal
./node_modules/.bin/tsc --noEmit 2>&1 | tail -5
```

Expected: no errors.

- [ ] **Step 4: Checkpoint**

Checkpoint message: `feat(user-portal): add Phase 2d API client (interview preps, negotiations, star stories, feedback)`

---

## Task 21: FeedbackWidget Shared Component + Wire Into Phase 2a/2b Cards

**Files:**
- Create: `user-portal/src/components/shared/FeedbackWidget.tsx`
- Modify: `user-portal/src/components/chat/cards/EvaluationCard.tsx`
- Modify: `user-portal/src/components/chat/cards/CvOutputCard.tsx`

- [ ] **Step 1: Create `user-portal/src/components/shared/FeedbackWidget.tsx`**

```tsx
import { useState, useRef, useEffect } from 'react';

import { api, type FeedbackResourceType } from '../../lib/api';

interface Props {
  resourceType: FeedbackResourceType;
  resourceId: string;
  /** Optional initial rating to display (e.g. from a prior session). */
  initialRating?: number;
  /** Compact layout for chat cards; expanded for detail pages. */
  variant?: 'compact' | 'expanded';
}

const DEBOUNCE_MS = 500;

export function FeedbackWidget({
  resourceType,
  resourceId,
  initialRating = 0,
  variant = 'compact',
}: Props) {
  const [rating, setRating] = useState(initialRating);
  const [notes, setNotes] = useState('');
  const [showNotes, setShowNotes] = useState(false);
  const [status, setStatus] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle');
  const [error, setError] = useState<string | null>(null);
  const timerRef = useRef<number | undefined>(undefined);

  useEffect(() => () => {
    if (timerRef.current !== undefined) window.clearTimeout(timerRef.current);
  }, []);

  async function submit(nextRating: number, nextNotes: string | undefined) {
    setStatus('saving');
    setError(null);
    try {
      await api.feedback.submit(resourceType, resourceId, {
        rating: nextRating,
        correction_notes: nextNotes,
      });
      setStatus('saved');
      window.setTimeout(() => setStatus('idle'), 2000);
    } catch (e) {
      setStatus('error');
      setError((e as Error).message);
    }
  }

  function handleStarClick(nextRating: number) {
    setRating(nextRating);
    // Debounce so rapid clicks resolve to a single POST
    if (timerRef.current !== undefined) window.clearTimeout(timerRef.current);
    timerRef.current = window.setTimeout(() => {
      submit(nextRating, notes || undefined);
    }, DEBOUNCE_MS);
  }

  async function handleNotesSubmit() {
    if (rating === 0) return;
    await submit(rating, notes || undefined);
  }

  const containerClass =
    variant === 'compact'
      ? 'mt-3 flex items-center gap-3 border-t border-[#e3e2e0] pt-2 text-xs'
      : 'mt-6 rounded-lg border border-[#e3e2e0] bg-[#fbfbfa] p-4';

  return (
    <div className={containerClass}>
      <div className="flex items-center gap-1">
        <span className="text-[#787774]">Rate:</span>
        {[1, 2, 3, 4, 5].map((n) => (
          <button
            key={n}
            type="button"
            onClick={() => handleStarClick(n)}
            aria-label={`Rate ${n} stars`}
            className={`text-lg ${
              n <= rating ? 'text-[#cb912f]' : 'text-[#e3e2e0]'
            }`}
          >
            ★
          </button>
        ))}
      </div>

      {variant === 'compact' ? (
        <>
          {!showNotes ? (
            <button
              type="button"
              onClick={() => setShowNotes(true)}
              className="text-[#2383e2]"
            >
              Add notes
            </button>
          ) : (
            <div className="flex flex-1 items-center gap-2">
              <input
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="What went wrong?"
                className="flex-1 rounded border border-[#e3e2e0] px-2 py-1 text-xs"
              />
              <button
                type="button"
                onClick={handleNotesSubmit}
                className="rounded bg-[#2383e2] px-2 py-1 text-xs text-white"
              >
                Save
              </button>
            </div>
          )}
          {status === 'saved' && <span className="text-[#35a849]">✓ Saved</span>}
          {status === 'error' && error && (
            <span className="text-[#e03e3e]">{error}</span>
          )}
        </>
      ) : (
        <div className="mt-3">
          <label className="block text-xs font-medium text-[#787774]">
            Correction notes (optional)
          </label>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={3}
            className="mt-1 w-full rounded border border-[#e3e2e0] px-3 py-2 text-sm"
            placeholder="What would you change?"
          />
          <div className="mt-2 flex items-center gap-3">
            <button
              type="button"
              onClick={handleNotesSubmit}
              disabled={rating === 0}
              className="rounded bg-[#2383e2] px-4 py-1.5 text-sm text-white disabled:opacity-50"
            >
              Save feedback
            </button>
            {status === 'saved' && <span className="text-sm text-[#35a849]">Saved</span>}
            {status === 'error' && error && (
              <span className="text-sm text-[#e03e3e]">{error}</span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Add FeedbackWidget to `EvaluationCard.tsx`**

Open `user-portal/src/components/chat/cards/EvaluationCard.tsx` and add the import at the top:

```tsx
import { FeedbackWidget } from '../../shared/FeedbackWidget';
```

Find the closing of the card's main content (before the closing `</article>` or `</div>`) and add:

```tsx
<FeedbackWidget resourceType="evaluation" resourceId={data.evaluation_id} />
```

- [ ] **Step 3: Add FeedbackWidget to `CvOutputCard.tsx`**

Same pattern:

```tsx
import { FeedbackWidget } from '../../shared/FeedbackWidget';
// ... in the JSX:
<FeedbackWidget resourceType="cv_output" resourceId={data.cv_output_id} />
```

- [ ] **Step 4: Type check + run tests to confirm no regressions**

```bash
cd ../user-portal
./node_modules/.bin/tsc --noEmit 2>&1 | tail -5
./node_modules/.bin/vitest run 2>&1 | tail -10
```

Expected: no type errors; all existing tests still pass.

- [ ] **Step 5: Checkpoint**

Checkpoint message: `feat(user-portal): add shared FeedbackWidget + wire into EvaluationCard + CvOutputCard`

---

## Task 22: Story Bank UI (StarStoryCard + StarStoryEditor + StoryBankPage)

**Files:**
- Create: `user-portal/src/components/interview-prep/StarStoryCard.tsx`
- Create: `user-portal/src/components/interview-prep/StarStoryEditor.tsx`
- Create: `user-portal/src/pages/StoryBankPage.tsx`

- [ ] **Step 1: Create `StarStoryCard.tsx`**

```tsx
import type { StarStory } from '../../lib/api';

interface Props {
  story: StarStory;
  onEdit: () => void;
  onDelete: () => void;
}

export function StarStoryCard({ story, onEdit, onDelete }: Props) {
  return (
    <article className="rounded-lg border border-[#e3e2e0] bg-white p-4">
      <header className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-base font-semibold">{story.title}</h3>
          <div className="mt-1 flex flex-wrap gap-1">
            {story.tags?.map((tag) => (
              <span
                key={tag}
                className="rounded-full bg-[#f7f6f3] px-2 py-0.5 text-xs text-[#787774]"
              >
                {tag}
              </span>
            ))}
            <span
              className={`rounded-full px-2 py-0.5 text-xs ${
                story.source === 'ai_generated'
                  ? 'bg-[#e8f3ff] text-[#2383e2]'
                  : 'bg-[#f7f6f3] text-[#787774]'
              }`}
            >
              {story.source === 'ai_generated' ? 'AI' : 'Manual'}
            </span>
          </div>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={onEdit}
            className="rounded border border-[#e3e2e0] px-2 py-1 text-xs"
          >
            Edit
          </button>
          <button
            type="button"
            onClick={onDelete}
            className="rounded border border-[#e3e2e0] px-2 py-1 text-xs text-[#e03e3e]"
          >
            Delete
          </button>
        </div>
      </header>
      <dl className="mt-3 space-y-2 text-sm">
        <div>
          <dt className="text-xs font-medium text-[#787774]">Situation</dt>
          <dd className="text-[#37352f]">{story.situation}</dd>
        </div>
        <div>
          <dt className="text-xs font-medium text-[#787774]">Task</dt>
          <dd className="text-[#37352f]">{story.task}</dd>
        </div>
        <div>
          <dt className="text-xs font-medium text-[#787774]">Action</dt>
          <dd className="text-[#37352f]">{story.action}</dd>
        </div>
        <div>
          <dt className="text-xs font-medium text-[#787774]">Result</dt>
          <dd className="text-[#37352f]">{story.result}</dd>
        </div>
        {story.reflection && (
          <div>
            <dt className="text-xs font-medium text-[#787774]">Reflection</dt>
            <dd className="text-[#37352f]">{story.reflection}</dd>
          </div>
        )}
      </dl>
    </article>
  );
}
```

- [ ] **Step 2: Create `StarStoryEditor.tsx`**

```tsx
import { useState, type FormEvent } from 'react';

import { api, type StarStory } from '../../lib/api';

interface Props {
  existing?: StarStory;
  onSave: (story: StarStory) => void;
  onCancel: () => void;
}

export function StarStoryEditor({ existing, onSave, onCancel }: Props) {
  const [title, setTitle] = useState(existing?.title ?? '');
  const [situation, setSituation] = useState(existing?.situation ?? '');
  const [task, setTask] = useState(existing?.task ?? '');
  const [action, setAction] = useState(existing?.action ?? '');
  const [result, setResult] = useState(existing?.result ?? '');
  const [reflection, setReflection] = useState(existing?.reflection ?? '');
  const [tagsInput, setTagsInput] = useState((existing?.tags ?? []).join(', '));
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setPending(true);
    setError(null);
    const tags = tagsInput
      .split(',')
      .map((t) => t.trim())
      .filter(Boolean);
    try {
      const body = {
        title,
        situation,
        task,
        action,
        result,
        reflection: reflection || undefined,
        tags: tags.length ? tags : undefined,
      };
      const resp = existing
        ? await api.starStories.update(existing.id, body)
        : await api.starStories.create(body);
      onSave(resp.data);
    } catch (err) {
      setError((err as Error).message);
      setPending(false);
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="rounded-lg border border-[#e3e2e0] bg-[#fbfbfa] p-4"
    >
      <h3 className="text-base font-semibold">
        {existing ? 'Edit story' : 'New story'}
      </h3>

      <label className="mt-3 block text-xs font-medium text-[#787774]">Title</label>
      <input
        required
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        className="mt-1 w-full rounded border border-[#e3e2e0] px-3 py-2 text-sm"
      />

      {(['situation', 'task', 'action', 'result'] as const).map((field) => {
        const value =
          field === 'situation'
            ? situation
            : field === 'task'
              ? task
              : field === 'action'
                ? action
                : result;
        const setter =
          field === 'situation'
            ? setSituation
            : field === 'task'
              ? setTask
              : field === 'action'
                ? setAction
                : setResult;
        return (
          <div key={field}>
            <label className="mt-3 block text-xs font-medium text-[#787774] capitalize">
              {field}
            </label>
            <textarea
              required
              value={value}
              onChange={(e) => setter(e.target.value)}
              rows={2}
              className="mt-1 w-full rounded border border-[#e3e2e0] px-3 py-2 text-sm"
            />
          </div>
        );
      })}

      <label className="mt-3 block text-xs font-medium text-[#787774]">
        Reflection (optional)
      </label>
      <textarea
        value={reflection}
        onChange={(e) => setReflection(e.target.value)}
        rows={2}
        className="mt-1 w-full rounded border border-[#e3e2e0] px-3 py-2 text-sm"
      />

      <label className="mt-3 block text-xs font-medium text-[#787774]">
        Tags (comma-separated)
      </label>
      <input
        value={tagsInput}
        onChange={(e) => setTagsInput(e.target.value)}
        placeholder="leadership, migration, scale"
        className="mt-1 w-full rounded border border-[#e3e2e0] px-3 py-2 text-sm"
      />

      {error && <p className="mt-3 text-sm text-[#e03e3e]">{error}</p>}

      <div className="mt-4 flex justify-end gap-2">
        <button
          type="button"
          onClick={onCancel}
          className="rounded border border-[#e3e2e0] px-3 py-1 text-sm"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={pending}
          className="rounded bg-[#2383e2] px-3 py-1 text-sm text-white disabled:opacity-50"
        >
          {pending ? 'Saving…' : 'Save'}
        </button>
      </div>
    </form>
  );
}
```

- [ ] **Step 3: Create `StoryBankPage.tsx`**

```tsx
import { useCallback, useEffect, useState } from 'react';

import { AppShell } from '../components/layout/AppShell';
import { StarStoryCard } from '../components/interview-prep/StarStoryCard';
import { StarStoryEditor } from '../components/interview-prep/StarStoryEditor';
import { api, type StarStory } from '../lib/api';

export default function StoryBankPage() {
  const [stories, setStories] = useState<StarStory[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<StarStory | 'new' | null>(null);
  const [tagFilter, setTagFilter] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const tags = tagFilter.trim() ? [tagFilter.trim()] : undefined;
      const resp = await api.starStories.list(tags);
      setStories(resp.data);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [tagFilter]);

  useEffect(() => {
    load();
  }, [load]);

  async function handleDelete(story: StarStory) {
    if (!confirm(`Delete "${story.title}"?`)) return;
    try {
      await api.starStories.delete(story.id);
      await load();
    } catch (e) {
      setError((e as Error).message);
    }
  }

  return (
    <AppShell>
      <div className="mx-auto max-w-3xl">
        <div className="flex items-center justify-between">
          <div>
            <a href="/interview-prep" className="text-sm text-[#2383e2]">
              ← Back to interview prep
            </a>
            <h1 className="mt-1 text-2xl font-semibold">Story bank</h1>
          </div>
          <button
            type="button"
            onClick={() => setEditing('new')}
            className="rounded bg-[#2383e2] px-4 py-2 text-sm font-medium text-white"
          >
            Add story
          </button>
        </div>

        <div className="mt-4 flex items-center gap-2 text-sm">
          <label className="text-[#787774]">Filter by tag:</label>
          <input
            value={tagFilter}
            onChange={(e) => setTagFilter(e.target.value)}
            placeholder="e.g. leadership"
            className="rounded border border-[#e3e2e0] px-2 py-1 text-xs"
          />
        </div>

        {error && <p className="mt-4 text-sm text-[#e03e3e]">{error}</p>}

        {loading ? (
          <p className="mt-8 text-sm text-[#787774]">Loading…</p>
        ) : editing ? (
          <div className="mt-6">
            <StarStoryEditor
              existing={editing === 'new' ? undefined : editing}
              onSave={() => {
                setEditing(null);
                load();
              }}
              onCancel={() => setEditing(null)}
            />
          </div>
        ) : stories.length === 0 ? (
          <p className="mt-8 text-sm text-[#787774]">
            No stories yet. Build an interview prep session to auto-extract stories
            from your resume, or add one manually.
          </p>
        ) : (
          <ul className="mt-6 space-y-3">
            {stories.map((story) => (
              <li key={story.id}>
                <StarStoryCard
                  story={story}
                  onEdit={() => setEditing(story)}
                  onDelete={() => handleDelete(story)}
                />
              </li>
            ))}
          </ul>
        )}
      </div>
    </AppShell>
  );
}
```

- [ ] **Step 4: Type check**

```bash
./node_modules/.bin/tsc --noEmit 2>&1 | tail -5
```

Expected: no errors.

- [ ] **Step 5: Checkpoint**

Checkpoint message: `feat(user-portal): add story bank page with CRUD editor`

---

## Task 23: Interview Prep Pages (List + Detail + QuestionListItem)

**Files:**
- Create: `user-portal/src/components/interview-prep/QuestionListItem.tsx`
- Create: `user-portal/src/pages/InterviewPrepListPage.tsx`
- Create: `user-portal/src/pages/InterviewPrepDetailPage.tsx`
- Modify: `user-portal/src/App.tsx` — add routes
- Modify: `user-portal/src/components/layout/AppShell.tsx` — add nav link

- [ ] **Step 1: Create `QuestionListItem.tsx`**

```tsx
import type { InterviewPrepQuestion } from '../../lib/api';

const CATEGORY_COLOR: Record<string, string> = {
  behavioral: 'bg-[#e8f3ff] text-[#2383e2]',
  technical: 'bg-[#e9f7eb] text-[#35a849]',
  situational: 'bg-[#fef5e7] text-[#cb912f]',
  culture: 'bg-[#f3e8ff] text-[#8b5cf6]',
};

export function QuestionListItem({ question }: { question: InterviewPrepQuestion }) {
  const color = CATEGORY_COLOR[question.category] ?? 'bg-[#f7f6f3] text-[#787774]';
  return (
    <article className="rounded border border-[#e3e2e0] bg-white p-3">
      <div className="flex items-start justify-between gap-3">
        <h4 className="text-sm font-medium text-[#37352f]">{question.question}</h4>
        <span className={`rounded px-2 py-0.5 text-xs ${color}`}>
          {question.category}
        </span>
      </div>
      {question.suggested_story_title && (
        <p className="mt-1 text-xs text-[#787774]">
          Use story: <strong>{question.suggested_story_title}</strong>
        </p>
      )}
      {question.framework && (
        <p className="mt-2 text-xs text-[#37352f]">{question.framework}</p>
      )}
    </article>
  );
}
```

- [ ] **Step 2: Create `InterviewPrepListPage.tsx`**

```tsx
import { useCallback, useEffect, useState } from 'react';

import { AppShell } from '../components/layout/AppShell';
import { api, type InterviewPrep } from '../lib/api';

export default function InterviewPrepListPage() {
  const [preps, setPreps] = useState<InterviewPrep[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const resp = await api.interviewPreps.list();
      setPreps(resp.data);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <AppShell>
      <div className="mx-auto max-w-3xl">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-semibold">Interview prep</h1>
          <a
            href="/interview-prep/story-bank"
            className="rounded border border-[#e3e2e0] px-4 py-2 text-sm"
          >
            Story bank
          </a>
        </div>

        {error && <p className="mt-4 text-sm text-[#e03e3e]">{error}</p>}

        {loading ? (
          <p className="mt-8 text-sm text-[#787774]">Loading…</p>
        ) : preps.length === 0 ? (
          <p className="mt-8 text-sm text-[#787774]">
            No interview prep sessions yet. Ask your agent to "prep me for a staff
            engineer interview" to generate one.
          </p>
        ) : (
          <ul className="mt-6 space-y-3">
            {preps.map((prep) => {
              const title = prep.custom_role || 'Job-specific prep';
              return (
                <li key={prep.id}>
                  <a
                    href={`/interview-prep/${prep.id}`}
                    className="block rounded-lg border border-[#e3e2e0] bg-white p-4 hover:bg-[#fbfbfa]"
                  >
                    <h3 className="text-base font-semibold">{title}</h3>
                    <p className="mt-1 text-xs text-[#787774]">
                      {prep.questions.length} questions ·{' '}
                      {prep.red_flag_questions?.length ?? 0} red flag questions ·
                      generated{' '}
                      {new Date(prep.created_at).toLocaleDateString()}
                    </p>
                  </a>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </AppShell>
  );
}
```

- [ ] **Step 3: Create `InterviewPrepDetailPage.tsx`**

```tsx
import { useCallback, useEffect, useMemo, useState } from 'react';

import { AppShell } from '../components/layout/AppShell';
import { QuestionListItem } from '../components/interview-prep/QuestionListItem';
import { FeedbackWidget } from '../components/shared/FeedbackWidget';
import { api, type InterviewPrep } from '../lib/api';

export default function InterviewPrepDetailPage() {
  const prepId = useMemo(() => {
    const parts = window.location.pathname.split('/');
    return parts[parts.length - 1];
  }, []);

  const [prep, setPrep] = useState<InterviewPrep | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [regenerating, setRegenerating] = useState(false);
  const [feedbackInput, setFeedbackInput] = useState('');
  const [showRegenForm, setShowRegenForm] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const resp = await api.interviewPreps.get(prepId);
      setPrep(resp.data);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [prepId]);

  useEffect(() => {
    load();
  }, [load]);

  async function handleRegenerate() {
    setRegenerating(true);
    setError(null);
    try {
      const resp = await api.interviewPreps.regenerate(prepId, feedbackInput || undefined);
      window.location.href = `/interview-prep/${resp.data.id}`;
    } catch (e) {
      setError((e as Error).message);
      setRegenerating(false);
    }
  }

  if (loading) {
    return (
      <AppShell>
        <p className="text-sm text-[#787774]">Loading…</p>
      </AppShell>
    );
  }

  if (!prep) {
    return (
      <AppShell>
        <p className="text-sm text-[#e03e3e]">
          {error ?? 'Interview prep not found'}
        </p>
      </AppShell>
    );
  }

  const title = prep.custom_role || 'Interview prep';

  return (
    <AppShell>
      <div className="mx-auto max-w-3xl">
        <a href="/interview-prep" className="text-sm text-[#2383e2]">
          ← Back to interview prep
        </a>
        <h1 className="mt-2 text-2xl font-semibold">{title}</h1>
        <p className="mt-1 text-xs text-[#787774]">
          Generated {new Date(prep.created_at).toLocaleDateString()} ·{' '}
          {prep.questions.length} questions
        </p>

        <section className="mt-6">
          <h2 className="text-lg font-semibold">Questions</h2>
          <ul className="mt-3 space-y-3">
            {prep.questions.map((q, i) => (
              <li key={i}>
                <QuestionListItem
                  question={{
                    question: q.question,
                    category: q.category,
                    suggested_story_title: q.suggested_story_title ?? null,
                    framework: q.framework ?? null,
                  }}
                />
              </li>
            ))}
          </ul>
        </section>

        {prep.red_flag_questions && prep.red_flag_questions.length > 0 && (
          <section className="mt-6">
            <h2 className="text-lg font-semibold">
              Questions to ask the interviewer
            </h2>
            <ul className="mt-3 space-y-3">
              {prep.red_flag_questions.map((r, i) => (
                <li
                  key={i}
                  className="rounded border border-[#e3e2e0] bg-white p-3"
                >
                  <p className="text-sm font-medium">{r.question}</p>
                  {r.what_to_listen_for && (
                    <p className="mt-1 text-xs text-[#787774]">
                      Listen for: {r.what_to_listen_for}
                    </p>
                  )}
                </li>
              ))}
            </ul>
          </section>
        )}

        <section className="mt-6">
          {!showRegenForm ? (
            <button
              type="button"
              onClick={() => setShowRegenForm(true)}
              className="rounded border border-[#e3e2e0] px-3 py-1.5 text-sm"
            >
              Regenerate with feedback
            </button>
          ) : (
            <div className="rounded-lg border border-[#e3e2e0] bg-[#fbfbfa] p-4">
              <label className="text-sm font-medium">
                What would you like changed?
              </label>
              <textarea
                value={feedbackInput}
                onChange={(e) => setFeedbackInput(e.target.value)}
                rows={3}
                placeholder="e.g. make questions harder, focus more on distributed systems"
                className="mt-2 w-full rounded border border-[#e3e2e0] px-3 py-2 text-sm"
              />
              <div className="mt-2 flex gap-2">
                <button
                  type="button"
                  onClick={handleRegenerate}
                  disabled={regenerating}
                  className="rounded bg-[#2383e2] px-3 py-1.5 text-sm text-white disabled:opacity-50"
                >
                  {regenerating ? 'Generating…' : 'Regenerate'}
                </button>
                <button
                  type="button"
                  onClick={() => setShowRegenForm(false)}
                  className="rounded border border-[#e3e2e0] px-3 py-1.5 text-sm"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
        </section>

        <FeedbackWidget
          resourceType="interview_prep"
          resourceId={prep.id}
          variant="expanded"
        />
      </div>
    </AppShell>
  );
}
```

- [ ] **Step 4: Update `App.tsx` — add routes**

```tsx
import InterviewPrepDetailPage from './pages/InterviewPrepDetailPage';
import InterviewPrepListPage from './pages/InterviewPrepListPage';
import StoryBankPage from './pages/StoryBankPage';

function matchRoute(pathname: string) {
  // existing routes...
  if (pathname === '/interview-prep') return 'interview-prep-list';
  if (pathname === '/interview-prep/story-bank') return 'story-bank';
  if (pathname.startsWith('/interview-prep/')) return 'interview-prep-detail';
  // ...
}

// in render:
{route === 'interview-prep-list' && <InterviewPrepListPage />}
{route === 'story-bank' && <StoryBankPage />}
{route === 'interview-prep-detail' && <InterviewPrepDetailPage />}
```

**Important:** the `story-bank` check must come **before** the `interview-prep-detail` startsWith check, otherwise `/interview-prep/story-bank` would be matched as a detail page with id "story-bank".

- [ ] **Step 5: Update `AppShell.tsx` — add nav link**

In the nav section (before the Billing link), add:

```tsx
<a href="/interview-prep" className="hover:text-[#37352f]">
  Interview Prep
</a>
```

- [ ] **Step 6: Type check**

```bash
./node_modules/.bin/tsc --noEmit 2>&1 | tail -5
```

Expected: no errors.

- [ ] **Step 7: Checkpoint**

Checkpoint message: `feat(user-portal): add interview prep list + detail pages with regenerate flow`

---

## Task 24: Negotiation Pages + OfferForm + MarketRangeChart + ScriptBlock

**Files:**
- Create: `user-portal/src/components/negotiation/OfferForm.tsx`
- Create: `user-portal/src/components/negotiation/MarketRangeChart.tsx`
- Create: `user-portal/src/components/negotiation/ScriptBlock.tsx`
- Create: `user-portal/src/pages/NegotiationListPage.tsx`
- Create: `user-portal/src/pages/NegotiationDetailPage.tsx`
- Modify: `user-portal/src/App.tsx` — add routes
- Modify: `user-portal/src/components/layout/AppShell.tsx` — nav link

- [ ] **Step 1: Create `OfferForm.tsx`**

```tsx
import { useState, type FormEvent } from 'react';

import { api, type Negotiation, type OfferDetailsInput } from '../../lib/api';

interface Props {
  jobId: string;
  onSuccess: (negotiation: Negotiation) => void;
  onCancel: () => void;
}

export function OfferForm({ jobId, onSuccess, onCancel }: Props) {
  const [base, setBase] = useState('');
  const [equity, setEquity] = useState('');
  const [signingBonus, setSigningBonus] = useState('');
  const [totalComp, setTotalComp] = useState('');
  const [location, setLocation] = useState('');
  const [startDate, setStartDate] = useState('');
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const baseNum = parseInt(base, 10);
    if (Number.isNaN(baseNum) || baseNum < 0) {
      setError('Base salary is required and must be a positive number');
      return;
    }
    setPending(true);
    setError(null);

    const offer_details: OfferDetailsInput = {
      base: baseNum,
      equity: equity || undefined,
      signing_bonus: signingBonus ? parseInt(signingBonus, 10) : undefined,
      total_comp: totalComp ? parseInt(totalComp, 10) : undefined,
      location: location || undefined,
      start_date: startDate || undefined,
    };

    try {
      const resp = await api.negotiations.create({
        job_id: jobId,
        offer_details,
      });
      onSuccess(resp.data);
    } catch (e) {
      setError((e as Error).message);
      setPending(false);
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="rounded-lg border border-[#e3e2e0] bg-[#fbfbfa] p-4"
    >
      <h3 className="text-base font-semibold">Enter offer details</h3>
      <p className="mt-1 text-xs text-[#787774]">
        These numbers drive the market research and counter-offer math.
      </p>

      <label className="mt-4 block text-xs font-medium text-[#787774]">
        Base salary (USD) *
      </label>
      <input
        type="number"
        required
        min={0}
        value={base}
        onChange={(e) => setBase(e.target.value)}
        placeholder="e.g. 195000"
        className="mt-1 w-full rounded border border-[#e3e2e0] px-3 py-2 text-sm"
      />

      <label className="mt-3 block text-xs font-medium text-[#787774]">
        Equity (optional)
      </label>
      <input
        value={equity}
        onChange={(e) => setEquity(e.target.value)}
        placeholder="e.g. 0.08% or $120k RSU over 4 years"
        className="mt-1 w-full rounded border border-[#e3e2e0] px-3 py-2 text-sm"
      />

      <div className="mt-3 grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs font-medium text-[#787774]">
            Signing bonus (optional)
          </label>
          <input
            type="number"
            min={0}
            value={signingBonus}
            onChange={(e) => setSigningBonus(e.target.value)}
            className="mt-1 w-full rounded border border-[#e3e2e0] px-3 py-2 text-sm"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-[#787774]">
            Total comp (optional)
          </label>
          <input
            type="number"
            min={0}
            value={totalComp}
            onChange={(e) => setTotalComp(e.target.value)}
            className="mt-1 w-full rounded border border-[#e3e2e0] px-3 py-2 text-sm"
          />
        </div>
      </div>

      <label className="mt-3 block text-xs font-medium text-[#787774]">
        Location (optional)
      </label>
      <input
        value={location}
        onChange={(e) => setLocation(e.target.value)}
        placeholder="e.g. San Francisco"
        className="mt-1 w-full rounded border border-[#e3e2e0] px-3 py-2 text-sm"
      />

      <label className="mt-3 block text-xs font-medium text-[#787774]">
        Start date (optional)
      </label>
      <input
        type="date"
        value={startDate}
        onChange={(e) => setStartDate(e.target.value)}
        className="mt-1 w-full rounded border border-[#e3e2e0] px-3 py-2 text-sm"
      />

      {error && <p className="mt-3 text-sm text-[#e03e3e]">{error}</p>}

      <div className="mt-4 flex justify-end gap-2">
        <button
          type="button"
          onClick={onCancel}
          className="rounded border border-[#e3e2e0] px-4 py-2 text-sm"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={pending || !base}
          className="rounded bg-[#2383e2] px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          {pending ? 'Generating playbook…' : 'Generate playbook'}
        </button>
      </div>
    </form>
  );
}
```

- [ ] **Step 2: Create `MarketRangeChart.tsx`**

```tsx
interface Props {
  low: number;
  mid: number;
  high: number;
  sourceNotes: string;
  comparableRoles: string[];
}

function fmt(n: number): string {
  return `$${(n / 1000).toFixed(0)}k`;
}

export function MarketRangeChart({ low, mid, high, sourceNotes, comparableRoles }: Props) {
  return (
    <div className="rounded-lg border border-[#e3e2e0] bg-white p-4">
      <h3 className="text-sm font-semibold text-[#37352f]">Market range</h3>

      <div className="mt-3 flex items-center gap-4">
        <div className="flex-1">
          <div className="relative h-2 rounded bg-[#f7f6f3]">
            <div
              className="absolute top-0 h-2 rounded bg-[#2383e2]"
              style={{ left: '0%', width: '100%' }}
            />
            <div
              className="absolute -top-1 h-4 w-0.5 bg-[#cb912f]"
              style={{ left: '50%' }}
              title={`Median: ${fmt(mid)}`}
            />
          </div>
          <div className="mt-1 flex justify-between text-xs text-[#787774]">
            <span>{fmt(low)}</span>
            <span className="font-semibold text-[#cb912f]">{fmt(mid)}</span>
            <span>{fmt(high)}</span>
          </div>
        </div>
      </div>

      <p className="mt-3 text-xs text-[#787774]">{sourceNotes}</p>

      {comparableRoles.length > 0 && (
        <div className="mt-2 text-xs text-[#787774]">
          <strong>Comparables:</strong> {comparableRoles.join(', ')}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Create `ScriptBlock.tsx`**

```tsx
import { useState } from 'react';

interface Props {
  title: string;
  content: string;
}

export function ScriptBlock({ title, content }: Props) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // noop — some browsers block without secure context
    }
  }

  return (
    <div className="rounded-lg border border-[#e3e2e0] bg-white p-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold">{title}</h3>
        <button
          type="button"
          onClick={copy}
          className="rounded border border-[#e3e2e0] px-2 py-1 text-xs"
        >
          {copied ? 'Copied!' : 'Copy'}
        </button>
      </div>
      <pre className="mt-2 whitespace-pre-wrap rounded bg-[#fbfbfa] p-3 text-xs text-[#37352f]">
        {content}
      </pre>
    </div>
  );
}
```

- [ ] **Step 4: Create `NegotiationListPage.tsx`**

```tsx
import { useCallback, useEffect, useState } from 'react';

import { AppShell } from '../components/layout/AppShell';
import { api, type Negotiation } from '../lib/api';

export default function NegotiationListPage() {
  const [negs, setNegs] = useState<Negotiation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const resp = await api.negotiations.list();
      setNegs(resp.data);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <AppShell>
      <div className="mx-auto max-w-3xl">
        <h1 className="text-2xl font-semibold">Negotiations</h1>

        {error && <p className="mt-4 text-sm text-[#e03e3e]">{error}</p>}

        {loading ? (
          <p className="mt-8 text-sm text-[#787774]">Loading…</p>
        ) : negs.length === 0 ? (
          <p className="mt-8 text-sm text-[#787774]">
            No negotiations yet. Once you have an offer, ask your agent to
            "help me negotiate this Stripe offer" and fill in the details.
          </p>
        ) : (
          <ul className="mt-6 space-y-3">
            {negs.map((neg) => {
              const target = neg.counter_offer?.target;
              return (
                <li key={neg.id}>
                  <a
                    href={`/negotiations/${neg.id}`}
                    className="block rounded-lg border border-[#e3e2e0] bg-white p-4 hover:bg-[#fbfbfa]"
                  >
                    <h3 className="text-base font-semibold">
                      Counter target: ${(target / 1000).toFixed(0)}k
                    </h3>
                    <p className="mt-1 text-xs text-[#787774]">
                      Generated {new Date(neg.created_at).toLocaleDateString()}
                    </p>
                  </a>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </AppShell>
  );
}
```

- [ ] **Step 5: Create `NegotiationDetailPage.tsx`**

```tsx
import { useCallback, useEffect, useMemo, useState } from 'react';

import { AppShell } from '../components/layout/AppShell';
import { MarketRangeChart } from '../components/negotiation/MarketRangeChart';
import { ScriptBlock } from '../components/negotiation/ScriptBlock';
import { FeedbackWidget } from '../components/shared/FeedbackWidget';
import { api, type Negotiation } from '../lib/api';

export default function NegotiationDetailPage() {
  const negId = useMemo(() => {
    const parts = window.location.pathname.split('/');
    return parts[parts.length - 1];
  }, []);

  const [neg, setNeg] = useState<Negotiation | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [regenerating, setRegenerating] = useState(false);
  const [feedbackInput, setFeedbackInput] = useState('');
  const [showRegenForm, setShowRegenForm] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const resp = await api.negotiations.get(negId);
      setNeg(resp.data);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [negId]);

  useEffect(() => {
    load();
  }, [load]);

  async function handleRegenerate() {
    setRegenerating(true);
    setError(null);
    try {
      const resp = await api.negotiations.regenerate(negId, feedbackInput || undefined);
      window.location.href = `/negotiations/${resp.data.id}`;
    } catch (e) {
      setError((e as Error).message);
      setRegenerating(false);
    }
  }

  if (loading) {
    return (
      <AppShell>
        <p className="text-sm text-[#787774]">Loading…</p>
      </AppShell>
    );
  }

  if (!neg) {
    return (
      <AppShell>
        <p className="text-sm text-[#e03e3e]">
          {error ?? 'Negotiation not found'}
        </p>
      </AppShell>
    );
  }

  const mr = neg.market_research;
  const co = neg.counter_offer;
  const scripts = neg.scripts;

  return (
    <AppShell>
      <div className="mx-auto max-w-3xl">
        <a href="/negotiations" className="text-sm text-[#2383e2]">
          ← Back to negotiations
        </a>
        <h1 className="mt-2 text-2xl font-semibold">Negotiation playbook</h1>

        <div className="mt-6">
          <MarketRangeChart
            low={mr.range_low}
            mid={mr.range_mid}
            high={mr.range_high}
            sourceNotes={mr.source_notes}
            comparableRoles={mr.comparable_roles}
          />
        </div>

        <section className="mt-6 rounded-lg border border-[#e3e2e0] bg-white p-4">
          <h2 className="text-sm font-semibold">Counter offer</h2>
          <dl className="mt-3 space-y-2 text-sm">
            <div className="flex justify-between">
              <dt className="text-[#787774]">Target</dt>
              <dd className="font-semibold text-[#35a849]">
                ${(co.target / 1000).toFixed(0)}k
              </dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-[#787774]">Minimum acceptable</dt>
              <dd className="font-semibold">
                ${(co.minimum_acceptable / 1000).toFixed(0)}k
              </dd>
            </div>
            <div>
              <dt className="text-[#787774]">Equity ask</dt>
              <dd className="text-[#37352f]">{co.equity_ask}</dd>
            </div>
          </dl>
          <p className="mt-3 text-xs text-[#787774]">{co.justification}</p>
        </section>

        <section className="mt-6 space-y-3">
          <h2 className="text-lg font-semibold">Scripts</h2>
          <ScriptBlock title="Email template" content={scripts.email_template} />
          <ScriptBlock title="Call script" content={scripts.call_script} />
        </section>

        {scripts.fallback_positions?.length > 0 && (
          <section className="mt-6">
            <h2 className="text-sm font-semibold">Fallback positions</h2>
            <ul className="mt-2 space-y-1 text-sm text-[#37352f]">
              {scripts.fallback_positions.map((f, i) => (
                <li key={i}>• {f}</li>
              ))}
            </ul>
          </section>
        )}

        {scripts.pitfalls?.length > 0 && (
          <section className="mt-6">
            <h2 className="text-sm font-semibold text-[#e03e3e]">Pitfalls to avoid</h2>
            <ul className="mt-2 space-y-1 text-sm text-[#37352f]">
              {scripts.pitfalls.map((p, i) => (
                <li key={i}>⚠ {p}</li>
              ))}
            </ul>
          </section>
        )}

        <section className="mt-6">
          {!showRegenForm ? (
            <button
              type="button"
              onClick={() => setShowRegenForm(true)}
              className="rounded border border-[#e3e2e0] px-3 py-1.5 text-sm"
            >
              Regenerate with feedback
            </button>
          ) : (
            <div className="rounded-lg border border-[#e3e2e0] bg-[#fbfbfa] p-4">
              <label className="text-sm font-medium">Feedback</label>
              <textarea
                value={feedbackInput}
                onChange={(e) => setFeedbackInput(e.target.value)}
                rows={3}
                placeholder="e.g. counter is too aggressive, scale back to $215k"
                className="mt-2 w-full rounded border border-[#e3e2e0] px-3 py-2 text-sm"
              />
              <div className="mt-2 flex gap-2">
                <button
                  type="button"
                  onClick={handleRegenerate}
                  disabled={regenerating}
                  className="rounded bg-[#2383e2] px-3 py-1.5 text-sm text-white disabled:opacity-50"
                >
                  {regenerating ? 'Generating…' : 'Regenerate'}
                </button>
                <button
                  type="button"
                  onClick={() => setShowRegenForm(false)}
                  className="rounded border border-[#e3e2e0] px-3 py-1.5 text-sm"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
        </section>

        <FeedbackWidget
          resourceType="negotiation"
          resourceId={neg.id}
          variant="expanded"
        />
      </div>
    </AppShell>
  );
}
```

- [ ] **Step 6: Update `App.tsx` — add negotiation routes**

```tsx
import NegotiationDetailPage from './pages/NegotiationDetailPage';
import NegotiationListPage from './pages/NegotiationListPage';

function matchRoute(pathname: string) {
  // existing routes...
  if (pathname === '/negotiations') return 'negotiation-list';
  if (pathname.startsWith('/negotiations/')) return 'negotiation-detail';
  // ...
}

// in render:
{route === 'negotiation-list' && <NegotiationListPage />}
{route === 'negotiation-detail' && <NegotiationDetailPage />}
```

- [ ] **Step 7: Update `AppShell.tsx` — add nav link**

```tsx
<a href="/negotiations" className="hover:text-[#37352f]">
  Negotiations
</a>
```

- [ ] **Step 8: Type check**

```bash
./node_modules/.bin/tsc --noEmit 2>&1 | tail -5
```

Expected: no errors.

- [ ] **Step 9: Checkpoint**

Checkpoint message: `feat(user-portal): add negotiation list + detail pages + OfferForm + MarketRangeChart + ScriptBlock`

---

## Task 25: Chat Cards — InterviewPrepCard + NegotiationCard + MessageList Wiring

**Files:**
- Create: `user-portal/src/components/chat/cards/InterviewPrepCard.tsx`
- Create: `user-portal/src/components/chat/cards/NegotiationCard.tsx`
- Modify: `user-portal/src/components/chat/MessageList.tsx`

- [ ] **Step 1: Create `InterviewPrepCard.tsx`**

```tsx
import { FeedbackWidget } from '../../shared/FeedbackWidget';

interface InterviewPrepCardData {
  interview_prep_id: string;
  job_id: string | null;
  role: string;
  question_count: number;
  top_questions: Array<{
    question: string;
    category: string;
    suggested_story_title: string | null;
  }>;
  red_flag_questions: Array<{
    question: string;
    what_to_listen_for: string;
  }>;
}

export function InterviewPrepCard({ data }: { data: InterviewPrepCardData }) {
  return (
    <article className="mt-3 rounded-lg border border-[#e3e2e0] bg-white p-4">
      <header>
        <h3 className="text-base font-semibold">
          Interview prep — {data.role}
        </h3>
        <p className="mt-1 text-xs text-[#787774]">
          {data.question_count} questions generated
        </p>
      </header>

      <ul className="mt-3 space-y-2">
        {data.top_questions.slice(0, 3).map((q, i) => (
          <li key={i} className="text-sm">
            <strong className="text-[#37352f]">{q.question}</strong>
            <div className="mt-1 flex items-center gap-2 text-xs text-[#787774]">
              <span className="rounded bg-[#f7f6f3] px-2 py-0.5">{q.category}</span>
              {q.suggested_story_title && (
                <span>Story: {q.suggested_story_title}</span>
              )}
            </div>
          </li>
        ))}
      </ul>

      <footer className="mt-3 flex gap-2">
        <a
          href={`/interview-prep/${data.interview_prep_id}`}
          className="rounded bg-[#2383e2] px-3 py-1 text-xs text-white"
        >
          View full prep
        </a>
      </footer>

      <FeedbackWidget
        resourceType="interview_prep"
        resourceId={data.interview_prep_id}
      />
    </article>
  );
}
```

- [ ] **Step 2: Create `NegotiationCard.tsx`**

The negotiation tool always returns `OFFER_DETAILS_REQUIRED`, so the card that renders from a successful tool call would be generated differently — via a direct REST call to `POST /negotiations`. The `NegotiationCard` here renders from the REST response shape.

But the more important case is the OfferForm hand-off. When the agent's tool result contains `error_code: "OFFER_DETAILS_REQUIRED"`, the chat needs to render an OfferForm inline. We handle that via a special `NegotiationCard` variant that inspects its data.

```tsx
import { useState } from 'react';

import { OfferForm } from '../../negotiation/OfferForm';
import { FeedbackWidget } from '../../shared/FeedbackWidget';

interface NegotiationCardData {
  // Existing playbook case (after REST POST /negotiations)
  negotiation_id?: string;
  job_title?: string;
  company?: string | null;
  market_range?: { low: number; mid: number; high: number };
  counter_offer?: { target: number; minimum: number; justification: string };
  scripts?: { email: string; call: string; fallbacks: string[] };
  // Offer-collection hand-off case (from agent tool error)
  offer_form_job_id?: string;
}

function fmt(n: number): string {
  return `$${(n / 1000).toFixed(0)}k`;
}

export function NegotiationCard({ data }: { data: NegotiationCardData }) {
  const [submitted, setSubmitted] = useState(false);

  // Hand-off from agent: render OfferForm inline
  if (data.offer_form_job_id && !submitted) {
    return (
      <article className="mt-3 rounded-lg border border-[#e3e2e0] bg-white p-4">
        <header>
          <h3 className="text-base font-semibold">Enter your offer details</h3>
          <p className="mt-1 text-xs text-[#787774]">
            The agent needs your specific offer numbers to generate a playbook.
          </p>
        </header>
        <div className="mt-3">
          <OfferForm
            jobId={data.offer_form_job_id}
            onSuccess={(neg) => {
              setSubmitted(true);
              window.location.href = `/negotiations/${neg.id}`;
            }}
            onCancel={() => setSubmitted(true)}
          />
        </div>
      </article>
    );
  }

  // Playbook-case: render the negotiation summary
  if (!data.negotiation_id) {
    return null;
  }

  return (
    <article className="mt-3 rounded-lg border border-[#e3e2e0] bg-white p-4">
      <header>
        <h3 className="text-base font-semibold">
          Negotiation playbook — {data.job_title ?? 'Offer'}
        </h3>
        {data.company && (
          <p className="mt-1 text-xs text-[#787774]">{data.company}</p>
        )}
      </header>

      {data.market_range && (
        <div className="mt-3 text-sm">
          <span className="text-[#787774]">Market range: </span>
          <strong>
            {fmt(data.market_range.low)} – {fmt(data.market_range.high)}
          </strong>
        </div>
      )}

      {data.counter_offer && (
        <div className="mt-2 text-sm">
          <span className="text-[#787774]">Counter target: </span>
          <strong className="text-[#35a849]">
            {fmt(data.counter_offer.target)}
          </strong>
        </div>
      )}

      <footer className="mt-3">
        <a
          href={`/negotiations/${data.negotiation_id}`}
          className="rounded bg-[#2383e2] px-3 py-1 text-xs text-white"
        >
          View full playbook
        </a>
      </footer>

      <FeedbackWidget
        resourceType="negotiation"
        resourceId={data.negotiation_id}
      />
    </article>
  );
}
```

- [ ] **Step 3: Wire new card types into `MessageList.tsx`**

Open `user-portal/src/components/chat/MessageList.tsx` and add the imports:

```tsx
import { InterviewPrepCard } from './cards/InterviewPrepCard';
import { NegotiationCard } from './cards/NegotiationCard';
```

Extend the card-type switch with two more branches (chain with the existing ternaries):

```tsx
card.type === 'interview_prep' ? (
  <InterviewPrepCard key={idx} data={card.data as any} />
) : card.type === 'negotiation' ? (
  <NegotiationCard key={idx} data={card.data as any} />
) : null,
```

- [ ] **Step 4: Handle the `OFFER_DETAILS_REQUIRED` tool error in the chat**

The backend's agent runner emits an AI message with an error note in the body when a tool fails — but the frontend needs to render the `NegotiationCard` with `offer_form_job_id` set when that specific error code appears. The cleanest path: the backend's `_summary_for_card` and error-response path in `graph.py` already produces a canned "I ran into an issue..." message. We augment that path in a minor modification to the backend: when the tool error code is `OFFER_DETAILS_REQUIRED`, emit a synthetic `negotiation` card with `offer_form_job_id` set instead of an error reply.

**Modify `backend/src/career_agent/core/agent/graph.py`** — in the `route_node` dispatch block, replace the branch that handles failed tool results with a version that special-cases `OFFER_DETAILS_REQUIRED`:

```python
        if tool_result.get("ok"):
            cards.append(tool_result["card"])
            reply_text = _summary_for_card(tool_result["card"])
        else:
            error_code = tool_result.get("error_code", "UNKNOWN")
            if error_code == "OFFER_DETAILS_REQUIRED":
                # Agent hand-off: emit a synthetic negotiation card that the
                # frontend will render as an OfferForm modal.
                offer_card = {
                    "type": "negotiation",
                    "data": {
                        "offer_form_job_id": tool_result.get("offer_form_job_id"),
                    },
                }
                cards.append(offer_card)
                reply_text = (
                    "I need your offer details to generate a negotiation playbook. "
                    "Please fill in the form below."
                )
            else:
                reply_text = (
                    f"I ran into an issue running that: "
                    f"{tool_result.get('message', 'unknown error')}. "
                    "Want to try something else?"
                )
```

- [ ] **Step 5: Type check + run backend + frontend tests**

```bash
cd ../backend
uv run pytest tests/ 2>&1 | tail -3
uv run ruff check src/ 2>&1 | tail -3
uv run mypy src/ 2>&1 | tail -3
cd ../user-portal
./node_modules/.bin/tsc --noEmit 2>&1 | tail -5
./node_modules/.bin/vitest run 2>&1 | tail -10
```

Expected: all passing + clean.

- [ ] **Step 6: Checkpoint**

Checkpoint message: `feat(user-portal): add InterviewPrepCard + NegotiationCard (with OfferForm hand-off) chat cards`

---

## Task 26: Frontend Tests for Phase 2d Components

**Files:**
- Create: `user-portal/src/components/shared/FeedbackWidget.test.tsx`
- Create: `user-portal/src/components/chat/cards/InterviewPrepCard.test.tsx`
- Create: `user-portal/src/components/chat/cards/NegotiationCard.test.tsx`
- Create: `user-portal/src/components/negotiation/OfferForm.test.tsx`
- Create: `user-portal/src/pages/StoryBankPage.test.tsx`
- Create: `user-portal/src/pages/InterviewPrepDetailPage.test.tsx`
- Create: `user-portal/src/pages/NegotiationDetailPage.test.tsx`

- [ ] **Step 1: Create `FeedbackWidget.test.tsx`**

```tsx
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { FeedbackWidget } from './FeedbackWidget';

const fetchMock = vi.fn();

beforeEach(() => {
  fetchMock.mockReset();
  vi.stubGlobal('fetch', fetchMock);
  vi.useFakeTimers();
});

function mockJson(body: unknown, status = 201) {
  return { ok: status < 400, status, json: async () => body };
}

describe('FeedbackWidget', () => {
  it('renders 5 stars initially with no rating', () => {
    render(<FeedbackWidget resourceType="evaluation" resourceId="eval-1" />);
    const stars = screen.getAllByRole('button', { name: /Rate \d star/i });
    expect(stars).toHaveLength(5);
  });

  it('posts to the right endpoint when a star is clicked', async () => {
    fetchMock.mockResolvedValueOnce(
      mockJson({
        data: {
          id: 'fb-1',
          user_id: 'u-1',
          resource_type: 'evaluation',
          resource_id: 'eval-1',
          rating: 4,
          correction_notes: null,
          created_at: new Date().toISOString(),
        },
      }),
    );

    render(<FeedbackWidget resourceType="evaluation" resourceId="eval-1" />);
    const star4 = screen.getByRole('button', { name: /Rate 4 stars/i });
    fireEvent.click(star4);

    // Advance timers past the debounce window
    vi.advanceTimersByTime(600);

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledTimes(1);
      const [url, init] = fetchMock.mock.calls[0];
      expect(url).toContain('/api/v1/evaluations/eval-1/feedback');
      expect(init.method).toBe('POST');
      const body = JSON.parse(init.body);
      expect(body.rating).toBe(4);
    });
  });

  it('debounces rapid star clicks into a single POST', async () => {
    fetchMock.mockResolvedValueOnce(
      mockJson({
        data: {
          id: 'fb-1',
          user_id: 'u-1',
          resource_type: 'evaluation',
          resource_id: 'eval-1',
          rating: 5,
          correction_notes: null,
          created_at: new Date().toISOString(),
        },
      }),
    );

    render(<FeedbackWidget resourceType="evaluation" resourceId="eval-1" />);
    fireEvent.click(screen.getByRole('button', { name: /Rate 3 stars/i }));
    fireEvent.click(screen.getByRole('button', { name: /Rate 4 stars/i }));
    fireEvent.click(screen.getByRole('button', { name: /Rate 5 stars/i }));

    vi.advanceTimersByTime(600);

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledTimes(1);
      const body = JSON.parse(fetchMock.mock.calls[0][1].body);
      expect(body.rating).toBe(5);
    });
  });
});
```

- [ ] **Step 2: Create `InterviewPrepCard.test.tsx`**

```tsx
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { InterviewPrepCard } from './InterviewPrepCard';

describe('InterviewPrepCard', () => {
  it('renders role title, question count, and top 3 questions', () => {
    render(
      <InterviewPrepCard
        data={{
          interview_prep_id: 'prep-1',
          job_id: null,
          role: 'Staff Engineer',
          question_count: 10,
          top_questions: [
            {
              question: 'Tell me about a migration you led',
              category: 'behavioral',
              suggested_story_title: 'Payments migration',
            },
            {
              question: 'Design a URL shortener at 1M QPS',
              category: 'technical',
              suggested_story_title: null,
            },
            {
              question: 'How do you handle team conflict?',
              category: 'behavioral',
              suggested_story_title: null,
            },
          ],
          red_flag_questions: [],
        }}
      />,
    );
    expect(screen.getByText(/Staff Engineer/i)).toBeInTheDocument();
    expect(screen.getByText('10 questions generated')).toBeInTheDocument();
    expect(
      screen.getByText(/Tell me about a migration/i),
    ).toBeInTheDocument();
  });

  it('shows a link to the full prep page', () => {
    render(
      <InterviewPrepCard
        data={{
          interview_prep_id: 'prep-1',
          job_id: null,
          role: 'SRE',
          question_count: 5,
          top_questions: [],
          red_flag_questions: [],
        }}
      />,
    );
    const link = screen.getByRole('link', { name: /view full prep/i });
    expect(link).toHaveAttribute('href', '/interview-prep/prep-1');
  });
});
```

- [ ] **Step 3: Create `NegotiationCard.test.tsx`**

```tsx
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { NegotiationCard } from './NegotiationCard';

describe('NegotiationCard', () => {
  it('renders the OfferForm when offer_form_job_id is set', () => {
    render(<NegotiationCard data={{ offer_form_job_id: 'job-1' }} />);
    expect(screen.getByText(/Enter your offer details/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /generate playbook/i })).toBeInTheDocument();
  });

  it('renders the playbook summary when negotiation_id is set', () => {
    render(
      <NegotiationCard
        data={{
          negotiation_id: 'neg-1',
          job_title: 'Senior Payments Engineer',
          company: 'Stripe',
          market_range: { low: 180000, mid: 210000, high: 240000 },
          counter_offer: {
            target: 225000,
            minimum: 205000,
            justification: 'Market data supports top of range',
          },
          scripts: {
            email: 'Thanks for the offer...',
            call: 'Opening: ...',
            fallbacks: [],
          },
        }}
      />,
    );
    expect(screen.getByText(/Senior Payments Engineer/i)).toBeInTheDocument();
    expect(screen.getByText(/Counter target/i)).toBeInTheDocument();
    expect(screen.getByText(/\$225k/)).toBeInTheDocument();
  });

  it('returns null when neither offer_form_job_id nor negotiation_id is set', () => {
    const { container } = render(<NegotiationCard data={{}} />);
    expect(container).toBeEmptyDOMElement();
  });
});
```

- [ ] **Step 4: Create `OfferForm.test.tsx`**

```tsx
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { OfferForm } from './OfferForm';

const fetchMock = vi.fn();

beforeEach(() => {
  fetchMock.mockReset();
  vi.stubGlobal('fetch', fetchMock);
});

function mockJson(body: unknown, status = 201) {
  return { ok: status < 400, status, json: async () => body };
}

describe('OfferForm', () => {
  it('posts offer details to /negotiations on submit', async () => {
    fetchMock.mockResolvedValueOnce(
      mockJson({
        data: {
          id: 'neg-1',
          user_id: 'u-1',
          job_id: 'job-1',
          offer_details: { base: 200000 },
          market_research: {
            range_low: 180000, range_mid: 210000, range_high: 240000,
            source_notes: 'x', comparable_roles: [],
          },
          counter_offer: { target: 225000, minimum_acceptable: 205000, equity_ask: 'x', justification: 'x' },
          scripts: { email_template: 'x', call_script: 'x', fallback_positions: [], pitfalls: [] },
          model_used: 'test', tokens_used: 100,
          created_at: new Date().toISOString(),
        },
      }),
    );
    const onSuccess = vi.fn();
    render(<OfferForm jobId="job-1" onSuccess={onSuccess} onCancel={vi.fn()} />);

    fireEvent.change(screen.getByPlaceholderText(/195000/i), { target: { value: '200000' } });
    fireEvent.click(screen.getByRole('button', { name: /generate playbook/i }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledTimes(1);
      const body = JSON.parse(fetchMock.mock.calls[0][1].body);
      expect(body.job_id).toBe('job-1');
      expect(body.offer_details.base).toBe(200000);
    });
  });

  it('calls onCancel when cancel is clicked', () => {
    const onCancel = vi.fn();
    render(<OfferForm jobId="job-1" onSuccess={vi.fn()} onCancel={onCancel} />);
    fireEvent.click(screen.getByRole('button', { name: /cancel/i }));
    expect(onCancel).toHaveBeenCalled();
  });
});
```

- [ ] **Step 5: Create `StoryBankPage.test.tsx`**

```tsx
import { render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import StoryBankPage from './StoryBankPage';

const fetchMock = vi.fn();

beforeEach(() => {
  fetchMock.mockReset();
  vi.stubGlobal('fetch', fetchMock);
});

function mockJson(body: unknown, status = 200) {
  return { ok: status < 400, status, json: async () => body };
}

describe('StoryBankPage', () => {
  it('renders stories from mocked API', async () => {
    fetchMock.mockResolvedValueOnce(
      mockJson({
        data: [
          {
            id: 's-1',
            user_id: 'u-1',
            title: 'Led payments migration',
            situation: 'Legacy monolith',
            task: 'Migrate',
            action: 'Strangler pattern',
            result: 'Zero downtime',
            reflection: null,
            tags: ['leadership'],
            source: 'ai_generated',
            created_at: new Date().toISOString(),
          },
        ],
      }),
    );

    render(<StoryBankPage />);
    await waitFor(() => {
      expect(screen.getByText(/Led payments migration/i)).toBeInTheDocument();
    });
  });

  it('shows the empty state when no stories', async () => {
    fetchMock.mockResolvedValueOnce(mockJson({ data: [] }));
    render(<StoryBankPage />);
    await waitFor(() => {
      expect(screen.getByText(/No stories yet/i)).toBeInTheDocument();
    });
  });
});
```

- [ ] **Step 6: Create `InterviewPrepDetailPage.test.tsx`**

```tsx
import { render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import InterviewPrepDetailPage from './InterviewPrepDetailPage';

const fetchMock = vi.fn();

beforeEach(() => {
  fetchMock.mockReset();
  vi.stubGlobal('fetch', fetchMock);
  Object.defineProperty(window, 'location', {
    value: { pathname: '/interview-prep/prep-1', href: '' },
    writable: true,
  });
});

function mockJson(body: unknown, status = 200) {
  return { ok: status < 400, status, json: async () => body };
}

describe('InterviewPrepDetailPage', () => {
  it('renders questions + red flag questions', async () => {
    fetchMock.mockResolvedValueOnce(
      mockJson({
        data: {
          id: 'prep-1',
          user_id: 'u-1',
          job_id: null,
          custom_role: 'Staff Engineer',
          questions: [
            {
              question: 'How do you prioritize work?',
              category: 'behavioral',
              suggested_story_title: null,
              framework: 'Describe a framework you use',
            },
          ],
          red_flag_questions: [
            {
              question: "What's the on-call burden like?",
              what_to_listen_for: 'Specific numbers',
            },
          ],
          model_used: 'claude-test',
          tokens_used: 1000,
          created_at: new Date().toISOString(),
        },
      }),
    );

    render(<InterviewPrepDetailPage />);
    await waitFor(() => {
      expect(screen.getByText('Staff Engineer')).toBeInTheDocument();
    });
    expect(
      screen.getByText(/How do you prioritize work\?/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/on-call burden/i),
    ).toBeInTheDocument();
  });
});
```

- [ ] **Step 7: Create `NegotiationDetailPage.test.tsx`**

```tsx
import { render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import NegotiationDetailPage from './NegotiationDetailPage';

const fetchMock = vi.fn();

beforeEach(() => {
  fetchMock.mockReset();
  vi.stubGlobal('fetch', fetchMock);
  Object.defineProperty(window, 'location', {
    value: { pathname: '/negotiations/neg-1', href: '' },
    writable: true,
  });
});

function mockJson(body: unknown, status = 200) {
  return { ok: status < 400, status, json: async () => body };
}

describe('NegotiationDetailPage', () => {
  it('renders market range, counter offer, and scripts', async () => {
    fetchMock.mockResolvedValueOnce(
      mockJson({
        data: {
          id: 'neg-1',
          user_id: 'u-1',
          job_id: 'job-1',
          offer_details: { base: 200000 },
          market_research: {
            range_low: 180000,
            range_mid: 210000,
            range_high: 240000,
            source_notes: 'Based on levels.fyi',
            comparable_roles: ['Stripe ~215k'],
          },
          counter_offer: {
            target: 225000,
            minimum_acceptable: 205000,
            equity_ask: '+$20k RSU',
            justification: 'Market data',
          },
          scripts: {
            email_template: 'Hi Recruiter, thanks for the offer...',
            call_script: 'Opening: I am excited...',
            fallback_positions: ['ask for signing bonus'],
            pitfalls: ['do not accept first counter'],
          },
          model_used: 'claude-test',
          tokens_used: 1000,
          created_at: new Date().toISOString(),
        },
      }),
    );

    render(<NegotiationDetailPage />);
    await waitFor(() => {
      expect(screen.getByText(/Counter offer/i)).toBeInTheDocument();
    });
    expect(screen.getByText(/\$225k/)).toBeInTheDocument();
    expect(screen.getByText(/Email template/i)).toBeInTheDocument();
    expect(screen.getByText(/thanks for the offer/i)).toBeInTheDocument();
    expect(screen.getByText(/Pitfalls to avoid/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 8: Run all frontend tests**

```bash
cd ../user-portal
./node_modules/.bin/vitest run 2>&1 | tail -25
```

Expected: all tests PASS (baseline 16 + ~10 new ≈ 26 total).

- [ ] **Step 9: Checkpoint**

Checkpoint message: `test(user-portal): add Phase 2d component + page tests`

---

## Task 27: End-to-End Smoke Test

**Files:**
- Create: `backend/tests/integration/test_phase2d_smoke.py`

- [ ] **Step 1: Create the smoke test**

```python
"""End-to-end Phase 2d smoke: interview prep → feedback → negotiation → link to application."""

import hashlib
import json
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select

from career_agent.db import get_session_factory
from career_agent.main import app
from career_agent.models.application import Application
from career_agent.models.interview_prep import InterviewPrep
from career_agent.models.job import Job
from career_agent.models.negotiation import Negotiation
from career_agent.models.star_story import StarStory
from career_agent.models.user import User
from tests.conftest import FAKE_CLAIMS
from tests.fixtures.fake_anthropic import fake_anthropic


_EXTRACT_RESPONSE = json.dumps(
    {
        "stories": [
            {
                "title": "Led payments migration",
                "situation": "Legacy monolith",
                "task": "Migrate without downtime",
                "action": "Strangler pattern",
                "result": "Zero downtime cutover",
                "reflection": "Would invest in observability earlier",
                "tags": ["leadership", "migration"],
            }
        ]
    }
)

_PREP_RESPONSE = json.dumps(
    {
        "questions": [
            {
                "question": "Tell me about a migration you led",
                "category": "behavioral",
                "suggested_story_title": "Led payments migration",
                "framework": "STAR",
            }
        ],
        "red_flag_questions": [
            {"question": "On-call burden?", "what_to_listen_for": "Specific numbers"}
        ],
    }
)

_NEG_RESPONSE = json.dumps(
    {
        "market_research": {
            "range_low": 180000,
            "range_mid": 210000,
            "range_high": 240000,
            "source_notes": "levels.fyi",
            "comparable_roles": ["Stripe ~215k"],
        },
        "counter_offer": {
            "target": 225000,
            "minimum_acceptable": 205000,
            "equity_ask": "+$20k RSU",
            "justification": "market data",
        },
        "scripts": {
            "email_template": "Thanks for the offer...",
            "call_script": "Opening: ...",
            "fallback_positions": ["signing bonus"],
            "pitfalls": ["don't accept first counter"],
        },
    }
)


async def _uid() -> UUID:
    factory = get_session_factory()
    async with factory() as s:
        r = await s.execute(select(User).where(User.cognito_sub == FAKE_CLAIMS["sub"]))
        return r.scalar_one().id


async def _reset_user_state(user_id: UUID) -> None:
    factory = get_session_factory()
    async with factory() as session:
        await session.execute(delete(Application).where(Application.user_id == user_id))
        await session.execute(delete(Negotiation).where(Negotiation.user_id == user_id))
        await session.execute(
            delete(InterviewPrep).where(InterviewPrep.user_id == user_id)
        )
        await session.execute(delete(StarStory).where(StarStory.user_id == user_id))
        await session.commit()


@pytest.mark.asyncio
async def test_phase2d_smoke_flow(auth_headers, seed_profile):
    uid = await _uid()
    await _reset_user_state(uid)

    factory = get_session_factory()

    # Seed a job + an application at "offered" status
    async with factory() as session:
        h = hashlib.sha256(f"2d-smoke-{uuid4()}".encode()).hexdigest()
        job = Job(
            content_hash=h,
            title="Senior Payments Engineer",
            description_md="Build payment systems at scale.",
            requirements_json={"skills": ["python"]},
            source="manual",
            company="Stripe",
            location="SF",
        )
        session.add(job)
        await session.flush()
        app_row = Application(user_id=uid, job_id=job.id, status="offered")
        session.add(app_row)
        await session.commit()
        job_id = job.id
        app_id = app_row.id

    # ---------- 1. Create interview prep (auto-populates story bank) ----------
    with (
        patch(
            "career_agent.integrations.cognito.CognitoJwtVerifier.verify",
            new=AsyncMock(return_value=FAKE_CLAIMS),
        ),
        fake_anthropic(
            {
                "RESUME": _EXTRACT_RESPONSE,
                "CANDIDATE RESUME": _PREP_RESPONSE,
            }
        ),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            r_prep = await client.post(
                "/api/v1/interview-preps",
                json={"job_id": str(job_id)},
                headers=auth_headers,
            )
    assert r_prep.status_code == 201
    prep_id = r_prep.json()["data"]["id"]

    # Story bank should now have 1 story
    async with factory() as session:
        stories = (
            (await session.execute(select(StarStory).where(StarStory.user_id == uid)))
            .scalars()
            .all()
        )
    assert len(stories) == 1
    assert stories[0].source == "ai_generated"

    # ---------- 2. Feedback on interview prep ----------
    with patch(
        "career_agent.integrations.cognito.CognitoJwtVerifier.verify",
        new=AsyncMock(return_value=FAKE_CLAIMS),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            r_fb = await client.post(
                f"/api/v1/interview-preps/{prep_id}/feedback",
                json={"rating": 4, "correction_notes": "Make questions harder"},
                headers=auth_headers,
            )
    assert r_fb.status_code == 201

    # ---------- 3. Create negotiation with offer details ----------
    with (
        patch(
            "career_agent.integrations.cognito.CognitoJwtVerifier.verify",
            new=AsyncMock(return_value=FAKE_CLAIMS),
        ),
        fake_anthropic({"INPUT:": _NEG_RESPONSE}),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            r_neg = await client.post(
                "/api/v1/negotiations",
                json={
                    "job_id": str(job_id),
                    "offer_details": {
                        "base": 195000,
                        "equity": "0.08%",
                        "location": "SF",
                    },
                },
                headers=auth_headers,
            )
    assert r_neg.status_code == 201
    neg_id = r_neg.json()["data"]["id"]

    # ---------- 4. Verify application.negotiation_id was populated ----------
    async with factory() as session:
        app_refreshed = (
            await session.execute(
                select(Application).where(Application.id == app_id)
            )
        ).scalar_one()
    assert str(app_refreshed.negotiation_id) == neg_id

    # ---------- 5. Feedback on negotiation ----------
    with patch(
        "career_agent.integrations.cognito.CognitoJwtVerifier.verify",
        new=AsyncMock(return_value=FAKE_CLAIMS),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            r_neg_fb = await client.post(
                f"/api/v1/negotiations/{neg_id}/feedback",
                json={"rating": 5},
                headers=auth_headers,
            )
    assert r_neg_fb.status_code == 201

    # ---------- 6. Verify everything is reachable via list endpoints ----------
    with patch(
        "career_agent.integrations.cognito.CognitoJwtVerifier.verify",
        new=AsyncMock(return_value=FAKE_CLAIMS),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            r_list_preps = await client.get(
                "/api/v1/interview-preps", headers=auth_headers
            )
            r_list_negs = await client.get("/api/v1/negotiations", headers=auth_headers)
            r_list_stories = await client.get(
                "/api/v1/star-stories", headers=auth_headers
            )

    assert r_list_preps.status_code == 200
    assert any(p["id"] == prep_id for p in r_list_preps.json()["data"])
    assert r_list_negs.status_code == 200
    assert any(n["id"] == neg_id for n in r_list_negs.json()["data"])
    assert r_list_stories.status_code == 200
    assert len(r_list_stories.json()["data"]) == 1
```

- [ ] **Step 2: Run the smoke test**

```bash
cd ../backend
uv run pytest tests/integration/test_phase2d_smoke.py -v 2>&1 | tail -15
```

Expected: PASS.

- [ ] **Step 3: Checkpoint**

Checkpoint message: `test(phase2d): end-to-end smoke covering prep → feedback → negotiation → application link`

---

## Task 28: Phase 2d Completion Verification

**Files:** None — checklist only.

- [ ] **Step 1: Run the full backend test suite**

```bash
cd backend
uv run pytest tests/ 2>&1 | tail -5
```

Expected: roughly **151+ passing** (133 Phase 2c baseline + ~18 new for Phase 2d).

- [ ] **Step 2: Backend lint + format + type check**

```bash
uv run ruff check src/ 2>&1 | tail -3
uv run black --check src/ 2>&1 | tail -3
uv run mypy src/ 2>&1 | tail -3
```

Expected: `All checks passed!`, clean black, clean mypy.

- [ ] **Step 3: Frontend tests + type check**

```bash
cd ../user-portal
./node_modules/.bin/vitest run 2>&1 | tail -10
./node_modules/.bin/tsc --noEmit 2>&1 | tail -5
```

Expected: ~26 tests passing, no type errors.

- [ ] **Step 4: pdf-render baseline still green**

```bash
cd ../pdf-render
./node_modules/.bin/vitest run 2>&1 | tail -10
```

Expected: 4 tests passing (unchanged).

- [ ] **Step 5: Completion checklist**

Verify every Phase 2d scope item is done:

- [ ] Migration `0006_phase2d_interview_prep_negotiation_feedback.py` creates 3 tables + the `applications.negotiation_id` FK
- [ ] `core/interview_prep/` — extractor + generator + service orchestrator
- [ ] `core/negotiation/` — playbook + service orchestrator with application auto-linking
- [ ] `core/feedback/` — generic service with 4 per-resource ownership validators
- [ ] `POST /api/v1/interview-preps` (paywalled), GET list + detail, POST regenerate (paywalled)
- [ ] `POST /api/v1/negotiations` (paywalled), GET list + detail, POST regenerate (paywalled)
- [ ] `POST /api/v1/star-stories` (non-paywalled), full CRUD with tag filter
- [ ] `POST /api/v1/{evaluations|cv-outputs|interview-preps|negotiations}/:id/feedback` — all 4 endpoints
- [ ] Agent tools `build_interview_prep_tool` + `generate_negotiation_playbook_tool` wired
- [ ] `NOT_YET_AVAILABLE_TEMPLATES` is now `{}` — agent has full 6-tool set
- [ ] System prompt references "SIX tools" instead of "FOUR"
- [ ] Graph dispatch handles both new tools + `OFFER_DETAILS_REQUIRED` hand-off emits a synthetic negotiation card
- [ ] Frontend: FeedbackWidget shared component mounted on EvaluationCard + CvOutputCard + InterviewPrepCard + NegotiationCard + 2 detail pages
- [ ] Frontend: StoryBankPage, InterviewPrepListPage, InterviewPrepDetailPage, NegotiationListPage, NegotiationDetailPage
- [ ] Frontend: OfferForm, MarketRangeChart, ScriptBlock, QuestionListItem, StarStoryCard, StarStoryEditor
- [ ] Frontend: InterviewPrepCard + NegotiationCard chat cards, MessageList handles both new card types
- [ ] Frontend: routes `/interview-prep`, `/interview-prep/story-bank`, `/interview-prep/:id`, `/negotiations`, `/negotiations/:id`
- [ ] Frontend: AppShell nav has Interview Prep + Negotiations links
- [ ] All backend tests pass
- [ ] All frontend tests pass
- [ ] mypy strict clean, ruff clean, black clean

- [ ] **Step 6: Checkpoint**

Checkpoint message: `chore(phase2d): complete Phase 2d — interview prep + negotiation + feedback + star stories CRUD`

---

## Phase 2d Summary

**What's built:**
- 3 new database tables (`interview_preps`, `negotiations`, `feedback`) + the `applications.negotiation_id` FK constraint that Phase 2c deferred
- `core/interview_prep/` — Claude story extractor (runs lazily once per user) + Claude question generator (Appendix D.6) + service orchestrator with job-id/custom-role XOR validation
- `core/negotiation/` — Claude playbook generator (Appendix D.7) + service orchestrator with automatic `applications.negotiation_id` linking
- `core/feedback/` — generic upsert service with 4 per-resource ownership validators dispatched by `resource_type`
- New API routers: interview_preps (create/list/get/regenerate), negotiations (create/list/get/regenerate), star_stories (full CRUD as Phase 1 backfill), feedback (4 endpoints)
- Agent tools: `build_interview_prep_tool` and `generate_negotiation_playbook_tool`. `NOT_YET_AVAILABLE_TEMPLATES` is now empty — the agent has the full 6-tool set documented in the parent spec.
- `OFFER_DETAILS_REQUIRED` hand-off pattern: the negotiation agent tool intentionally returns a non-`ok` result with this error code, and the graph dispatch emits a synthetic `negotiation` card with `offer_form_job_id` set so the frontend can render the OfferForm modal and submit via direct REST.
- Frontend: 5 new pages (InterviewPrepListPage, InterviewPrepDetailPage, StoryBankPage, NegotiationListPage, NegotiationDetailPage), shared FeedbackWidget mounted on 4 card types + 2 detail pages, OfferForm with validation, MarketRangeChart, ScriptBlock with copy-to-clipboard, QuestionListItem with category badges, StarStoryCard + StarStoryEditor, InterviewPrepCard + NegotiationCard chat cards
- ~18 new backend tests + ~10 new frontend tests
- Running total after 2d: ~151 backend tests, ~26 frontend tests

**What's deferred to later phases (Phase 5):**
- Multi-round negotiation chaining ("create a new negotiation with context from the previous one")
- Interview prep / negotiation PDF export
- Mock interview chat mode (multi-turn Q&A with Claude playing interviewer)
- Live compensation data API (levels.fyi, Glassdoor)
- Admin feedback review UI
- `POST /conversations/:id/actions` card action routing
- Calendar integration / scheduled interview reminders
- Voice or video coaching

**Next phase: 5** — real AWS deployment, full UX polish (slash commands, quick-action chips, card action routing, conversation summarization, admin UI build-out), scheduled scans (cron), annual billing plan, per-user cost quota enforcement, plus the deferred items from every prior phase. No feature modules left after 2d.

