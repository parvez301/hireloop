# CareerAgent Phase 2b — Stripe Billing + Trial Enforcement Implementation Plan

> **For agentic workers:** Implement tasks in order; use checkbox (`- [ ]`) syntax for tracking.
>
> **Design spec (read first):** [`docs/superpowers/specs/2026-04-10-phase2b-stripe-billing-design.md`](../specs/2026-04-10-phase2b-stripe-billing-design.md)
>
> **Parent spec:** [`docs/superpowers/specs/2026-04-10-careeragent-design.md`](../specs/2026-04-10-careeragent-design.md) — API list, Appendix L.

**Goal:** Wire Stripe Checkout + Customer Portal + webhooks; enforce subscription on Phase 2a routes; populate `AgentState` subscription fields from `subscriptions`; minimal user-portal handling for `TRIAL_EXPIRED`.

**Out of scope:** Admin metrics, Inngest trial emails, Cognito attribute sync, full billing UX polish.

---

## Task 1 — Config and dependencies

- [x] Add `stripe` Python dependency and env vars: `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRICE_PRO_MONTHLY`, `STRIPE_PRICE_PRO_ANNUAL` (or single price for MVP), `APP_URL`, `DISABLE_PAYWALL` (bool).
- [x] Document in `backend/.env.example`.
- [x] Extend `config.py` / settings model with typed fields and safe defaults (`DISABLE_PAYWALL=false`).

**Checkpoint:** `uv sync` / install succeeds; no runtime import of Stripe until T3.

---

## Task 2 — Migration: webhook idempotency

- [x] Add Alembic migration for `stripe_webhook_events` (see design spec §3) **or** document Redis-only idempotency and implement in T4 without a table.
- [x] If table: unique index on `stripe_event_id`.

**Checkpoint:** `alembic upgrade head` runs against dev DB.

---

## Task 3 — Stripe integration module

- [x] Create `integrations/stripe_client.py` (or `services/billing/stripe_service.py`) wrapping Checkout Session, Portal Session, and customer create-if-missing.
- [x] On first checkout, ensure `stripe.Customer` exists; persist `stripe_customer_id` on `subscriptions`.

**Checkpoint:** Unit test with mocked `stripe` SDK for session creation shapes.

---

## Task 4 — Webhook router

- [x] `POST /api/v1/webhooks/stripe` — raw body, signature verification.
- [x] Handle at minimum: `checkout.session.completed`, `customer.subscription.updated`, `customer.subscription.deleted` — sync `subscriptions.status`, `plan`, `stripe_subscription_id`, `current_period_end`, `trial_ends_at` as applicable.
- [x] Idempotency: skip if `stripe_event_id` already processed.

**Checkpoint:** Integration test with constructed payload + test secret from Stripe CLI pattern.

---

## Task 5 — Billing API routes

- [x] `POST /api/v1/billing/checkout` — returns `{ url }` for redirect.
- [x] `POST /api/v1/billing/portal` — returns `{ url }`.
- [x] `GET /api/v1/billing/subscription` — returns subscription DTO for UI.

**Checkpoint:** Authenticated user can hit GET; unauthenticated 401.

---

## Task 6 — `require_active_subscription` dependency

- [x] Implement in `api/deps.py`: load `subscriptions` for `current_user.id`; compute entitlement (trial active, or `status in active/paid` per your mapping).
- [x] If `DISABLE_PAYWALL` env true → return without check.
- [x] Else if not entitled → raise HTTP 403 with `TRIAL_EXPIRED` or `SUBSCRIPTION_REQUIRED`.

**Checkpoint:** Unit tests for date edge cases (trial ends midnight UTC).

---

## Task 7 — Apply dependency to Phase 2a routers

- [x] Add `Depends(require_active_subscription)` to paywalled routes per design spec §2.2 matrix (conversations, evaluations, cv-outputs, jobs parse).
- [x] Do **not** attach to profile, health, billing routes.

**Checkpoint:** Existing integration tests updated; new test proves 403 on expired subscription fixture.

---

## Task 8 — AgentState wiring

- [x] In `core/agent/runner.py` (or state builder), load subscription row and set `subscription_status` + `trial_days_remaining` per spec §2.3.
- [x] Update system prompt injection if needed so trial copy matches real numbers.

**Checkpoint:** Single unit test on state builder with mocked DB row.

---

## Task 9 — User portal minimum UX

- [x] In `user-portal` API client, map `403` + `TRIAL_EXPIRED` to a visible CTA (banner or modal) with button that triggers checkout session POST and `window.location` redirect to returned URL.

**Checkpoint:** Manual or component test that error path renders CTA (optional: MSW).

---

## Task 10 — Wire `main.py` and regression

- [x] Register new routers; run full `pytest backend/tests/`.
- [x] Update Phase 2a smoke test if it assumed unlimited trial without subscription row — seed subscription fixtures.

**Checkpoint:** All tests green; README or plan pointer from Phase 2a “Next phase” satisfied.

---

## File structure (expected)

```
backend/src/career_agent/
├── api/
│   ├── billing.py              [NEW]
│   ├── webhooks.py             [NEW] stripe only, or extend if exists
│   └── deps.py                 [MODIFY]
├── integrations/
│   └── stripe_client.py        [NEW]
├── services/
│   └── subscription.py         [NEW] optional entitlement helpers
├── migrations/versions/
│   └── 0003_phase2b_stripe_webhooks.py   [NEW] if table approach
└── main.py                     [MODIFY]
```

---

## Completion verification

- [x] Paywalled route returns 403 when `trial_ends_at` past and no active paid status.
- [x] Same user succeeds when `DISABLE_PAYWALL=true`.
- [x] Webhook handler + idempotency table implemented (confirm with Stripe CLI + test mode when wiring real keys).
- [x] `GET /billing/subscription` exposed for UI (confirm post-checkout state in test mode as needed).
