# CareerAgent Phase 2d — Interview Prep + Negotiation + Feedback (Design Spec)

> **Parent spec:** [`2026-04-10-careeragent-design.md`](./2026-04-10-careeragent-design.md). This is a **delta spec**.
>
> **Predecessors:** Phase 2a (agent + eval + cv), Phase 2b (Stripe), Phase 2c (scanning + batch + pipeline). All done.
>
> **This is the last feature phase** before Phase 5 (polish + deploy). Phase 2d ships the remaining two feature modules (Interview Prep + Negotiation), the generic feedback loop, and fills the `star_stories` CRUD API gap left by Phase 1.

---

## 1. Goal

Ship the two remaining feature modules from the parent spec's 6-module roster, plus the generic feedback loop that telemeters LLM-generated artifact quality. After Phase 2d, the agent has its **full 6-tool set** and `NOT_YET_AVAILABLE_TEMPLATES` is empty.

**End state:**

1. **Interview prep — per-job mode:** user says *"prep me for my Stripe interview"* (or clicks "Practice" on an evaluation card) → agent calls `build_interview_prep_tool(job_id=...)`. First call auto-populates the STAR story bank from the master resume (5-10 stories via Claude). Generates 10 role-specific questions + 5 red-flag questions the candidate should ask the interviewer. Persists to `interview_preps`. Returns an `InterviewPrepCard`.
2. **Interview prep — custom-role mode:** user says *"prep me for staff SRE interviews in general"* → agent calls `build_interview_prep_tool(custom_role="staff SRE")`. Same story-bank behavior; prompt is role-description-based instead of job-description-based.
3. **Story bank CRUD:** user navigates to `/interview-prep/story-bank` → sees the extracted stories → can edit a metric, add a missing story from a side project, tag stories, delete stale ones. REST endpoints `GET/POST/PUT/DELETE /api/v1/star-stories` back the page.
4. **Negotiation — offer in hand:** user says *"help me negotiate this offer"* after Stripe extends an offer → user provides `{base, equity, signing_bonus, total_comp}` via an `OfferForm` modal → agent calls `generate_negotiation_playbook_tool(job_id, offer_details)` → Claude generates market research + counter-offer target + scripts (email, call) + fallbacks + pitfalls. Persists to `negotiations`. Returns a `NegotiationCard`.
5. **Regenerate flows:** both `InterviewPrepCard` and `NegotiationCard` have a "Regenerate with feedback" button that calls `POST /api/v1/interview-preps/:id/regenerate {feedback}` or `POST /api/v1/negotiations/:id/regenerate {feedback}` — mirroring the Phase 2a CV pattern.
6. **Feedback loop:** every `EvaluationCard`, `CvOutputCard`, `InterviewPrepCard`, `NegotiationCard` renders a `FeedbackWidget` (5-star rating + optional correction notes). Saving a rating posts to `POST /api/v1/{resource_type}/:id/feedback`. All four resource types are supported.
7. **Pipeline integration:** when a negotiation is generated, the corresponding application's `negotiation_id` field (column exists as nullable from Phase 2c) is populated with the `negotiations.id`. The 2d migration adds the FK constraint that Phase 2c deferred.

**Non-goals (explicit):**
- Multi-round negotiation linking (*"create a new negotiation with context from the previous one"* — parent spec §1). Each negotiation is standalone in 2d; Phase 5 adds the chain.
- Interview prep PDF export.
- Negotiation playbook PDF export.
- Voice/video coaching or mock-interview chat mode.
- Admin feedback review UI. Phase 5.
- Compensation research without an offer (speculative comp queries fall through to `CAREER_GENERAL` classifier path — Claude answers from training data).
- `POST /conversations/:id/actions` card action routing. Still Phase 5.
- Conversation summarization. Still Phase 5.
- Scheduled interview reminders / calendar integration.

---

## 2. Architecture delta

Phase 2c left the backend with `core/agent/`, `core/evaluation/`, `core/cv_optimizer/`, `core/scanner/`, `core/batch/`, `core/llm/`. Phase 2d adds two new core modules (`interview_prep/`, `negotiation/`), one new cross-cutting service (`feedback/`), four new API routers, and four new frontend pages.

**New backend modules:**

