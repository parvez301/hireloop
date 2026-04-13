import { render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import PipelinePage from './PipelinePage';

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

describe('PipelinePage', () => {
  it('renders Pipeline heading and kanban columns', async () => {
    fetchMock.mockResolvedValue(mockJsonResponse({ data: [] }));

    render(<PipelinePage />);

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Pipeline' })).toBeInTheDocument();
    });
    expect(screen.getByText('Saved')).toBeInTheDocument();
    expect(screen.getByText('Applied')).toBeInTheDocument();
  });
});
