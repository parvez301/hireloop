import { afterEach, describe, expect, it, vi } from 'vitest';

describe('config', () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.resetModules();
  });

  it('signupUrl strips trailing slash and appends /signup', async () => {
    vi.stubEnv('VITE_USER_PORTAL_URL', 'https://app.example.com/');
    const { signupUrl } = await import('../lib/config');
    expect(signupUrl()).toBe('https://app.example.com/signup');
  });

  it('signupUrl falls back to localhost when env is unset', async () => {
    vi.stubEnv('VITE_USER_PORTAL_URL', undefined);
    const { signupUrl } = await import('../lib/config');
    expect(signupUrl()).toBe('http://localhost:5173/signup');
  });
});