```
backend/src/career_agent/
├── core/
│   ├── interview_prep/
│   │   ├── __init__.py                    [NEW]
│   │   ├── extractor.py                   [NEW]  Claude call: master resume → STAR stories
│   │   ├── generator.py                   [NEW]  Claude call: role → questions + red-flag Qs
│   │   └── service.py                     [NEW]  ensure_story_bank → generate → persist
│   ├── negotiation/
│   │   ├── __init__.py                    [NEW]
│   │   ├── playbook.py                    [NEW]  Claude call via Appendix D.7 prompt
│   │   └── service.py                     [NEW]  validate offer → generate → persist
│   ├── feedback/
│   │   ├── __init__.py                    [NEW]
│   │   └── service.py                     [NEW]  generic write-path + per-resource owner validators
│   └── agent/
│       ├── tools.py                       [MOD]  +build_interview_prep_tool, +generate_negotiation_playbook_tool
│       ├── graph.py                       [MOD]  register new tools in dispatch
│       └── prompts.py                     [MOD]  NOT_YET_AVAILABLE_TEMPLATES = {}
├── api/
│   ├── interview_preps.py                 [NEW]  POST, GET list, GET detail, POST regenerate
│   ├── negotiations.py                    [NEW]  POST, GET list, GET detail, POST regenerate
│   ├── star_stories.py                    [NEW]  POST, GET list, GET detail, PUT, DELETE
│   ├── feedback.py                        [NEW]  4 sub-routers per resource type (evaluations, cv_outputs, interview_preps, negotiations)
│   └── main.py                            [MOD]  register 4 new routers
├── models/
│   ├── interview_prep.py                  [NEW]
│   ├── negotiation.py                     [NEW]
│   ├── feedback.py                        [NEW]
│   └── star_story.py                      [EXISTS from Phase 1; no changes]
├── schemas/
│   ├── interview_prep.py                  [NEW]
│   ├── negotiation.py                     [NEW]
│   ├── star_story.py                      [NEW]
│   └── feedback.py                        [NEW]
└── services/
    ├── interview_prep.py                  [NEW]  DB CRUD thin wrapper (kept separate from core/)
    ├── negotiation.py                     [NEW]
    └── star_story.py                      [NEW]
```

**Migration:** `0006_phase2d_interview_prep_negotiation_feedback.py` creates 3 tables + 1 FK constraint.

**Frontend delta (user-portal):**

```
src/
├── pages/
│   ├── InterviewPrepListPage.tsx          [NEW]  /interview-prep
│   ├── InterviewPrepDetailPage.tsx        [NEW]  /interview-prep/:id
│   ├── StoryBankPage.tsx                  [NEW]  /interview-prep/story-bank
│   ├── NegotiationListPage.tsx            [NEW]  /negotiations
│   └── NegotiationDetailPage.tsx          [NEW]  /negotiations/:id
├── components/
│   ├── interview-prep/
│   │   ├── StarStoryCard.tsx              [NEW]
│   │   ├── StarStoryEditor.tsx            [NEW]  inline edit + tag input + save
│   │   └── QuestionListItem.tsx           [NEW]
│   ├── negotiation/
│   │   ├── OfferForm.tsx                  [NEW]  collect offer_details before generate
│   │   ├── MarketRangeChart.tsx           [NEW]  text bar showing low/mid/high
│   │   └── ScriptBlock.tsx                [NEW]  copy-to-clipboard wrapper
│   ├── chat/cards/
│   │   ├── InterviewPrepCard.tsx          [NEW]
│   │   └── NegotiationCard.tsx            [NEW]
│   └── shared/
│       └── FeedbackWidget.tsx             [NEW]  5-star + textarea, used in 4 cards + 2 detail pages
├── lib/
│   └── api.ts                             [MOD]  add interviewPreps, negotiations, starStories, feedback namespaces
├── App.tsx                                [MOD]  5 new routes
└── components/layout/AppShell.tsx         [MOD]  nav: Interview Prep, Negotiations
```

**Phase 2c touch points:**
- `EvaluationCard.tsx` + `CvOutputCard.tsx` — add the `FeedbackWidget` component so users can rate existing 2a/2b outputs.
- `MessageList.tsx` — add `InterviewPrepCard` + `NegotiationCard` branches to the chat card dispatch.

**Agent gets the full 6-tool set:**
- `evaluate_job` (Phase 2a)
- `optimize_cv` (Phase 2a)
- `start_job_scan` (Phase 2c)
- `start_batch_evaluation` (Phase 2c)
- `build_interview_prep` (Phase 2d, new)
- `generate_negotiation_playbook` (Phase 2d, new)

`NOT_YET_AVAILABLE_TEMPLATES` becomes `{}`. System prompt updated: *"You have SIX tools — the full product surface is live."*

### 2.1 Data flow — interview prep, first call

