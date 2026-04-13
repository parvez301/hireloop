import { act, render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { PaywallModal } from './PaywallModal';

describe('PaywallModal', () => {
  it('is hidden by default', () => {
    render(<PaywallModal />);
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('opens when a subscription-required event fires', () => {
    render(<PaywallModal />);
    act(() => {
      window.dispatchEvent(
        new CustomEvent('subscription-required', { detail: { message: 'trial over' } }),
      );
    });
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByText(/your trial has ended/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /subscribe/i })).toBeInTheDocument();
  });
});
