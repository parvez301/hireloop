# CareerAgent Phase 2c — Job Scanning + Batch Processing + Application Pipeline (Design Spec)

> **Parent spec:** [`2026-04-10-careeragent-design.md`](./2026-04-10-careeragent-design.md). This is a **delta spec**.
>
> **Predecessors:** Phase 2a (agent + evaluation + CV), Phase 2b (Stripe + paywall). Both shipped.
>
> **Rescope:** this spec pulls the `applications` table + pipeline kanban forward from Phase 2d into Phase 2c. Phase 2d shrinks to: interview prep + negotiation + `feedback` table.

---

## 1. Goal

Ship **Job Scanning** (Greenhouse + Ashby + Lever adapters), **Batch Processing** (L0/L1/L2 funnel), and the **Application Pipeline** (kanban) — all end-to-end from the agent, REST endpoints, and a full frontend. Introduce **Inngest** as the async job runner for long-running fan-out work. Ship a default 15-company seeded scan config so every new user can run a scan on day one.

**End state:**

1. New user onboards → default "AI & Developer Tools Companies" scan config is seeded on their account with all 15 companies from parent spec Appendix M.
2. User says *"scan for jobs"* in chat → agent calls `start_job_scan` tool → Inngest event `scan/started` fires → `scan_boards_fn` runs in background → scrapes all 15 boards in parallel → dedupes into shared `jobs` pool by `content_hash` → L1 Gemini classifies each new listing for relevance → marks scan run `completed`.
3. Agent's initial response returns a `ScanProgressCard` that polls `GET /scan-runs/:id` every 3s until status=completed, then transitions to a `ScanResultsCard` showing top listings.
4. User says *"evaluate all of them"* → agent calls `start_batch_evaluation` tool with `scan_run_id` → Inngest event `batch/started` fires → `batch_evaluate_fn` runs the L0/L1/L2 funnel → L0 rule filter → L1 Gemini relevance score → L2 Claude Sonnet full evaluation on survivors → writes `evaluations` rows → finalizes `batch_run`.
5. Agent initial response returns a `BatchProgressCard` that polls `GET /batch-runs/:id` every 3s showing L0/L1/L2 counts as they advance, then transitions to a final results card sorted by grade.
6. User clicks *"Save to pipeline"* on any evaluation card → `POST /api/v1/applications` → row in `applications` table with `status='saved'` → visible on `/pipeline` kanban.
7. User can drag cards across kanban columns (`saved` → `applied` → `interviewing` → `offered` → `rejected`) which updates `applications.status`.
8. User can visit `/scans` to see all scan configs, run them manually, view past run history, and **create / edit / delete** scan configs (companies, keywords, exclude keywords).