```
User says "prep me for my Stripe interview" in chat
         │
         ▼
L0 classifier → INTERVIEW_PREP (Gemini)
         │
         ▼
route_node → Claude → TOOL_CALL: {"call": "build_interview_prep", "args": {"job_id": "<uuid>"}}
         │
         ▼
build_interview_prep_tool(runtime, job_id=...):
  1. load evaluation / job
  2. InterviewPrepService.ensure_story_bank(user_id)
     - if star_stories for user is empty:
         call InterviewPrepExtractor.extract(master_resume_md)
         → Claude returns JSON with 5-10 STAR stories
         → persist to star_stories with source='ai_generated'
     - else: skip
  3. InterviewPrepService.generate(user_id, job_id=job_id)
     - call InterviewPrepGenerator.generate(
           resume_md, job_markdown, existing_stories_summary
       )
     - Claude runs Appendix D.6 prompt → returns JSON with
       {questions, red_flag_questions, suggested stories}
     - persist to interview_preps
  4. return {ok: True, card: InterviewPrepCardPayload}
         │
         ▼
assistant message with InterviewPrepCard inline
         │
         ▼
User clicks "Practice" or "Rate this" on the card (direct REST, no agent)
```

### 2.2 Data flow — negotiation, first call

```
User says "help me negotiate this Stripe offer"
         │
         ▼
L0 classifier → NEGOTIATE
         │
         ▼
route_node → Claude → TOOL_CALL: {"call": "generate_negotiation_playbook", "args": {"job_id": "<uuid>"}}
         │
         ▼
generate_negotiation_playbook_tool(runtime, job_id=...):
  NOTE: does NOT accept offer_details from the agent path directly.
  If offer_details not yet on file, returns:
    {ok: False, error_code: "OFFER_DETAILS_REQUIRED",
     message: "Open the negotiation form to provide your offer details."}

  Frontend interprets this by rendering an OfferForm modal in the chat.
  User fills in {base, equity, signing_bonus, location}, clicks Submit.
  Direct REST call: POST /api/v1/negotiations {job_id, offer_details}
         │
         ▼
NegotiationService.create(user_id, job_id, offer_details):
  1. Load evaluation, job, profile
  2. Build context {title, company, location, offer_json,
                    current_comp, experience_summary, market_context}
  3. Claude runs Appendix D.7 prompt → returns JSON with
     {market_research, counter_offer, scripts, pitfalls}
  4. persist to negotiations
  5. Populate applications.negotiation_id if an application exists for this (user, job)
         │
         ▼
Frontend receives NegotiationCard payload, renders inline in chat + in list page
```

### 2.3 Key architectural decisions

| Decision | Choice | Why |
|---|---|---|
| Interview prep story bank | **Lazy auto-populate on first tool call** (D1) | Zero friction for first call; cheap reuse after; matches Appendix D.6 prompt which expects existing stories context |
| Interview prep input mode | **`job_id` OR `custom_role`, mutually exclusive** (D2) | Supports both real-job prep and general practice; matches parent spec E.2 |
| Negotiation input | **`job_id` + `offer_details` required** (D3) | Without real numbers, market research + counter + scripts are meaningless. Speculative comp queries fall through to `CAREER_GENERAL` |
| Offer collection via agent | **Tool returns `OFFER_DETAILS_REQUIRED` error; frontend renders OfferForm modal; user submits via direct REST `POST /negotiations`** | Agent is bad at multi-turn form filling; OfferForm is a real form component. The tool call error code is a deliberate hand-off signal to the frontend |
| Feedback scope | **All 4 LLM-generated resources** (evaluations, cv_outputs, interview_preps, negotiations) via generic `feedback` table with per-resource owner validators (D4) | Max telemetry for minimal extra code. One service with a dispatch dict, four thin routes |
| Frontend scope | **Full CRUD — list + detail pages for both modules, StoryBankPage, chat cards, shared FeedbackWidget** (D5) | Avoids the 2b/2c.1 mistake of shipping backend-only and needing a cleanup pass |
| Regenerate | **Dedicated endpoints mirroring Phase 2a CV pattern** — `POST /interview-preps/:id/regenerate {feedback}` and `POST /negotiations/:id/regenerate {feedback}` (D6) | Consistent iteration affordance across all generated artifacts |
| Star stories CRUD | **Full CRUD added in 2d** (Phase 1 backfill) | Table and model exist from Phase 1 but no API; StoryBankPage needs it; user-created and AI-edited stories share the same table |
| `applications.negotiation_id` FK | **Added in 2d's migration 0006** alongside the new `negotiations` table | Phase 2c created the column nullable without FK (per design §3.6); 2d adds `ALTER TABLE ... ADD CONSTRAINT fk_applications_negotiation_id` |
| Paywall gating | **POST/regenerate endpoints paywalled** (`EntitledDbUser`); GET + story bank CRUD + feedback endpoints non-paywalled (`CurrentDbUser`) | Consistent with Phase 2c pattern — generation costs are gated, organizational data and telemetry are free |
| Prompts | **Parent Appendix D.6 and D.7 verbatim with prompt caching** on the cacheable prefix blocks | Matches Phase 2a evaluation + cv optimizer patterns |

---

## 3. Data model delta

Migration `0006_phase2d_interview_prep_negotiation_feedback.py` — 3 new tables + 1 FK constraint.

