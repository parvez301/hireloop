# Onboarding Redesign — Resume-First Funnel with Evaluation Wow

**Date:** 2026-04-22
**Status:** Draft, pending implementation plan
**Parent:** `docs/superpowers/specs/2026-04-10-careeragent-design.md`
**Predecessors in onboarding stack:** `backend/src/hireloop/services/profile.py` (existing state machine), `backend/src/hireloop/api/profile.py` (resume endpoint).

## Problem

A fresh authenticated user lands on `ChatPage` with a blank message list and the placeholder "Tell your agent what to do…". There is no signal about what the product does, no prompt for the profile data every module depends on, and no guided first action. Because every feature (evaluate, CV, prep, negotiation, scan, pipeline) is resume-dependent at its core, a user who types into chat before completing their profile gets either a stub response or a "complete onboarding first" error. The current experience effectively hides the product.

The backend already encodes a three-step state machine (`resume_upload → preferences → done`) with a trial-start hook on the transition to `done`, but this machine has no corresponding frontend surface.

## Goal

When a fresh user finishes signup and arrives at `app.dev.hireloop.xyz`, they reach a concrete moment of demonstrated value (a real evaluation of a real job they chose) in under 90 seconds, and they are never confronted with an empty page that has nothing to offer.

## Non-goals

- Redesigning any of the six post-onboarding module pages (chat, scans, pipeline, story bank, interview prep, negotiations). This spec only designs onboarding itself plus the single payoff screen.
- Introducing a router library (react-router, tanstack-router, etc.). The existing hand-rolled `matchRoute` in `App.tsx` remains.
- Mobile-first layouts. Portal is desktop-first; the payoff screen degrades gracefully on mobile but is not optimized for it.
- Reworking the profile or resume parsing backend. That API exists and works.
- Free-vs-paid interaction changes. Trial-start hook semantics stay identical (fire on `onboarding_state='done'`).

## Key decisions (from brainstorming)

- **D1. Hard gate = resume only.** Until the user has a parsed resume (`profile.resume_text` non-empty), every route except onboarding, auth-callback, billing, and subscribe-redirect is redirected to the onboarding page. Resume upload is the single unskippable step.
- **D2. "Wow moment" = W2.** The user pastes/enters one job URL (or raw job text) during onboarding, and is landed on a full evaluation card for that job. No preferences collection, no scan trigger, no tour — one concrete output they chose the target of.
- **D3. Preferences (`target_roles`, `target_locations`) is demoted from onboarding.** It becomes a just-in-time collection the first time the user visits `/scans`. Rationale: none of the wow-moment outputs (evaluate, CV, prep, negotiation) need preferences. Only scanning does.
- **D4. Parse failures are recoverable, not fatal.** On resume-parse or job-parse failure, the user sees an inline paste-text fallback with a one-click retry. After two failed attempts, the user may contact support but can also force-advance with whatever we parsed.
- **D5. Design language = marketing site.** The user portal adopts the marketing gradient (`#14b8a6 → #2563eb → #7c3aed`), the grade-tier color system (A=teal→green, A-=teal→cobalt, B+=cobalt→violet, B=violet→purple), radial-gradient panel washes, and gradient-filled section titles. Design tokens in `tailwind.config.ts` are already identical; the gradient system lives in components and is adopted incrementally starting with the onboarding surface.
- **D6. Payoff layout = Y** (evaluation card + persistent "what's next" sidebar). The sidebar holds content-action CTAs (Tailor CV, Prep Q&A, Save to pipeline) and one visually-distinct upsell card (Unlock scanning) that navigates to `/scans` for the preferences nudge.

## Backend changes

### State machine

`backend/src/hireloop/services/profile.py`:

