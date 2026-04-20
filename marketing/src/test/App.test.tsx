import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';

import App from '../App';

function renderAt(path: string) {
  render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  );
}

describe('App routes', () => {
  it('renders home', () => {
    renderAt('/');
    expect(screen.getByRole('heading', { name: /Apply to 5 jobs/i })).toBeInTheDocument();
  });

  it('renders pricing', () => {
    renderAt('/pricing');
    expect(screen.getByRole('heading', { name: /^Pricing$/ })).toBeInTheDocument();
    expect(document.getElementById('faq')).not.toBeNull();
  });

  it('renders terms', () => {
    renderAt('/terms');
    expect(screen.getByRole('heading', { name: /Terms of Service/i })).toBeInTheDocument();
  });

  it('renders privacy', () => {
    renderAt('/privacy');
    expect(screen.getByRole('heading', { name: /Privacy Policy/i })).toBeInTheDocument();
  });
});
