# Marketing Site Launch — Design Spec

**Date:** 2026-04-16
**Status:** Approved
**Predecessor:** [`2026-04-10-careeragent-design.md`](./2026-04-10-careeragent-design.md) §"Marketing" (parent spec lists the 7 routes but leaves content and design unspecified). This spec narrows scope to the 4 launch-minimum routes and defines everything needed to ship.

---

## Overview

The `marketing/` workspace has been a Phase 1 scaffold — a single placeholder page reading "Landing content TBD in Phase 5" — since the initial commit. This spec closes that out with a minimally viable marketing site that supports the $4.99/mo conversion funnel.

## Goals

1. Launch-quality home, pricing, terms, privacy pages under `hireloop.xyz`.
2. Honest to the product today — no fake testimonials, no authored screenshots, no aspirational features.
3. Fast, quiet, Notion-inspired visual tone matching the existing Tailwind tokens.
4. Copy that maps 1:1 to what the product actually does (six feature modules, $4.99/mo monthly plan, 3-day in-app trial).

## Non-Goals

- `/features`, `/blog`, `/blog/:slug` (deferred — home carries the features story; blog has no content and an empty shell looks worse than no blog).
- Dark mode, scroll animations, gradient heroes.
- Real product screenshots, customer testimonials, or founder-quote storytelling.
- Analytics wiring (PostHog / Plausible / etc. — post-launch).
- Mailing list signup / newsletter embed.
- Real `og-image.png` asset (placeholder committed; real image tracked as post-launch work).
- CDK / CloudFront / S3 deploy pipeline — lives in future **Phase 5a.4 (frontend CDN)**.

---

## Locked Product Decisions

These drive copy and layout. Source of truth in each case noted in parentheses.

| Decision | Value | Source |
|---|---|---|
| Route set | `/`, `/pricing`, `/terms`, `/privacy` | This spec |
| Visual direction | Existing Notion-inspired Tailwind tokens unchanged | `marketing/tailwind.config.ts` |
| Hero angle | Outcome-driven ("Spend your job hunt on interviews, not applications.") | This spec §"Home Page > Hero Copy" |
| Home shape | Hero → Features → How-it-works → Pricing preview → FAQ → Final CTA → Footer | This spec §"Home page" |
| Pricing page | Single-plan card, no comparison | This spec §"Pricing page" |
| Legal | Hand-written plain-language markdown | This spec §"Legal pages" |
| Price | $4.99/month · monthly only | Phase 2b D4 |
| Trial | 3 days in-app, no credit card | Phase 2b D1 / D3a |
| Default scan | 15 companies across Greenhouse / Ashby / Lever | `backend/src/hireloop/core/scanner/default_config.py` |
| Evaluation grading | 10 dimensions, A–F grade | `backend/src/hireloop/core/evaluation/grader.py` |
| AI training policy | Zero-retention — never train on user data | Parent design §"Operational Guardrails" |

---

## Architecture

### Stack
- Existing `marketing/` Vite + React 18 + TypeScript + Tailwind workspace (no new tooling).
- `react-router-dom@6.28` already in `package.json` — this spec is what finally wires it up.
- No new runtime dependencies except `marked` (tiny markdown-to-HTML for legal pages).
- No icon library — features use inline SVGs.

### Routes

| Route | Component | `<title>` |
|---|---|---|
| `/` | `HomePage` | HireLoop — AI job search for senior ICs and managers |
| `/pricing` | `PricingPage` | Pricing — HireLoop |
| `/terms` | `TermsPage` | Terms of Service — HireLoop |
| `/privacy` | `PrivacyPage` | Privacy Policy — HireLoop |

All four wrapped in a shared `<SiteLayout>` providing `<Nav>` at top and `<Footer>` at bottom. Per-route `<title>` handled via a manual `useEffect` shim in each page (avoids adding `react-helmet-async` for 4 routes).

### File Layout

