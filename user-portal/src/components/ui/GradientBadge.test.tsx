import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { GradientBadge } from './GradientBadge';

describe('GradientBadge', () => {
  it('renders the score', () => {
    render(<GradientBadge grade="A-" score={82} />);
    expect(screen.getByText('82')).toBeInTheDocument();
  });

  it('uses teal→green gradient for A', () => {
    render(<GradientBadge grade="A" score={94} />);
    const el = screen.getByText('94').closest('div');
    expect(el?.className).toMatch(/from-\[#14b8a6\]/);
    expect(el?.className).toMatch(/to-\[#22c55e\]/);
  });

  it('uses cobalt→violet gradient for B+', () => {
    render(<GradientBadge grade="B+" score={75} />);
    const el = screen.getByText('75').closest('div');
    expect(el?.className).toMatch(/from-\[#2563eb\]/);
    expect(el?.className).toMatch(/to-\[#7c3aed\]/);
  });

  it('renders C-grade with neutral amber', () => {
    render(<GradientBadge grade="C" score={55} />);
    const el = screen.getByText('55').closest('div');
    expect(el?.className).toMatch(/from-\[#f59e0b\]/);
  });
});
