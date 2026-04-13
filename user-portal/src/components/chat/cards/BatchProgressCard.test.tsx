import { render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { BatchProgressCard } from './BatchProgressCard';

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

describe('BatchProgressCard', () => {
  it('renders batch title and status from API', async () => {
    fetchMock.mockResolvedValue(
      mockJsonResponse({
        data: {
          batch_run: {
            id: 'br-1',
            user_id: 'u-1',
            status: 'completed',
            total_jobs: 4,
            l0_passed: 4,
            l1_passed: 3,
            l2_evaluated: 2,
            source_type: 'scan_run_id',
            source_ref: 'sr-1',
            started_at: new Date().toISOString(),
            completed_at: new Date().toISOString(),
          },
          items_summary: {
            queued: 0,
            l0: 0,
            l1: 0,
            l2: 0,
            done: 2,
            filtered: 2,
          },
          top_results: [],
        },
      }),
    );

    render(
      <BatchProgressCard
        data={{
          batch_run_id: 'br-1',
          status: 'running',
          total: 4,
          l0_passed: 0,
          l1_passed: 0,
          l2_evaluated: 0,
        }}
      />,
    );

    expect(screen.getByText('Batch evaluation')).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText(/status: completed/)).toBeInTheDocument();
    });
  });
});