```
marketing/
├── public/
│   ├── favicon.svg                 (HireLoop wordmark — simple placeholder)
│   ├── og-image.png                (1200×630 placeholder — real asset post-launch)
│   ├── robots.txt                  (allow all, sitemap ref)
│   ├── sitemap.xml                 (static, 4 URLs)
│   ├── llms.txt                    (generated at build time)
│   └── llms-full.txt               (generated at build time)
├── scripts/
│   └── generate-llms-txt.ts        (reads content/*, writes public/llms.txt + llms-full.txt)
├── src/
│   ├── App.tsx                     (BrowserRouter, 4 <Route>)
│   ├── main.tsx                    (unchanged)
│   ├── index.css                   (unchanged)
│   ├── components/
│   │   ├── SiteLayout.tsx
│   │   ├── Nav.tsx
│   │   ├── Footer.tsx
│   │   ├── Hero.tsx
│   │   ├── FeatureGrid.tsx
│   │   ├── FeatureCard.tsx
│   │   ├── HowItWorks.tsx
│   │   ├── PricingCard.tsx         (variant: "full" | "compact")
│   │   ├── PricingPreview.tsx      (wraps PricingCard with variant="compact")
│   │   ├── FAQ.tsx                 (takes items: {q,a}[])
│   │   ├── FaqItem.tsx             (native <details>/<summary>)
│   │   ├── FinalCTA.tsx
│   │   └── LegalPage.tsx           (shared wrapper for terms+privacy, renders parsed markdown)
│   ├── pages/
│   │   ├── HomePage.tsx
│   │   ├── PricingPage.tsx
│   │   ├── TermsPage.tsx
│   │   └── PrivacyPage.tsx
│   ├── content/
│   │   ├── copy.ts                 (hero, how-it-works, pricing preview, final CTA, nav/footer strings)
│   │   ├── features.ts             (6 feature entries: {title, summary, icon})
│   │   ├── faq-home.ts             (5 Q&A entries)
│   │   ├── faq-pricing.ts          (5 Q&A entries)
│   │   ├── terms.md                (hand-written markdown)
│   │   └── privacy.md              (hand-written markdown)
│   ├── lib/
│   │   ├── config.ts               (USER_PORTAL_URL, signupUrl())
│   │   └── useDocumentTitle.ts     (hook: sets document.title + meta description on mount)
│   └── test/
│       ├── App.test.tsx
│       ├── Nav.test.tsx
│       ├── FAQ.test.tsx
│       ├── Hero.test.tsx
│       └── config.test.ts
├── index.html                      (SEO meta + og tags updated; title rebrand)
├── .env.example                    (VITE_USER_PORTAL_URL added)
├── vite.config.ts                  (add plugin call to run generate-llms-txt pre-build)
├── package.json                    (add marked, react-router-dom usage, test scripts)
├── tsconfig.json                   (unchanged)
├── tailwind.config.ts              (unchanged — tokens stay)
└── postcss.config.js               (unchanged)
```

### CTA Wiring

All "Start free trial" / "Subscribe" buttons link to `${USER_PORTAL_URL}/signup`.

```ts
// src/lib/config.ts
export const USER_PORTAL_URL = (import.meta.env.VITE_USER_PORTAL_URL ?? 'http://localhost:5173').replace(/\/$/, '');
export const signupUrl = () => `${USER_PORTAL_URL}/signup`;
```

Dev default points at user-portal on `:5173`. Prod env sets `VITE_USER_PORTAL_URL=https://app.hireloop.xyz`.

---

## Home Page

Composition (top to bottom), inside `<SiteLayout>`:

1. **Hero** — full-width, centered content, `max-w-3xl` headline.
2. **Feature grid** — `max-w-5xl`, 6 cards in `grid-cols-1 md:grid-cols-2 lg:grid-cols-3`.
3. **How it works** — 3-step horizontal row on desktop, stacked mobile. Anchor id: `how-it-works`.
4. **Pricing preview** — single compact card centered, with "See full pricing →" link to `/pricing`.
5. **FAQ** — 5 accordion rows using native `<details>`.
6. **Final CTA** — full-width accent-tinted panel, single primary button.
7. **Footer** — 3 columns: brand + tagline, product nav, legal links. Copyright row below.

