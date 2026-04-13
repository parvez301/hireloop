import { render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import ScanDetailPage from './ScanDetailPage';

const fetchMock = vi.fn();

beforeEach(() => {
  fetchMock.mockReset();
  vi.stubGlobal('fetch', fetchMock);
  window.history.pushState({}, '', '/scans/run-abc');
});

afterEach(() => {
  window.history.pushState({}, '', '/');
});

function mockJsonResponse(body: unknown, status = 200) {
  return {
    ok: status < 400,
    status,
    json: async () => body,
  };
}

describe('ScanDetailPage', () => {
  it('shows scan status when detail loads', async () => {
    const scan_run = {
      id: 'run-abc',
      user_id: 'u-1',
      scan_config_id: 'sc-1',
      status: 'completed' as const,
      jobs_found: 3,
      jobs_new: 2,
      truncated: false,
      error: null,
      started_at: new Date().toISOString(),
      completed_at: new Date().toISOString(),
    };

    fetchMock.mockResolvedValue(
      mockJsonResponse({
        data: {
          scan_run,
          results: [],
        },
      }),
    );

    render(<ScanDetailPage />);

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Scan run' })).toBeInTheDocument();
    });
    expect(screen.getByText(/Status: completed/)).toBeInTheDocument();
  });
});