### 3.1 `interview_preps`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `user_id` | UUID FK → users CASCADE | |
| `job_id` | UUID FK → jobs SET NULL | Nullable — custom-role prep has no job |
| `custom_role` | VARCHAR(255) | Nullable; set only when `job_id` is null |
| `questions` | JSONB NOT NULL | Array of `{question, category, suggested_story_title, framework}` |
| `red_flag_questions` | JSONB | Array of `{question, what_to_listen_for}` |
| `model_used` | VARCHAR(64) NOT NULL | |
| `tokens_used` | INTEGER | |
| `created_at` | TIMESTAMPTZ | |

Constraint: `CHECK (job_id IS NOT NULL OR custom_role IS NOT NULL)` — exactly one of the two is set. Indexes: `idx_interview_preps_user_id`, `idx_interview_preps_user_created (user_id, created_at DESC)`.

### 3.2 `negotiations`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `user_id` | UUID FK → users CASCADE | |
| `job_id` | UUID FK → jobs CASCADE | Required — negotiation is always tied to a specific offer for a specific job |
| `offer_details` | JSONB NOT NULL | `{base, equity, signing_bonus, total_comp, location, start_date, ...}` |
| `market_research` | JSONB NOT NULL | `{range_low, range_mid, range_high, source_notes, comparable_roles}` |
| `counter_offer` | JSONB NOT NULL | `{target, minimum_acceptable, equity_ask, justification}` |
| `scripts` | JSONB NOT NULL | `{email_template, call_script, fallback_positions, pitfalls}` |
| `model_used` | VARCHAR(64) NOT NULL | |
| `tokens_used` | INTEGER | |
| `created_at` | TIMESTAMPTZ | |

Indexes: `idx_negotiations_user_id`, `idx_negotiations_user_created (user_id, created_at DESC)`, `idx_negotiations_job_id`.

**FK constraint added to `applications`:**
```sql
ALTER TABLE applications
  ADD CONSTRAINT fk_applications_negotiation_id
  FOREIGN KEY (negotiation_id) REFERENCES negotiations(id) ON DELETE SET NULL;
```

The column already exists from Phase 2c migration 0005. Phase 2d's migration only adds the constraint.

### 3.3 `feedback`

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `user_id` | UUID FK → users CASCADE | |
| `resource_type` | VARCHAR(32) NOT NULL | `'evaluation' \| 'cv_output' \| 'interview_prep' \| 'negotiation'` |
| `resource_id` | UUID NOT NULL | No FK — polymorphic; ownership validated in service layer |
| `rating` | INTEGER NOT NULL | 1–5 (CHECK constraint) |
| `correction_notes` | TEXT | |
| `created_at` | TIMESTAMPTZ | |

Constraints:
- `CHECK (rating >= 1 AND rating <= 5)`
- Unique on `(user_id, resource_type, resource_id)` — one feedback per user per resource; PUT via upsert

Indexes:
- `idx_feedback_user_id`
- `idx_feedback_resource (resource_type, resource_id)` — for admin queries like "show all ratings for this specific evaluation"
- `idx_feedback_created (created_at DESC)` — for admin dashboards

---

## 4. API delta

All endpoints under `/api/v1`. Auth required unless noted. Paywall (`EntitledDbUser`) marked per route.

### 4.1 Interview prep

| Method | Path | Gate | Body / Params | Response |
|---|---|---|---|---|
| `POST` | `/interview-preps` | **Entitled** | `{job_id?, custom_role?}` (XOR) | `201 { "data": InterviewPrepOut }` |
| `GET` | `/interview-preps` | Current | `?limit=20` | `200 { "data": InterviewPrepOut[] }` |
| `GET` | `/interview-preps/:id` | Current | — | `200 { "data": InterviewPrepOut }` |
| `POST` | `/interview-preps/:id/regenerate` | **Entitled** | `{feedback?}` | `201 { "data": InterviewPrepOut }` — creates a new row, doesn't mutate the old |
| `POST` | `/interview-preps/:id/feedback` | Current | `{rating, correction_notes?}` | `201 { "data": FeedbackOut }` |

### 4.2 Star stories (Phase 1 backfill)

| Method | Path | Gate | Body / Params | Response |
|---|---|---|---|---|
| `GET` | `/star-stories` | Current | `?tags=leadership,technical` | `200 { "data": StarStoryOut[] }` |
| `POST` | `/star-stories` | Current | `{title, situation, task, action, result, reflection?, tags[]}` | `201 { "data": StarStoryOut }` — `source='user_created'` |
| `GET` | `/star-stories/:id` | Current | — | `200 { "data": StarStoryOut }` |
| `PUT` | `/star-stories/:id` | Current | any subset of the create body | `200 { "data": StarStoryOut }` |
| `DELETE` | `/star-stories/:id` | Current | — | `204` |

