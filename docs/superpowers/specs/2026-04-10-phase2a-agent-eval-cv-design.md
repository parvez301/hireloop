# CareerAgent Phase 2a — Agent + Evaluation + CV Optimization (Design Spec)

> **Parent spec:** [`2026-04-10-careeragent-design.md`](./2026-04-10-careeragent-design.md). This document is a **delta spec** — it does not repeat anything already defined in the parent. Read the parent first.
>
> **Predecessor plan:** [`plans/2026-04-10-phase1-foundation.md`](../plans/2026-04-10-phase1-foundation.md) (foundation — users, profiles, resume upload, CDK stubs, frontend skeletons). Phase 1 is **done and on disk**; Phase 2a builds on top of it without modifying Phase 1 contracts.
>
> **Successor:** Phase 2b (Stripe billing + trial gating) — [`2026-04-10-phase2b-stripe-billing-design.md`](./2026-04-10-phase2b-stripe-billing-design.md); implementation plan [`plans/2026-04-10-phase2b-stripe-billing.md`](../plans/2026-04-10-phase2b-stripe-billing.md).

---

## 1. Goal

Ship the **LangGraph agent** and its first two real tools — **Job Evaluation** (Module 1) and **CV Optimization + PDF generation** (Module 2) — end-to-end, backed by a minimum-viable chat UI in `user-portal` so the whole flow is dogfoodable from a browser.

**End state:** A logged-in Phase 1 user can

1. Open the user portal, land on a chat page.
2. Send a message like *"Evaluate this job for me: https://boards.greenhouse.io/stripe/jobs/123"*.
3. Watch the agent classify → route → call `evaluate_job` → return a structured **Evaluation card** with grade A–F, rule-based + Claude-reasoned dimensions, reasoning, and red flags.
4. Follow up with *"Tailor my CV for that job"*, watch the agent call `optimize_cv` → return a **CV Output card** with a 15-minute signed S3 URL for a real PDF rendered by the Fastify/Playwright `pdf-render` service.
5. See every turn persisted in `conversations` + `messages`, and every LLM call logged to `usage_events`.

**Non-goals (explicitly out of scope for 2a):**

- Stripe billing and paywall enforcement — deferred to Phase 2b. All users in 2a are implicitly on an unlimited trial (no `require_active_subscription` middleware).
- Job Scanning, Batch Processing, Interview Prep, Negotiation modules (Phases 2c and 2d).
- Inngest functions of any kind — every Phase 2a endpoint is synchronous.
- Real AWS deployment — `pdf-render` runs as a docker-compose service locally; CDK stack for it is stubbed in Phase 1 but not deployed.
- Polished user-portal UX (pipeline kanban, CV list page, settings tabs, slash commands, quick-action chips, card action buttons). Phase 2a ships **just enough UI** to exercise the backend: one chat page, basic message list, basic card renderers for the two card types. Polish is Phase 5.
- Admin UI changes. Admin UI remains the Phase 1 stub.

---

## 2. Architecture delta

Phase 1 left the backend organised as:

```
backend/src/career_agent/
├── api/         auth, deps, errors, health, profile
├── integrations/cognito, s3
├── models/      base, user, subscription, profile, star_story
├── schemas/     (phase 1 schemas)
├── services/    auth, profile, resume_parser, storage
├── config.py
├── db.py
├── logging.py
└── main.py
```

Phase 2a adds:

```
backend/src/career_agent/
├── api/
│   ├── conversations.py          [NEW]  POST/GET conversations + /messages + /stream SSE
│   ├── evaluations.py            [NEW]  POST/GET evaluations + /feedback
│   ├── cv_outputs.py             [NEW]  POST/GET cv-outputs + /pdf
│   └── jobs.py                   [NEW]  POST /jobs/parse (URL → structured job)
├── core/
│   ├── __init__.py               [NEW]
│   ├── agent/
│   │   ├── __init__.py           [NEW]
│   │   ├── classifier.py         [NEW]  L0 Gemini Flash intent classifier
│   │   ├── graph.py              [NEW]  LangGraph state graph construction
│   │   ├── prompts.py            [NEW]  System prompt + classifier prompt constants
│   │   ├── state.py              [NEW]  AgentState TypedDict (Appendix E.1)
│   │   ├── tools.py              [NEW]  evaluate_job + optimize_cv langchain tools (2 only)
│   │   ├── runner.py             [NEW]  Async entrypoint: run_turn(conversation, user_msg) → stream
│   │   └── usage.py              [NEW]  Token/cost accounting helpers → usage_events
│   ├── evaluation/
│   │   ├── __init__.py           [NEW]
│   │   ├── job_parser.py         [NEW]  URL/raw → structured job (html fetch + Gemini structure)
│   │   ├── rule_scorer.py        [NEW]  4 rule-based dimensions (skills, exp, location, salary)
│   │   ├── claude_scorer.py      [NEW]  6 Claude dimensions via Appendix D.3 prompt
│   │   ├── grader.py             [NEW]  Weighted aggregate → A–F grade (Appendix C)
│   │   ├── cache.py              [NEW]  evaluation_cache read/write by content_hash
│   │   └── service.py            [NEW]  Orchestrator: parse → cache → score → persist
│   ├── cv_optimizer/
│   │   ├── __init__.py           [NEW]
│   │   ├── optimizer.py          [NEW]  Claude Sonnet CV rewriter (Appendix D.4 prompt)
│   │   ├── render_client.py      [NEW]  HTTP client for pdf-render service
│   │   └── service.py            [NEW]  Orchestrator: load resume → rewrite → render → persist
│   └── llm/
│       ├── __init__.py           [NEW]
│       ├── anthropic_client.py   [NEW]  Shared Claude client with prompt caching
│       ├── gemini_client.py      [NEW]  Shared Gemini Flash client
│       └── errors.py             [NEW]  LLMError, LLMTimeoutError, LLMQuotaError
├── integrations/
│   └── pdf_render.py             [NEW]  Typed HTTP wrapper around the render service
├── models/
│   ├── job.py                    [NEW]
│   ├── evaluation.py             [NEW]  + EvaluationCache
│   ├── cv_output.py              [NEW]
│   ├── conversation.py           [NEW]  + Message
│   └── usage_event.py            [NEW]
├── schemas/
│   ├── agent.py                  [NEW]  Message/Card/StreamEvent pydantic schemas
│   ├── job.py                    [NEW]
│   ├── evaluation.py             [NEW]
│   ├── cv_output.py              [NEW]
│   └── conversation.py           [NEW]
└── services/
    ├── conversation.py           [NEW]  CRUD over conversations + messages
    └── rate_limit.py             [NEW]  Redis token bucket (10 msg/min per user)
```