### Hero Copy

- **Eyebrow:** `Built for senior ICs & managers`
- **Headline:** `Spend your job hunt on interviews, not applications.`
- **Subhead:** `HireLoop scans hundreds of openings, ranks them against your actual experience, and hands you a tailored résumé for the ones worth applying to.`
- **Primary CTA:** `Start 3-day free trial` → `signupUrl()`
- **Secondary CTA:** `How it works →` → scrolls to `#how-it-works`
- **Micro:** `3 days free · $4.99/mo · cancel anytime`

### Feature Grid Copy (`content/features.ts`)

| Title | One-liner |
|---|---|
| **Job evaluation** | Paste any job link. Get an A–F grade across 10 dimensions — skills, comp, seniority, red flags — in under 10 seconds. |
| **Résumé tailoring** | Upload your master résumé once. Every job gets its own ATS-optimized PDF, rewritten to match without inventing experience. |
| **Job scanning** | Track 15 companies on Greenhouse, Ashby, and Lever. New openings are scored against your profile the moment they post. |
| **Batch evaluation** | Drop hundreds of jobs in. Get "12 strong, 23 worth exploring, 165 skip" — sorted, reasoned, ready. |
| **Interview prep** | A STAR story bank built from your real experience, plus role-specific questions with answer frameworks. |
| **Negotiation playbooks** | Market range research, counter-offer scripts, and pushback tactics — ready the day an offer lands. |

Each feature card has an inline SVG icon (24×24, `stroke="currentColor"`, from a minimal set — search, document, rss, layers, chat, handshake).

### How It Works Copy (`HowItWorks.tsx` inline, 3 steps)

1. **Upload your master résumé.** One time. HireLoop extracts your experience into structured data.
2. **Paste a job link or set up scanning.** Greenhouse, Ashby, Lever, or any URL.
3. **Ask for what you need.** "Evaluate this job." "Tailor my résumé." "Prep me for the interview." One chat. Six tools.

### FAQ — Home (`content/faq-home.ts`)

1. **What happens during the free trial?** — Full access to everything — evaluations, résumé tailoring, scanning, batch, interview prep, negotiation. No credit card required to start. When the 3 days end, you'll see a paywall until you subscribe.
2. **Do you train AI on my data?** — No. Your résumé, conversations, and job evaluations are never used to train or fine-tune any AI model. We use API providers (Anthropic, Google) with zero-retention settings enabled.
3. **What job boards does scanning support?** — Greenhouse, Ashby, and Lever — which covers most modern tech and mid-market companies. We're adding more boards as users request them.
4. **Can I cancel anytime?** — Yes. Cancellation is one click in the Stripe customer portal. You keep access until the end of your current billing period, then we stop charging.
5. **What happens to my data if I delete my account?** — All personal data (résumé content, job evaluations, conversations) is deleted within 30 days. Aggregate, anonymized job listings stay in our shared scanning pool so future users benefit from dedup.

### Pricing Preview (compact card)

Inline text: **One plan. $4.99/month. Cancel anytime.** Everything the agent does, no usage caps, 3-day free trial. Link: `See full pricing →`.

### Final CTA Panel

- Headline: `Stop applying. Start interviewing.`
- Button: `Start 3-day free trial` → `signupUrl()`
- Micro: `No credit card to start.`

---

## Pricing Page

Centered `max-w-md` single card:

- **Eyebrow:** `PRO`
- **Price:** `$4.99/mo`
- **CTA:** `Start 3-day free trial` (primary button, full-width)
- **Included list** (✓-prefixed, 6 items):
  - Unlimited job evaluations
  - Tailored résumé PDFs
  - Job scanning (Greenhouse, Ashby, Lever)
  - Batch evaluation of hundreds of jobs at once
  - Interview prep + STAR story bank
  - Negotiation playbooks

Below the card, `<FAQ items={faqPricing} />`.

### FAQ — Pricing (`content/faq-pricing.ts`)

