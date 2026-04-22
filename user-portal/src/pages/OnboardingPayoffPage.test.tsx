import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { api } from '../lib/api';
import OnboardingPayoffPage from './OnboardingPayoffPage';

vi.mock('../lib/api', () => ({
  api: {
    evaluations: { get: vi.fn() },
    applications: { create: vi.fn() },
    interviewPreps: { create: vi.fn() },
    createConversation: vi.fn(),
    sendMessage: vi.fn(),
  },
}));

const MOCK_EVALUATION = {
  id: 'eval-1',
  user_id: 'user-1',
  job_id: 'job-1',
  overall_grade: 'B+',
  dimension_scores: {
    skills_match: { score: 0.82, grade: 'B+', reasoning: 'Strong Python.' },
  },
  reasoning: 'Solid fit overall.',
  red_flags: [],
  personalization: null,
  match_score: 0.82,
  recommendation: 'worth_exploring' as const,
  model_used: 'test',
  tokens_used: null,
  cached: false,
  created_at: '2026-04-22T00:00:00Z',
};

const MOCK_HANDOFF = {
  evaluation: MOCK_EVALUATION,
  job: {
    content_hash: 'h',
    url: null,
    title: 'Senior Backend',
    company: 'Acme',
    location: 'Remote',
    description_md: '...',
  },
};

describe('OnboardingPayoffPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    sessionStorage.clear();
  });

  it('renders the evaluation card and four CTAs using sessionStorage handoff', async () => {
    sessionStorage.setItem(
      'onboarding-payoff-eval-1',
      JSON.stringify(MOCK_HANDOFF),
    );
    render(<OnboardingPayoffPage id="eval-1" />);
    await waitFor(() => screen.getByText('Senior Backend'));
    expect(screen.getByText('Acme · Remote')).toBeInTheDocument();
    expect(screen.getByText('82')).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: /tailor my cv/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: /generate interview prep/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: /save to pipeline/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: /unlock job scanning/i }),
    ).toBeInTheDocument();
  });

  it('falls back to fetching via api.evaluations.get when handoff missing', async () => {
    vi.mocked(api.evaluations.get).mockResolvedValue({
      data: MOCK_EVALUATION,
    });
    render(<OnboardingPayoffPage id="eval-1" />);
    await waitFor(() => expect(api.evaluations.get).toHaveBeenCalledWith('eval-1'));
    expect(screen.getByText('82')).toBeInTheDocument();
  });

  it('creates an application on Save to pipeline click', async () => {
    sessionStorage.setItem(
      'onboarding-payoff-eval-1',
      JSON.stringify(MOCK_HANDOFF),
    );
    vi.mocked(api.applications.create).mockResolvedValue({
      data: { id: 'app-1' } as never,
    });
    render(<OnboardingPayoffPage id="eval-1" />);
    await waitFor(() => screen.getByText('Senior Backend'));
    fireEvent.click(screen.getByRole('button', { name: /save to pipeline/i }));
    await waitFor(() =>
      expect(api.applications.create).toHaveBeenCalledWith({
        job_id: 'job-1',
        status: 'saved',
        evaluation_id: 'eval-1',
      }),
    );
    await waitFor(() =>
      expect(screen.getByRole('button', { name: /saved/i })).toBeInTheDocument(),
    );
  });
});
