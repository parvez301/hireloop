import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import ChatPage from './ChatPage';

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

describe('ChatPage', () => {
  it('loads the default conversation and renders a sent message with an evaluation card', async () => {
    const conversation = {
      id: 'conv-1',
      user_id: 'u-1',
      title: 'Default',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };

    fetchMock
      .mockResolvedValueOnce(mockJsonResponse({ data: [] }))
      .mockResolvedValueOnce(mockJsonResponse({ data: conversation }))
      .mockResolvedValueOnce(
        mockJsonResponse({
          data: { conversation, messages: [] },
        }),
      )
      .mockResolvedValueOnce(
        mockJsonResponse({
          data: {
            id: 'msg-2',
            conversation_id: 'conv-1',
            role: 'assistant',
            content: 'Here is the evaluation.',
            cards: [
              {
                type: 'evaluation',
                data: {
                  evaluation_id: 'eval-1',
                  job_id: 'job-1',
                  job_title: 'Staff Engineer',
                  company: 'Acme',
                  location: 'Remote',
                  salary_range: '$180,000 - $220,000',
                  overall_grade: 'A-',
                  match_score: 0.87,
                  recommendation: 'strong_match',
                  dimension_scores: {
                    skills_match: { score: 0.9, grade: 'A-', reasoning: '' },
                  },
                  reasoning: 'Strong fit overall.',
                  red_flags: [],
                  personalization: null,
                  cached: false,
                },
              },
            ],
            metadata: null,
            created_at: new Date().toISOString(),
          },
          meta: { tokens_used: 1200 },
        }),
      )
      .mockResolvedValueOnce(
        mockJsonResponse({
          data: {
            conversation,
            messages: [
              {
                id: 'msg-1',
                conversation_id: 'conv-1',
                role: 'user',
                content: 'Evaluate this',
                cards: null,
                metadata: null,
                created_at: new Date().toISOString(),
              },
              {
                id: 'msg-2',
                conversation_id: 'conv-1',
                role: 'assistant',
                content: 'Here is the evaluation.',
                cards: [
                  {
                    type: 'evaluation',
                    data: {
                      evaluation_id: 'eval-1',
                      job_id: 'job-1',
                      job_title: 'Staff Engineer',
                      company: 'Acme',
                      location: 'Remote',
                      salary_range: '$180,000 - $220,000',
                      overall_grade: 'A-',
                      match_score: 0.87,
                      recommendation: 'strong_match',
                      dimension_scores: {
                        skills_match: { score: 0.9, grade: 'A-', reasoning: '' },
                      },
                      reasoning: 'Strong fit overall.',
                      red_flags: [],
                      personalization: null,
                      cached: false,
                    },
                  },
                ],
                metadata: null,
                created_at: new Date().toISOString(),
              },
            ],
          },
        }),
      );

    render(<ChatPage />);

    const textbox = await screen.findByPlaceholderText(/tell your agent/i);
    fireEvent.change(textbox, { target: { value: 'Evaluate this' } });
    const sendButton = screen.getByRole('button', { name: /send/i });
    fireEvent.click(sendButton);

    await waitFor(() => {
      expect(screen.getByText(/Staff Engineer/)).toBeInTheDocument();
      expect(screen.getByText('A-')).toBeInTheDocument();
    });
  });
});
