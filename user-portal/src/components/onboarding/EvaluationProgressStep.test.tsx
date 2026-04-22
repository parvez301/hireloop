import { act, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { EvaluationProgressStep } from './EvaluationProgressStep';

describe('EvaluationProgressStep', () => {
  it('renders the three progress steps', () => {
    render(<EvaluationProgressStep />);
    expect(screen.getByText(/parsing job description/i)).toBeInTheDocument();
    expect(screen.getByText(/comparing to your profile/i)).toBeInTheDocument();
    expect(screen.getByText(/writing evaluation/i)).toBeInTheDocument();
  });

  it('advances the active step over time', () => {
    vi.useFakeTimers();
    try {
      render(<EvaluationProgressStep />);
      expect(screen.getByTestId('progress-step-1').className).toMatch(
        /text-text-primary/,
      );
      act(() => {
        vi.advanceTimersByTime(20_000);
      });
      expect(screen.getByTestId('progress-step-2').className).toMatch(
        /text-text-primary/,
      );
    } finally {
      vi.useRealTimers();
    }
  });
});