- `_advance_onboarding` becomes a two-state machine: `resume_upload → done`. The `preferences` state is removed from the advancement path — if a profile has a parsed resume, it transitions directly to `done`.
- Existing `Profile.onboarding_state` rows with value `'preferences'` are migrated to `'done'` via an Alembic migration. The column keeps the `'preferences'` value legal (no enum change) to preserve the state-machine as a documented historical value and avoid a destructive migration; new writes never produce it.
- `_on_onboarding_done` hook (trial-start, default-scan-seed) is unchanged. It still fires on the `→ done` transition, now triggered by resume upload rather than preferences submission.
- The `has_prefs` local inside `_advance_onboarding` is no longer used in the advancement logic but remains as a derived field on the profile response for the frontend to read (to render the "preferences needed" badge on `/scans`).

### New endpoint: `POST /profile/resume-text`

`backend/src/hireloop/api/profile.py` gains a companion to the existing `POST /profile/resume` (PDF/DOCX upload). Accepts a JSON body `{ "text": "..." }` with a `max_length=50_000` validator and calls the same downstream parser/structurer as the file endpoint. This is the paste-text fallback for D4.

### New endpoint: `POST /jobs/parse-text`

`backend/src/hireloop/api/jobs.py` gains a paste-text variant of the URL parser. Accepts `{ "text": "...", "source_url": "..." | null }`. The `source_url` is stored as a reference when present but the LLM structures only the pasted text. Same rationale as above — the fallback for when URL fetching fails (paywalled boards, redirect loops, JS-rendered pages).

### Onboarding endpoint (new, single-purpose)

`POST /onboarding/first-evaluation`: accepts `{ "job_input": {"type": "url", "value": "..."} | {"type": "text", "value": "..."} }`, orchestrates parse-job-then-evaluate server-side, returns the evaluation envelope ready to render. Rationale: the frontend otherwise has to chain `/jobs/parse` → `/evaluations` with error handling at each step; collapsing into one server call simplifies the loading UX and lets us tune the prompt/caching choices for the onboarding-specific first evaluation (we may choose to use a smaller/faster model here).

## Frontend changes

### Routing

`user-portal/src/App.tsx`:

- New route `onboarding` matched on `pathname === '/onboarding'`.
- A new `requiresProfile(route)` predicate returns `true` for all routes except `signup`, `login`, `auth-callback`, `billing`, `subscribe-redirect`, and `onboarding`.
- On route change: if the user is authenticated, `requiresProfile(route)` is `true`, and `profile.onboarding_state !== 'done'`, replace the history to `/onboarding`.
- The fallthrough default remains `chat` (not onboarding), so users who have completed onboarding go where they expect.

### New page: `OnboardingPage`

Path: `user-portal/src/pages/OnboardingPage.tsx`.

A three-step wizard with progress indication:

1. **Step 1 — Welcome & Resume.** Header: "Let's get you set up in under a minute." Explains what HireLoop will do with the resume in one sentence. File-upload zone (drag-drop + click) accepting PDF/DOCX, plus a "Paste text instead" link that reveals a textarea with a word-count hint. On successful parse, advances to step 2. On parse failure, reveals the paste-text textarea inline with the raw server error above it; retry up to twice, then surface "Continue anyway — we'll use what we got" link that calls the resume endpoint with whatever text/file content we had on the last attempt.
2. **Step 2 — Pick your first job.** Header: "Paste a job you're curious about. We'll show you how you stack up." Text input labeled "Job URL or job description." Submit button copy: "Evaluate". The input is a single field with auto-detection: if the value looks like a URL (starts with `http`), we call `/onboarding/first-evaluation` with `type=url`; otherwise `type=text`. Same failure handling as step 1 — on failure, surface a paste-text textarea.
3. **Step 3 — Evaluating.** A full-screen loading state that replaces the wizard. Layout: centered gradient-ring spinner, the user's uploaded resume summary on the left (single line: "Senior Backend Engineer · 8 yrs"), the parsed job title on the right (single line: "Senior Backend Engineer · Acme"), a three-step progress list below ("Parsing job description", "Comparing to your profile", "Writing evaluation") that animates through over ~60s. The only call is `POST /onboarding/first-evaluation` which returns the full envelope when done. On success, navigate to `/onboarding/evaluation/:id`. On failure, navigate back to step 2 with the error.

### New page: `OnboardingPayoffPage`