1. **Why $4.99?** — Priced to break even on typical usage. Heavy users cost us more; light users cost us less. We'd rather have you here than churn on price.
2. **Is there an annual plan?** — Not yet. Monthly only while we're learning what usage looks like.
3. **What counts as "unlimited"?** — All six features have no per-action caps during a subscription. We reserve the right to rate-limit abusive usage (thousands of requests per hour) but you'll never hit that in normal job-seeking.
4. **Do you offer refunds?** — If something broke on our end in your first 30 days, email support@hireloop.xyz and we'll refund the month. Outside that, cancellation stops future charges.
5. **I don't want to pay with Stripe.** — Stripe is the only payment processor we support. They handle card data; we don't store it.

---

## Legal Pages

Both `/terms` and `/privacy` use `<LegalPage>`, which:

- Takes a `markdown: string` prop and a `title: string`.
- Uses `marked` to convert to HTML.
- Renders inside `max-w-2xl mx-auto px-6 prose` wrapper with a Tailwind `prose`-style manual CSS (no `@tailwindcss/typography` plugin — roll our own with `[&_h2]:...` etc., keeping deps minimal).

**Markdown trust boundary.** The markdown inputs (`terms.md`, `privacy.md`) are repo-owned, reviewed at commit time, and never mixed with user input. No sanitization layer is included in v1. If any future version routes user-supplied markdown through the same pipeline, add `DOMPurify` after `marked` — that is not needed now.

### Terms of Service Content (approx 800 words)

