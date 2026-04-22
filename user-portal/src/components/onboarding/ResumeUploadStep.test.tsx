import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { api } from '../../lib/api';
import { ResumeUploadStep } from './ResumeUploadStep';

vi.mock('../../lib/api', () => ({
  api: {
    profile: {
      uploadResume: vi.fn(),
      uploadResumeText: vi.fn(),
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

describe('ResumeUploadStep', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows the upload zone and the paste-text fallback link', () => {
    render(<ResumeUploadStep onAdvance={vi.fn()} />);
    expect(screen.getByText(/drop your resume/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /paste plain text/i })).toBeInTheDocument();
  });

  it('reveals textarea when paste-text link clicked', () => {
    render(<ResumeUploadStep onAdvance={vi.fn()} />);
    fireEvent.click(screen.getByRole('button', { name: /paste plain text/i }));
    expect(screen.getByRole('textbox')).toBeInTheDocument();
  });

  it('calls uploadResumeText and advances on successful paste', async () => {
    const onAdvance = vi.fn();
    vi.mocked(api.profile.uploadResumeText).mockResolvedValue({
      data: { onboarding_state: 'done' } as never,
    });
    render(<ResumeUploadStep onAdvance={onAdvance} />);
    fireEvent.click(screen.getByRole('button', { name: /paste plain text/i }));
    fireEvent.change(screen.getByRole('textbox'), {
      target: { value: 'My resume content' },
    });
    fireEvent.click(screen.getByRole('button', { name: /continue/i }));
    await waitFor(() =>
      expect(api.profile.uploadResumeText).toHaveBeenCalledWith('My resume content'),
    );
    expect(onAdvance).toHaveBeenCalled();
  });

  it('surfaces errors inline on failure', async () => {
    vi.mocked(api.profile.uploadResumeText).mockRejectedValue(new Error('parse failed'));
    render(<ResumeUploadStep onAdvance={vi.fn()} />);
    fireEvent.click(screen.getByRole('button', { name: /paste plain text/i }));
    fireEvent.change(screen.getByRole('textbox'), {
      target: { value: 'x' },
    });
    fireEvent.click(screen.getByRole('button', { name: /continue/i }));
    await waitFor(() =>
      expect(screen.getByText(/parse failed/i)).toBeInTheDocument(),
    );
  });
});