Path: `user-portal/src/pages/OnboardingPayoffPage.tsx`, route `/onboarding/evaluation/:id`.

Two-column layout (desktop). On mobile the sidebar stacks below the card.

**Left column (2fr): Evaluation card.** Reuses the existing `EvaluationCard` primitive from `user-portal/src/components/chat/cards/EvaluationCard.tsx` rendered at full width (the same primitive today's chat uses, lifted out of the chat container), with one addition: the overall score is rendered in a large gradient badge using the grade-tier color system (A/A-/B+/B/C) via the new `GradientBadge` component. The card background has the radial-gradient wash from `Hero.tsx` at reduced opacity. No new `EvaluationDetailPage` route is created — the page lives at `/onboarding/evaluation/:id` only.

**Right column (1fr): "What's next?" sidebar.** Four cards, vertically stacked:

1. **Tailor my CV for this role** — primary gradient button styling, matches marketing CTAs. Because there is no CV-output detail page on the frontend and CV generation currently runs through the agent pipeline, this CTA navigates to `/` (chat) after creating a new conversation pre-seeded with a message "Tailor my CV for job {job_id}" that auto-sends on page load. The agent's existing `create_cv_output` tool handles the generation; the chat card is the detail view. (Building a dedicated `/cv-outputs/:id` page is explicitly a non-goal of this spec.)
2. **Generate interview prep** — secondary card styling (solid background, no gradient). Calls `POST /api/v1/interview-preps` with `{ job_id }` directly via a new `api.createInterviewPrep` wrapper, then navigates to `/interview-prep/:id` (the existing detail page).
3. **Save to pipeline** — secondary card styling. Calls `POST /api/v1/applications` with `{ job_id, status: 'saved' }` via the existing `api.createApplication`, then shows an inline "Saved ✓ view pipeline →" confirmation without navigating.
4. **(Upsell) Unlock job scanning** — visually distinct: dashed top-border separator, subtitle "Tell us where you want to work — we'll find more jobs like this." Navigates to `/scans` (the just-in-time preferences collection lives there per D3).

The "Save to pipeline" action is the one side-effect CTA that does not navigate. All others navigate to their respective detail creation flows.

Completing step 3 (seeing the payoff page) is what marks `onboarding_state='done'` server-side. The `POST /onboarding/first-evaluation` endpoint fires the transition after successful evaluation persistence. The frontend does not need to explicitly advance state.

### Design-token adoption

`user-portal/tailwind.config.ts` is extended with the marketing gradient stops as named colors so component code can reference `accent-teal`, `accent-cobalt`, `accent-violet` without repeating hex values:

```ts
colors: {
  // existing Notion-ish palette preserved
  'accent-teal': '#14b8a6',
  'accent-cobalt': '#2563eb',
  'accent-violet': '#7c3aed',
}
```

A new shared component `user-portal/src/components/ui/GradientButton.tsx` extracts the marketing rounded-full primary button pattern (gradient fill, colored drop-shadow, hover translate). This component is used for the primary CTAs in onboarding and is available to the rest of the app for future adoption.

A new shared component `user-portal/src/components/ui/GradientBadge.tsx` wraps the grade-tier color system for evaluation scores. Takes a grade prop (`'A' | 'A-' | 'B+' | 'B' | 'C'`) and numeric score, renders the gradient-filled rounded-square badge from the marketing `LiveDemo`.

### API surface additions in `user-portal/src/lib/api.ts`

Thin wrappers only — no new backend endpoints behind them:

- `api.createInterviewPrep({ job_id })` → `POST /api/v1/interview-preps`
- `api.submitOnboardingFirstEvaluation({ job_input })` → `POST /api/v1/onboarding/first-evaluation` (new backend endpoint from this spec)
- `api.submitResumeText({ text })` → `POST /api/v1/profile/resume-text` (new backend endpoint from this spec)

`api.createApplication` already exists and is used for the Save-to-pipeline CTA. CV output creation and evaluation creation are intentionally NOT added to the frontend API surface — those are still agent-tool-owned per the Phase 2a design.

### Failure-mode wireframing

Three discrete failure surfaces must be implemented:

- **Resume parse fail:** inline banner above the upload zone with the sanitized error, plus the paste-text textarea revealed automatically. Two retries then the "Continue anyway" escape hatch.
- **Job parse fail (URL):** inline banner above the input, plus the paste-text textarea revealed with the user's pasted URL preserved as a disabled field labeled "Original URL (we'll keep this as a reference)." Two retries then support-contact copy.
- **Evaluation fail (LLM timeout, bridge down, etc.):** navigate back to step 2 with a banner. If three consecutive evaluations fail, offer "Skip this step — you can evaluate jobs from the main app" which sets `onboarding_state='done'` without a first evaluation.

