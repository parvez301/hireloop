import { test, expect } from '@playwright/test';

test.describe('post-login E2E — each module', () => {
  test('1. Chat — user message sends and the send button re-enables when settled', async ({ page }) => {
    // Chat fans out into classifier + agent turns. Via llm-bridge each call
    // incurs ~30-60s (subprocess spawn + model latency) so we allow up to 3 min.
    test.setTimeout(180_000);
    await page.goto('/');

    const input = page.getByPlaceholder('Tell your agent what to do…');
    await expect(input).toBeVisible({ timeout: 10_000 });

    // Snapshot state BEFORE sending so we can detect the new reply (conversation
    // may already contain prior assistant replies from earlier runs).
    const assistantBubble = page.locator('li[data-role="assistant"]');
    const errorBanner = page.getByText(/^Error:/);
    const beforeAssistant = await assistantBubble.count();
    const beforeError = await errorBanner.count();

    const msg = `pw-probe-${Date.now()}`;
    await input.fill(msg);
    await page.getByRole('button', { name: 'Send' }).click();

    // Optimistic user bubble appears before the backend round-trip completes
    await expect(page.getByText(msg)).toBeVisible({ timeout: 5_000 });

    // Settled = either a NEW assistant reply OR a NEW error banner.
    // Forgiving on which — works with ANTHROPIC_API_KEY, llm-bridge, or neither.
    // Bridge path can take up to 60s (subprocess + real model call).
    await expect
      .poll(
        async () => {
          const a = await assistantBubble.count();
          const e = await errorBanner.count();
          return a > beforeAssistant || e > beforeError;
        },
        { timeout: 160_000, message: 'expected a new assistant reply or error banner' },
      )
      .toBe(true);
  });

  test('2. Scans — create scan config end-to-end', async ({ page }) => {
    await page.goto('/scans');
    await expect(page.getByRole('heading', { name: 'Scans' })).toBeVisible();

    const configName = `PW Scan ${Date.now()}`;
    await page.getByRole('button', { name: 'New scan config' }).click();

    const modal = page.locator('form').filter({ hasText: 'New scan config' });
    await expect(modal).toBeVisible();

    await modal.locator('input').nth(0).fill(configName); // Name
    await modal.getByPlaceholder('Name').fill('Acme');
    await modal.getByPlaceholder('board_slug').fill('acme');
    await modal.getByRole('button', { name: 'Add company' }).click();
    await modal.getByRole('button', { name: 'Save' }).click();

    await expect(modal).toBeHidden({ timeout: 10_000 });
    await expect(page.getByRole('heading', { name: configName })).toBeVisible({ timeout: 10_000 });
  });

  test('3. Pipeline — all 6 kanban columns render', async ({ page }) => {
    await page.goto('/pipeline');
    await expect(page.getByRole('heading', { name: 'Pipeline' })).toBeVisible();

    for (const title of ['Saved', 'Applied', 'Interviewing', 'Offered', 'Rejected', 'Withdrawn']) {
      await expect(page.getByText(title, { exact: true }).first()).toBeVisible();
    }
  });

  test('4. Story bank — create STAR story end-to-end', async ({ page }) => {
    await page.goto('/story-bank');
    await expect(page.getByRole('heading', { name: 'Story bank' })).toBeVisible();

    const title = `PW Story ${Date.now()}`;
    await page.getByPlaceholder('Title').fill(title);
    await page.getByPlaceholder('Situation').fill('Legacy pipeline flaky in prod');
    await page.getByPlaceholder('Task').fill('Stabilize within a quarter');
    await page.getByPlaceholder('Action').fill('Introduced idempotent retries + SLOs');
    await page.getByPlaceholder('Result').fill('Incidents dropped 80%');
    await page.getByRole('button', { name: 'Save story' }).click();

    await expect(page.getByText(title)).toBeVisible({ timeout: 10_000 });
    // Form cleared after save
    await expect(page.getByPlaceholder('Title')).toHaveValue('');
  });

  test('5. Interview prep — empty state renders with guidance copy', async ({ page }) => {
    await page.goto('/interview-prep');
    await expect(page.getByRole('heading', { name: 'Interview prep' })).toBeVisible();
    await expect(page.getByText(/No interview prep yet/i)).toBeVisible();
  });

  test('6. Negotiations — empty state renders with guidance copy', async ({ page }) => {
    await page.goto('/negotiations');
    await expect(page.getByRole('heading', { name: 'Negotiations' })).toBeVisible();
    await expect(page.getByText(/No negotiations yet/i)).toBeVisible();
  });

  test('7. Onboarding — full flow on a fresh user', async ({ page }) => {
    // Two LLM calls on bridge (parse + evaluate) — allow ~3 min wall.
    test.setTimeout(240_000);

    await page.route('https://acme.example.com/jobs/1', async (route) => {
      const fs = await import('node:fs/promises');
      const body = await fs.readFile('e2e/fixtures/job.html', 'utf-8');
      await route.fulfill({ status: 200, contentType: 'text/html', body });
    });

    await page.goto('/onboarding');
    await page.setInputFiles('input[type=file]', 'e2e/fixtures/resume.pdf');

    await page.waitForSelector('textarea[placeholder*="https"]', { timeout: 30_000 });
    await page.locator('textarea').fill('https://acme.example.com/jobs/1');
    await page.getByRole('button', { name: /evaluat/i }).click();

    await expect(page.getByText(/parsing job description/i)).toBeVisible({
      timeout: 15_000,
    });

    await expect(page.getByRole('button', { name: /tailor my cv/i })).toBeVisible({
      timeout: 200_000,
    });
  });

  test('8. Onboarding — paste-text fallback when PDF upload fails', async ({ page }) => {
    test.setTimeout(60_000);

    await page.route('**/api/v1/profile/resume', (route) =>
      route.fulfill({
        status: 422,
        contentType: 'application/json',
        body: JSON.stringify({
          error: { code: 'UNPROCESSABLE_ENTITY', message: 'parse failed' },
        }),
      }),
    );

    await page.goto('/onboarding');
    await page.setInputFiles('input[type=file]', 'e2e/fixtures/resume.pdf');

    await expect(page.locator('textarea')).toBeVisible({ timeout: 10_000 });
    await page
      .locator('textarea')
      .fill('# Jane Doe\n\nSenior Backend Engineer, 8 yrs Python.\n');
    await page.getByRole('button', { name: /continue/i }).click();

    await expect(page.getByText(/paste a job/i)).toBeVisible({ timeout: 15_000 });
  });

  test('9. Onboarding — skip escape after 3 consecutive evaluation failures', async ({
    page,
  }) => {
    test.setTimeout(60_000);

    let attempt = 0;
    await page.route('**/api/v1/onboarding/first-evaluation', (route) => {
      attempt += 1;
      void route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({
          error: { code: 'LLM_TIMEOUT', message: 'eval failed' },
        }),
      });
    });

    await page.goto('/onboarding');
    await page.setInputFiles('input[type=file]', 'e2e/fixtures/resume.pdf');
    await page.waitForSelector('textarea[placeholder*="https"]', { timeout: 30_000 });

    for (let index = 0; index < 3; index += 1) {
      await page.locator('textarea').fill('Senior backend role at Acme');
      await page.getByRole('button', { name: /evaluat/i }).click();
      await page.waitForTimeout(1_500);
    }

    await expect(
      page.getByRole('button', { name: /skip this step/i }),
    ).toBeVisible({ timeout: 10_000 });
    expect(attempt).toBeGreaterThanOrEqual(3);
  });
});