Sections (all plain-language):
1. **Who we are.** HireLoop, operated by [Company Name TBD at publish time], contact: `legal@hireloop.xyz`.
2. **Using HireLoop.** You must be 18+. You're responsible for the accuracy of information you upload. Don't use the service for illegal activity.
3. **The free trial.** 3 days of full access. No credit card required to start. Access stops at the paywall when the trial ends.
4. **Subscription and billing.** $4.99/month, charged by Stripe. Automatic renewal until you cancel. No refunds except under the conditions described in the [Pricing FAQ](/pricing#faq) ("Do you offer refunds?").
5. **Cancellation.** One click in the Stripe customer portal. Access continues until the end of the current billing period.
6. **Termination.** We may suspend accounts that abuse the service (spam, automation, resource exhaustion, illegal content). You can delete your account anytime from the settings page.
7. **AI-generated content disclaimer.** HireLoop's evaluations, tailored résumés, and advice are generated by AI models. They are tools, not guarantees. You are responsible for reviewing output before acting on it.
8. **Intellectual property.** You keep all rights to content you upload. We keep all rights to the HireLoop platform.
9. **Warranties and liability.** Service is provided "as is." We don't guarantee that any job evaluation, tailored résumé, or advice will result in an interview, offer, or specific outcome. Our liability is limited to the amount you've paid us in the last 12 months.
10. **Changes to these terms.** We'll email active subscribers at least 30 days before any material changes.
11. **Governing law.** [Jurisdiction TBD at publish time — likely Delaware or wherever the operating entity is incorporated].

### Privacy Policy Content (approx 600 words)

Sections:
1. **What we collect.** Account data (email, name), profile data you upload (résumé, preferences), conversation data (messages to the agent), billing metadata (Stripe customer ID — we never see card numbers).
2. **What we don't collect.** We do not collect location data, device fingerprints, or advertising IDs. We do not sell data to third parties.
3. **How we use your data.** To operate the service (evaluate jobs, tailor résumés, etc.) and to keep it running (logs, error tracking). Nothing else.
4. **AI training — the important one.** We do not train or fine-tune AI models on your data, ever. We use AI provider APIs (Anthropic, Google) with zero-retention settings enabled, meaning the providers do not store or train on your content.
5. **Sub-processors.** Stripe (billing), Anthropic (Claude), Google (Gemini), AWS (hosting), Inngest (async jobs). All have enterprise-grade data processing agreements in place.
6. **Your rights.** Access, export, correction, deletion. Email `privacy@hireloop.xyz`. GDPR and CCPA opt-out honored as a matter of practice regardless of your jurisdiction.
7. **Retention.** Active account data retained while your account is active. On deletion, personal data is wiped within 30 days. Anonymized aggregate job listings stay for shared scanning dedup.
8. **Security.** TLS in transit, AES-256 at rest, access controls via AWS IAM, no production database access without MFA.
9. **Cookies.** Only essential session cookies. No tracking or advertising cookies.
10. **Children.** Not for anyone under 18.
11. **Contact.** `privacy@hireloop.xyz`.

**Caveat in spec:** these texts are plain-language boilerplate drafted by Claude. They are **not a substitute for lawyer review** before the service scales or before any material change to data handling. The implementation plan will flag the bracketed `[TBD]` items above (company name, jurisdiction) for human resolution before publish.

---

## Visual System

Tokens are as already defined in `marketing/tailwind.config.ts`:

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
}
```

### Type Ramp (pinned by spec; no changes to `tailwind.config.ts`)

| Use | Classes |
|---|---|
| Hero headline | `text-4xl md:text-5xl font-bold tracking-tight leading-[1.1]` |
| Section heading | `text-3xl font-semibold tracking-tight` |
| Subsection heading | `text-xl font-semibold` |
| Body | `text-base text-text-secondary leading-relaxed` |
| Eyebrow / label | `text-xs font-medium uppercase tracking-wider text-text-secondary` |

### Component Utilities

| Pattern | Classes |
|---|---|
| Card | `bg-card border border-border rounded-lg p-6` |
| Primary button | `bg-accent text-white px-5 py-2.5 rounded-md font-medium transition-opacity hover:opacity-90` |
| Ghost button | `text-text-primary px-4 py-2.5 rounded-md font-medium hover:bg-hover transition-colors` |
| Accordion row | `border-t border-border py-4` (native `<details>`) |

### Layout

| Container | Classes |
|---|---|
| Content pages (home, pricing) | `max-w-5xl mx-auto px-6` inner wrapper |
| Prose pages (terms, privacy) | `max-w-2xl mx-auto px-6` |
| Nav bar outer | full-width `border-b border-border`; inner `max-w-6xl mx-auto px-6` |

### Responsive

Tailwind defaults (`sm` 640, `md` 768, `lg` 1024). No custom breakpoints.

- Feature grid: `grid-cols-1 md:grid-cols-2 lg:grid-cols-3`.
- How it works: `grid-cols-1 md:grid-cols-3`.
- Hero CTA row: `flex-col md:flex-row` with `gap-3`.
- Nav: "Start free trial" button stays visible on mobile; "Pricing" link collapses into a hamburger menu on `sm` (simple CSS-only toggle via `<details>` — no JS dep).

### No dark mode. No scroll animations.

Only `transition-colors` and `transition-opacity` on buttons + links. The Notion aesthetic is quiet.

---

## SEO & Crawler Files

### `index.html` `<head>` replacement

Current file has stale `<title>CareerAgent — AI Career Assistant</title>`. Replace the entire `<head>` inside `<!doctype html>` with:

```html
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<meta name="theme-color" content="#ffffff" />
<link rel="icon" type="image/svg+xml" href="/favicon.svg" />
<link rel="canonical" href="https://hireloop.xyz" />

<title>HireLoop — AI job search for senior ICs and managers</title>
<meta name="description" content="HireLoop scans hundreds of openings, ranks them against your experience, and writes tailored résumés for the ones worth applying to. 3 days free. $4.99/mo." />

<meta property="og:title" content="HireLoop — AI job search for senior ICs and managers" />
<meta property="og:description" content="Scans hundreds of openings, ranks them against your experience, writes tailored résumés. $4.99/mo." />
<meta property="og:image" content="https://hireloop.xyz/og-image.png" />
<meta property="og:type" content="website" />
<meta property="og:url" content="https://hireloop.xyz" />