The user-portal also grows (minimum viable only):

```
user-portal/src/
├── lib/
│   ├── api.ts                    [NEW]  Fetch client with Cognito auth header
│   └── sse.ts                    [NEW]  EventSource wrapper for /stream
├── pages/
│   └── ChatPage.tsx              [NEW]  Single chat page — the only new route
├── components/
│   ├── chat/
│   │   ├── MessageList.tsx       [NEW]
│   │   ├── InputBar.tsx          [NEW]
│   │   └── cards/
│   │       ├── EvaluationCard.tsx [NEW]
│   │       └── CvOutputCard.tsx   [NEW]
│   └── layout/
│       └── AppShell.tsx          [NEW]  Header + nav shell (minimal)
└── App.tsx                       [MODIFY]  Route `/` → ChatPage (auth-gated)
```

The `pdf-render/` workspace graduates from Phase 1 **stub** to real service:

```
pdf-render/src/
├── server.ts                     [REPLACE]  Fastify w/ POST /render + GET /health
├── render.ts                     [REPLACE]  markdown → html → Playwright → buffer
├── s3.ts                         [NEW]      Upload buffer to S3 (or LocalStack)
├── templates/
│   └── resume.html               [NEW]      Handlebars template (Space Grotesk + DM Sans)
└── auth.ts                       [NEW]      Bearer shared-secret middleware
pdf-render/test/
├── render.spec.ts                [NEW]      Unit test: markdown → html + Playwright smoke
└── server.spec.ts                [NEW]      Integration: POST /render roundtrip
```

### 2.1 Data flow — a single agent turn

```
Browser (ChatPage)
  │
  │  POST /api/v1/conversations/{id}/messages  { content }
  │  + Cognito JWT
  ▼
FastAPI route (conversations.py::send_message)
  │
  │  1. rate_limit.check(user_id)                    → Redis token bucket
  │  2. conversation_service.append_user_message()   → insert into messages
  │  3. await runner.run_turn(conversation, user, body)
  ▼
core.agent.runner
  │
  │  a. classifier.classify(user_msg)                → Gemini Flash (OFF_TOPIC short-circuits)
  │  b. build AgentState (profile summary, subscription="trial", trial_days=None)
  │  c. graph.ainvoke(state)                         → LangGraph
  │       └── route_node           → Claude Sonnet (tools bound)
  │       └── ToolNode             → evaluate_job / optimize_cv
  │             ├── evaluation.service.evaluate()
  │             └── cv_optimizer.service.optimize()  → pdf_render.render()
  │       └── respond_node         → Claude Sonnet (final text + cards)
  │  d. usage.record_turn(state.model_calls)         → insert into usage_events
  │  e. conversation_service.append_assistant_message(content, cards, metadata)
  │
  ▼
Route yields a StreamingResponse:
  event: token          (Claude streamed tokens)
  event: tool_start     ({"tool": "evaluate_job"})
  event: tool_end       ({"tool": "evaluate_job", "ok": true})
  event: card           ({"type": "evaluation", "data": {...}})
  event: done           ({"message_id": "msg_..."})
```

The non-streaming `POST /api/v1/conversations/{id}/messages` endpoint returns the same final assembled message (content + cards) for clients that don't want SSE. SSE is delivered over `GET /api/v1/conversations/{id}/stream?pending=msg_...` — the same `run_turn` result is multiplexed. See §5.1 for the exact streaming contract.

### 2.2 Key architectural decisions (Phase 2a only)

| Decision | Choice | Why |
|---|---|---|
| Agent framework | **LangGraph** (already in Phase 1 deps) | Parent spec Appendix E mandates it; no need to reopen. |
| Classifier | **Gemini 1.5 Flash** via `google-generativeai` SDK | Cheap pre-filter; matches parent spec. One-shot prompt, no chain. |
| Router LLM | **Claude Sonnet 4** via `langchain-anthropic` + direct `anthropic` SDK for prompt caching | LangChain handles tool binding and streaming; direct SDK call used only when we need `cache_control: ephemeral` on the system prompt. |
| Prompt caching | Enabled by default via `ANTHROPIC_BETA=prompt-caching-2024-07-31` header and `cache_control` on the static framework block of each prompt (system prompt, eval framework, CV rules) | Parent spec §2 Cost Structure depends on this to hit margins. |
| Streaming | FastAPI `StreamingResponse` with `text/event-stream`, one event per line | No websockets in Phase 2a; SSE is simpler, works with Cognito bearer token, and doesn't require connection upgrades through ALB. |
| Tool-call loop | Single round of tools per turn (no multi-hop). The agent either calls 0 or 1 tool, then responds. | Keeps latency bounded; matches the only two tools we ship. Multi-hop is deferred until we have enough tools to need chaining. |
| Rate limiting | Redis token bucket keyed `rl:user:{user_id}`, 10 tokens, 6s refill | Parent spec §API Design. Bucket is created lazily; no migration. |
| Idempotency | `POST /api/v1/evaluations` and `POST /api/v1/cv-outputs` accept an `Idempotency-Key` header. Implementation: Redis SETNX on `idem:{user_id}:{key}` with 24h TTL; cache the 200 response body. | Parent spec §Idempotency. Conversations endpoints are **not** idempotent (each message is a new turn). |
| PDF rendering | **Fastify + Playwright** as a separate service on port 4000, called over HTTP with a shared-secret bearer token | Parent spec Appendix N. Can't run in Lambda (Chromium >250 MB). Local dev: docker-compose service. |
| PDF storage | Service uploads to S3 (or LocalStack in dev), returns `s3_key`. Backend stores the key, generates signed URL on demand. | Keeps backend stateless wrt rendering; PDF is re-downloadable until the `cv_outputs` row is deleted. |
| Conversation memory | Full message history replayed into the agent every turn, no summarization yet. Hard cap at 20 prior messages. Tokens past that are dropped silently. | YAGNI — summarization is Phase 5 territory. 20 messages is ~10 user turns which is plenty for 2a. |
| Trial gating | No-op. `deps.get_current_user` remains; no `require_active_subscription` dependency exists yet. | 2b will add it and apply it to the endpoints 2a creates. |
| Anthropic model ID | `claude-sonnet-4-6` (from `CLAUDE_MODEL` env var, default per Phase 1 `.env.example`) | Matches knowledge cutoff + Phase 1 settings. |
| Gemini model ID | `gemini-2.0-flash-exp` (from `GEMINI_MODEL` env var) | Matches Phase 1 `.env.example`. |

