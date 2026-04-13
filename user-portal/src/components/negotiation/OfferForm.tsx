import { useState } from 'react';

import { ApiError, api } from '../../lib/api';

interface OfferFormProps {
  jobId: string;
  onCreated?: (negotiationId: string) => void;
}

export function OfferForm({ jobId, onCreated }: OfferFormProps) {
  const [base, setBase] = useState('');
  const [equity, setEquity] = useState('');
  const [err, setErr] = useState<string | null>(null);
  const [sending, setSending] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const n = Number(base);
    if (!Number.isFinite(n) || n < 0) {
      setErr('Enter a valid base salary');
      return;
    }
    setSending(true);
    setErr(null);
    try {
      const r = await api.negotiations.create({
        job_id: jobId,
        offer_details: {
          base: Math.round(n),
          equity: equity.trim() || null,
        },
      });
      onCreated?.(r.data.id);
    } catch (ex) {
      setErr(ex instanceof ApiError ? ex.message : 'Request failed');
    } finally {
      setSending(false);
    }
  }

  return (
    <form onSubmit={(e) => void submit(e)} className="mt-3 max-w-md space-y-2">
      <div>
        <label className="text-xs text-[#787774]" htmlFor="offer-base">
          Base salary (USD)
        </label>
        <input
          id="offer-base"
          type="number"
          min={0}
          className="mt-1 w-full rounded border border-[#e3e2e0] px-2 py-1 text-sm"
          value={base}
          onChange={(e) => setBase(e.target.value)}
        />
      </div>
      <div>
        <label className="text-xs text-[#787774]" htmlFor="offer-eq">
          Equity (optional)
        </label>
        <input
          id="offer-eq"
          className="mt-1 w-full rounded border border-[#e3e2e0] px-2 py-1 text-sm"
          value={equity}
          onChange={(e) => setEquity(e.target.value)}
          placeholder="e.g. 0.1% or $40k RSU"
        />
      </div>
      {err && <p className="text-xs text-[#e03e3e]">{err}</p>}
      <button
        type="submit"
        disabled={sending}
        className="rounded bg-[#2383e2] px-3 py-1 text-sm text-white disabled:opacity-50"
      >
        {sending ? 'Generating…' : 'Generate playbook'}
      </button>
    </form>
  );
}
