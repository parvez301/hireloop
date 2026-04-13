import { useCallback, useEffect, useState } from 'react';

import { api, type SubscriptionOut } from '../lib/api';

function formatDate(iso: string | null): string {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  } catch {
    return iso;
  }
}

function daysBetween(from: Date, to: Date): number {
  const ms = to.getTime() - from.getTime();
  return Math.max(0, Math.ceil(ms / (24 * 60 * 60 * 1000)));
}

function trialDaysRemaining(sub: SubscriptionOut): number | null {
  if (!sub.trial_ends_at) return null;
  const end = new Date(sub.trial_ends_at);
  if (end.getTime() < Date.now()) return 0;
  return daysBetween(new Date(), end);
}

function graceDaysRemaining(sub: SubscriptionOut): number | null {
  if (!sub.past_due_since) return null;
  const stamp = new Date(sub.past_due_since);
  const graceEnd = new Date(stamp.getTime() + 3 * 24 * 60 * 60 * 1000);
  if (graceEnd.getTime() < Date.now()) return 0;
  return daysBetween(new Date(), graceEnd);
}

export default function BillingPage() {
  const [sub, setSub] = useState<SubscriptionOut | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionPending, setActionPending] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const resp = await api.getSubscription();
        if (!cancelled) setSub(resp.data);
      } catch (e) {
        if (!cancelled) setError((e as Error).message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, []);

  const handleSubscribe = useCallback(async () => {
    setActionPending(true);
    setError(null);
    try {
      const resp = await api.startCheckout();
      window.location.href = resp.data.url;
    } catch (e) {
      setError((e as Error).message);
      setActionPending(false);
    }
  }, []);

  const handleManage = useCallback(async () => {
    setActionPending(true);
    setError(null);
    try {
      const resp = await api.openPortal();
      window.location.href = resp.data.url;
    } catch (e) {
      setError((e as Error).message);
      setActionPending(false);
    }
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-white p-8 text-[#37352f]">
        <p>Loading billing details…</p>
      </div>
    );
  }

  if (error || !sub) {
    return (
      <div className="min-h-screen bg-white p-8 text-[#37352f]">
        <a href="/" className="text-sm text-[#2383e2]">
          ← Back to chat
        </a>
        <h1 className="mt-4 text-2xl font-semibold">Billing</h1>
        <p className="mt-4 text-sm text-[#e03e3e]">Error: {error ?? 'Unknown'}</p>
      </div>
    );
  }

  const onTrial = sub.plan === 'trial' && sub.has_active_entitlement;
  const isPro = sub.plan === 'pro' && sub.status === 'active';
  const isPastDue = sub.status === 'past_due';
  const isCanceled = sub.status === 'canceled' || sub.plan === 'canceled';
  const willCancel = isPro && sub.cancel_at_period_end;
  const trialDays = trialDaysRemaining(sub);
  const graceDays = graceDaysRemaining(sub);

  return (
    <div className="min-h-screen bg-white text-[#37352f]">
      <header className="flex items-center justify-between border-b border-[#e3e2e0] px-6 py-3">
        <div className="flex items-center gap-3">
          <a href="/" className="text-sm text-[#2383e2]">
            ← Back to chat
          </a>
          <span className="text-sm text-[#787774]">·</span>
          <span className="text-sm font-medium">Settings · Billing</span>
        </div>
      </header>

      <main className="mx-auto max-w-2xl px-6 py-10">
        <h1 className="text-2xl font-semibold">Your plan</h1>

        <section className="mt-6 rounded-lg border border-[#e3e2e0] bg-[#fbfbfa] p-6">
          {onTrial && (
            <>
              <p className="text-lg font-medium">Free trial</p>
              <p className="mt-1 text-sm text-[#787774]">
                {trialDays !== null && trialDays > 0
                  ? `${trialDays} day${trialDays === 1 ? '' : 's'} remaining`
                  : 'Trial ends today'}{' '}
                · Expires {formatDate(sub.trial_ends_at)}
              </p>
              <button
                type="button"
                onClick={handleSubscribe}
                disabled={actionPending}
                className="mt-4 rounded bg-[#2383e2] px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
              >
                Subscribe — $4.99/mo
              </button>
            </>
          )}

          {isPro && !willCancel && (
            <>
              <p className="text-lg font-medium">Pro plan — $4.99/mo</p>
              <p className="mt-1 text-sm text-[#787774]">
                Renews {formatDate(sub.current_period_end)}
              </p>
              <button
                type="button"
                onClick={handleManage}
                disabled={actionPending}
                className="mt-4 rounded border border-[#e3e2e0] px-4 py-2 text-sm font-medium text-[#37352f] disabled:opacity-50"
              >
                Manage billing
              </button>
            </>
          )}

          {isPro && willCancel && (
            <>
              <p className="text-lg font-medium">Pro plan — cancelling</p>
              <p className="mt-1 text-sm text-[#cb912f]">
                Access ends {formatDate(sub.current_period_end)}. You can undo this from the
                billing portal.
              </p>
              <button
                type="button"
                onClick={handleManage}
                disabled={actionPending}
                className="mt-4 rounded border border-[#e3e2e0] px-4 py-2 text-sm font-medium text-[#37352f] disabled:opacity-50"
              >
                Manage billing
              </button>
            </>
          )}

          {isPastDue && (
            <>
              <p className="text-lg font-medium text-[#e03e3e]">Payment failed</p>
              <p className="mt-1 text-sm text-[#787774]">
                {graceDays !== null && graceDays > 0
                  ? `Update your card within ${graceDays} day${graceDays === 1 ? '' : 's'} to keep access.`
                  : 'Your access will be revoked shortly if the card is not updated.'}
              </p>
              <button
                type="button"
                onClick={handleManage}
                disabled={actionPending}
                className="mt-4 rounded bg-[#e03e3e] px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
              >
                Update card
              </button>
            </>
          )}

          {isCanceled && (
            <>
              <p className="text-lg font-medium">No active subscription</p>
              <p className="mt-1 text-sm text-[#787774]">
                Your previous subscription ended. Subscribe again to restore access.
              </p>
              <button
                type="button"
                onClick={handleSubscribe}
                disabled={actionPending}
                className="mt-4 rounded bg-[#2383e2] px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
              >
                Subscribe — $4.99/mo
              </button>
            </>
          )}

          {!onTrial && !isPro && !isPastDue && !isCanceled && (
            <p className="text-sm text-[#787774]">
              Plan state: {sub.plan} ({sub.status}). Contact support if this looks wrong.
            </p>
          )}
        </section>

        {error && <p className="mt-4 text-sm text-[#e03e3e]">Error: {error}</p>}
      </main>
    </div>
  );
}
