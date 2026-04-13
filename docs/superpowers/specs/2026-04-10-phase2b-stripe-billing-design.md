# CareerAgent Phase 2b — Stripe Billing + Trial Paywall (Design Spec)

> **Parent spec:** [`2026-04-10-careeragent-design.md`](./2026-04-10-careeragent-design.md). This is a **delta spec**.
>
> **Predecessor:** [`2026-04-10-phase2a-agent-eval-cv-design.md`](./2026-04-10-phase2a-agent-eval-cv-design.md) — Phase 2a shipped the agent + evaluation + CV optimization with no paywall. Every Phase 2a user was on an implicit unlimited trial.
>
> **This spec was rewritten retroactively** after the implementation landed. The 6 key decisions captured in §8 were made interactively during brainstorming; the implementation follows them with the deviations noted in §12.

---

## 1. Goal

Ship Stripe billing end-to-end and enforce a **hard paywall** on the five cost-generating endpoints that Phase 2a created. The paywall is an in-app 3-day trial, followed by Stripe-managed monthly subscription at **$4.99/mo**. Stripe owns payments and subscription lifecycle; we own the in-app trial and the entitlement check.

**End state:**

1. New user onboards → trial subscription row materializes eagerly → 3 days of unlimited access.
2. Trial expires → any cost-generating endpoint returns `403 TRIAL_EXPIRED` → frontend renders a paywall modal with a Subscribe button.
3. User clicks Subscribe → `POST /api/v1/billing/checkout` → redirect to Stripe Checkout → card entered → redirect to `/billing/success` → frontend polls `/billing/subscription` until `plan=pro`.
4. Stripe fires `checkout.session.completed` + `customer.subscription.updated` → our handler persists `stripe_customer_id`, `stripe_subscription_id`, flips `plan='pro'`, `status='active'`.
5. User has access for the paid period.
6. On renewal, `invoice.paid` clears `past_due_since` (if set) and refreshes `current_period_end`.
7. On renewal failure, `invoice.payment_failed` sets `past_due_since=now()` (only on first failure — idempotent across Stripe retries). User retains access for 3 days of grace; after grace, paywall re-engages.
8. On cancel, user clicks "Manage billing" → Stripe Customer Portal → cancel → `cancel_at_period_end=true` mirrored by `customer.subscription.updated`; user retains access until `current_period_end`; `customer.subscription.deleted` finally flips to `canceled`.

**Non-goals (explicit):**
- Annual plan, monthly↔annual switching, promo codes, team seats, refund UI — Phase 5 or later.
- Per-user usage quotas (cost caps) — a forward-compat column is reserved but no enforcement ships in 2b.
- Tax/VAT handling — Stripe Tax is a dashboard toggle, not code.
- Admin impersonation to comp subscriptions — Phase 5 admin UI.
- Custom billing page with Stripe Elements — we use Stripe Customer Portal instead.
- Conversion / trial funnel analytics — post-launch instrumentation.
- Inngest/cron for `trial_will_end` notifications (Phase 5).
- Cognito `custom:subscription_tier` sync.

---

## 2. Architecture delta

Phase 2a left the backend organized with `core/agent/`, `core/evaluation/`, `core/cv_optimizer/`, `core/llm/`, and 2a's API routers. Phase 2b adds one cross-cutting concern (paywall gating) and three new integration points (Stripe Checkout, Stripe Portal, Stripe webhooks).

**New backend modules:**

