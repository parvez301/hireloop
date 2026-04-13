import { useCallback } from 'react';

import { api, type ScanRunDetail } from '../../../lib/api';
import { usePolling } from '../../../lib/polling';

interface ScanProgressCardData {
  scan_run_id: string;
  scan_name: string;
  status: string;
  companies_count: number;
}

export function ScanProgressCard({ data }: { data: ScanProgressCardData }) {
  const fetcher = useCallback(
    () => api.scanRuns.get(data.scan_run_id).then((r) => r.data),
    [data.scan_run_id],
  );
  const { data: run } = usePolling<ScanRunDetail>(
    fetcher,
    3000,
    (latest) =>
      latest.scan_run.status === 'completed' || latest.scan_run.status === 'failed',
  );

  const live = run ?? null;
  const status = live?.scan_run.status ?? data.status;
  const jobsFound = live?.scan_run.jobs_found ?? 0;
  const jobsNew = live?.scan_run.jobs_new ?? 0;

  const isRunning = status === 'pending' || status === 'running';
  const isCompleted = status === 'completed';
  const isFailed = status === 'failed';

  return (
    <article className="mt-3 rounded-lg border border-[#e3e2e0] bg-white p-4">
      <header>
        <h3 className="text-base font-semibold">Scanning — {data.scan_name}</h3>
        <p className="mt-1 text-xs text-[#787774]">{data.companies_count} companies</p>
      </header>

      {isRunning && (
        <div className="mt-3 flex items-center gap-3 text-sm">
          <div className="h-2 flex-1 rounded bg-[#f7f6f3]">
            <div className="h-2 w-1/3 animate-pulse rounded bg-[#2383e2]" />
          </div>
          <span className="text-[#787774]">Scraping…</span>
        </div>
      )}

      {isCompleted && (
        <div className="mt-3">
          <p className="text-sm">
            Found <strong>{jobsFound}</strong> jobs ({jobsNew} new).
          </p>
          <a
            href={`/scans/${data.scan_run_id}`}
            className="mt-2 inline-block rounded bg-[#2383e2] px-3 py-1 text-xs text-white"
          >
            View results
          </a>
        </div>
      )}

      {isFailed && (
        <p className="mt-3 text-sm text-[#e03e3e]">
          Scan failed. {live?.scan_run.error ?? ''}
        </p>
      )}
    </article>
  );
}
