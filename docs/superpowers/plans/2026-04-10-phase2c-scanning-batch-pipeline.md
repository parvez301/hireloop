# CareerAgent Phase 2c — Scanning + Batch + Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship Job Scanning (Greenhouse + Ashby + Lever adapters), Batch Processing (L0/L1/L2 funnel), and the Application Pipeline (kanban) — all end-to-end from the agent, REST endpoints, and a full frontend. Introduce Inngest as the async job runner for long-running fan-out work.

**Architecture:** New backend modules under `core/scanner/`, `core/batch/`, and `inngest/`. Single migration `0005_phase2c_scanning_batch_pipeline` creates 6 new tables. Frontend adds 4 new pages (ScansPage, ScanDetailPage, PipelinePage, ScanConfigEditor modal) + 4 new chat cards (ScanProgressCard, ScanResultsCard, BatchProgressCard, ApplicationStatusCard). Agent gets 2 new tools (`start_job_scan`, `start_batch_evaluation`). Scan runs + batch runs both execute as Inngest functions triggered by events; frontend polls progress endpoints every 3s.

**Tech Stack:** Python 3.12 + FastAPI + Inngest Python SDK 0.4 + httpx + BeautifulSoup4 + markdownify + tenacity + SQLAlchemy 2.0 async + Alembic. React 18 + Vite + TypeScript 5 + Tailwind + @dnd-kit/core (new dep for kanban drag-drop).

**Reference spec:** [`docs/superpowers/specs/2026-04-10-phase2c-scanning-batch-pipeline-design.md`](../specs/2026-04-10-phase2c-scanning-batch-pipeline-design.md) — **read it first**. This plan operationalizes that spec; the spec is the source of truth for any ambiguity.

**Parent spec:** [`docs/superpowers/specs/2026-04-10-careeragent-design.md`](../specs/2026-04-10-careeragent-design.md) — especially Appendix F (Inngest function signatures), Appendix M (default scan config), Appendix D.5 (L1 relevance prompt), Appendix D.8 (L0 rule filter), Appendix G (card payload schemas).

**Infra / spec prep (already applied in repo):** `docker-compose.yml` runs the `inngest` service on default `docker compose up` (no `profiles` gate). `backend/.env.example` includes Phase 2c Inngest + scanning env placeholders. The Phase 2c design spec includes §2.3 (Inngest signing-key security), corrected §11 text for `negotiation_id` vs Phase 2d, and clarified Greenhouse test fixtures (JSON API with optional HTML in fields).