**Non-goals (explicit):**
- **Scheduled scans** — the `schedule` column is persisted but no cron/Inngest trigger reads it. Manual scans only. `FEATURE_SCAN_SCHEDULING=false`.
- **Interview prep, negotiation modules** — Phase 2d.
- **`feedback` table + `POST /evaluations/:id/feedback`** — Phase 2d.
- **`POST /conversations/:id/actions` card-action routing** — Phase 5. Card buttons in Phase 2c call REST endpoints directly.
- **Real AWS deployment of Inngest** — Phase 5. Dev uses `inngest dev` in `docker-compose.yml` (already present behind the `inngest` profile).
- **LinkedIn / Workday / SmartRecruiters scrapers** — post-MVP future work.
- **JS-heavy SPA scraping** (Playwright-driven) — out. The 3 supported platforms all have public JSON APIs; scraper uses `httpx` only. Sites requiring JS get a "paste the job description" fallback (same as Phase 2a's `POST /jobs/parse`).
- **Custom L1 classifiers per user** — one shared Gemini prompt with per-user profile injected at call time.
- **Per-company scan cost caps** — the 500-listing cap is per-scan-run, not per-board.

---

## 2. Architecture delta

**New backend modules:**

```
backend/src/career_agent/
├── core/
│   ├── scanner/
│   │   ├── __init__.py               [NEW]
│   │   ├── adapters/
│   │   │   ├── __init__.py           [NEW]
│   │   │   ├── base.py               [NEW]  BoardAdapter ABC + ListingPayload dataclass
│   │   │   ├── greenhouse.py         [NEW]  boards-api.greenhouse.io adapter
│   │   │   ├── ashby.py              [NEW]  api.ashbyhq.com adapter
│   │   │   └── lever.py              [NEW]  api.lever.co adapter
│   │   ├── dedup.py                  [NEW]  content_hash dedup + jobs pool upsert
│   │   ├── relevance.py              [NEW]  Gemini L1 relevance scorer (Appendix D.5 prompt)
│   │   ├── default_config.py         [NEW]  Seed 15-company config from Appendix M
│   │   └── service.py                [NEW]  ScannerService: run_scan(scan_config_id) orchestrator
│   └── batch/
│       ├── __init__.py               [NEW]
│       ├── l0_filter.py              [NEW]  Rule filter (parent spec Appendix D.8)
│       ├── l1_triage.py              [NEW]  Wraps scanner.relevance for batch use
│       ├── l2_evaluate.py            [NEW]  Wraps evaluation.service for batch fan-out
│       ├── funnel.py                 [NEW]  L0 → L1 → L2 orchestrator
│       └── service.py                [NEW]  BatchService: resolve inputs, start run, finalize
├── inngest/
│   ├── __init__.py                   [NEW]
│   ├── client.py                     [NEW]  inngest.Inngest singleton + signing key
│   ├── scan_boards.py                [NEW]  scan_boards_fn (parent Appendix F)
│   ├── batch_evaluate.py             [NEW]  batch_evaluate_fn (parent Appendix F)
│   └── functions.py                  [NEW]  ALL_FUNCTIONS registry for Inngest serve endpoint
├── api/
│   ├── scan_configs.py               [NEW]  POST/GET/PUT/DELETE /scan-configs
│   ├── scan_runs.py                  [NEW]  GET /scan-runs, GET /scan-runs/:id, POST /scan-configs/:id/run
│   ├── batch_runs.py                 [NEW]  POST /batch-runs, GET /batch-runs, GET /batch-runs/:id
│   ├── applications.py               [NEW]  CRUD pipeline
│   └── inngest.py                    [NEW]  POST /inngest (function serve endpoint, signed)
├── integrations/
│   └── board_http.py                 [NEW]  Shared httpx client with 1-req/sec per-platform rate limit
├── models/
│   ├── scan_config.py                [NEW]
│   ├── scan_run.py                   [NEW]  ScanRun + ScanResult
│   ├── batch_run.py                  [NEW]  BatchRun + BatchItem
│   └── application.py                [NEW]
├── schemas/
│   ├── scan_config.py                [NEW]
│   ├── scan_run.py                   [NEW]
│   ├── batch_run.py                  [NEW]
│   └── application.py                [NEW]
├── services/
│   ├── scan_config.py                [NEW]  CRUD + seed on onboarding done
│   └── application.py                [NEW]  CRUD + state transitions
├── core/agent/
│   ├── tools.py                      [MOD]  +start_job_scan_tool, +start_batch_evaluation_tool
│   ├── graph.py                      [MOD]  register new tools in TOOL_CALL dispatch
│   └── prompts.py                    [MOD]  remove SCAN_JOBS + BATCH_EVAL from NOT_YET_AVAILABLE_TEMPLATES
└── services/profile.py               [MOD]  _on_onboarding_done also seeds default scan config
```

**Migration:** `0005_phase2c_scanning_batch_pipeline.py` — adds 6 new tables.

**Frontend delta (user-portal):**

```
src/pages/
├── ScansPage.tsx                         [NEW]  list scan configs, run buttons, last-run status
├── ScanDetailPage.tsx                    [NEW]  scan run results + "evaluate all" + scan config edit
├── ScanConfigEditor.tsx                  [NEW]  create/edit modal (companies list + keywords)
└── PipelinePage.tsx                      [NEW]  kanban view of applications

src/components/chat/cards/
├── ScanProgressCard.tsx                  [NEW]  polls until scan completes
├── ScanResultsCard.tsx                   [NEW]  top-5 listings, "Evaluate all" button
├── BatchProgressCard.tsx                 [NEW]  L0/L1/L2 counters live, polls until done
└── ApplicationStatusCard.tsx             [NEW]  existing spec Appendix G

src/components/pipeline/
├── KanbanColumn.tsx                      [NEW]
├── ApplicationCard.tsx                   [NEW]
└── PipelineFilters.tsx                   [NEW]  filter by status, min grade

src/lib/
├── api.ts                                [MOD]  +scanConfigs, +scanRuns, +batchRuns, +applications
└── polling.ts                            [NEW]  usePolling hook (setInterval-based, cancel on unmount)

src/App.tsx                               [MOD]  routes: /scans, /scans/:id, /pipeline
src/components/layout/AppShell.tsx        [MOD]  nav links for Scans + Pipeline
```

**Phase 2a touch points (gating only):**
- `POST /api/v1/scan-configs`, `POST /api/v1/scan-configs/:id/run`, `POST /api/v1/batch-runs` all use `EntitledDbUser` (paywalled). `GET` endpoints use `CurrentDbUser` (trial-expired users can still *view* their historical scan data; they just can't start new work).
- `POST /api/v1/applications`, `PUT /api/v1/applications/:id`, `DELETE /api/v1/applications/:id` use `CurrentDbUser` — application tracking is free even after trial expiry, because users shouldn't lose organizational data when they stop paying.
- `POST /api/v1/inngest` — Inngest function serve endpoint. **Not JWT-authenticated**; uses Inngest's signing key middleware.

### 2.1 Data flow — user says "scan for jobs"

```
ChatPage → POST /conversations/:id/messages { content: "scan for jobs" }
       │
       │  runner.run_turn:
       │    classifier → SCAN_JOBS
       │    route_node (Claude) → TOOL_CALL: start_job_scan {}
       │    start_job_scan_tool:
       │      - load user's default scan config
       │      - INSERT INTO scan_runs (status='pending', scan_config_id, inngest_event_id=<uuid>)
       │      - await inngest_client.send(Event(name="scan/started",
       │            data={scan_config_id, user_id, scan_run_id}))
       │      - return {ok: True, card: {type: "scan_progress",
       │            data: {scan_run_id, status: "pending", scan_name}}}
       ▼
Assistant message persisted with ScanProgressCard
       │
       ▼
Frontend: ScanProgressCard renders; usePolling → GET /scan-runs/:id every 3s
       │
       │    Meanwhile, Inngest picks up scan/started event and runs
       │    scan_boards_fn in background (may take 30s–2min):
       │
       │    step 1 (parallel): scrape all configured board URLs via
       │        GreenhouseAdapter / AshbyAdapter / LeverAdapter
       │        Each adapter hits the public JSON API with a 10s timeout
       │        and 3 retries. 1 req/sec rate limit per platform.
       │
       │    step 2: flatten all listings → compute content_hash per listing
       │        → upsert into jobs pool (existing rows kept).
       │        → cap at 500 total (take first 500 after dedup).
       │
       │    step 3: for each new job, run L1 Gemini relevance scoring
       │        (Appendix D.5 prompt) with user's profile.
       │        Low-concurrency: 5 at a time to respect Gemini QPS.
       │
       │    step 4: INSERT INTO scan_results (scan_run_id, job_id, relevance_score, is_new)
       │
       │    step 5: UPDATE scan_runs SET status='completed',
       │        jobs_found=..., jobs_new=..., completed_at=now()
       │
       ▼
Next poll returns status=completed + results
       │
       │  Frontend transitions ScanProgressCard → ScanResultsCard
       │  showing top 5 listings sorted by relevance score.
       ▼
User clicks "Evaluate all" on the card (REST call, not agent turn)
       │
       ▼
POST /api/v1/batch-runs { scan_run_id }
       │
       │  batch_runs row created
       │  inngest_client.send(Event(name="batch/started",
       │      data={batch_run_id, user_id, scan_run_id}))
       │  returns {data: {id: batch_run_id, status: 'pending', ...}}
       ▼
Frontend shows BatchProgressCard, polls GET /batch-runs/:id every 3s
       │
       │  Meanwhile, batch_evaluate_fn runs:
       │    step 1: resolve input → list of job_ids (from scan_run_id)
       │    step 2: L0 filter — pure Python, no LLM — mark survivors
       │    step 3: L1 Gemini relevance — mark survivors
       │    step 4: L2 Claude Sonnet evaluation — fan-out, concurrency=10
       │             writes evaluations rows
       │    step 5: finalize batch_run, update counters
       │
       ▼
Polling shows L0/L1/L2 counts advancing, then final results
       │
       │  BatchProgressCard transitions to results view
       │  User can click "Save to pipeline" on any high-grade eval
       ▼
POST /api/v1/applications { job_id, evaluation_id, status: "saved" }
       │
       ▼
Application row created → visible on /pipeline kanban
```

### 2.2 Key architectural decisions

| Decision | Choice | Why |
|---|---|---|
| Async runner | **Inngest** (already in parent spec) | Durable, replay-friendly, matches Synapse pattern. Local dev: `inngest` service runs on default `docker compose up` (no profile gate). |
| Inngest serve | **Single `/api/v1/inngest` endpoint** with all function registrations | Standard Inngest pattern; the dev server polls it for signing + dispatch. |
| Scraper HTTP | **`httpx` async with shared rate limiter**, 1 req/sec per platform | Lever and Ashby public APIs are forgiving, but being a polite citizen prevents future IP bans. |
| Scraper fallback | **No JS rendering.** Sites that need JS return `JOB_PARSE_FAILED` and user pastes the JD manually | The 3 supported platforms all publish JSON APIs. Playwright is Phase 5 work. |
| Scan polling | **Client polls `GET /scan-runs/:id` every 3s**; no server push | Simple. 3s is snappy enough; scans typically take 30s–2min. SSE or websockets is overkill. |
| Batch polling | Same 3-second poll on `GET /batch-runs/:id` | Consistent with scan polling. |
| L0 location for batch | **Pure Python rule filter in `core/batch/l0_filter.py`** — no LLM, no I/O | Matches parent spec Appendix D.8. Fast, deterministic, cheap to test. |
| L1 relevance for batch | **Shared with scanner** — both use `core/scanner/relevance.py` | One prompt, one client call site, consistent scoring. |
| L2 evaluation for batch | **Reuses `core/evaluation/service.py` from 2a** via fan-out | No new Claude prompt; full 10-dimension eval per survivor. Expensive but bounded by L0+L1 filter. |
| Batch L2 concurrency | **10 parallel via `ctx.step.parallel`** | Matches parent spec Appendix F. Bounded to respect Anthropic rate limits. |
| Default scan config | **Seeded at onboarding `done` transition**, same hook as Phase 2b trial start | Single hook point (`_on_onboarding_done`), reuses existing transition detection. |
| Scanner adapter pattern | **Abstract `BoardAdapter` with 3 concrete subclasses** | Lets us add Workday / SmartRecruiters later without touching the orchestrator. Each adapter owns its own URL format + JSON schema parsing. |
| Scan result limit | **Hard cap at 500 listings per run** (after dedup, before L1) | Cost guardrail per Q3 decision. If a scan would return >500, truncate and mark the run with `truncated=true` for UI display. |
| Card button actions | **Direct REST calls from frontend**, not agent turns | Phase 5 will add `POST /conversations/:id/actions` routing; 2c keeps things simple. "Save to pipeline" = direct `POST /applications`. |
| Application CRUD | **Accessible to trial-expired users** | Users shouldn't lose organizational data on expiry. Only new cost-generating work is paywalled. |

### 2.3 `POST /api/v1/inngest` — security

This route is **not** JWT-authenticated. Inngest Cloud (or the dev server) calls it to register functions and dispatch work. Protection relies entirely on **Inngest signing-key verification** in middleware.

| Environment | Expectation |
|---|---|
| **Local** | `INNGEST_DEV=1`; signing key may be empty per SDK defaults; only trusted processes should reach your API. |
| **Production** | Set **`INNGEST_SIGNING_KEY`** (and event key as required by your deployment). Requests must fail closed if verification fails. |

**Production checklist (minimum):**

1. `INNGEST_SIGNING_KEY` is set from a secret store; never committed.
2. The `/api/v1/inngest` path is reachable only by Inngest’s IPs or your ingress allowlist if you self-host.
3. Rotating keys: update the secret and redeploy before retiring the old key.
4. Misconfiguration (missing verification, wrong key) can allow **unauthorized registration or invocation of background work** — treat as a **severity-high** ops concern.

---

## 3. Data model delta

Migration `0005_phase2c_scanning_batch_pipeline.py` — 6 new tables + indexes.

### 3.1 `scan_configs`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `user_id` | UUID FK → `users.id` CASCADE | |
| `name` | VARCHAR(255) NOT NULL | |
| `companies` | JSONB NOT NULL | `[{name, platform, board_slug}]` |
| `keywords` | JSONB | array of strings (optional filter terms) |
| `exclude_keywords` | JSONB | |
| `schedule` | VARCHAR(32) NOT NULL DEFAULT `'manual'` | `'manual' \| 'daily' \| 'weekly'` — persisted but ignored in 2c |
| `is_active` | BOOLEAN NOT NULL DEFAULT true | |
| `created_at` | TIMESTAMPTZ | |
| `updated_at` | TIMESTAMPTZ | |

Indexes: `idx_scan_configs_user_id`.

### 3.2 `scan_runs`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `user_id` | UUID FK → `users.id` CASCADE | |
| `scan_config_id` | UUID FK → `scan_configs.id` CASCADE | |
| `inngest_event_id` | VARCHAR(255) | Inngest event ID for observability |
| `status` | VARCHAR(32) NOT NULL | `'pending' \| 'running' \| 'completed' \| 'failed'` |
| `jobs_found` | INTEGER NOT NULL DEFAULT 0 | |
| `jobs_new` | INTEGER NOT NULL DEFAULT 0 | |
| `truncated` | BOOLEAN NOT NULL DEFAULT false | Set to true when 500-cap hit |
| `error` | TEXT | |
| `started_at` | TIMESTAMPTZ NOT NULL DEFAULT now() | |
| `completed_at` | TIMESTAMPTZ | |

Indexes: `idx_scan_runs_user_id`, `idx_scan_runs_status`, `idx_scan_runs_user_started` (`user_id, started_at DESC`).

### 3.3 `scan_results`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `scan_run_id` | UUID FK → `scan_runs.id` CASCADE | |
| `job_id` | UUID FK → `jobs.id` CASCADE | |
| `relevance_score` | FLOAT | 0.0–1.0 from L1 Gemini |
| `is_new` | BOOLEAN NOT NULL DEFAULT true | True if content_hash was not in `jobs` pool before this run |
| `created_at` | TIMESTAMPTZ | |

Unique constraint on `(scan_run_id, job_id)`. Indexes: `idx_scan_results_run_id`, `idx_scan_results_run_score` (`scan_run_id, relevance_score DESC`).

### 3.4 `batch_runs`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `user_id` | UUID FK → `users.id` CASCADE | |
| `inngest_event_id` | VARCHAR(255) | |
| `status` | VARCHAR(32) NOT NULL | `'pending' \| 'running' \| 'completed' \| 'failed'` |
| `total_jobs` | INTEGER NOT NULL | |
| `l0_passed` | INTEGER NOT NULL DEFAULT 0 | |
| `l1_passed` | INTEGER NOT NULL DEFAULT 0 | |
| `l2_evaluated` | INTEGER NOT NULL DEFAULT 0 | |
| `source_type` | VARCHAR(32) NOT NULL | `'job_urls' \| 'job_ids' \| 'scan_run_id'` — for audit |
| `source_ref` | VARCHAR(255) | scan_run_id UUID or 'ad-hoc' |
| `started_at` | TIMESTAMPTZ NOT NULL DEFAULT now() | |
| `completed_at` | TIMESTAMPTZ | |

Indexes: `idx_batch_runs_user_id`, `idx_batch_runs_user_started` (`user_id, started_at DESC`).

### 3.5 `batch_items`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `batch_run_id` | UUID FK → `batch_runs.id` CASCADE | |
| `job_id` | UUID FK → `jobs.id` CASCADE | |
| `evaluation_id` | UUID FK → `evaluations.id` SET NULL | Populated on L2 success |
| `stage` | VARCHAR(32) NOT NULL | `'queued' \| 'l0' \| 'l1' \| 'l2' \| 'done' \| 'filtered'` |
| `filter_reason` | VARCHAR(64) | `'location_mismatch' \| 'below_min_salary' \| 'seniority_mismatch' \| 'low_relevance' \| ...` |
| `created_at` | TIMESTAMPTZ | |

Indexes: `idx_batch_items_run_id`, `idx_batch_items_run_stage` (`batch_run_id, stage`).

### 3.6 `applications`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `user_id` | UUID FK → `users.id` CASCADE | |
| `job_id` | UUID FK → `jobs.id` CASCADE | |
| `status` | VARCHAR(32) NOT NULL | `'saved' \| 'applied' \| 'interviewing' \| 'offered' \| 'rejected' \| 'withdrawn'` |
| `applied_at` | TIMESTAMPTZ | Set when status transitions to `'applied'` |
| `notes` | TEXT | |
| `evaluation_id` | UUID FK → `evaluations.id` SET NULL | Optional link |
| `cv_output_id` | UUID FK → `cv_outputs.id` SET NULL | Optional link |
| `negotiation_id` | UUID NULL | No FK constraint in 2c — the `negotiations` table doesn't exist yet. Phase 2d adds the constraint when the table lands. Populated by 2d code path. |
| `updated_at` | TIMESTAMPTZ NOT NULL DEFAULT now() | |

Unique on `(user_id, job_id)`. Indexes: `idx_applications_user_id`, `idx_applications_user_status` (`user_id, status`), `idx_applications_updated` (`updated_at DESC`).

**Note:** `negotiation_id` is added in 2c as a nullable UUID column without an FK constraint, to avoid a dedicated migration in 2d just for this column. Phase 2d will add the `negotiations` table and add the `FOREIGN KEY (negotiation_id) REFERENCES negotiations(id) ON DELETE SET NULL` constraint in its own migration.

---

## 4. API delta

All endpoints under `/api/v1`. JWT required unless noted. Paywall (`EntitledDbUser`) marked where applied.

### 4.1 Scan configs

| Method | Path | Gate | Body / Params | Response |
|---|---|---|---|---|
| `GET` | `/scan-configs` | Current | — | `200 { "data": ScanConfig[] }` |
| `POST` | `/scan-configs` | **Entitled** | `{ name, companies[], keywords[], exclude_keywords[], schedule }` | `201 { "data": ScanConfig }` |
| `GET` | `/scan-configs/:id` | Current | — | `200 { "data": ScanConfig }` |
| `PUT` | `/scan-configs/:id` | **Entitled** | `{ name?, companies?, keywords?, exclude_keywords?, schedule?, is_active? }` | `200 { "data": ScanConfig }` |
| `DELETE` | `/scan-configs/:id` | Current | — | `204` |
| `POST` | `/scan-configs/:id/run` | **Entitled** | `{}` | `202 { "data": { scan_run_id, status } }` — fires Inngest event, returns immediately |

### 4.2 Scan runs

| Method | Path | Gate | Body / Params | Response |
|---|---|---|---|---|
| `GET` | `/scan-runs` | Current | `?limit=20&status=completed` | `200 { "data": ScanRun[] }` |
| `GET` | `/scan-runs/:id` | Current | — | `200 { "data": { scan_run, results: ScanResult[top 50 by relevance] } }` |

### 4.3 Batch runs

| Method | Path | Gate | Body / Params | Response |
|---|---|---|---|---|
| `POST` | `/batch-runs` | **Entitled** | exactly one of `{ job_urls[] }`, `{ job_ids[] }`, `{ scan_run_id }` | `202 { "data": { batch_run_id, status: "pending", total_jobs } }` |
| `GET` | `/batch-runs` | Current | `?limit=20` | `200 { "data": BatchRun[] }` |
| `GET` | `/batch-runs/:id` | Current | — | `200 { "data": { batch_run, items_summary: { queued, l0, l1, l2, done, filtered }, top_results: Evaluation[top 10] } }` |

### 4.4 Applications (pipeline)

| Method | Path | Gate | Body / Params | Response |
|---|---|---|---|---|
| `GET` | `/applications` | Current | `?status=applied&min_grade=B` | `200 { "data": Application[] }` |
| `POST` | `/applications` | Current | `{ job_id, status?, evaluation_id?, cv_output_id?, notes? }` — defaults to `status='saved'` | `201 { "data": Application }` |
| `GET` | `/applications/:id` | Current | — | `200 { "data": Application }` |
| `PUT` | `/applications/:id` | Current | `{ status?, notes?, applied_at?, cv_output_id? }` | `200 { "data": Application }` |
| `DELETE` | `/applications/:id` | Current | — | `204` |

### 4.5 Inngest serve endpoint

| Method | Path | Gate | Purpose |
|---|---|---|---|
| `POST` | `/inngest` | **Inngest signing key** | FastAPI integration via `inngest.fast_api.serve(app, inngest_client, functions)` — dispatches function invocations from the Inngest dev server (or cloud in prod). |
| `PUT` | `/inngest` | Inngest | Used by Inngest for introspection / function registration. |
| `GET` | `/inngest` | Inngest | Health check. |

### 4.6 New error codes

| Code | HTTP | When |
|---|---|---|
| `SCAN_CONFIG_NOT_FOUND` | 404 | User doesn't own the scan config |
| `SCAN_RUN_NOT_FOUND` | 404 | |
| `BATCH_RUN_NOT_FOUND` | 404 | |
| `APPLICATION_NOT_FOUND` | 404 | |
| `INVALID_BATCH_INPUT` | 422 | More than one of `job_urls`/`job_ids`/`scan_run_id`, or none |
| `SCAN_RUN_STILL_RUNNING` | 409 | User tried to `POST /batch-runs` with a `scan_run_id` that hasn't completed |
| `SCAN_ADAPTER_FAILED` | 502 | All 3 board adapters failed for a scan — surfaced as a scan run `status='failed'` with `error` field |
| `LISTING_CAP_REACHED` | 200 | Not an error — returned as `scan_runs.truncated=true` and a `meta.warning` field on `GET /scan-runs/:id` |

---

## 5. Component designs

### 5.1 Scanner adapters (`core/scanner/adapters/`)

**Abstract base** (`base.py`):

```python
@dataclass
class ListingPayload:
    """Normalized listing across all platforms."""
    title: str
    company: str
    location: str | None
    salary_min: int | None
    salary_max: int | None
    employment_type: str | None
    seniority: str | None
    description_md: str
    requirements_json: dict[str, Any]
    source_url: str  # The canonical job URL


class BoardAdapter(ABC):
    """Base class for company board scrapers."""

    platform: str  # 'greenhouse' | 'ashby' | 'lever'

    @abstractmethod
    async def fetch_listings(self, board_slug: str) -> list[ListingPayload]:
        """Fetch and normalize all open listings for a company slug."""
```

**Concrete adapters:**

- `GreenhouseAdapter` — GETs `https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true`. Parses `jobs[]`, each has `{title, content (HTML), location, metadata, absolute_url, offices}`. HTML → markdown via `markdownify`. Salary/requirements often in structured metadata when present.
- `AshbyAdapter` — GETs `https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=true`. Parses `jobs[]`, each has `{title, description, locationName, departmentName, employmentType, compensation, descriptionHtml}`.
- `LeverAdapter` — GETs `https://api.lever.co/v0/postings/{slug}?mode=json`. Returns a flat array of postings with `{text, categories, descriptionPlain, lists, additional}`.

All adapters share:
- 10s timeout, 3 retries with exponential backoff via `tenacity`
- 1 req/sec rate limit via `integrations/board_http.py` (asyncio.Semaphore + sleep)
- User-Agent: `CareerAgent/1.0 (+https://careeragent.com/bot)` (same as Phase 2a job parser)
- Errors raise `BoardAdapterError(platform, slug, cause)`; orchestrator catches per-company so one bad board doesn't kill a scan

### 5.2 `core/scanner/dedup.py`

```python
def compute_content_hash(listing: ListingPayload) -> str:
    """SHA256 of normalize(description + requirements_json)."""


async def upsert_jobs(
    session: AsyncSession,
    listings: list[ListingPayload],
    platform: str,
    company: str,
) -> list[tuple[Job, bool]]:
    """
    For each listing, either load existing `jobs` row by content_hash or insert new.
    Returns [(job, is_new), ...]. Bounded to first 500 after dedup.
    """
```

### 5.3 `core/scanner/relevance.py`

Thin wrapper around the Gemini Flash client (`core/llm/gemini_client.py` from 2a). Uses **parent spec Appendix D.5 prompt** verbatim. One function:

```python
async def score_relevance(
    *,
    job: Job,
    profile_summary: dict[str, Any],
    timeout_s: float = 5.0,
) -> float:
    """Returns a 0.0–1.0 relevance score. 0.0 on parse failure."""
```

Internal concurrency via asyncio.Semaphore at the call site (5 at a time).

### 5.4 `core/scanner/service.py`

```python
@dataclass
class ScannerContext:
    user_id: UUID
    session: AsyncSession


class ScannerService:
    async def run_scan(self, scan_config_id: UUID) -> ScanRunResult:
        """
        Orchestrator called from Inngest scan_boards_fn.
        1. load scan_config
        2. for each company in parallel, call the matching adapter
        3. flatten + dedup + truncate at 500
        4. upsert into jobs pool
        5. L1 relevance score each new job
        6. write scan_results
        7. mark scan_run completed
        """
```

### 5.5 `core/scanner/default_config.py`

```python
DEFAULT_SCAN_CONFIG_NAME = "AI & Developer Tools Companies"

DEFAULT_COMPANIES = [
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
    """Create the default config for a user. Idempotent — returns existing if already seeded.

    Does NOT trigger a scan run. The user must explicitly click 'Run scan' or ask
    the agent to scan. This avoids hidden first-session cost at signup.
    """
```

Called from `services/profile.py::_on_onboarding_done` alongside the existing `ensure_subscription` call.

### 5.6 `core/batch/l0_filter.py`

Pure Python rule filter per parent Appendix D.8:

```python
def l0_filter(job: Job, profile: Profile) -> tuple[bool, str | None]:
    """Returns (passes, reason_if_filtered)."""
```

Tests (TDD):
- Location match: user target vs. job location, remote always passes.
- Salary floor: `job.salary_max < profile.min_salary` → filter (only if salary posted).
- Seniority match: derive user seniority from profile, filter on obvious mismatches.
- No filter when data missing → pass by default (don't filter optimistically).

### 5.7 `core/batch/funnel.py`

```python
async def run_l0(
    session: AsyncSession,
    batch_run_id: UUID,
    job_ids: list[UUID],
    user_id: UUID,
) -> list[UUID]:
    """Run rule filter. Update batch_items.stage. Return survivors."""


async def run_l1(
    session: AsyncSession,
    batch_run_id: UUID,
    job_ids: list[UUID],
    user_id: UUID,
    threshold: float = 0.5,
) -> list[UUID]:
    """Run Gemini relevance scoring. Survivors ≥ threshold."""


async def run_l2(
    session: AsyncSession,
    batch_run_id: UUID,
    job_ids: list[UUID],
    user_id: UUID,
) -> list[UUID]:
    """Run full 10-dim Claude Sonnet evaluation. Writes evaluations rows."""
```

### 5.8 `inngest/client.py`

```python
import inngest
from career_agent.config import get_settings

_client: inngest.Inngest | None = None


def get_inngest_client() -> inngest.Inngest:
    global _client
    if _client is None:
        settings = get_settings()
        _client = inngest.Inngest(
            app_id="career-agent",
            event_key=settings.inngest_event_key or None,
            signing_key=settings.inngest_signing_key or None,
            is_production=settings.environment == "prod",
        )
    return _client
```

### 5.9 `inngest/scan_boards.py` (and `batch_evaluate.py`)

Both functions follow parent spec Appendix F verbatim. Key additions:

- `retries=3` on both.
- Per-user concurrency limit 5 via `inngest.Concurrency(limit=5, key="event.data.user_id")`.
- Global concurrency 50.
- Each step wraps the real service call (`ScannerService.run_scan` or the funnel stages) so Inngest can replay on failure.

Both functions open their own DB session via `get_session_factory()` — they do not inherit from the HTTP request scope.

### 5.10 Agent tool additions

`core/agent/tools.py`:

```python
async def start_job_scan_tool(
    runtime: ToolRuntime,
    *,
    scan_config_id: str | None = None,
) -> dict[str, Any]:
    """If scan_config_id is None, use user's default scan config."""


async def start_batch_evaluation_tool(
    runtime: ToolRuntime,
    *,
    scan_run_id: str | None = None,
    job_urls: list[str] | None = None,
    job_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Exactly one of scan_run_id / job_urls / job_ids required."""
```

Both tools:
1. Create the DB row (`scan_runs` or `batch_runs`) with `status='pending'`.
2. Send the corresponding Inngest event.
3. Return a `ScanProgressCard` or `BatchProgressCard` with the run ID.
4. The agent's response text is something like *"Starting a scan across your 15 default companies. I'll let you know when it's done."*

`core/agent/graph.py`:
- Dispatch table in `route_node`:
  - `"start_job_scan"` → `start_job_scan_tool(...)`
  - `"start_batch_evaluation"` → `start_batch_evaluation_tool(...)`
- Tool manifest string in the cacheable system block is updated to list all 4 tools (evaluate_job, optimize_cv, start_job_scan, start_batch_evaluation).

`core/agent/prompts.py`:
- `NOT_YET_AVAILABLE_TEMPLATES` loses its `"SCAN_JOBS"` and `"BATCH_EVAL"` keys. The dict keeps only `"INTERVIEW_PREP"` and `"NEGOTIATE"` (those ship in Phase 2d).

### 5.11 Frontend — Pipeline kanban

**`PipelinePage.tsx`** at `/pipeline`:
- 6 columns (saved, applied, interviewing, offered, rejected, withdrawn).
- Loads `GET /applications` on mount; regroups by status client-side.
- Column cards show: job title, company, grade badge (if evaluation linked), last update time, "Edit" button.
- **Drag-and-drop** via `@dnd-kit/core` (new dep) — dragging a card to a new column fires `PUT /applications/:id {status: <new>}`. Optimistic update with rollback on error.
- Filter bar at top: status multi-select, min grade select.

**`KanbanColumn.tsx`** — stateless, accepts `{title, applications[], onMove}`.

**`ApplicationCard.tsx`** — accepts `{application, evaluation}`; renders the job title + grade + actions (Open job, Edit notes, Delete).

### 5.12 Frontend — Scan UI

**`ScansPage.tsx`** at `/scans`:
- List of user's scan configs with last-run status badges.
- "New scan config" button → opens `ScanConfigEditor` modal.
- Each row: "Run now" button → `POST /scan-configs/:id/run` → redirects to `/scans/:id` (scan detail page showing progress).

**`ScanDetailPage.tsx`** at `/scans/:id`:
- Top section: config summary + edit button.
- Tabs: "Latest run" (results table with relevance scores) / "History" (list of past runs).
- "Evaluate all" button on a completed run → `POST /batch-runs {scan_run_id}` → opens `BatchProgressCard` modal or inline panel that polls.
- Uses `usePolling` hook when run status is `pending`/`running`.

**`ScanConfigEditor.tsx`** modal:
- Form fields: name, companies (add/remove rows with name+platform+slug), keywords, exclude_keywords.
- On save: `POST` or `PUT` `/scan-configs`.
- "Add company" → dropdown to pick platform + slug input; auto-validate slug by hitting the platform's API in preview mode (optional stretch).

**`BatchProgressCard.tsx`**:
- Props: `{batchRunId}`.
- Polls `GET /batch-runs/:id` every 3s via `usePolling`.
- Shows 4-stage progress bar (L0 → L1 → L2 → done) with counters.
- On `status='completed'`: renders a sortable table of top 10 evaluations by grade, each with "Save to pipeline" + "Tailor CV" buttons.
- On `status='failed'`: shows error + "Retry" button.

**`ScanProgressCard.tsx`**:
- Props: `{scanRunId, scanName}`.
- Polls `GET /scan-runs/:id` every 3s.
- Shows "Scraping [N] companies…" → "Classifying [M] listings…" → transition to `ScanResultsCard` on completion.

**`ScanResultsCard.tsx`**:
- Shows `jobs_found`, `jobs_new`, and top 5 highest-relevance listings with `relevance_score`.
- "Evaluate all" button at bottom.
- "View all results" link → navigates to `/scans/:scan_config_id`.

### 5.13 Frontend — Applications API client + polling

`lib/api.ts` adds:
```typescript
api.scanConfigs = {
  list: () => request<{data: ScanConfig[]}>('GET', '/api/v1/scan-configs'),
  create: (body) => request<{data: ScanConfig}>('POST', '/api/v1/scan-configs', body),
  update: (id, body) => request<{data: ScanConfig}>('PUT', `/api/v1/scan-configs/${id}`, body),
  delete: (id) => request<void>('DELETE', `/api/v1/scan-configs/${id}`),
  run: (id) => request<{data: {scan_run_id: string, status: string}}>('POST', `/api/v1/scan-configs/${id}/run`, {}),
};
api.scanRuns = {
  list: () => request<{data: ScanRun[]}>('GET', '/api/v1/scan-runs'),
  get: (id) => request<{data: {scan_run: ScanRun, results: ScanResult[]}}>('GET', `/api/v1/scan-runs/${id}`),
};
api.batchRuns = {
  create: (body) => request<{data: BatchRun}>('POST', '/api/v1/batch-runs', body),
  list: () => request<{data: BatchRun[]}>('GET', '/api/v1/batch-runs'),
  get: (id) => request<{data: BatchRunDetail}>('GET', `/api/v1/batch-runs/${id}`),
};
api.applications = {
  list: (filters) => request<{data: Application[]}>('GET', `/api/v1/applications?${qs(filters)}`),
  create: (body) => request<{data: Application}>('POST', '/api/v1/applications', body),
  update: (id, body) => request<{data: Application}>('PUT', `/api/v1/applications/${id}`, body),
  delete: (id) => request<void>('DELETE', `/api/v1/applications/${id}`),
};
```

`lib/polling.ts`:
```typescript
export function usePolling<T>(
  fetcher: () => Promise<T>,
  intervalMs: number,
  shouldStop: (latest: T) => boolean,
): {data: T | null, error: Error | null}
```

---

## 6. Testing strategy

**Unit tests** (`tests/unit/`):

- `test_l0_filter.py` — 10+ cases: location match (remote, aliases, mismatch), salary floor (posted/not-posted/below/above), seniority ladder, missing-data pass.
- `test_content_hash_dedup.py` — same text → same hash; trivial whitespace ignored; different requirements → different hash.
- `test_greenhouse_adapter.py` — fixture **JSON** (Greenhouse boards API shape; job `content` may be HTML strings) → normalized `ListingPayload[]`.
- `test_ashby_adapter.py` — fixture JSON (Ashby API) → normalized.
- `test_lever_adapter.py` — fixture JSON (Lever API) → normalized.
- `test_relevance_scorer.py` — fake Gemini returns `0.85` text → parsed as `0.85`; garbage → `0.0`; timeout → `0.0`.
- `test_default_scan_config.py` — seed is idempotent; creates exactly 15 companies.
- `test_agent_scan_tool.py` — tool creates scan_run row + sends Inngest event (mock); returns progress card.
- `test_agent_batch_tool.py` — same for batch, with all three input modes.

**Integration tests** (`tests/integration/`):

- `test_scan_configs_crud.py` — full CRUD, user scoping, paywall gating on POST/PUT/run.
- `test_scan_runs_trigger_inngest.py` — `POST /scan-configs/:id/run` creates scan_run row and sends the Inngest event (mocked).
- `test_scanner_service_end_to_end.py` — with all 3 adapters mocked via `respx`, run `ScannerService.run_scan`, assert jobs inserted, scan_results written, status=completed.
- `test_scanner_service_one_adapter_fails.py` — one adapter 500s; scan still completes with the other 2's results.
- `test_scanner_service_500_cap.py` — feed >500 listings; assert `truncated=true` and exactly 500 results.
- `test_batch_runs_create_job_urls.py` — create batch from `job_urls[]` (job_parser mocked), progresses through L0/L1/L2.
- `test_batch_runs_create_job_ids.py` — create from pre-existing job_ids.
- `test_batch_runs_create_scan_run_id.py` — create from completed scan; 409 if scan still running.
- `test_batch_runs_l0_filters.py` — jobs failing L0 land in `batch_items.stage='filtered'` with `filter_reason`.
- `test_batch_runs_l1_filters.py` — jobs scoring below threshold filtered out.
- `test_batch_runs_l2_evaluates.py` — jobs surviving L1 get full evaluations via fan-out.
- `test_applications_crud.py` — CRUD, user scoping, status transitions, uniqueness on (user_id, job_id).
- `test_applications_filters.py` — `?status=applied&min_grade=B` filter behavior.
- `test_default_scan_config_seeded_on_onboarding.py` — profile transitions to `done` → default config exists with 15 companies.
- `test_agent_scan_flow.py` — end-to-end: user message "scan for jobs" → classifier → tool → Inngest event → poll → card.
- `test_agent_batch_flow.py` — end-to-end similarly.
- `test_phase2c_smoke.py` — the big one: onboarding → scan → batch → save to pipeline → kanban reflects.

**Frontend tests** (`user-portal/src/`):

- `ScansPage.test.tsx` — renders list from mocked API, "Run scan" calls POST.
- `ScanDetailPage.test.tsx` — renders progress during pending, results on completion (mocked polling).
- `ScanConfigEditor.test.tsx` — form create + edit + validation; saves via POST / PUT.
- `PipelinePage.test.tsx` — renders 6 columns from mocked applications; drag-drop fires PUT.
- `BatchProgressCard.test.tsx` — polls, shows counters, transitions to results view.
- `ScanProgressCard.test.tsx` — polls, transitions to ScanResultsCard.
- `ApplicationCard.test.tsx` — renders job title, grade badge, action buttons.

**Fake Inngest strategy:** no real Inngest dev server in tests. Mock `inngest_client.send` to return a `{"ids": ["evt_test_..."]}` stub. Run the functions **directly** as plain async calls from integration tests, bypassing Inngest step durability. Separate `test_inngest_serve_endpoint.py` confirms the `POST /inngest` route responds and registers functions correctly.

**Fake scrapers:** Each adapter test uses `respx` to mock `boards-api.greenhouse.io`, `api.ashbyhq.com`, `api.lever.co`. Store fixtures as **`.json`** mirroring each vendor’s HTTP API; Greenhouse responses may include **HTML inside JSON fields** (normalized with `markdownify` in the adapter). Real platform calls only happen in an opt-in nightly smoke job.

**Total:** ~35 new backend tests + 7 frontend tests. Running total after 2c: **134+ backend tests, 16 frontend tests**.

---

## 7. Environment variables

Added to `backend/.env.example`:

```bash
# Phase 2c — Inngest
INNGEST_EVENT_KEY=                       # Empty in dev; populated from Inngest Cloud in prod
INNGEST_SIGNING_KEY=                     # Empty in dev; required in prod
INNGEST_DEV=1                            # 1 in dev to use the local dev server
FEATURE_SCAN_SCHEDULING=false            # Ignored in 2c; reserved for Phase 5

# Phase 2c — Scanning limits
SCAN_MAX_LISTINGS_PER_RUN=500
SCAN_BOARD_RATE_LIMIT_REQS_PER_SEC=1
SCAN_L1_CONCURRENCY=5
BATCH_L2_CONCURRENCY=10
BATCH_L1_RELEVANCE_THRESHOLD=0.5
```

Frontend `.env.example`: no changes (uses `VITE_API_URL` for all new endpoints).

`docker-compose.yml`: the existing `inngest` service is moved out of the `profiles: ["inngest"]` gate and becomes part of the default `up` flow, so Phase 2c backend talks to it without extra steps.

---

## 8. Decisions log — the 8 locked choices

| # | Question | Decision | Rationale |
|---|---|---|---|
| **D1** | Scope split | Single Phase 2c plan: scanning + batch + pipeline | Shared infra (Inngest, migration, Gemini L1), tightly-coupled data flow. Splitting creates fake seams. |
| **D2** | Scheduled scans | **Manual only** — `schedule` column persisted but ignored | No cron, no DST bugs, no trial-state cron edge cases. Revisit in Phase 5. |
| **D3** | Default scan config | **All 15 companies from parent Appendix M seeded at onboarding, but NOT auto-run.** User must explicitly click "Run scan" or ask the agent to scan. | Day-1 demo-ready (config is there) with zero first-session cost. No hidden charges at signup. |
| **D3b** | Scan cost guard | **500-listing hard cap per scan run** | Prevents runaway cost on blockbuster hiring days. Surfaces as `truncated=true` flag. |
| **D4** | Agent tool wiring | **`start_job_scan` + `start_batch_evaluation` wired in 2c** | Full agent-first UX. `BatchProgressCard` polls; same for `ScanProgressCard`. |
| **D5** | Batch input modes | **All 3: `job_urls[]`, `job_ids[]`, `scan_run_id`** | Minimal extra code; covers every natural user phrase. |
| **D6** | Frontend scope | **Full CRUD: ScansPage, ScanDetailPage, ScanConfigEditor, PipelinePage** | Complete feature; pipeline kanban enables real workflow. |
| **D7** | `applications` table timing | **Moves from Phase 2d → Phase 2c** | Pipeline kanban needs it. Phase 2d shrinks to interview prep + negotiation + feedback. |
| **D8** | Card action buttons | **Direct REST calls (B1)**, not agent-action routing | `/conversations/:id/actions` stays Phase 5. Card buttons in 2c call `POST /applications` directly. |

---

## 9. Open questions (resolved inline)

1. *What happens when Inngest dev server is down in local dev?* → `POST /scan-configs/:id/run` creates the `scan_runs` row but the event send fails. Return `503 INNGEST_UNAVAILABLE` and mark `scan_runs.status='failed'`. User sees a clear error.
2. *What if a user edits a scan config while a run is in progress?* → The in-flight run uses the config snapshot passed via the Inngest event payload, not the live DB row. Future runs use the new config.
3. *Content hash for jobs scraped from two different boards (same company, different slugs)?* → Content hash is based on description + requirements, not source URL. Duplicates across boards correctly converge to one `jobs` row.
4. *Relevance threshold on scan?* → Scan runs L1 on every listing but does **not** filter by threshold; all listings land in `scan_results` with their score. Filtering happens client-side (UI shows top-by-score, user can drill down). The threshold (0.5 by default) only matters for the **batch** L1 stage, where we need to cut cost before L2.
5. *What if a batch has 0 jobs surviving L1?* → `batch_run.status='completed'`, `l2_evaluated=0`. UI shows "No strong matches" with an option to re-batch with a lower threshold.
6. *User cancels a running batch?* → Out of scope for 2c. Inngest functions aren't cancelable mid-flight via our API; user just waits. Add a cancel path in Phase 5 if needed.
7. *Applications for jobs that get deleted from the `jobs` pool?* → Shouldn't happen (jobs pool is append-only in 2c). If it did, `ON DELETE CASCADE` on the FK removes the application row. Alternative would be `SET NULL`, but we don't expect deletion.
8. *Scan config edits — does deleting a company from the config affect past scan results?* → No. Historical `scan_results` rows reference the jobs, not the config. Editing the config only affects the next run.

---

## 10. Unit economics — scan cost envelope

**Scan cost per run:**
- Scraping: free (public APIs).
- L1 Gemini: ~$0.0003 per listing. At 500 listings max, worst case **$0.15 per scan**.
- No L2 during scan.

**Batch cost per run (depends on filter pass-through):**
- L0: free.
- L1: ~$0.0003 per job that survives L0.
- L2: ~$0.04 per job that survives L1 (Claude Sonnet full 10-dim eval).
- Worst case (100 jobs, all pass L0 + L1): 100 × ($0.0003 + $0.04) ≈ **$4.03**.
- Typical case (100 jobs, 50% pass L0, 40% of those pass L1): 100 × $0.0003 + 50 × $0.0003 + 20 × $0.04 = $0.82.

**Monthly envelope at $4.99 ARPU:**
- User does 4 scans/month + 2 batches/month: 4 × $0.15 + 2 × $0.82 = **$2.24** (~45% of ARPU).
- Plus the existing 2a evaluation + CV costs. Thin margins remain the real concern.

**Phase 2c still does not enforce `plan_monthly_cost_cap_cents`** (the Phase 2b column stays NULL). But the L0/L1 filter + 500-listing cap provide natural cost containment. If telemetry shows abuse, turn on the cost cap in a focused follow-up.

---

## 11. Out of scope (explicit)

- Scheduled scans (cron / Inngest cron trigger).
- LinkedIn, Workday, SmartRecruiters scrapers.
- Playwright-based JS-rendered site scraping.
- Batch cancellation mid-flight.
- Interview prep + negotiation (Phase 2d).
- `feedback` table + `POST /evaluations/:id/feedback` (Phase 2d).
- `POST /conversations/:id/actions` card action routing (Phase 5).
- Conversation summarization (Phase 5).
- Real AWS deployment of Inngest functions (Phase 5).
- Admin dashboards for scan health / cost breakdown (Phase 5).
- Per-user scan quotas beyond the 500-listing cap.
- **`negotiations` table**, **foreign key** on `applications.negotiation_id` → `negotiations(id)`, and negotiation-module writes to that column (Phase 2d). **Phase 2c still adds** `applications.negotiation_id` as a **nullable UUID without FK** (see §3) so Phase 2d does not need a column-only migration.

---

## 12. Risks

| Risk | Mitigation |
|---|---|
| Scraped platform changes JSON schema | Each adapter has its own test fixture + adapter unit test. Nightly smoke job detects drift. Failure of one adapter doesn't kill the whole scan. |
| Inngest dev server flaky in local dev | `docker-compose` brings it up by default; `POST /scan-configs/:id/run` returns 503 if event send fails, with a clear error message. |
| Inngest signing key missing or wrong in production | Unauthorized callers could hit `/api/v1/inngest`. Enforce signing verification; use secrets management; see §2.3. |
| L1 relevance misclassifies (false negatives filter out good jobs) | Users can re-batch with `BATCH_L1_RELEVANCE_THRESHOLD` env override. No per-user override in 2c (Phase 5). |
| Long-running batch during trial expiry | Trial-state is checked at tool-call time (before Inngest event), not during the async run. Once a batch is in flight, it completes even if trial expires mid-run. |
| 500-listing cap hides strong matches | Warning surfaced via `scan_runs.truncated=true`; UI shows banner suggesting keyword filtering. |
| Applications CRUD drift vs evaluations link | FK is `SET NULL`, so evaluation deletion doesn't break applications. Status transitions are user-controlled, no server-enforced state machine (by design — users may want to revisit rejected apps). |
| Kanban drag-drop optimistic update + server failure | Frontend rollback on failure + toast error. Standard pattern. |
| Scan + batch + pipeline in one cycle is a lot of code | Vertical slice order (scan → batch → pipeline) means the plan has natural checkpoints. Each slice is independently mergeable. |
| `inngest` Python SDK is under `<0.5` and APIs shift | Pin to `>=0.4,<0.5` in pyproject; upgrade deliberately. |

---

## 13. References

- Parent spec Appendix F (Inngest function signatures), Appendix M (default scan config), Appendix D.5 (L1 relevance prompt), Appendix D.8 (L0 rule filter), Appendix G (card payload schemas).
- Phase 2a spec: [`2026-04-10-phase2a-agent-eval-cv-design.md`](./2026-04-10-phase2a-agent-eval-cv-design.md) — evaluation service reused as-is in batch L2.
- Phase 2b spec: [`2026-04-10-phase2b-stripe-billing-design.md`](./2026-04-10-phase2b-stripe-billing-design.md) — `EntitledDbUser` dependency applied to new cost-generating endpoints.

---

*End of spec.*