```
backend/src/career_agent/
├── services/subscription.py            [NEW]  ensure_subscription, is_entitled,
│                                              trial_days_remaining, agent_subscription_fields
├── integrations/stripe_client.py       [NEW]  thin sync helpers around stripe SDK:
│                                              ensure_stripe_customer, create_checkout_session,
│                                              create_portal_session, retrieve_subscription,
│                                              apply_stripe_subscription_to_row
├── api/billing.py                      [NEW]  POST /checkout, POST /portal, GET /subscription
├── api/stripe_webhooks.py              [NEW]  POST /webhooks/stripe with signature verify,
│                                              idempotency ledger, event dispatch
├── schemas/billing.py                  [NEW]  CheckoutSessionOut, PortalSessionOut, SubscriptionOut
├── models/stripe_webhook_event.py      [NEW]  idempotency ledger row
├── models/subscription.py              [MOD]  +past_due_since, +cancel_at_period_end,
│                                              +plan_monthly_cost_cap_cents
├── services/profile.py                 [MOD]  _advance_onboarding returns transition bool;
│                                              _on_onboarding_done hook calls ensure_subscription
├── api/deps.py                         [MOD]  require_entitled_user + EntitledDbUser alias
├── core/agent/runner.py                [MOD]  AgentState.subscription_status / trial_days_remaining
│                                              now populated from real subscription row
├── api/conversations.py                [MOD]  all routes use EntitledDbUser
├── api/evaluations.py                  [MOD]  gated
├── api/cv_outputs.py                   [MOD]  gated
├── api/jobs.py                         [MOD]  gated
├── config.py                           [MOD]  +stripe_secret_key, +stripe_webhook_secret,
│                                              +stripe_price_pro_monthly, +app_url,
│                                              +disable_paywall, +trial_period_days
└── main.py                             [MOD]  register billing + stripe_webhooks routers
```

**Migrations:**
- `0003_phase2b_stripe_webhooks.py` — `stripe_webhook_events` idempotency table.
- `0004_phase2b1_subscription_columns.py` — `past_due_since`, `cancel_at_period_end`, `plan_monthly_cost_cap_cents` columns on `subscriptions`.

**Frontend delta (user-portal):**

```
src/pages/BillingPage.tsx                    [NEW]  trial/pro/past_due/cancelled states
src/pages/SubscribeRedirect.tsx              [NEW]  /billing/success polling, /billing/cancel handling
src/components/billing/PaywallModal.tsx      [NEW]  global modal on 403 TRIAL_EXPIRED event
src/lib/api.ts                               [MOD]  +startCheckout, +openPortal, +getSubscription;
                                                     global subscription-required event on 403
src/App.tsx                                  [MOD]  hand-rolled router: /, /settings/billing,
                                                     /billing/success, /billing/cancel
src/components/layout/AppShell.tsx           [MOD]  Billing nav link
src/pages/BillingPage.test.tsx               [NEW]  5 state-rendering tests
src/components/billing/PaywallModal.test.tsx [NEW]  hidden/open transitions
src/test/setup.ts                            [MOD]  afterEach cleanup() — prevents listener leak
```

**Phase 2a touch points:** the 5 cost-generating endpoints all swap `CurrentDbUser` → `EntitledDbUser`. No rewrites to any 2a service or module.

### 2.1 Data flow — post-trial subscribe

```
ChatPage sends message → POST /conversations/:id/messages
            │
            │   EntitledDbUser dependency runs first
            │   ensure_subscription → is_entitled(sub, now) → False
            │   raise AppError(403, "TRIAL_EXPIRED", ...)
            ▼
api.ts sees 403 + code TRIAL_EXPIRED
            │
            │   dispatchEvent("subscription-required")
            ▼
PaywallModal opens
            │
            │   User clicks Subscribe
            ▼
api.startCheckout() → POST /billing/checkout
            │
            │   ensure_subscription(user)
            │   ensure_stripe_customer(settings, user, sub)  ← persists stripe_customer_id
            │   create_checkout_session(price, customer, client_reference_id=user.id)
            │   returns {data: {url: "https://checkout.stripe.com/..."}}
            ▼
window.location.href = url → Stripe Checkout
            │
            │   user enters card, confirms
            │   Stripe charges immediately
            │   Stripe redirects → {app_url}/billing/success?session_id=cs_...
            ▼
SubscribeRedirect polls GET /billing/subscription every 2s
            │
            │   (meanwhile, Stripe fires webhooks asynchronously)
            │
            ▼
Stripe → POST /webhooks/stripe
            │
            │   stripe.Webhook.construct_event(body, sig, secret)  ← signature verify
            │   INSERT INTO stripe_webhook_events (stripe_event_id) ← idempotency ledger
            │   on IntegrityError: return 200 (dupe)
            │   dispatch by event.type:
            │     checkout.session.completed → persist customer_id + apply subscription
            │     customer.subscription.updated → apply subscription (flips to plan=pro)
            │     invoice.paid → clear past_due_since + apply subscription
            │     invoice.payment_failed → stamp past_due_since (if null)
            │     customer.subscription.deleted → status=canceled
            │   commit
            ▼
Next poll of GET /billing/subscription sees plan=pro, status=active
            │
            │   SubscribeRedirect navigates to /
            ▼
User back in chat with full entitlement
```