**Note:** star_stories CRUD is NOT paywalled. Users manage their own life/career data regardless of billing state. Consistent with `applications` in Phase 2c.

### 4.3 Negotiations

| Method | Path | Gate | Body / Params | Response |
|---|---|---|---|---|
| `POST` | `/negotiations` | **Entitled** | `{job_id, offer_details: {base, equity?, signing_bonus?, total_comp?, location?, start_date?}}` | `201 { "data": NegotiationOut }` |
| `GET` | `/negotiations` | Current | `?limit=20` | `200 { "data": NegotiationOut[] }` |
| `GET` | `/negotiations/:id` | Current | — | `200 { "data": NegotiationOut }` |
| `POST` | `/negotiations/:id/regenerate` | **Entitled** | `{feedback?}` | `201 { "data": NegotiationOut }` |
| `POST` | `/negotiations/:id/feedback` | Current | `{rating, correction_notes?}` | `201 { "data": FeedbackOut }` |

### 4.4 Feedback endpoints on existing resources (Phase 2a/2b backfill)

| Method | Path | Gate | Body / Params | Response |
|---|---|---|---|---|
| `POST` | `/evaluations/:id/feedback` | Current | `{rating, correction_notes?}` | `201 { "data": FeedbackOut }` |
| `POST` | `/cv-outputs/:id/feedback` | Current | `{rating, correction_notes?}` | `201 { "data": FeedbackOut }` |

These are additive to the existing `/evaluations/*` and `/cv-outputs/*` routers from Phase 2a.

### 4.5 New error codes

| Code | HTTP | When |
|---|---|---|
| `INTERVIEW_PREP_NOT_FOUND` | 404 | |
| `NEGOTIATION_NOT_FOUND` | 404 | |
| `STAR_STORY_NOT_FOUND` | 404 | |
| `INVALID_INTERVIEW_PREP_INPUT` | 422 | Both `job_id` and `custom_role` provided, or neither |
| `OFFER_DETAILS_REQUIRED` | 422 | Negotiation tool called without offer details — frontend signal to render OfferForm |
| `MISSING_MASTER_RESUME` | 422 | Interview prep extractor called on a user with no `master_resume_md` |
| `INVALID_FEEDBACK` | 422 | Rating outside 1–5 range |
| `FEEDBACK_RESOURCE_NOT_FOUND` | 404 | Ownership check failed — either resource doesn't exist or belongs to another user |

---

## 5. Component designs

### 5.1 Interview prep extractor (`core/interview_prep/extractor.py`)

```python
async def extract_star_stories_from_resume(
    *,
    master_resume_md: str,
    max_stories: int = 10,
    timeout_s: float = 60.0,
) -> list[ExtractedStory]:
    """One-shot Claude call that reads the master resume and returns 5–10 STAR stories.

    Returns ExtractedStory{title, situation, task, action, result, reflection, tags[]}.
    Uses prompt caching on the instructions block.
    """
```

Prompt structure (based on Appendix D.6 but extraction-only):
- **Cacheable:** extraction instructions (rules: "don't fabricate", "extract from actual resume content", STAR+Reflection format)
- **Dynamic:** the resume markdown

### 5.2 Interview prep generator (`core/interview_prep/generator.py`)

Uses parent spec Appendix D.6 prompt verbatim. Two modes:

```python
async def generate_interview_prep(
    *,
    existing_stories_summary: str,
    job_markdown: str | None,
    custom_role: str | None,
    resume_md: str,
    timeout_s: float = 60.0,
) -> GeneratedInterviewPrep:
    """Generate questions + red-flag questions + suggested_story_title mappings.

    If job_markdown is provided, tailors to the specific role.
    If custom_role is provided, generic prep for that role description.
    Exactly one must be set.
    """
```

**Cacheable prefix:** Appendix D.6 instructions block (STAR+Reflection format rules, rules about grounding in resume, output JSON schema).
**Dynamic suffix:** resume + job_markdown-or-custom_role + existing_stories_summary.

### 5.3 Interview prep service (`core/interview_prep/service.py`)

```python
class InterviewPrepService:
    async def ensure_story_bank(self, user_id: UUID) -> list[StarStory]:
        """If user has no star_stories, extract from master resume and persist."""

    async def create(
        self,
        *,
        user_id: UUID,
        job_id: UUID | None,
        custom_role: str | None,
        feedback: str | None = None,
    ) -> InterviewPrep:
        """Full flow: ensure story bank → load job/resume → generate → persist."""

    async def regenerate(
        self,
        *,
        user_id: UUID,
        interview_prep_id: UUID,
        feedback: str | None,
    ) -> InterviewPrep:
        """Create a new row using the original's job_id/custom_role + new feedback context."""
```

