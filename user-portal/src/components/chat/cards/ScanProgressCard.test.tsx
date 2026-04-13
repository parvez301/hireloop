import { render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ScanProgressCard } from './ScanProgressCard';

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

describe('ScanProgressCard', () => {
  it('renders scan name and completes state from API', async () => {
    fetchMock.mockResolvedValue(
      mockJsonResponse({
        data: {
          scan_run: {
            id: 'sr-1',
            user_id: 'u-1',
            scan_config_id: 'sc-1',
            status: 'completed',
            jobs_found: 5,
            jobs_new: 2,
            truncated: false,
            error: null,
            started_at: new Date().toISOString(),
            completed_at: new Date().toISOString(),
          },
          results: [],
        },
      }),
    );

    render(
      <ScanProgressCard
        data={{
          scan_run_id: 'sr-1',
          scan_name: 'My scan',
          status: 'running',
          companies_count: 3,
        }}
      />,
    );

    expect(screen.getByText(/Scanning — My scan/)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText(/Found/)).toBeInTheDocument();
    });
    expect(screen.getByText(/5/)).toBeInTheDocument();
  });
});
