/**
 * Visual-regression helper: renders each user-portal route and each design
 * prototype HTML file into /tmp/hl-screens/{live,proto}/*.png.
 *
 * NOT a correctness test — it's tooling. Any navigation error is logged to
 * /tmp/hl-screens/errors.json so compare.html can surface it.
 */
import { test, expect, Page, Route } from '@playwright/test';
import fs from 'node:fs/promises';
import path from 'node:path';

// Neutralise the global auth-setup dependency from playwright.config.ts.
test.use({ storageState: { cookies: [], origins: [] } });

const LIVE_DIR = '/tmp/hl-screens/live';
const PROTO_DIR = '/tmp/hl-screens/proto';
const ERRORS_PATH = '/tmp/hl-screens/errors.json';
const VIEWPORT = { width: 1440, height: 900 };
const PROTO_SRC = '/Users/parvez/Downloads/design_handoff_complete';

// JWT-shaped fake id token. Payload is base64url of
// {"sub":"demo","email":"demo@hireloop.dev","exp":<far future>}.
// The app only reads `email` from the claims and checks `exp > now`.
const FAKE_JWT =
  'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.' +
  'eyJzdWIiOiJkZW1vIiwiZW1haWwiOiJkZW1vQGhpcmVsb29wLmRldiIsImV4cCI6NDEwMjQ0NDgwMH0.' +
  'sig';

const errorLog: Array<{ route: string; error: string }> = [];

async function ensureDirs(): Promise<void> {
  await fs.mkdir(LIVE_DIR, { recursive: true });
  await fs.mkdir(PROTO_DIR, { recursive: true });
}

function safeName(input: string): string {
  return input.replace(/[^a-zA-Z0-9._-]+/g, '_').replace(/^_+|_+$/g, '') || 'root';
}