---

## 3. Data model delta

A single new Alembic migration: `backend/migrations/versions/0002_phase2a_agent_eval_cv.py`.

**New tables (all `tenant_id`-free — CareerAgent is single-tenant-per-user; scoping is by `user_id`):**

| Table | Columns (beyond id + timestamps) | Notes |
|---|---|---|
| `jobs` | `content_hash`(uniq), `url`, `title`, `company`, `location`, `salary_min`, `salary_max`, `employment_type`, `seniority`, `description_md`, `requirements_json`, `source`, `board_company`, `discovered_at`, `expires_at` | Shared pool, not scoped by user. `source='manual'` for 2a (scanner-discovered rows arrive in Phase 2c). |
| `evaluations` | `user_id` FK, `job_id` FK, `overall_grade`, `dimension_scores` JSONB, `reasoning`, `red_flags` JSONB, `personalization`, `match_score`, `recommendation`, `model_used`, `tokens_used`, `cached` BOOL, **UNIQUE(user_id, job_id)** | |
| `evaluation_cache` | `content_hash` FK UNIQUE, `base_evaluation` JSONB, `requirements_json` JSONB, `model_used`, `hit_count` | Only stores the **4 Claude dimensions** — rule-based dimensions are recomputed per user since they depend on profile. |
| `cv_outputs` | `user_id` FK, `job_id` FK, `tailored_md`, `pdf_s3_key`, `changes_summary`, `model_used` | No uniqueness constraint — users may regenerate. Most recent per (user, job) wins in list views. |
| `conversations` | `user_id` FK, `title` | `title` is auto-set from first user message (first 50 chars) if null. |
| `messages` | `conversation_id` FK, `role` (`user`/`assistant`), `content`, `tool_calls` JSONB, `cards` JSONB, `metadata` JSONB (`{model, tokens_in, tokens_out, cost_cents, classifier_intent}`) | |
| `usage_events` | `user_id` FK, `event_type`, `tokens_used`, `cost_cents`, plus `model` and `module` VARCHARs | `event_type` ∈ {`classify`, `evaluate`, `optimize_cv`, `respond`}. Used by admin cost dashboards later. |

**Indexes** are created in the same migration, copied verbatim from parent spec Appendix H for each of the seven tables above. Nothing else in Appendix H changes.

**What is NOT created in 0002** (remains absent until later phases): `scan_configs`, `scan_runs`, `scan_results`, `batch_runs`, `batch_items`, `interview_preps`, `negotiations`, `applications`, `notifications`, `feedback`.

### 3.1 A note on `evaluation_cache`

The parent spec is ambiguous on whether the cache stores the full evaluation or just the reasoning dimensions. **Decision for 2a:** cache stores the 6 Claude dimensions only (`{dimensions, overall_reasoning, red_flag_items, personalization_notes}`). Rule-based dimensions and the final grade are recomputed per user on every call because they depend on `profile.target_locations`, `profile.min_salary`, and the resume skill set — none of which are stable across users. Cache key is `SHA256(normalize(job.description_md + job.requirements_json))`.

This decision is documented in the cache docstring and enforced in `cache.py::put`.

---

## 4. API delta

All endpoints under `/api/v1`. All require `Authorization: Bearer <cognito_jwt>`. All scoped by `user_id` in the service layer.

### 4.1 Conversations + messages

| Method | Path | Body / Params | Response |
|---|---|---|---|
| `POST` | `/conversations` | `{ "title": string? }` | `201 { "data": Conversation }` |
| `GET`  | `/conversations` | `?limit=20&cursor=...` | `200 { "data": Conversation[], "meta": {next_cursor} }` |
| `GET`  | `/conversations/:id` | — | `200 { "data": { conversation, messages: [...last 50...] } }` |
| `DELETE` | `/conversations/:id` | — | `204` |
| `POST` | `/conversations/:id/messages` | `{ "content": string }` (1–4000 chars) | `200 { "data": AssistantMessage, "meta": {tokens_used, cost_cents} }` — blocking, returns the completed assistant turn. |
| `GET`  | `/conversations/:id/stream` | `?pending=msg_...` | `200 text/event-stream` — see §5.1. |

**Out of scope for 2a:** `POST /conversations/:id/actions` (card button callbacks). Cards in 2a are **display-only** in the UI; follow-up actions happen by the user typing a new message. Action routing ships in Phase 5.

### 4.2 Jobs

| Method | Path | Body | Response |
|---|---|---|---|
| `POST` | `/jobs/parse` | `{ "url": string } \| { "description_md": string }` | `200 { "data": Job }` — parses but does **not** persist. Returns a transient Job payload. |

This endpoint is used both by the frontend (preview-before-evaluate flow, Phase 5) and by `evaluate_job_tool` (it calls the service directly, not the HTTP route).

### 4.3 Evaluations

| Method | Path | Body | Response |
|---|---|---|---|
| `POST` | `/evaluations` | `{ "job_url": string?, "job_description": string? }` (exactly one required) | `200 { "data": Evaluation, "meta": { cached, tokens_used, cost_cents } }` |
| `GET`  | `/evaluations` | `?grade=A&since=...&limit=20&cursor=...` | `200 { "data": Evaluation[], "meta": {next_cursor} }` |
| `GET`  | `/evaluations/:id` | — | `200 { "data": Evaluation }` |


