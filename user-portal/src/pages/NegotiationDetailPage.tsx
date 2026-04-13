import { useEffect, useState } from 'react';

import { AppShell } from '../components/layout/AppShell';
import { FeedbackWidget } from '../components/shared/FeedbackWidget';
import { OfferForm } from '../components/negotiation/OfferForm';
import { api, type Negotiation } from '../lib/api';

export default function NegotiationDetailPage({ id }: { id: string }) {
  const [neg, setNeg] = useState<Negotiation | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function run() {
      try {
        const r = await api.negotiations.get(id);
        if (!cancelled) setNeg(r.data);
      } catch (e) {
        if (!cancelled) setError((e as Error).message);
      }
    }
    void run();
    return () => {
      cancelled = true;
    };
  }, [id]);

  if (error) {
    return (
      <AppShell>
        <p className="text-[#e03e3e]">{error}</p>
      </AppShell>
    );
  }
  if (!neg) {
    return (
      <AppShell>
        <p className="text-[#787774]">Loading…</p>
      </AppShell>
    );
  }

  const mr = neg.market_research as Record<string, unknown>;
  const co = neg.counter_offer as Record<string, unknown>;
  const scripts = neg.scripts as Record<string, unknown>;

  return (
    <AppShell>
      <a href="/negotiations" className="text-sm text-[#2383e2] hover:underline">
        ← All negotiations
      </a>
      <h1 className="mt-2 text-xl font-semibold">Negotiation playbook</h1>
      <p className="text-xs text-[#787774]">{new Date(neg.created_at).toLocaleString()}</p>

      <section className="mt-6 rounded border border-[#e3e2e0] bg-[#fbfbfa] p-4 text-sm">
        <h2 className="font-semibold text-[#787774]">Market (indicative)</h2>
        <pre className="mt-2 overflow-x-auto whitespace-pre-wrap text-xs">{JSON.stringify(mr, null, 2)}</pre>
      </section>

      <section className="mt-4 rounded border border-[#e3e2e0] bg-[#fbfbfa] p-4 text-sm">
        <h2 className="font-semibold text-[#787774]">Counter-offer</h2>
        <pre className="mt-2 overflow-x-auto whitespace-pre-wrap text-xs">{JSON.stringify(co, null, 2)}</pre>
      </section>

      <section className="mt-4 rounded border border-[#e3e2e0] bg-white p-4 text-sm">
        <h2 className="font-semibold text-[#787774]">Scripts</h2>
        <pre className="mt-2 overflow-x-auto whitespace-pre-wrap text-xs">{JSON.stringify(scripts, null, 2)}</pre>
      </section>

      <section className="mt-8">
        <h2 className="text-sm font-semibold">New playbook for same job</h2>
        <p className="text-xs text-[#787774]">Submit a fresh offer to regenerate (entitled plan).</p>
        <OfferForm jobId={neg.job_id} onCreated={(nid) => (window.location.href = `/negotiations/${nid}`)} />
      </section>

      <FeedbackWidget resource="negotiation" resourceId={neg.id} className="mt-8" />
    </AppShell>
  );
}