<meta name="twitter:card" content="summary_large_image" />
<meta name="twitter:title" content="HireLoop" />
<meta name="twitter:description" content="AI job search for senior ICs and managers." />
<meta name="twitter:image" content="https://hireloop.xyz/og-image.png" />
```

### Per-route `<title>` and `<meta name="description">`

Each page calls `useDocumentTitle(title, description)` from `lib/useDocumentTitle.ts` on mount. Implementation sets `document.title` and updates the meta description tag in place. Values listed in the Routes table above.

**SPA SEO limitation.** This is a client-rendered SPA, so crawlers that do not execute JavaScript (e.g., older social-card scrapers, some archival crawlers) will only see the home defaults in `index.html` for every route. Modern search engines (Google, Bing) render JS and will index per-route titles correctly. This is acceptable at launch given launch-minimum scope; if `/pricing` needs perfect non-JS indexing in the future, the options are (a) pre-rendering with `vite-plugin-ssr` or `@vitejs/plugin-legacy`, or (b) migrating to an SSR framework. Tracked as a post-launch consideration.

### `public/robots.txt`

```
User-agent: *
Allow: /

Sitemap: https://hireloop.xyz/sitemap.xml
```

### `public/sitemap.xml`

Static, 4 `<url>` entries for `/`, `/pricing`, `/terms`, `/privacy`, all with `changefreq=monthly` and today's date as `lastmod` (committed as the date of the implementation PR, updated manually when pages change materially).

### `public/llms.txt` — structured markdown index for LLM crawlers

Per [llmstxt.org](https://llmstxt.org) convention. Generated at build time from content sources:

```markdown
# HireLoop

> AI-powered job search for senior ICs and managers. Scans Greenhouse, Ashby, and Lever; evaluates jobs across 10 dimensions with an A–F grade; writes ATS-optimized résumés tailored to each job; preps interviews with a STAR story bank; generates negotiation playbooks. $4.99/month after a 3-day free trial.