**Phase 2c scope (what's IN):**

- Migration `0005_phase2c_scanning_batch_pipeline` with 6 new tables (`scan_configs`, `scan_runs`, `scan_results`, `batch_runs`, `batch_items`, `applications`)
- `core/scanner/` — BoardAdapter ABC, Greenhouse/Ashby/Lever concrete adapters, dedup, relevance scoring, default config, ScannerService
- `core/batch/` — L0 rule filter, L1 triage wrapper, L2 evaluate wrapper, funnel orchestrator, BatchService
- `inngest/` — Inngest client, `scan_boards_fn`, `batch_evaluate_fn`, function registry
- New API routers: `/scan-configs`, `/scan-runs`, `/batch-runs`, `/applications`, `/inngest`
- Agent tool additions: `start_job_scan_tool`, `start_batch_evaluation_tool`, graph dispatch updates, prompt updates
- Default 15-company scan config seeded at onboarding (`_on_onboarding_done` hook)
- Full frontend: ScansPage, ScanDetailPage, ScanConfigEditor modal, PipelinePage (6-column kanban with drag-drop), 4 new chat cards, polling hook
- ~35 new backend tests + 7 new frontend tests

**Phase 2c scope (what's OUT):**

- Scheduled scans (cron / Inngest cron trigger) — Phase 5
- Interview prep + Negotiation modules — Phase 2d
- `feedback` table + `POST /evaluations/:id/feedback` — Phase 2d
- `POST /conversations/:id/actions` card action routing — Phase 5
- LinkedIn / Workday / SmartRecruiters scrapers — post-MVP
- Playwright-based JS rendering for SPA job pages — Phase 5
- Batch cancellation mid-flight — Phase 5
- Real AWS deployment of Inngest — Phase 5
- `negotiations` table (but `applications.negotiation_id` column is added now as nullable to avoid a future migration)

### Git note

The project directory was not a git repo at the time of prior plans. Every task ends with a **Checkpoint** step. If you have initialized git, run `git add` + `git commit`. If not, treat the checkpoint as a pause point to review what you built.

### Execution order and mergeability

Tasks are ordered so each one leaves the system in a working state. Tasks 1–6 establish shared primitives (migration, models, schemas, Inngest client, HTTP helpers). Tasks 7–17 deliver the scanner end-to-end including the Inngest function. Tasks 18–22 deliver the batch funnel. Task 23 ships the Inngest serve endpoint. Task 24 ships applications CRUD. Tasks 25–26 wire the onboarding hook and agent tools. Tasks 27–31 deliver the frontend in four slices (API client, scan UI, chat cards, pipeline kanban). Task 32 covers frontend tests. Task 33 is an end-to-end smoke test. Task 34 is final verification.

You should be able to run `pytest backend/tests/` successfully after every task from T5 onward.

### Pipeline kanban is the last frontend slice

Per the Phase 2c design spec §4 open concerns, the pipeline kanban (Task 31) is deliberately sequenced last among the frontend tasks. If plan execution hits friction or runs low on context there, the kanban can be cleanly excised and revisited as a 2c.1 follow-up without breaking the rest — scanning, batch, and chat cards all work independently of `/pipeline`. Do not interleave kanban work with earlier frontend tasks.

---

## File Structure Plan

```
career-agent/
├── backend/
│   ├── pyproject.toml                                         [MODIFY T1]
│   ├── .env.example                                           [MODIFY T1]
│   ├── migrations/versions/
│   │   └── 0005_phase2c_scanning_batch_pipeline.py            [CREATE T2]
│   ├── src/career_agent/
│   │   ├── config.py                                          [MODIFY T1]
│   │   ├── main.py                                            [MODIFY T15, T16, T21, T23, T24]
│   │   ├── models/
│   │   │   ├── scan_config.py                                 [CREATE T3]
│   │   │   ├── scan_run.py                                    [CREATE T3]
│   │   │   ├── batch_run.py                                   [CREATE T3]
│   │   │   ├── application.py                                 [CREATE T3]
│   │   │   └── __init__.py                                    [MODIFY T3]
│   │   ├── schemas/
│   │   │   ├── scan_config.py                                 [CREATE T4]
│   │   │   ├── scan_run.py                                    [CREATE T4]
│   │   │   ├── batch_run.py                                   [CREATE T4]
│   │   │   └── application.py                                 [CREATE T4]
│   │   ├── inngest/
│   │   │   ├── __init__.py                                    [CREATE T5]
│   │   │   ├── client.py                                      [CREATE T5]
│   │   │   ├── scan_boards.py                                 [CREATE T17]
│   │   │   ├── batch_evaluate.py                              [CREATE T22]
│   │   │   └── functions.py                                   [CREATE T23]
│   │   ├── integrations/
│   │   │   └── board_http.py                                  [CREATE T6]
│   │   ├── core/
│   │   │   ├── scanner/
│   │   │   │   ├── __init__.py                                [CREATE T7]
│   │   │   │   ├── adapters/
│   │   │   │   │   ├── __init__.py                            [CREATE T7]
│   │   │   │   │   ├── base.py                                [CREATE T7]
│   │   │   │   │   ├── greenhouse.py                          [CREATE T8]
│   │   │   │   │   ├── ashby.py                               [CREATE T9]
│   │   │   │   │   └── lever.py                               [CREATE T10]
│   │   │   │   ├── dedup.py                                   [CREATE T11]
│   │   │   │   ├── relevance.py                               [CREATE T12]
│   │   │   │   ├── default_config.py                          [CREATE T13]
│   │   │   │   └── service.py                                 [CREATE T14]
│   │   │   ├── batch/
│   │   │   │   ├── __init__.py                                [CREATE T18]
│   │   │   │   ├── l0_filter.py                               [CREATE T18]
│   │   │   │   ├── l1_triage.py                               [CREATE T19]
│   │   │   │   ├── l2_evaluate.py                             [CREATE T19]
│   │   │   │   ├── funnel.py                                  [CREATE T19]
│   │   │   │   └── service.py                                 [CREATE T20]
│   │   │   └── agent/
│   │   │       ├── tools.py                                   [MODIFY T26]
│   │   │       ├── graph.py                                   [MODIFY T26]
│   │   │       └── prompts.py                                 [MODIFY T26]
│   │   ├── services/
│   │   │   ├── scan_config.py                                 [CREATE T13]
│   │   │   ├── scan_run.py                                    [CREATE T14]
│   │   │   ├── batch_run.py                                   [CREATE T20]
│   │   │   ├── application.py                                 [CREATE T24]
│   │   │   └── profile.py                                     [MODIFY T25]
│   │   └── api/
│   │       ├── scan_configs.py                                [CREATE T15]
│   │       ├── scan_runs.py                                   [CREATE T16]
│   │       ├── batch_runs.py                                  [CREATE T21]
│   │       ├── applications.py                                [CREATE T24]
│   │       └── inngest.py                                     [CREATE T23]
│   └── tests/
│       ├── fixtures/
│       │   └── boards/
│       │       ├── greenhouse/
│       │       │   └── stripe.json                            [CREATE T8]
│       │       ├── ashby/
│       │       │   └── linear.json                            [CREATE T9]
│       │       └── lever/
│       │           └── shopify.json                           [CREATE T10]
│       ├── unit/
│       │   ├── test_board_base.py                             [CREATE T7]
│       │   ├── test_greenhouse_adapter.py                     [CREATE T8]
│       │   ├── test_ashby_adapter.py                           [CREATE T9]
│       │   ├── test_lever_adapter.py                          [CREATE T10]
│       │   ├── test_scanner_dedup.py                          [CREATE T11]
│       │   ├── test_scanner_relevance.py                      [CREATE T12]
│       │   ├── test_default_scan_config.py                    [CREATE T13]
│       │   └── test_l0_filter.py                              [CREATE T18]
│       └── integration/
│           ├── test_scan_configs_crud.py                      [CREATE T15]
│           ├── test_scan_run_trigger.py                       [CREATE T16]
│           ├── test_scanner_service_e2e.py                    [CREATE T14]
│           ├── test_scanner_service_adapter_failure.py        [CREATE T14]
│           ├── test_scanner_service_500_cap.py                [CREATE T14]
│           ├── test_batch_l1_triage.py                        [CREATE T19]
│           ├── test_batch_funnel.py                           [CREATE T19]
│           ├── test_batch_service_inputs.py                   [CREATE T20]
│           ├── test_batch_runs_crud.py                        [CREATE T21]
│           ├── test_batch_runs_scan_run_id.py                 [CREATE T21]
│           ├── test_inngest_scan_function.py                  [CREATE T17]
│           ├── test_inngest_batch_function.py                 [CREATE T22]
│           ├── test_inngest_serve_endpoint.py                 [CREATE T23]
│           ├── test_applications_crud.py                      [CREATE T24]
│           ├── test_applications_filters.py                   [CREATE T24]
│           ├── test_default_config_seed_onboarding.py         [CREATE T25]
│           ├── test_agent_scan_tool.py                        [CREATE T26]
│           ├── test_agent_batch_tool.py                       [CREATE T26]
│           └── test_phase2c_smoke.py                          [CREATE T33]
│
├── user-portal/
│   ├── package.json                                           [MODIFY T27]
│   ├── src/
│   │   ├── App.tsx                                            [MODIFY T28, T31]
│   │   ├── components/layout/AppShell.tsx                     [MODIFY T28, T31]
│   │   ├── lib/
│   │   │   ├── api.ts                                         [MODIFY T27]
│   │   │   └── polling.ts                                     [CREATE T27]
│   │   ├── pages/
│   │   │   ├── ScansPage.tsx                                  [CREATE T28]
│   │   │   ├── ScanDetailPage.tsx                             [CREATE T29]
│   │   │   ├── ScanConfigEditor.tsx                           [CREATE T28]
│   │   │   └── PipelinePage.tsx                               [CREATE T31]
│   │   └── components/
│   │       ├── chat/cards/
│   │       │   ├── ScanProgressCard.tsx                       [CREATE T30]
│   │       │   ├── ScanResultsCard.tsx                        [CREATE T30]
│   │       │   ├── BatchProgressCard.tsx                      [CREATE T30]
│   │       │   └── ApplicationStatusCard.tsx                  [CREATE T31]
│   │       └── pipeline/
│   │           ├── KanbanColumn.tsx                           [CREATE T31]
│   │           ├── ApplicationCard.tsx                        [CREATE T31]
│   │           └── PipelineFilters.tsx                        [CREATE T31]
│   └── src/                                                   [test files in T32]
│       ├── pages/
│       │   ├── ScansPage.test.tsx                             [CREATE T32]
│       │   ├── ScanDetailPage.test.tsx                        [CREATE T32]
│       │   └── PipelinePage.test.tsx                          [CREATE T32]
│       └── components/
│           ├── chat/cards/
│           │   ├── BatchProgressCard.test.tsx                 [CREATE T32]
│           │   ├── ScanProgressCard.test.tsx                  [CREATE T32]
│           │   └── ScanResultsCard.test.tsx                   [CREATE T32]
│           └── pipeline/
│               └── PipelineFilters.test.tsx                   [CREATE T32]
│
├── docker-compose.yml                                         [MODIFY T1]
└── docs/superpowers/plans/
    └── 2026-04-10-phase2c-scanning-batch-pipeline.md          [THIS FILE]
```

---

## Task 1: Dependencies + Environment Variables + docker-compose

**Files:**
- Modify: `backend/pyproject.toml`
- Modify: `backend/.env.example`
- Modify: `backend/src/career_agent/config.py`
- Modify: `docker-compose.yml`

- [ ] **Step 1: Add Phase 2c Python dependencies**

Open `backend/pyproject.toml` and add these entries under `[project].dependencies` (merge with existing list):

```toml
"inngest>=0.4,<0.5",
"markdownify>=0.13,<0.14",
```

Under `[tool.mypy.overrides]`, extend the list with `inngest.*`:

```toml
[[tool.mypy.overrides]]
module = ["boto3.*", "botocore.*", "docx.*", "pypdf.*", "stripe.*", "inngest.*"]
ignore_missing_imports = true
```

- [ ] **Step 2: Sync dependencies**

```bash
cd backend
uv sync
```

Expected: installs `inngest` and `markdownify`, updates `uv.lock`. No test runs yet.

- [ ] **Step 3: Extend `backend/.env.example`**

Append to `backend/.env.example`:

```bash
# ==========================================
# Phase 2c — Inngest
# ==========================================
INNGEST_EVENT_KEY=                               # Empty in dev; populated from Inngest Cloud in prod
INNGEST_SIGNING_KEY=                             # Empty in dev; required in prod
INNGEST_DEV=1                                    # 1 in dev to use the local dev server
FEATURE_SCAN_SCHEDULING=false                    # Ignored in 2c; reserved for Phase 5

# ==========================================
# Phase 2c — Scanning limits
# ==========================================
SCAN_MAX_LISTINGS_PER_RUN=500
SCAN_BOARD_RATE_LIMIT_REQS_PER_SEC=1
SCAN_L1_CONCURRENCY=5
BATCH_L2_CONCURRENCY=10
BATCH_L1_RELEVANCE_THRESHOLD=0.5
```

- [ ] **Step 4: Extend `Settings` in `backend/src/career_agent/config.py`**

Add the new fields to the `Settings` class (preserve existing fields). The Pydantic settings class uses snake_case attribute names mapped to uppercase env vars:

```python
# ---- Inngest ----
inngest_event_key: str = ""
inngest_signing_key: str = ""
inngest_dev: bool = True
feature_scan_scheduling: bool = False

# ---- Scanning limits ----
scan_max_listings_per_run: int = 500
scan_board_rate_limit_reqs_per_sec: float = 1.0
scan_l1_concurrency: int = 5
batch_l2_concurrency: int = 10
batch_l1_relevance_threshold: float = 0.5
```

- [ ] **Step 5: Update `docker-compose.yml`**

Ensure the `inngest` service has **no** `profiles:` gate so it starts on default `docker compose up`. If `profiles: ["inngest"]` is still present, remove it. The repo may already match this (comment above service is optional). Expected shape:

```yaml
  # Inngest dev server (Phase 2c). On default `docker compose up` …
  inngest:
    image: inngest/inngest:latest
    ports: ["8288:8288"]
    command: inngest dev -u http://host.docker.internal:8000/api/v1/inngest
    extra_hosts:
      - host.docker.internal:host-gateway
```

Save the file.

- [ ] **Step 6: Verify config loads**

```bash
cd backend
uv run python -c "from career_agent.config import get_settings; s = get_settings(); print(s.scan_max_listings_per_run, s.batch_l1_relevance_threshold)"
```

Expected: `500 0.5`

- [ ] **Step 7: Verify the existing test suite still passes**

```bash
uv run pytest tests/ 2>&1 | tail -5
```

Expected: `99 passed` (baseline from Phase 2b; no new tests yet).

- [ ] **Step 8: Checkpoint**

Checkpoint message: `chore(phase2c): add inngest + markdownify deps + scanning limits config`

---

## Task 2: Alembic Migration 0005 — 6 New Tables

**Files:**
- Create: `backend/migrations/versions/0005_phase2c_scanning_batch_pipeline.py`

- [ ] **Step 1: Create the migration file**

Create `backend/migrations/versions/0005_phase2c_scanning_batch_pipeline.py`:

```python
"""phase2c_scanning_batch_pipeline

Revision ID: 0005_phase2c
Revises: 0004_phase2b1
Create Date: 2026-04-10

Adds scan_configs, scan_runs, scan_results, batch_runs, batch_items,
applications tables with their indexes.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_phase2c"
down_revision: Union[str, None] = "0004_phase2b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ---------- scan_configs ----------
    op.create_table(
        "scan_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("companies", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("keywords", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("exclude_keywords", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "schedule",
            sa.String(32),
            nullable=False,
            server_default=sa.text("'manual'"),
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_scan_configs_user_id", "scan_configs", ["user_id"])

    # ---------- scan_runs ----------
    op.create_table(
        "scan_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scan_config_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("inngest_event_id", sa.String(255), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("jobs_found", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("jobs_new", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("truncated", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["scan_config_id"], ["scan_configs.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_scan_runs_user_id", "scan_runs", ["user_id"])
    op.create_index("idx_scan_runs_status", "scan_runs", ["status"])
    op.create_index(
        "idx_scan_runs_user_started",
        "scan_runs",
        ["user_id", sa.text("started_at DESC")],
    )

    # ---------- scan_results ----------
    op.create_table(
        "scan_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scan_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("relevance_score", sa.Float(), nullable=True),
        sa.Column("is_new", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["scan_run_id"], ["scan_runs.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("scan_run_id", "job_id", name="uq_scan_results_run_job"),
    )
    op.create_index("idx_scan_results_run_id", "scan_results", ["scan_run_id"])
    op.create_index(
        "idx_scan_results_run_score",
        "scan_results",
        ["scan_run_id", sa.text("relevance_score DESC NULLS LAST")],
    )

    # ---------- batch_runs ----------
    op.create_table(
        "batch_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("inngest_event_id", sa.String(255), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("total_jobs", sa.Integer(), nullable=False),
        sa.Column("l0_passed", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("l1_passed", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("l2_evaluated", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("source_type", sa.String(32), nullable=False),
        sa.Column("source_ref", sa.String(255), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_batch_runs_user_id", "batch_runs", ["user_id"])
    op.create_index(
        "idx_batch_runs_user_started",
        "batch_runs",
        ["user_id", sa.text("started_at DESC")],
    )

    # ---------- batch_items ----------
    op.create_table(
        "batch_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("batch_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("evaluation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("stage", sa.String(32), nullable=False),
        sa.Column("filter_reason", sa.String(64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["batch_run_id"], ["batch_runs.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["evaluation_id"], ["evaluations.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_batch_items_run_id", "batch_items", ["batch_run_id"])
    op.create_index(
        "idx_batch_items_run_stage",
        "batch_items",
        ["batch_run_id", "stage"],
    )

    # ---------- applications ----------
    op.create_table(
        "applications",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("evaluation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("cv_output_id", postgresql.UUID(as_uuid=True), nullable=True),
        # Nullable FK-less column for Phase 2d — negotiations table doesn't exist yet.
        # The FK constraint is added in Phase 2d's migration alongside the negotiations table.
        sa.Column("negotiation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["evaluation_id"], ["evaluations.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["cv_output_id"], ["cv_outputs.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "job_id", name="uq_applications_user_job"),
    )
    op.create_index("idx_applications_user_id", "applications", ["user_id"])
    op.create_index(
        "idx_applications_user_status",
        "applications",
        ["user_id", "status"],
    )
    op.create_index(
        "idx_applications_updated",
        "applications",
        [sa.text("updated_at DESC")],
    )


def downgrade() -> None:
    op.drop_index("idx_applications_updated", table_name="applications")
    op.drop_index("idx_applications_user_status", table_name="applications")
    op.drop_index("idx_applications_user_id", table_name="applications")
    op.drop_table("applications")

    op.drop_index("idx_batch_items_run_stage", table_name="batch_items")
    op.drop_index("idx_batch_items_run_id", table_name="batch_items")
    op.drop_table("batch_items")

    op.drop_index("idx_batch_runs_user_started", table_name="batch_runs")
    op.drop_index("idx_batch_runs_user_id", table_name="batch_runs")
    op.drop_table("batch_runs")

    op.drop_index("idx_scan_results_run_score", table_name="scan_results")
    op.drop_index("idx_scan_results_run_id", table_name="scan_results")
    op.drop_table("scan_results")

    op.drop_index("idx_scan_runs_user_started", table_name="scan_runs")
    op.drop_index("idx_scan_runs_status", table_name="scan_runs")
    op.drop_index("idx_scan_runs_user_id", table_name="scan_runs")
    op.drop_table("scan_runs")

    op.drop_index("idx_scan_configs_user_id", table_name="scan_configs")
    op.drop_table("scan_configs")
```

- [ ] **Step 2: Run the migration up / down / up**

You'll need to set the same env vars the test conftest sets. Run from `backend/`:

```bash
ENVIRONMENT=test \
COGNITO_USER_POOL_ID=us-east-1_test \
COGNITO_CLIENT_ID=testclient \
COGNITO_REGION=us-east-1 \
COGNITO_JWKS_URL=http://localhost/jwks \
ANTHROPIC_API_KEY=test \
GOOGLE_API_KEY=test \
CORS_ORIGINS=http://localhost:5173 \
DATABASE_URL=postgresql+asyncpg://$(whoami)@localhost:5432/career_agent \
REDIS_URL=redis://localhost:6379/0 \
APP_URL=http://localhost:5173 \
STRIPE_SECRET_KEY=sk_test \
STRIPE_WEBHOOK_SECRET=whsec \
STRIPE_PRICE_PRO_MONTHLY=price_test \
uv run alembic upgrade head

# then down and back up:
ENVIRONMENT=test COGNITO_USER_POOL_ID=us-east-1_test COGNITO_CLIENT_ID=testclient \
COGNITO_REGION=us-east-1 COGNITO_JWKS_URL=http://localhost/jwks \
ANTHROPIC_API_KEY=test GOOGLE_API_KEY=test CORS_ORIGINS=http://localhost:5173 \
DATABASE_URL=postgresql+asyncpg://$(whoami)@localhost:5432/career_agent \
REDIS_URL=redis://localhost:6379/0 APP_URL=http://localhost:5173 \
STRIPE_SECRET_KEY=sk_test STRIPE_WEBHOOK_SECRET=whsec \
STRIPE_PRICE_PRO_MONTHLY=price_test \
uv run alembic downgrade -1

# and up again
ENVIRONMENT=test COGNITO_USER_POOL_ID=us-east-1_test COGNITO_CLIENT_ID=testclient \
COGNITO_REGION=us-east-1 COGNITO_JWKS_URL=http://localhost/jwks \
ANTHROPIC_API_KEY=test GOOGLE_API_KEY=test CORS_ORIGINS=http://localhost:5173 \
DATABASE_URL=postgresql+asyncpg://$(whoami)@localhost:5432/career_agent \
REDIS_URL=redis://localhost:6379/0 APP_URL=http://localhost:5173 \
STRIPE_SECRET_KEY=sk_test STRIPE_WEBHOOK_SECRET=whsec \
STRIPE_PRICE_PRO_MONTHLY=price_test \
uv run alembic upgrade head
```

Expected: each command prints `Running upgrade/downgrade 0004_phase2b1 <-> 0005_phase2c, phase2c_scanning_batch_pipeline` and exits 0. After the final `upgrade`, all 6 new tables exist.

- [ ] **Step 3: Checkpoint**

Checkpoint message: `feat(db): add Phase 2c tables (scan_configs, scan_runs, scan_results, batch_runs, batch_items, applications)`

---

## Task 3: SQLAlchemy Models for Phase 2c

**Files:**
- Create: `backend/src/career_agent/models/scan_config.py`
- Create: `backend/src/career_agent/models/scan_run.py`
- Create: `backend/src/career_agent/models/batch_run.py`
- Create: `backend/src/career_agent/models/application.py`
- Modify: `backend/src/career_agent/models/__init__.py`

- [ ] **Step 1: Create `backend/src/career_agent/models/scan_config.py`**

```python
"""ScanConfig — per-user saved scan configuration."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from career_agent.models.base import Base


class ScanConfig(Base):
    __tablename__ = "scan_configs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    companies: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    keywords: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    exclude_keywords: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    schedule: Mapped[str] = mapped_column(
        String(32), nullable=False, default="manual", server_default="manual"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
```

- [ ] **Step 2: Create `backend/src/career_agent/models/scan_run.py`**

```python
"""ScanRun + ScanResult — each execution of a scan config."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from career_agent.models.base import Base


class ScanRun(Base):
    __tablename__ = "scan_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    scan_config_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("scan_configs.id", ondelete="CASCADE"),
        nullable=False,
    )
    inngest_event_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)  # 'pending'|'running'|'completed'|'failed'
    jobs_found: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    jobs_new: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    truncated: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ScanResult(Base):
    __tablename__ = "scan_results"
    __table_args__ = (
        UniqueConstraint("scan_run_id", "job_id", name="uq_scan_results_run_job"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    scan_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("scan_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    relevance_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_new: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
```

- [ ] **Step 3: Create `backend/src/career_agent/models/batch_run.py`**

```python
"""BatchRun + BatchItem — L0/L1/L2 funnel execution."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from career_agent.models.base import Base


class BatchRun(Base):
    __tablename__ = "batch_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    inngest_event_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    total_jobs: Mapped[int] = mapped_column(Integer, nullable=False)
    l0_passed: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    l1_passed: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    l2_evaluated: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)  # 'job_urls'|'job_ids'|'scan_run_id'
    source_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class BatchItem(Base):
    __tablename__ = "batch_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    batch_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("batch_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    evaluation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evaluations.id", ondelete="SET NULL"),
        nullable=True,
    )
    stage: Mapped[str] = mapped_column(String(32), nullable=False)  # 'queued'|'l0'|'l1'|'l2'|'done'|'filtered'
    filter_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
```

- [ ] **Step 4: Create `backend/src/career_agent/models/application.py`**

```python
"""Application — user's job application pipeline entry."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from career_agent.models.base import Base


class Application(Base):
    __tablename__ = "applications"
    __table_args__ = (
        UniqueConstraint("user_id", "job_id", name="uq_applications_user_job"),
    )

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
    status: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # 'saved'|'applied'|'interviewing'|'offered'|'rejected'|'withdrawn'
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    evaluation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evaluations.id", ondelete="SET NULL"),
        nullable=True,
    )
    cv_output_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cv_outputs.id", ondelete="SET NULL"),
        nullable=True,
    )
    # No FK — the negotiations table doesn't exist until Phase 2d.
    negotiation_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
```

- [ ] **Step 5: Update `backend/src/career_agent/models/__init__.py`**

Append to the existing imports:

```python
from career_agent.models.scan_config import ScanConfig  # noqa: F401
from career_agent.models.scan_run import ScanRun, ScanResult  # noqa: F401
from career_agent.models.batch_run import BatchRun, BatchItem  # noqa: F401
from career_agent.models.application import Application  # noqa: F401
```

- [ ] **Step 6: Verify models import**

```bash
uv run python -c "from career_agent.models import ScanConfig, ScanRun, ScanResult, BatchRun, BatchItem, Application; print('ok')"
```

Expected: `ok`

- [ ] **Step 7: Run the full test suite**

```bash
uv run pytest tests/ 2>&1 | tail -5
```

Expected: `99 passed` (no regressions; no new tests yet).

- [ ] **Step 8: Checkpoint**

Checkpoint message: `feat(models): add Phase 2c SQLAlchemy models`

---

## Task 4: Pydantic Schemas for Phase 2c

**Files:**
- Create: `backend/src/career_agent/schemas/scan_config.py`
- Create: `backend/src/career_agent/schemas/scan_run.py`
- Create: `backend/src/career_agent/schemas/batch_run.py`
- Create: `backend/src/career_agent/schemas/application.py`

- [ ] **Step 1: Create `backend/src/career_agent/schemas/scan_config.py`**

```python
from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CompanyRef(BaseModel):
    name: str
    platform: Literal["greenhouse", "ashby", "lever"]
    board_slug: str


class ScanConfigCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    companies: list[CompanyRef] = Field(..., min_length=1)
    keywords: list[str] | None = None
    exclude_keywords: list[str] | None = None
    schedule: Literal["manual", "daily", "weekly"] = "manual"


class ScanConfigUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    companies: list[CompanyRef] | None = None
    keywords: list[str] | None = None
    exclude_keywords: list[str] | None = None
    schedule: Literal["manual", "daily", "weekly"] | None = None
    is_active: bool | None = None


class ScanConfigOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    name: str
    companies: list[dict]
    keywords: list[str] | None
    exclude_keywords: list[str] | None
    schedule: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
```

- [ ] **Step 2: Create `backend/src/career_agent/schemas/scan_run.py`**

```python
from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ScanRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    scan_config_id: UUID
    status: Literal["pending", "running", "completed", "failed"]
    jobs_found: int
    jobs_new: int
    truncated: bool
    error: str | None
    started_at: datetime
    completed_at: datetime | None


class ScanResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    job_id: UUID
    relevance_score: float | None
    is_new: bool
    created_at: datetime


class ScanRunDetail(BaseModel):
    scan_run: ScanRunOut
    results: list[ScanResultOut]
```

- [ ] **Step 3: Create `backend/src/career_agent/schemas/batch_run.py`**

```python
from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class BatchRunCreate(BaseModel):
    job_urls: list[str] | None = None
    job_ids: list[UUID] | None = None
    scan_run_id: UUID | None = None

    @model_validator(mode="after")
    def _exactly_one_input(self) -> "BatchRunCreate":
        provided = [
            x is not None for x in (self.job_urls, self.job_ids, self.scan_run_id)
        ]
        if sum(provided) != 1:
            raise ValueError(
                "Provide exactly one of job_urls, job_ids, or scan_run_id"
            )
        return self


class BatchRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    status: Literal["pending", "running", "completed", "failed"]
    total_jobs: int
    l0_passed: int
    l1_passed: int
    l2_evaluated: int
    source_type: str
    source_ref: str | None
    started_at: datetime
    completed_at: datetime | None


class BatchItemsSummary(BaseModel):
    queued: int = 0
    l0: int = 0
    l1: int = 0
    l2: int = 0
    done: int = 0
    filtered: int = 0


class BatchEvaluationSummary(BaseModel):
    evaluation_id: UUID
    job_id: UUID
    job_title: str
    company: str | None
    overall_grade: str
    match_score: float


class BatchRunDetail(BaseModel):
    batch_run: BatchRunOut
    items_summary: BatchItemsSummary
    top_results: list[BatchEvaluationSummary] = Field(default_factory=list)
```

- [ ] **Step 4: Create `backend/src/career_agent/schemas/application.py`**

```python
from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

ApplicationStatus = Literal[
    "saved", "applied", "interviewing", "offered", "rejected", "withdrawn"
]


class ApplicationCreate(BaseModel):
    job_id: UUID
    status: ApplicationStatus = "saved"
    evaluation_id: UUID | None = None
    cv_output_id: UUID | None = None
    notes: str | None = None


class ApplicationUpdate(BaseModel):
    status: ApplicationStatus | None = None
    notes: str | None = None
    applied_at: datetime | None = None
    cv_output_id: UUID | None = None


class ApplicationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    job_id: UUID
    status: ApplicationStatus
    applied_at: datetime | None
    notes: str | None
    evaluation_id: UUID | None
    cv_output_id: UUID | None
    negotiation_id: UUID | None
    updated_at: datetime
```

- [ ] **Step 5: Verify schemas import**

```bash
uv run python -c "from career_agent.schemas.scan_config import ScanConfigOut; from career_agent.schemas.scan_run import ScanRunDetail; from career_agent.schemas.batch_run import BatchRunDetail; from career_agent.schemas.application import ApplicationOut; print('ok')"
```

Expected: `ok`

- [ ] **Step 6: Run pytest + lint + typecheck**

```bash
uv run pytest tests/ 2>&1 | tail -3; uv run ruff check src/ 2>&1 | tail -3; uv run mypy src/ 2>&1 | tail -3
```

Expected: `99 passed`, `All checks passed!`, `Success: no issues found`.

- [ ] **Step 7: Checkpoint**

Checkpoint message: `feat(schemas): add Phase 2c Pydantic schemas`

---

## Task 5: Inngest Client Module

**Files:**
- Create: `backend/src/career_agent/inngest/__init__.py`
- Create: `backend/src/career_agent/inngest/client.py`

- [ ] **Step 1: Create `backend/src/career_agent/inngest/__init__.py`**

```python
"""Inngest integration — client + function definitions."""
```

- [ ] **Step 2: Create `backend/src/career_agent/inngest/client.py`**

```python
"""Inngest client singleton.

Uses dev mode (no signing key required) when INNGEST_DEV=true. In production,
both INNGEST_EVENT_KEY and INNGEST_SIGNING_KEY must be populated.
"""
from __future__ import annotations

from functools import lru_cache

import inngest

from career_agent.config import get_settings


@lru_cache(maxsize=1)
def get_inngest_client() -> inngest.Inngest:
    settings = get_settings()
    return inngest.Inngest(
        app_id="career-agent",
        event_key=settings.inngest_event_key or None,
        signing_key=settings.inngest_signing_key or None,
        is_production=not settings.inngest_dev,
    )
```

- [ ] **Step 3: Verify import**

```bash
uv run python -c "from career_agent.inngest.client import get_inngest_client; c = get_inngest_client(); print('ok', c.app_id)"
```

Expected: `ok career-agent`

- [ ] **Step 4: Checkpoint**

Checkpoint message: `feat(inngest): add Inngest client singleton`

---

## Task 6: Shared Board HTTP Helper + Rate Limiter

**Files:**
- Create: `backend/src/career_agent/integrations/board_http.py`

- [ ] **Step 1: Create `backend/src/career_agent/integrations/board_http.py`**

```python
"""Shared httpx client for public job-board APIs.

Applies a per-platform token-bucket rate limit so we stay polite with the
public APIs. Configured via `SCAN_BOARD_RATE_LIMIT_REQS_PER_SEC`.
"""
from __future__ import annotations

import asyncio
import time
from collections import defaultdict
from contextlib import asynccontextmanager
from typing import AsyncIterator

import httpx
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from career_agent.config import get_settings

_USER_AGENT = "CareerAgent/1.0 (+https://careeragent.com/bot)"
_DEFAULT_TIMEOUT_S = 10.0

_platform_last_request: dict[str, float] = defaultdict(float)
_platform_lock: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)


async def _rate_limit(platform: str) -> None:
    settings = get_settings()
    min_interval = 1.0 / max(0.1, settings.scan_board_rate_limit_reqs_per_sec)
    async with _platform_lock[platform]:
        now = time.monotonic()
        last = _platform_last_request[platform]
        elapsed = now - last
        if elapsed < min_interval:
            await asyncio.sleep(min_interval - elapsed)
        _platform_last_request[platform] = time.monotonic()


@asynccontextmanager
async def board_client() -> AsyncIterator[httpx.AsyncClient]:
    """Yield a configured async httpx client for one operation.

    Use once per adapter call. The client is short-lived; per-platform rate
    limiting is enforced by `get_with_retry` using `_rate_limit`, not by the
    client instance itself.
    """
    async with httpx.AsyncClient(
        timeout=_DEFAULT_TIMEOUT_S,
        follow_redirects=True,
        headers={"User-Agent": _USER_AGENT, "Accept": "application/json"},
    ) as client:
        yield client


async def get_with_retry(
    client: httpx.AsyncClient,
    url: str,
    *,
    platform: str,
    max_attempts: int = 3,
) -> httpx.Response:
    """GET with exponential-backoff retry and platform rate limiting."""
    async for attempt in AsyncRetrying(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=0.5, max=4.0),
        retry=retry_if_exception_type((httpx.HTTPError,)),
        reraise=True,
    ):
        with attempt:
            await _rate_limit(platform)
            response = await client.get(url)
            if response.status_code >= 500:
                raise httpx.HTTPStatusError(
                    f"{url} returned {response.status_code}",
                    request=response.request,
                    response=response,
                )
            return response
    raise RuntimeError("unreachable")  # tenacity reraises on failure
```

- [ ] **Step 2: Verify import**

```bash
uv run python -c "from career_agent.integrations.board_http import board_client, get_with_retry; print('ok')"
```

Expected: `ok`

- [ ] **Step 3: Run full suite + lint + typecheck**

```bash
uv run pytest tests/ 2>&1 | tail -3; uv run ruff check src/ 2>&1 | tail -3; uv run mypy src/ 2>&1 | tail -3
```

Expected: `99 passed`, clean ruff, clean mypy.

- [ ] **Step 4: Checkpoint**

Checkpoint message: `feat(integrations): add shared board HTTP helper with rate limiting`

---

## Task 7: Scanner Base Adapter (`BoardAdapter` ABC)

**Files:**
- Create: `backend/src/career_agent/core/scanner/__init__.py`
- Create: `backend/src/career_agent/core/scanner/adapters/__init__.py`
- Create: `backend/src/career_agent/core/scanner/adapters/base.py`
- Create: `backend/tests/unit/test_board_base.py`

- [ ] **Step 1: Create `backend/src/career_agent/core/scanner/__init__.py`**

```python
"""Job scanner module — board adapters + orchestrator."""
```

- [ ] **Step 2: Create `backend/src/career_agent/core/scanner/adapters/__init__.py`**

```python
"""Board adapters: Greenhouse, Ashby, Lever."""
from career_agent.core.scanner.adapters.base import (
    BoardAdapter,
    BoardAdapterError,
    ListingPayload,
)

__all__ = ["BoardAdapter", "BoardAdapterError", "ListingPayload"]
```

- [ ] **Step 3: Write the failing test**

Create `backend/tests/unit/test_board_base.py`:

```python
import pytest

from career_agent.core.scanner.adapters.base import (
    BoardAdapter,
    BoardAdapterError,
    ListingPayload,
)


def test_listing_payload_constructs() -> None:
    p = ListingPayload(
        title="Staff Engineer",
        company="Acme",
        location="Remote, US",
        salary_min=180000,
        salary_max=240000,
        employment_type="full_time",
        seniority="staff",
        description_md="## Role\n\nBuild things.",
        requirements_json={"skills": ["python"], "years_experience": 8, "nice_to_haves": []},
        source_url="https://example.com/jobs/1",
    )
    assert p.title == "Staff Engineer"
    assert p.requirements_json["skills"] == ["python"]


def test_board_adapter_error_carries_platform_and_slug() -> None:
    err = BoardAdapterError(
        platform="greenhouse",
        slug="stripe",
        message="API returned 500",
    )
    assert err.platform == "greenhouse"
    assert err.slug == "stripe"
    assert "greenhouse" in str(err)
    assert "stripe" in str(err)


def test_board_adapter_is_abstract() -> None:
    with pytest.raises(TypeError):
        BoardAdapter()  # type: ignore[abstract]
```

Run:

```bash
uv run pytest tests/unit/test_board_base.py -v
```

Expected: FAIL (module not found).

- [ ] **Step 4: Create `backend/src/career_agent/core/scanner/adapters/base.py`**

```python
"""Base classes for job-board adapters."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ListingPayload:
    """Normalized job listing across all platforms."""

    title: str
    company: str
    location: str | None
    salary_min: int | None
    salary_max: int | None
    employment_type: str | None
    seniority: str | None
    description_md: str
    requirements_json: dict[str, Any] = field(default_factory=dict)
    source_url: str = ""


class BoardAdapterError(Exception):
    """Raised when a board adapter fails to fetch or parse listings."""

    def __init__(self, *, platform: str, slug: str, message: str):
        super().__init__(f"[{platform}:{slug}] {message}")
        self.platform = platform
        self.slug = slug


class BoardAdapter(ABC):
    """Abstract base: one subclass per supported platform."""

    platform: str

    @abstractmethod
    async def fetch_listings(self, board_slug: str) -> list[ListingPayload]:
        """Fetch and normalize all open listings for a company slug."""
```

- [ ] **Step 5: Run tests — expect pass**

```bash
uv run pytest tests/unit/test_board_base.py -v
```

Expected: all 3 tests PASS.

- [ ] **Step 6: Checkpoint**

Checkpoint message: `feat(scanner): add BoardAdapter ABC + ListingPayload dataclass`

---

## Task 8: Greenhouse Adapter

**Files:**
- Create: `backend/src/career_agent/core/scanner/adapters/greenhouse.py`
- Create: `backend/tests/fixtures/boards/greenhouse/stripe.json`
- Create: `backend/tests/unit/test_greenhouse_adapter.py`

- [ ] **Step 1: Create the fixture JSON**

The Greenhouse boards API returns `{"jobs": [...]}` where each job has `title`, `location` (`{name}`), `content` (HTML), `absolute_url`, `metadata` (array of `{name, value}`), `offices` (array of `{name}`).

Create `backend/tests/fixtures/boards/greenhouse/stripe.json`:

```json
{
  "jobs": [
    {
      "id": 4000001,
      "title": "Senior Software Engineer, Payments",
      "absolute_url": "https://boards.greenhouse.io/stripe/jobs/4000001",
      "location": {"name": "Remote, US"},
      "content": "<h3>About the role</h3>\n<p>We're hiring a senior engineer to work on payment infrastructure.</p>\n<h3>You have</h3>\n<ul><li>5+ years of Python</li><li>Distributed systems experience</li></ul>",
      "metadata": [
        {"name": "Employment Type", "value": "Full-time"},
        {"name": "Seniority Level", "value": "Senior"}
      ],
      "offices": [{"name": "Remote"}]
    },
    {
      "id": 4000002,
      "title": "Staff Software Engineer, API Platform",
      "absolute_url": "https://boards.greenhouse.io/stripe/jobs/4000002",
      "location": {"name": "San Francisco, CA"},
      "content": "<h3>Role</h3>\n<p>Lead API platform work.</p>",
      "metadata": [],
      "offices": [{"name": "San Francisco"}]
    }
  ]
}
```

- [ ] **Step 2: Write the failing test**

Create `backend/tests/unit/test_greenhouse_adapter.py`:

```python
import json
from pathlib import Path

import pytest
import respx
from httpx import Response

from career_agent.core.scanner.adapters.greenhouse import GreenhouseAdapter
from career_agent.core.scanner.adapters.base import BoardAdapterError

_FIXTURE = (
    Path(__file__).parent.parent / "fixtures" / "boards" / "greenhouse" / "stripe.json"
)


@pytest.mark.asyncio
@respx.mock
async def test_greenhouse_adapter_fetches_and_normalizes() -> None:
    payload = json.loads(_FIXTURE.read_text())
    respx.get("https://boards-api.greenhouse.io/v1/boards/stripe/jobs?content=true").mock(
        return_value=Response(200, json=payload)
    )
    adapter = GreenhouseAdapter()
    listings = await adapter.fetch_listings("stripe")

    assert len(listings) == 2
    first = listings[0]
    assert first.title == "Senior Software Engineer, Payments"
    assert first.company == "stripe"  # board_slug fallback — caller maps to pretty name
    assert first.location == "Remote, US"
    assert first.employment_type == "full_time"
    assert first.seniority == "senior"
    # HTML → markdown converted
    assert "5+ years of Python" in first.description_md
    assert first.source_url == "https://boards.greenhouse.io/stripe/jobs/4000001"


@pytest.mark.asyncio
@respx.mock
async def test_greenhouse_adapter_raises_on_500() -> None:
    respx.get("https://boards-api.greenhouse.io/v1/boards/unknown/jobs?content=true").mock(
        return_value=Response(500, text="server error")
    )
    adapter = GreenhouseAdapter()
    with pytest.raises(BoardAdapterError) as exc:
        await adapter.fetch_listings("unknown")
    assert exc.value.platform == "greenhouse"
    assert exc.value.slug == "unknown"


@pytest.mark.asyncio
@respx.mock
async def test_greenhouse_adapter_returns_empty_on_empty_board() -> None:
    respx.get("https://boards-api.greenhouse.io/v1/boards/empty/jobs?content=true").mock(
        return_value=Response(200, json={"jobs": []})
    )
    adapter = GreenhouseAdapter()
    listings = await adapter.fetch_listings("empty")
    assert listings == []
```

Run:

```bash
uv run pytest tests/unit/test_greenhouse_adapter.py -v
```

Expected: FAIL (module not found).

- [ ] **Step 3: Create `backend/src/career_agent/core/scanner/adapters/greenhouse.py`**

```python
"""Greenhouse boards API adapter."""
from __future__ import annotations

from typing import Any

import httpx
from markdownify import markdownify as md

from career_agent.core.scanner.adapters.base import (
    BoardAdapter,
    BoardAdapterError,
    ListingPayload,
)
from career_agent.integrations.board_http import board_client, get_with_retry


class GreenhouseAdapter(BoardAdapter):
    platform = "greenhouse"

    async def fetch_listings(self, board_slug: str) -> list[ListingPayload]:
        url = f"https://boards-api.greenhouse.io/v1/boards/{board_slug}/jobs?content=true"
        try:
            async with board_client() as client:
                response = await get_with_retry(client, url, platform=self.platform)
        except httpx.HTTPError as e:
            raise BoardAdapterError(
                platform=self.platform,
                slug=board_slug,
                message=f"HTTP error: {e}",
            ) from e

        if response.status_code != 200:
            raise BoardAdapterError(
                platform=self.platform,
                slug=board_slug,
                message=f"API returned {response.status_code}",
            )

        try:
            data = response.json()
        except ValueError as e:
            raise BoardAdapterError(
                platform=self.platform,
                slug=board_slug,
                message=f"Invalid JSON: {e}",
            ) from e

        listings: list[ListingPayload] = []
        for job in data.get("jobs", []):
            listings.append(self._normalize(job, board_slug))
        return listings

    def _normalize(self, job: dict[str, Any], board_slug: str) -> ListingPayload:
        location_obj = job.get("location") or {}
        location = location_obj.get("name") if isinstance(location_obj, dict) else None

        description_html = job.get("content") or ""
        description_md = md(description_html).strip()

        metadata = {m.get("name", ""): m.get("value") for m in (job.get("metadata") or [])}
        employment_type = self._normalize_employment_type(metadata.get("Employment Type"))
        seniority = self._normalize_seniority(metadata.get("Seniority Level"))

        return ListingPayload(
            title=str(job.get("title") or "Untitled"),
            company=board_slug,
            location=location,
            salary_min=None,
            salary_max=None,
            employment_type=employment_type,
            seniority=seniority,
            description_md=description_md,
            requirements_json={},
            source_url=str(job.get("absolute_url") or ""),
        )

    @staticmethod
    def _normalize_employment_type(value: Any) -> str | None:
        if not isinstance(value, str):
            return None
        v = value.lower().strip()
        if "full" in v:
            return "full_time"
        if "part" in v:
            return "part_time"
        if "contract" in v:
            return "contract"
        return None

    @staticmethod
    def _normalize_seniority(value: Any) -> str | None:
        if not isinstance(value, str):
            return None
        v = value.lower().strip()
        for key in ("principal", "staff", "senior", "mid", "junior"):
            if key in v:
                return key
        return None
```

- [ ] **Step 4: Run tests — expect pass**

```bash
uv run pytest tests/unit/test_greenhouse_adapter.py -v
```

Expected: all 3 tests PASS.

- [ ] **Step 5: Checkpoint**

Checkpoint message: `feat(scanner): add Greenhouse adapter with HTML→markdown normalization`

---

## Task 9: Ashby Adapter

**Files:**
- Create: `backend/src/career_agent/core/scanner/adapters/ashby.py`
- Create: `backend/tests/fixtures/boards/ashby/linear.json`
- Create: `backend/tests/unit/test_ashby_adapter.py`

- [ ] **Step 1: Create the fixture JSON**

The Ashby posting API returns `{"jobs": [...]}` where each job has `id`, `title`, `descriptionHtml`, `locationName`, `departmentName`, `employmentType`, `compensation` (optional), `jobUrl`.

Create `backend/tests/fixtures/boards/ashby/linear.json`:

```json
{
  "jobs": [
    {
      "id": "ashby-job-1",
      "title": "Senior Backend Engineer",
      "descriptionHtml": "<p>Build Linear's backend at scale.</p><ul><li>5+ years backend experience</li><li>TypeScript or Go</li></ul>",
      "locationName": "Remote (Americas)",
      "departmentName": "Engineering",
      "employmentType": "FullTime",
      "compensation": {
        "compensationTierSummary": "$180K – $240K"
      },
      "jobUrl": "https://jobs.ashbyhq.com/linear/ashby-job-1"
    },
    {
      "id": "ashby-job-2",
      "title": "Staff Frontend Engineer",
      "descriptionHtml": "<p>Lead frontend architecture.</p>",
      "locationName": "San Francisco",
      "departmentName": "Engineering",
      "employmentType": "FullTime",
      "jobUrl": "https://jobs.ashbyhq.com/linear/ashby-job-2"
    }
  ]
}
```

- [ ] **Step 2: Write the failing test**

Create `backend/tests/unit/test_ashby_adapter.py`:

```python
import json
import re
from pathlib import Path

import pytest
import respx
from httpx import Response

from career_agent.core.scanner.adapters.ashby import AshbyAdapter
from career_agent.core.scanner.adapters.base import BoardAdapterError

_FIXTURE = Path(__file__).parent.parent / "fixtures" / "boards" / "ashby" / "linear.json"


@pytest.mark.asyncio
@respx.mock
async def test_ashby_adapter_fetches_and_normalizes() -> None:
    payload = json.loads(_FIXTURE.read_text())
    respx.get(
        re.compile(r"https://api\.ashbyhq\.com/posting-api/job-board/linear.*")
    ).mock(return_value=Response(200, json=payload))
    adapter = AshbyAdapter()
    listings = await adapter.fetch_listings("linear")

    assert len(listings) == 2
    first = listings[0]
    assert first.title == "Senior Backend Engineer"
    assert first.company == "linear"
    assert first.location == "Remote (Americas)"
    assert first.employment_type == "full_time"
    assert first.salary_min == 180000
    assert first.salary_max == 240000
    assert "Linear's backend" in first.description_md
    assert first.source_url == "https://jobs.ashbyhq.com/linear/ashby-job-1"


@pytest.mark.asyncio
@respx.mock
async def test_ashby_adapter_handles_missing_compensation() -> None:
    payload = json.loads(_FIXTURE.read_text())
    respx.get(
        re.compile(r"https://api\.ashbyhq\.com/posting-api/job-board/linear.*")
    ).mock(return_value=Response(200, json=payload))
    adapter = AshbyAdapter()
    listings = await adapter.fetch_listings("linear")
    assert listings[1].salary_min is None
    assert listings[1].salary_max is None


@pytest.mark.asyncio
@respx.mock
async def test_ashby_adapter_raises_on_500() -> None:
    respx.get(
        re.compile(r"https://api\.ashbyhq\.com/posting-api/job-board/broken.*")
    ).mock(return_value=Response(500, text="boom"))
    adapter = AshbyAdapter()
    with pytest.raises(BoardAdapterError):
        await adapter.fetch_listings("broken")
```

Run: `uv run pytest tests/unit/test_ashby_adapter.py -v`
Expected: FAIL.

- [ ] **Step 3: Create `backend/src/career_agent/core/scanner/adapters/ashby.py`**

```python
"""Ashby posting API adapter."""
from __future__ import annotations

import re
from typing import Any

import httpx
from markdownify import markdownify as md

from career_agent.core.scanner.adapters.base import (
    BoardAdapter,
    BoardAdapterError,
    ListingPayload,
)
from career_agent.integrations.board_http import board_client, get_with_retry


class AshbyAdapter(BoardAdapter):
    platform = "ashby"

    async def fetch_listings(self, board_slug: str) -> list[ListingPayload]:
        url = (
            f"https://api.ashbyhq.com/posting-api/job-board/{board_slug}"
            "?includeCompensation=true"
        )
        try:
            async with board_client() as client:
                response = await get_with_retry(client, url, platform=self.platform)
        except httpx.HTTPError as e:
            raise BoardAdapterError(
                platform=self.platform, slug=board_slug, message=f"HTTP error: {e}"
            ) from e

        if response.status_code != 200:
            raise BoardAdapterError(
                platform=self.platform,
                slug=board_slug,
                message=f"API returned {response.status_code}",
            )

        try:
            data = response.json()
        except ValueError as e:
            raise BoardAdapterError(
                platform=self.platform,
                slug=board_slug,
                message=f"Invalid JSON: {e}",
            ) from e

        return [self._normalize(j, board_slug) for j in data.get("jobs", [])]

    def _normalize(self, job: dict[str, Any], board_slug: str) -> ListingPayload:
        description_html = job.get("descriptionHtml") or ""
        description_md = md(description_html).strip()
        employment_type = self._normalize_employment_type(job.get("employmentType"))
        comp = job.get("compensation") or {}
        salary_min, salary_max = self._parse_comp_tier(comp.get("compensationTierSummary"))

        return ListingPayload(
            title=str(job.get("title") or "Untitled"),
            company=board_slug,
            location=job.get("locationName"),
            salary_min=salary_min,
            salary_max=salary_max,
            employment_type=employment_type,
            seniority=self._guess_seniority(job.get("title")),
            description_md=description_md,
            requirements_json={},
            source_url=str(job.get("jobUrl") or ""),
        )

    @staticmethod
    def _normalize_employment_type(value: Any) -> str | None:
        if not isinstance(value, str):
            return None
        v = value.lower()
        if "full" in v:
            return "full_time"
        if "part" in v:
            return "part_time"
        if "contract" in v or "temp" in v:
            return "contract"
        return None

    @staticmethod
    def _parse_comp_tier(summary: Any) -> tuple[int | None, int | None]:
        """Parse "$180K – $240K" → (180000, 240000). Returns (None, None) on failure."""
        if not isinstance(summary, str):
            return (None, None)
        numbers = re.findall(r"\$?([\d,]+)\s*[Kk]?", summary)
        values: list[int] = []
        for raw in numbers:
            clean = raw.replace(",", "")
            try:
                n = int(clean)
            except ValueError:
                continue
            if "K" in summary.upper() and n < 10000:
                n *= 1000
            values.append(n)
        if len(values) >= 2:
            return (min(values[:2]), max(values[:2]))
        if len(values) == 1:
            return (values[0], None)
        return (None, None)

    @staticmethod
    def _guess_seniority(title: Any) -> str | None:
        if not isinstance(title, str):
            return None
        t = title.lower()
        for key in ("principal", "staff", "senior", "mid", "junior"):
            if key in t:
                return key
        return None
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/unit/test_ashby_adapter.py -v
```

Expected: all 3 tests PASS.

- [ ] **Step 5: Checkpoint**

Checkpoint message: `feat(scanner): add Ashby adapter with compensation parsing`

---

## Task 10: Lever Adapter

**Files:**
- Create: `backend/src/career_agent/core/scanner/adapters/lever.py`
- Create: `backend/tests/fixtures/boards/lever/shopify.json`
- Create: `backend/tests/unit/test_lever_adapter.py`

- [ ] **Step 1: Create the fixture JSON**

Lever's public API returns a flat array of postings. Each has `id`, `text` (title), `categories` (`{commitment, location, team}`), `descriptionPlain`, `lists` (array of `{text, content}`), `hostedUrl`, `workplaceType`.

Create `backend/tests/fixtures/boards/lever/shopify.json`:

```json
[
  {
    "id": "lever-1",
    "text": "Staff Engineer, Platform",
    "categories": {
      "commitment": "Full Time",
      "location": "Remote - Canada",
      "team": "Platform Engineering"
    },
    "descriptionPlain": "Build Shopify's core platform at massive scale.",
    "lists": [
      {
        "text": "Requirements",
        "content": "<ul><li>8+ years of backend</li><li>Ruby or Go</li></ul>"
      }
    ],
    "hostedUrl": "https://jobs.lever.co/shopify/lever-1",
    "workplaceType": "remote"
  },
  {
    "id": "lever-2",
    "text": "Senior Frontend Engineer",
    "categories": {
      "commitment": "Full Time",
      "location": "Toronto, ON",
      "team": "Admin Experience"
    },
    "descriptionPlain": "Work on the Shopify admin UI.",
    "lists": [],
    "hostedUrl": "https://jobs.lever.co/shopify/lever-2",
    "workplaceType": "hybrid"
  }
]
```

- [ ] **Step 2: Write the failing test**

Create `backend/tests/unit/test_lever_adapter.py`:

```python
import json
import re
from pathlib import Path

import pytest
import respx
from httpx import Response

from career_agent.core.scanner.adapters.lever import LeverAdapter
from career_agent.core.scanner.adapters.base import BoardAdapterError

_FIXTURE = Path(__file__).parent.parent / "fixtures" / "boards" / "lever" / "shopify.json"


@pytest.mark.asyncio
@respx.mock
async def test_lever_adapter_fetches_and_normalizes() -> None:
    payload = json.loads(_FIXTURE.read_text())
    respx.get(
        re.compile(r"https://api\.lever\.co/v0/postings/shopify.*")
    ).mock(return_value=Response(200, json=payload))
    adapter = LeverAdapter()
    listings = await adapter.fetch_listings("shopify")

    assert len(listings) == 2
    first = listings[0]
    assert first.title == "Staff Engineer, Platform"
    assert first.company == "shopify"
    assert first.location == "Remote - Canada"
    assert first.employment_type == "full_time"
    assert first.seniority == "staff"
    assert "Shopify's core platform" in first.description_md
    assert "8+ years of backend" in first.description_md
    assert first.source_url == "https://jobs.lever.co/shopify/lever-1"


@pytest.mark.asyncio
@respx.mock
async def test_lever_adapter_handles_empty_array() -> None:
    respx.get(
        re.compile(r"https://api\.lever\.co/v0/postings/empty.*")
    ).mock(return_value=Response(200, json=[]))
    adapter = LeverAdapter()
    listings = await adapter.fetch_listings("empty")
    assert listings == []


@pytest.mark.asyncio
@respx.mock
async def test_lever_adapter_raises_on_500() -> None:
    respx.get(
        re.compile(r"https://api\.lever\.co/v0/postings/broken.*")
    ).mock(return_value=Response(500, text="server error"))
    adapter = LeverAdapter()
    with pytest.raises(BoardAdapterError):
        await adapter.fetch_listings("broken")
```

Run: `uv run pytest tests/unit/test_lever_adapter.py -v`
Expected: FAIL.

- [ ] **Step 3: Create `backend/src/career_agent/core/scanner/adapters/lever.py`**

```python
"""Lever postings API adapter."""
from __future__ import annotations

from typing import Any

import httpx
from markdownify import markdownify as md

from career_agent.core.scanner.adapters.base import (
    BoardAdapter,
    BoardAdapterError,
    ListingPayload,
)
from career_agent.integrations.board_http import board_client, get_with_retry


class LeverAdapter(BoardAdapter):
    platform = "lever"

    async def fetch_listings(self, board_slug: str) -> list[ListingPayload]:
        url = f"https://api.lever.co/v0/postings/{board_slug}?mode=json"
        try:
            async with board_client() as client:
                response = await get_with_retry(client, url, platform=self.platform)
        except httpx.HTTPError as e:
            raise BoardAdapterError(
                platform=self.platform, slug=board_slug, message=f"HTTP error: {e}"
            ) from e

        if response.status_code != 200:
            raise BoardAdapterError(
                platform=self.platform,
                slug=board_slug,
                message=f"API returned {response.status_code}",
            )

        try:
            postings = response.json()
        except ValueError as e:
            raise BoardAdapterError(
                platform=self.platform,
                slug=board_slug,
                message=f"Invalid JSON: {e}",
            ) from e

        if not isinstance(postings, list):
            raise BoardAdapterError(
                platform=self.platform,
                slug=board_slug,
                message="Expected JSON array of postings",
            )

        return [self._normalize(p, board_slug) for p in postings]

    def _normalize(self, posting: dict[str, Any], board_slug: str) -> ListingPayload:
        categories = posting.get("categories") or {}
        title = str(posting.get("text") or "Untitled")
        description_plain = str(posting.get("descriptionPlain") or "")
        # Flatten "lists" (requirements, benefits, etc.) into the description
        lists = posting.get("lists") or []
        extras = "\n\n".join(
            f"### {item.get('text', 'Details')}\n\n{md(item.get('content', '')).strip()}"
            for item in lists
            if isinstance(item, dict)
        )
        description_md = (description_plain + "\n\n" + extras).strip()

        return ListingPayload(
            title=title,
            company=board_slug,
            location=categories.get("location"),
            salary_min=None,
            salary_max=None,
            employment_type=self._normalize_commitment(categories.get("commitment")),
            seniority=self._guess_seniority(title),
            description_md=description_md,
            requirements_json={},
            source_url=str(posting.get("hostedUrl") or ""),
        )

    @staticmethod
    def _normalize_commitment(value: Any) -> str | None:
        if not isinstance(value, str):
            return None
        v = value.lower()
        if "full" in v:
            return "full_time"
        if "part" in v:
            return "part_time"
        if "contract" in v or "intern" in v:
            return "contract"
        return None

    @staticmethod
    def _guess_seniority(title: str) -> str | None:
        t = title.lower()
        for key in ("principal", "staff", "senior", "mid", "junior"):
            if key in t:
                return key
        return None
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/unit/test_lever_adapter.py -v
```

Expected: all 3 tests PASS.

- [ ] **Step 5: Run all adapter tests + lint + mypy**

```bash
uv run pytest tests/unit/test_board_base.py tests/unit/test_greenhouse_adapter.py tests/unit/test_ashby_adapter.py tests/unit/test_lever_adapter.py -v 2>&1 | tail -15
uv run ruff check src/ 2>&1 | tail -3
uv run mypy src/ 2>&1 | tail -3
```

Expected: all adapter tests pass, ruff clean, mypy clean.

- [ ] **Step 6: Checkpoint**

Checkpoint message: `feat(scanner): add Lever adapter — all 3 platforms wired`

---

## Task 11: Scanner Dedup — Content Hash + Jobs Pool Upsert

**Files:**
- Create: `backend/src/career_agent/core/scanner/dedup.py`
- Create: `backend/tests/unit/test_scanner_dedup.py`

- [ ] **Step 1: Write the failing test**

`backend/tests/unit/test_scanner_dedup.py`:

```python
from career_agent.core.scanner.adapters.base import ListingPayload
from career_agent.core.scanner.dedup import compute_content_hash


def _listing(**overrides) -> ListingPayload:
    defaults = dict(
        title="Senior Engineer",
        company="acme",
        location="Remote",
        salary_min=None,
        salary_max=None,
        employment_type="full_time",
        seniority="senior",
        description_md="Build things.",
        requirements_json={"skills": ["python"]},
        source_url="https://example.com/1",
    )
    defaults.update(overrides)
    return ListingPayload(**defaults)


def test_same_description_same_hash() -> None:
    a = _listing(description_md="Build things.")
    b = _listing(description_md="Build things.")
    assert compute_content_hash(a) == compute_content_hash(b)


def test_whitespace_differences_same_hash() -> None:
    a = _listing(description_md="Build things.")
    b = _listing(description_md="  Build things.  \n")
    assert compute_content_hash(a) == compute_content_hash(b)


def test_different_description_different_hash() -> None:
    a = _listing(description_md="Build things.")
    b = _listing(description_md="Destroy things.")
    assert compute_content_hash(a) != compute_content_hash(b)


def test_different_requirements_different_hash() -> None:
    a = _listing(requirements_json={"skills": ["python"]})
    b = _listing(requirements_json={"skills": ["ruby"]})
    assert compute_content_hash(a) != compute_content_hash(b)


def test_source_url_not_part_of_hash() -> None:
    """Two boards hosting the same JD should dedupe to one hash."""
    a = _listing(source_url="https://a.com/1")
    b = _listing(source_url="https://b.com/2")
    assert compute_content_hash(a) == compute_content_hash(b)
```

Run:

```bash
uv run pytest tests/unit/test_scanner_dedup.py -v
```

Expected: FAIL.

- [ ] **Step 2: Create `backend/src/career_agent/core/scanner/dedup.py`**

```python
"""Content-hash dedup + jobs pool upsert."""
from __future__ import annotations

import hashlib
import json
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from career_agent.core.scanner.adapters.base import ListingPayload
from career_agent.models.job import Job


def compute_content_hash(listing: ListingPayload) -> str:
    """SHA256 of normalized description + requirements_json.

    Whitespace is normalized. Source URL is intentionally excluded so two boards
    hosting the same JD dedupe to one hash.
    """
    normalized_desc = " ".join(listing.description_md.split())
    normalized_reqs = json.dumps(listing.requirements_json, sort_keys=True)
    payload = normalized_desc + "|" + normalized_reqs
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


async def upsert_jobs_from_listings(
    session: AsyncSession,
    listings: Sequence[ListingPayload],
    *,
    platform: str,
    company_pretty_name: str,
    max_listings: int,
) -> tuple[list[tuple[Job, bool]], bool]:
    """Upsert listings into the jobs pool. Returns (rows, was_truncated).

    rows: list of (Job, is_new) tuples in the same order as the input listings
          that made the cut (up to `max_listings` after dedup).
    was_truncated: True when the input exceeded `max_listings`.
    """
    seen: set[str] = set()
    deduped: list[tuple[ListingPayload, str]] = []
    for listing in listings:
        h = compute_content_hash(listing)
        if h in seen:
            continue
        seen.add(h)
        deduped.append((listing, h))

    was_truncated = len(deduped) > max_listings
    if was_truncated:
        deduped = deduped[:max_listings]

    results: list[tuple[Job, bool]] = []
    for listing, content_hash in deduped:
        stmt = select(Job).where(Job.content_hash == content_hash)
        existing = (await session.execute(stmt)).scalar_one_or_none()
        if existing is not None:
            results.append((existing, False))
            continue

        job = Job(
            content_hash=content_hash,
            url=listing.source_url or None,
            title=listing.title,
            company=company_pretty_name,
            location=listing.location,
            salary_min=listing.salary_min,
            salary_max=listing.salary_max,
            employment_type=listing.employment_type,
            seniority=listing.seniority,
            description_md=listing.description_md,
            requirements_json=listing.requirements_json,
            source=platform,
            board_company=company_pretty_name,
        )
        session.add(job)
        await session.flush()
        results.append((job, True))

    return results, was_truncated
```

- [ ] **Step 3: Run tests**

```bash
uv run pytest tests/unit/test_scanner_dedup.py -v
```

Expected: 5 tests PASS.

- [ ] **Step 4: Checkpoint**

Checkpoint message: `feat(scanner): add content hash dedup + jobs pool upsert`

---

## Task 12: Scanner L1 Relevance Scorer

**Files:**
- Create: `backend/src/career_agent/core/scanner/relevance.py`
- Create: `backend/tests/unit/test_scanner_relevance.py`

- [ ] **Step 1: Write the failing test**

`backend/tests/unit/test_scanner_relevance.py`:

```python
import pytest

from career_agent.core.scanner.relevance import score_relevance
from career_agent.models.job import Job
from tests.fixtures.fake_gemini import fake_gemini


def _job(**overrides) -> Job:
    defaults = dict(
        content_hash="test_hash_" + str(id(object())),
        title="Staff Engineer",
        description_md="Staff engineering role at Acme.",
        requirements_json={"skills": ["python"], "years_experience": 8},
        source="greenhouse",
    )
    defaults.update(overrides)
    return Job(**defaults)


@pytest.mark.asyncio
async def test_relevance_parses_numeric_response() -> None:
    job = _job()
    profile = {"skills": ["python"], "years_experience": 8, "target_roles": ["staff engineer"]}
    with fake_gemini({"Staff": "0.87"}):
        score = await score_relevance(job=job, profile_summary=profile)
    assert score == pytest.approx(0.87, abs=0.01)


@pytest.mark.asyncio
async def test_relevance_handles_embedded_number_in_text() -> None:
    job = _job()
    profile = {"skills": ["python"]}
    with fake_gemini({"Staff": "Score: 0.65 - strong match"}):
        score = await score_relevance(job=job, profile_summary=profile)
    assert score == pytest.approx(0.65, abs=0.01)


@pytest.mark.asyncio
async def test_relevance_defaults_to_zero_on_garbage() -> None:
    job = _job()
    profile = {"skills": ["python"]}
    with fake_gemini({"Staff": "not a number at all"}):
        score = await score_relevance(job=job, profile_summary=profile)
    assert score == 0.0


@pytest.mark.asyncio
async def test_relevance_clamps_to_0_1_range() -> None:
    job = _job()
    profile = {"skills": ["python"]}
    with fake_gemini({"Staff": "1.5"}):
        score = await score_relevance(job=job, profile_summary=profile)
    assert score == 1.0
    with fake_gemini({"Staff": "-0.2"}):
        score = await score_relevance(job=job, profile_summary=profile)
    assert score == 0.0
```

Run: `uv run pytest tests/unit/test_scanner_relevance.py -v`
Expected: FAIL.

- [ ] **Step 2: Create `backend/src/career_agent/core/scanner/relevance.py`**

```python
"""L1 relevance scorer — Gemini Flash, one call per job."""
from __future__ import annotations

import asyncio
import re
from typing import Any

import google.generativeai as genai  # type: ignore[attr-defined]

from career_agent.config import get_settings
from career_agent.core.llm.gemini_client import _get_model
from career_agent.models.job import Job


def _build_prompt(job: Job, profile_summary: dict[str, Any]) -> str:
    """Parent spec Appendix D.5 — relevance scoring prompt."""
    return (
        "Score this job listing's relevance to the candidate profile. "
        "Output ONLY a number between 0.0 and 1.0.\n\n"
        "Scoring guide:\n"
        "- 0.9-1.0: Strong match (right seniority, right skills, right location)\n"
        "- 0.7-0.9: Good match with minor gaps\n"
        "- 0.5-0.7: Partial match\n"
        "- 0.3-0.5: Weak match\n"
        "- 0.0-0.3: Poor match or wrong role entirely\n\n"
        "CANDIDATE:\n"
        f"Target roles: {profile_summary.get('target_roles', [])}\n"
        f"Skills: {profile_summary.get('skills', [])}\n"
        f"Seniority: {profile_summary.get('seniority', 'unknown')}\n"
        f"Location prefs: {profile_summary.get('target_locations', [])}\n\n"
        "JOB:\n"
        f"Title: {job.title}\n"
        f"Company: {job.company or 'unknown'}\n"
        f"Location: {job.location or 'unknown'}\n"
        f"Snippet: {(job.description_md or '')[:500]}\n\n"
        "Relevance score (0.0-1.0):"
    )


async def score_relevance(
    *,
    job: Job,
    profile_summary: dict[str, Any],
    timeout_s: float = 5.0,
) -> float:
    """Return a 0.0–1.0 relevance score. 0.0 on any error."""
    prompt = _build_prompt(job, profile_summary)
    model = _get_model()
    try:
        response = await asyncio.wait_for(
            model.generate_content_async(prompt),
            timeout=timeout_s,
        )
    except Exception:
        return 0.0

    raw = getattr(response, "text", "") or ""
    match = re.search(r"-?\d+(?:\.\d+)?", raw)
    if not match:
        return 0.0
    try:
        value = float(match.group(0))
    except ValueError:
        return 0.0
    return max(0.0, min(1.0, value))
```

- [ ] **Step 3: Run tests**

```bash
uv run pytest tests/unit/test_scanner_relevance.py -v
```

Expected: 4 tests PASS.

- [ ] **Step 4: Checkpoint**

Checkpoint message: `feat(scanner): add L1 relevance scorer with clamping + parse-robustness`

---

## Task 13: Default Scan Config (15 companies) + ScanConfigService

**Files:**
- Create: `backend/src/career_agent/core/scanner/default_config.py`
- Create: `backend/src/career_agent/services/scan_config.py`
- Create: `backend/tests/unit/test_default_scan_config.py`

- [ ] **Step 1: Write the failing test**

`backend/tests/unit/test_default_scan_config.py`:

```python
import pytest

from career_agent.core.scanner.default_config import (
    DEFAULT_COMPANIES,
    DEFAULT_SCAN_CONFIG_NAME,
)


def test_default_has_15_companies() -> None:
    assert len(DEFAULT_COMPANIES) == 15


def test_default_covers_all_three_platforms() -> None:
    platforms = {c["platform"] for c in DEFAULT_COMPANIES}
    assert platforms == {"greenhouse", "ashby", "lever"}


def test_default_has_exactly_5_per_platform() -> None:
    from collections import Counter
    counts = Counter(c["platform"] for c in DEFAULT_COMPANIES)
    assert counts["greenhouse"] == 5
    assert counts["ashby"] == 5
    assert counts["lever"] == 5


def test_default_name_is_ai_and_dev_tools() -> None:
    assert DEFAULT_SCAN_CONFIG_NAME == "AI & Developer Tools Companies"
```

Run: `uv run pytest tests/unit/test_default_scan_config.py -v`
Expected: FAIL.

- [ ] **Step 2: Create `backend/src/career_agent/core/scanner/default_config.py`**

```python
"""Default 15-company scan config seeded at onboarding.

Parent spec Appendix M. Seeded eagerly when a user's profile transitions to
onboarding_state='done', but NOT auto-run — the user must explicitly click
'Run scan' or ask the agent to scan.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from career_agent.models.scan_config import ScanConfig

DEFAULT_SCAN_CONFIG_NAME = "AI & Developer Tools Companies"

DEFAULT_COMPANIES: list[dict[str, Any]] = [
    # Greenhouse
    {"name": "Stripe", "platform": "greenhouse", "board_slug": "stripe"},
    {"name": "Airtable", "platform": "greenhouse", "board_slug": "airtable"},
    {"name": "Figma", "platform": "greenhouse", "board_slug": "figma"},
    {"name": "Vercel", "platform": "greenhouse", "board_slug": "vercel"},
    {"name": "Notion", "platform": "greenhouse", "board_slug": "notion"},
    # Ashby
    {"name": "Linear", "platform": "ashby", "board_slug": "linear"},
    {"name": "Anthropic", "platform": "ashby", "board_slug": "anthropic"},
    {"name": "Ramp", "platform": "ashby", "board_slug": "ramp"},
    {"name": "OpenAI", "platform": "ashby", "board_slug": "openai"},
    {"name": "Perplexity", "platform": "ashby", "board_slug": "perplexity"},
    # Lever
    {"name": "Netflix", "platform": "lever", "board_slug": "netflix"},
    {"name": "Shopify", "platform": "lever", "board_slug": "shopify"},
    {"name": "GitLab", "platform": "lever", "board_slug": "gitlab"},
    {"name": "Postman", "platform": "lever", "board_slug": "postman"},
    {"name": "Asana", "platform": "lever", "board_slug": "asana"},
]


async def seed_default_scan_config(session: AsyncSession, user_id: UUID) -> ScanConfig:
    """Create the default config for a user. Idempotent.

    Does NOT trigger a scan run. The user must explicitly click 'Run scan' or
    ask the agent. This avoids hidden first-session cost at signup.
    """
    stmt = select(ScanConfig).where(
        ScanConfig.user_id == user_id,
        ScanConfig.name == DEFAULT_SCAN_CONFIG_NAME,
    )
    existing = (await session.execute(stmt)).scalar_one_or_none()
    if existing is not None:
        return existing

    config = ScanConfig(
        user_id=user_id,
        name=DEFAULT_SCAN_CONFIG_NAME,
        companies=list(DEFAULT_COMPANIES),
        keywords=None,
        exclude_keywords=None,
        schedule="manual",
        is_active=True,
    )
    session.add(config)
    await session.flush()
    return config
```

- [ ] **Step 3: Create `backend/src/career_agent/services/scan_config.py`**

```python
"""ScanConfig CRUD service."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from career_agent.models.scan_config import ScanConfig
from career_agent.schemas.scan_config import ScanConfigCreate, ScanConfigUpdate


class ScanConfigService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_for_user(self, user_id: UUID) -> list[ScanConfig]:
        stmt = select(ScanConfig).where(ScanConfig.user_id == user_id).order_by(
            ScanConfig.created_at.desc()
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def get(self, user_id: UUID, config_id: UUID) -> ScanConfig | None:
        stmt = select(ScanConfig).where(
            ScanConfig.id == config_id,
            ScanConfig.user_id == user_id,
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def create(self, user_id: UUID, payload: ScanConfigCreate) -> ScanConfig:
        config = ScanConfig(
            user_id=user_id,
            name=payload.name,
            companies=[c.model_dump() for c in payload.companies],
            keywords=payload.keywords,
            exclude_keywords=payload.exclude_keywords,
            schedule=payload.schedule,
            is_active=True,
        )
        self.session.add(config)
        await self.session.flush()
        return config

    async def update(
        self, user_id: UUID, config_id: UUID, payload: ScanConfigUpdate
    ) -> ScanConfig | None:
        config = await self.get(user_id, config_id)
        if config is None:
            return None
        data = payload.model_dump(exclude_unset=True)
        if "companies" in data and data["companies"] is not None:
            data["companies"] = [c.model_dump() if hasattr(c, "model_dump") else c for c in data["companies"]]
        for k, v in data.items():
            setattr(config, k, v)
        await self.session.flush()
        return config

    async def delete(self, user_id: UUID, config_id: UUID) -> bool:
        config = await self.get(user_id, config_id)
        if config is None:
            return False
        await self.session.delete(config)
        await self.session.flush()
        return True
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/unit/test_default_scan_config.py -v
```

Expected: 4 tests PASS.

- [ ] **Step 5: Checkpoint**

Checkpoint message: `feat(scanner): add default 15-company config + ScanConfigService`

---

## Task 14: Scanner Service Orchestrator

**Files:**
- Create: `backend/src/career_agent/core/scanner/service.py`
- Create: `backend/src/career_agent/services/scan_run.py`
- Create: `backend/tests/integration/test_scanner_service_e2e.py`
- Create: `backend/tests/integration/test_scanner_service_adapter_failure.py`
- Create: `backend/tests/integration/test_scanner_service_500_cap.py`

- [ ] **Step 1: Create `backend/src/career_agent/services/scan_run.py`**

```python
"""ScanRun CRUD helpers."""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from career_agent.models.scan_run import ScanResult, ScanRun


class ScanRunService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_pending(
        self,
        *,
        user_id: UUID,
        scan_config_id: UUID,
        inngest_event_id: str | None = None,
    ) -> ScanRun:
        run = ScanRun(
            user_id=user_id,
            scan_config_id=scan_config_id,
            inngest_event_id=inngest_event_id,
            status="pending",
        )
        self.session.add(run)
        await self.session.flush()
        return run

    async def get_for_user(self, user_id: UUID, run_id: UUID) -> ScanRun | None:
        stmt = select(ScanRun).where(
            ScanRun.id == run_id, ScanRun.user_id == user_id
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def list_for_user(
        self, user_id: UUID, *, limit: int = 20, status: str | None = None
    ) -> list[ScanRun]:
        stmt = (
            select(ScanRun)
            .where(ScanRun.user_id == user_id)
            .order_by(ScanRun.started_at.desc())
            .limit(limit)
        )
        if status:
            stmt = stmt.where(ScanRun.status == status)
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_results(self, run_id: UUID, *, limit: int = 50) -> list[ScanResult]:
        stmt = (
            select(ScanResult)
            .where(ScanResult.scan_run_id == run_id)
            .order_by(ScanResult.relevance_score.desc().nullslast())
            .limit(limit)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def mark_running(self, run: ScanRun) -> None:
        run.status = "running"
        await self.session.flush()

    async def mark_completed(
        self,
        run: ScanRun,
        *,
        jobs_found: int,
        jobs_new: int,
        truncated: bool,
    ) -> None:
        run.status = "completed"
        run.jobs_found = jobs_found
        run.jobs_new = jobs_new
        run.truncated = truncated
        run.completed_at = datetime.now(UTC)
        await self.session.flush()

    async def mark_failed(self, run: ScanRun, error: str) -> None:
        run.status = "failed"
        run.error = error[:2000]
        run.completed_at = datetime.now(UTC)
        await self.session.flush()
```

- [ ] **Step 2: Create `backend/src/career_agent/core/scanner/service.py`**

```python
"""ScannerService — orchestrator called from scan_boards_fn Inngest function."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from career_agent.config import get_settings
from career_agent.core.scanner.adapters import BoardAdapter, BoardAdapterError, ListingPayload
from career_agent.core.scanner.adapters.ashby import AshbyAdapter
from career_agent.core.scanner.adapters.greenhouse import GreenhouseAdapter
from career_agent.core.scanner.adapters.lever import LeverAdapter
from career_agent.core.scanner.dedup import upsert_jobs_from_listings
from career_agent.core.scanner.relevance import score_relevance
from career_agent.models.job import Job
from career_agent.models.profile import Profile
from career_agent.models.scan_config import ScanConfig
from career_agent.models.scan_run import ScanResult, ScanRun
from career_agent.services.scan_run import ScanRunService

_ADAPTERS: dict[str, BoardAdapter] = {
    "greenhouse": GreenhouseAdapter(),
    "ashby": AshbyAdapter(),
    "lever": LeverAdapter(),
}


@dataclass
class ScanRunOutcome:
    jobs_found: int
    jobs_new: int
    truncated: bool


class ScannerService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.runs = ScanRunService(session)

    async def run_scan(self, scan_run_id: UUID) -> ScanRunOutcome:
        """Execute a scan run end-to-end.

        Loads the pending ScanRun row by id, loads its config, scrapes all
        configured boards in parallel, dedups into the jobs pool, runs L1
        relevance on new jobs, writes scan_results, and marks the run complete.
        """
        run = (
            await self.session.execute(select(ScanRun).where(ScanRun.id == scan_run_id))
        ).scalar_one()
        config = (
            await self.session.execute(
                select(ScanConfig).where(ScanConfig.id == run.scan_config_id)
            )
        ).scalar_one()
        profile = (
            await self.session.execute(
                select(Profile).where(Profile.user_id == run.user_id)
            )
        ).scalar_one_or_none()

        await self.runs.mark_running(run)

        try:
            all_listings = await self._scrape_all_boards(config.companies)
        except Exception as e:
            await self.runs.mark_failed(run, f"Scrape failed: {e}")
            raise

        if not all_listings:
            await self.runs.mark_completed(
                run, jobs_found=0, jobs_new=0, truncated=False
            )
            return ScanRunOutcome(jobs_found=0, jobs_new=0, truncated=False)

        settings = get_settings()
        rows_with_flags: list[tuple[Job, bool]] = []
        all_truncated = False
        # Group listings by platform+company to call upsert per-company for provenance
        grouped: dict[tuple[str, str], list[ListingPayload]] = {}
        for listing, platform, company in all_listings:
            grouped.setdefault((platform, company), []).append(listing)

        for (platform, company), listings in grouped.items():
            rows, truncated = await upsert_jobs_from_listings(
                self.session,
                listings,
                platform=platform,
                company_pretty_name=company,
                max_listings=settings.scan_max_listings_per_run,
            )
            rows_with_flags.extend(rows)
            if truncated:
                all_truncated = True

        # Apply a second-pass cap if total across companies still exceeds max
        if len(rows_with_flags) > settings.scan_max_listings_per_run:
            rows_with_flags = rows_with_flags[: settings.scan_max_listings_per_run]
            all_truncated = True

        profile_summary = self._compact_profile(profile)
        new_jobs = [(j, is_new) for (j, is_new) in rows_with_flags if is_new]

        sem = asyncio.Semaphore(max(1, settings.scan_l1_concurrency))

        async def _score(job: Job) -> float:
            async with sem:
                return await score_relevance(job=job, profile_summary=profile_summary)

        new_scores = await asyncio.gather(*(_score(j) for (j, _) in new_jobs))
        new_score_map = {nj.id: sc for (nj, _), sc in zip(new_jobs, new_scores, strict=True)}

        for job, is_new in rows_with_flags:
            result = ScanResult(
                scan_run_id=run.id,
                job_id=job.id,
                relevance_score=new_score_map.get(job.id),
                is_new=is_new,
            )
            self.session.add(result)
        await self.session.flush()

        await self.runs.mark_completed(
            run,
            jobs_found=len(rows_with_flags),
            jobs_new=sum(1 for _, is_new in rows_with_flags if is_new),
            truncated=all_truncated,
        )
        return ScanRunOutcome(
            jobs_found=len(rows_with_flags),
            jobs_new=len(new_jobs),
            truncated=all_truncated,
        )

    async def _scrape_all_boards(
        self, companies: list[dict[str, Any]]
    ) -> list[tuple[ListingPayload, str, str]]:
        """Scrape all configured companies in parallel.

        Returns a flat list of (listing, platform, company_pretty_name).
        Failures of individual boards are logged but do not kill the scan.
        """

        async def _one(company: dict[str, Any]) -> list[tuple[ListingPayload, str, str]]:
            platform = str(company.get("platform") or "")
            slug = str(company.get("board_slug") or "")
            pretty = str(company.get("name") or slug)
            adapter = _ADAPTERS.get(platform)
            if adapter is None:
                return []
            try:
                listings = await adapter.fetch_listings(slug)
            except BoardAdapterError:
                return []
            return [(lst, platform, pretty) for lst in listings]

        results = await asyncio.gather(*(_one(c) for c in companies))
        return [item for sub in results for item in sub]

    @staticmethod
    def _compact_profile(profile: Profile | None) -> dict[str, Any]:
        if profile is None:
            return {}
        parsed = profile.parsed_resume_json or {}
        return {
            "skills": list(parsed.get("skills", []))[:20],
            "years_experience": parsed.get("total_years_experience"),
            "target_roles": list(profile.target_roles or []),
            "target_locations": list(profile.target_locations or []),
        }
```

- [ ] **Step 3: Write the integration tests**

`backend/tests/integration/test_scanner_service_e2e.py`:

```python
import json
import re
from pathlib import Path
from uuid import UUID, uuid4

import pytest
import respx
from httpx import Response
from sqlalchemy import select

from career_agent.core.scanner.service import ScannerService
from career_agent.db import get_session_factory
from career_agent.models.scan_config import ScanConfig
from career_agent.models.scan_run import ScanResult, ScanRun
from career_agent.models.user import User
from tests.conftest import FAKE_CLAIMS
from tests.fixtures.fake_gemini import fake_gemini

_GH = json.loads(
    (Path(__file__).parent.parent / "fixtures" / "boards" / "greenhouse" / "stripe.json").read_text()
)
_ASHBY = json.loads(
    (Path(__file__).parent.parent / "fixtures" / "boards" / "ashby" / "linear.json").read_text()
)
_LEVER = json.loads(
    (Path(__file__).parent.parent / "fixtures" / "boards" / "lever" / "shopify.json").read_text()
)


async def _get_user_id() -> UUID:
    factory = get_session_factory()
    async with factory() as session:
        r = await session.execute(select(User).where(User.cognito_sub == FAKE_CLAIMS["sub"]))
        user = r.scalar_one_or_none()
        if user is None:
            user = User(cognito_sub=FAKE_CLAIMS["sub"], email=FAKE_CLAIMS["email"], name="Test")
            session.add(user)
            await session.commit()
            await session.refresh(user)
        return user.id


@pytest.mark.asyncio
@respx.mock
async def test_scanner_service_happy_path_all_three_platforms(seed_profile) -> None:
    respx.get("https://boards-api.greenhouse.io/v1/boards/stripe/jobs?content=true").mock(
        return_value=Response(200, json=_GH)
    )
    respx.get(
        re.compile(r"https://api\.ashbyhq\.com/posting-api/job-board/linear.*")
    ).mock(return_value=Response(200, json=_ASHBY))
    respx.get(re.compile(r"https://api\.lever\.co/v0/postings/shopify.*")).mock(
        return_value=Response(200, json=_LEVER)
    )

    user_id = await _get_user_id()
    factory = get_session_factory()
    async with factory() as session:
        config = ScanConfig(
            user_id=user_id,
            name="Test scan",
            companies=[
                {"name": "Stripe", "platform": "greenhouse", "board_slug": "stripe"},
                {"name": "Linear", "platform": "ashby", "board_slug": "linear"},
                {"name": "Shopify", "platform": "lever", "board_slug": "shopify"},
            ],
            status_placeholder=None,  # just to silence linters
        ) if False else None

    async with factory() as session:
        config = ScanConfig(
            user_id=user_id,
            name="Test scan",
            companies=[
                {"name": "Stripe", "platform": "greenhouse", "board_slug": "stripe"},
                {"name": "Linear", "platform": "ashby", "board_slug": "linear"},
                {"name": "Shopify", "platform": "lever", "board_slug": "shopify"},
            ],
            schedule="manual",
            is_active=True,
        )
        session.add(config)
        await session.flush()
        run = ScanRun(
            user_id=user_id,
            scan_config_id=config.id,
            status="pending",
        )
        session.add(run)
        await session.commit()
        await session.refresh(run)
        run_id = run.id

    with fake_gemini({"Staff": "0.85", "Senior": "0.75"}):
        async with factory() as session:
            service = ScannerService(session)
            outcome = await service.run_scan(run_id)
            await session.commit()

    assert outcome.jobs_found >= 4  # 2 gh + 2 ashby + 2 lever = 6
    assert outcome.jobs_new >= 4
    assert outcome.truncated is False

    async with factory() as session:
        reloaded = (
            await session.execute(select(ScanRun).where(ScanRun.id == run_id))
        ).scalar_one()
        assert reloaded.status == "completed"
        results = (
            await session.execute(
                select(ScanResult).where(ScanResult.scan_run_id == run_id)
            )
        ).scalars().all()
        assert len(results) >= 4
```

`backend/tests/integration/test_scanner_service_adapter_failure.py`:

```python
import json
import re
from pathlib import Path
from uuid import UUID

import pytest
import respx
from httpx import Response
from sqlalchemy import select

from career_agent.core.scanner.service import ScannerService
from career_agent.db import get_session_factory
from career_agent.models.scan_config import ScanConfig
from career_agent.models.scan_run import ScanRun
from career_agent.models.user import User
from tests.conftest import FAKE_CLAIMS
from tests.fixtures.fake_gemini import fake_gemini

_GH = json.loads(
    (Path(__file__).parent.parent / "fixtures" / "boards" / "greenhouse" / "stripe.json").read_text()
)


async def _user_id() -> UUID:
    factory = get_session_factory()
    async with factory() as s:
        r = await s.execute(select(User).where(User.cognito_sub == FAKE_CLAIMS["sub"]))
        return r.scalar_one().id


@pytest.mark.asyncio
@respx.mock
async def test_scan_completes_when_one_adapter_fails(seed_profile) -> None:
    # greenhouse works
    respx.get("https://boards-api.greenhouse.io/v1/boards/stripe/jobs?content=true").mock(
        return_value=Response(200, json=_GH)
    )
    # ashby returns 500 repeatedly
    respx.get(re.compile(r"https://api\.ashbyhq\.com/posting-api/job-board/linear.*")).mock(
        return_value=Response(500, text="boom")
    )

    uid = await _user_id()
    factory = get_session_factory()
    async with factory() as session:
        config = ScanConfig(
            user_id=uid,
            name="Half-broken",
            companies=[
                {"name": "Stripe", "platform": "greenhouse", "board_slug": "stripe"},
                {"name": "Linear", "platform": "ashby", "board_slug": "linear"},
            ],
            schedule="manual",
            is_active=True,
        )
        session.add(config)
        await session.flush()
        run = ScanRun(user_id=uid, scan_config_id=config.id, status="pending")
        session.add(run)
        await session.commit()
        run_id = run.id

    with fake_gemini({"Staff": "0.6", "Senior": "0.55"}):
        async with factory() as session:
            outcome = await ScannerService(session).run_scan(run_id)
            await session.commit()

    assert outcome.jobs_found >= 2  # greenhouse's 2 listings
    async with factory() as session:
        reloaded = (
            await session.execute(select(ScanRun).where(ScanRun.id == run_id))
        ).scalar_one()
        assert reloaded.status == "completed"
```

`backend/tests/integration/test_scanner_service_500_cap.py`:

```python
from uuid import UUID

import pytest
import respx
from httpx import Response
from sqlalchemy import select

from career_agent.core.scanner.service import ScannerService
from career_agent.db import get_session_factory
from career_agent.models.scan_config import ScanConfig
from career_agent.models.scan_run import ScanRun
from career_agent.models.user import User
from tests.conftest import FAKE_CLAIMS
from tests.fixtures.fake_gemini import fake_gemini


def _fake_greenhouse_with_n_listings(n: int) -> dict:
    jobs = []
    for i in range(n):
        jobs.append(
            {
                "id": 1000 + i,
                "title": f"Job {i}",
                "absolute_url": f"https://boards.greenhouse.io/huge/jobs/{i}",
                "location": {"name": "Remote"},
                "content": f"<p>Unique description for job {i}</p>",
                "metadata": [],
                "offices": [],
            }
        )
    return {"jobs": jobs}


async def _user_id() -> UUID:
    factory = get_session_factory()
    async with factory() as s:
        r = await s.execute(select(User).where(User.cognito_sub == FAKE_CLAIMS["sub"]))
        return r.scalar_one().id


@pytest.mark.asyncio
@respx.mock
async def test_scan_truncates_at_500(seed_profile) -> None:
    respx.get("https://boards-api.greenhouse.io/v1/boards/huge/jobs?content=true").mock(
        return_value=Response(200, json=_fake_greenhouse_with_n_listings(600))
    )

    uid = await _user_id()
    factory = get_session_factory()
    async with factory() as session:
        config = ScanConfig(
            user_id=uid,
            name="Huge",
            companies=[{"name": "Huge", "platform": "greenhouse", "board_slug": "huge"}],
            schedule="manual",
            is_active=True,
        )
        session.add(config)
        await session.flush()
        run = ScanRun(user_id=uid, scan_config_id=config.id, status="pending")
        session.add(run)
        await session.commit()
        run_id = run.id

    with fake_gemini({"Job": "0.5"}):
        async with factory() as session:
            outcome = await ScannerService(session).run_scan(run_id)
            await session.commit()

    assert outcome.truncated is True
    assert outcome.jobs_found == 500
```

- [ ] **Step 4: Run all 3 new integration tests**

```bash
uv run pytest tests/integration/test_scanner_service_e2e.py tests/integration/test_scanner_service_adapter_failure.py tests/integration/test_scanner_service_500_cap.py -v 2>&1 | tail -30
```

Expected: all 3 tests PASS.

- [ ] **Step 5: Checkpoint**

Checkpoint message: `feat(scanner): add ScannerService orchestrator + e2e tests`

---

## Task 15: Scan Configs API (CRUD)

**Files:**
- Create: `backend/src/career_agent/api/scan_configs.py`
- Modify: `backend/src/career_agent/main.py` — register router
- Create: `backend/tests/integration/test_scan_configs_crud.py`

- [ ] **Step 1: Write the failing tests**

`backend/tests/integration/test_scan_configs_crud.py`:

```python
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete
from unittest.mock import AsyncMock, patch

from career_agent.db import get_session_factory
from career_agent.main import app
from career_agent.models.scan_config import ScanConfig
from tests.conftest import FAKE_CLAIMS


async def _clear_configs_for_test_user() -> None:
    from sqlalchemy import select
    from career_agent.models.user import User
    factory = get_session_factory()
    async with factory() as session:
        u = (await session.execute(select(User).where(User.cognito_sub == FAKE_CLAIMS["sub"]))).scalar_one()
        await session.execute(delete(ScanConfig).where(ScanConfig.user_id == u.id))
        await session.commit()


@pytest.mark.asyncio
async def test_scan_config_create_list_get_update_delete(auth_headers, seed_profile):
    await _clear_configs_for_test_user()

    with patch(
        "career_agent.integrations.cognito.CognitoJwtVerifier.verify",
        new=AsyncMock(return_value=FAKE_CLAIMS),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Create
            r1 = await client.post(
                "/api/v1/scan-configs",
                json={
                    "name": "My scan",
                    "companies": [
                        {"name": "Stripe", "platform": "greenhouse", "board_slug": "stripe"}
                    ],
                    "keywords": ["python"],
                },
                headers=auth_headers,
            )
            assert r1.status_code == 201
            config_id = r1.json()["data"]["id"]

            # List
            r2 = await client.get("/api/v1/scan-configs", headers=auth_headers)
            assert r2.status_code == 200
            names = [c["name"] for c in r2.json()["data"]]
            assert "My scan" in names

            # Get
            r3 = await client.get(f"/api/v1/scan-configs/{config_id}", headers=auth_headers)
            assert r3.status_code == 200
            assert r3.json()["data"]["name"] == "My scan"

            # Update
            r4 = await client.put(
                f"/api/v1/scan-configs/{config_id}",
                json={"name": "Renamed scan"},
                headers=auth_headers,
            )
            assert r4.status_code == 200
            assert r4.json()["data"]["name"] == "Renamed scan"

            # Delete
            r5 = await client.delete(f"/api/v1/scan-configs/{config_id}", headers=auth_headers)
            assert r5.status_code == 204

            # Get again → 404
            r6 = await client.get(f"/api/v1/scan-configs/{config_id}", headers=auth_headers)
            assert r6.status_code == 404


@pytest.mark.asyncio
async def test_scan_config_paywalled_on_create(auth_headers, seed_profile):
    """POST /scan-configs requires entitlement (trial or active sub)."""
    from datetime import UTC, datetime, timedelta
    from sqlalchemy import select
    from career_agent.models.subscription import Subscription
    from career_agent.models.user import User

    await _clear_configs_for_test_user()

    # Force expired trial
    factory = get_session_factory()
    async with factory() as session:
        u = (await session.execute(select(User).where(User.cognito_sub == FAKE_CLAIMS["sub"]))).scalar_one()
        sub = (
            await session.execute(select(Subscription).where(Subscription.user_id == u.id))
        ).scalar_one_or_none()
        if sub is None:
            sub = Subscription(user_id=u.id, plan="trial", status="active")
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
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post(
                    "/api/v1/scan-configs",
                    json={
                        "name": "x",
                        "companies": [
                            {"name": "Stripe", "platform": "greenhouse", "board_slug": "stripe"}
                        ],
                    },
                    headers=auth_headers,
                )
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "TRIAL_EXPIRED"
    finally:
        # restore trial
        async with factory() as session:
            u = (await session.execute(select(User).where(User.cognito_sub == FAKE_CLAIMS["sub"]))).scalar_one()
            sub = (
                await session.execute(select(Subscription).where(Subscription.user_id == u.id))
            ).scalar_one_or_none()
            if sub is not None:
                sub.trial_ends_at = datetime.now(UTC) + timedelta(days=30)
                await session.commit()
```

Run: `uv run pytest tests/integration/test_scan_configs_crud.py -v`
Expected: FAIL.

- [ ] **Step 2: Create `backend/src/career_agent/api/scan_configs.py`**

```python
"""Scan configs API — CRUD. POST / PUT / run paywalled; GET / DELETE not."""
from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter

from career_agent.api.deps import CurrentDbUser, DbSession, EntitledDbUser
from career_agent.api.errors import AppError
from career_agent.schemas.scan_config import (
    ScanConfigCreate,
    ScanConfigOut,
    ScanConfigUpdate,
)
from career_agent.services.scan_config import ScanConfigService

router = APIRouter(prefix="/scan-configs", tags=["scan-configs"])


@router.get("")
async def list_scan_configs(
    user: CurrentDbUser,
    session: DbSession,
) -> dict[str, Any]:
    configs = await ScanConfigService(session).list_for_user(user.id)
    return {"data": [ScanConfigOut.model_validate(c).model_dump(mode="json") for c in configs]}


@router.post("", status_code=201)
async def create_scan_config(
    payload: ScanConfigCreate,
    user: EntitledDbUser,
    session: DbSession,
) -> dict[str, Any]:
    config = await ScanConfigService(session).create(user.id, payload)
    await session.commit()
    return {"data": ScanConfigOut.model_validate(config).model_dump(mode="json")}


@router.get("/{config_id}")
async def get_scan_config(
    config_id: UUID,
    user: CurrentDbUser,
    session: DbSession,
) -> dict[str, Any]:
    config = await ScanConfigService(session).get(user.id, config_id)
    if config is None:
        raise AppError(404, "SCAN_CONFIG_NOT_FOUND", "Scan config not found")
    return {"data": ScanConfigOut.model_validate(config).model_dump(mode="json")}


@router.put("/{config_id}")
async def update_scan_config(
    config_id: UUID,
    payload: ScanConfigUpdate,
    user: EntitledDbUser,
    session: DbSession,
) -> dict[str, Any]:
    config = await ScanConfigService(session).update(user.id, config_id, payload)
    if config is None:
        raise AppError(404, "SCAN_CONFIG_NOT_FOUND", "Scan config not found")
    await session.commit()
    return {"data": ScanConfigOut.model_validate(config).model_dump(mode="json")}


@router.delete("/{config_id}", status_code=204)
async def delete_scan_config(
    config_id: UUID,
    user: CurrentDbUser,
    session: DbSession,
) -> None:
    ok = await ScanConfigService(session).delete(user.id, config_id)
    if not ok:
        raise AppError(404, "SCAN_CONFIG_NOT_FOUND", "Scan config not found")
    await session.commit()
```

- [ ] **Step 3: Register router in `main.py`**

Find the existing router registrations block and add:

```python
from career_agent.api import scan_configs
app.include_router(scan_configs.router, prefix="/api/v1")
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/integration/test_scan_configs_crud.py -v
```

Expected: both tests PASS.

- [ ] **Step 5: Checkpoint**

Checkpoint message: `feat(api): add scan configs CRUD with paywall on POST/PUT`

---

## Task 16: Scan Runs API + Trigger

**Files:**
- Create: `backend/src/career_agent/api/scan_runs.py`
- Modify: `backend/src/career_agent/main.py` — register router
- Create: `backend/tests/integration/test_scan_run_trigger.py`

The trigger endpoint `POST /scan-configs/:id/run` is registered under the `/scan-runs` module's router via a secondary path, since it conceptually belongs to both. We keep it in `scan_runs.py` for cohesion.

- [ ] **Step 1: Write the failing test**

`backend/tests/integration/test_scan_run_trigger.py`:

```python
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from career_agent.db import get_session_factory
from career_agent.main import app
from career_agent.models.scan_config import ScanConfig
from career_agent.models.scan_run import ScanRun
from career_agent.models.user import User
from tests.conftest import FAKE_CLAIMS


@pytest.mark.asyncio
async def test_scan_run_trigger_creates_pending_run_and_sends_event(auth_headers, seed_profile):
    factory = get_session_factory()
    async with factory() as session:
        u = (await session.execute(select(User).where(User.cognito_sub == FAKE_CLAIMS["sub"]))).scalar_one()
        config = ScanConfig(
            user_id=u.id,
            name="Trigger test",
            companies=[{"name": "Stripe", "platform": "greenhouse", "board_slug": "stripe"}],
            schedule="manual",
            is_active=True,
        )
        session.add(config)
        await session.commit()
        config_id = config.id

    class _FakeClient:
        def __init__(self):
            self.sent: list = []

        async def send(self, event):
            self.sent.append(event)
            return ["evt_fake_1"]

    fake_client = _FakeClient()

    with (
        patch(
            "career_agent.integrations.cognito.CognitoJwtVerifier.verify",
            new=AsyncMock(return_value=FAKE_CLAIMS),
        ),
        patch(
            "career_agent.inngest.client.get_inngest_client",
            return_value=fake_client,
        ),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                f"/api/v1/scan-configs/{config_id}/run",
                headers=auth_headers,
            )
    assert resp.status_code == 202
    body = resp.json()["data"]
    scan_run_id = body["scan_run_id"]
    assert body["status"] == "pending"
    assert len(fake_client.sent) == 1

    # Verify the DB row
    async with factory() as session:
        row = (await session.execute(select(ScanRun).where(ScanRun.id == scan_run_id))).scalar_one()
        assert row.status == "pending"


@pytest.mark.asyncio
async def test_scan_run_trigger_404_on_unknown_config(auth_headers, seed_profile):
    from uuid import uuid4

    with patch(
        "career_agent.integrations.cognito.CognitoJwtVerifier.verify",
        new=AsyncMock(return_value=FAKE_CLAIMS),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                f"/api/v1/scan-configs/{uuid4()}/run",
                headers=auth_headers,
            )
    assert resp.status_code == 404
```

Run: `uv run pytest tests/integration/test_scan_run_trigger.py -v`
Expected: FAIL.

- [ ] **Step 2: Create `backend/src/career_agent/api/scan_runs.py`**

```python
"""Scan runs API — trigger + list + get detail."""
from __future__ import annotations

from typing import Any
from uuid import UUID

import inngest
from fastapi import APIRouter, Query

from career_agent.api.deps import CurrentDbUser, DbSession, EntitledDbUser
from career_agent.api.errors import AppError
from career_agent.inngest.client import get_inngest_client
from career_agent.schemas.scan_run import ScanResultOut, ScanRunDetail, ScanRunOut
from career_agent.services.scan_config import ScanConfigService
from career_agent.services.scan_run import ScanRunService

router = APIRouter(tags=["scan-runs"])


@router.post("/scan-configs/{config_id}/run", status_code=202)
async def trigger_scan(
    config_id: UUID,
    user: EntitledDbUser,
    session: DbSession,
) -> dict[str, Any]:
    config = await ScanConfigService(session).get(user.id, config_id)
    if config is None:
        raise AppError(404, "SCAN_CONFIG_NOT_FOUND", "Scan config not found")

    runs = ScanRunService(session)
    scan_run = await runs.create_pending(
        user_id=user.id, scan_config_id=config.id
    )
    await session.commit()

    client = get_inngest_client()
    try:
        sent_ids = await client.send(
            inngest.Event(
                name="scan/started",
                data={
                    "scan_config_id": str(config.id),
                    "user_id": str(user.id),
                    "scan_run_id": str(scan_run.id),
                },
            )
        )
    except Exception as e:
        # Mark the run failed so the user sees a clear error
        await runs.mark_failed(scan_run, f"Inngest send failed: {e}")
        await session.commit()
        raise AppError(
            503, "INNGEST_UNAVAILABLE", "Background worker is unavailable"
        ) from e

    if sent_ids:
        scan_run.inngest_event_id = str(sent_ids[0])
        await session.commit()

    return {
        "data": {
            "scan_run_id": str(scan_run.id),
            "status": scan_run.status,
        }
    }


@router.get("/scan-runs")
async def list_scan_runs(
    user: CurrentDbUser,
    session: DbSession,
    limit: int = Query(default=20, ge=1, le=100),
    status: str | None = Query(default=None),
) -> dict[str, Any]:
    runs = await ScanRunService(session).list_for_user(user.id, limit=limit, status=status)
    return {"data": [ScanRunOut.model_validate(r).model_dump(mode="json") for r in runs]}


@router.get("/scan-runs/{scan_run_id}")
async def get_scan_run(
    scan_run_id: UUID,
    user: CurrentDbUser,
    session: DbSession,
) -> dict[str, Any]:
    svc = ScanRunService(session)
    run = await svc.get_for_user(user.id, scan_run_id)
    if run is None:
        raise AppError(404, "SCAN_RUN_NOT_FOUND", "Scan run not found")
    results = await svc.list_results(run.id, limit=50)
    detail = ScanRunDetail(
        scan_run=ScanRunOut.model_validate(run),
        results=[ScanResultOut.model_validate(r) for r in results],
    )
    return {"data": detail.model_dump(mode="json")}
```

- [ ] **Step 3: Register router in `main.py`**

```python
from career_agent.api import scan_runs
app.include_router(scan_runs.router, prefix="/api/v1")
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/integration/test_scan_run_trigger.py -v
```

Expected: both tests PASS.

- [ ] **Step 5: Checkpoint**

Checkpoint message: `feat(api): add scan runs trigger + list + get detail`

---

## Task 17: Inngest Scan Function (`scan_boards_fn`)

**Files:**
- Create: `backend/src/career_agent/inngest/scan_boards.py`
- Create: `backend/tests/integration/test_inngest_scan_function.py`

- [ ] **Step 1: Create `backend/src/career_agent/inngest/scan_boards.py`**

```python
"""Inngest function: scan/started → scrape + classify + persist.

In unit/integration tests the real Inngest runtime is bypassed — tests call
`run_scan_boards(scan_run_id)` directly, which is the sync entry point the
Inngest wrapper delegates to.
"""
from __future__ import annotations

from uuid import UUID

import inngest

from career_agent.core.scanner.service import ScannerService
from career_agent.db import get_session_factory
from career_agent.inngest.client import get_inngest_client


async def run_scan_boards(scan_run_id: UUID) -> dict[str, int | bool]:
    """Pure-Python entry point. Opens its own DB session."""
    factory = get_session_factory()
    async with factory() as session:
        outcome = await ScannerService(session).run_scan(scan_run_id)
        await session.commit()
    return {
        "jobs_found": outcome.jobs_found,
        "jobs_new": outcome.jobs_new,
        "truncated": outcome.truncated,
    }


def register() -> inngest.Function:
    """Register the scan_boards function with the Inngest client."""
    client = get_inngest_client()

    @client.create_function(
        fn_id="scan-boards",
        trigger=inngest.TriggerEvent(event="scan/started"),
        concurrency=[
            inngest.Concurrency(limit=5, key="event.data.user_id"),
            inngest.Concurrency(limit=50),
        ],
        retries=3,
    )
    async def scan_boards_fn(ctx: inngest.Context) -> dict[str, int | bool]:
        scan_run_id = UUID(str(ctx.event.data["scan_run_id"]))
        return await ctx.step.run(
            "run-scan", run_scan_boards, scan_run_id
        )

    return scan_boards_fn
```

- [ ] **Step 2: Write the integration test**

`backend/tests/integration/test_inngest_scan_function.py`:

```python
import json
import re
from pathlib import Path

import pytest
import respx
from httpx import Response
from sqlalchemy import select

from career_agent.db import get_session_factory
from career_agent.inngest.scan_boards import run_scan_boards
from career_agent.models.scan_config import ScanConfig
from career_agent.models.scan_run import ScanRun
from career_agent.models.user import User
from tests.conftest import FAKE_CLAIMS
from tests.fixtures.fake_gemini import fake_gemini

_GH = json.loads(
    (Path(__file__).parent.parent / "fixtures" / "boards" / "greenhouse" / "stripe.json").read_text()
)


@pytest.mark.asyncio
@respx.mock
async def test_inngest_scan_boards_e2e(seed_profile) -> None:
    """Call run_scan_boards directly (bypass Inngest runtime)."""
    respx.get("https://boards-api.greenhouse.io/v1/boards/stripe/jobs?content=true").mock(
        return_value=Response(200, json=_GH)
    )

    factory = get_session_factory()
    async with factory() as session:
        user = (
            await session.execute(select(User).where(User.cognito_sub == FAKE_CLAIMS["sub"]))
        ).scalar_one()
        config = ScanConfig(
            user_id=user.id,
            name="Inngest test",
            companies=[{"name": "Stripe", "platform": "greenhouse", "board_slug": "stripe"}],
            schedule="manual",
            is_active=True,
        )
        session.add(config)
        await session.flush()
        run = ScanRun(user_id=user.id, scan_config_id=config.id, status="pending")
        session.add(run)
        await session.commit()
        run_id = run.id

    with fake_gemini({"Staff": "0.7", "Senior": "0.65"}):
        result = await run_scan_boards(run_id)

    assert result["jobs_found"] >= 2
    assert result["truncated"] is False

    async with factory() as session:
        reloaded = (
            await session.execute(select(ScanRun).where(ScanRun.id == run_id))
        ).scalar_one()
        assert reloaded.status == "completed"
```

Run: `uv run pytest tests/integration/test_inngest_scan_function.py -v`
Expected: PASS.

- [ ] **Step 3: Run lint + mypy**

```bash
uv run ruff check src/ 2>&1 | tail -3
uv run mypy src/ 2>&1 | tail -3
```

Expected: clean.

- [ ] **Step 4: Checkpoint**

Checkpoint message: `feat(inngest): add scan_boards function + direct-entry pure-python shim`

---

## Task 18: Batch L0 Rule Filter (TDD, pure Python)

**Files:**
- Create: `backend/src/career_agent/core/batch/__init__.py`
- Create: `backend/src/career_agent/core/batch/l0_filter.py`
- Create: `backend/tests/unit/test_l0_filter.py`

- [ ] **Step 1: Create `backend/src/career_agent/core/batch/__init__.py`**

```python
"""L0/L1/L2 batch processing funnel."""
```

- [ ] **Step 2: Write the failing tests**

`backend/tests/unit/test_l0_filter.py`:

```python
from career_agent.core.batch.l0_filter import l0_filter
from career_agent.models.job import Job
from career_agent.models.profile import Profile


def _job(**overrides) -> Job:
    defaults = dict(
        content_hash="test_" + str(id(object())),
        title="Test",
        description_md="x",
        requirements_json={},
        source="manual",
        location="Remote",
        salary_min=None,
        salary_max=None,
        seniority="senior",
    )
    defaults.update(overrides)
    return Job(**defaults)


def _profile(**overrides) -> Profile:
    defaults = dict(
        user_id="00000000-0000-0000-0000-000000000001",
        onboarding_state="done",
        target_roles=["senior engineer"],
        target_locations=["remote", "new york"],
        min_salary=150000,
        parsed_resume_json={"total_years_experience": 6, "skills": ["python"]},
    )
    defaults.update(overrides)
    p = Profile()
    for k, v in defaults.items():
        setattr(p, k, v)
    return p


def test_passes_remote_job() -> None:
    passes, reason = l0_filter(_job(location="Remote"), _profile())
    assert passes is True
    assert reason is None


def test_passes_target_location() -> None:
    passes, reason = l0_filter(_job(location="New York, NY"), _profile())
    assert passes is True


def test_filters_location_mismatch() -> None:
    passes, reason = l0_filter(_job(location="Tokyo"), _profile())
    assert passes is False
    assert reason == "location_mismatch"


def test_filters_salary_below_floor() -> None:
    passes, reason = l0_filter(
        _job(salary_min=80000, salary_max=110000), _profile(min_salary=150000)
    )
    assert passes is False
    assert reason == "below_min_salary"


def test_passes_when_salary_not_posted() -> None:
    """No salary data → pass (don't filter optimistically)."""
    passes, reason = l0_filter(_job(salary_min=None, salary_max=None), _profile())
    assert passes is True


def test_passes_when_no_min_salary_set() -> None:
    passes, reason = l0_filter(
        _job(salary_min=80000, salary_max=90000), _profile(min_salary=None)
    )
    assert passes is True


def test_filters_seniority_mismatch_junior_vs_staff() -> None:
    # Profile says "senior" (6 years), job says "principal" → wide gap
    passes, reason = l0_filter(
        _job(seniority="principal"),
        _profile(parsed_resume_json={"total_years_experience": 2, "skills": []}),
    )
    assert passes is False
    assert reason == "seniority_mismatch"


def test_passes_when_seniority_missing() -> None:
    passes, reason = l0_filter(_job(seniority=None), _profile())
    assert passes is True
```

Run: `uv run pytest tests/unit/test_l0_filter.py -v`
Expected: FAIL.

- [ ] **Step 3: Create `backend/src/career_agent/core/batch/l0_filter.py`**

```python
"""L0 rule filter — pure Python, no I/O, no LLM.

Parent spec Appendix D.8. Returns (passes, reason_if_filtered).
"""
from __future__ import annotations

from typing import Any

from career_agent.models.job import Job
from career_agent.models.profile import Profile


_LOCATION_ALIASES = {
    "nyc": "new york",
    "ny": "new york",
    "sf": "san francisco",
    "la": "los angeles",
}


def _normalize_location(loc: str) -> str:
    loc = loc.strip().lower()
    for short, full in _LOCATION_ALIASES.items():
        if short in loc.split():
            loc = loc.replace(short, full)
    return loc


def _location_match(job_location: str | None, targets: list[str]) -> bool:
    if not job_location:
        return True  # unknown → pass
    normalized = _normalize_location(job_location)
    if "remote" in normalized:
        return True
    for target in targets:
        if _normalize_location(target) in normalized:
            return True
        if normalized in _normalize_location(target):
            return True
    return False


_SENIORITY_RANK = {
    "junior": 1,
    "mid": 2,
    "senior": 3,
    "staff": 4,
    "principal": 5,
}


def _seniority_from_years(years: int) -> str:
    if years < 2:
        return "junior"
    if years < 5:
        return "mid"
    if years < 8:
        return "senior"
    if years < 12:
        return "staff"
    return "principal"


def l0_filter(job: Job, profile: Profile) -> tuple[bool, str | None]:
    """Returns (passes, reason_if_filtered)."""
    # Location
    targets: list[str] = list(profile.target_locations or [])
    if not _location_match(job.location, targets):
        return False, "location_mismatch"

    # Salary floor — only if the job posted a salary
    if profile.min_salary is not None:
        posted_max = job.salary_max
        if posted_max is not None and posted_max < profile.min_salary:
            return False, "below_min_salary"

    # Seniority ladder
    if job.seniority:
        parsed: dict[str, Any] = profile.parsed_resume_json or {}
        years = int(parsed.get("total_years_experience") or 0)
        profile_seniority = _seniority_from_years(years)
        profile_rank = _SENIORITY_RANK.get(profile_seniority, 3)
        job_rank = _SENIORITY_RANK.get(job.seniority.lower(), profile_rank)
        # Allow ±1 level. >1 level gap → mismatch.
        if abs(job_rank - profile_rank) > 1:
            return False, "seniority_mismatch"

    return True, None
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/unit/test_l0_filter.py -v
```

Expected: 8 tests PASS.

- [ ] **Step 5: Checkpoint**

Checkpoint message: `feat(batch): add L0 rule filter (location + salary + seniority)`

---

## Task 19: Batch Funnel (L1 Triage + L2 Evaluate + Orchestrator)

**Files:**
- Create: `backend/src/career_agent/core/batch/l1_triage.py`
- Create: `backend/src/career_agent/core/batch/l2_evaluate.py`
- Create: `backend/src/career_agent/core/batch/funnel.py`
- Create: `backend/tests/integration/test_batch_l1_triage.py`
- Create: `backend/tests/integration/test_batch_funnel.py`

- [ ] **Step 1: Create `backend/src/career_agent/core/batch/l1_triage.py`**

```python
"""L1 triage — Gemini relevance scoring wrapper for batch use."""
from __future__ import annotations

import asyncio
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from career_agent.config import get_settings
from career_agent.core.scanner.relevance import score_relevance
from career_agent.models.job import Job
from career_agent.models.profile import Profile


async def score_jobs_relevance(
    session: AsyncSession,
    *,
    user_id,
    job_ids: list,
) -> dict[str, float]:
    """Return {str(job_id): relevance_score} for the given jobs."""
    if not job_ids:
        return {}

    profile = (
        await session.execute(select(Profile).where(Profile.user_id == user_id))
    ).scalar_one_or_none()
    profile_summary: dict[str, Any] = {}
    if profile is not None:
        parsed = profile.parsed_resume_json or {}
        profile_summary = {
            "skills": list(parsed.get("skills", []))[:20],
            "years_experience": parsed.get("total_years_experience"),
            "target_roles": list(profile.target_roles or []),
            "target_locations": list(profile.target_locations or []),
        }

    jobs = (
        await session.execute(select(Job).where(Job.id.in_(job_ids)))
    ).scalars().all()

    settings = get_settings()
    sem = asyncio.Semaphore(max(1, settings.scan_l1_concurrency))

    async def _one(job: Job) -> tuple[str, float]:
        async with sem:
            score = await score_relevance(job=job, profile_summary=profile_summary)
        return str(job.id), score

    pairs = await asyncio.gather(*(_one(j) for j in jobs))
    return dict(pairs)
```

- [ ] **Step 2: Create `backend/src/career_agent/core/batch/l2_evaluate.py`**

```python
"""L2 evaluate — full 10-dim Claude evaluation per surviving job."""
from __future__ import annotations

import asyncio
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from career_agent.config import get_settings
from career_agent.core.evaluation.service import EvaluationContext, EvaluationService
from career_agent.models.evaluation import Evaluation
from career_agent.models.job import Job
from career_agent.services.usage_event import UsageEventService


async def evaluate_job_for_user(
    session: AsyncSession,
    *,
    user_id: UUID,
    job_id: UUID,
) -> Evaluation | None:
    """Run the full evaluation pipeline for a single (user, job)."""
    job = (
        await session.execute(select(Job).where(Job.id == job_id))
    ).scalar_one_or_none()
    if job is None:
        return None

    usage = UsageEventService(session)
    context = EvaluationContext(user_id=user_id, session=session, usage=usage)
    service = EvaluationService(context)
    return await service.evaluate(job_description=job.description_md)


async def evaluate_jobs_bounded(
    session: AsyncSession,
    *,
    user_id: UUID,
    job_ids: list[UUID],
) -> list[tuple[UUID, Evaluation | None]]:
    """Fan-out L2 evaluation with configured concurrency."""
    settings = get_settings()
    sem = asyncio.Semaphore(max(1, settings.batch_l2_concurrency))

    async def _one(jid: UUID) -> tuple[UUID, Evaluation | None]:
        async with sem:
            result = await evaluate_job_for_user(session, user_id=user_id, job_id=jid)
        return jid, result

    return await asyncio.gather(*(_one(jid) for jid in job_ids))
```

- [ ] **Step 3: Create `backend/src/career_agent/core/batch/funnel.py`**

```python
"""Batch funnel orchestrator — L0 → L1 → L2 stages."""
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from career_agent.config import get_settings
from career_agent.core.batch.l0_filter import l0_filter
from career_agent.core.batch.l1_triage import score_jobs_relevance
from career_agent.core.batch.l2_evaluate import evaluate_jobs_bounded
from career_agent.models.batch_run import BatchItem
from career_agent.models.job import Job
from career_agent.models.profile import Profile


async def run_l0(
    session: AsyncSession,
    *,
    batch_run_id: UUID,
    job_ids: list[UUID],
    user_id: UUID,
) -> list[UUID]:
    profile = (
        await session.execute(select(Profile).where(Profile.user_id == user_id))
    ).scalar_one_or_none()
    survivors: list[UUID] = []
    for jid in job_ids:
        job = (
            await session.execute(select(Job).where(Job.id == jid))
        ).scalar_one_or_none()
        if job is None:
            continue
        passes = True
        reason: str | None = None
        if profile is not None:
            passes, reason = l0_filter(job, profile)
        stage = "l0" if passes else "filtered"
        item = BatchItem(
            batch_run_id=batch_run_id,
            job_id=jid,
            stage=stage,
            filter_reason=reason,
        )
        session.add(item)
        if passes:
            survivors.append(jid)
    await session.flush()
    return survivors


async def run_l1(
    session: AsyncSession,
    *,
    batch_run_id: UUID,
    job_ids: list[UUID],
    user_id: UUID,
) -> list[UUID]:
    if not job_ids:
        return []
    settings = get_settings()
    scores = await score_jobs_relevance(session, user_id=user_id, job_ids=job_ids)
    survivors: list[UUID] = []
    for jid in job_ids:
        score = scores.get(str(jid), 0.0)
        # Update the stage of the most recent batch_item for this job in this run
        stmt = select(BatchItem).where(
            BatchItem.batch_run_id == batch_run_id, BatchItem.job_id == jid
        )
        item = (await session.execute(stmt)).scalar_one_or_none()
        if item is None:
            continue
        if score >= settings.batch_l1_relevance_threshold:
            item.stage = "l1"
            survivors.append(jid)
        else:
            item.stage = "filtered"
            item.filter_reason = "low_relevance"
    await session.flush()
    return survivors


async def run_l2(
    session: AsyncSession,
    *,
    batch_run_id: UUID,
    job_ids: list[UUID],
    user_id: UUID,
) -> list[UUID]:
    results = await evaluate_jobs_bounded(session, user_id=user_id, job_ids=job_ids)
    evaluated: list[UUID] = []
    for jid, evaluation in results:
        stmt = select(BatchItem).where(
            BatchItem.batch_run_id == batch_run_id, BatchItem.job_id == jid
        )
        item = (await session.execute(stmt)).scalar_one_or_none()
        if item is None:
            continue
        if evaluation is not None:
            item.stage = "done"
            item.evaluation_id = evaluation.id
            evaluated.append(jid)
        else:
            item.stage = "filtered"
            item.filter_reason = "l2_failed"
    await session.flush()
    return evaluated
```

- [ ] **Step 4: Write the failing tests**

`backend/tests/integration/test_batch_l1_triage.py`:

```python
import hashlib
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from career_agent.core.batch.l1_triage import score_jobs_relevance
from career_agent.db import get_session_factory
from career_agent.models.job import Job
from career_agent.models.user import User
from tests.conftest import FAKE_CLAIMS
from tests.fixtures.fake_gemini import fake_gemini


async def _user_id() -> UUID:
    factory = get_session_factory()
    async with factory() as s:
        r = await s.execute(select(User).where(User.cognito_sub == FAKE_CLAIMS["sub"]))
        return r.scalar_one().id


@pytest.mark.asyncio
async def test_l1_triage_scores_jobs(seed_profile):
    uid = await _user_id()
    factory = get_session_factory()
    async with factory() as session:
        h = hashlib.sha256(str(uuid4()).encode()).hexdigest()
        job = Job(
            content_hash=h,
            title="Staff Python Engineer",
            description_md="Remote role building Python services.",
            requirements_json={"skills": ["python"]},
            source="manual",
        )
        session.add(job)
        await session.commit()
        await session.refresh(job)
        jid = job.id

    with fake_gemini({"Staff": "0.82"}):
        async with factory() as session:
            scores = await score_jobs_relevance(session, user_id=uid, job_ids=[jid])
    assert str(jid) in scores
    assert scores[str(jid)] == pytest.approx(0.82, abs=0.01)
```

`backend/tests/integration/test_batch_funnel.py`:

```python
import hashlib
import json
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from career_agent.core.batch.funnel import run_l0, run_l1, run_l2
from career_agent.db import get_session_factory
from career_agent.models.batch_run import BatchItem, BatchRun
from career_agent.models.job import Job
from career_agent.models.user import User
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
            h = hashlib.sha256(f"batch-job-{i}-{uuid4()}".encode()).hexdigest()
            job = Job(
                content_hash=h,
                title=f"Senior Engineer {i}",
                description_md=f"Remote role {i} building systems.",
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


@pytest.mark.asyncio
async def test_funnel_l0_through_l2(seed_profile):
    uid = await _user_id()
    jids = await _make_jobs(2)

    factory = get_session_factory()
    async with factory() as session:
        brun = BatchRun(
            user_id=uid,
            status="pending",
            total_jobs=2,
            source_type="job_ids",
            source_ref="ad-hoc",
        )
        session.add(brun)
        await session.flush()
        # queue items
        for jid in jids:
            session.add(BatchItem(batch_run_id=brun.id, job_id=jid, stage="queued"))
        await session.commit()
        brun_id = brun.id

    # L0
    async with factory() as session:
        survivors_l0 = await run_l0(session, batch_run_id=brun_id, job_ids=jids, user_id=uid)
        await session.commit()
    assert len(survivors_l0) == 2

    # L1 — Gemini returns 0.75 (above 0.5 threshold)
    with fake_gemini({"Senior": "0.75"}):
        async with factory() as session:
            survivors_l1 = await run_l1(session, batch_run_id=brun_id, job_ids=survivors_l0, user_id=uid)
            await session.commit()
    assert len(survivors_l1) == 2

    # L2 — Claude eval each
    with fake_anthropic({"USER PROFILE": _CLAUDE_EVAL}):
        async with factory() as session:
            evaluated = await run_l2(session, batch_run_id=brun_id, job_ids=survivors_l1, user_id=uid)
            await session.commit()
    assert len(evaluated) == 2

    # Verify batch_items stages
    async with factory() as session:
        items = (
            await session.execute(
                select(BatchItem).where(BatchItem.batch_run_id == brun_id)
            )
        ).scalars().all()
        done_count = sum(1 for i in items if i.stage == "done")
        assert done_count == 2
```

Run: `uv run pytest tests/integration/test_batch_l1_triage.py tests/integration/test_batch_funnel.py -v`
Expected: all tests PASS.

- [ ] **Step 5: Checkpoint**

Checkpoint message: `feat(batch): add L1 triage + L2 fan-out + funnel orchestrator`

---

## Task 20: Batch Service (input resolution — all 3 modes)

**Files:**
- Create: `backend/src/career_agent/core/batch/service.py`
- Create: `backend/src/career_agent/services/batch_run.py`
- Create: `backend/tests/integration/test_batch_service_inputs.py`

- [ ] **Step 1: Create `backend/src/career_agent/services/batch_run.py`**

```python
"""BatchRun CRUD helpers."""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from career_agent.models.batch_run import BatchItem, BatchRun


class BatchRunService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_pending(
        self,
        *,
        user_id: UUID,
        total_jobs: int,
        source_type: str,
        source_ref: str | None,
    ) -> BatchRun:
        run = BatchRun(
            user_id=user_id,
            status="pending",
            total_jobs=total_jobs,
            source_type=source_type,
            source_ref=source_ref,
        )
        self.session.add(run)
        await self.session.flush()
        return run

    async def get_for_user(self, user_id: UUID, run_id: UUID) -> BatchRun | None:
        stmt = select(BatchRun).where(
            BatchRun.id == run_id, BatchRun.user_id == user_id
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def list_for_user(self, user_id: UUID, *, limit: int = 20) -> list[BatchRun]:
        stmt = (
            select(BatchRun)
            .where(BatchRun.user_id == user_id)
            .order_by(BatchRun.started_at.desc())
            .limit(limit)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def items_summary(self, run_id: UUID) -> dict[str, int]:
        stmt = select(BatchItem).where(BatchItem.batch_run_id == run_id)
        items = (await self.session.execute(stmt)).scalars().all()
        summary = {"queued": 0, "l0": 0, "l1": 0, "l2": 0, "done": 0, "filtered": 0}
        for item in items:
            stage = item.stage or "queued"
            if stage in summary:
                summary[stage] += 1
        return summary

    async def mark_running(self, run: BatchRun) -> None:
        run.status = "running"
        await self.session.flush()

    async def mark_completed(
        self,
        run: BatchRun,
        *,
        l0_passed: int,
        l1_passed: int,
        l2_evaluated: int,
    ) -> None:
        run.status = "completed"
        run.l0_passed = l0_passed
        run.l1_passed = l1_passed
        run.l2_evaluated = l2_evaluated
        run.completed_at = datetime.now(UTC)
        await self.session.flush()

    async def mark_failed(self, run: BatchRun, error: str) -> None:
        run.status = "failed"
        run.completed_at = datetime.now(UTC)
        await self.session.flush()
```

- [ ] **Step 2: Create `backend/src/career_agent/core/batch/service.py`**

```python
"""BatchService — resolves input, runs funnel, finalizes."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from career_agent.api.errors import AppError
from career_agent.core.batch.funnel import run_l0, run_l1, run_l2
from career_agent.core.evaluation.job_parser import JobParseError, parse_url
from career_agent.models.batch_run import BatchItem, BatchRun
from career_agent.models.job import Job
from career_agent.models.scan_result import ScanResult  # type: ignore[attr-defined]  # may alias
from career_agent.models.scan_run import ScanResult as ScanResultModel, ScanRun
from career_agent.services.batch_run import BatchRunService


class BatchService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.runs = BatchRunService(session)

    async def resolve_job_ids_from_scan(
        self, *, user_id: UUID, scan_run_id: UUID
    ) -> list[UUID]:
        run = (
            await self.session.execute(
                select(ScanRun).where(
                    ScanRun.id == scan_run_id, ScanRun.user_id == user_id
                )
            )
        ).scalar_one_or_none()
        if run is None:
            raise AppError(404, "SCAN_RUN_NOT_FOUND", "Scan run not found")
        if run.status != "completed":
            raise AppError(409, "SCAN_RUN_STILL_RUNNING", "Scan run not yet complete")
        results = (
            await self.session.execute(
                select(ScanResultModel).where(ScanResultModel.scan_run_id == scan_run_id)
            )
        ).scalars().all()
        return [r.job_id for r in results]

    async def resolve_job_ids_from_urls(
        self, *, user_id: UUID, urls: list[str]
    ) -> list[UUID]:
        """Parse each URL through the Phase 2a job parser. Dedupes into jobs pool."""
        from career_agent.core.scanner.dedup import compute_content_hash
        job_ids: list[UUID] = []
        for url in urls:
            try:
                parsed = await parse_url(url)
            except JobParseError:
                continue
            h = parsed.content_hash
            existing = (
                await self.session.execute(select(Job).where(Job.content_hash == h))
            ).scalar_one_or_none()
            if existing is not None:
                job_ids.append(existing.id)
                continue
            job = Job(
                content_hash=h,
                url=parsed.url,
                title=parsed.title,
                company=parsed.company,
                location=parsed.location,
                salary_min=parsed.salary_min,
                salary_max=parsed.salary_max,
                employment_type=parsed.employment_type,
                seniority=parsed.seniority,
                description_md=parsed.description_md,
                requirements_json=parsed.requirements_json,
                source="manual",
            )
            self.session.add(job)
            await self.session.flush()
            job_ids.append(job.id)
        return job_ids

    async def resolve_job_ids_from_ids(self, *, ids: list[UUID]) -> list[UUID]:
        existing = (
            await self.session.execute(select(Job.id).where(Job.id.in_(ids)))
        ).scalars().all()
        return list(existing)

    async def start_batch(
        self,
        *,
        user_id: UUID,
        job_ids: list[UUID],
        source_type: str,
        source_ref: str | None,
    ) -> BatchRun:
        run = await self.runs.create_pending(
            user_id=user_id,
            total_jobs=len(job_ids),
            source_type=source_type,
            source_ref=source_ref,
        )
        for jid in job_ids:
            self.session.add(
                BatchItem(batch_run_id=run.id, job_id=jid, stage="queued")
            )
        await self.session.flush()
        return run

    async def run_funnel(self, *, batch_run_id: UUID) -> None:
        run = (
            await self.session.execute(
                select(BatchRun).where(BatchRun.id == batch_run_id)
            )
        ).scalar_one()
        await self.runs.mark_running(run)
        item_rows = (
            await self.session.execute(
                select(BatchItem).where(BatchItem.batch_run_id == run.id)
            )
        ).scalars().all()
        job_ids: list[UUID] = [i.job_id for i in item_rows]

        try:
            l0_survivors = await run_l0(
                self.session,
                batch_run_id=run.id,
                job_ids=job_ids,
                user_id=run.user_id,
            )
            l1_survivors = await run_l1(
                self.session,
                batch_run_id=run.id,
                job_ids=l0_survivors,
                user_id=run.user_id,
            )
            evaluated = await run_l2(
                self.session,
                batch_run_id=run.id,
                job_ids=l1_survivors,
                user_id=run.user_id,
            )
        except Exception as e:
            await self.runs.mark_failed(run, str(e))
            raise

        await self.runs.mark_completed(
            run,
            l0_passed=len(l0_survivors),
            l1_passed=len(l1_survivors),
            l2_evaluated=len(evaluated),
        )
```

- [ ] **Step 3: Write the failing test**

`backend/tests/integration/test_batch_service_inputs.py`:

```python
import hashlib
import json
from uuid import UUID, uuid4

import pytest
import respx
from httpx import Response
from sqlalchemy import select

from career_agent.api.errors import AppError
from career_agent.core.batch.service import BatchService
from career_agent.db import get_session_factory
from career_agent.models.job import Job
from career_agent.models.scan_run import ScanResult, ScanRun
from career_agent.models.scan_config import ScanConfig
from career_agent.models.user import User
from tests.conftest import FAKE_CLAIMS
from tests.fixtures.fake_gemini import fake_gemini


async def _uid() -> UUID:
    factory = get_session_factory()
    async with factory() as s:
        r = await s.execute(select(User).where(User.cognito_sub == FAKE_CLAIMS["sub"]))
        return r.scalar_one().id


@pytest.mark.asyncio
async def test_resolve_from_job_ids(seed_profile):
    uid = await _uid()
    factory = get_session_factory()
    async with factory() as session:
        h = hashlib.sha256(f"input-test-{uuid4()}".encode()).hexdigest()
        job = Job(
            content_hash=h,
            title="Existing Job",
            description_md="x",
            requirements_json={},
            source="manual",
        )
        session.add(job)
        await session.commit()
        jid = job.id

    async with factory() as session:
        svc = BatchService(session)
        ids = await svc.resolve_job_ids_from_ids(ids=[jid])
    assert ids == [jid]


@pytest.mark.asyncio
async def test_resolve_from_scan_run_requires_completed(seed_profile):
    uid = await _uid()
    factory = get_session_factory()
    async with factory() as session:
        config = ScanConfig(
            user_id=uid,
            name="T",
            companies=[],
            schedule="manual",
            is_active=True,
        )
        session.add(config)
        await session.flush()
        run = ScanRun(
            user_id=uid,
            scan_config_id=config.id,
            status="running",
        )
        session.add(run)
        await session.commit()
        run_id = run.id

    async with factory() as session:
        svc = BatchService(session)
        with pytest.raises(AppError) as exc:
            await svc.resolve_job_ids_from_scan(user_id=uid, scan_run_id=run_id)
        assert exc.value.code == "SCAN_RUN_STILL_RUNNING"
```

Run: `uv run pytest tests/integration/test_batch_service_inputs.py -v`
Expected: both tests PASS.

- [ ] **Step 4: Checkpoint**

Checkpoint message: `feat(batch): add BatchService with 3-mode input resolution`

---

## Task 21: Batch Runs API

**Files:**
- Create: `backend/src/career_agent/api/batch_runs.py`
- Modify: `backend/src/career_agent/main.py`
- Create: `backend/tests/integration/test_batch_runs_crud.py`
- Create: `backend/tests/integration/test_batch_runs_scan_run_id.py`

- [ ] **Step 1: Write the failing tests**

`backend/tests/integration/test_batch_runs_crud.py`:

```python
import hashlib
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from career_agent.db import get_session_factory
from career_agent.main import app
from career_agent.models.batch_run import BatchRun
from career_agent.models.job import Job
from career_agent.models.user import User
from tests.conftest import FAKE_CLAIMS


async def _uid() -> UUID:
    factory = get_session_factory()
    async with factory() as s:
        r = await s.execute(select(User).where(User.cognito_sub == FAKE_CLAIMS["sub"]))
        return r.scalar_one().id


async def _seed_job() -> UUID:
    factory = get_session_factory()
    async with factory() as session:
        h = hashlib.sha256(f"batch-api-{uuid4()}".encode()).hexdigest()
        job = Job(
            content_hash=h,
            title="Test",
            description_md="x",
            requirements_json={},
            source="manual",
        )
        session.add(job)
        await session.commit()
        return job.id


class _FakeClient:
    def __init__(self):
        self.sent = []

    async def send(self, event):
        self.sent.append(event)
        return ["evt_batch_1"]


@pytest.mark.asyncio
async def test_batch_run_create_from_job_ids(auth_headers, seed_profile):
    jid = await _seed_job()
    fake = _FakeClient()

    with (
        patch(
            "career_agent.integrations.cognito.CognitoJwtVerifier.verify",
            new=AsyncMock(return_value=FAKE_CLAIMS),
        ),
        patch("career_agent.inngest.client.get_inngest_client", return_value=fake),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/batch-runs",
                json={"job_ids": [str(jid)]},
                headers=auth_headers,
            )
    assert resp.status_code == 202
    data = resp.json()["data"]
    assert data["status"] == "pending"
    assert data["total_jobs"] == 1
    assert len(fake.sent) == 1


@pytest.mark.asyncio
async def test_batch_run_reject_multiple_inputs(auth_headers, seed_profile):
    jid = await _seed_job()
    with patch(
        "career_agent.integrations.cognito.CognitoJwtVerifier.verify",
        new=AsyncMock(return_value=FAKE_CLAIMS),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/batch-runs",
                json={
                    "job_ids": [str(jid)],
                    "job_urls": ["https://example.com/x"],
                },
                headers=auth_headers,
            )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_batch_run_list_and_get(auth_headers, seed_profile):
    factory = get_session_factory()
    uid = await _uid()
    async with factory() as session:
        run = BatchRun(
            user_id=uid,
            status="completed",
            total_jobs=3,
            l0_passed=3,
            l1_passed=2,
            l2_evaluated=2,
            source_type="job_ids",
            source_ref="ad-hoc",
        )
        session.add(run)
        await session.commit()
        rid = run.id

    with patch(
        "career_agent.integrations.cognito.CognitoJwtVerifier.verify",
        new=AsyncMock(return_value=FAKE_CLAIMS),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r1 = await client.get("/api/v1/batch-runs", headers=auth_headers)
            assert r1.status_code == 200
            ids = [b["id"] for b in r1.json()["data"]]
            assert str(rid) in ids

            r2 = await client.get(f"/api/v1/batch-runs/{rid}", headers=auth_headers)
            assert r2.status_code == 200
            body = r2.json()["data"]
            assert body["batch_run"]["id"] == str(rid)
            assert "items_summary" in body
            assert "top_results" in body
```

`backend/tests/integration/test_batch_runs_scan_run_id.py`:

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
from career_agent.models.scan_config import ScanConfig
from career_agent.models.scan_run import ScanResult, ScanRun
from career_agent.models.user import User
from tests.conftest import FAKE_CLAIMS


async def _uid() -> UUID:
    factory = get_session_factory()
    async with factory() as s:
        r = await s.execute(select(User).where(User.cognito_sub == FAKE_CLAIMS["sub"]))
        return r.scalar_one().id


class _FakeClient:
    def __init__(self):
        self.sent = []
    async def send(self, event):
        self.sent.append(event)
        return ["evt_x"]


@pytest.mark.asyncio
async def test_batch_run_from_completed_scan_run(auth_headers, seed_profile):
    uid = await _uid()
    factory = get_session_factory()
    async with factory() as session:
        config = ScanConfig(
            user_id=uid, name="T", companies=[], schedule="manual", is_active=True
        )
        session.add(config)
        await session.flush()
        run = ScanRun(
            user_id=uid,
            scan_config_id=config.id,
            status="completed",
            jobs_found=1,
            jobs_new=1,
        )
        session.add(run)
        await session.flush()
        h = hashlib.sha256(f"scan-{uuid4()}".encode()).hexdigest()
        job = Job(
            content_hash=h,
            title="Senior",
            description_md="x",
            requirements_json={},
            source="greenhouse",
        )
        session.add(job)
        await session.flush()
        session.add(
            ScanResult(scan_run_id=run.id, job_id=job.id, relevance_score=0.8, is_new=True)
        )
        await session.commit()
        scan_run_id = run.id

    fake = _FakeClient()
    with (
        patch(
            "career_agent.integrations.cognito.CognitoJwtVerifier.verify",
            new=AsyncMock(return_value=FAKE_CLAIMS),
        ),
        patch("career_agent.inngest.client.get_inngest_client", return_value=fake),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/batch-runs",
                json={"scan_run_id": str(scan_run_id)},
                headers=auth_headers,
            )
    assert resp.status_code == 202
    assert resp.json()["data"]["total_jobs"] == 1


@pytest.mark.asyncio
async def test_batch_run_from_running_scan_run_is_409(auth_headers, seed_profile):
    uid = await _uid()
    factory = get_session_factory()
    async with factory() as session:
        config = ScanConfig(
            user_id=uid, name="T", companies=[], schedule="manual", is_active=True
        )
        session.add(config)
        await session.flush()
        run = ScanRun(
            user_id=uid, scan_config_id=config.id, status="running"
        )
        session.add(run)
        await session.commit()
        scan_run_id = run.id

    with patch(
        "career_agent.integrations.cognito.CognitoJwtVerifier.verify",
        new=AsyncMock(return_value=FAKE_CLAIMS),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/batch-runs",
                json={"scan_run_id": str(scan_run_id)},
                headers=auth_headers,
            )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "SCAN_RUN_STILL_RUNNING"
```

Run: `uv run pytest tests/integration/test_batch_runs_crud.py tests/integration/test_batch_runs_scan_run_id.py -v`
Expected: FAIL.

- [ ] **Step 2: Create `backend/src/career_agent/api/batch_runs.py`**

```python
"""Batch runs API."""
from __future__ import annotations

from typing import Any
from uuid import UUID

import inngest
from fastapi import APIRouter, Query
from sqlalchemy import select

from career_agent.api.deps import CurrentDbUser, DbSession, EntitledDbUser
from career_agent.api.errors import AppError
from career_agent.core.batch.service import BatchService
from career_agent.inngest.client import get_inngest_client
from career_agent.models.evaluation import Evaluation
from career_agent.models.job import Job
from career_agent.schemas.batch_run import (
    BatchEvaluationSummary,
    BatchItemsSummary,
    BatchRunCreate,
    BatchRunDetail,
    BatchRunOut,
)
from career_agent.services.batch_run import BatchRunService

router = APIRouter(prefix="/batch-runs", tags=["batch-runs"])


@router.post("", status_code=202)
async def create_batch_run(
    payload: BatchRunCreate,
    user: EntitledDbUser,
    session: DbSession,
) -> dict[str, Any]:
    service = BatchService(session)

    if payload.scan_run_id is not None:
        job_ids = await service.resolve_job_ids_from_scan(
            user_id=user.id, scan_run_id=payload.scan_run_id
        )
        source_type = "scan_run_id"
        source_ref = str(payload.scan_run_id)
    elif payload.job_urls is not None:
        job_ids = await service.resolve_job_ids_from_urls(
            user_id=user.id, urls=payload.job_urls
        )
        source_type = "job_urls"
        source_ref = None
    elif payload.job_ids is not None:
        job_ids = await service.resolve_job_ids_from_ids(ids=payload.job_ids)
        source_type = "job_ids"
        source_ref = None
    else:
        raise AppError(422, "INVALID_BATCH_INPUT", "No input provided")

    if not job_ids:
        raise AppError(422, "INVALID_BATCH_INPUT", "No valid jobs resolved from input")

    run = await service.start_batch(
        user_id=user.id,
        job_ids=job_ids,
        source_type=source_type,
        source_ref=source_ref,
    )
    await session.commit()

    # Fire Inngest event
    client = get_inngest_client()
    try:
        sent_ids = await client.send(
            inngest.Event(
                name="batch/started",
                data={
                    "batch_run_id": str(run.id),
                    "user_id": str(user.id),
                },
            )
        )
    except Exception as e:
        runs_svc = BatchRunService(session)
        await runs_svc.mark_failed(run, f"Inngest send failed: {e}")
        await session.commit()
        raise AppError(
            503, "INNGEST_UNAVAILABLE", "Background worker is unavailable"
        ) from e

    if sent_ids:
        run.inngest_event_id = str(sent_ids[0])
        await session.commit()

    return {"data": BatchRunOut.model_validate(run).model_dump(mode="json")}


@router.get("")
async def list_batch_runs(
    user: CurrentDbUser,
    session: DbSession,
    limit: int = Query(default=20, ge=1, le=100),
) -> dict[str, Any]:
    runs = await BatchRunService(session).list_for_user(user.id, limit=limit)
    return {"data": [BatchRunOut.model_validate(r).model_dump(mode="json") for r in runs]}


@router.get("/{batch_run_id}")
async def get_batch_run(
    batch_run_id: UUID,
    user: CurrentDbUser,
    session: DbSession,
) -> dict[str, Any]:
    svc = BatchRunService(session)
    run = await svc.get_for_user(user.id, batch_run_id)
    if run is None:
        raise AppError(404, "BATCH_RUN_NOT_FOUND", "Batch run not found")

    summary_raw = await svc.items_summary(run.id)
    summary = BatchItemsSummary(**summary_raw)

    # Top 10 results: join evaluations via completed batch_items
    stmt = (
        select(Evaluation, Job)
        .join(Job, Evaluation.job_id == Job.id)
        .where(
            Evaluation.user_id == user.id,
            Evaluation.job_id.in_(
                select(Job.id).join(
                    # pick jobs linked from this batch run's done items
                    select(Job.id).select_from(Job).subquery()
                )
            ),
        )
        .order_by(Evaluation.match_score.desc())
        .limit(10)
    )
    # Simpler approach: re-query via batch_items directly
    from career_agent.models.batch_run import BatchItem
    done_items = (
        await session.execute(
            select(BatchItem).where(
                BatchItem.batch_run_id == run.id,
                BatchItem.stage == "done",
                BatchItem.evaluation_id.isnot(None),
            )
        )
    ).scalars().all()
    eval_ids = [i.evaluation_id for i in done_items if i.evaluation_id is not None]
    evaluations = []
    if eval_ids:
        evaluations = (
            await session.execute(
                select(Evaluation)
                .where(Evaluation.id.in_(eval_ids))
                .order_by(Evaluation.match_score.desc())
                .limit(10)
            )
        ).scalars().all()

    top_results: list[BatchEvaluationSummary] = []
    for ev in evaluations:
        job = (await session.execute(select(Job).where(Job.id == ev.job_id))).scalar_one()
        top_results.append(
            BatchEvaluationSummary(
                evaluation_id=ev.id,
                job_id=ev.job_id,
                job_title=job.title,
                company=job.company,
                overall_grade=ev.overall_grade,
                match_score=ev.match_score,
            )
        )

    detail = BatchRunDetail(
        batch_run=BatchRunOut.model_validate(run),
        items_summary=summary,
        top_results=top_results,
    )
    return {"data": detail.model_dump(mode="json")}
```

- [ ] **Step 3: Register router in `main.py`**

```python
from career_agent.api import batch_runs
app.include_router(batch_runs.router, prefix="/api/v1")
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/integration/test_batch_runs_crud.py tests/integration/test_batch_runs_scan_run_id.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Checkpoint**

Checkpoint message: `feat(api): add batch runs CRUD with 3-mode input resolution`

---

## Task 22: Inngest Batch Function (`batch_evaluate_fn`)

**Files:**
- Create: `backend/src/career_agent/inngest/batch_evaluate.py`
- Create: `backend/tests/integration/test_inngest_batch_function.py`

- [ ] **Step 1: Create `backend/src/career_agent/inngest/batch_evaluate.py`**

```python
"""Inngest function: batch/started → run funnel.

Tests call `run_batch_evaluate(batch_run_id)` directly, bypassing Inngest's
runtime. The Inngest wrapper only adds durability + retries in production.
"""
from __future__ import annotations

from uuid import UUID

import inngest

from career_agent.core.batch.service import BatchService
from career_agent.db import get_session_factory
from career_agent.inngest.client import get_inngest_client


async def run_batch_evaluate(batch_run_id: UUID) -> dict[str, str]:
    factory = get_session_factory()
    async with factory() as session:
        await BatchService(session).run_funnel(batch_run_id=batch_run_id)
        await session.commit()
    return {"batch_run_id": str(batch_run_id)}


def register() -> inngest.Function:
    client = get_inngest_client()

    @client.create_function(
        fn_id="batch-evaluate",
        trigger=inngest.TriggerEvent(event="batch/started"),
        concurrency=[
            inngest.Concurrency(limit=5, key="event.data.user_id"),
            inngest.Concurrency(limit=50),
        ],
        retries=3,
    )
    async def batch_evaluate_fn(ctx: inngest.Context) -> dict[str, str]:
        batch_run_id = UUID(str(ctx.event.data["batch_run_id"]))
        return await ctx.step.run("run-funnel", run_batch_evaluate, batch_run_id)

    return batch_evaluate_fn
```

- [ ] **Step 2: Write the test**

`backend/tests/integration/test_inngest_batch_function.py`:

```python
import hashlib
import json
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from career_agent.db import get_session_factory
from career_agent.inngest.batch_evaluate import run_batch_evaluate
from career_agent.models.batch_run import BatchItem, BatchRun
from career_agent.models.job import Job
from career_agent.models.user import User
from tests.conftest import FAKE_CLAIMS
from tests.fixtures.fake_anthropic import fake_anthropic
from tests.fixtures.fake_gemini import fake_gemini

_CLAUDE = json.dumps(
    {
        "dimensions": {
            "domain_relevance": {"score": 0.9, "grade": "A-", "reasoning": "", "signals": []},
            "role_match": {"score": 0.85, "grade": "A-", "reasoning": "", "signals": []},
            "trajectory_fit": {"score": 0.8, "grade": "B+", "reasoning": "", "signals": []},
            "culture_signal": {"score": 0.75, "grade": "B", "reasoning": "", "signals": []},
            "red_flags": {"score": 0.9, "grade": "A", "reasoning": "", "signals": []},
            "growth_potential": {"score": 0.8, "grade": "B+", "reasoning": "", "signals": []},
        },
        "overall_reasoning": "Fit.",
        "red_flag_items": [],
        "personalization_notes": "",
    }
)


async def _uid() -> UUID:
    factory = get_session_factory()
    async with factory() as s:
        r = await s.execute(select(User).where(User.cognito_sub == FAKE_CLAIMS["sub"]))
        return r.scalar_one().id


@pytest.mark.asyncio
async def test_inngest_batch_evaluate_e2e(seed_profile):
    uid = await _uid()
    factory = get_session_factory()
    async with factory() as session:
        h = hashlib.sha256(f"inngest-batch-{uuid4()}".encode()).hexdigest()
        job = Job(
            content_hash=h,
            title="Senior Engineer",
            description_md="Remote role building systems.",
            requirements_json={"skills": ["python"]},
            source="manual",
            location="Remote",
            salary_min=170000,
            salary_max=220000,
            seniority="senior",
        )
        session.add(job)
        await session.flush()
        run = BatchRun(
            user_id=uid,
            status="pending",
            total_jobs=1,
            source_type="job_ids",
            source_ref="ad-hoc",
        )
        session.add(run)
        await session.flush()
        session.add(BatchItem(batch_run_id=run.id, job_id=job.id, stage="queued"))
        await session.commit()
        run_id = run.id

    with fake_gemini({"Senior": "0.8"}), fake_anthropic({"USER PROFILE": _CLAUDE}):
        result = await run_batch_evaluate(run_id)

    assert result["batch_run_id"] == str(run_id)

    async with factory() as session:
        reloaded = (
            await session.execute(select(BatchRun).where(BatchRun.id == run_id))
        ).scalar_one()
        assert reloaded.status == "completed"
        assert reloaded.l0_passed == 1
        assert reloaded.l1_passed == 1
        assert reloaded.l2_evaluated == 1
```

Run: `uv run pytest tests/integration/test_inngest_batch_function.py -v`
Expected: PASS.

- [ ] **Step 3: Checkpoint**

Checkpoint message: `feat(inngest): add batch_evaluate function + pure-python entry shim`

---

## Task 23: Inngest Serve Endpoint + Function Registry

**Files:**
- Create: `backend/src/career_agent/inngest/functions.py`
- Create: `backend/src/career_agent/api/inngest.py`
- Modify: `backend/src/career_agent/main.py`
- Create: `backend/tests/integration/test_inngest_serve_endpoint.py`

- [ ] **Step 1: Create `backend/src/career_agent/inngest/functions.py`**

```python
"""Registry of all Inngest functions served by the app."""
from __future__ import annotations

import inngest

from career_agent.inngest.batch_evaluate import register as register_batch_evaluate
from career_agent.inngest.scan_boards import register as register_scan_boards


def all_functions() -> list[inngest.Function]:
    return [register_scan_boards(), register_batch_evaluate()]
```

- [ ] **Step 2: Create `backend/src/career_agent/api/inngest.py`**

```python
"""Inngest serve endpoint — POST/GET/PUT /api/v1/inngest.

In dev (INNGEST_DEV=true) signatures are not required. In prod, inngest's
fastapi integration enforces signature verification via the signing key.
"""
from __future__ import annotations

from fastapi import APIRouter, FastAPI

from career_agent.inngest.client import get_inngest_client
from career_agent.inngest.functions import all_functions


def mount_inngest(app: FastAPI) -> None:
    """Register Inngest serve routes on the FastAPI app.

    Use this from main.py instead of include_router because inngest's serve
    helper mounts all 3 HTTP methods (POST/GET/PUT) on one path internally.
    """
    import inngest.fast_api

    inngest.fast_api.serve(
        app,
        get_inngest_client(),
        all_functions(),
        serve_path="/api/v1/inngest",
    )


# No APIRouter here; inngest mounts directly on the app.
```

- [ ] **Step 3: Modify `backend/src/career_agent/main.py`**

After all `include_router(...)` calls, add:

```python
from career_agent.api.inngest import mount_inngest

mount_inngest(app)
```

- [ ] **Step 4: Write the failing test**

`backend/tests/integration/test_inngest_serve_endpoint.py`:

```python
import pytest
from httpx import ASGITransport, AsyncClient

from career_agent.main import app


@pytest.mark.asyncio
async def test_inngest_serve_get_responds():
    """GET /api/v1/inngest is used by the Inngest dev server to discover functions."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/inngest")
    # Inngest returns 200 with function metadata, or 401/405 depending on SDK version.
    # Accept any 2xx or expected no-auth response.
    assert resp.status_code in (200, 201, 401, 405)
```

Run: `uv run pytest tests/integration/test_inngest_serve_endpoint.py -v`
Expected: PASS.

- [ ] **Step 5: Run full backend suite + lint + mypy**

```bash
uv run pytest tests/ 2>&1 | tail -5
uv run ruff check src/ 2>&1 | tail -3
uv run mypy src/ 2>&1 | tail -3
```

Expected: all passing + clean.

- [ ] **Step 6: Checkpoint**

Checkpoint message: `feat(inngest): add serve endpoint + mount scan + batch functions`

---

## Task 24: Applications Service + API

**Files:**
- Create: `backend/src/career_agent/services/application.py`
- Create: `backend/src/career_agent/api/applications.py`
- Modify: `backend/src/career_agent/main.py`
- Create: `backend/tests/integration/test_applications_crud.py`
- Create: `backend/tests/integration/test_applications_filters.py`

- [ ] **Step 1: Create `backend/src/career_agent/services/application.py`**

```python
"""Application service — CRUD scoped by user_id."""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from career_agent.models.application import Application
from career_agent.schemas.application import ApplicationCreate, ApplicationUpdate


class ApplicationService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_for_user(
        self,
        user_id: UUID,
        *,
        status: str | None = None,
    ) -> list[Application]:
        stmt = select(Application).where(Application.user_id == user_id)
        if status:
            stmt = stmt.where(Application.status == status)
        stmt = stmt.order_by(Application.updated_at.desc())
        return list((await self.session.execute(stmt)).scalars().all())

    async def get(self, user_id: UUID, app_id: UUID) -> Application | None:
        stmt = select(Application).where(
            Application.id == app_id, Application.user_id == user_id
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def create(
        self, user_id: UUID, payload: ApplicationCreate
    ) -> Application | None:
        row = Application(
            user_id=user_id,
            job_id=payload.job_id,
            status=payload.status,
            evaluation_id=payload.evaluation_id,
            cv_output_id=payload.cv_output_id,
            notes=payload.notes,
            applied_at=datetime.now(UTC) if payload.status == "applied" else None,
        )
        self.session.add(row)
        try:
            await self.session.flush()
        except IntegrityError:
            await self.session.rollback()
            return None
        return row

    async def update(
        self, user_id: UUID, app_id: UUID, payload: ApplicationUpdate
    ) -> Application | None:
        app = await self.get(user_id, app_id)
        if app is None:
            return None
        data = payload.model_dump(exclude_unset=True)
        if "status" in data and data["status"] == "applied" and app.applied_at is None:
            app.applied_at = datetime.now(UTC)
        for k, v in data.items():
            setattr(app, k, v)
        app.updated_at = datetime.now(UTC)
        await self.session.flush()
        return app

    async def delete(self, user_id: UUID, app_id: UUID) -> bool:
        app = await self.get(user_id, app_id)
        if app is None:
            return False
        await self.session.delete(app)
        await self.session.flush()
        return True
```

- [ ] **Step 2: Create `backend/src/career_agent/api/applications.py`**

```python
"""Applications API — pipeline CRUD. Non-paywalled (trial-expired users can still manage)."""
from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Query

from career_agent.api.deps import CurrentDbUser, DbSession
from career_agent.api.errors import AppError
from career_agent.models.evaluation import Evaluation
from career_agent.schemas.application import (
    ApplicationCreate,
    ApplicationOut,
    ApplicationUpdate,
)
from career_agent.services.application import ApplicationService

from sqlalchemy import select

router = APIRouter(prefix="/applications", tags=["applications"])


@router.get("")
async def list_applications(
    user: CurrentDbUser,
    session: DbSession,
    status: str | None = Query(default=None),
    min_grade: str | None = Query(default=None),
) -> dict[str, Any]:
    apps = await ApplicationService(session).list_for_user(user.id, status=status)

    # Optional min_grade filter: requires the linked evaluation to exist
    if min_grade:
        grade_order = ["F", "D", "C", "C+", "B-", "B", "B+", "A-", "A"]
        threshold_idx = grade_order.index(min_grade) if min_grade in grade_order else 0
        filtered: list[Any] = []
        for a in apps:
            if a.evaluation_id is None:
                continue
            ev = (
                await session.execute(
                    select(Evaluation).where(Evaluation.id == a.evaluation_id)
                )
            ).scalar_one_or_none()
            if ev is None:
                continue
            if ev.overall_grade in grade_order and grade_order.index(ev.overall_grade) >= threshold_idx:
                filtered.append(a)
        apps = filtered

    return {
        "data": [ApplicationOut.model_validate(a).model_dump(mode="json") for a in apps]
    }


@router.post("", status_code=201)
async def create_application(
    payload: ApplicationCreate,
    user: CurrentDbUser,
    session: DbSession,
) -> dict[str, Any]:
    row = await ApplicationService(session).create(user.id, payload)
    if row is None:
        raise AppError(409, "APPLICATION_ALREADY_EXISTS", "An application already exists for this job")
    await session.commit()
    return {"data": ApplicationOut.model_validate(row).model_dump(mode="json")}


@router.get("/{app_id}")
async def get_application(
    app_id: UUID,
    user: CurrentDbUser,
    session: DbSession,
) -> dict[str, Any]:
    row = await ApplicationService(session).get(user.id, app_id)
    if row is None:
        raise AppError(404, "APPLICATION_NOT_FOUND", "Application not found")
    return {"data": ApplicationOut.model_validate(row).model_dump(mode="json")}


@router.put("/{app_id}")
async def update_application(
    app_id: UUID,
    payload: ApplicationUpdate,
    user: CurrentDbUser,
    session: DbSession,
) -> dict[str, Any]:
    row = await ApplicationService(session).update(user.id, app_id, payload)
    if row is None:
        raise AppError(404, "APPLICATION_NOT_FOUND", "Application not found")
    await session.commit()
    return {"data": ApplicationOut.model_validate(row).model_dump(mode="json")}


@router.delete("/{app_id}", status_code=204)
async def delete_application(
    app_id: UUID,
    user: CurrentDbUser,
    session: DbSession,
) -> None:
    ok = await ApplicationService(session).delete(user.id, app_id)
    if not ok:
        raise AppError(404, "APPLICATION_NOT_FOUND", "Application not found")
    await session.commit()
```

- [ ] **Step 3: Register router in `main.py`**

```python
from career_agent.api import applications
app.include_router(applications.router, prefix="/api/v1")
```

- [ ] **Step 4: Write the failing tests**

`backend/tests/integration/test_applications_crud.py`:

```python
import hashlib
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select

from career_agent.db import get_session_factory
from career_agent.main import app
from career_agent.models.application import Application
from career_agent.models.job import Job
from career_agent.models.user import User
from tests.conftest import FAKE_CLAIMS


async def _uid() -> UUID:
    factory = get_session_factory()
    async with factory() as s:
        r = await s.execute(select(User).where(User.cognito_sub == FAKE_CLAIMS["sub"]))
        return r.scalar_one().id


async def _seed_job() -> UUID:
    factory = get_session_factory()
    async with factory() as session:
        h = hashlib.sha256(f"app-test-{uuid4()}".encode()).hexdigest()
        job = Job(
            content_hash=h,
            title="Saved Job",
            description_md="x",
            requirements_json={},
            source="manual",
        )
        session.add(job)
        await session.commit()
        return job.id


async def _clear_apps() -> None:
    factory = get_session_factory()
    uid = await _uid()
    async with factory() as session:
        await session.execute(delete(Application).where(Application.user_id == uid))
        await session.commit()


@pytest.mark.asyncio
async def test_applications_crud_happy_path(auth_headers, seed_profile):
    await _clear_apps()
    jid = await _seed_job()

    with patch(
        "career_agent.integrations.cognito.CognitoJwtVerifier.verify",
        new=AsyncMock(return_value=FAKE_CLAIMS),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r1 = await client.post(
                "/api/v1/applications",
                json={"job_id": str(jid), "notes": "looks good"},
                headers=auth_headers,
            )
            assert r1.status_code == 201
            app_id = r1.json()["data"]["id"]
            assert r1.json()["data"]["status"] == "saved"

            r2 = await client.put(
                f"/api/v1/applications/{app_id}",
                json={"status": "applied"},
                headers=auth_headers,
            )
            assert r2.status_code == 200
            body = r2.json()["data"]
            assert body["status"] == "applied"
            assert body["applied_at"] is not None

            r3 = await client.get("/api/v1/applications", headers=auth_headers)
            assert r3.status_code == 200
            assert any(a["id"] == app_id for a in r3.json()["data"])

            r4 = await client.delete(f"/api/v1/applications/{app_id}", headers=auth_headers)
            assert r4.status_code == 204


@pytest.mark.asyncio
async def test_applications_unique_on_job_per_user(auth_headers, seed_profile):
    await _clear_apps()
    jid = await _seed_job()

    with patch(
        "career_agent.integrations.cognito.CognitoJwtVerifier.verify",
        new=AsyncMock(return_value=FAKE_CLAIMS),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r1 = await client.post(
                "/api/v1/applications",
                json={"job_id": str(jid)},
                headers=auth_headers,
            )
            assert r1.status_code == 201
            r2 = await client.post(
                "/api/v1/applications",
                json={"job_id": str(jid)},
                headers=auth_headers,
            )
            assert r2.status_code == 409
            assert r2.json()["error"]["code"] == "APPLICATION_ALREADY_EXISTS"


@pytest.mark.asyncio
async def test_applications_survive_expired_trial(auth_headers, seed_profile):
    """Trial-expired users can still CRUD applications (non-paywalled)."""
    from datetime import UTC, datetime, timedelta
    from career_agent.models.subscription import Subscription

    await _clear_apps()
    jid = await _seed_job()

    factory = get_session_factory()
    uid = await _uid()
    async with factory() as session:
        sub = (
            await session.execute(select(Subscription).where(Subscription.user_id == uid))
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
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                resp = await client.post(
                    "/api/v1/applications",
                    json={"job_id": str(jid)},
                    headers=auth_headers,
                )
        assert resp.status_code == 201  # Not 403 — applications are free
    finally:
        async with factory() as session:
            sub = (
                await session.execute(select(Subscription).where(Subscription.user_id == uid))
            ).scalar_one_or_none()
            if sub is not None:
                from datetime import UTC as _UTC, datetime as _dt, timedelta as _td
                sub.trial_ends_at = _dt.now(_UTC) + _td(days=30)
                await session.commit()
```

`backend/tests/integration/test_applications_filters.py`:

```python
import hashlib
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select

from career_agent.db import get_session_factory
from career_agent.main import app
from career_agent.models.application import Application
from career_agent.models.job import Job
from career_agent.models.user import User
from tests.conftest import FAKE_CLAIMS


async def _uid() -> UUID:
    factory = get_session_factory()
    async with factory() as s:
        r = await s.execute(select(User).where(User.cognito_sub == FAKE_CLAIMS["sub"]))
        return r.scalar_one().id


@pytest.mark.asyncio
async def test_applications_status_filter(auth_headers, seed_profile):
    factory = get_session_factory()
    uid = await _uid()

    async with factory() as session:
        await session.execute(delete(Application).where(Application.user_id == uid))
        jobs = []
        for i in range(3):
            h = hashlib.sha256(f"filter-{i}-{uuid4()}".encode()).hexdigest()
            j = Job(
                content_hash=h,
                title=f"Job {i}",
                description_md="x",
                requirements_json={},
                source="manual",
            )
            session.add(j)
            jobs.append(j)
        await session.flush()
        for i, j in enumerate(jobs):
            session.add(
                Application(
                    user_id=uid,
                    job_id=j.id,
                    status="applied" if i == 0 else "saved",
                )
            )
        await session.commit()

    with patch(
        "career_agent.integrations.cognito.CognitoJwtVerifier.verify",
        new=AsyncMock(return_value=FAKE_CLAIMS),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            r = await client.get("/api/v1/applications?status=saved", headers=auth_headers)
    assert r.status_code == 200
    apps = r.json()["data"]
    assert all(a["status"] == "saved" for a in apps)
    assert len(apps) >= 2
```

Run: `uv run pytest tests/integration/test_applications_crud.py tests/integration/test_applications_filters.py -v`
Expected: all tests PASS.

- [ ] **Step 5: Checkpoint**

Checkpoint message: `feat(api): add applications CRUD + filters (non-paywalled)`

---

## Task 25: Onboarding Hook — Seed Default Scan Config

**Files:**
- Modify: `backend/src/career_agent/services/profile.py`
- Create: `backend/tests/integration/test_default_config_seed_onboarding.py`

- [ ] **Step 1: Write the failing test**

`backend/tests/integration/test_default_config_seed_onboarding.py`:

```python
import pytest
from sqlalchemy import delete, select

from career_agent.core.scanner.default_config import DEFAULT_SCAN_CONFIG_NAME
from career_agent.db import get_session_factory
from career_agent.models.profile import Profile
from career_agent.models.scan_config import ScanConfig
from career_agent.models.user import User
from career_agent.schemas.profile import ProfileUpdate
from career_agent.services.profile import update_profile
from tests.conftest import FAKE_CLAIMS


async def _user():
    factory = get_session_factory()
    async with factory() as session:
        r = await session.execute(select(User).where(User.cognito_sub == FAKE_CLAIMS["sub"]))
        return r.scalar_one_or_none()


@pytest.mark.asyncio
async def test_onboarding_done_seeds_default_scan_config():
    user = await _user()
    assert user is not None
    factory = get_session_factory()

    async with factory() as session:
        await session.execute(delete(ScanConfig).where(ScanConfig.user_id == user.id))
        pr = await session.execute(select(Profile).where(Profile.user_id == user.id))
        profile = pr.scalar_one_or_none()
        if profile is None:
            profile = Profile(user_id=user.id, onboarding_state="preferences")
            session.add(profile)
        else:
            profile.onboarding_state = "preferences"
            profile.target_roles = None
            profile.target_locations = None
        profile.master_resume_md = "# resume"
        await session.commit()

    async with factory() as session:
        pr = await session.execute(select(Profile).where(Profile.user_id == user.id))
        profile = pr.scalar_one()
        await update_profile(
            session,
            profile,
            ProfileUpdate(target_roles=["senior engineer"], target_locations=["remote"]),
        )
        await session.commit()

    async with factory() as session:
        configs = (
            await session.execute(
                select(ScanConfig).where(
                    ScanConfig.user_id == user.id,
                    ScanConfig.name == DEFAULT_SCAN_CONFIG_NAME,
                )
            )
        ).scalars().all()
    assert len(configs) == 1
    config = configs[0]
    assert len(config.companies) == 15
    assert config.schedule == "manual"
```

Run: `uv run pytest tests/integration/test_default_config_seed_onboarding.py -v`
Expected: FAIL.

- [ ] **Step 2: Modify `backend/src/career_agent/services/profile.py`**

Find the `_on_onboarding_done` function (added in Phase 2b for `ensure_subscription`) and extend it to also call `seed_default_scan_config`. The updated function:

```python
async def _on_onboarding_done(db: AsyncSession, profile: Profile) -> None:
    """Hook fired when onboarding transitions to 'done'.

    1. Materialize the in-app trial subscription row (Phase 2b).
    2. Seed the default 15-company scan config (Phase 2c). Does NOT auto-run;
       the user must explicitly trigger a scan from the UI or via the agent.
    """
    settings = get_settings()
    await ensure_subscription(db, profile.user_id, settings)

    # Phase 2c: seed default scan config
    from career_agent.core.scanner.default_config import seed_default_scan_config
    await seed_default_scan_config(db, profile.user_id)
```

- [ ] **Step 3: Run the test**

```bash
uv run pytest tests/integration/test_default_config_seed_onboarding.py -v
```

Expected: PASS.

- [ ] **Step 4: Run the existing onboarding test from Phase 2b** to confirm no regression:

```bash
uv run pytest tests/integration/test_trial_start_on_onboarding.py -v
```

Expected: both existing tests still PASS.

- [ ] **Step 5: Checkpoint**

Checkpoint message: `feat(onboarding): seed default scan config on onboarding done transition`

---

## Task 26: Agent Tool Wiring — `start_job_scan` + `start_batch_evaluation`

**Files:**
- Modify: `backend/src/career_agent/core/agent/tools.py`
- Modify: `backend/src/career_agent/core/agent/graph.py`
- Modify: `backend/src/career_agent/core/agent/prompts.py`
- Create: `backend/tests/integration/test_agent_scan_tool.py`
- Create: `backend/tests/integration/test_agent_batch_tool.py`

- [ ] **Step 1: Remove SCAN_JOBS + BATCH_EVAL from NOT_YET_AVAILABLE_TEMPLATES**

In `backend/src/career_agent/core/agent/prompts.py`, update `NOT_YET_AVAILABLE_TEMPLATES` to remove the `SCAN_JOBS` and `BATCH_EVAL` entries. The dict should now only contain `INTERVIEW_PREP` and `NEGOTIATE`:

```python
NOT_YET_AVAILABLE_TEMPLATES: dict[str, str] = {
    "INTERVIEW_PREP": (
        "Interview prep (STAR stories + role-specific questions) is coming soon! "
        "In the meantime, I can evaluate the job and tailor your CV for it."
    ),
    "NEGOTIATE": (
        "Salary negotiation playbooks are coming soon! "
        "Once you have an offer, I'll be able to generate market research and counter-offer scripts."
    ),
}
```

Also update `SYSTEM_PROMPT` in the same file — change the "TWO tools" phrasing to "FOUR tools":

```python
TOOL USAGE:
- You have FOUR tools available: evaluate_job, optimize_cv, start_job_scan, start_batch_evaluation
- Other capabilities (interview prep, negotiation) are coming soon. If the user asks,
  say so briefly and suggest using one of the available tools.
- When calling a tool, briefly tell the user what you're doing
- After a tool returns, summarize the result in 1-2 sentences, then let the
  embedded card speak for itself (the UI renders it automatically)
- Never expose internal IDs or raw JSON in chat text
```

- [ ] **Step 2: Add the two new tools to `backend/src/career_agent/core/agent/tools.py`**

Append to the existing file:

```python
async def start_job_scan_tool(
    runtime: ToolRuntime,
    *,
    scan_config_id: str | None = None,
) -> dict[str, Any]:
    """Start an async scan. If scan_config_id is None, use user's default config."""
    from sqlalchemy import select
    import inngest

    from career_agent.core.scanner.default_config import DEFAULT_SCAN_CONFIG_NAME
    from career_agent.inngest.client import get_inngest_client
    from career_agent.models.scan_config import ScanConfig
    from career_agent.services.scan_run import ScanRunService

    # Resolve the config
    if scan_config_id is not None:
        try:
            cfg_uuid = UUID(scan_config_id)
        except ValueError:
            return {
                "ok": False,
                "error_code": "SCAN_CONFIG_NOT_FOUND",
                "message": "Invalid scan_config_id",
            }
        stmt = select(ScanConfig).where(
            ScanConfig.id == cfg_uuid, ScanConfig.user_id == runtime.user_id
        )
    else:
        stmt = select(ScanConfig).where(
            ScanConfig.user_id == runtime.user_id,
            ScanConfig.name == DEFAULT_SCAN_CONFIG_NAME,
        )
    config = (await runtime.session.execute(stmt)).scalar_one_or_none()
    if config is None:
        return {
            "ok": False,
            "error_code": "SCAN_CONFIG_NOT_FOUND",
            "message": "No scan config found. Complete onboarding to get the default one.",
        }

    runs = ScanRunService(runtime.session)
    scan_run = await runs.create_pending(
        user_id=runtime.user_id, scan_config_id=config.id
    )

    client = get_inngest_client()
    try:
        sent_ids = await client.send(
            inngest.Event(
                name="scan/started",
                data={
                    "scan_config_id": str(config.id),
                    "user_id": str(runtime.user_id),
                    "scan_run_id": str(scan_run.id),
                },
            )
        )
    except Exception as e:
        await runs.mark_failed(scan_run, f"Inngest send failed: {e}")
        return {
            "ok": False,
            "error_code": "INNGEST_UNAVAILABLE",
            "message": "Background worker is unavailable — try again in a moment.",
        }
    if sent_ids:
        scan_run.inngest_event_id = str(sent_ids[0])

    return {
        "ok": True,
        "card": {
            "type": "scan_progress",
            "data": {
                "scan_run_id": str(scan_run.id),
                "scan_name": config.name,
                "status": scan_run.status,
                "companies_count": len(config.companies),
            },
        },
    }


async def start_batch_evaluation_tool(
    runtime: ToolRuntime,
    *,
    scan_run_id: str | None = None,
    job_urls: list[str] | None = None,
    job_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Start an async batch evaluation."""
    import inngest

    from career_agent.core.batch.service import BatchService
    from career_agent.inngest.client import get_inngest_client

    # Validate exactly one input mode provided
    provided = [x is not None for x in (scan_run_id, job_urls, job_ids)]
    if sum(provided) != 1:
        return {
            "ok": False,
            "error_code": "INVALID_BATCH_INPUT",
            "message": "Provide exactly one of scan_run_id, job_urls, or job_ids",
        }

    service = BatchService(runtime.session)
    try:
        if scan_run_id is not None:
            srid = UUID(scan_run_id)
            resolved = await service.resolve_job_ids_from_scan(
                user_id=runtime.user_id, scan_run_id=srid
            )
            source_type = "scan_run_id"
            source_ref = scan_run_id
        elif job_urls is not None:
            resolved = await service.resolve_job_ids_from_urls(
                user_id=runtime.user_id, urls=job_urls
            )
            source_type = "job_urls"
            source_ref = None
        else:
            assert job_ids is not None
            parsed_ids = [UUID(j) for j in job_ids]
            resolved = await service.resolve_job_ids_from_ids(ids=parsed_ids)
            source_type = "job_ids"
            source_ref = None
    except Exception as e:
        return {
            "ok": False,
            "error_code": "INVALID_BATCH_INPUT",
            "message": str(e),
        }

    if not resolved:
        return {
            "ok": False,
            "error_code": "INVALID_BATCH_INPUT",
            "message": "No valid jobs resolved from input",
        }

    run = await service.start_batch(
        user_id=runtime.user_id,
        job_ids=resolved,
        source_type=source_type,
        source_ref=source_ref,
    )

    client = get_inngest_client()
    try:
        sent_ids = await client.send(
            inngest.Event(
                name="batch/started",
                data={"batch_run_id": str(run.id), "user_id": str(runtime.user_id)},
            )
        )
    except Exception:
        return {
            "ok": False,
            "error_code": "INNGEST_UNAVAILABLE",
            "message": "Background worker is unavailable",
        }
    if sent_ids:
        run.inngest_event_id = str(sent_ids[0])

    return {
        "ok": True,
        "card": {
            "type": "batch_progress",
            "data": {
                "batch_run_id": str(run.id),
                "status": run.status,
                "total": run.total_jobs,
                "l0_passed": 0,
                "l1_passed": 0,
                "l2_evaluated": 0,
            },
        },
    }
```

Also add `from uuid import UUID` to the imports at the top of `tools.py` if not already present.

- [ ] **Step 3: Update the agent graph dispatch in `backend/src/career_agent/core/agent/graph.py`**

Extend the tool manifest string and the dispatch in `route_node`:

Update the `tool_manifest` constant:

```python
    tool_manifest = """Available tools (you may call at most ONE):

{"call": "evaluate_job", "args": {"job_url": "..."}} — when the user pastes a URL
{"call": "evaluate_job", "args": {"job_description": "..."}} — when the user pastes raw JD text
{"call": "optimize_cv", "args": {"job_id": "<uuid>"}} — when the user wants a tailored CV for a prior evaluation
{"call": "start_job_scan", "args": {}} — when the user wants to find/discover jobs across their default scan config
{"call": "start_batch_evaluation", "args": {"scan_run_id": "<uuid>"}} — to evaluate all results from a recent scan
{"call": "start_batch_evaluation", "args": {"job_urls": ["https://...", ...]}} — to evaluate a list of URLs
{"call": "start_batch_evaluation", "args": {"job_ids": ["<uuid>", ...]}} — to evaluate existing jobs

If no tool is needed (career_general questions, follow-ups), respond naturally.

To call a tool, reply with EXACTLY this structure and nothing else:
TOOL_CALL: {"call": "...", "args": {...}}

Otherwise, reply normally with conversational text."""
```

In the tool dispatch block (after the `tool_name = call.get("call")` line), add the new cases:

```python
        if tool_name == "evaluate_job":
            tool_result = await evaluate_job_tool(runtime, **args)
        elif tool_name == "optimize_cv":
            tool_result = await optimize_cv_tool(runtime, **args)
        elif tool_name == "start_job_scan":
            tool_result = await start_job_scan_tool(runtime, **args)
        elif tool_name == "start_batch_evaluation":
            tool_result = await start_batch_evaluation_tool(runtime, **args)
        else:
            tool_result = {
                "ok": False,
                "error_code": "UNKNOWN_TOOL",
                "message": f"Tool {tool_name} is not available",
            }
```

Add the new tool imports at the top of `graph.py`:

```python
from career_agent.core.agent.tools import (
    ToolRuntime,
    evaluate_job_tool,
    optimize_cv_tool,
    start_batch_evaluation_tool,
    start_job_scan_tool,
)
```

Update `_summary_for_card` to handle the new card types:

```python
def _summary_for_card(card: dict[str, Any]) -> str:
    if card["type"] == "evaluation":
        d = card["data"]
        return (
            f"I evaluated **{d['job_title']}** at {d.get('company') or 'the company'}. "
            f"Overall grade: **{d['overall_grade']}** ({d['recommendation'].replace('_', ' ')})."
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
    return "Done."
```

- [ ] **Step 4: Write the failing tests**

`backend/tests/integration/test_agent_scan_tool.py`:

```python
from unittest.mock import AsyncMock, patch
from uuid import UUID

import pytest
from sqlalchemy import select

from career_agent.core.agent.tools import ToolRuntime, start_job_scan_tool
from career_agent.core.scanner.default_config import DEFAULT_COMPANIES, DEFAULT_SCAN_CONFIG_NAME
from career_agent.db import get_session_factory
from career_agent.models.scan_config import ScanConfig
from career_agent.models.scan_run import ScanRun
from career_agent.models.user import User
from tests.conftest import FAKE_CLAIMS


class _FakeClient:
    def __init__(self):
        self.sent = []
    async def send(self, event):
        self.sent.append(event)
        return ["evt_tool_1"]


@pytest.mark.asyncio
async def test_start_job_scan_tool_uses_default_config():
    factory = get_session_factory()
    async with factory() as session:
        user = (
            await session.execute(select(User).where(User.cognito_sub == FAKE_CLAIMS["sub"]))
        ).scalar_one()
        # Ensure default config exists
        cfg = (
            await session.execute(
                select(ScanConfig).where(
                    ScanConfig.user_id == user.id,
                    ScanConfig.name == DEFAULT_SCAN_CONFIG_NAME,
                )
            )
        ).scalar_one_or_none()
        if cfg is None:
            cfg = ScanConfig(
                user_id=user.id,
                name=DEFAULT_SCAN_CONFIG_NAME,
                companies=list(DEFAULT_COMPANIES),
                schedule="manual",
                is_active=True,
            )
            session.add(cfg)
            await session.commit()
        uid = user.id

    fake = _FakeClient()
    async with factory() as session:
        with patch("career_agent.inngest.client.get_inngest_client", return_value=fake):
            runtime = ToolRuntime(user_id=uid, session=session)
            result = await start_job_scan_tool(runtime)
            await session.commit()

    assert result["ok"] is True
    assert result["card"]["type"] == "scan_progress"
    assert result["card"]["data"]["companies_count"] == 15
    assert len(fake.sent) == 1
```

`backend/tests/integration/test_agent_batch_tool.py`:

```python
import hashlib
from unittest.mock import patch
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from career_agent.core.agent.tools import ToolRuntime, start_batch_evaluation_tool
from career_agent.db import get_session_factory
from career_agent.models.job import Job
from career_agent.models.user import User
from tests.conftest import FAKE_CLAIMS


class _FakeClient:
    def __init__(self):
        self.sent = []
    async def send(self, event):
        self.sent.append(event)
        return ["evt_batch_tool_1"]


@pytest.mark.asyncio
async def test_start_batch_tool_with_job_ids(seed_profile):
    factory = get_session_factory()
    async with factory() as session:
        user = (
            await session.execute(select(User).where(User.cognito_sub == FAKE_CLAIMS["sub"]))
        ).scalar_one()
        h = hashlib.sha256(f"agent-batch-{uuid4()}".encode()).hexdigest()
        job = Job(
            content_hash=h,
            title="Test Job",
            description_md="x",
            requirements_json={},
            source="manual",
        )
        session.add(job)
        await session.commit()
        uid = user.id
        jid = job.id

    fake = _FakeClient()
    async with factory() as session:
        with patch("career_agent.inngest.client.get_inngest_client", return_value=fake):
            runtime = ToolRuntime(user_id=uid, session=session)
            result = await start_batch_evaluation_tool(runtime, job_ids=[str(jid)])
            await session.commit()

    assert result["ok"] is True
    assert result["card"]["type"] == "batch_progress"
    assert result["card"]["data"]["total"] == 1
    assert len(fake.sent) == 1


@pytest.mark.asyncio
async def test_start_batch_tool_rejects_multiple_inputs(seed_profile):
    factory = get_session_factory()
    async with factory() as session:
        user = (
            await session.execute(select(User).where(User.cognito_sub == FAKE_CLAIMS["sub"]))
        ).scalar_one()
        uid = user.id

    async with factory() as session:
        runtime = ToolRuntime(user_id=uid, session=session)
        result = await start_batch_evaluation_tool(
            runtime, job_ids=["abc"], job_urls=["https://x.com"]
        )
    assert result["ok"] is False
    assert result["error_code"] == "INVALID_BATCH_INPUT"
```

Run: `uv run pytest tests/integration/test_agent_scan_tool.py tests/integration/test_agent_batch_tool.py -v`
Expected: all tests PASS.

- [ ] **Step 5: Run full backend suite + lint + mypy**

```bash
uv run pytest tests/ 2>&1 | tail -5
uv run ruff check src/ 2>&1 | tail -3
uv run mypy src/ 2>&1 | tail -3
```

Expected: all passing + clean.

- [ ] **Step 6: Checkpoint**

Checkpoint message: `feat(agent): wire start_job_scan + start_batch_evaluation tools`

---

## Task 27: Frontend API Client Additions + `usePolling` Hook

**Files:**
- Modify: `user-portal/package.json` — add `@dnd-kit/core` dep (used in T31)
- Modify: `user-portal/src/lib/api.ts` — add scanConfigs, scanRuns, batchRuns, applications
- Create: `user-portal/src/lib/polling.ts` — `usePolling` hook

- [ ] **Step 1: Add dependencies**

Add to `user-portal/package.json` `dependencies`:

```json
"@dnd-kit/core": "^6.1.0",
"@dnd-kit/sortable": "^8.0.0"
```

Run:

```bash
cd user-portal
pnpm install
```

- [ ] **Step 2: Create `user-portal/src/lib/polling.ts`**

```typescript
import { useEffect, useRef, useState } from 'react';

export interface PollingResult<T> {
  data: T | null;
  error: Error | null;
  loading: boolean;
}

/**
 * Poll `fetcher` every `intervalMs` until `shouldStop(latest)` returns true
 * or the component unmounts. Cancels cleanly on unmount.
 */
export function usePolling<T>(
  fetcher: () => Promise<T>,
  intervalMs: number,
  shouldStop: (latest: T) => boolean,
): PollingResult<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [loading, setLoading] = useState(true);
  const cancelledRef = useRef(false);

  useEffect(() => {
    cancelledRef.current = false;
    let timer: number | undefined;

    async function poll(): Promise<void> {
      if (cancelledRef.current) return;
      try {
        const latest = await fetcher();
        if (cancelledRef.current) return;
        setData(latest);
        setError(null);
        setLoading(false);
        if (shouldStop(latest)) return;
      } catch (e) {
        if (!cancelledRef.current) {
          setError(e as Error);
          setLoading(false);
        }
      }
      timer = window.setTimeout(poll, intervalMs);
    }

    poll();
    return () => {
      cancelledRef.current = true;
      if (timer !== undefined) window.clearTimeout(timer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [intervalMs]);

  return { data, error, loading };
}
```

- [ ] **Step 3: Extend `user-portal/src/lib/api.ts`**

Add these types above the `api` export:

```typescript
// ----- Phase 2c types -----

export interface CompanyRef {
  name: string;
  platform: 'greenhouse' | 'ashby' | 'lever';
  board_slug: string;
}

export interface ScanConfig {
  id: string;
  user_id: string;
  name: string;
  companies: CompanyRef[];
  keywords: string[] | null;
  exclude_keywords: string[] | null;
  schedule: 'manual' | 'daily' | 'weekly';
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ScanRun {
  id: string;
  user_id: string;
  scan_config_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  jobs_found: number;
  jobs_new: number;
  truncated: boolean;
  error: string | null;
  started_at: string;
  completed_at: string | null;
}

export interface ScanResult {
  id: string;
  job_id: string;
  relevance_score: number | null;
  is_new: boolean;
  created_at: string;
}

export interface ScanRunDetail {
  scan_run: ScanRun;
  results: ScanResult[];
}

export interface BatchRun {
  id: string;
  user_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  total_jobs: number;
  l0_passed: number;
  l1_passed: number;
  l2_evaluated: number;
  source_type: string;
  source_ref: string | null;
  started_at: string;
  completed_at: string | null;
}

export interface BatchItemsSummary {
  queued: number;
  l0: number;
  l1: number;
  l2: number;
  done: number;
  filtered: number;
}

export interface BatchEvaluationSummary {
  evaluation_id: string;
  job_id: string;
  job_title: string;
  company: string | null;
  overall_grade: string;
  match_score: number;
}

export interface BatchRunDetail {
  batch_run: BatchRun;
  items_summary: BatchItemsSummary;
  top_results: BatchEvaluationSummary[];
}

export interface Application {
  id: string;
  user_id: string;
  job_id: string;
  status: 'saved' | 'applied' | 'interviewing' | 'offered' | 'rejected' | 'withdrawn';
  applied_at: string | null;
  notes: string | null;
  evaluation_id: string | null;
  cv_output_id: string | null;
  negotiation_id: string | null;
  updated_at: string;
}
```

Extend the `api` const with new namespaces (merge — keep existing methods):

```typescript
  // ----- Phase 2c methods -----
  scanConfigs: {
    list: () => request<{ data: ScanConfig[] }>('GET', '/api/v1/scan-configs'),
    create: (body: {
      name: string;
      companies: CompanyRef[];
      keywords?: string[] | null;
      exclude_keywords?: string[] | null;
      schedule?: 'manual' | 'daily' | 'weekly';
    }) => request<{ data: ScanConfig }>('POST', '/api/v1/scan-configs', body),
    get: (id: string) =>
      request<{ data: ScanConfig }>('GET', `/api/v1/scan-configs/${id}`),
    update: (id: string, body: Partial<ScanConfig>) =>
      request<{ data: ScanConfig }>('PUT', `/api/v1/scan-configs/${id}`, body),
    delete: (id: string) => request<void>('DELETE', `/api/v1/scan-configs/${id}`),
    run: (id: string) =>
      request<{ data: { scan_run_id: string; status: string } }>(
        'POST',
        `/api/v1/scan-configs/${id}/run`,
        {},
      ),
  },
  scanRuns: {
    list: (params: { limit?: number; status?: string } = {}) => {
      const qs = new URLSearchParams();
      if (params.limit) qs.set('limit', String(params.limit));
      if (params.status) qs.set('status', params.status);
      return request<{ data: ScanRun[] }>(
        'GET',
        `/api/v1/scan-runs${qs.size ? `?${qs}` : ''}`,
      );
    },
    get: (id: string) =>
      request<{ data: ScanRunDetail }>('GET', `/api/v1/scan-runs/${id}`),
  },
  batchRuns: {
    create: (
      body:
        | { job_urls: string[] }
        | { job_ids: string[] }
        | { scan_run_id: string },
    ) => request<{ data: BatchRun }>('POST', '/api/v1/batch-runs', body),
    list: () => request<{ data: BatchRun[] }>('GET', '/api/v1/batch-runs'),
    get: (id: string) =>
      request<{ data: BatchRunDetail }>('GET', `/api/v1/batch-runs/${id}`),
  },
  applications: {
    list: (params: { status?: string; min_grade?: string } = {}) => {
      const qs = new URLSearchParams();
      if (params.status) qs.set('status', params.status);
      if (params.min_grade) qs.set('min_grade', params.min_grade);
      return request<{ data: Application[] }>(
        'GET',
        `/api/v1/applications${qs.size ? `?${qs}` : ''}`,
      );
    },
    create: (body: {
      job_id: string;
      status?: Application['status'];
      evaluation_id?: string;
      cv_output_id?: string;
      notes?: string;
    }) => request<{ data: Application }>('POST', '/api/v1/applications', body),
    update: (id: string, body: Partial<Application>) =>
      request<{ data: Application }>('PUT', `/api/v1/applications/${id}`, body),
    delete: (id: string) =>
      request<void>('DELETE', `/api/v1/applications/${id}`),
  },
```

- [ ] **Step 4: Type-check**

```bash
cd user-portal
./node_modules/.bin/tsc --noEmit
```

Expected: no errors.

- [ ] **Step 5: Checkpoint**

Checkpoint message: `feat(user-portal): add Phase 2c API client methods + usePolling hook`

---

## Task 28: ScansPage + ScanConfigEditor Modal

**Files:**
- Create: `user-portal/src/pages/ScansPage.tsx`
- Create: `user-portal/src/pages/ScanConfigEditor.tsx`
- Modify: `user-portal/src/App.tsx` — add `/scans` route
- Modify: `user-portal/src/components/layout/AppShell.tsx` — add Scans nav link

- [ ] **Step 1: Create `user-portal/src/pages/ScanConfigEditor.tsx`**

```tsx
import { useState, type FormEvent } from 'react';

import { api, type CompanyRef, type ScanConfig } from '../lib/api';

interface Props {
  existing?: ScanConfig;
  onSave: (config: ScanConfig) => void;
  onCancel: () => void;
}

const PLATFORMS = ['greenhouse', 'ashby', 'lever'] as const;

export default function ScanConfigEditor({ existing, onSave, onCancel }: Props) {
  const [name, setName] = useState(existing?.name ?? '');
  const [companies, setCompanies] = useState<CompanyRef[]>(
    existing?.companies ?? [],
  );
  const [keywordInput, setKeywordInput] = useState(
    (existing?.keywords ?? []).join(', '),
  );
  const [excludeInput, setExcludeInput] = useState(
    (existing?.exclude_keywords ?? []).join(', '),
  );
  const [newCompany, setNewCompany] = useState<CompanyRef>({
    name: '',
    platform: 'greenhouse',
    board_slug: '',
  });
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function addCompany() {
    if (!newCompany.name || !newCompany.board_slug) return;
    setCompanies([...companies, newCompany]);
    setNewCompany({ name: '', platform: 'greenhouse', board_slug: '' });
  }

  function removeCompany(idx: number) {
    setCompanies(companies.filter((_, i) => i !== idx));
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setPending(true);
    setError(null);
    const keywords = keywordInput
      .split(',')
      .map((k) => k.trim())
      .filter(Boolean);
    const exclude_keywords = excludeInput
      .split(',')
      .map((k) => k.trim())
      .filter(Boolean);
    try {
      const payload = {
        name,
        companies,
        keywords: keywords.length ? keywords : null,
        exclude_keywords: exclude_keywords.length ? exclude_keywords : null,
      };
      const resp = existing
        ? await api.scanConfigs.update(existing.id, payload)
        : await api.scanConfigs.create({ ...payload, keywords: keywords.length ? keywords : undefined, exclude_keywords: exclude_keywords.length ? exclude_keywords : undefined });
      onSave(resp.data);
    } catch (err) {
      setError((err as Error).message);
      setPending(false);
    }
  }

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/40 p-4">
      <form
        onSubmit={handleSubmit}
        className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-lg bg-white p-6 shadow-xl"
      >
        <h2 className="text-xl font-semibold">
          {existing ? 'Edit scan config' : 'New scan config'}
        </h2>

        <label className="mt-4 block text-sm font-medium">Name</label>
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
          className="mt-1 w-full rounded border border-[#e3e2e0] px-3 py-2 text-sm"
        />

        <h3 className="mt-6 text-sm font-medium">
          Companies ({companies.length})
        </h3>
        <ul className="mt-2 max-h-48 overflow-y-auto rounded border border-[#e3e2e0] bg-[#fbfbfa] p-2 text-sm">
          {companies.length === 0 && (
            <li className="text-[#787774]">No companies yet — add one below.</li>
          )}
          {companies.map((c, i) => (
            <li key={i} className="flex items-center justify-between py-1">
              <span>
                <strong>{c.name}</strong>{' '}
                <span className="text-[#787774]">
                  ({c.platform}:{c.board_slug})
                </span>
              </span>
              <button
                type="button"
                onClick={() => removeCompany(i)}
                className="text-xs text-[#e03e3e]"
              >
                Remove
              </button>
            </li>
          ))}
        </ul>

        <div className="mt-3 grid grid-cols-3 gap-2">
          <input
            placeholder="Name"
            value={newCompany.name}
            onChange={(e) =>
              setNewCompany({ ...newCompany, name: e.target.value })
            }
            className="rounded border border-[#e3e2e0] px-2 py-1 text-sm"
          />
          <select
            value={newCompany.platform}
            onChange={(e) =>
              setNewCompany({
                ...newCompany,
                platform: e.target.value as CompanyRef['platform'],
              })
            }
            className="rounded border border-[#e3e2e0] px-2 py-1 text-sm"
          >
            {PLATFORMS.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
          <input
            placeholder="board_slug"
            value={newCompany.board_slug}
            onChange={(e) =>
              setNewCompany({ ...newCompany, board_slug: e.target.value })
            }
            className="rounded border border-[#e3e2e0] px-2 py-1 text-sm"
          />
        </div>
        <button
          type="button"
          onClick={addCompany}
          className="mt-2 rounded border border-[#e3e2e0] px-3 py-1 text-xs"
        >
          Add company
        </button>

        <label className="mt-6 block text-sm font-medium">
          Keywords (comma-separated)
        </label>
        <input
          value={keywordInput}
          onChange={(e) => setKeywordInput(e.target.value)}
          className="mt-1 w-full rounded border border-[#e3e2e0] px-3 py-2 text-sm"
        />

        <label className="mt-4 block text-sm font-medium">
          Exclude keywords (comma-separated)
        </label>
        <input
          value={excludeInput}
          onChange={(e) => setExcludeInput(e.target.value)}
          className="mt-1 w-full rounded border border-[#e3e2e0] px-3 py-2 text-sm"
        />

        {error && <p className="mt-4 text-sm text-[#e03e3e]">{error}</p>}

        <div className="mt-6 flex justify-end gap-2">
          <button
            type="button"
            onClick={onCancel}
            className="rounded border border-[#e3e2e0] px-4 py-2 text-sm"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={pending || !name || companies.length === 0}
            className="rounded bg-[#2383e2] px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            {pending ? 'Saving…' : 'Save'}
          </button>
        </div>
      </form>
    </div>
  );
}
```

- [ ] **Step 2: Create `user-portal/src/pages/ScansPage.tsx`**

```tsx
import { useCallback, useEffect, useState } from 'react';

import { AppShell } from '../components/layout/AppShell';
import { api, type ScanConfig, type ScanRun } from '../lib/api';
import ScanConfigEditor from './ScanConfigEditor';

export default function ScansPage() {
  const [configs, setConfigs] = useState<ScanConfig[]>([]);
  const [runs, setRuns] = useState<Record<string, ScanRun>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<ScanConfig | null | 'new'>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const configResp = await api.scanConfigs.list();
      setConfigs(configResp.data);
      const runsResp = await api.scanRuns.list({ limit: 100 });
      const byConfig: Record<string, ScanRun> = {};
      for (const run of runsResp.data) {
        const prev = byConfig[run.scan_config_id];
        if (!prev || new Date(run.started_at) > new Date(prev.started_at)) {
          byConfig[run.scan_config_id] = run;
        }
      }
      setRuns(byConfig);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function runScan(config: ScanConfig) {
    try {
      const resp = await api.scanConfigs.run(config.id);
      window.location.href = `/scans/${resp.data.scan_run_id}`;
    } catch (e) {
      setError((e as Error).message);
    }
  }

  async function deleteConfig(config: ScanConfig) {
    if (!confirm(`Delete "${config.name}"?`)) return;
    try {
      await api.scanConfigs.delete(config.id);
      await load();
    } catch (e) {
      setError((e as Error).message);
    }
  }

  return (
    <AppShell>
      <div className="mx-auto max-w-3xl">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-semibold">Scans</h1>
          <button
            type="button"
            onClick={() => setEditing('new')}
            className="rounded bg-[#2383e2] px-4 py-2 text-sm font-medium text-white"
          >
            New scan config
          </button>
        </div>

        {error && <p className="mt-4 text-sm text-[#e03e3e]">Error: {error}</p>}

        {loading ? (
          <p className="mt-8 text-sm text-[#787774]">Loading…</p>
        ) : configs.length === 0 ? (
          <p className="mt-8 text-sm text-[#787774]">
            No scan configs yet. Complete onboarding to get the default one, or create a new one above.
          </p>
        ) : (
          <ul className="mt-6 space-y-3">
            {configs.map((c) => {
              const run = runs[c.id];
              return (
                <li
                  key={c.id}
                  className="rounded-lg border border-[#e3e2e0] bg-[#fbfbfa] p-4"
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <h3 className="text-base font-semibold">{c.name}</h3>
                      <p className="mt-1 text-xs text-[#787774]">
                        {c.companies.length} companies
                        {c.keywords?.length ? ` · ${c.keywords.length} keywords` : ''}
                      </p>
                      {run && (
                        <p className="mt-1 text-xs text-[#787774]">
                          Last run: {run.status}
                          {run.status === 'completed' &&
                            ` — ${run.jobs_found} jobs (${run.jobs_new} new)`}
                          {' · '}
                          <a
                            href={`/scans/${run.id}`}
                            className="text-[#2383e2]"
                          >
                            View
                          </a>
                        </p>
                      )}
                    </div>
                    <div className="flex gap-2">
                      <button
                        type="button"
                        onClick={() => runScan(c)}
                        className="rounded bg-[#2383e2] px-3 py-1 text-xs text-white"
                      >
                        Run now
                      </button>
                      <button
                        type="button"
                        onClick={() => setEditing(c)}
                        className="rounded border border-[#e3e2e0] px-3 py-1 text-xs"
                      >
                        Edit
                      </button>
                      <button
                        type="button"
                        onClick={() => deleteConfig(c)}
                        className="rounded border border-[#e3e2e0] px-3 py-1 text-xs text-[#e03e3e]"
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </div>

      {editing !== null && (
        <ScanConfigEditor
          existing={editing === 'new' ? undefined : editing}
          onSave={() => {
            setEditing(null);
            load();
          }}
          onCancel={() => setEditing(null)}
        />
      )}
    </AppShell>
  );
}
```

- [ ] **Step 3: Update `user-portal/src/App.tsx`**

Extend `matchRoute`:

```typescript
function matchRoute(pathname: string) {
  if (pathname === '/settings/billing') return 'billing';
  if (pathname === '/billing/success') return 'subscribe-redirect';
  if (pathname === '/billing/cancel') return 'subscribe-redirect';
  if (pathname === '/scans') return 'scans';
  if (pathname.startsWith('/scans/')) return 'scan-detail';
  return 'chat';
}
```

And render:

```tsx
import ScansPage from './pages/ScansPage';
// ...
{route === 'scans' && <ScansPage />}
```

(ScanDetailPage added in T29.)

- [ ] **Step 4: Update `AppShell.tsx`** — add Scans nav link next to Billing:

```tsx
<a href="/scans" className="hover:text-[#37352f]">
  Scans
</a>
<a href="/settings/billing" className="hover:text-[#37352f]">
  Billing
</a>
```

- [ ] **Step 5: Type-check**

```bash
cd user-portal
./node_modules/.bin/tsc --noEmit
```

Expected: no errors.

- [ ] **Step 6: Checkpoint**

Checkpoint message: `feat(user-portal): add ScansPage + ScanConfigEditor modal`

---

## Task 29: ScanDetailPage with Polling

**Files:**
- Create: `user-portal/src/pages/ScanDetailPage.tsx`
- Modify: `user-portal/src/App.tsx` — render ScanDetailPage on `/scans/:id`

- [ ] **Step 1: Create `user-portal/src/pages/ScanDetailPage.tsx`**

```tsx
import { useCallback, useMemo, useState } from 'react';

import { AppShell } from '../components/layout/AppShell';
import { api, type ScanRunDetail } from '../lib/api';
import { usePolling } from '../lib/polling';

export default function ScanDetailPage() {
  const scanRunId = useMemo(() => {
    const parts = window.location.pathname.split('/');
    return parts[parts.length - 1];
  }, []);

  const [batchError, setBatchError] = useState<string | null>(null);
  const [batchPending, setBatchPending] = useState(false);

  const fetcher = useCallback(
    () => api.scanRuns.get(scanRunId).then((r) => r.data),
    [scanRunId],
  );

  const { data, error, loading } = usePolling<ScanRunDetail>(
    fetcher,
    3000,
    (latest) =>
      latest.scan_run.status === 'completed' ||
      latest.scan_run.status === 'failed',
  );

  async function evaluateAll() {
    if (!data) return;
    setBatchPending(true);
    setBatchError(null);
    try {
      const resp = await api.batchRuns.create({ scan_run_id: data.scan_run.id });
      window.location.href = `/`;
      void resp;
    } catch (e) {
      setBatchError((e as Error).message);
      setBatchPending(false);
    }
  }

  if (loading && !data) {
    return (
      <AppShell>
        <p className="text-sm text-[#787774]">Loading scan…</p>
      </AppShell>
    );
  }

  if (error && !data) {
    return (
      <AppShell>
        <p className="text-sm text-[#e03e3e]">Error: {error.message}</p>
      </AppShell>
    );
  }

  if (!data) return null;

  const { scan_run, results } = data;
  const isRunning = scan_run.status === 'pending' || scan_run.status === 'running';

  return (
    <AppShell>
      <div className="mx-auto max-w-3xl">
        <a href="/scans" className="text-sm text-[#2383e2]">
          ← Back to scans
        </a>
        <h1 className="mt-2 text-2xl font-semibold">Scan run</h1>
        <p className="mt-1 text-sm text-[#787774]">
          Status: {scan_run.status}
          {scan_run.status === 'completed' &&
            ` · ${scan_run.jobs_found} jobs (${scan_run.jobs_new} new)`}
          {scan_run.truncated && ' · (truncated at 500)'}
        </p>

        {isRunning && (
          <div className="mt-4 rounded border border-[#e3e2e0] bg-[#fbfbfa] p-4 text-sm">
            Scan in progress — this page refreshes automatically.
          </div>
        )}

        {scan_run.status === 'completed' && (
          <>
            <div className="mt-6 flex items-center justify-between">
              <h2 className="text-lg font-semibold">Top results</h2>
              <button
                type="button"
                onClick={evaluateAll}
                disabled={batchPending || results.length === 0}
                className="rounded bg-[#2383e2] px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
              >
                {batchPending ? 'Starting…' : 'Evaluate all'}
              </button>
            </div>
            {batchError && (
              <p className="mt-2 text-sm text-[#e03e3e]">{batchError}</p>
            )}
            <ul className="mt-3 divide-y divide-[#e3e2e0]">
              {results.length === 0 && (
                <li className="py-4 text-sm text-[#787774]">
                  No results in this scan run.
                </li>
              )}
              {results.map((r) => (
                <li key={r.id} className="flex items-center justify-between py-3">
                  <span className="text-sm">
                    Job <span className="font-mono text-xs">{r.job_id.slice(0, 8)}</span>
                  </span>
                  <span className="text-xs text-[#787774]">
                    Relevance:{' '}
                    <strong>
                      {r.relevance_score === null
                        ? 'n/a'
                        : r.relevance_score.toFixed(2)}
                    </strong>
                    {r.is_new ? ' · new' : ''}
                  </span>
                </li>
              ))}
            </ul>
          </>
        )}

        {scan_run.status === 'failed' && (
          <div className="mt-6 rounded border border-[#e03e3e] bg-[#fdf1f1] p-4 text-sm text-[#e03e3e]">
            Scan failed: {scan_run.error ?? 'Unknown error'}
          </div>
        )}
      </div>
    </AppShell>
  );
}
```

- [ ] **Step 2: Register route in `App.tsx`**

```tsx
import ScanDetailPage from './pages/ScanDetailPage';
// ...
{route === 'scan-detail' && <ScanDetailPage />}
```

- [ ] **Step 3: Type-check**

```bash
cd user-portal
./node_modules/.bin/tsc --noEmit
```

Expected: no errors.

- [ ] **Step 4: Checkpoint**

Checkpoint message: `feat(user-portal): add ScanDetailPage with polling + Evaluate all button`

---

## Task 30: Chat Cards — ScanProgress, ScanResults, BatchProgress

**Files:**
- Create: `user-portal/src/components/chat/cards/ScanProgressCard.tsx`
- Create: `user-portal/src/components/chat/cards/ScanResultsCard.tsx`
- Create: `user-portal/src/components/chat/cards/BatchProgressCard.tsx`
- Modify: `user-portal/src/components/chat/MessageList.tsx` — render new card types

- [ ] **Step 1: Create `ScanProgressCard.tsx`**

```tsx
import { useCallback } from 'react';

import { api, type ScanRunDetail } from '../../../lib/api';
import { usePolling } from '../../../lib/polling';

interface ScanProgressCardData {
  scan_run_id: string;
  scan_name: string;
  status: string;
  companies_count: number;
}

export function ScanProgressCard({ data }: { data: ScanProgressCardData }) {
  const fetcher = useCallback(
    () => api.scanRuns.get(data.scan_run_id).then((r) => r.data),
    [data.scan_run_id],
  );
  const { data: run } = usePolling<ScanRunDetail>(
    fetcher,
    3000,
    (latest) =>
      latest.scan_run.status === 'completed' ||
      latest.scan_run.status === 'failed',
  );

  const live = run ?? null;
  const status = live?.scan_run.status ?? data.status;
  const jobsFound = live?.scan_run.jobs_found ?? 0;
  const jobsNew = live?.scan_run.jobs_new ?? 0;

  const isRunning = status === 'pending' || status === 'running';
  const isCompleted = status === 'completed';
  const isFailed = status === 'failed';

  return (
    <article className="mt-3 rounded-lg border border-[#e3e2e0] bg-white p-4">
      <header>
        <h3 className="text-base font-semibold">Scanning — {data.scan_name}</h3>
        <p className="mt-1 text-xs text-[#787774]">
          {data.companies_count} companies
        </p>
      </header>

      {isRunning && (
        <div className="mt-3 flex items-center gap-3 text-sm">
          <div className="h-2 flex-1 rounded bg-[#f7f6f3]">
            <div className="h-2 w-1/3 animate-pulse rounded bg-[#2383e2]" />
          </div>
          <span className="text-[#787774]">Scraping…</span>
        </div>
      )}

      {isCompleted && (
        <div className="mt-3">
          <p className="text-sm">
            Found <strong>{jobsFound}</strong> jobs ({jobsNew} new).
          </p>
          <a
            href={`/scans/${data.scan_run_id}`}
            className="mt-2 inline-block rounded bg-[#2383e2] px-3 py-1 text-xs text-white"
          >
            View results
          </a>
        </div>
      )}

      {isFailed && (
        <p className="mt-3 text-sm text-[#e03e3e]">
          Scan failed. {live?.scan_run.error ?? ''}
        </p>
      )}
    </article>
  );
}
```

- [ ] **Step 2: Create `ScanResultsCard.tsx`**

```tsx
interface ScanResultsCardData {
  scan_run_id: string;
  scan_name: string;
  scanned_count: number;
  new_count: number;
  top_jobs: Array<{
    job_id: string;
    title: string;
    company: string;
    location: string;
    salary_range: string | null;
    grade?: string;
    match_score?: number;
  }>;
}

export function ScanResultsCard({ data }: { data: ScanResultsCardData }) {
  return (
    <article className="mt-3 rounded-lg border border-[#e3e2e0] bg-white p-4">
      <header>
        <h3 className="text-base font-semibold">Scan results — {data.scan_name}</h3>
        <p className="mt-1 text-xs text-[#787774]">
          {data.scanned_count} jobs scanned · {data.new_count} new
        </p>
      </header>

      <ul className="mt-3 divide-y divide-[#e3e2e0]">
        {data.top_jobs.slice(0, 5).map((j) => (
          <li key={j.job_id} className="flex items-center justify-between py-2 text-sm">
            <div>
              <strong>{j.title}</strong>{' '}
              <span className="text-[#787774]">@ {j.company}</span>
              <div className="text-xs text-[#787774]">
                {j.location} {j.salary_range ? `· ${j.salary_range}` : ''}
              </div>
            </div>
          </li>
        ))}
      </ul>

      <footer className="mt-3 flex gap-2">
        <a
          href={`/scans/${data.scan_run_id}`}
          className="rounded border border-[#e3e2e0] px-3 py-1 text-xs"
        >
          View all
        </a>
      </footer>
    </article>
  );
}
```

- [ ] **Step 3: Create `BatchProgressCard.tsx`**

```tsx
import { useCallback } from 'react';

import { api, type BatchRunDetail } from '../../../lib/api';
import { usePolling } from '../../../lib/polling';

interface BatchProgressCardData {
  batch_run_id: string;
  status: string;
  total: number;
  l0_passed: number;
  l1_passed: number;
  l2_evaluated: number;
}

const GRADE_COLOR: Record<string, string> = {
  A: 'bg-[#35a849] text-white',
  'A-': 'bg-[#35a849] text-white',
  'B+': 'bg-[#2383e2] text-white',
  B: 'bg-[#2383e2] text-white',
  'B-': 'bg-[#2383e2] text-white',
  'C+': 'bg-[#cb912f] text-white',
  C: 'bg-[#cb912f] text-white',
  D: 'bg-[#e03e3e] text-white',
  F: 'bg-[#e03e3e] text-white',
};

export function BatchProgressCard({ data }: { data: BatchProgressCardData }) {
  const fetcher = useCallback(
    () => api.batchRuns.get(data.batch_run_id).then((r) => r.data),
    [data.batch_run_id],
  );
  const { data: live } = usePolling<BatchRunDetail>(
    fetcher,
    3000,
    (latest) =>
      latest.batch_run.status === 'completed' ||
      latest.batch_run.status === 'failed',
  );

  const run = live?.batch_run;
  const summary = live?.items_summary;
  const top = live?.top_results ?? [];
  const status = run?.status ?? data.status;
  const total = run?.total_jobs ?? data.total;
  const l0 = run?.l0_passed ?? data.l0_passed;
  const l1 = run?.l1_passed ?? data.l1_passed;
  const l2 = run?.l2_evaluated ?? data.l2_evaluated;

  return (
    <article className="mt-3 rounded-lg border border-[#e3e2e0] bg-white p-4">
      <header>
        <h3 className="text-base font-semibold">Batch evaluation</h3>
        <p className="mt-1 text-xs text-[#787774]">
          {total} jobs · status: {status}
        </p>
      </header>

      <div className="mt-3 grid grid-cols-4 gap-2 text-center text-xs">
        <div className="rounded bg-[#fbfbfa] p-2">
          <div className="text-[#787774]">Total</div>
          <div className="text-lg font-semibold">{total}</div>
        </div>
        <div className="rounded bg-[#fbfbfa] p-2">
          <div className="text-[#787774]">L0</div>
          <div className="text-lg font-semibold">{l0}</div>
        </div>
        <div className="rounded bg-[#fbfbfa] p-2">
          <div className="text-[#787774]">L1</div>
          <div className="text-lg font-semibold">{l1}</div>
        </div>
        <div className="rounded bg-[#fbfbfa] p-2">
          <div className="text-[#787774]">L2</div>
          <div className="text-lg font-semibold">{l2}</div>
        </div>
      </div>

      {summary && (
        <p className="mt-2 text-xs text-[#787774]">
          Filtered: {summary.filtered} · Done: {summary.done}
        </p>
      )}

      {status === 'completed' && top.length > 0 && (
        <>
          <h4 className="mt-4 text-sm font-medium">Top matches</h4>
          <ul className="mt-2 divide-y divide-[#e3e2e0]">
            {top.map((t) => (
              <li
                key={t.evaluation_id}
                className="flex items-center justify-between py-2 text-sm"
              >
                <div>
                  <strong>{t.job_title}</strong>{' '}
                  <span className="text-[#787774]">@ {t.company ?? '?'}</span>
                </div>
                <span
                  className={`rounded px-2 py-0.5 text-xs font-semibold ${
                    GRADE_COLOR[t.overall_grade] ?? 'bg-[#787774] text-white'
                  }`}
                >
                  {t.overall_grade}
                </span>
              </li>
            ))}
          </ul>
        </>
      )}

      {status === 'failed' && (
        <p className="mt-3 text-sm text-[#e03e3e]">Batch failed.</p>
      )}
    </article>
  );
}
```

- [ ] **Step 4: Update `MessageList.tsx` to render the new card types**

In `user-portal/src/components/chat/MessageList.tsx`, import the new cards and extend the card-type switch:

```tsx
import { BatchProgressCard } from './cards/BatchProgressCard';
import { ScanProgressCard } from './cards/ScanProgressCard';
import { ScanResultsCard } from './cards/ScanResultsCard';
```

In the card rendering logic (where `EvaluationCard` and `CvOutputCard` are dispatched), add three more branches:

```tsx
card.type === 'scan_progress' ? (
  <ScanProgressCard key={idx} data={card.data as any} />
) : card.type === 'scan_results' ? (
  <ScanResultsCard key={idx} data={card.data as any} />
) : card.type === 'batch_progress' ? (
  <BatchProgressCard key={idx} data={card.data as any} />
) : null,
```

Chain these with the existing `EvaluationCard` / `CvOutputCard` ternaries so all 5 card types are handled.

- [ ] **Step 5: Type-check**

```bash
cd user-portal
./node_modules/.bin/tsc --noEmit
```

Expected: no errors.

- [ ] **Step 6: Checkpoint**

Checkpoint message: `feat(user-portal): add scan + batch progress/results chat cards`

---

## Task 31: Pipeline Kanban Page

**Files:**
- Create: `user-portal/src/pages/PipelinePage.tsx`
- Create: `user-portal/src/components/pipeline/KanbanColumn.tsx`
- Create: `user-portal/src/components/pipeline/ApplicationCard.tsx`
- Create: `user-portal/src/components/pipeline/PipelineFilters.tsx`
- Modify: `user-portal/src/App.tsx` — `/pipeline` route
- Modify: `user-portal/src/components/layout/AppShell.tsx` — Pipeline nav link

- [ ] **Step 1: Create `user-portal/src/components/pipeline/ApplicationCard.tsx`**

```tsx
import { type Application } from '../../lib/api';

interface Props {
  application: Application;
  jobTitle?: string;
  company?: string;
  grade?: string;
}

export function ApplicationCard({ application, jobTitle, company, grade }: Props) {
  return (
    <div className="rounded border border-[#e3e2e0] bg-white p-3 text-sm shadow-sm">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="truncate font-medium">{jobTitle ?? 'Job'}</div>
          {company && (
            <div className="truncate text-xs text-[#787774]">{company}</div>
          )}
        </div>
        {grade && (
          <span className="rounded bg-[#f7f6f3] px-2 py-0.5 text-xs font-semibold">
            {grade}
          </span>
        )}
      </div>
      {application.notes && (
        <p className="mt-2 line-clamp-2 text-xs text-[#787774]">{application.notes}</p>
      )}
      <div className="mt-2 text-xs text-[#787774]">
        Updated {new Date(application.updated_at).toLocaleDateString()}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Create `user-portal/src/components/pipeline/KanbanColumn.tsx`**

```tsx
import { useDroppable } from '@dnd-kit/core';

import { type Application } from '../../lib/api';
import { ApplicationCard } from './ApplicationCard';
import { useDraggable } from '@dnd-kit/core';

interface Props {
  title: string;
  status: Application['status'];
  applications: Application[];
  metaByJob: Record<string, { title: string; company: string | null; grade?: string }>;
}

function DraggableApplicationCard({
  application,
  meta,
}: {
  application: Application;
  meta: { title: string; company: string | null; grade?: string };
}) {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id: application.id,
  });
  const style = transform
    ? { transform: `translate3d(${transform.x}px, ${transform.y}px, 0)` }
    : undefined;
  return (
    <div
      ref={setNodeRef}
      style={style}
      className={isDragging ? 'cursor-grabbing opacity-60' : 'cursor-grab'}
      {...listeners}
      {...attributes}
    >
      <ApplicationCard
        application={application}
        jobTitle={meta.title}
        company={meta.company ?? undefined}
        grade={meta.grade}
      />
    </div>
  );
}