> **Deferred:** `POST /evaluations/:id/feedback` is **not** in the 2a surface. It requires the `feedback` table, which is scheduled for Phase 2d. The parent spec lists it; 2a explicitly skips it.

Accepts `Idempotency-Key` header on `POST /evaluations`.

### 4.4 CV outputs

| Method | Path | Body | Response |
|---|---|---|---|
| `POST` | `/cv-outputs` | `{ "job_id": uuid }` | `200 { "data": CvOutput, "meta": {...} }` |
| `POST` | `/cv-outputs/:id/regenerate` | `{ "feedback": string? }` | `200 { "data": CvOutput, "meta": {...} }` |
| `GET`  | `/cv-outputs` | `?limit=20&cursor=...` | `200 { "data": CvOutput[] }` |
| `GET`  | `/cv-outputs/:id` | — | `200 { "data": CvOutput }` |
| `GET`  | `/cv-outputs/:id/pdf` | — | `302` redirect to signed S3 URL (15 min expiry). |

Accepts `Idempotency-Key` on `POST`.

### 4.5 Error envelope

Unchanged from Phase 1 (`{"error": {"code", "message", "request_id"}}`). Add these Phase 2a codes:

| Code | HTTP | When |
|---|---|---|
| `RATE_LIMITED` | 429 | Token bucket empty |
| `LLM_TIMEOUT` | 504 | Anthropic/Gemini call exceeded 60 s |
| `LLM_QUOTA_EXCEEDED` | 503 | Provider returned 429 |
| `JOB_PARSE_FAILED` | 422 | URL fetch or structure extraction failed |
| `PDF_RENDER_FAILED` | 502 | pdf-render service returned `success: false` or HTTP 5xx |
| `CONVERSATION_NOT_FOUND` | 404 | id does not belong to user |
| `EVALUATION_REQUIRES_JOB` | 422 | `/cv-outputs` called with a `job_id` the user has not evaluated |

---

## 5. Component designs

### 5.1 Agent (`core/agent/`)

#### State (Appendix E.1, unchanged)

Copy verbatim from parent Appendix E.1. In 2a, `subscription_status` is always populated with the literal string `"trial"` and `trial_days_remaining` is always `None`. These fields are written into the state but no node reads them. The 2b implementation will start reading them and wire real values from the `subscriptions` table.

#### Classifier (`classifier.py`)

```python
async def classify(message: str) -> Literal[
    "EVALUATE_JOB", "OPTIMIZE_CV", "SCAN_JOBS", "INTERVIEW_PREP",
    "BATCH_EVAL", "NEGOTIATE", "CAREER_GENERAL", "OFF_TOPIC", "PROMPT_INJECTION"
]:
    """One-shot Gemini Flash call. Returns CAREER_GENERAL on parse failure."""
```

- Timeout: 3 s (fast fail → fall through to `CAREER_GENERAL`).
- Never raises — failures degrade to `CAREER_GENERAL` so the user gets an answer.
- Cost per call is logged to `usage_events` with `event_type="classify"`.

**Short-circuits in the graph:**
- `OFF_TOPIC` → `refuse_off_topic_node` → respond with a canned message (no Claude call, no cost).
- `PROMPT_INJECTION` → log the message for review, return a canned response.
- `SCAN_JOBS`, `INTERVIEW_PREP`, `BATCH_EVAL`, `NEGOTIATE` → these tools **don't exist yet** in 2a. The graph responds with a canned "Not available yet — I can currently evaluate jobs or tailor your CV." message and suggests the user rephrase. Classifier accuracy is intentionally high-recall to route these early.
- `EVALUATE_JOB`, `OPTIMIZE_CV`, `CAREER_GENERAL` → normal router path.

#### Graph (`graph.py`)

Matches parent Appendix E.3 with nodes: `classify → [refuse_off_topic | route] → [tools | respond] → END`. Only two tools are bound: `evaluate_job_tool` and `optimize_cv_tool`.

#### System prompt (`prompts.py`)

Verbatim from parent Appendix D.1, with two line changes for 2a:

1. Items 3–6 of the numbered list (scan/prep/batch/negotiate) remain in the prompt text — we want the agent's self-model to match the product — but the tool manifest bound at runtime only includes `evaluate_job` and `optimize_cv`. If the user asks for a scan or prep, the model replies in natural language (there's no tool to call) and suggests the capability is coming soon.
2. The `TRIAL STATE` section is kept but the variable injection always passes `trial_days_remaining=None` in 2a; the model sees no trial status and never prompts for upgrade. 2b will populate it.

The system prompt is sent as a cached block (`cache_control: ephemeral`) on every Claude call.

#### Tools (`tools.py`)

```python
@tool
async def evaluate_job(
    job_url: str | None = None,
    job_description: str | None = None,
    user_id: str = None,
) -> dict:
    """Evaluate a single job against the user's profile..."""
```

- Implementation delegates directly to `core.evaluation.service.evaluate()`.
- Returns `{"ok": True, "card": EvaluationCardPayload}` on success, `{"ok": False, "error_code": ..., "message": ...}` on failure.
- On failure, the agent's `respond_node` sees the error in the tool result and generates a user-friendly explanation.

```python
@tool
async def optimize_cv(job_id: str, user_id: str = None) -> dict:
    """Generate a tailored resume PDF..."""
```

- Delegates to `core.cv_optimizer.service.optimize()`.
- Tool **requires** an `evaluations` row for `(user_id, job_id)` — if missing, returns `{"ok": False, "error_code": "EVALUATION_REQUIRES_JOB"}`. This mirrors the REST endpoint.

#### Runner (`runner.py`)

```python
async def run_turn(
    *,
    conversation_id: UUID,
    user: User,
    user_message: str,
    emit: Callable[[StreamEvent], Awaitable[None]] | None = None,
) -> AssistantMessage:
    """Run one agent turn. If emit is supplied, stream events during execution."""
```