/** Minimal fixture responses keyed by URL substring. */
function fulfillFixture(route: Route, url: string): Promise<void> {
  const now = new Date().toISOString();
  const json = (data: unknown) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(data),
    });

  if (url.includes('/api/v1/profile')) {
    return json({
      data: {
        user_id: 'demo',
        master_resume_md: '# Jane Doe\n\nSenior Engineer',
        master_resume_s3: null,
        parsed_resume_json: { name: 'Jane Doe' },
        target_roles: ['Staff Engineer', 'Principal Engineer'],
        target_locations: ['Remote US'],
        min_salary: 200000,
        preferred_industries: ['SaaS', 'Fintech'],
        work_arrangement: 'remote',
        linkedin_url: 'https://linkedin.com/in/demo',
        github_url: 'https://github.com/demo',
        portfolio_url: null,
        onboarding_state: 'done',
        created_at: now,
        updated_at: now,
      },
    });
  }
  if (url.includes('/api/v1/me/briefing')) {
    return json({
      data: {
        top_jobs: [
          {
            evaluation_id: 'ev1',
            job_id: 'j1',
            title: 'Staff Backend Engineer',
            company: 'Acme',
            location: 'Remote',
            overall_grade: 'A',
            match_score: 92,
            created_at: now,
          },
          {
            evaluation_id: 'ev2',
            job_id: 'j2',
            title: 'Principal Platform Engineer',
            company: 'Globex',
            location: 'NYC',
            overall_grade: 'A-',
            match_score: 88,
            created_at: now,
          },
        ],
        pipeline_counts: { saved: 3, applied: 2, interviewing: 1, offered: 0, rejected: 1, withdrawn: 0 },
        next_prep: { id: 'p1', job_id: 'j1', custom_role: null, created_at: now },
        generated_at: now,
      },
    });
  }
  if (url.includes('/api/v1/billing/subscription')) {
    return json({
      data: {
        id: 'sub1',
        user_id: 'demo',
        plan: 'pro',
        status: 'active',
        trial_ends_at: null,
        current_period_end: '2026-05-23T00:00:00Z',
        past_due_since: null,
        cancel_at_period_end: false,
        stripe_customer_id: 'cus_demo',
        has_active_entitlement: true,
      },
    });
  }
  if (url.includes('/api/v1/applications')) {
    return json({
      data: [
        { id: 'a1', user_id: 'demo', job_id: 'j1', status: 'saved', applied_at: null, notes: null,
          evaluation_id: 'ev1', cv_output_id: null, negotiation_id: null, updated_at: now },
        { id: 'a2', user_id: 'demo', job_id: 'j2', status: 'applied', applied_at: now, notes: null,
          evaluation_id: 'ev2', cv_output_id: null, negotiation_id: null, updated_at: now },
        { id: 'a3', user_id: 'demo', job_id: 'j3', status: 'interviewing', applied_at: now, notes: null,
          evaluation_id: null, cv_output_id: null, negotiation_id: null, updated_at: now },
      ],
    });
  }
  if (url.includes('/api/v1/scan-configs')) {
    return json({
      data: [
        { id: 'sc1', user_id: 'demo', name: 'SaaS Staff roles', companies: [
            { name: 'Acme', platform: 'greenhouse', board_slug: 'acme' },
            { name: 'Globex', platform: 'ashby', board_slug: 'globex' },
          ], keywords: ['python', 'platform'], exclude_keywords: ['manager'],
          schedule: 'daily', is_active: true, created_at: now, updated_at: now },
        { id: 'sc2', user_id: 'demo', name: 'Fintech backend', companies: [
            { name: 'Stripe', platform: 'greenhouse', board_slug: 'stripe' },
          ], keywords: null, exclude_keywords: null,
          schedule: 'weekly', is_active: true, created_at: now, updated_at: now },
      ],
    });
  }
  if (url.includes('/api/v1/scan-runs')) {
    return json({
      data: [
        { id: 'r1', user_id: 'demo', scan_config_id: 'sc1', status: 'completed',
          jobs_found: 42, jobs_new: 7, truncated: false, error: null,
          started_at: now, completed_at: now },
        { id: 'r2', user_id: 'demo', scan_config_id: 'sc2', status: 'completed',
          jobs_found: 18, jobs_new: 2, truncated: false, error: null,
          started_at: now, completed_at: now },
      ],
    });
  }
  if (url.includes('/api/v1/interview-preps')) {
    return json({
      data: [
        { id: 'p1', user_id: 'demo', job_id: 'j1', custom_role: null,
          questions: [{ q: 'Tell me about a time...', category: 'behavioral' }],
          red_flag_questions: null, model_used: 'claude', tokens_used: 1200, created_at: now },
        { id: 'p2', user_id: 'demo', job_id: null, custom_role: 'Engineering Manager',
          questions: [{ q: 'How do you handle conflict?', category: 'leadership' }],
          red_flag_questions: null, model_used: 'claude', tokens_used: 900, created_at: now },
      ],
    });
  }
  if (url.includes('/api/v1/negotiations')) {
    return json({
      data: [
        { id: 'n1', user_id: 'demo', job_id: 'j1',
          offer_details: { base: 210000, equity: '0.05%' },
          market_research: { p50: 215000 },
          counter_offer: { base: 235000 },
          scripts: { email: 'Thanks for the offer...' },
          model_used: 'claude', tokens_used: 1500, created_at: now },
      ],
    });
  }
  if (url.includes('/api/v1/star-stories')) {
    return json({
      data: [
        { id: 's1', user_id: 'demo', title: 'Stabilized legacy pipeline',
          situation: 'Flaky prod jobs', task: 'Cut incidents 80%',
          action: 'Introduced idempotent retries + SLOs', result: 'Incidents dropped 80%',
          reflection: null, tags: ['reliability'], source: 'user_created', created_at: now },
        { id: 's2', user_id: 'demo', title: 'Led migration to event-driven arch',
          situation: 'Monolith at scale', task: 'Unblock team velocity',
          action: 'Built async event bus + dual-write migration', result: 'p99 halved',
          reflection: 'Next time start with consumer-first design', tags: ['architecture'],
          source: 'ai_generated', created_at: now },
      ],
    });
  }
  if (url.includes('/api/v1/conversations')) {
    return json({ data: [] });
  }
  // Fallback: empty list so pages that call arbitrary endpoints don't hang.
  return json({ data: [] });
}

async function wireAuthAndFixtures(page: Page): Promise<void> {
  // Inject before any page scripts run.
  await page.addInitScript(
    ({ token, email }) => {
      try {
        localStorage.setItem('ca:idToken', token);
        localStorage.setItem('ca:userEmail', email);
        localStorage.setItem(
          'ca:expiresAt',
          String(Date.now() + 24 * 60 * 60 * 1000),
        );
      } catch {
        // ignore
      }
    },
    { token: FAKE_JWT, email: 'demo@hireloop.dev' },
  );
  await page.route('**/api/v1/**', (route) => {
    void fulfillFixture(route, route.request().url());
  });
}

async function snapRoute(
  page: Page,
  route: string,
  opts: { authed: boolean },
): Promise<void> {
  const name = safeName(route);
  const out = path.join(LIVE_DIR, `${name}.png`);
  try {
    if (opts.authed) {
      await wireAuthAndFixtures(page);
    }
    await page.setViewportSize(VIEWPORT);
    await page.goto(route, { waitUntil: 'domcontentloaded', timeout: 20_000 });
    // AuthShell on unauth routes; main/body on authed routes.
    if (!opts.authed) {
      await page
        .locator('main, [data-test="auth-shell"]')
        .first()
        .waitFor({ timeout: 10_000 })
        .catch(() => undefined);
    } else {
      await page.locator('body').waitFor({ timeout: 5_000 });
    }
    await page.waitForLoadState('networkidle', { timeout: 10_000 }).catch(() => undefined);
    await page.screenshot({ path: out, fullPage: false });
  } catch (err) {
    errorLog.push({ route, error: (err as Error).message });
    // Save whatever we have so compare.html shows something.
    await page.screenshot({ path: out, fullPage: false }).catch(() => undefined);
  }
}

