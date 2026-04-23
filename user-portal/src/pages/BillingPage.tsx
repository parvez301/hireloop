import { useCallback, useEffect, useState } from 'react';
import { CreditCard, FileText, Trash2 } from 'lucide-react';

import { SoftCard } from '../components/ui/SoftCard';
import { WorkspaceShell } from '../components/workspace/WorkspaceShell';
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

function trialProgressPct(sub: SubscriptionOut): number | null {
  if (!sub.trial_ends_at) return null;
  const end = new Date(sub.trial_ends_at).getTime();
  const start = end - 15 * 24 * 60 * 60 * 1000;
  const now = Date.now();
  if (now >= end) return 100;
  if (now <= start) return 0;
  return Math.round(((now - start) / (end - start)) * 100);
}

function graceDaysRemaining(sub: SubscriptionOut): number | null {
  if (!sub.past_due_since) return null;
  const stamp = new Date(sub.past_due_since);
  const graceEnd = new Date(stamp.getTime() + 3 * 24 * 60 * 60 * 1000);
  if (graceEnd.getTime() < Date.now()) return 0;
  return daysBetween(new Date(), graceEnd);
}

const GRADIENT_BUTTON =
  'inline-flex items-center gap-1 rounded-lg px-4 py-2 text-[13px] font-semibold text-white shadow-[0_14px_30px_-16px_rgba(37,99,235,0.55),inset_0_1px_0_rgba(255,255,255,0.15)] disabled:opacity-50';
