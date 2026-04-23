import { useCallback } from 'react';

import { api, type BatchRunDetail } from '../../../lib/api';
import { usePolling } from '../../../lib/polling';

interface BatchProgressCardData {
  batch_run_id: string;
  status: string;
  total: number;
  l0_passed: number;
  l1_passed: number;
  l2_evaluated: number;
}

const GRADE_COLOR: Record<string, string> = {
  A: 'bg-[#35a849] text-white',
  'A-': 'bg-[#35a849] text-white',
  'B+': 'bg-cobalt text-white',
  B: 'bg-cobalt text-white',
  'B-': 'bg-cobalt text-white',
  'C+': 'bg-[#cb912f] text-white',
  C: 'bg-[#cb912f] text-white',
  D: 'bg-red-600 text-white',
  F: 'bg-red-600 text-white',
};

export function BatchProgressCard({ data }: { data: BatchProgressCardData }) {
  const fetcher = useCallback(
    () => api.batchRuns.get(data.batch_run_id).then((r) => r.data),
    [data.batch_run_id],
  );
  const { data: live } = usePolling<BatchRunDetail>(
    fetcher,
    3000,
    (latest) =>
      latest.batch_run.status === 'completed' || latest.batch_run.status === 'failed',
  );

  const run = live?.batch_run;
  const summary = live?.items_summary;
  const top = live?.top_results ?? [];
  const status = run?.status ?? data.status;
  const total = run?.total_jobs ?? data.total;
  const l0 = run?.l0_passed ?? data.l0_passed;
  const l1 = run?.l1_passed ?? data.l1_passed;
  const l2 = run?.l2_evaluated ?? data.l2_evaluated;

  return (
    <article className="mt-3 rounded-lg border border-line-2 bg-white p-4">
      <header>
        <h3 className="text-base font-semibold">Batch evaluation</h3>
        <p className="mt-1 text-xs text-ink-3">
          {total} jobs · status: {status}
        </p>
      </header>

      <div className="mt-3 grid grid-cols-4 gap-2 text-center text-xs">
        <div className="rounded bg-sidebar p-2">
          <div className="text-ink-3">Total</div>
          <div className="text-lg font-semibold">{total}</div>
        </div>
        <div className="rounded bg-sidebar p-2">
          <div className="text-ink-3">L0</div>
          <div className="text-lg font-semibold">{l0}</div>
        </div>
        <div className="rounded bg-sidebar p-2">
          <div className="text-ink-3">L1</div>
          <div className="text-lg font-semibold">{l1}</div>
        </div>
        <div className="rounded bg-sidebar p-2">
          <div className="text-ink-3">L2</div>
          <div className="text-lg font-semibold">{l2}</div>
        </div>
      </div>

      {summary && (
        <p className="mt-2 text-xs text-ink-3">
          Filtered: {summary.filtered} · Done: {summary.done}
        </p>
      )}

      {status === 'completed' && top.length > 0 && (
        <>
          <h4 className="mt-4 text-sm font-medium">Top matches</h4>
          <ul className="mt-2 divide-y divide-line-2">
            {top.map((t) => (
              <li
                key={t.evaluation_id}
                className="flex items-center justify-between py-2 text-sm"
              >
                <div>
                  <strong>{t.job_title}</strong>{' '}
                  <span className="text-ink-3">@ {t.company ?? '?'}</span>
                </div>
                <span
                  className={`rounded px-2 py-0.5 text-xs font-semibold ${
                    GRADE_COLOR[t.overall_grade] ?? 'bg-ink-4 text-white'
                  }`}
                >
                  {t.overall_grade}
                </span>
              </li>
            ))}
          </ul>
        </>
      )}

      {status === 'failed' && (
        <p className="mt-3 text-sm text-red-600">Batch failed.</p>
      )}
    </article>
  );
}
