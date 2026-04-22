import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { JobInputStep } from './JobInputStep';

describe('JobInputStep', () => {
  it('calls onSubmit with {type:url} when a URL is entered', () => {
    const onSubmit = vi.fn();
    render(<JobInputStep onSubmit={onSubmit} />);
    fireEvent.change(screen.getByRole('textbox'), {
      target: { value: 'https://example.com/jobs/1' },
    });
    fireEvent.click(screen.getByRole('button', { name: /evaluat/i }));
    expect(onSubmit).toHaveBeenCalledWith({
      type: 'url',
      value: 'https://example.com/jobs/1',
    });
  });

  it('calls onSubmit with {type:text} when raw text is entered', () => {
    const onSubmit = vi.fn();
    render(<JobInputStep onSubmit={onSubmit} />);
    fireEvent.change(screen.getByRole('textbox'), {
      target: { value: 'Senior backend at Acme' },
    });
    fireEvent.click(screen.getByRole('button', { name: /evaluat/i }));
    expect(onSubmit).toHaveBeenCalledWith({
      type: 'text',
      value: 'Senior backend at Acme',
    });
  });

  it('disables submit while busy', () => {
    render(<JobInputStep onSubmit={vi.fn()} busy />);
    expect(screen.getByRole('button', { name: /evaluat/i })).toBeDisabled();
  });

  it('surfaces error inline', () => {
    render(<JobInputStep onSubmit={vi.fn()} error="parse failed" />);
    expect(screen.getByRole('alert')).toHaveTextContent(/parse failed/i);
  });
});
