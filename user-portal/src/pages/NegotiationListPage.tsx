import { useEffect, useState } from 'react';

import { EmptyState } from '../components/ui/EmptyState';
import { SoftCard } from '../components/ui/SoftCard';
import { WorkspaceShell } from '../components/workspace/WorkspaceShell';
import { api, type Negotiation } from '../lib/api';

export default function NegotiationListPage() {
  const [rows, setRows] = useState<Negotiation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function run() {
      try {
        const r = await api.negotiations.list();
        if (!cancelled) setRows(r.data);
      } catch (e) {
        if (!cancelled) setError((e as Error).message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void run();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <WorkspaceShell>
      <div className="mx-auto max-w-5xl">
        <div className="flex items-end justify-between gap-4">
          <div>
            <p className="text-[11px] uppercase tracking-[0.18em] text-ink-3">
              Offer in hand
            </p>
            <h1 className="mt-1 text-[28px] font-semibold tracking-[-0.02em] text-ink">
              Negotiation
            </h1>
            <p className="mt-2 max-w-xl text-[14px] text-ink-3">
              Saved playbooks and scripts. Each one breaks down what to push
              on, what to trade, and the exact words to use.
            </p>
          </div>
          <a
            href="/ask"
            style={{
              backgroundImage:
                'linear-gradient(135deg, #0f766e 0%, #1d4ed8 45%, #6d28d9 100%)',
            }}
            className="inline-flex items-center gap-1 rounded-lg px-4 py-2 text-[13px] font-semibold text-white shadow-[0_14px_30px_-16px_rgba(37,99,235,0.55),inset_0_1px_0_rgba(255,255,255,0.15)]"
          >
            + New playbook
          </a>
        </div>

        {error && (
          <p
            role="alert"
            className="mt-5 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-[13px] text-red-800"
          >
            {error}
          </p>
        )}

        {loading ? (
          <div className="mt-6 text-ink-3">Loading…</div>
        ) : rows.length === 0 ? (
          <div className="mt-6">
            <EmptyState
              title="No negotiations yet."
              body="When you get an offer, ask the assistant to build a playbook — it'll walk you through the trade-offs and hand back a script."
            />
          </div>
        ) : (
          <ul className="mt-6 grid gap-3 md:grid-cols-2">
            {rows.map((negotiation) => (
              <li key={negotiation.id}>
                <a
                  href={`/negotiations/${negotiation.id}`}
                  className="group block"
                >
                  <SoftCard className="p-5 transition-shadow duration-150 group-hover:shadow-[0_12px_28px_-16px_rgba(31,29,26,0.18)] motion-reduce:transition-none">
                    <div className="flex items-center justify-between">
                      <span className="text-[11px] uppercase tracking-[0.18em] text-ink-3">
                        Playbook
                      </span>
                      <span className="text-[11px] text-ink-3">
                        {new Date(negotiation.created_at).toLocaleDateString()}
                      </span>
                    </div>
                    <div className="mt-3 text-[16px] font-semibold text-ink">
                      Job {negotiation.job_id.slice(0, 8)}…
                    </div>
                    <div className="mt-1 text-[12px] text-ink-3">
                      Open the playbook to see the ask, trade, and script.
                    </div>
                  </SoftCard>
                </a>
              </li>
            ))}
          </ul>
        )}
      </div>
    </WorkspaceShell>
  );
}
