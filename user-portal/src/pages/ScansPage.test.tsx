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

describe('ScansPage', () => {
  it('loads configs and shows the Scans heading', async () => {
    fetchMock
      .mockResolvedValueOnce(mockJsonResponse({ data: [baseConfig] }))
      .mockResolvedValueOnce(mockJsonResponse({ data: [] }));

    render(<ScansPage />);

    expect(screen.getByText('Loading…')).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Scans' })).toBeInTheDocument();
    });
    expect(screen.getByText('Default')).toBeInTheDocument();
  });
});
