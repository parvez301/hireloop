import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { FeedbackWidget } from './FeedbackWidget';

const post = vi.fn().mockResolvedValue({ data: { id: 'fb-1' } });

vi.mock('../../lib/api', () => ({
  api: {
    feedback: {
      post: (...args: unknown[]) => post(...args),
    },
  },
  ApiError: class extends Error {
    constructor(
      public status: number,
      public code: string,
      message: string,
    ) {
      super(message);
    }
  },
}));

describe('FeedbackWidget', () => {
  it('submits rating to the API', async () => {
    render(<FeedbackWidget resource="evaluation" resourceId="ev-1" />);
    fireEvent.change(screen.getByRole('combobox'), { target: { value: '5' } });
    fireEvent.click(screen.getByRole('button', { name: /submit/i }));
    await waitFor(() => {
      expect(post).toHaveBeenCalledWith('evaluation', 'ev-1', {
        rating: 5,
        correction_notes: null,
      });
    });
    expect(await screen.findByText(/thanks/i)).toBeInTheDocument();
  });
});