The create() method validates `job_id XOR custom_role` and raises `InvalidInterviewPrepInput` if both or neither. Story bank extraction fires once per user; the `star_stories.source='ai_generated'` marker lets tests distinguish AI-extracted from user-created stories.

### 5.4 Negotiation playbook (`core/negotiation/playbook.py`)

Uses parent spec Appendix D.7 prompt verbatim. One function:

```python
async def generate_negotiation_playbook(
    *,
    title: str,
    company: str,
    location: str,
    offer_details: dict[str, Any],
    current_comp: dict[str, Any] | None,
    experience_summary: str,
    feedback: str | None = None,
    timeout_s: float = 60.0,
) -> GeneratedPlaybook:
    """Returns {market_research, counter_offer, scripts, pitfalls}."""
```

**Cacheable prefix:** Appendix D.7 instructions + output schema.
**Dynamic suffix:** title + company + offer_details + current_comp + feedback.

Market context is pulled from Claude's training data (*"Based on levels.fyi and Glassdoor data for staff engineer at senior in SF..."*). No live market API in 2d — Phase 5 can wire one if needed.

### 5.5 Negotiation service (`core/negotiation/service.py`)

```python
class NegotiationService:
    async def create(
        self,
        *,
        user_id: UUID,
        job_id: UUID,
        offer_details: dict[str, Any],
    ) -> Negotiation:
        """Load context → generate playbook → persist → link to application if any."""

    async def regenerate(
        self,
        *,
        user_id: UUID,
        negotiation_id: UUID,
        feedback: str | None,
    ) -> Negotiation:
        """Create a new row with feedback-guided regeneration."""
```

After persisting the negotiation row, the service queries for an existing `Application` row matching `(user_id, job_id)` and, if found, sets `application.negotiation_id = negotiation.id`. Multi-negotiation chaining is deferred — only the most recent negotiation is linked.

### 5.6 Feedback service (`core/feedback/service.py`)

```python
_RESOURCE_VALIDATORS: dict[str, Callable[[AsyncSession, UUID, UUID], Awaitable[bool]]] = {
    "evaluation": _validate_evaluation_ownership,
    "cv_output": _validate_cv_output_ownership,
    "interview_prep": _validate_interview_prep_ownership,
    "negotiation": _validate_negotiation_ownership,
}


class FeedbackService:
    async def record(
        self,
        *,
        user_id: UUID,
        resource_type: str,
        resource_id: UUID,
        rating: int,
        correction_notes: str | None,
    ) -> Feedback:
        """Upsert feedback for a resource. Validates ownership via the dispatch dict.

        Raises FeedbackResourceNotFound if the resource doesn't exist or the user
        doesn't own it. Raises InvalidFeedback if rating is outside 1-5.
        """
```

The four validators are thin: each loads the resource by id, checks `resource.user_id == user_id`, returns bool. The service raises `FeedbackResourceNotFound` on false. Unique constraint on `(user_id, resource_type, resource_id)` means the second POST with the same triple performs an UPSERT (new rating replaces the old).

### 5.7 Agent tool additions (`core/agent/tools.py`)

```python
async def build_interview_prep_tool(
    runtime: ToolRuntime,
    *,
    job_id: str | None = None,
    custom_role: str | None = None,
) -> dict[str, Any]:
    """Build interview prep. Exactly one of job_id / custom_role required."""


async def generate_negotiation_playbook_tool(
    runtime: ToolRuntime,
    *,
    job_id: str,
) -> dict[str, Any]:
    """Generate a negotiation playbook. Requires prior offer_details stored for this job.

    If no offer exists, returns {ok: False, error_code: "OFFER_DETAILS_REQUIRED"}
    — frontend interprets this as a signal to render the OfferForm modal and
    make a direct POST /negotiations call with the user-entered offer details.
    """
```

Graph dispatch in `core/agent/graph.py` adds both branches. Prompt manifest adds two more tool signatures. `NOT_YET_AVAILABLE_TEMPLATES` becomes `{}`. System prompt text changes "You have FOUR tools" → "You have SIX tools — the full product surface is live."

### 5.8 Frontend

**`FeedbackWidget.tsx`** (shared component):
- 5-star rating click → immediately POSTs `{rating}` to the appropriate `/{resource_type}/:id/feedback` endpoint
- Optional "Add notes" button expands a textarea; second POST sends `{rating, correction_notes}`
- Idempotent: clicking a different star updates the existing row via the upsert semantics
- Compact footer in card layouts, inline section in detail pages

**`InterviewPrepCard.tsx`** (chat card, parent spec Appendix G):
- Shows top 3 questions with category badges + the suggested STAR story title
- "View full prep" → navigates to `/interview-prep/:id`
- "Regenerate with feedback" → inline textarea → POST regenerate
- `FeedbackWidget` at bottom