## Product
- [Home](https://hireloop.xyz/): overview and features
- [Pricing](https://hireloop.xyz/pricing): single plan — $4.99/month, cancel anytime

## Legal
- [Terms of Service](https://hireloop.xyz/terms)
- [Privacy Policy](https://hireloop.xyz/privacy): HireLoop never trains AI on user data

## Optional
- [llms-full.txt](https://hireloop.xyz/llms-full.txt): full text of all pages
```

### `public/llms-full.txt`

Full markdown dump of all 4 pages' content concatenated with H1 section headers. Built by the same script from `content/*` sources, so it never drifts from the live site.

### Generator script (`scripts/generate-llms-txt.ts`)

Node-executable TypeScript. Reads `src/content/*.ts` (hero/nav/footer/CTA/how-it-works copy from `copy.ts`, features, FAQs) and `src/content/*.md` (legal) and emits both files into `public/`. Hooked as a Vite plugin that runs in the `buildStart` hook, so `npm run build` produces both files fresh. The same script can also run standalone via `tsx scripts/generate-llms-txt.ts` for local debugging.

---

## Configuration

### `marketing/.env.example` update

```
VITE_USER_PORTAL_URL=http://localhost:5173
VITE_ENVIRONMENT=dev
```

(Existing `VITE_APP_URL` key is renamed to `VITE_USER_PORTAL_URL` — `APP_URL` was ambiguous about which app.)

### `marketing/package.json` dependency changes

Add:
- `marked` — markdown parser for legal pages.

No other runtime deps. Dev deps get `@testing-library/react`, `@testing-library/jest-dom`, `vitest`, `jsdom`, `@vitejs/plugin-react` already present — mirror user-portal's test setup.

### Scripts in `package.json`

```json
{
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview",
    "lint": "tsc --noEmit",
    "test": "vitest run",
    "test:watch": "vitest"
  }
}
```

---

## Testing

All tests use Vitest + React Testing Library, mirroring user-portal's harness.

"All tests pass" in the acceptance criteria below means every `test()` / `it()` case in every file passes — not "6 tests total." Each file will typically contain several assertions.

| Test file | Coverage |
|---|---|
| `test/App.test.tsx` | Each of the 4 routes renders without crashing and shows its distinctive heading |
| `test/Nav.test.tsx` | "Start free trial" button `href` resolves to the configured `signupUrl()` |
| `test/FAQ.test.tsx` | Clicking/pressing a `<summary>` toggles the `<details>` `open` attribute (native accordion behavior). jsdom supports `<details>` toggling via `fireEvent.click(summary)` — if behavior is flaky on the installed jsdom version, assert against the `open` attribute directly after dispatching the click. |
| `test/Hero.test.tsx` | Secondary "How it works →" CTA has `href="#how-it-works"` |
| `test/config.test.ts` | `signupUrl()` strips trailing slash, composes correctly, falls back to localhost when env missing |
| `test/generate-llms-txt.test.ts` | Generator produces both files; content includes expected sections |

### Not tested
- Visual regression (no Percy/Chromatic — 4 pages, human review sufficient).
- Exact copy strings (tests break on every copy tweak — copy correctness is a human-review concern).
- Individual meta tag values (one-off static assertion provides low value).

### Must pass before merge
- `npm run build` completes cleanly (Vite + tsc).
- `npm run lint` (`tsc --noEmit`) clean.
- `npm run test` passes (6 tests, all green).
- Lighthouse manual check on the built preview: home hits 95+ on Performance, Accessibility, Best Practices, SEO (desktop).

### Accessibility gates
- FAQ uses native `<details>/<summary>` → keyboard and screen-reader navigation work without additional ARIA.
- All icon-only elements have `aria-label`.
- Contrast: `#37352f` on `#ffffff` = 12.6:1 (AAA). `#787774` on `#ffffff` = 4.6:1 (AA for ≥ 14pt bold or ≥ 18pt normal — we restrict this to secondary body text).

---

## Out of Scope (Post-Launch)

These are real needs but intentionally excluded from this spec to keep scope tight:

- **Real `og-image.png`.** Placeholder is committed; proper design needed before any social sharing push.
- **Favicon beyond a wordmark SVG.** Proper rounded square with PWA-ready sizes is a small follow-up.
- **Production deploy** (S3 + CloudFront wiring). Deferred to Phase 5a.4.
- **Analytics.** Lightweight product analytics (Plausible recommended — privacy-friendly, matches our AI training stance).
- **Blog.** Phase 2 of marketing once we have real stories to tell.
- **Lawyer-reviewed legal text.** The hand-written boilerplate is a starting point; a solo engineer's lawyer pass is the next step.
- **Dynamic company logos on scanning feature.** "We scan Stripe, Figma, Notion, Anthropic, Linear…" as a marquee would be nice; adds complexity to a launch-minimum spec.

---

## Acceptance Criteria

- [ ] All 4 routes render without errors, each with correct `<title>` and meta description.
- [ ] All CTAs ("Start free trial", "Subscribe") link to `${VITE_USER_PORTAL_URL}/signup`.
- [ ] `<FAQ>` components expand/collapse via native `<details>`, no JS state.
- [ ] `public/robots.txt`, `public/sitemap.xml` exist; both reference correct URLs.
- [ ] `public/llms.txt` and `public/llms-full.txt` are generated from `content/*` by the build.
- [ ] `index.html` `<head>` updated with the replacement block above.
- [ ] `marketing/.env.example` uses `VITE_USER_PORTAL_URL`.
- [ ] `marketing/package.json` adds `marked` and a `test` script.
- [ ] All 6 Vitest tests pass.
- [ ] `npm run build` + `npm run lint` clean.
- [ ] Manual Lighthouse run on the preview build shows 95+ across all 4 categories (desktop).
- [ ] Bracketed `[TBD]` items in terms/privacy (company name, jurisdiction) are resolved before publish (tracked in implementation plan as the gating item for the merge).
- [ ] Privacy policy sub-processor list (Stripe, Anthropic, Google, AWS, Inngest) is reconciled against actual production integrations before publish — any provider not in production at publish time is removed, any provider in production but not listed is added.
