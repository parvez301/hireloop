import { useCallback, useEffect, useMemo, useState } from 'react';
import { Radar } from 'lucide-react';

import { Chip } from '../components/ui/Chip';
import { EmptyState } from '../components/ui/EmptyState';
import { GradientButton } from '../components/ui/GradientButton';
import { SoftCard } from '../components/ui/SoftCard';
import { WorkspaceShell } from '../components/workspace/WorkspaceShell';
import {
  api,
  type Profile,
  type ScanConfig,
  type ScanRun,
} from '../lib/api';
import ScanConfigEditor from './ScanConfigEditor';

function hoursAgo(iso: string | null): string {
  if (!iso) return '—';
  const delta = Date.now() - new Date(iso).getTime();
  const hours = Math.round(delta / 3600_000);
  if (hours <= 0) return 'just now';
  if (hours < 24) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  return `${days}d ago`;
}

export default function ScansPage() {
  const [configs, setConfigs] = useState<ScanConfig[]>([]);
  const [runs, setRuns] = useState<Record<string, ScanRun>>({});
  const [recentRuns, setRecentRuns] = useState<ScanRun[]>([]);
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
      setRecentRuns(runsResponse.data);
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

  const kpis = useMemo(() => {
    const active = configs.filter((config) => config.is_active).length;
    const jobs7d = recentRuns
      .filter((run) => {
        const started = new Date(run.started_at).getTime();
        return Date.now() - started < 7 * 86400_000;
      })
      .reduce((sum, run) => sum + (run.jobs_found ?? 0), 0);
    const newFound = recentRuns.reduce(
      (sum, run) => sum + (run.jobs_new ?? 0),
      0,
    );
    return {
      active,
      total: configs.length,
      jobs7d,
      newFound,
    };
  }, [configs, recentRuns]);

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
      <div className="mx-auto max-w-5xl">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-[11px] uppercase tracking-[0.18em] text-ink-3">
              Always-on sourcing
            </p>
            <h1 className="mt-1 text-[28px] font-semibold tracking-[-0.02em] text-ink">
              Scans
            </h1>
            <p className="mt-2 max-w-xl text-[14px] text-ink-3">
              Saved searches that run on a schedule. Click any scan for the
              latest run, history, and per-job reasoning.
            </p>
          </div>
          <GradientButton onClick={() => setEditing('new')}>
            + New scan
          </GradientButton>
        </div>

        <div className="mt-6 grid grid-cols-2 gap-3 md:grid-cols-4">
          <SoftCard className="p-4">
            <div className="text-[11px] uppercase tracking-[0.18em] text-ink-3">
              Active scans
            </div>
            <div className="mt-1 flex items-baseline gap-1.5 text-[24px] font-semibold text-ink">
              {kpis.active}
              <span className="text-[12px] font-normal text-ink-3">
                / {kpis.total}
              </span>
            </div>
          </SoftCard>
          <SoftCard className="p-4">
            <div className="text-[11px] uppercase tracking-[0.18em] text-ink-3">
              Jobs surfaced 7d
            </div>
            <div className="mt-1 text-[24px] font-semibold text-ink">
              {kpis.jobs7d}
            </div>
          </SoftCard>
          <SoftCard className="p-4">
            <div className="text-[11px] uppercase tracking-[0.18em] text-ink-3">
              New this period
            </div>
            <div className="mt-1 text-[24px] font-semibold text-ink">
              {kpis.newFound}
            </div>
          </SoftCard>
          <SoftCard className="p-4">
            <div className="text-[11px] uppercase tracking-[0.18em] text-ink-3">
              Last run
            </div>
            <div className="mt-1 text-[16px] font-semibold text-ink">
              {recentRuns[0] ? hoursAgo(recentRuns[0].started_at) : '—'}
            </div>
          </SoftCard>
        </div>

        {prefsIncomplete && (
          <div className="mt-5">
            <SoftCard className="p-4">
              <div
                className="flex items-start gap-3"
                role="alert"
                data-testid="preferences-needed-banner"
              >
                <Radar size={18} className="flex-none text-amber" />
                <div>
                  <p className="text-[13px] font-medium text-ink">
                    Set your scan targets first
                  </p>
                  <p className="mt-1 text-[12px] text-ink-3">
                    Add the roles and locations you want so we know what to
                    look for.
                  </p>
                  <a
                    href="/profile/targets"
                    className="mt-2 inline-block text-[12px] text-cobalt hover:underline"
                  >
                    Open Profile → Targets →
                  </a>
                </div>
              </div>
            </SoftCard>
          </div>
        )}

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
        ) : configs.length === 0 ? (
          <div className="mt-6">
            <EmptyState
              title="No scans yet."
              body="Create a scan to track new roles at companies you care about."
              cta={
                <GradientButton onClick={() => setEditing('new')}>
                  Create your first scan
                </GradientButton>
              }
            />
          </div>
        ) : (
          <div className="mt-5 space-y-3">
            {configs.map((config) => {
              const run = runs[config.id];
              const isRunning = run?.status === 'running';
              const isErrored = run?.status === 'failed';
              return (
                <SoftCard key={config.id} className="overflow-hidden">
                  <div className="flex items-start justify-between gap-4 p-5">
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-3">
                        <a
                          href={`/scans/${run?.id ?? config.id}`}
                          className="text-[16px] font-semibold text-ink hover:underline"
                        >
                          {config.name}
                        </a>
                        {isRunning && (
                          <span className="inline-flex items-center gap-1.5 rounded-full bg-teal/10 px-2 py-0.5 text-[11px] font-medium text-teal">
                            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-teal" />
                            Running
                          </span>
                        )}
                        {isErrored && (
                          <span className="inline-flex items-center gap-1.5 rounded-full bg-amber/10 px-2 py-0.5 text-[11px] font-medium text-amber">
                            ! Errored on last run
                          </span>
                        )}
                        {!isRunning && !isErrored && config.is_active && (
                          <span className="inline-flex items-center gap-1.5 rounded-full bg-card px-2 py-0.5 text-[11px] font-medium text-ink-3">
                            Idle
                          </span>
                        )}
                        {!config.is_active && (
                          <span className="inline-flex items-center gap-1.5 rounded-full bg-card px-2 py-0.5 text-[11px] font-medium text-ink-3">
                            Paused
                          </span>
                        )}
                        <span className="text-[11.5px] text-ink-3">
                          Last run {hoursAgo(run?.started_at ?? null)}
                        </span>
                      </div>
                      <div className="mt-2 flex flex-wrap gap-1.5">
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
                        {config.companies.length > 4 && (
                          <span className="inline-flex items-center rounded-full border border-line bg-white px-2.5 py-0.5 text-[11.5px] text-ink-3">
                            +{config.companies.length - 4} more
                          </span>
                        )}
                      </div>
                      {run && (
                        <div className="mt-3 flex flex-wrap items-center gap-5 text-[12px] text-ink-3">
                          <span>
                            <b className="text-ink-2">{run.jobs_found ?? 0}</b>{' '}
                            jobs
                            {(run.jobs_new ?? 0) > 0 && (
                              <>
                                {' '}
                                ·{' '}
                                <b className="text-teal">
                                  {run.jobs_new} new
                                </b>
                              </>
                            )}
                          </span>
                          <span>
                            status <b className="text-ink-2">{run.status}</b>
                          </span>
                        </div>
                      )}
                    </div>
                    <div className="flex flex-col gap-2">
                      <button
                        type="button"
                        onClick={() => runScan(config)}
                        style={{
                          backgroundImage:
                            'linear-gradient(135deg, #0f766e 0%, #1d4ed8 45%, #6d28d9 100%)',
                        }}
                        className="rounded-lg px-3 py-1.5 text-[12px] font-semibold text-white shadow-[0_14px_30px_-16px_rgba(37,99,235,0.55),inset_0_1px_0_rgba(255,255,255,0.15)]"
                      >
                        Run now
                      </button>
                      <button
                        type="button"
                        onClick={() => setEditing(config)}
                        className="rounded-lg border border-line-2 bg-white px-3 py-1.5 text-[12px] text-ink hover:bg-card"
                      >
                        Edit
                      </button>
                      <button
                        type="button"
                        onClick={() => deleteConfig(config)}
                        className="rounded-lg border border-line-2 bg-white px-3 py-1.5 text-[12px] text-amber hover:bg-amber/10"
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                </SoftCard>
              );
            })}

            <div className="rounded-2xl border border-dashed border-line-2 p-6 text-center">
              <p className="text-[13px] text-ink-3">
                Add another scan to widen your net — different seniority,
                location, or comp floor.
              </p>
              <button
                type="button"
                onClick={() => setEditing('new')}
                className="mt-3 rounded-lg border border-line-2 bg-white px-3 py-1.5 text-[12px] font-medium text-ink hover:bg-card"
              >
                + New scan
              </button>
            </div>
          </div>
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
