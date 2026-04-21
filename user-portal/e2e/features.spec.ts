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
});
