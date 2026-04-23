import { render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import BillingPage from './BillingPage';

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

function mockSubscription(overrides: Record<string, unknown> = {}) {
  return {
    id: 'sub-1',
    user_id: 'u-1',
    plan: 'trial',
    status: 'active',
    trial_ends_at: new Date(Date.now() + 3 * 86400000).toISOString(),
    current_period_end: null,
    past_due_since: null,
    cancel_at_period_end: false,
    stripe_customer_id: null,
    has_active_entitlement: true,
    ...overrides,
  };
}

describe('BillingPage', () => {
  it('renders trial state with Subscribe button', async () => {
    fetchMock.mockResolvedValueOnce(mockJsonResponse({ data: mockSubscription() }));
    render(<BillingPage />);

    await waitFor(() => {
      expect(screen.getByText(/free trial/i)).toBeInTheDocument();
    });
    expect(screen.getByRole('button', { name: /subscribe/i })).toBeInTheDocument();
  });

  it('renders pro active state with Manage billing button', async () => {
    fetchMock.mockResolvedValueOnce(
      mockJsonResponse({
        data: mockSubscription({
          plan: 'pro',
          status: 'active',
          current_period_end: new Date(Date.now() + 25 * 86400000).toISOString(),
          trial_ends_at: new Date(Date.now() - 10 * 86400000).toISOString(),
          stripe_customer_id: 'cus_1',
        }),
      }),
    );
    render(<BillingPage />);

    await waitFor(() => {
      expect(screen.getByText(/Pro plan/i)).toBeInTheDocument();
    });
    expect(screen.getByText(/\$4\.99\/mo/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /manage billing/i })).toBeInTheDocument();
  });

  it('renders past_due state with Update card button', async () => {
    fetchMock.mockResolvedValueOnce(
      mockJsonResponse({
        data: mockSubscription({
          plan: 'pro',
          status: 'past_due',
          past_due_since: new Date(Date.now() - 1 * 86400000).toISOString(),
          stripe_customer_id: 'cus_1',
          has_active_entitlement: true,
        }),
      }),
    );
    render(<BillingPage />);

    await waitFor(() => {
      expect(screen.getByText(/payment failed/i)).toBeInTheDocument();
    });
    expect(screen.getByRole('button', { name: /update card/i })).toBeInTheDocument();
  });

  it('renders canceled state with Subscribe again button', async () => {
    fetchMock.mockResolvedValueOnce(
      mockJsonResponse({
        data: mockSubscription({
          plan: 'canceled',
          status: 'canceled',
          has_active_entitlement: false,
        }),
      }),
    );
    render(<BillingPage />);

    await waitFor(() => {
      expect(screen.getByText(/no active subscription/i)).toBeInTheDocument();
    });
    expect(screen.getByRole('button', { name: /subscribe/i })).toBeInTheDocument();
  });

  it('renders will-cancel state with end date notice', async () => {
    fetchMock.mockResolvedValueOnce(
      mockJsonResponse({
        data: mockSubscription({
          plan: 'pro',
          status: 'active',
          cancel_at_period_end: true,
          current_period_end: new Date(Date.now() + 10 * 86400000).toISOString(),
          trial_ends_at: new Date(Date.now() - 10 * 86400000).toISOString(),
          stripe_customer_id: 'cus_1',
        }),
      }),
    );
    render(<BillingPage />);

    await waitFor(() => {
      expect(screen.getByText(/cancelling/i)).toBeInTheDocument();
    });
    expect(screen.getByText(/access ends/i)).toBeInTheDocument();
  });
});