- Loads the last 20 messages via `conversation_service`.
- Loads a compact profile summary (≈500 tokens) — a helper on `ProfileService`.
- Calls classifier, builds state, invokes graph.
- Every LLM call accumulates into `state["model_calls"]`; runner persists them as `usage_events` at the end.
- Writes the final assistant message to `messages` with `cards`, `tool_calls`, and `metadata`.
- Emits SSE events as the graph runs (classifier done, tool start/end, token stream from Claude, final card, done).

#### SSE stream contract

```
event: classifier
data: {"intent": "EVALUATE_JOB"}

event: token
data: {"delta": "I'll evaluate "}

event: tool_start
data: {"tool": "evaluate_job", "args_preview": {"job_url": "https://..."}}

event: tool_end
data: {"tool": "evaluate_job", "ok": true}

event: card
data: {"type": "evaluation", "data": { ... EvaluationCardPayload ... }}

event: done
data: {"message_id": "msg_abc123", "tokens_used": 4210, "cost_cents": 7}
```

SSE is delivered through `GET /api/v1/conversations/:id/stream?pending=msg_...`. The flow:

1. Client `POST`s the user message.
2. Server creates both the user `messages` row and a **placeholder** assistant row with `role='assistant'`, `content=''`, `metadata={status: 'running'}`, and returns the placeholder's `id` immediately.
3. Client opens SSE connection to `/stream?pending={assistant_msg_id}`.
4. Server runs the turn and streams events; on `done` it updates the assistant row with final content + cards and sets `metadata.status='done'`.
5. Server ends the SSE stream.

If the client is slow/disconnected, the turn still completes server-side; client can re-fetch the conversation via `GET /conversations/:id` and see the final message.

### 5.2 Evaluation (`core/evaluation/`)

#### Flow

```
evaluate(user, job_url? | job_description?)
  │
  │  1. if job_url: job = await job_parser.parse_url(url)
  │     else:       job = await job_parser.parse_description(description_md)
  │
  │  2. persisted_job = await jobs_service.upsert_by_content_hash(job)
  │
  │  3. cache_entry = await cache.get(persisted_job.content_hash)
  │     if cache_entry:
  │         claude_dims = cache_entry.base_evaluation
  │     else:
  │         claude_dims = await claude_scorer.score(persisted_job, profile_summary)
  │         await cache.put(persisted_job.content_hash, claude_dims)
  │
  │  4. rule_dims = rule_scorer.score(persisted_job, profile)
  │
  │  5. aggregate = grader.aggregate(rule_dims, claude_dims)
  │       → { overall_grade, match_score, recommendation, red_flags, reasoning }
  │
  │  6. evaluation = await repo.upsert_unique(user_id, job_id, aggregate, cached_flag)
  │
  │  return evaluation
```

#### `job_parser.py`

- `parse_url(url)` — httpx GET with 10 s timeout, user-agent `CareerAgent/1.0 (+https://careeragent.com/bot)`, follow up to 3 redirects. Pass HTML through BeautifulSoup to strip nav/scripts/styles, then send the first 8000 chars to Gemini Flash with a one-shot "extract Job JSON" prompt (schema: `{title, company, location, salary_min, salary_max, employment_type, seniority, description_md, requirements}`). The raw text is also kept as `description_md` fallback if structure extraction fails.
- `parse_description(description_md)` — same Gemini prompt, no HTTP.
- On any failure → raise `JobParseError(code="JOB_PARSE_FAILED", details=...)`.

#### `rule_scorer.py`

Pure Python, no I/O. Returns:

```python
RuleDimensions(
    skills_match   = DimensionResult(score=0.0..1.0, details=...),
    experience_fit = DimensionResult(...),
    location_fit   = DimensionResult(...),
    salary_fit     = DimensionResult(...),
)
```

- **Skills match:** Jaccard of normalized skills from resume vs. extracted `requirements.skills`. Case-insensitive, stop-word filtered.
- **Experience fit:** parse `"X+ years"` patterns from JD; compare to resume total years (computed from earliest start date to today). Full credit if resume years ≥ required; graduated penalty below.
- **Location fit:** simple set intersection on normalized strings (`remote`, `new york`, `nyc` collapsed). Remote jobs always pass location.
- **Salary fit:** if JD has no salary range → `score=None, skip=True` and the weight is redistributed across the other rule dims. Otherwise `max(0, min(1, (job.salary_max - profile.min_salary) / profile.min_salary))`.

#### `claude_scorer.py`

Single function `async def score(job, profile_summary) -> dict[str, DimensionResult]` that:

1. Builds the cacheable framework block (parent Appendix D.3) — passed as first content block with `cache_control: ephemeral`.
2. Builds the dynamic suffix with the job markdown and profile summary.
3. Calls `anthropic.messages.create` directly (not through LangChain) to use prompt caching.
4. Parses JSON out of the response. Retries once on JSON parse failure with a "JSON only, no prose" reminder.
5. Raises `LLMError` on unrecoverable failure.

#### `grader.py`

```python
def aggregate(rule: RuleDimensions, claude: ClaudeDimensions) -> EvaluationResult:
    weights = {
        "skills_match": 0.15, "experience_fit": 0.10, "location_fit": 0.05, "salary_fit": 0.05,
        "domain_relevance": 0.15, "role_match": 0.15, "trajectory_fit": 0.10,
        "culture_signal": 0.08, "red_flags": 0.10, "growth_potential": 0.07,
    }
    # If salary_fit is skipped, redistribute its 0.05 proportionally across the other 9.
    ...
    score = weighted_sum
    grade = _map_to_letter(score)   # Appendix C mapping
    recommendation = (
        "strong_match" if grade in ("A", "A-") else
        "worth_exploring" if grade.startswith("B") else
        "skip"
    )
    return EvaluationResult(...)
```

#### `cache.py`

- `async def get(content_hash) -> CacheEntry | None` — returns None if not found; on hit, increments `hit_count`.
- `async def put(content_hash, base_evaluation, requirements_json, model_used)` — upsert.
- 30-day TTL enforced at read time: rows older than 30 days are treated as a miss and overwritten on next `put`. (No background deletion job in 2a.)