async function snapProtoFile(
  page: Page,
  fileName: string,
  sectionSteps?: Array<{ selector: string; suffix: string }>,
): Promise<void> {
  const url = 'file://' + path.join(PROTO_SRC, fileName);
  await page.setViewportSize(VIEWPORT);
  try {
    await page.goto(url, { waitUntil: 'load', timeout: 15_000 });
    await page.waitForTimeout(400);
    const base = safeName(fileName.replace(/\.html$/i, ''));
    if (!sectionSteps || sectionSteps.length === 0) {
      await page.screenshot({
        path: path.join(PROTO_DIR, `${base}.png`),
        fullPage: false,
      });
      return;
    }
    for (const step of sectionSteps) {
      try {
        await page.locator(step.selector).first().click({ timeout: 2_000 });
        await page.waitForTimeout(200);
      } catch {
        // Some selectors may not exist on every prototype — skip.
      }
      await page.screenshot({
        path: path.join(PROTO_DIR, `${base}__${step.suffix}.png`),
        fullPage: false,
      });
    }
  } catch (err) {
    errorLog.push({ route: `proto:${fileName}`, error: (err as Error).message });
  }
}

test.describe('visual-regression capture', () => {
  test.beforeAll(async () => {
    await ensureDirs();
  });

  test('capture unauth routes', async ({ browser }) => {
    test.setTimeout(120_000);
    const ctx = await browser.newContext({ viewport: VIEWPORT });
    const page = await ctx.newPage();
    const unauthRoutes = [
      '/login',
      '/signup',
      '/auth/verify',
      '/auth/forgot',
      '/auth/reset?token=FAKE',
    ];
    for (const route of unauthRoutes) {
      await snapRoute(page, route, { authed: false });
    }
    await ctx.close();
    expect(errorLog.length).toBeLessThan(99); // never fail the suite on errors; just record
  });

  test('capture authed routes', async ({ browser }) => {
    test.setTimeout(180_000);
    const ctx = await browser.newContext({ viewport: VIEWPORT });
    const page = await ctx.newPage();
    const authedRoutes = [
      '/',
      '/pipeline',
      '/scans',
      '/interview-prep',
      '/story-bank',
      '/negotiations',
      '/settings/billing',
      '/profile/basics',
    ];
    for (const route of authedRoutes) {
      await snapRoute(page, route, { authed: true });
    }
    await ctx.close();
  });

  test('capture prototype HTML files', async ({ browser }) => {
    test.setTimeout(120_000);
    const ctx = await browser.newContext({ viewport: VIEWPORT });
    const page = await ctx.newPage();

    await snapProtoFile(page, 'Auth Redesign.html');
    await snapProtoFile(page, 'Onboarding Redesign.html');
    await snapProtoFile(page, 'Current Onboarding.html');

    await snapProtoFile(page, 'Post-Onboarding Review.html', [
      { selector: '[data-nav="dashboard"]', suffix: 'dashboard' },
      { selector: '[data-nav="pipeline"]', suffix: 'pipeline' },
      { selector: '[data-nav="scans"]', suffix: 'scans' },
      { selector: '[data-nav="interview"]', suffix: 'interview' },
      { selector: '[data-nav="stories"]', suffix: 'stories' },
      { selector: '[data-nav="negotiation"]', suffix: 'negotiation' },
      { selector: '[data-nav="billing"]', suffix: 'billing' },
    ]);

    await snapProtoFile(page, 'Profile.html', [
      { selector: '.tab-btn[data-tab="basics"]', suffix: 'basics' },
      { selector: '.tab-btn[data-tab="resume"]', suffix: 'resume' },
      { selector: '.tab-btn[data-tab="targets"]', suffix: 'targets' },
      { selector: '.tab-btn[data-tab="social"]', suffix: 'social' },
      { selector: '.tab-btn[data-tab="privacy"]', suffix: 'privacy' },
    ]);

    await ctx.close();
  });

  test.afterAll(async () => {
    await fs.writeFile(ERRORS_PATH, JSON.stringify(errorLog, null, 2));
    if (errorLog.length) {
      // eslint-disable-next-line no-console
      console.log(`[screenshots] ${errorLog.length} route(s) errored — see ${ERRORS_PATH}`);
      for (const entry of errorLog) {
        // eslint-disable-next-line no-console
        console.log(`  - ${entry.route}: ${entry.error}`);
      }
    }
  });
});
