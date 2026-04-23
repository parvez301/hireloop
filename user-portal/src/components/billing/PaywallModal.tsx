import { useCallback, useEffect, useState } from 'react';

import { api } from '../../lib/api';

/**
 * Global paywall modal. Listens for `subscription-required` CustomEvents
 * (dispatched by `api.ts` when any request returns 403 TRIAL_EXPIRED)
 * and renders an overlay with a Subscribe button.
 */
export function PaywallModal() {
  const [open, setOpen] = useState(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    function onEvent() {
      setOpen(true);
    }
    window.addEventListener('subscription-required', onEvent as EventListener);
    return () => window.removeEventListener('subscription-required', onEvent as EventListener);
  }, []);

  const subscribe = useCallback(async () => {
    setPending(true);
    setError(null);
    try {
      const resp = await api.startCheckout();
      window.location.href = resp.data.url;
    } catch (e) {
      setError((e as Error).message);
      setPending(false);
    }
  }, []);

  if (!open) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="paywall-title"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
    >
      <div className="max-w-md rounded-lg bg-white p-6 shadow-xl">
        <h2 id="paywall-title" className="text-xl font-semibold">
          Your trial has ended
        </h2>
        <p className="mt-2 text-sm text-ink-3">
          Subscribe to HireLoop Pro to keep evaluating jobs, tailoring your CV, and chatting
          with your agent.
        </p>
        <p className="mt-4 text-sm">
          <strong className="text-lg">$4.99</strong>
          <span className="text-ink-3"> / month · cancel anytime</span>
        </p>

        {error && <p className="mt-3 text-sm text-red-600">{error}</p>}

        <div className="mt-6 flex gap-2">
          <button
            type="button"
            onClick={subscribe}
            disabled={pending}
            className="flex-1 rounded bg-cobalt px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            {pending ? 'Redirecting…' : 'Subscribe'}
          </button>
          <button
            type="button"
            onClick={() => setOpen(false)}
            className="rounded border border-line-2 px-4 py-2 text-sm text-[#37352f]"
          >
            Not now
          </button>
        </div>

        <p className="mt-4 text-center text-xs text-ink-3">
          Or visit{' '}
          <a href="/settings/billing" className="text-cobalt">
            Billing
          </a>{' '}
          to see your plan details.
        </p>
      </div>
    </div>
  );
}