**`InterviewPrepDetailPage.tsx`** at `/interview-prep/:id`:
- Full question list with suggested STAR story mappings + answer frameworks
- Red-flag questions section (questions for the interviewer)
- Regenerate button
- FeedbackWidget

**`StoryBankPage.tsx`** at `/interview-prep/story-bank`:
- List of STAR stories with title + tags + source badge (`AI` / `Manual`)
- "Add story" button → inline `StarStoryEditor`
- Click story → inline edit mode (`StarStoryEditor` replaces the card)
- Tag filter at top

**`StarStoryEditor.tsx`**:
- Form with title, situation, task, action, result, reflection, tags input
- Save → PUT or POST depending on whether editing existing
- Cancel → discards

**`NegotiationCard.tsx`** (chat card):
- Market range bar (`MarketRangeChart`)
- Counter offer: target + minimum
- Top script snippet with copy button
- "View full playbook" → `/negotiations/:id`
- "Regenerate with feedback"
- FeedbackWidget

**`NegotiationDetailPage.tsx`** at `/negotiations/:id`:
- Market research section with range, source notes, comparable roles
- Counter offer section (target, minimum, equity ask, justification)
- Scripts: email template (copyable), call script (copyable), fallback positions
- Pitfalls list
- FeedbackWidget

**`OfferForm.tsx`** modal:
- Inputs: base_salary (required), equity, signing_bonus, total_comp, location, start_date
- Submit → POST `/negotiations` directly
- Rendered by the chat page when it receives a `OFFER_DETAILS_REQUIRED` tool result in an assistant message

---

## 6. Testing strategy

**Unit tests** (`tests/unit/`):

- `test_interview_prep_extractor_prompt.py` — prompt builder produces expected structure given a sample resume
- `test_interview_prep_generator_prompt.py` — XOR validation, cacheable block verification
- `test_negotiation_playbook_prompt.py` — offer_details injected correctly, feedback appended when provided
- `test_feedback_service_validators.py` — ownership validators return True for owner, False for non-owner, False for missing resource

**Integration tests** (`tests/integration/`):

- `test_interview_prep_auto_populates_story_bank.py` — first call extracts stories; second call skips extraction and reuses
- `test_interview_prep_custom_role.py` — no `job_id`, `custom_role="staff SRE"` → prep generated without a job fetch
- `test_interview_prep_job_id_mode.py` — `job_id` present, `custom_role` None, prep tailored to the job
- `test_interview_prep_regenerate.py` — POST regenerate creates a new row
- `test_interview_prep_paywalled.py` — trial-expired user gets 403 on POST, 200 on GET
- `test_negotiation_requires_offer_details.py` — POST without `offer_details` → 422
- `test_negotiation_full_playbook.py` — full flow including `application.negotiation_id` linking
- `test_negotiation_regenerate.py`
- `test_negotiation_paywalled.py`
- `test_star_stories_crud.py` — full CRUD + user scoping + tag filter
- `test_star_stories_not_paywalled.py` — trial-expired user can still manage stories
- `test_feedback_evaluation.py` — POST + upsert semantics + 5-star range validation
- `test_feedback_cv_output.py`
- `test_feedback_interview_prep.py`
- `test_feedback_negotiation.py`
- `test_feedback_ownership_cross_user.py` — user A cannot feedback on user B's evaluation
- `test_agent_interview_prep_tool.py` — classifier → tool dispatch → result card
- `test_agent_negotiation_tool_requires_offer.py` — tool returns `OFFER_DETAILS_REQUIRED` card signal
- `test_phase2d_smoke.py` — end-to-end: extract stories → generate prep → feedback → create negotiation → link to application

**Frontend tests** (`user-portal/src/`):

- `InterviewPrepListPage.test.tsx`
- `InterviewPrepDetailPage.test.tsx` — renders questions + feedback widget
- `StoryBankPage.test.tsx` — list + add + edit flows
- `NegotiationListPage.test.tsx`
- `NegotiationDetailPage.test.tsx` — renders market range + counter + scripts
- `OfferForm.test.tsx` — submit POSTs offer details
- `FeedbackWidget.test.tsx` — click star → POST
- `InterviewPrepCard.test.tsx` — chat card rendering
- `NegotiationCard.test.tsx`

**Fake LLM strategy:** reuse `fake_anthropic` + `fake_gemini` from Phase 2a, with new substring triggers for:
- Story extraction (`"STAR+REFLECTION"` in prompt)
- Question generation (`"OUTPUT JSON"` + `"questions"` in prompt)
- Negotiation playbook (`"market_research"` in prompt)

**Total:** ~18 new backend tests + ~9 frontend tests. Running total after 2d: **~151 backend tests, ~25 frontend tests**.

---

## 7. Environment variables

No new env vars. Phase 2d reuses everything from 2a (Anthropic + Gemini + prompt caching flag + timeouts). The existing `LLM_EVALUATION_TIMEOUT_S` (60s) is reused for both interview prep and negotiation generation — both are similar-size Claude calls.

