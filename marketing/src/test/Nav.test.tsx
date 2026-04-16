import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';

describe('Nav', () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.resetModules();
  });

  it('links Start free trial to signup URL', async () => {
    vi.stubEnv('VITE_USER_PORTAL_URL', 'https://app.example.com');
    const { Nav } = await import('../components/Nav');
    const { signupUrl } = await import('../lib/config');
    render(
      <MemoryRouter>
        <Nav />
      </MemoryRouter>,
    );
    const cta = screen.getByRole('link', { name: /Start free trial/i });
    expect(cta).toHaveAttribute('href', signupUrl());
  });
});
