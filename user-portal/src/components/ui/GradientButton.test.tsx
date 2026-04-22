import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { GradientButton } from './GradientButton';

describe('GradientButton', () => {
  it('renders the label', () => {
    render(<GradientButton>Tailor my CV</GradientButton>);
    expect(screen.getByRole('button', { name: 'Tailor my CV' })).toBeInTheDocument();
  });

  it('fires onClick', () => {
    const onClick = vi.fn();
    render(<GradientButton onClick={onClick}>Go</GradientButton>);
    fireEvent.click(screen.getByRole('button', { name: 'Go' }));
    expect(onClick).toHaveBeenCalled();
  });

  it('applies the marketing gradient classes', () => {
    render(<GradientButton>X</GradientButton>);
    const btn = screen.getByRole('button', { name: 'X' });
    expect(btn.className).toContain('from-accent-teal');
    expect(btn.className).toContain('via-accent-cobalt');
    expect(btn.className).toContain('to-accent-violet');
  });

  it('supports disabled state', () => {
    render(<GradientButton disabled>X</GradientButton>);
    expect(screen.getByRole('button', { name: 'X' })).toBeDisabled();
  });
});
