import { useEffect, useState } from 'react';

import { api, type SubscriptionOut } from '../lib/api';

/**
 * Landing page after Stripe Checkout redirects back to our app.
 *
 * Behavior:
 *  - /billing/success → poll GET /billing/subscription every 2s for up to 30s
 *    until plan === 'pro', then bounce user back to /.
 *  - /billing/cancel or ?canceled=1 → show "checkout canceled" message with
 *    a link back to /settings/billing.
 */
export default function SubscribeRedirect() {
  const path = window.location.pathname;
  const params = new URLSearchParams(window.location.search);
  const canceled = path.endsWith('/cancel') || params.get('canceled') === '1';

  const [sub, setSub] = useState<SubscriptionOut | null>(null);
  const [attempts, setAttempts] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [givenUp, setGivenUp] = useState(false);

  useEffect(() => {
    if (canceled) return;

    let cancelledFlag = false;
    let timer: number | undefined;

    async function poll(attempt: number): Promise<void> {
      if (cancelledFlag) return;
      try {
        const resp = await api.getSubscription();
        if (cancelledFlag) return;
        setSub(resp.data);
        setAttempts(attempt + 1);
        if (resp.data.plan === 'pro' && resp.data.status === 'active') {
          timer = window.setTimeout(() => {
            window.location.href = '/';
          }, 1200);
          return;
        }
      } catch (e) {
        if (!cancelledFlag) setError((e as Error).message);
      }
      if (attempt < 14) {
        timer = window.setTimeout(() => poll(attempt + 1), 2000);
      } else if (!cancelledFlag) {
        setGivenUp(true);
      }
    }

    poll(0);
    return () => {
      cancelledFlag = true;
      if (timer !== undefined) window.clearTimeout(timer);
    };
  }, [canceled]);

  if (canceled) {
    return (
      <div className="min-h-screen bg-white p-8 text-[#37352f]">
        <h1 className="text-2xl font-semibold">Checkout canceled</h1>
        <p className="mt-2 text-sm text-ink-3">No charge was made.</p>
        <a
          href="/settings/billing"
          className="mt-4 inline-block rounded bg-cobalt px-4 py-2 text-sm font-medium text-white"
        >
          Back to billing
        </a>
      </div>
    );
  }

  const activated = sub?.plan === 'pro' && sub.status === 'active';

  return (
    <div className="min-h-screen bg-white p-8 text-[#37352f]">
      {activated ? (
        <>
          <h1 className="text-2xl font-semibold text-[#35a849]">Subscription activated</h1>
          <p className="mt-2 text-sm text-ink-3">Redirecting you to the agent…</p>
        </>
      ) : givenUp ? (
        <>
          <h1 className="text-2xl font-semibold">Almost there…</h1>
          <p className="mt-2 text-sm text-ink-3">
            We haven't received confirmation from Stripe yet. This can take a minute. Refresh this
            page or visit{' '}
            <a href="/settings/billing" className="text-cobalt">
              Billing
            </a>{' '}
            to check status.
          </p>
        </>
      ) : (
        <>
          <h1 className="text-2xl font-semibold">Confirming your subscription…</h1>
          <p className="mt-2 text-sm text-ink-3">
            Waiting for Stripe (attempt {attempts} of 15)
          </p>
        </>
      )}
      {error && <p className="mt-4 text-sm text-red-600">Error: {error}</p>}
    </div>
  );
}