### 5.3 CV Optimizer (`core/cv_optimizer/`)

#### Flow

```
optimize(user, job_id, feedback=None)
  │
  │  1. evaluation = await evaluation_repo.get_or_404(user_id, job_id)
  │  2. profile    = await profile_service.get(user_id)
  │  3. master_md  = profile.master_resume_md  (or load from S3 if only s3 key exists)
  │
  │  4. keywords   = _extract_keywords(evaluation.dimension_scores)  # from Claude signals
  │
  │  5. result = await optimizer.rewrite(
  │         master_resume_md=master_md,
  │         job_markdown=job.description_md,
  │         keywords=keywords,
  │         additional_feedback=feedback,   # from /regenerate
  │     )
  │     → { tailored_md, changes_summary, keywords_injected, sections_reordered }
  │
  │  6. pdf_key = f"cv-outputs/{user_id}/{uuid4()}.pdf"
  │     render_result = await pdf_render_client.render(
  │         markdown=result.tailored_md,
  │         template="resume",
  │         user_id=user_id,
  │         output_key=pdf_key,
  │     )
  │
  │  7. cv_output = await repo.insert(
  │         user_id, job_id, tailored_md=..., pdf_s3_key=pdf_key,
  │         changes_summary=..., model_used=CLAUDE_MODEL,
  │     )
  │
  │  return cv_output
```

#### `optimizer.py`

- Uses parent Appendix D.4 prompt verbatim.
- Prompt caching: the cacheable prefix is items 1–8 ("RULES:" block). Dynamic suffix is resume + JD + keywords + optional feedback.
- 90 s timeout (CV rewrites are slower than evaluations).
- Output is strict JSON; one retry on parse failure.

#### `render_client.py`

- Typed wrapper around `integrations.pdf_render`.
- 60 s timeout.
- Raises `PdfRenderError(code="PDF_RENDER_FAILED")` on HTTP error or `success: false`.

### 5.4 PDF Render Service (`pdf-render/`)

Replaces the Phase 1 stub with a real Fastify + Playwright service.

#### Stack

- Fastify 5, TypeScript 5, Node 20.
- Playwright 1.48 with Chromium (installed via `npx playwright install --with-deps chromium` at Docker build time).
- `marked` for markdown → HTML.
- `handlebars` for the template shell (inject HTML body + user name into `resume.html`).
- `@aws-sdk/client-s3` for uploads.

#### API

Exactly matches parent Appendix N. Plus:

- **Concurrency:** the service creates **one Chromium browser instance** at startup and reuses it across requests (pages are isolated via `browser.newContext()`). Requests queue behind a semaphore with `max=2` concurrent renders to keep memory bounded.
- **Cold start:** `GET /health` returns `{status, chromium_ready}`. During startup, `chromium_ready=false` until the browser launches.
- **Fonts:** Space Grotesk + DM Sans are embedded as local `.woff2` files in `pdf-render/templates/fonts/` (no external CDN fetch during render — deterministic + airgap-safe).

#### Template

`pdf-render/templates/resume.html`:

- A4 at 0.5in margins, 10.5pt body, 13pt section headers.
- Two-column layout: narrow left (contact + skills), wide right (experience + projects + education).
- Handlebars placeholders: `{{body}}` (pre-rendered HTML from markdown), `{{generatedAt}}`.
- Matches the Career-Ops OSS aesthetic (spec §2 says "matching Career-Ops OSS aesthetics"). Concrete CSS is developed during implementation; the final output must pass visual smoke test (a human looks at it once).

#### Auth

- `Authorization: Bearer <PDF_RENDER_API_KEY>` header required on `POST /render`.
- Service loads the key from env at startup; rejects requests that don't match with `401`.
- In docker-compose the key is a shared secret mounted via env; in prod it's a Secrets Manager reference (Phase 5 infra).

#### S3

- In tests and local dev: uploads go to LocalStack S3 at `http://localstack:4566` (same endpoint Phase 1 already uses).
- In prod: real S3 bucket from env `AWS_S3_BUCKET`.
- The service uploads, then returns `{success: true, s3_key, size_bytes, render_ms, page_count}`. Backend does not need to touch S3 during CV generation.

### 5.5 LLM clients (`core/llm/`)

#### `anthropic_client.py`

A thin singleton around `anthropic.AsyncAnthropic`:

- `get_client() -> AsyncAnthropic`
- `async def complete_with_cache(system, cacheable_blocks, user_block, model, max_tokens, tools=None) -> CompletionResult` — wraps `messages.create` with the caching header and returns `{content, usage, model}`.
- `async def stream_with_cache(...) -> AsyncIterator[StreamEvent]` — streaming variant used by the agent's `respond_node`.
- Wraps all errors in `LLMError`, `LLMTimeoutError`, `LLMQuotaError`.

#### `gemini_client.py`

- One-shot classifier and structured extraction only — no streaming.
- `async def classify(prompt: str, timeout: float = 3.0) -> str`
- `async def extract_json(prompt: str, schema: dict, timeout: float = 8.0) -> dict`
- Same error taxonomy.

Both clients emit `usage_events` via a callback the caller passes in (so the runner can attribute cost to the right `event_type`).

### 5.6 Minimum-viable chat UI (`user-portal/`)

Phase 1 left `user-portal` as an empty Vite + Tailwind skeleton. Phase 2a adds:

- **One route:** `/` → `ChatPage`. Any other route 404s until Phase 5.
- **Auth:** uses the Cognito client already wired in Phase 1. Unauthenticated users see a minimal "Please log in" screen (Phase 5 builds the real auth UI).
- **Chat page layout:**
  - Top bar: CareerAgent logo, user email, logout button.
  - Left: a single fixed conversation ("Default"). No conversation list in 2a.
  - Center: scrolling `MessageList` with user/assistant bubbles.
  - Bottom: `InputBar` — single textarea, enter to send, shift+enter for newline.