const GRADIENT_BG = {
  backgroundImage:
    'linear-gradient(135deg, #0f766e 0%, #1d4ed8 45%, #6d28d9 100%)',
};

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

  const onTrial = sub?.plan === 'trial' && sub.has_active_entitlement;
  const isPro = sub?.plan === 'pro' && sub?.status === 'active';
  const isPastDue = sub?.status === 'past_due';
  const isCanceled = sub?.status === 'canceled' || sub?.plan === 'canceled';
  const willCancel = isPro && sub?.cancel_at_period_end;
  const trialDays = sub ? trialDaysRemaining(sub) : null;
  const trialPct = sub ? trialProgressPct(sub) : null;
  const graceDays = sub ? graceDaysRemaining(sub) : null;

  return (
    <WorkspaceShell crumb="Settings · Billing">
      <div className="mx-auto max-w-3xl">
        <p className="text-[11px] uppercase tracking-[0.18em] text-ink-3">
          Settings · Billing
        </p>
        <h1 className="mt-1 text-[28px] font-semibold tracking-[-0.02em] text-ink">
          Your plan
        </h1>

        {loading ? (
          <p className="mt-8 text-ink-3">Loading billing details…</p>
        ) : !sub ? (
          <p className="mt-8 text-[13px] text-red-700">
            Error: {error ?? 'Could not load subscription'}
          </p>
        ) : (
          <>
            <SoftCard className="mt-8 overflow-hidden">
              <div className="relative p-6">
                <div
                  aria-hidden
                  className="pointer-events-none absolute -right-20 -top-20 h-52 w-52 rounded-full opacity-40 blur-3xl"
                  style={{
                    backgroundImage:
                      'radial-gradient(circle at 30% 30%, rgba(20,184,166,0.55), transparent 55%), radial-gradient(circle at 70% 40%, rgba(37,99,235,0.55), transparent 55%), radial-gradient(circle at 50% 80%, rgba(124,58,237,0.55), transparent 55%)',
                  }}
                />
                <div className="relative flex flex-wrap items-start justify-between gap-6">
                  <div className="min-w-0">
                    {onTrial && (
                      <>
                        <span className="inline-flex items-center rounded-full border border-line bg-white px-2.5 py-0.5 text-[11.5px] font-medium text-ink">
                          Free trial
                        </span>
                        <h3 className="mt-3 text-[22px] font-semibold text-ink">
                          {trialDays !== null && trialDays > 0
                            ? `${trialDays} day${trialDays === 1 ? '' : 's'} remaining`
                            : 'Trial ends today'}
                        </h3>
                        <p className="mt-1 max-w-md text-[13px] text-ink-3">
                          Trial ends {formatDate(sub.trial_ends_at)} · subscribe
                          to keep scans running and unlock unlimited
                          evaluations.
                        </p>
                        <div className="mt-5 flex flex-wrap items-center gap-3">
                          <button
                            type="button"
                            onClick={handleSubscribe}
                            disabled={actionPending}
                            style={GRADIENT_BG}
                            className={GRADIENT_BUTTON}
                          >
                            Subscribe — $4.99/mo
                          </button>
                          <button
                            type="button"
                            className="text-[12px] text-ink-3 hover:text-ink"
                          >
                            Compare plans
                          </button>
                        </div>
                      </>
                    )}

                    {isPro && !willCancel && (
                      <>
                        <span
                          className="inline-flex items-center rounded-full px-2.5 py-0.5 text-[11.5px] font-semibold text-white"
                          style={GRADIENT_BG}
                        >
                          Pro plan
                        </span>
                        <h3 className="mt-3 text-[22px] font-semibold text-ink">
                          $4.99/mo
                        </h3>
                        <p className="mt-1 text-[13px] text-ink-3">
                          Renews {formatDate(sub.current_period_end)}.
                        </p>
                        <button
                          type="button"
                          onClick={handleManage}
                          disabled={actionPending}
                          className="mt-5 rounded-lg border border-line-2 bg-white px-4 py-2 text-[13px] font-medium text-ink hover:bg-card disabled:opacity-50"
                        >
                          Manage billing
                        </button>
                      </>
                    )}

                    {isPro && willCancel && (
                      <>
                        <span className="inline-flex items-center rounded-full bg-amber/10 px-2.5 py-0.5 text-[11.5px] font-medium text-amber">
                          Cancelling
                        </span>
                        <h3 className="mt-3 text-[22px] font-semibold text-ink">
                          Access ends {formatDate(sub.current_period_end)}
                        </h3>
                        <p className="mt-1 text-[13px] text-ink-3">
                          You can undo this from the billing portal.
                        </p>
                        <button
                          type="button"
                          onClick={handleManage}
                          disabled={actionPending}
                          className="mt-5 rounded-lg border border-line-2 bg-white px-4 py-2 text-[13px] font-medium text-ink hover:bg-card disabled:opacity-50"
                        >
                          Manage billing
                        </button>
                      </>
                    )}

                    {isPastDue && (
                      <>
                        <span className="inline-flex items-center rounded-full bg-red-50 px-2.5 py-0.5 text-[11.5px] font-medium text-red-700">
                          Payment failed
                        </span>
                        <h3 className="mt-3 text-[22px] font-semibold text-ink">
                          {graceDays !== null && graceDays > 0
                            ? `Update card within ${graceDays} day${graceDays === 1 ? '' : 's'}`
                            : 'Access will be revoked shortly'}
                        </h3>
                        <p className="mt-1 max-w-md text-[13px] text-ink-3">
                          We'll keep retrying the card. Updating it now avoids
                          any interruption.
                        </p>
                        <button
                          type="button"
                          onClick={handleManage}
                          disabled={actionPending}
                          className="mt-5 rounded-lg bg-red-600 px-4 py-2 text-[13px] font-semibold text-white disabled:opacity-50"
                        >
                          Update card
                        </button>
                      </>
                    )}

                    {isCanceled && (
                      <>
                        <span className="inline-flex items-center rounded-full bg-card px-2.5 py-0.5 text-[11.5px] font-medium text-ink-3">
                          No active subscription
                        </span>
                        <h3 className="mt-3 text-[22px] font-semibold text-ink">
                          Come back when you're ready
                        </h3>
                        <p className="mt-1 text-[13px] text-ink-3">
                          Your previous subscription ended. Subscribe again to
                          restore access.
                        </p>
                        <button
                          type="button"
                          onClick={handleSubscribe}
                          disabled={actionPending}
                          style={GRADIENT_BG}
                          className={`mt-5 ${GRADIENT_BUTTON}`}
                        >
                          Subscribe — $4.99/mo
                        </button>
                      </>
                    )}

                    {!onTrial && !isPro && !isPastDue && !isCanceled && (
                      <p className="text-[13px] text-ink-3">
                        Plan state: {sub.plan} ({sub.status}). Contact support
                        if this looks wrong.
                      </p>
                    )}
                  </div>

                  {onTrial && trialPct !== null && (
                    <div className="hidden sm:flex flex-col items-end">
                      <div className="text-[11px] uppercase tracking-[0.18em] text-ink-3">
                        Trial progress
                      </div>
                      <div className="mt-3 h-2 w-40 overflow-hidden rounded-full bg-line-2">
                        <div
                          className="h-full rounded-full"
                          style={{
                            width: `${trialPct}%`,
                            backgroundImage:
                              'linear-gradient(90deg, #14b8a6, #2563eb, #7c3aed)',
                          }}
                        />
                      </div>
                      <div className="mt-1 text-[11.5px] text-ink-3">
                        Day {Math.max(1, 15 - (trialDays ?? 0))} of 15
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </SoftCard>

            <div className="mt-6 grid gap-3 md:grid-cols-3">
              <SoftCard className="p-5">
                <div className="flex items-center gap-2">
                  <FileText size={16} className="text-ink-3" strokeWidth={1.8} />
                  <span className="text-[13.5px] font-medium text-ink">
                    Download receipts
                  </span>
                </div>
                <p className="mt-2 text-[12px] text-ink-3">
                  Exportable PDFs for your records.
                </p>
              </SoftCard>
              <SoftCard className="p-5">
                <div className="flex items-center gap-2">
                  <CreditCard size={16} className="text-ink-3" strokeWidth={1.8} />
                  <span className="text-[13.5px] font-medium text-ink">
                    Payment method
                  </span>
                </div>
                <p className="mt-2 text-[12px] text-ink-3">
                  Add one before your trial ends.
                </p>
              </SoftCard>
              <SoftCard className="p-5">
                <div className="flex items-center gap-2">
                  <Trash2 size={16} className="text-ink-3" strokeWidth={1.8} />
                  <span className="text-[13.5px] font-medium text-ink">
                    Delete account
                  </span>
                </div>
                <p className="mt-2 text-[12px] text-ink-3">
                  We remove everything within 7 days.
                </p>
              </SoftCard>
            </div>
          </>
        )}

        {error && !loading && sub && (
          <p className="mt-4 text-[13px] text-red-600">Error: {error}</p>
        )}
      </div>
    </WorkspaceShell>
  );
}