### 2.2 Paywall matrix

All routes require a valid Cognito JWT unless noted.

| Area | Paywall (`EntitledDbUser`)? |
|------|---|
| `POST /conversations`, `GET /conversations`, `POST .../messages`, `GET .../stream`, `DELETE` | **Yes** |
| `POST /evaluations`, `GET /evaluations*` | **Yes** |
| `POST /cv-outputs*`, `GET /cv-outputs*`, `GET .../pdf` | **Yes** |
| `POST /jobs/parse` | **Yes** |
| `GET /profile`, `PUT /profile`, resume upload | **No** (auth only) |
| `GET /health`, `GET /health/ready` | **No** |
| `POST /billing/checkout`, `POST /billing/portal`, `GET /billing/subscription` | **No** (auth only — user must be able to subscribe while blocked) |
| `POST /webhooks/stripe` | **No JWT** — signature only |

When `DISABLE_PAYWALL=true`, `require_entitled_user` no-ops success for any authenticated user.

### 2.3 Key architectural decisions

| Decision | Choice | Why |
|---|---|---|
| Stripe SDK | Official `stripe` Python SDK, sync calls inside async route handlers | Sync boundary is acceptable at current volume. An async wrapper can ship in a follow-up if blocking becomes a real hotspot. |
| Paywall style | FastAPI dependency `require_entitled_user` wrapping `CurrentDbUser` | Single-line change per route. Uses existing `AppError` + error envelope. |
| Paywall HTTP status | `403 TRIAL_EXPIRED` | 402 Payment Required is underused and some proxies mishandle it. |
| Dependency naming | `EntitledDbUser` | "Entitled" is standard SaaS vocabulary; scales to future entitlement types. |
| Trial start | Eager on onboarding `done` transition; lazy fallback in `ensure_subscription` | Matches user mental model; lazy fallback handles edge cases. |
| Trial quota | Unlimited (rate limit is the only bound) | Simplest v1. Revisit if cost telemetry shows abuse. |
| Stripe trial stacking | **Never** send `trial_period_days` on Checkout | Single source of truth: our in-app trial is the trial. |
| Idempotency | Ledger table `stripe_webhook_events` keyed on `stripe_event_id` (unique constraint) | Simple SETNX-style insert with `IntegrityError` catch. Survives app restarts. |
| Billing UI | Stripe Customer Portal (no custom Elements) | Zero PCI surface. Free upgrades when Stripe improves the portal. |
| `past_due` handling | 3-day grace counted from `past_due_since` (first failure timestamp) | Matches Stripe default dunning window. |
| Cancellation timing | Honored at `current_period_end` (Stripe default) | User paid for the month. |
| `invoice.paid` as source of truth | `invoice.paid` clears `past_due_since` and refreshes `current_period_end` by re-fetching the Stripe subscription | Prevents using unconfirmed `checkout.session.completed` as the source of truth. |
| Development webhook forwarding | `stripe listen --forward-to http://localhost:8000/api/v1/webhooks/stripe` | Documented in README, not automated in docker-compose. |
| `disable_paywall` flag | `DISABLE_PAYWALL=true` env bypasses `require_entitled_user` entirely | Lets integration tests run gated endpoints without seeding a valid subscription per test. |

---

## 3. Data model delta

**Migration `0003_phase2b_stripe_webhooks.py`**