export function KanbanColumn({ title, status, applications, metaByJob }: Props) {
  const { setNodeRef, isOver } = useDroppable({ id: status });
  return (
    <div
      ref={setNodeRef}
      className={`flex w-64 flex-shrink-0 flex-col rounded-lg border ${
        isOver ? 'border-[#2383e2] bg-[#f0f7ff]' : 'border-[#e3e2e0] bg-[#fbfbfa]'
      } p-3`}
    >
      <header className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold">{title}</h3>
        <span className="text-xs text-[#787774]">{applications.length}</span>
      </header>
      <div className="flex flex-col gap-2">
        {applications.map((a) => (
          <DraggableApplicationCard
            key={a.id}
            application={a}
            meta={metaByJob[a.job_id] ?? { title: 'Job', company: null }}
          />
        ))}
        {applications.length === 0 && (
          <p className="text-xs text-[#787774]">Empty</p>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Create `user-portal/src/components/pipeline/PipelineFilters.tsx`**

```tsx
interface Props {
  minGrade: string;
  onMinGradeChange: (grade: string) => void;
}

const GRADES = ['', 'B-', 'B', 'B+', 'A-', 'A'];

export function PipelineFilters({ minGrade, onMinGradeChange }: Props) {
  return (
    <div className="flex items-center gap-3 text-sm">
      <label>
        Min grade:{' '}
        <select
          value={minGrade}
          onChange={(e) => onMinGradeChange(e.target.value)}
          className="rounded border border-[#e3e2e0] px-2 py-1"
        >
          {GRADES.map((g) => (
            <option key={g} value={g}>
              {g || 'any'}
            </option>
          ))}
        </select>
      </label>
    </div>
  );
}
```

- [ ] **Step 4: Create `user-portal/src/pages/PipelinePage.tsx`**

```tsx
import { useCallback, useEffect, useState } from 'react';
import { DndContext, type DragEndEvent } from '@dnd-kit/core';

import { AppShell } from '../components/layout/AppShell';
import { ApplicationCard } from '../components/pipeline/ApplicationCard';
import { KanbanColumn } from '../components/pipeline/KanbanColumn';
import { PipelineFilters } from '../components/pipeline/PipelineFilters';
import { api, type Application } from '../lib/api';

const COLUMNS: Array<{ status: Application['status']; title: string }> = [
  { status: 'saved', title: 'Saved' },
  { status: 'applied', title: 'Applied' },
  { status: 'interviewing', title: 'Interviewing' },
  { status: 'offered', title: 'Offered' },
  { status: 'rejected', title: 'Rejected' },
  { status: 'withdrawn', title: 'Withdrawn' },
];

export default function PipelinePage() {
  const [apps, setApps] = useState<Application[]>([]);
  const [minGrade, setMinGrade] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [metaByJob, setMetaByJob] = useState<
    Record<string, { title: string; company: string | null; grade?: string }>
  >({});

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const resp = await api.applications.list(
        minGrade ? { min_grade: minGrade } : {},
      );
      setApps(resp.data);
      // For Phase 2c we leave metaByJob empty; ApplicationCard falls back to
      // rendering "Job" as a placeholder. A bulk GET /jobs endpoint would let
      // us resolve titles + companies + grades here — that's a separate,
      // focused enhancement and not part of 2c's critical path.
      setMetaByJob({});
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [minGrade]);

  useEffect(() => {
    load();
  }, [load]);

  const handleDragEnd = async (event: DragEndEvent) => {
    const appId = String(event.active.id);
    const newStatus = event.over?.id as Application['status'] | undefined;
    if (!newStatus) return;
    const app = apps.find((a) => a.id === appId);
    if (!app || app.status === newStatus) return;

    // Optimistic update
    const prev = apps;
    setApps(apps.map((a) => (a.id === appId ? { ...a, status: newStatus } : a)));
    try {
      await api.applications.update(appId, { status: newStatus });
    } catch (e) {
      // Rollback
      setApps(prev);
      setError((e as Error).message);
    }
  };

  return (
    <AppShell>
      <div className="max-w-full">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-semibold">Pipeline</h1>
          <PipelineFilters minGrade={minGrade} onMinGradeChange={setMinGrade} />
        </div>

        {error && <p className="mt-4 text-sm text-[#e03e3e]">Error: {error}</p>}
        {loading && <p className="mt-4 text-sm text-[#787774]">Loading…</p>}

        <DndContext onDragEnd={handleDragEnd}>
          <div className="mt-6 flex gap-4 overflow-x-auto pb-4">
            {COLUMNS.map((col) => (
              <KanbanColumn
                key={col.status}
                status={col.status}
                title={col.title}
                applications={apps.filter((a) => a.status === col.status)}
                metaByJob={metaByJob}
              />
            ))}
          </div>
        </DndContext>
      </div>
    </AppShell>
  );
}
```

- [ ] **Step 5: Register route in `App.tsx`** and add nav link in `AppShell.tsx`

App.tsx:

```tsx
import PipelinePage from './pages/PipelinePage';
// ...

function matchRoute(pathname: string) {
  // existing routes
  if (pathname === '/pipeline') return 'pipeline';
  // ...
}

// in render:
{route === 'pipeline' && <PipelinePage />}
```

AppShell.tsx — add nav link before Scans:

```tsx
<a href="/pipeline" className="hover:text-[#37352f]">
  Pipeline
</a>
```

- [ ] **Step 6: Type-check + smoke run**

```bash
cd user-portal
./node_modules/.bin/tsc --noEmit
pnpm run dev
# visit http://localhost:5173/pipeline manually, confirm empty kanban renders
# Ctrl-C to stop
```

Expected: no type errors, empty 6-column kanban renders.

- [ ] **Step 7: Checkpoint**

Checkpoint message: `feat(user-portal): add PipelinePage kanban with drag-and-drop`

---

## Task 32: Frontend Tests for Phase 2c Components

**Files:**
- Create: `user-portal/src/pages/ScansPage.test.tsx`
- Create: `user-portal/src/pages/ScanDetailPage.test.tsx`
- Create: `user-portal/src/pages/PipelinePage.test.tsx`
- Create: `user-portal/src/components/chat/cards/BatchProgressCard.test.tsx`
- Create: `user-portal/src/components/chat/cards/ScanProgressCard.test.tsx`
- Create: `user-portal/src/components/chat/cards/ScanResultsCard.test.tsx`
- Create: `user-portal/src/components/pipeline/PipelineFilters.test.tsx`

- [ ] **Step 1: Create `ScansPage.test.tsx`**

```tsx
import { render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import ScansPage from './ScansPage';

const fetchMock = vi.fn();

beforeEach(() => {
  fetchMock.mockReset();
  vi.stubGlobal('fetch', fetchMock);
});

function mockJson(body: unknown, status = 200) {
  return { ok: status < 400, status, json: async () => body };
}

describe('ScansPage', () => {
  it('renders the list of scan configs from mocked API', async () => {
    fetchMock
      .mockResolvedValueOnce(
        mockJson({
          data: [
            {
              id: 'cfg-1',
              user_id: 'u-1',
              name: 'My custom scan',
              companies: [
                { name: 'Stripe', platform: 'greenhouse', board_slug: 'stripe' },
              ],
              keywords: null,
              exclude_keywords: null,
              schedule: 'manual',
              is_active: true,
              created_at: new Date().toISOString(),
              updated_at: new Date().toISOString(),
            },
          ],
        }),
      )
      .mockResolvedValueOnce(mockJson({ data: [] }));

    render(<ScansPage />);
    await waitFor(() => {
      expect(screen.getByText('My custom scan')).toBeInTheDocument();
    });
    expect(screen.getByRole('button', { name: /run now/i })).toBeInTheDocument();
  });

  it('shows empty state when no configs', async () => {
    fetchMock
      .mockResolvedValueOnce(mockJson({ data: [] }))
      .mockResolvedValueOnce(mockJson({ data: [] }));
    render(<ScansPage />);
    await waitFor(() => {
      expect(screen.getByText(/no scan configs yet/i)).toBeInTheDocument();
    });
  });
});
```

- [ ] **Step 2: Create `ScanDetailPage.test.tsx`**

```tsx
import { render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import ScanDetailPage from './ScanDetailPage';

const fetchMock = vi.fn();

beforeEach(() => {
  fetchMock.mockReset();
  vi.stubGlobal('fetch', fetchMock);
  Object.defineProperty(window, 'location', {
    value: { pathname: '/scans/run-abc', href: '' },
    writable: true,
  });
});

function mockJson(body: unknown, status = 200) {
  return { ok: status < 400, status, json: async () => body };
}

describe('ScanDetailPage', () => {
  it('renders completed scan results', async () => {
    fetchMock.mockResolvedValue(
      mockJson({
        data: {
          scan_run: {
            id: 'run-abc',
            user_id: 'u-1',
            scan_config_id: 'cfg-1',
            status: 'completed',
            jobs_found: 12,
            jobs_new: 7,
            truncated: false,
            error: null,
            started_at: new Date().toISOString(),
            completed_at: new Date().toISOString(),
          },
          results: [
            {
              id: 'r-1',
              job_id: 'job-aaaaaaaa',
              relevance_score: 0.82,
              is_new: true,
              created_at: new Date().toISOString(),
            },
          ],
        },
      }),
    );

    render(<ScanDetailPage />);
    await waitFor(() => {
      expect(screen.getByText(/12 jobs/)).toBeInTheDocument();
    });
    expect(screen.getByText(/top results/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /evaluate all/i })).toBeInTheDocument();
  });
});
```

- [ ] **Step 3: Create `PipelinePage.test.tsx`**

```tsx
import { render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import PipelinePage from './PipelinePage';

const fetchMock = vi.fn();

beforeEach(() => {
  fetchMock.mockReset();
  vi.stubGlobal('fetch', fetchMock);
});

function mockJson(body: unknown, status = 200) {
  return { ok: status < 400, status, json: async () => body };
}

describe('PipelinePage', () => {
  it('renders 6 kanban columns', async () => {
    fetchMock.mockResolvedValue(mockJson({ data: [] }));
    render(<PipelinePage />);
    await waitFor(() => {
      expect(screen.getByText('Saved')).toBeInTheDocument();
    });
    for (const title of ['Saved', 'Applied', 'Interviewing', 'Offered', 'Rejected', 'Withdrawn']) {
      expect(screen.getByText(title)).toBeInTheDocument();
    }
  });
});
```

- [ ] **Step 4: Create the 3 chat card tests + 1 filter test**

`BatchProgressCard.test.tsx`:

```tsx
import { render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { BatchProgressCard } from './BatchProgressCard';

const fetchMock = vi.fn();

beforeEach(() => {
  fetchMock.mockReset();
  vi.stubGlobal('fetch', fetchMock);
});

function mockJson(body: unknown, status = 200) {
  return { ok: status < 400, status, json: async () => body };
}

describe('BatchProgressCard', () => {
  it('renders initial counters from props before polling resolves', () => {
    fetchMock.mockImplementation(() => new Promise(() => {})); // never resolves
    render(
      <BatchProgressCard
        data={{
          batch_run_id: 'b-1',
          status: 'pending',
          total: 20,
          l0_passed: 0,
          l1_passed: 0,
          l2_evaluated: 0,
        }}
      />,
    );
    expect(screen.getByText('Batch evaluation')).toBeInTheDocument();
    expect(screen.getByText('20')).toBeInTheDocument();
  });

  it('renders top results when polling returns completed', async () => {
    fetchMock.mockResolvedValue(
      mockJson({
        data: {
          batch_run: {
            id: 'b-1',
            user_id: 'u-1',
            status: 'completed',
            total_jobs: 20,
            l0_passed: 15,
            l1_passed: 8,
            l2_evaluated: 5,
            source_type: 'scan_run_id',
            source_ref: 'run-1',
            started_at: new Date().toISOString(),
            completed_at: new Date().toISOString(),
          },
          items_summary: {
            queued: 0, l0: 0, l1: 0, l2: 0, done: 5, filtered: 15,
          },
          top_results: [
            {
              evaluation_id: 'e-1',
              job_id: 'j-1',
              job_title: 'Staff Engineer',
              company: 'Acme',
              overall_grade: 'A-',
              match_score: 0.88,
            },
          ],
        },
      }),
    );
    render(
      <BatchProgressCard
        data={{
          batch_run_id: 'b-1',
          status: 'pending',
          total: 20,
          l0_passed: 0,
          l1_passed: 0,
          l2_evaluated: 0,
        }}
      />,
    );
    await waitFor(() => {
      expect(screen.getByText('Staff Engineer')).toBeInTheDocument();
    });
    expect(screen.getByText('A-')).toBeInTheDocument();
  });
});
```

`ScanProgressCard.test.tsx`:

```tsx
import { render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ScanProgressCard } from './ScanProgressCard';

const fetchMock = vi.fn();

beforeEach(() => {
  fetchMock.mockReset();
  vi.stubGlobal('fetch', fetchMock);
});

function mockJson(body: unknown, status = 200) {
  return { ok: status < 400, status, json: async () => body };
}

describe('ScanProgressCard', () => {
  it('shows completed results once polling finishes', async () => {
    fetchMock.mockResolvedValue(
      mockJson({
        data: {
          scan_run: {
            id: 'run-1',
            user_id: 'u-1',
            scan_config_id: 'cfg-1',
            status: 'completed',
            jobs_found: 7,
            jobs_new: 4,
            truncated: false,
            error: null,
            started_at: new Date().toISOString(),
            completed_at: new Date().toISOString(),
          },
          results: [],
        },
      }),
    );

    render(
      <ScanProgressCard
        data={{
          scan_run_id: 'run-1',
          scan_name: 'AI companies',
          status: 'pending',
          companies_count: 15,
        }}
      />,
    );
    await waitFor(() => {
      expect(screen.getByText(/Found/i)).toBeInTheDocument();
    });
    expect(screen.getByText(/7/)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /view results/i })).toBeInTheDocument();
  });
});
```

`ScanResultsCard.test.tsx`:

```tsx
import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { ScanResultsCard } from './ScanResultsCard';

describe('ScanResultsCard', () => {
  it('renders top jobs and counts', () => {
    render(
      <ScanResultsCard
        data={{
          scan_run_id: 'run-1',
          scan_name: 'AI',
          scanned_count: 20,
          new_count: 8,
          top_jobs: [
            {
              job_id: 'j-1',
              title: 'Senior Engineer',
              company: 'Anthropic',
              location: 'Remote',
              salary_range: '$200K–$280K',
            },
          ],
        }}
      />,
    );
    expect(screen.getByText(/Scan results — AI/)).toBeInTheDocument();
    expect(screen.getByText(/20 jobs scanned · 8 new/)).toBeInTheDocument();
    expect(screen.getByText('Senior Engineer')).toBeInTheDocument();
  });
});
```

`PipelineFilters.test.tsx`:

```tsx
import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { PipelineFilters } from './PipelineFilters';

describe('PipelineFilters', () => {
  it('calls onMinGradeChange when selection changes', () => {
    const onChange = vi.fn();
    render(<PipelineFilters minGrade="" onMinGradeChange={onChange} />);
    fireEvent.change(screen.getByLabelText(/min grade/i), { target: { value: 'B+' } });
    expect(onChange).toHaveBeenCalledWith('B+');
  });
});
```

- [ ] **Step 5: Run the full frontend test suite**

```bash
cd user-portal
./node_modules/.bin/vitest run 2>&1 | tail -20
```

Expected: all frontend tests PASS (baseline 9 + ~9 new ≈ 18 tests).

- [ ] **Step 6: Checkpoint**

Checkpoint message: `test(user-portal): add Phase 2c component tests`

---

## Task 33: End-to-End Smoke Test — Scan → Batch → Pipeline

**Files:**
- Create: `backend/tests/integration/test_phase2c_smoke.py`

- [ ] **Step 1: Create the smoke test**

```python
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
from pathlib import Path
from unittest.mock import AsyncMock, patch
from uuid import UUID

import pytest
import respx
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy import delete, select

from career_agent.core.batch.service import BatchService
from career_agent.core.scanner.default_config import seed_default_scan_config
from career_agent.core.scanner.service import ScannerService
from career_agent.db import get_session_factory
from career_agent.main import app
from career_agent.models.application import Application
from career_agent.models.batch_run import BatchRun
from career_agent.models.evaluation import Evaluation
from career_agent.models.job import Job
from career_agent.models.scan_config import ScanConfig
from career_agent.models.scan_run import ScanRun
from career_agent.models.user import User
from tests.conftest import FAKE_CLAIMS
from tests.fixtures.fake_anthropic import fake_anthropic
from tests.fixtures.fake_gemini import fake_gemini

_GH = json.loads(
    (Path(__file__).parent.parent / "fixtures" / "boards" / "greenhouse" / "stripe.json").read_text()
)
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
    # Stub ashby and lever for all slugs to empty arrays so default config's
    # other 14 companies don't break the test.
    import re
    respx.get(re.compile(r"https://api\.ashbyhq\.com/posting-api/job-board/.*")).mock(
        return_value=Response(200, json={"jobs": []})
    )
    respx.get(re.compile(r"https://api\.lever\.co/v0/postings/.*")).mock(
        return_value=Response(200, json=[])
    )
    # Stub greenhouse for non-stripe slugs too
    respx.get(
        re.compile(r"https://boards-api\.greenhouse\.io/v1/boards/(?!stripe).*")
    ).mock(return_value=Response(200, json={"jobs": []}))

    user_id = await _get_user_id()
    await _reset_user_scan_state(user_id)

    factory = get_session_factory()

    # ------------ 1. Seed default scan config ------------
    async with factory() as session:
        await seed_default_scan_config(session, user_id)
        await session.commit()

    # Confirm the config exists
    async with factory() as session:
        configs = (
            await session.execute(select(ScanConfig).where(ScanConfig.user_id == user_id))
        ).scalars().all()
        assert len(configs) == 1
        config = configs[0]
        assert len(config.companies) == 15
        config_id = config.id

    # ------------ 2. Run a scan via ScannerService ------------
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

    # ------------ 3. Assert scan_results populated ------------
    async with factory() as session:
        reloaded = (
            await session.execute(select(ScanRun).where(ScanRun.id == scan_run_id))
        ).scalar_one()
        assert reloaded.status == "completed"

    # ------------ 4. Start batch from scan run ------------
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

    # ------------ 5. Run the funnel (L0 → L1 → L2) ------------
    with fake_gemini({"Senior": "0.75", "Staff": "0.8"}), fake_anthropic({"USER PROFILE": _CLAUDE}):
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

    # ------------ 6. POST /applications from the first evaluation ------------
    with patch(
        "career_agent.integrations.cognito.CognitoJwtVerifier.verify",
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

            # ------------ 7. PUT status=applied ------------
            r_update = await client.put(
                f"/api/v1/applications/{app_id}",
                json={"status": "applied"},
                headers=auth_headers,
            )
            assert r_update.status_code == 200
            assert r_update.json()["data"]["status"] == "applied"
            assert r_update.json()["data"]["applied_at"] is not None

            # ------------ 8. GET /applications?status=applied ------------
            r_list = await client.get(
                "/api/v1/applications?status=applied",
                headers=auth_headers,
            )
            assert r_list.status_code == 200
            ids = [a["id"] for a in r_list.json()["data"]]
            assert app_id in ids
```

- [ ] **Step 2: Run the smoke test**

```bash
uv run pytest tests/integration/test_phase2c_smoke.py -v
```

Expected: PASS.

- [ ] **Step 3: Run the full backend suite**

```bash
uv run pytest tests/ 2>&1 | tail -5
```

Expected: all tests pass. Roughly 134+ total (99 baseline + ~35 new Phase 2c tests).

- [ ] **Step 4: Checkpoint**

Checkpoint message: `test(phase2c): add end-to-end smoke test scan → batch → pipeline`

---

## Task 34: Phase 2c Completion Verification

**Files:**
- None (this task is a checklist)

- [ ] **Step 1: Run the full backend test suite**

```bash
cd backend
uv run pytest tests/ -v 2>&1 | tail -20
```

Expected: all tests PASS (~134+).

- [ ] **Step 2: Run lint + black + mypy on backend**

```bash
cd backend
uv run ruff check src/ 2>&1 | tail -3
uv run black --check src/ 2>&1 | tail -3
uv run mypy src/ 2>&1 | tail -3
```

Expected: `All checks passed!`, `X files would be left unchanged`, `Success: no issues found`.

- [ ] **Step 3: Run the pdf-render tests**

```bash
cd ../pdf-render
./node_modules/.bin/vitest run 2>&1 | tail -10
```

Expected: 4 tests PASS (unchanged baseline).

- [ ] **Step 4: Run the user-portal tests + type check**

```bash
cd ../user-portal
./node_modules/.bin/vitest run 2>&1 | tail -15
./node_modules/.bin/tsc --noEmit 2>&1 | tail -5
```

Expected: ~18 tests PASS, no type errors.

- [ ] **Step 5: Bring up docker-compose and smoke the new endpoints manually**

```bash
cd ..
docker-compose up -d
cd backend
uv run alembic upgrade head
uv run uvicorn career_agent.main:app --reload
```

In another terminal:

```bash
# All should 401 (auth required) but NOT 404 — confirms routes are registered:
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/api/v1/scan-configs
curl -s -o /dev/null -w "%{http_code}\n" -X POST http://localhost:8000/api/v1/batch-runs
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/api/v1/applications
# Inngest serve endpoint should respond (200/201/405 depending on SDK):
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/api/v1/inngest
```

Expected: `401, 401, 401, 200/201/405`.

Visit `http://localhost:8288` in a browser — Inngest dev server dashboard should show both `scan-boards` and `batch-evaluate` functions registered.

- [ ] **Step 6: (Optional) Real end-to-end dogfood pass**

With real `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`, and Inngest dev server running:

1. Log in to user-portal → complete onboarding (default config auto-seeds).
2. Open chat, say *"scan for jobs"*. Watch `ScanProgressCard` transition to completed.
3. Say *"evaluate all the results from that scan"*. Watch `BatchProgressCard` counters advance.
4. Click *"Save to pipeline"* on a top result.
5. Navigate to `/pipeline`. Confirm the application appears in the Saved column.
6. Drag it to Applied. Refresh. Verify status persisted.
7. Navigate to `/scans`, run the default scan again manually, confirm the detail page polls correctly.

Kill the stack: `docker-compose down` + any background processes.

- [ ] **Step 7: Completion checklist**

Verify every Phase 2c scope item is done:

- [ ] Migration `0005_phase2c_scanning_batch_pipeline.py` creates 6 tables + indexes
- [ ] `core/scanner/` — 3 adapters (Greenhouse, Ashby, Lever) + dedup + relevance + default_config + ScannerService
- [ ] `core/batch/` — l0_filter + l1_triage + l2_evaluate + funnel + BatchService
- [ ] `inngest/` — client, scan_boards_fn, batch_evaluate_fn, functions registry
- [ ] `POST /api/v1/scan-configs` (paywalled), GET/PUT/DELETE, `POST /:id/run` (paywalled)
- [ ] `GET /api/v1/scan-runs`, `GET /api/v1/scan-runs/:id`
- [ ] `POST /api/v1/batch-runs` (paywalled, 3 input modes), GET list + detail
- [ ] `POST /api/v1/applications` (non-paywalled), GET/PUT/DELETE with filters
- [ ] `POST /api/v1/inngest` serve endpoint
- [ ] Default 15-company scan config seeded on onboarding `done` transition
- [ ] Agent tools: `start_job_scan` + `start_batch_evaluation` wired + dispatch + system prompt updated
- [ ] `NOT_YET_AVAILABLE_TEMPLATES` in prompts.py no longer lists `SCAN_JOBS` or `BATCH_EVAL`
- [ ] Frontend: ScansPage, ScanDetailPage, ScanConfigEditor modal, PipelinePage kanban with drag-drop
- [ ] Frontend: ScanProgressCard + ScanResultsCard + BatchProgressCard chat cards
- [ ] Frontend: `usePolling` hook + API client extensions
- [ ] Frontend: routes `/scans`, `/scans/:id`, `/pipeline` + AppShell nav links
- [ ] `@dnd-kit/core` + `@dnd-kit/sortable` added to user-portal dependencies
- [ ] All unit tests pass
- [ ] All integration tests pass (incl. test_phase2c_smoke)
- [ ] pdf-render tests pass
- [ ] user-portal vitest passes
- [ ] Backend mypy strict clean
- [ ] Backend ruff clean, black clean
- [ ] (Optional) dogfood pass completed

- [ ] **Step 8: Checkpoint**

Checkpoint message: `chore(phase2c): complete Phase 2c — scanning + batch + pipeline`

---

## Phase 2c Summary

**What's built:**
- 6 new database tables: `scan_configs`, `scan_runs`, `scan_results`, `batch_runs`, `batch_items`, `applications`
- `core/scanner/` module: 3 board adapters (Greenhouse / Ashby / Lever) sharing a BoardAdapter ABC, httpx rate limiter, content-hash dedup, Gemini L1 relevance scorer, default 15-company config, ScannerService orchestrator with parallel board scraping + 500-listing cap
- `core/batch/` module: pure-Python L0 rule filter (location + salary + seniority), L1 Gemini triage wrapper, L2 Claude evaluation fan-out with 10-concurrent bounded parallelism, funnel orchestrator, BatchService with 3-mode input resolution (`job_urls`, `job_ids`, `scan_run_id`)
- `inngest/` module: Inngest client singleton, `scan_boards_fn` + `batch_evaluate_fn` with per-user concurrency limits + retries + pure-Python entry shims for direct test invocation
- New API routers: scan-configs CRUD, scan-runs + trigger, batch-runs CRUD with detail summary, applications CRUD with status + min-grade filters, Inngest serve endpoint
- Default 15-company scan config seeded at onboarding `done` transition (shares `_on_onboarding_done` hook with Phase 2b trial start) — NOT auto-run to avoid hidden first-session cost
- Agent: `start_job_scan` + `start_batch_evaluation` tools wired, graph dispatch updated, system prompt updated to reference 4 tools, `NOT_YET_AVAILABLE_TEMPLATES` trimmed to interview_prep + negotiate only
- Frontend: `ScansPage` (list + run + delete), `ScanConfigEditor` (create/edit modal), `ScanDetailPage` (polling + evaluate-all button), `PipelinePage` (6-column kanban with drag-and-drop via @dnd-kit), `ScanProgressCard` + `ScanResultsCard` + `BatchProgressCard` chat cards, `usePolling` hook, API client extensions
- ~35 new backend tests + ~9 new frontend tests
- Running total after 2c: ~134+ backend tests, ~18 frontend tests

**What's deferred to later phases:**
- Scheduled scans (cron / Inngest cron trigger) — Phase 5
- Interview prep + Negotiation modules — Phase 2d
- `feedback` table + `POST /evaluations/:id/feedback` — Phase 2d
- `negotiations` table + `FOREIGN KEY` constraint on `applications.negotiation_id` — Phase 2d
- `POST /conversations/:id/actions` card-action routing — Phase 5
- LinkedIn / Workday / SmartRecruiters scrapers — post-MVP
- Playwright-based JS-rendered job scraping — Phase 5
- Batch cancellation mid-flight — Phase 5
- Real AWS deployment of Inngest — Phase 5
- Admin dashboards for scan health / cost breakdown — Phase 5
- Per-user cost quotas (column exists since Phase 2b, still unused) — follow-up

**Next phase: 2d** — Interview prep + Negotiation + `feedback` table + `POST /evaluations/:id/feedback`. Phase 2d was rescoped smaller when `applications` moved forward into 2c.

