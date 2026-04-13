import { useState } from 'react';

import { ApiError, api, type FeedbackResource } from '../../lib/api';

interface FeedbackWidgetProps {
  resource: FeedbackResource;
  resourceId: string;
  className?: string;
}

export function FeedbackWidget({ resource, resourceId, className = '' }: FeedbackWidgetProps) {
  const [rating, setRating] = useState<number>(4);
  const [notes, setNotes] = useState('');
  const [status, setStatus] = useState<'idle' | 'sending' | 'done' | 'error'>('idle');
  const [err, setErr] = useState<string | null>(null);

  async function submit() {
    setStatus('sending');
    setErr(null);
    try {
      await api.feedback.post(resource, resourceId, {
        rating,
        correction_notes: notes.trim() || null,
      });
      setStatus('done');
    } catch (e) {
      setStatus('error');
      setErr(e instanceof ApiError ? e.message : 'Could not save feedback');
    }
  }

  if (status === 'done') {
    return (
      <p className={`text-xs text-[#35a849] ${className}`}>Thanks — feedback saved.</p>
    );
  }

  return (
    <div className={`rounded border border-[#e3e2e0] bg-[#fbfbfa] p-3 ${className}`}>
      <p className="text-xs font-medium text-[#787774]">Rate this output</p>
      <div className="mt-2 flex flex-wrap items-center gap-2">
        <label className="text-xs text-[#787774]" htmlFor={`rt-${resourceId}`}>
          Rating (1–5)
        </label>
        <select
          id={`rt-${resourceId}`}
          className="rounded border border-[#e3e2e0] bg-white px-2 py-1 text-sm"
          value={rating}
          onChange={(e) => setRating(Number(e.target.value))}
        >
          {[1, 2, 3, 4, 5].map((n) => (
            <option key={n} value={n}>
              {n}
            </option>
          ))}
        </select>
        <button
          type="button"
          onClick={() => void submit()}
          disabled={status === 'sending'}
          className="rounded bg-[#2383e2] px-3 py-1 text-xs text-white disabled:opacity-50"
        >
          {status === 'sending' ? 'Saving…' : 'Submit'}
        </button>
      </div>
      <textarea
        className="mt-2 w-full rounded border border-[#e3e2e0] bg-white px-2 py-1 text-xs"
        rows={2}
        placeholder="Optional corrections or context"
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
      />
      {err && <p className="mt-1 text-xs text-[#e03e3e]">{err}</p>}
    </div>
  );
}