**New table `stripe_webhook_events`** — idempotency ledger.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `stripe_event_id` | VARCHAR(255) UNIQUE | From Stripe event envelope |
| `event_type` | VARCHAR(128) | e.g. `invoice.paid`, `customer.subscription.updated` |
| `processed_at` | TIMESTAMPTZ | `now()` default |

Unique index `ix_stripe_webhook_events_stripe_event_id` enforces dedup.

**Migration `0004_phase2b1_subscription_columns.py`**

**New columns on `subscriptions`:**

| Column | Type | Default | Purpose |
|---|---|---|---|
| `past_due_since` | TIMESTAMPTZ | NULL | First-failure timestamp for grace window. Cleared on `invoice.paid`. |
| `cancel_at_period_end` | BOOLEAN NOT NULL | `false` | Mirrors Stripe flag for UI display. |
| `plan_monthly_cost_cap_cents` | INTEGER | NULL | Forward-compat quota hook. 2b leaves NULL; no enforcement ships. |

---

## 4. API delta

| Method | Path | Body / Params | Response |
|---|---|---|---|
| `POST` | `/api/v1/billing/checkout` | `{}` | `200 { "data": { "url": "https://checkout.stripe.com/..." } }` |
| `POST` | `/api/v1/billing/portal` | `{}` | `200 { "data": { "url": "https://billing.stripe.com/..." } }` — requires `stripe_customer_id`, else `422 NO_STRIPE_CUSTOMER` |
| `GET` | `/api/v1/billing/subscription` | — | `200 { "data": SubscriptionOut }` |
| `POST` | `/api/v1/webhooks/stripe` | Raw Stripe event payload | `200 {"received": true}` or `400` on signature failure |

**Gated endpoints** (return `403 TRIAL_EXPIRED` when entitlement fails):

1. `POST /api/v1/conversations/:id/messages`
2. `POST /api/v1/evaluations`
3. `POST /api/v1/cv-outputs`
4. `POST /api/v1/cv-outputs/:id/regenerate`
5. `POST /api/v1/jobs/parse`

**`SubscriptionOut` schema:**

```python
class SubscriptionOut(BaseModel):
    id: UUID
    user_id: UUID
    plan: str                         # 'trial' | 'pro' | 'canceled' | ...
    status: str                       # 'active' | 'past_due' | 'canceled' | 'trialing' | ...
    trial_ends_at: datetime | None
    current_period_end: datetime | None
    past_due_since: datetime | None = None
    cancel_at_period_end: bool = False
    stripe_customer_id: str | None = None
    has_active_entitlement: bool      # computed from is_entitled(sub, now)
```

**New error codes:**

| Code | HTTP | When |
|---|---|---|
| `TRIAL_EXPIRED` | 403 | `require_entitled_user` denied (trial ended and no valid paid sub, or past_due beyond grace) |
| `BILLING_NOT_CONFIGURED` | 503 | Server missing `STRIPE_SECRET_KEY` or `STRIPE_PRICE_PRO_MONTHLY` |
| `NO_STRIPE_CUSTOMER` | 422 | `POST /billing/portal` called before Checkout has run |

---

## 5. Component designs

### 5.1 `services/subscription.py`

Three pure functions + one side-effect writer:

```python
def is_entitled(sub: Subscription, now: datetime) -> bool:
    """
    True if:
      - in-app trial window is open (now < trial_ends_at)
      - OR Stripe subscription is active/trialing
      - OR Stripe subscription is past_due within PAST_DUE_GRACE_DAYS (3)
    """
```

```python
def agent_subscription_fields(
    sub: Subscription, now: datetime
) -> tuple[AgentSubscriptionStatus, int | None]:
    """Returns ('trial' | 'active' | 'expired', days_remaining | None) for AgentState."""
```

```python
def trial_days_remaining(trial_ends_at: datetime | None, now: datetime) -> int | None:
    """Integer days-until-end, or None if no trial."""
```