If we ever want to tune timeouts per module, we can add `LLM_INTERVIEW_PREP_TIMEOUT_S` and `LLM_NEGOTIATION_TIMEOUT_S` in a follow-up; not needed for v1.

---

## 8. Decisions log — the 7 locked choices

| # | Question | Decision | Rationale |
|---|---|---|---|
| **D1** | Interview prep story bank flow | **Lazy auto-populate on first tool call** if `star_stories` is empty | Zero friction first call; cheap reuse; matches parent spec D.6 which expects "existing stories summary" context |
| **D2** | Interview prep input modes | **`job_id` OR `custom_role`, mutually exclusive** | Supports both real-job prep and general practice; matches Appendix E.2 |
| **D3** | Negotiation input | **`job_id` + `offer_details` required — no speculative mode** | Without real numbers the outputs are meaningless; speculative comp queries fall through to `CAREER_GENERAL` |
| **D4** | Feedback scope | **All 4 LLM-generated resources** (evaluations, cv_outputs, interview_preps, negotiations) | Max telemetry; one generic service with per-resource owner validators |
| **D5** | Frontend scope | **Full CRUD** — list + detail pages for both modules, StoryBankPage, chat cards, shared FeedbackWidget | Ship complete feature; avoid the 2b/2c.1 backend-first mistake |
| **D6** | Regenerate | **Dedicated endpoints** mirroring Phase 2a CV pattern | Consistent iteration affordance |
| **D7** | Star stories CRUD | **Full CRUD added in 2d** (Phase 1 backfill) | StoryBankPage needs it; table exists from Phase 1, only API missing |

---

## 9. Out of scope (explicit)

- Multi-round negotiation chaining ("create a new negotiation with context from the previous one") — Phase 5 polish
- Interview prep PDF export / negotiation PDF export — Phase 5
- Mock interview chat mode (multi-turn Q&A with Claude playing interviewer) — Phase 5
- Voice or video coaching
- Calendar integration / scheduled interview reminders
- Admin feedback review UI — Phase 5
- Live compensation data API (levels.fyi, Glassdoor) — Phase 5 if needed
- Batch interview prep (generate prep for multiple jobs at once) — not in parent spec
- `POST /conversations/:id/actions` card action routing — Phase 5
- `applications.negotiation_id` auto-linking across multiple negotiations per job — only most recent is linked in 2d

---

## 10. Risks

| Risk | Mitigation |
|---|---|
| Story bank extraction on a weak resume produces low-quality stories | User can edit/delete manually via StoryBankPage (CRUD ships in 2d). Future Phase 5 could add a "re-extract" button. |
| Claude fabricates facts in the interview prep questions or negotiation market range | Prompts explicitly say "do not fabricate" / "cite actual experience from resume" / "base on levels.fyi + glassdoor data"; `FeedbackWidget` surfaces issues via telemetry for future prompt refinement |
| User provides incomplete offer details (e.g. only base salary) | Claude prompt is robust to partial offers — unknown fields are treated as "not disclosed"; tests cover this |
| `applications.negotiation_id` FK add on a table with existing rows that violate the constraint | Phase 2c seeds the column as NULL; no existing rows violate; the ALTER TABLE is safe |
| Feedback upsert race conditions under concurrent rating changes | Unique constraint + `ON CONFLICT DO UPDATE` SQL; Postgres handles it |
| Prompt caching breaks Appendix D.6/D.7 expected structure | Existing test pattern from 2a (test_anthropic_client.py verifies `cache_control` headers); add similar for the 2d prompts |
| FeedbackWidget POSTs on every star click, causing network spam for indecisive users | Debounce clicks 500ms client-side before POSTing; one POST per settled rating |
| Interview prep tool called with empty master_resume_md → extractor fails | Service raises `MISSING_MASTER_RESUME` (422) with clear message pointing user to upload a resume first |

---

## 11. References

- Parent spec Appendix D.6 (interview prep prompt), D.7 (negotiation playbook prompt), G (card payload schemas), E (LangGraph agent state + tools)
- Phase 2a spec: [`2026-04-10-phase2a-agent-eval-cv-design.md`](./2026-04-10-phase2a-agent-eval-cv-design.md) — reuse of `EntitledDbUser` pattern, prompt caching, `fake_anthropic` fixtures
- Phase 2b spec: [`2026-04-10-phase2b-stripe-billing-design.md`](./2026-04-10-phase2b-stripe-billing-design.md) — paywall gating pattern
- Phase 2c spec: [`2026-04-10-phase2c-scanning-batch-pipeline-design.md`](./2026-04-10-phase2c-scanning-batch-pipeline-design.md) — `applications.negotiation_id` nullable column that 2d adds an FK to

---

*End of spec.*