The "skip" escape for evaluation is an acknowledgment that the bridge or the LLM could be broken at any given moment and we shouldn't trap users in onboarding if the product itself is degraded.

## Testing

### Backend

- `test_profile_service_advance_to_done.py` — asserts `_advance_onboarding` transitions `resume_upload → done` on resume presence alone, and the `_on_onboarding_done` hook is invoked once.
- `test_profile_service_preferences_not_blocking.py` — asserts a profile with resume but no preferences reaches `done`.
- `test_profile_resume_text_endpoint.py` — POST `/profile/resume-text` happy path + validation errors.
- `test_jobs_parse_text_endpoint.py` — POST `/jobs/parse-text` happy path + validation errors.
- `test_onboarding_first_evaluation.py` — full pipeline from URL/text input through evaluation row creation, asserts state-machine advancement.
- Alembic migration test: existing `'preferences'` rows flip to `'done'`.

### Frontend

Extend `user-portal/e2e/features.spec.ts`:

- New test: "Onboarding — full flow" that uploads a real PDF resume (fixture), pastes a job URL (fixture markup served by Playwright's route interception so we don't hit a real external site), waits for the payoff page, and asserts the evaluation card renders.
- New test: "Onboarding — resume paste fallback" that uploads a corrupt fixture, asserts the paste-text textarea surfaces, pastes text, completes the flow.
- New test: "Onboarding — evaluation skip" that fails the `/onboarding/first-evaluation` endpoint three times via route interception and asserts the "Skip this step" escape lands the user in `/`.
- Update the existing "Scans — create scan config end-to-end" test to include the just-in-time preferences prompt on first visit.

Manual verification on prod: the 60s wait state must render progressively (not just a frozen spinner). Verify by throttling network in Chrome DevTools.

## Rollout

1. Backend lands first: state machine tweak, paste-text endpoints, onboarding-first-evaluation endpoint. Migration included.
2. Frontend lands second: OnboardingPage + OnboardingPayoffPage + shared gradient components + router gate.
3. Design-system components (`GradientButton`, `GradientBadge`) are checked for use by future module redesigns, but this spec does not rewrite existing pages.
4. After ship: manual prod dogfood sweep using a fresh Cognito user. Each failure mode exercised at least once.

## Open questions (resolved)

- *Does preferences stay in onboarding?* No (D3). Moved to `/scans` as JIT collection.
- *Do we block the 4 content-action CTAs on preferences submission?* No. Only "Unlock scanning" needs preferences, and that's its own path.
- *What if the user closes the tab mid-onboarding?* `profile.onboarding_state` is persisted after resume upload, so they resume at step 2 when they return. If they close during step 2, they resume at step 2 with their resume intact.
- *What about users who already have `onboarding_state='done'` in the DB from the old three-step machine?* Unaffected. They continue to default-route to chat.

## Explicitly not resolved in this spec

- Visual polish of the `EvaluationDetail` card in its own right. It's reused as-is.
- Mobile breakpoint behavior of the payoff-page sidebar (stacked below is the fallback; a dedicated mobile layout is not in scope).
- Analytics/telemetry on funnel drop-off. Useful follow-up but out of scope here.
- Whether `/onboarding/first-evaluation` should use a cheaper/faster model than the general `/evaluations` endpoint. Can be decided during implementation.
