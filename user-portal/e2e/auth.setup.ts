import { test as setup, expect } from '@playwright/test';
import path from 'node:path';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const authFile = path.join(here, '.auth/user.json');
const EMAIL = process.env.PW_USER_EMAIL ?? 'playwright@hireloop.test';
const PASSWORD = process.env.PW_USER_PASSWORD ?? 'PlaywrightT3st!2026';

setup('authenticate via real Cognito Hosted UI', async ({ page }) => {
  fs.mkdirSync(path.dirname(authFile), { recursive: true });

  await page.goto('/');
  await page.waitForURL(/amazoncognito\.com/, { timeout: 15_000 });

  const visibleUser = page.locator('input[name="username"]:visible');
  await visibleUser.waitFor({ state: 'visible', timeout: 10_000 });
  await visibleUser.fill(EMAIL);
  await page.locator('input[name="password"]:visible').fill(PASSWORD);
  await page.locator('input[name="signInSubmitButton"]:visible').click();

  // Wait for callback page, then the post-callback redirect
  await page.waitForURL(/localhost:5173\/auth\/callback/, { timeout: 20_000 });
  await page.waitForURL(
    (url) => url.origin === 'http://localhost:5173' && !url.pathname.startsWith('/auth/callback'),
    { timeout: 15_000 },
  );
  await page.waitForLoadState('networkidle');

  const idToken = await page.evaluate(() => window.localStorage.getItem('ca:idToken'));
  expect(idToken, 'ca:idToken should be a JWT after login').toMatch(/^ey[A-Za-z0-9_-]+\./);

  await page.context().storageState({ path: authFile });
});