- **Cards:** `EvaluationCard` and `CvOutputCard` are rendered inline in assistant messages. Each is ≤150 lines of TSX with Tailwind classes matching parent spec §UX Notion palette. Action buttons are rendered but **disabled** in 2a (no action wiring yet).
- **Streaming:** `InputBar` POSTs the user message, receives the placeholder `message_id`, then opens an `EventSource` to the stream endpoint. Tokens are appended to the placeholder bubble live.
- **State:** local component state only. No Zustand in 2a. TanStack Query only for the conversation fetch on mount.
- **Tests:** one Vitest file — `ChatPage.test.tsx` — covering "send message, mock SSE stream, render evaluation card". No E2E in 2a.

---

## 6. Testing strategy

Phase 1 conventions: integration tests use a real Postgres via `pytest-postgresql`, HTTP mocked via `respx`, LLMs mocked via hand-written fakes. Phase 2a follows the same pattern.

### 6.1 Unit tests (no I/O)

| File | Coverage |
|---|---|
| `test_rule_scorer.py` | All 4 rule dimensions: edge cases (no salary, remote, missing experience years, empty skills). |
| `test_grader.py` | Score → grade mapping (all 9 bands), weight redistribution when salary is skipped. |
| `test_classifier_prompt.py` | Prompt builder produces exactly the Appendix D.2 string given a sample message. |
| `test_system_prompt_builder.py` | Prompt builder produces the cacheable system prompt with profile injection. |
| `test_sse_event_formatter.py` | Events serialize to the wire format. |

### 6.2 Integration tests (Postgres + fake LLMs + LocalStack)

| File | Coverage |
|---|---|
| `test_conversations_crud.py` | Create, list, get, delete — with `user_id` scoping verified. |
| `test_send_message_happy_path.py` | POST a message → assistant row persisted, usage_events recorded. Fake LLM returns deterministic output. |
| `test_send_message_off_topic.py` | Classifier returns `OFF_TOPIC` → canned response, no Claude call, no `usage_events` row for `respond`. |
| `test_send_message_rate_limited.py` | 11th message in 60 s → 429 RATE_LIMITED. |
| `test_stream_sse.py` | Open stream, verify event ordering (classifier → token → tool_start → tool_end → card → done). |
| `test_jobs_parse.py` | `/jobs/parse` with URL (httpx mocked) and with raw description. |
| `test_evaluations_create.py` | First call hits Claude (mock), second call hits cache, third call (different user, same job) hits cache. |
| `test_evaluations_scoped.py` | User A cannot read user B's evaluations. |
| `test_cv_outputs_create.py` | Requires prior evaluation. Generates cv_output row + uploads to LocalStack. Mock pdf-render service via respx. |
| `test_cv_outputs_regenerate.py` | Second call with `feedback` produces a distinct row and a distinct `pdf_s3_key`. |
| `test_cv_outputs_pdf_download.py` | `/pdf` returns 302 with signed URL. |
| `test_idempotency_evaluations.py` | Duplicate `Idempotency-Key` returns the cached response. |
| `test_error_envelope_phase2a.py` | Each new error code produces the right HTTP status + JSON envelope. |

### 6.3 Fake LLMs

- `tests/fixtures/fake_anthropic.py` — context manager `anthropic_stub({"evaluation": {...canned JSON...}, "cv": {...}})` that monkey-patches the `AsyncAnthropic` client to return canned messages by matching a keyword in the user prompt.
- `tests/fixtures/fake_gemini.py` — same idea for classifier responses.

No test ever contacts a real LLM provider. If `ANTHROPIC_API_KEY` is unset in CI, tests still pass. The CI matrix adds a nightly **smoke job** that runs a single end-to-end evaluation test against real providers (opt-in via env flag) — this job can fail without blocking merges.

### 6.4 pdf-render service

- `render.spec.ts` — unit: markdown → HTML rendering via the template, no browser.
- `server.spec.ts` — integration: boots a real Fastify instance, launches a real Chromium, renders a fixture markdown, verifies the returned PDF is a valid PDF header (`%PDF-`), is 1–3 pages, and uploads to LocalStack. Run in CI via a dedicated job that installs Chromium.

### 6.5 Chat UI

- `ChatPage.test.tsx` — Vitest + React Testing Library. Mocks `fetch` and `EventSource`. Asserts that sending a message renders the user bubble immediately, then streams tokens into the placeholder assistant bubble, then renders an `EvaluationCard` component from the final `card` event.

---

## 7. Environment variables (new)

Added to `backend/.env.example`:

```bash
# New in Phase 2a
ANTHROPIC_API_KEY=sk-ant-...                    # Required (tests use fakes)
GOOGLE_API_KEY=AIza...                          # Required (tests use fakes)
CLAUDE_MODEL=claude-sonnet-4-6
GEMINI_MODEL=gemini-2.0-flash-exp
ENABLE_PROMPT_CACHING=true
LLM_CLASSIFIER_TIMEOUT_S=3.0
LLM_EVALUATION_TIMEOUT_S=60.0
LLM_CV_OPTIMIZE_TIMEOUT_S=90.0

PDF_RENDER_URL=http://localhost:4000
PDF_RENDER_API_KEY=local-dev-key

AGENT_MESSAGE_RATE_LIMIT_PER_MINUTE=10
AGENT_MAX_HISTORY_MESSAGES=20
```

Added to `pdf-render/.env.example`:

```bash
PORT=4000
PDF_RENDER_API_KEY=local-dev-key
AWS_REGION=us-east-1
AWS_S3_BUCKET=career-agent-dev-assets
AWS_ENDPOINT_URL=http://localstack:4566       # Optional, for LocalStack
AWS_ACCESS_KEY_ID=test
AWS_SECRET_ACCESS_KEY=test
PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
```

Added to `user-portal/.env.example`:

```bash
VITE_SSE_KEEPALIVE_MS=15000
```

---

## 8. Decisions log — pushback welcome

These are the judgment calls I'm making without explicit user input. Tell me if any are wrong; changing them before the plan is cheap.

