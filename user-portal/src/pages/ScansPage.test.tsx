import { render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import ScansPage from './ScansPage';

const fetchMock = vi.fn();

beforeEach(() => {
  fetchMock.mockReset();
  vi.stubGlobal('fetch', fetchMock);
});

function mockJsonResponse(body: unknown, status = 200) {
  return {
    ok: status < 400,
    status,
    json: async () => body,
  };
}

const baseConfig = {
  id: 'sc-1',
  user_id: 'u-1',
  name: 'Default',
  companies: [{ name: 'Stripe', platform: 'greenhouse' as const, board_slug: 'stripe' }],
  keywords: [] as string[] | null,
  exclude_keywords: [] as string[] | null,
  schedule: 'manual' as const,
  is_active: true,
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
};

const profileWithoutPrefs = {
  data: {
    user_id: 'u-1',
    master_resume_md: '# x',
    master_resume_s3: null,
    parsed_resume_json: null,
    target_roles: null,
    target_locations: null,
    min_salary: null,
    preferred_industries: null,
    linkedin_url: null,
    github_url: null,
    portfolio_url: null,
    onboarding_state: 'done',
    created_at: '2026-04-22T00:00:00Z',
    updated_at: '2026-04-22T00:00:00Z',
  },
};

function mockScansLoadSequence(profile: unknown = profileWithoutPrefs) {
  // load() awaits scanConfigs.list first — the profile useEffect fires during
  // that await — so actual fetch order is configs → profile → runs.
  fetchMock
    .mockResolvedValueOnce(mockJsonResponse({ data: [baseConfig] }))
    .mockResolvedValueOnce(mockJsonResponse(profile))
    .mockResolvedValueOnce(mockJsonResponse({ data: [] }));
}

describe('ScansPage', () => {
  it('loads configs and shows the Scans heading', async () => {
    mockScansLoadSequence();

    render(<ScansPage />);

    expect(screen.getByText('Loading…')).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Scans' })).toBeInTheDocument();
    });
    expect(screen.getByText('Default')).toBeInTheDocument();
  });

  it('shows the JIT preferences banner when target_roles/locations are empty', async () => {
    mockScansLoadSequence();

    render(<ScansPage />);

    await waitFor(() =>
      expect(screen.getByTestId('preferences-needed-banner')).toBeInTheDocument(),
    );
  });

  it('hides the JIT banner when preferences are already set', async () => {
    mockScansLoadSequence({
      data: {
        ...profileWithoutPrefs.data,
        target_roles: ['Senior Backend Engineer'],
        target_locations: ['Remote'],
      },
    });

    render(<ScansPage />);

    await waitFor(() =>
      expect(screen.getByRole('heading', { name: 'Scans' })).toBeInTheDocument(),
    );
    expect(screen.queryByTestId('preferences-needed-banner')).not.toBeInTheDocument();
  });
});
