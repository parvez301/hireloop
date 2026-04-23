import { useEffect, useState } from 'react';

import { WorkspaceShell } from '../components/workspace/WorkspaceShell';
import { api, type InterviewPrep } from '../lib/api';

export default function InterviewPrepListPage() {
  const [rows, setRows] = useState<InterviewPrep[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function run() {
      try {
        const r = await api.interviewPreps.list();
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
      <h1 className="text-xl font-semibold">Interview prep</h1>
      <p className="mt-1 text-sm text-ink-3">Saved prep packs from chat or the API.</p>
      {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
      <ul className="mt-6 space-y-2">
        {rows.map((p) => (
          <li key={p.id}>
            <a
              href={`/interview-prep/${p.id}`}
              className="text-cobalt hover:underline"
            >
              {p.custom_role || `Job ${p.job_id?.slice(0, 8) ?? ''}…`} —{' '}
              {new Date(p.created_at).toLocaleString()}
            </a>
          </li>
        ))}
      </ul>
      {rows.length === 0 && !error && (
        <p className="mt-4 text-sm text-ink-3">No interview prep yet. Ask the assistant in chat.</p>
      )}
    </WorkspaceShell>
  );
}
