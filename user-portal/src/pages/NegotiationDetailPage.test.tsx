import { render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import NegotiationDetailPage from './NegotiationDetailPage';

const get = vi.fn();
const create = vi.fn();

vi.mock('../lib/api', () => ({
  api: {
    negotiations: {
      get: (...args: unknown[]) => get(...args),
      create: (...args: unknown[]) => create(...args),
    },
    feedback: {
      post: vi.fn().mockResolvedValue({ data: { id: 'fb-1' } }),
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

describe('NegotiationDetailPage', () => {
  it('renders market research, counter offer, scripts, and an OfferForm for regeneration', async () => {
    get.mockResolvedValueOnce({
      data: {
        id: 'neg-1',
        user_id: 'u-1',
        job_id: 'job-42',
        offer_details: { base: 180000, equity: '0.1%' },
        market_research: {
          range_low: 170000,
          range_mid: 195000,
          range_high: 225000,
          source_notes: 'levels.fyi + glassdoor',
        },
        counter_offer: {
          target: 210000,
          minimum_acceptable: 195000,
          justification: 'Market median supports 5% above',
        },
        scripts: {
          email_template: 'Thanks for the offer...',
          call_script: 'Opening: I am very excited...',
        },
        model_used: 'claude-test',
        tokens_used: 2000,
        created_at: new Date().toISOString(),
      },
    });

    render(<NegotiationDetailPage id="neg-1" />);

    await waitFor(() => {
      expect(screen.getByText(/Negotiation playbook/i)).toBeInTheDocument();
    });

    // All three JSON sections are visible
    expect(screen.getByText(/Market \(indicative\)/i)).toBeInTheDocument();
    expect(screen.getByText(/Counter-offer/i)).toBeInTheDocument();
    expect(screen.getByText(/Scripts/i)).toBeInTheDocument();

    // The inline OfferForm is rendered with the same job id for regeneration
    expect(screen.getByText(/New playbook for same job/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/base salary/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /generate playbook/i })).toBeInTheDocument();
  });

  it('renders the error state when the API rejects', async () => {
    get.mockRejectedValueOnce(new Error('Not found'));
    render(<NegotiationDetailPage id="neg-404" />);
    await waitFor(() => {
      expect(screen.getByText(/Not found/i)).toBeInTheDocument();
    });
  });

  it('renders loading state before the API resolves', () => {
    get.mockImplementationOnce(() => new Promise(() => {}));
    render(<NegotiationDetailPage id="neg-slow" />);
    expect(screen.getByText(/Loading/i)).toBeInTheDocument();
  });
});
