import { useEffect, useState } from 'react';

import { WorkspaceShell } from '../components/workspace/WorkspaceShell';
import { api, type Negotiation } from '../lib/api';

export default function NegotiationListPage() {
  const [rows, setRows] = useState<Negotiation[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function run() {
      try {
        const r = await api.negotiations.list();
        if (!cancelled) setRows(r.data);
      } catch (e) {
        if (!cancelled) setError((e as Error).message);
      }
    }
    void run();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <WorkspaceShell>
      <h1 className="text-xl font-semibold">Negotiations</h1>
      <p className="mt-1 text-sm text-ink-3">Saved playbooks and scripts.</p>
      {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
      <ul className="mt-6 space-y-2">
        {rows.map((n) => (
          <li key={n.id}>
            <a href={`/negotiations/${n.id}`} className="text-cobalt hover:underline">
              Job {n.job_id.slice(0, 8)}… — {new Date(n.created_at).toLocaleString()}
            </a>
          </li>
        ))}
      </ul>
      {rows.length === 0 && !error && (
        <p className="mt-4 text-sm text-ink-3">
          No negotiations yet. Use the assistant and complete the offer form when prompted.
        </p>
      )}
    </WorkspaceShell>
  );
}
