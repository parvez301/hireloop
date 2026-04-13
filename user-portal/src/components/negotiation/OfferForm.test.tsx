import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { OfferForm } from './OfferForm';

const create = vi
  .fn()
  .mockResolvedValue({
    data: {
      id: 'neg-1',
      user_id: 'u-1',
      job_id: 'job-1',
      offer_details: { base: 180000 },
      market_research: {},
      counter_offer: {},
      scripts: {},
      model_used: 'test',
      tokens_used: 0,
      created_at: new Date().toISOString(),
    },
  });

vi.mock('../../lib/api', () => ({
  api: {
    negotiations: {
      create: (...args: unknown[]) => create(...args),
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

describe('OfferForm', () => {
  it('submits base + equity to negotiations.create and calls onCreated', async () => {
    const onCreated = vi.fn();
    render(<OfferForm jobId="job-1" onCreated={onCreated} />);

    fireEvent.change(screen.getByLabelText(/base salary/i), {
      target: { value: '180000' },
    });
    fireEvent.change(screen.getByLabelText(/equity/i), {
      target: { value: '0.1% or $40k RSU' },
    });
    fireEvent.click(screen.getByRole('button', { name: /generate playbook/i }));

    await waitFor(() => {
      expect(create).toHaveBeenCalledTimes(1);
      expect(create).toHaveBeenCalledWith({
        job_id: 'job-1',
        offer_details: {
          base: 180000,
          equity: '0.1% or $40k RSU',
        },
      });
      expect(onCreated).toHaveBeenCalledWith('neg-1');
    });
  });

  it('nullifies an empty equity field', async () => {
    create.mockClear();
    const onCreated = vi.fn();
    render(<OfferForm jobId="job-2" onCreated={onCreated} />);

    fireEvent.change(screen.getByLabelText(/base salary/i), {
      target: { value: '200000' },
    });
    // leave equity blank
    fireEvent.click(screen.getByRole('button', { name: /generate playbook/i }));

    await waitFor(() => {
      expect(create).toHaveBeenCalledWith({
        job_id: 'job-2',
        offer_details: {
          base: 200000,
          equity: null,
        },
      });
    });
  });
});
