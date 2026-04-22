import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { api } from '../lib/api';
import OnboardingPage from './OnboardingPage';

vi.mock('../lib/api', () => ({
  api: {
    profile: {
      get: vi.fn(),
      uploadResume: vi.fn(),
      uploadResumeText: vi.fn(),
    },
    onboarding: {
      firstEvaluation: vi.fn(),
    },
  },
}));

describe('OnboardingPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('starts on step 1 (resume upload) when onboarding_state is resume_upload', async () => {
    vi.mocked(api.profile.get).mockResolvedValue({
      data: { onboarding_state: 'resume_upload' } as never,
    });
    render(<OnboardingPage />);
    await waitFor(() =>
      expect(screen.getByText(/drag and drop/i)).toBeInTheDocument(),
    );
  });

  it('advances to step 2 after successful resume upload', async () => {
    vi.mocked(api.profile.get).mockResolvedValue({
      data: { onboarding_state: 'resume_upload' } as never,
    });
    vi.mocked(api.profile.uploadResumeText).mockResolvedValue({
      data: { onboarding_state: 'done' } as never,
    });
    render(<OnboardingPage />);
    await waitFor(() =>
      screen.getByRole('button', { name: /paste text/i }),
    );
    fireEvent.click(screen.getByRole('button', { name: /paste text/i }));
    fireEvent.change(screen.getByRole('textbox'), {
      target: { value: 'Resume content' },
    });
    fireEvent.click(screen.getByRole('button', { name: /continue/i }));
    await waitFor(() =>
      expect(screen.getByText(/paste a job/i)).toBeInTheDocument(),
    );
  });

  it('shows evaluation progress during the wait', async () => {
    vi.mocked(api.profile.get).mockResolvedValue({
      data: { onboarding_state: 'done', master_resume_md: '# x' } as never,
    });
    let resolveEval: (value: unknown) => void = () => {};
    vi.mocked(api.onboarding.firstEvaluation).mockReturnValue(
      new Promise((resolve) => {
        resolveEval = resolve;
      }) as never,
    );
    render(<OnboardingPage />);
    await waitFor(() => screen.getByText(/paste a job/i));
    fireEvent.change(screen.getByRole('textbox'), {
      target: { value: 'https://example.com/jobs/1' },
    });
    fireEvent.click(screen.getByRole('button', { name: /evaluat/i }));
    await waitFor(() =>
      expect(screen.getByText(/parsing job description/i)).toBeInTheDocument(),
    );
    resolveEval({ data: { evaluation: { id: 'eval-1' }, job: {} } });
  });
});