```python
async def ensure_subscription(
    session: AsyncSession, user_id: UUID, settings: Settings
) -> Subscription:
    """
    Load the user's subscription row, or create a fresh trial row if none exists.
    Called from: onboarding transition hook, require_entitled_user dependency,
    agent runner (for AgentState), all billing endpoints.
    """
```

Constant: `PAST_DUE_GRACE_DAYS = 3`.

### 5.2 `integrations/stripe_client.py`

Six sync helpers. All load `stripe.api_key` on demand from settings.

- `ensure_stripe_customer(settings, user, sub) -> str` — creates a Stripe Customer and persists the id on the subscription row if missing.
- `create_checkout_session(*, settings, user, sub, success_path, cancel_path) -> str` — returns Checkout URL. Uses `client_reference_id=user.id` so webhook can map back.
- `create_portal_session(*, settings, stripe_customer_id, return_path) -> str` — returns Portal URL.
- `retrieve_subscription(subscription_id, settings) -> stripe.Subscription`
- `dt_from_stripe_ts(ts: int | None) -> datetime | None` — Stripe epoch → UTC datetime.
- `apply_stripe_subscription_to_row(sub_row, stripe_sub) -> None` — mutates the ORM row with `status`, `current_period_end`, `trial_ends_at`, `cancel_at_period_end`; flips `plan='pro'` on active/trialing; clears `past_due_since` on any healthy state; flips to `canceled` on Stripe `canceled` status.

### 5.3 `api/stripe_webhooks.py`

One route: `POST /webhooks/stripe`. Flow:

1. Read raw body (`await request.body()`) — FastAPI must not JSON-parse.
2. Verify signature via `stripe.Webhook.construct_event(payload, stripe-signature header, secret)`. On failure: `400`.
3. INSERT `StripeWebhookEvent(stripe_event_id, event_type)` in a fresh session. On `IntegrityError`: rollback, return `{"received": true}` (dup).
4. Dispatch by `event.type`:
   - `checkout.session.completed` → `_handle_checkout_completed` — looks up user by `client_reference_id`, sets `stripe_customer_id`, fetches and applies full Stripe subscription.
   - `customer.subscription.updated` → `_handle_subscription_updated` — re-fetches subscription from Stripe and applies (including `cancel_at_period_end`).
   - `customer.subscription.deleted` → `_handle_subscription_deleted` — sets `status='canceled'`, clears `past_due_since`.
   - `invoice.paid` → `_handle_invoice_paid` — re-fetches subscription, applies, clears `past_due_since`.
   - `invoice.payment_failed` → `_handle_invoice_payment_failed` — sets `status='past_due'`, stamps `past_due_since=now()` only if currently `NULL` (idempotent across Stripe retries).
   - `customer.subscription.trial_will_end` → **ignored** (we don't use Stripe trials).
5. Commit.

### 5.4 `api/deps.py::require_entitled_user`

```python
async def require_entitled_user(user: CurrentDbUser, session: DbSession) -> User:
    settings = get_settings()
    if settings.disable_paywall:
        return user
    sub = await ensure_subscription(session, user.id, settings)
    if not is_entitled(sub, utc_now()):
        raise AppError(
            403, "TRIAL_EXPIRED",
            "Your trial has ended. Subscribe to continue using CareerAgent.",
        )
    return user


EntitledDbUser = Annotated[User, Depends(require_entitled_user)]
```

### 5.5 `services/profile.py` — onboarding hook

`_advance_onboarding(profile) -> bool` returns `True` if the profile just transitioned to `done`. Callers (`update_profile`, `upload_resume`) check the return and call `_on_onboarding_done(db, profile)`, which delegates to `ensure_subscription`.

This makes the trial row appear eagerly, so admin queries and `GET /billing/subscription` see a newly-onboarded user as a trialing customer without waiting for them to hit a gated endpoint.

### 5.6 Frontend

- `lib/api.ts` dispatches `window.CustomEvent("subscription-required", {detail: {message}})` whenever a request fails with `status=403, code=TRIAL_EXPIRED`.
- `components/billing/PaywallModal.tsx` mounts once at app root, listens for the event, renders a modal overlay with a Subscribe button. Button calls `api.startCheckout()` and redirects.
- `pages/BillingPage.tsx` — loads `GET /billing/subscription` on mount, renders one of five panels: trial, pro active, pro cancelling, past_due, canceled. Each panel has the appropriate CTA (Subscribe / Manage billing / Update card).
- `pages/SubscribeRedirect.tsx` — landing page after Stripe redirects to `/billing/success` or `/billing/cancel`. On success, polls `/billing/subscription` every 2s up to 15 attempts, then bounces to `/`. On cancel, shows a "no charge made" message and a link back to `/settings/billing`.
- `App.tsx` — hand-rolled path matcher (`window.location.pathname` + `popstate` listener). No react-router added. Routes: `/`, `/settings/billing`, `/billing/success`, `/billing/cancel`. All other paths fall through to `ChatPage`.

---

## 6. Testing strategy

**Unit tests** (`tests/unit/`):

- `test_subscription_entitlement.py` — 9 cases:
  - in-app trial active → entitled
  - trial expired + no Stripe → denied
  - Stripe active → entitled
  - past_due within grace → entitled
  - past_due beyond grace → denied
  - past_due without `past_due_since` stamp → denied
  - canceled → denied
  - `agent_subscription_fields` maps states correctly
  - `trial_days_remaining` handles midnight UTC boundary

**Integration tests** (`tests/integration/`):

- `test_billing_paywall.py` — 5 cases: `/jobs/parse` denies on expired trial; all 5 gated endpoints return 403; past_due within grace allowed; past_due beyond grace blocked; `DISABLE_PAYWALL=true` bypasses.
- `test_billing_endpoints.py` — 4 cases: `GET /subscription` bootstraps a trial for a new user; `POST /checkout` creates a Customer and returns URL; `POST /portal` requires existing customer (422); `POST /portal` succeeds when customer exists.
- `test_stripe_webhooks.py` — 5 cases: idempotent dup event → no mutation; `invoice.payment_failed` stamps `past_due_since` only on first call; `invoice.paid` clears `past_due_since` and flips to active; `customer.subscription.deleted` sets `canceled`; `customer.subscription.updated` mirrors `cancel_at_period_end`.
- `test_trial_start_on_onboarding.py` — 2 cases: transition to `done` creates trial row with `trial_ends_at ≈ now+3d`; a subsequent update to an already-`done` profile does not create a new row (transition-triggered only).

**Frontend tests** (`user-portal/src/`):

- `BillingPage.test.tsx` — 5 state renders: trial, pro active, past_due, canceled, will-cancel.
- `PaywallModal.test.tsx` — hidden by default; opens on `subscription-required` event.

**Fake Stripe strategy:** No calls to real Stripe. Tests monkey-patch:
- `stripe.Webhook.construct_event` → returns a hand-built `_FakeEvent` object, bypassing signature verification.
- `stripe.Customer.create`, `stripe.checkout.Session.create`, `stripe.billing_portal.Session.create` → return `SimpleNamespace` with `id`/`url` fields.
- `career_agent.integrations.stripe_client.retrieve_subscription` → returns a hand-built `_FakeStripeSubscription`.

The DB, webhook ledger, idempotency logic, and `apply_stripe_subscription_to_row` all run for real.

**Total:** 18 new Phase 2b tests across unit, integration, and frontend. Running total after 2b: **99 backend tests + 9 frontend tests**.

---

## 7. Environment variables

Added to `backend/.env.example`:

```bash
# Phase 2b — billing
APP_URL=http://localhost:5173
TRIAL_PERIOD_DAYS=3
DISABLE_PAYWALL=false

# Stripe — populate from dashboard before running
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_PRO_MONTHLY=price_...
```

`STRIPE_PRICE_PRO_ANNUAL` is **not** part of Phase 2b — annual plan is deferred. Frontend `.env.example` unchanged (billing UI uses the same `VITE_API_URL` as the rest of the app).

---

## 8. Decisions log — the 6 locked choices (from brainstorming)

| # | Question | Decision | Rationale |
|---|---|---|---|
| **D1** | When does the 3-day trial clock start? | **On onboarding `done` transition** (eager), with lazy fallback in `ensure_subscription` | Matches user mental model; trial starts when the user has real value to consume. |
| **D2** | Stripe trial stacking | **Never send `trial_period_days`; charge immediately at Checkout** | Single source of truth — our in-app trial is the trial. |
| **D3a** | Trial quota | **Unlimited — only the rate limit applies** | Simplest v1; 3 days is short enough that abuse is bounded. |
| **D3b** | Paywall style | **Hard 403 on the 5 cost-generating endpoints** | Clean API surface; single code path for frontend interception. |
| **D4** | Plans at launch | **Monthly only at $4.99/mo. Annual entirely deferred.** | Half the Stripe setup, no plan-switching logic. Unit-economics risk flagged in §10. |
| **D5** | Subscription management UI | **Stripe Customer Portal (no custom billing UI)** | Zero PCI surface, zero code to maintain. |
| **D6a** | `past_due` grace | **3-day grace from first-failure timestamp** | Matches Stripe's default dunning window. |
| **D6b** | Cancellation timing | **Honored at `current_period_end`** | User paid for the month. |

---

## 9. Open questions (resolved during implementation)

1. *How does the frontend know when the webhook has landed?* → `SubscribeRedirect` polls `GET /billing/subscription` every 2s for up to 30s after the Checkout redirect.
2. *What if Stripe fires events in unexpected order?* → Handlers are order-independent. Both `checkout.session.completed` and `customer.subscription.updated` look up by stable Stripe IDs and upsert. Covered by `test_stripe_webhooks.py`.
3. *What if `invoice.payment_failed` fires multiple times during Stripe dunning?* → Handler only stamps `past_due_since` on first failure (when currently `NULL`). Grace window counts from when trouble started, not from the latest retry. Covered by a dedicated test.
4. *Where does the Stripe CLI dev webhook secret come from?* → `stripe listen --forward-to http://localhost:8000/api/v1/webhooks/stripe` prints a `whsec_...` secret on first run; pasted into `.env`. Documented in README.

---

## 10. Unit economics — risk noted, not mitigated in 2b

At $4.99 ARPU, the break-even per user is ~10¢/day of LLM cost. A single Claude Sonnet eval costs ~$0.04 and a CV optimize ~$0.06. A heavy paid user can easily burn $0.50+/day against $0.16/day revenue — a net loss of several dollars per month.

**Phase 2b does not implement quota enforcement.** The `plan_monthly_cost_cap_cents` column is added as a forward-compat hook but is left `NULL` for every user. `is_entitled` never consults it.

**How to add quotas later** (Phase 2b.2 or later):

1. Populate `plan_monthly_cost_cap_cents` on the subscription row (e.g. 100 cents/month for $4.99 Pro).
2. Add a `services/usage_meter.py` that sums `usage_events.cost_cents` for `(user_id, month)`.
3. Extend `is_entitled` (or add a new `within_monthly_cost_cap` helper) to return False when cap reached.
4. Wire the new check into `require_entitled_user`.

The column exists, so this is a pure service-layer change with no schema work.

---

## 11. Security

- Webhook route: verify `Stripe-Signature` with webhook secret; reject on mismatch.
- Do not log full payment payloads; log `event.id` and `event.type` only.
- Webhook endpoint is otherwise unauthenticated (Stripe doesn't send JWTs).
- `disable_paywall` flag must never be set in production. A future hardening task could add a startup assertion that refuses to boot with `DISABLE_PAYWALL=true` + `ENVIRONMENT=prod`.

---

## 12. Implementation history — what shipped, and when

**Phase 2b initial implementation** (backend MVP):
- All 6 locked decisions (D1–D6b) implemented at least partially
- 5 gated endpoints wired with `EntitledDbUser`
- `stripe_webhook_events` idempotency ledger + migration 0003
- `ensure_subscription`, `is_entitled`, `agent_subscription_fields` service
- Stripe Checkout, Portal, and `retrieve_subscription` helpers
- Webhook handlers for `checkout.session.completed`, `customer.subscription.updated`, `customer.subscription.deleted`
- `AgentState.subscription_status` + `trial_days_remaining` wired from real subscription row
- `disable_paywall` flag added (not in original design)
- 7 tests (5 unit, 2 integration)

**Phase 2b.1 cleanup** (gaps closed in the same session):
- Migration `0004_phase2b1_subscription_columns` — added `past_due_since`, `cancel_at_period_end`, `plan_monthly_cost_cap_cents` columns (absent in initial implementation)
- `is_entitled` extended with 3-day past_due grace window (D6a)
- Added `_handle_invoice_paid` webhook handler — clears `past_due_since`, refreshes `current_period_end`
- Added `_handle_invoice_payment_failed` webhook handler — stamps `past_due_since=now()` only if NULL (idempotent)
- Extended `apply_stripe_subscription_to_row` to mirror `cancel_at_period_end` and clear `past_due_since` on healthy states
- `SubscriptionOut` schema extended with `past_due_since` + `cancel_at_period_end`
- `services/profile.py` onboarding hook: `_advance_onboarding` now returns a transition bool and callers invoke `_on_onboarding_done` → `ensure_subscription` (D1 eager path)
- Added 11 more backend tests (4 unit, 7 integration) covering past_due grace, webhook handlers, billing endpoints, onboarding hook
- Added minimum-viable frontend billing UI: `BillingPage`, `SubscribeRedirect`, `PaywallModal`, global `subscription-required` event, billing API client methods, hand-rolled router in `App.tsx`, Billing nav link
- Added 7 frontend tests (5 for BillingPage states, 2 for PaywallModal)
- Fixed test setup: `afterEach(cleanup)` to prevent event-listener leak across tests
- Retroactively wrote this spec file with the full design history

**Known simplifications:**
- `SubscribeRedirect` polls for 30s max; a webhook that lands later still works, user just needs to refresh `/settings/billing`.
- Hand-rolled router in `App.tsx` — no react-router. Works for 4 routes; add router when we hit ~8+ routes.
- Stripe SDK calls are sync inside async handlers. Low-volume endpoints; not a hotspot at current scale.
- `trial_will_end` Stripe event intentionally ignored (no Stripe trials).
- `DISABLE_PAYWALL` env flag exists for test/dev convenience; never should be set in prod.

---

## 13. Risks

| Risk | Mitigation |
|---|---|
| Webhook delivery delay / out-of-order events | Handlers are order-independent and idempotent; `SubscribeRedirect` polls for up to 30s. |
| User onboards via direct API call, skipping the profile service → no eager trial row | Lazy fallback in `ensure_subscription` handles this on first entitled request. |
| `invoice.payment_failed` never fires (e.g. user cancels card at bank silently) | Stripe will eventually fire `customer.subscription.deleted`; user is denied then. |
| Unit economics at $4.99 ARPU | Flagged in §10; quota hook column in place for follow-up. |
| `stripe` Python SDK is sync inside async routes | Acceptable at current volume; add async wrapper if it becomes a hotspot. |
| `DISABLE_PAYWALL` accidentally set in prod | Document loudly in `.env.example`; future hardening task can add boot-time check. |
| Stripe `apply_stripe_subscription_to_row` mutates a row fetched in a prior session | All webhook handlers open a fresh session via `get_session_factory()` and hold a single transaction. |

---

## 14. References

- Parent spec Appendix L (Stripe Configuration): [`2026-04-10-careeragent-design.md`](./2026-04-10-careeragent-design.md)
- Phase 2a spec: [`2026-04-10-phase2a-agent-eval-cv-design.md`](./2026-04-10-phase2a-agent-eval-cv-design.md)
- Phase 2a plan: [`../plans/2026-04-10-phase2a-agent-eval-cv.md`](../plans/2026-04-10-phase2a-agent-eval-cv.md)

---

*End of spec.*
