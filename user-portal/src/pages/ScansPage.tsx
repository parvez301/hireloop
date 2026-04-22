import { useCallback, useEffect, useState } from 'react';
import { Radar } from 'lucide-react';

import { Chip } from '../components/ui/Chip';
import { EmptyState } from '../components/ui/EmptyState';
import { GradientButton } from '../components/ui/GradientButton';
import { SoftCard } from '../components/ui/SoftCard';
import { Sparkline } from '../components/ui/Sparkline';
import { WorkspaceShell } from '../components/workspace/WorkspaceShell';
import {
  api,
  type Profile,
  type ScanConfig,
  type ScanRun,
} from '../lib/api';
import ScanConfigEditor from './ScanConfigEditor';

function sparklineFromRun(run: ScanRun | undefined): number[] {
  if (!run) return [0, 0, 0, 0, 0, 0, 0];
  const total = run.jobs_found ?? 0;
  return [0, Math.max(0, total - 5), Math.max(0, total - 3), total, total, total, total];
}

export default function ScansPage() {
  const [configs, setConfigs] = useState<ScanConfig[]>([]);
  const [runs, setRuns] = useState<Record<string, ScanRun>>({});
  const [profile, setProfile] = useState<Profile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<ScanConfig | null | 'new'>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const configsResponse = await api.scanConfigs.list();
      setConfigs(configsResponse.data);
      const runsResponse = await api.scanRuns.list({ limit: 100 });
      const byConfig: Record<string, ScanRun> = {};
      for (const run of runsResponse.data) {
        const previous = byConfig[run.scan_config_id];
        if (!previous || new Date(run.started_at) > new Date(previous.started_at)) {
          byConfig[run.scan_config_id] = run;
        }
      }
      setRuns(byConfig);
    } catch (caught) {
      setError((caught as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    let cancelled = false;
    api.profile
      .get()
      .then((response) => {
        if (!cancelled) setProfile(response.data);
      })
      .catch(() => {
        /* JIT banner is nice-to-have */
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const prefsIncomplete =
    profile !== null &&
    (!profile.target_roles?.length || !profile.target_locations?.length);

  async function runScan(config: ScanConfig) {
    try {
      const response = await api.scanConfigs.run(config.id);
      window.location.assign(`/scans/${response.data.scan_run_id}`);
    } catch (caught) {
      setError((caught as Error).message);
    }
  }

  async function deleteConfig(config: ScanConfig) {
    if (!confirm(`Delete "${config.name}"?`)) return;
    try {
      await api.scanConfigs.delete(config.id);
      await load();
    } catch (caught) {
      setError((caught as Error).message);
    }
  }

  return (
    <WorkspaceShell>
      <div className="mx-auto max-w-5xl space-y-6">
        <header className="flex items-center justify-between">
          <div>
            <h1 className="text-[28px] font-semibold tracking-tight">Scans</h1>
            <p className="mt-1 text-[13px] text-ink-3">
              Saved searches that grade new jobs for you daily.
            </p>
          </div>
          <GradientButton onClick={() => setEditing('new')}>
            + New scan
          </GradientButton>
        </header>

        {prefsIncomplete && (
          <SoftCard padding="sm">
            <div className="flex items-start gap-3" role="alert" data-testid="preferences-needed-banner">
              <Radar size={18} className="flex-none text-amber" />
              <div>
                <p className="text-[13px] font-medium text-ink">Set your scan targets first</p>
                <p className="mt-1 text-[12px] text-ink-3">
                  Add the roles and locations you want so we know what to look for.
                </p>
                <a
                  href="/profile/targets"
                  className="mt-2 inline-block text-[12px] text-accent-cobalt hover:underline"
                >
                  Open Profile → Targets →
                </a>
              </div>
            </div>
          </SoftCard>
        )}

        {error && (
          <p
            role="alert"
            className="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-[13px] text-red-800"
          >
            {error}
          </p>
        )}

        {loading ? (
          <div className="text-ink-3">Loading…</div>
        ) : configs.length === 0 ? (
          <EmptyState
            title="No scans yet."
            body="Create a scan to track new roles at companies you care about."
            cta={
              <GradientButton onClick={() => setEditing('new')}>
                Create your first scan
              </GradientButton>
            }
          />
        ) : (
          <ul className="space-y-3">
            {configs.map((config) => {
              const run = runs[config.id];
              return (
                <li key={config.id}>
                  <SoftCard padding="md">
                    <div className="flex items-center justify-between gap-6">
                      <div className="min-w-0">
                        <a
                          href={`/scans/${run?.id ?? config.id}`}
                          className="text-[15px] font-semibold text-ink hover:underline"
                        >
                          {config.name}
                        </a>
                        <div className="mt-2 flex flex-wrap gap-2">
                          {config.companies.slice(0, 4).map((company) => (
                            <Chip
                              key={company.board_slug}
                              label={company.name}
                              variant="suggest"
                            />
                          ))}
                          {config.keywords?.slice(0, 3).map((keyword) => (
                            <Chip key={keyword} label={keyword} variant="suggest" />
                          ))}
                        </div>
                        {run && (
                          <p className="mt-2 text-[12px] text-ink-3">
                            Last run: {run.status}
                            {run.status === 'completed' &&
                              ` — ${run.jobs_found} jobs (${run.jobs_new} new)`}
                          </p>
                        )}
                      </div>
                      <div className="flex items-center gap-4">
                        <Sparkline values={sparklineFromRun(run)} label="Jobs" />
                        <div className="flex flex-col gap-1.5">
                          <button
                            type="button"
                            onClick={() => runScan(config)}
                            className="rounded-full border border-line-2 bg-white px-3 py-1 text-[12px] text-ink-2 hover:bg-[#faf9f6]"
                          >
                            Run now
                          </button>
                          <button
                            type="button"
                            onClick={() => setEditing(config)}
                            className="rounded-full border border-line-2 bg-white px-3 py-1 text-[12px] text-ink-2 hover:bg-[#faf9f6]"
                          >
                            Edit
                          </button>
                          <button
                            type="button"
                            onClick={() => deleteConfig(config)}
                            className="rounded-full border border-line-2 bg-white px-3 py-1 text-[12px] text-amber hover:bg-amber/10"
                          >
                            Delete
                          </button>
                        </div>
                      </div>
                    </div>
                  </SoftCard>
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
    </WorkspaceShell>
  );
}
