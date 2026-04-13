import { useCallback, useMemo, useState } from 'react';

import { AppShell } from '../components/layout/AppShell';
import { api, type ScanRunDetail } from '../lib/api';
import { usePolling } from '../lib/polling';

export default function ScanDetailPage() {
  const scanRunId = useMemo(() => {
    const parts = window.location.pathname.split('/');
    return parts[parts.length - 1];
  }, []);

  const [batchError, setBatchError] = useState<string | null>(null);
  const [batchPending, setBatchPending] = useState(false);

  const fetcher = useCallback(
    () => api.scanRuns.get(scanRunId).then((r) => r.data),
    [scanRunId],
  );

  const { data, error, loading } = usePolling<ScanRunDetail>(
    fetcher,
    3000,
    (latest) =>
      latest.scan_run.status === 'completed' || latest.scan_run.status === 'failed',
  );

  async function evaluateAll() {
    if (!data) return;
    setBatchPending(true);
    setBatchError(null);
    try {
      const resp = await api.batchRuns.create({ scan_run_id: data.scan_run.id });
      window.location.href = `/`;
      void resp;
    } catch (e) {
      setBatchError((e as Error).message);
      setBatchPending(false);
    }
  }

  if (loading && !data) {
    return (
      <AppShell>
        <p className="text-sm text-[#787774]">Loading scan…</p>
      </AppShell>
    );
  }

  if (error && !data) {
    return (
      <AppShell>
        <p className="text-sm text-[#e03e3e]">Error: {error.message}</p>
      </AppShell>
    );
  }

  if (!data) return null;

  const { scan_run, results } = data;
  const isRunning = scan_run.status === 'pending' || scan_run.status === 'running';

  return (
    <AppShell>
      <div className="mx-auto max-w-3xl">
        <a href="/scans" className="text-sm text-[#2383e2]">
          ← Back to scans
        </a>
        <h1 className="mt-2 text-2xl font-semibold">Scan run</h1>
        <p className="mt-1 text-sm text-[#787774]">
          Status: {scan_run.status}
          {scan_run.status === 'completed' &&
            ` · ${scan_run.jobs_found} jobs (${scan_run.jobs_new} new)`}
          {scan_run.truncated && ' · (truncated at 500)'}
        </p>

        {isRunning && (
          <div className="mt-4 rounded border border-[#e3e2e0] bg-[#fbfbfa] p-4 text-sm">
            Scan in progress — this page refreshes automatically.
          </div>
        )}

        {scan_run.status === 'completed' && (
          <>
            <div className="mt-6 flex items-center justify-between">
              <h2 className="text-lg font-semibold">Top results</h2>
              <button
                type="button"
                onClick={evaluateAll}
                disabled={batchPending || results.length === 0}
                className="rounded bg-[#2383e2] px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
              >
                {batchPending ? 'Starting…' : 'Evaluate all'}
              </button>
            </div>
            {batchError && <p className="mt-2 text-sm text-[#e03e3e]">{batchError}</p>}
            <ul className="mt-3 divide-y divide-[#e3e2e0]">
              {results.length === 0 && (
                <li className="py-4 text-sm text-[#787774]">No results in this scan run.</li>
              )}
              {results.map((r) => (
                <li key={r.id} className="flex items-center justify-between py-3">
                  <span className="text-sm">
                    Job <span className="font-mono text-xs">{r.job_id.slice(0, 8)}</span>
                  </span>
                  <span className="text-xs text-[#787774]">
                    Relevance:{' '}
                    <strong>
                      {r.relevance_score === null ? 'n/a' : r.relevance_score.toFixed(2)}
                    </strong>
                    {r.is_new ? ' · new' : ''}
                  </span>
                </li>
              ))}
            </ul>
          </>
        )}

        {scan_run.status === 'failed' && (
          <div className="mt-6 rounded border border-[#e03e3e] bg-[#fdf1f1] p-4 text-sm text-[#e03e3e]">
            Scan failed: {scan_run.error ?? 'Unknown error'}
          </div>
        )}
      </div>
    </AppShell>
  );
}