| # | Decision | Alternatives considered |
|---|---|---|
| D1 | **2 tools only** — `evaluate_job` + `optimize_cv`. Other categories route to canned "not yet" responses. | Stub all 6 tools with "not implemented" bodies. **Rejected** — the system prompt would lie about capabilities and the agent would hallucinate successes. |
| D2 | **Cache stores only the 6 Claude dimensions**, not the whole evaluation. | Cache the whole thing keyed by `(content_hash, profile_hash)`. **Rejected** — profile changes frequently (resume edits, target role updates), would tank hit rate. |
| D3 | **SSE over websockets** for streaming. | Websockets. **Rejected** — SSE is simpler, works with bearer token, no connection upgrade through ALB. |
| D4 | **Single round of tools per turn.** | Multi-hop ReAct loop. **Rejected as YAGNI** — we have 2 tools that don't chain; add multi-hop when we have ≥3 tools. |
| D5 | **No conversation summarization.** Replay last 20 messages verbatim. | Running summary via Claude Haiku. **Rejected as YAGNI** — 20 messages ≈ 10 user turns is enough for 2a; revisit in Phase 5. |
| D6 | **No paywall middleware.** All 2a users are on implicit unlimited trial. | Add `require_active_subscription` now with a `DISABLE_PAYWALL=true` flag. **Rejected** — double work; 2b adds it fresh. |
| D7 | **Minimum-viable chat UI in user-portal** (one route, one page, basic cards). | Leave user-portal as a stub and test only via curl. **Rejected** — dogfooding matters; curl testing hides SSE bugs. |
| D8 | **Feedback endpoint deferred.** `POST /evaluations/:id/feedback` does not ship in 2a (needs `feedback` table which doesn't exist). | Ship the table and endpoint. **Rejected** — moves unrelated work into 2a; feedback table is Phase 2d alongside interview prep. |
| D9 | **PDF fonts embedded locally** in the pdf-render service, not fetched from a CDN. | Google Fonts CDN. **Rejected** — determinism + no external dep at render time. |
| D10 | **One Chromium instance, semaphore-bounded to 2 concurrent renders.** | Browser-per-request. **Rejected** — 1.5 s Chromium cold-start per render is unacceptable; reuse saves ~1.4 s. |
| D11 | **Fake LLMs in all test suites.** Real provider smoke test is an opt-in nightly job. | Mocks for unit, real API for integration. **Rejected** — cost and flakiness; Phase 1 already set the pattern of fakes. |
| D12 | **Job scraping is a JS-free HTML fetch.** Any site that requires JS (SPAs) returns `JOB_PARSE_FAILED` and the user is told to paste the JD instead. | Playwright-based scraping. **Rejected for 2a** — would bloat the backend; pdf-render already has Chromium and we're trying to keep that service focused. Revisit in Phase 2c with the scanner. |

---

## 9. Open questions (answer before plan execution if any are wrong)

1. **Q:** Is "one default conversation per user" good enough for 2a, or do we want conversation creation in the UI?
   **A (my default):** Auto-create a default conversation on first chat page load (`GET /conversations` → if empty, POST one). One conversation per user in 2a. Multi-conversation UI is Phase 5.

2. **Q:** Should `evaluate_job` accept `job_url` OR `job_description`, or just require `job_url`?
   **A (my default):** Both, with mutual exclusion. The agent picks which based on what the user pasted — URL vs. raw JD text. Classifier output doesn't need to distinguish.

3. **Q:** When `/cv-outputs` is called with a `job_id` the user has never evaluated, do we auto-evaluate first, or return an error telling the user to evaluate first?
   **A (my default):** Return `422 EVALUATION_REQUIRES_JOB`. The agent, which is the primary caller, will have already evaluated the job in an earlier turn. The REST endpoint is a power-user surface; it can enforce ordering.

4. **Q:** Who triggers the Alembic migration in dev?
   **A (my default):** The Phase 1 quickstart `uv run alembic upgrade head` already runs all migrations; no change needed. CI runs migrations against the pytest-postgresql instance.

---

## 10. What Phase 2a does NOT ship (summary)

- Stripe customer creation, checkout, portal, webhook — 2b.
- Trial enforcement middleware — 2b.
- Job scanning (Greenhouse/Ashby/Lever adapters + Inngest) — 2c.
- Batch processing (L0/L1/L2 funnel + Inngest) — 2c.
- Interview prep (STAR stories + questions) — 2d.
- Negotiation playbooks — 2d.
- Applications / pipeline kanban — 2d (table + simple CRUD).
- Admin UI changes — Phase 5.
- Real AWS deployment / CDK completion — Phase 5.
- Full user-portal UX (slash commands, card actions, quick chips, kanban, settings tabs) — Phase 5.
- `POST /conversations/:id/actions` card action routing — Phase 5.
- `POST /evaluations/:id/feedback` — Phase 2d.
- Conversation titles from first message — sure, 2a (auto-set server-side from first user msg).
- Conversation summarization — Phase 5+.

---

## 11. Risks

| Risk | Mitigation |
|---|---|
| Playwright + Chromium inside docker-compose is finicky (memory, fonts, permissions) | Dedicated Dockerfile with `mcr.microsoft.com/playwright:v1.48.0-jammy` base image; single browser instance; CI job runs the same image. |
| Anthropic prompt caching headers change before we ship | Feature flag `ENABLE_PROMPT_CACHING=true`; fallback path makes uncached calls. Test both paths in unit tests. |
| Classifier false positives send legitimate career questions to `OFF_TOPIC` | Low-temperature classifier with explicit `CAREER_GENERAL` category as a catch-all. Log all `OFF_TOPIC` classifications with the user message so we can tune thresholds after dogfooding. |
| SSE connection closed mid-turn leaves orphaned placeholder message | Runner always completes the turn server-side regardless of SSE connection state. If the placeholder is still `running` after 120 s, a cleanup on next conversation fetch marks it as `failed`. |
| JD URL parsing fails on protected sites (require cookies, JS) | Return `422 JOB_PARSE_FAILED` with a message "Paste the job description text instead" — the chat UI handles this gracefully. |
| LocalStack and pdf-render networking in docker-compose | Document in docker-compose that pdf-render needs `localstack` as a network alias; test in CI. |

---

*End of spec.*
