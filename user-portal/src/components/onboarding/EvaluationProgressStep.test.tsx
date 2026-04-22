import { act, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { EvaluationProgressStep } from './EvaluationProgressStep';

describe('EvaluationProgressStep', () => {
  it('reveals the three thought-stream labels after their stagger timeouts', () => {
    vi.useFakeTimers();
    try {
      render(<EvaluationProgressStep />);
      act(() => {
        vi.advanceTimersByTime(2_000);
      });
      expect(screen.getByText(/parsing job description/i)).toBeInTheDocument();
      expect(screen.getByText(/comparing to your profile/i)).toBeInTheDocument();
      expect(screen.getByText(/writing evaluation/i)).toBeInTheDocument();
    } finally {
      vi.useRealTimers();
    }
  });

  it('advances the progress list over time', () => {
    vi.useFakeTimers();
    try {
      render(<EvaluationProgressStep />);
      // Initial: row 1 is "running".
      expect(screen.getByTestId('ring-row-1').textContent).toMatch(/running/i);
      act(() => {
        vi.advanceTimersByTime(1_300);
      });
      // After ~1.2s: row 1 done (✓), row 2 running.
      expect(screen.getByTestId('ring-row-1').textContent).toContain('✓');
      expect(screen.getByTestId('ring-row-2').textContent).toMatch(/running/i);
    } finally {
      vi.useRealTimers();
    }
  });

  it('renders the estimated score ring as a progressbar', () => {
    render(<EvaluationProgressStep />);
    expect(screen.getByRole('progressbar')).toBeInTheDocument();
  });
});
