import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './test',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [['list']],
  use: {
    baseURL: 'http://127.0.0.1:4000',
  },
  webServer: {
    command: 'npx tsx src/server.ts',
    url: 'http://127.0.0.1:4000/health',
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
