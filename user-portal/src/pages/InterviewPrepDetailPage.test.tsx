import { render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import InterviewPrepDetailPage from './InterviewPrepDetailPage';

const get = vi.fn();

vi.mock('../lib/api', () => ({
  api: {
    interviewPreps: {
      get: (...args: unknown[]) => get(...args),
    },
    feedback: {
      post: vi.fn().mockResolvedValue({ data: { id: 'fb-1' } }),
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

describe('InterviewPrepDetailPage', () => {
  it('renders questions + red-flag questions from the API', async () => {
    get.mockResolvedValueOnce({
      data: {
        id: 'prep-1',
        user_id: 'u-1',
        job_id: null,
        custom_role: 'Staff Backend Engineer',
        questions: [
          {
            question: 'Tell me about a migration you led.',
            category: 'behavioral',
            framework: 'STAR — emphasize risk management',
          },
          {
            question: 'Design a rate limiter for 1M QPS.',
            category: 'technical',
          },
        ],
        red_flag_questions: [
          {
            question: "What's the on-call rotation like?",
            what_to_listen_for: 'Specific numbers, not vague answers',
          },
        ],
        model_used: 'claude-test',
        tokens_used: 1200,
        created_at: new Date().toISOString(),
      },
    });

    render(<InterviewPrepDetailPage id="prep-1" />);

    await waitFor(() => {
      expect(screen.getByText('Staff Backend Engineer')).toBeInTheDocument();
    });
    expect(screen.getByText(/Tell me about a migration/i)).toBeInTheDocument();
    expect(screen.getByText(/Framework: STAR/i)).toBeInTheDocument();
    expect(screen.getByText(/Design a rate limiter/i)).toBeInTheDocument();
    expect(screen.getByText(/on-call rotation/i)).toBeInTheDocument();
    expect(screen.getByText(/Specific numbers/i)).toBeInTheDocument();
  });

  it('renders the loading state before the API resolves', () => {
    get.mockImplementationOnce(() => new Promise(() => {}));
    render(<InterviewPrepDetailPage id="prep-2" />);
    expect(screen.getByText(/Loading/i)).toBeInTheDocument();
  });

  it('renders error state when the API rejects', async () => {
    get.mockRejectedValueOnce(new Error('Network down'));
    render(<InterviewPrepDetailPage id="prep-3" />);
    await waitFor(() => {
      expect(screen.getByText(/Network down/i)).toBeInTheDocument();
    });
  });
});
