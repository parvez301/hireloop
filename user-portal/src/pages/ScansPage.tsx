import { useCallback, useEffect, useState } from 'react';

import { AppShell } from '../components/layout/AppShell';
import { api, type ScanConfig, type ScanRun } from '../lib/api';
import ScanConfigEditor from './ScanConfigEditor';

export default function ScansPage() {
  const [configs, setConfigs] = useState<ScanConfig[]>([]);
  const [runs, setRuns] = useState<Record<string, ScanRun>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<ScanConfig | null | 'new'>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const configResp = await api.scanConfigs.list();
      setConfigs(configResp.data);
      const runsResp = await api.scanRuns.list({ limit: 100 });
      const byConfig: Record<string, ScanRun> = {};
      for (const run of runsResp.data) {
        const prev = byConfig[run.scan_config_id];
        if (!prev || new Date(run.started_at) > new Date(prev.started_at)) {
          byConfig[run.scan_config_id] = run;
        }
      }
      setRuns(byConfig);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function runScan(config: ScanConfig) {
    try {
      const resp = await api.scanConfigs.run(config.id);
      window.location.href = `/scans/${resp.data.scan_run_id}`;
    } catch (e) {
      setError((e as Error).message);
    }
  }

  async function deleteConfig(config: ScanConfig) {
    if (!confirm(`Delete "${config.name}"?`)) return;
    try {
      await api.scanConfigs.delete(config.id);
      await load();
    } catch (e) {
      setError((e as Error).message);
    }
  }

  return (
    <AppShell>
      <div className="mx-auto max-w-3xl">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-semibold">Scans</h1>
          <button
            type="button"
            onClick={() => setEditing('new')}
            className="rounded bg-[#2383e2] px-4 py-2 text-sm font-medium text-white"
          >
            New scan config
          </button>
        </div>

        {error && <p className="mt-4 text-sm text-[#e03e3e]">Error: {error}</p>}

        {loading ? (
          <p className="mt-8 text-sm text-[#787774]">Loading…</p>
        ) : configs.length === 0 ? (
          <p className="mt-8 text-sm text-[#787774]">
            No scan configs yet. Complete onboarding to get the default one, or create a new one
            above.
          </p>
        ) : (
          <ul className="mt-6 space-y-3">
            {configs.map((c) => {
              const run = runs[c.id];
              return (
                <li
                  key={c.id}
                  className="rounded-lg border border-[#e3e2e0] bg-[#fbfbfa] p-4"
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <h3 className="text-base font-semibold">{c.name}</h3>
                      <p className="mt-1 text-xs text-[#787774]">
                        {c.companies.length} companies
                        {c.keywords?.length ? ` · ${c.keywords.length} keywords` : ''}
                      </p>
                      {run && (
                        <p className="mt-1 text-xs text-[#787774]">
                          Last run: {run.status}
                          {run.status === 'completed' &&
                            ` — ${run.jobs_found} jobs (${run.jobs_new} new)`}
                          {' · '}
                          <a href={`/scans/${run.id}`} className="text-[#2383e2]">
                            View
                          </a>
                        </p>
                      )}
                    </div>
                    <div className="flex gap-2">
                      <button
                        type="button"
                        onClick={() => runScan(c)}
                        className="rounded bg-[#2383e2] px-3 py-1 text-xs text-white"
                      >
                        Run now
                      </button>
                      <button
                        type="button"
                        onClick={() => setEditing(c)}
                        className="rounded border border-[#e3e2e0] px-3 py-1 text-xs"
                      >
                        Edit
                      </button>
                      <button
                        type="button"
                        onClick={() => deleteConfig(c)}
                        className="rounded border border-[#e3e2e0] px-3 py-1 text-xs text-[#e03e3e]"
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </div>

      {editing !== null && (
        <ScanConfigEditor
          existing={editing === 'new' ? undefined : editing}
          onSave={() => {
            setEditing(null);
            void load();
          }}
          onCancel={() => setEditing(null)}
        />
      )}
    </AppShell>
  );
}
