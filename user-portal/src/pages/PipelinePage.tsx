import { useCallback, useEffect, useMemo, useState } from 'react';
import { Plus } from 'lucide-react';

import { EmptyState } from '../components/ui/EmptyState';
import { Kanban, type KanbanColumn } from '../components/ui/Kanban';
import { WorkspaceShell } from '../components/workspace/WorkspaceShell';
import { api, type Application } from '../lib/api';

type Stage = Application['status'];

const COLUMNS: KanbanColumn<Stage>[] = [
  { id: 'saved', label: 'Saved' },
  { id: 'applied', label: 'Applied' },
  { id: 'interviewing', label: 'Interviewing' },
  { id: 'offered', label: 'Offered' },
  { id: 'rejected', label: 'Rejected' },
  { id: 'withdrawn', label: 'Withdrawn' },
];

type Item = Application & { stage: Stage };

const MONOGRAM_COLORS = [
  '#0f766e',
  '#2563eb',
  '#7c3aed',
  '#4348B8',
  '#c2410c',
  '#1f1d1a',
];

function monogramColor(seed: string): string {
  let hash = 0;
  for (let index = 0; index < seed.length; index += 1) {
    hash = (hash * 31 + seed.charCodeAt(index)) >>> 0;
  }
  return MONOGRAM_COLORS[hash % MONOGRAM_COLORS.length];
}

function initialsOf(text: string | null): string {
  if (!text) return 'J';
  const trimmed = text.trim();
  if (!trimmed) return 'J';
  return trimmed.charAt(0).toUpperCase();
}

function relativeDate(iso: string): string {
  const delta = Date.now() - new Date(iso).getTime();
  const days = Math.round(delta / 86400000);
  if (days <= 0) return 'today';
  if (days === 1) return '1d ago';
  if (days < 7) return `${days}d ago`;
  const weeks = Math.round(days / 7);
  if (weeks === 1) return '1w';
  if (weeks < 5) return `${weeks}w`;
  const months = Math.round(days / 30);
  return `${months}mo`;
}

export default function PipelinePage() {
  const [apps, setApps] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const response = await api.applications.list();
      setApps(response.data);
    } catch (caught) {
      setError((caught as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function handleStageChange(id: string, nextStage: Stage) {
    const previous = apps;
    setApps((current) =>
      current.map((app) => (app.id === id ? { ...app, status: nextStage } : app)),
    );
    try {
      await api.applications.update(id, { status: nextStage });
    } catch (caught) {
      setApps(previous);
      setError((caught as Error).message);
    }
  }

  const items: Item[] = apps.map((app) => ({ ...app, stage: app.status }));
  const inMotion = useMemo(
    () =>
      items.filter(
        (item) => item.stage !== 'rejected' && item.stage !== 'withdrawn',
      ).length,
    [items],
  );

  return (
    <WorkspaceShell>
      <div className="mx-auto max-w-[1200px]">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-[11px] uppercase tracking-[0.18em] text-ink-3">
              {inMotion} in motion
            </p>
            <h1 className="mt-1 text-[28px] font-semibold tracking-[-0.02em] text-ink">
              Pipeline
            </h1>
          </div>
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1 rounded-full border border-line bg-white p-1 text-[12px]">
              <button
                type="button"
                className="rounded-full bg-ink px-2.5 py-1 text-[11.5px] font-medium text-white"
              >
                All grades
              </button>
              <button
                type="button"
                className="rounded-full px-2.5 py-1 text-[11.5px] text-ink-3 hover:text-ink"
              >
                A &amp; up
              </button>
              <button
                type="button"
                className="rounded-full px-2.5 py-1 text-[11.5px] text-ink-3 hover:text-ink"
              >
                B+ &amp; up
              </button>
            </div>
            <a
              href="/scans"
              style={{
                backgroundImage:
                  'linear-gradient(135deg, #0f766e 0%, #1d4ed8 45%, #6d28d9 100%)',
              }}
              className="inline-flex items-center gap-1 rounded-lg px-3 py-2 text-[12px] font-semibold text-white shadow-[0_14px_30px_-16px_rgba(37,99,235,0.55),0_2px_6px_-2px_rgba(15,23,42,0.12),inset_0_1px_0_rgba(255,255,255,0.15)] transition-transform duration-150 hover:-translate-y-px motion-reduce:transition-none"
            >
              <Plus size={12} strokeWidth={2.4} />
              Add job
            </a>
          </div>
        </div>

        {error && (
          <p
            role="alert"
            className="mt-6 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-[13px] text-red-800"
          >
            {error}
          </p>
        )}

        {loading ? (
          <div className="mt-8 text-ink-3">Loading pipeline…</div>
        ) : (
          <div className="mt-8">
            <Kanban<Stage, Item>
              columns={COLUMNS}
              items={items}
              onStageChange={handleStageChange}
              emptyHint="Drop cards here"
              renderCard={(item) => {
                const label = item.notes?.trim() || 'Saved role';
                const monogram = initialsOf(label);
                const color = monogramColor(item.job_id);
                return (
                  <div className="flex items-start gap-2.5">
                    <div
                      aria-hidden
                      className="flex h-10 w-10 flex-none items-center justify-center rounded-lg text-[14px] font-bold text-white"
                      style={{ backgroundColor: color }}
                    >
                      {monogram}
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="line-clamp-2 text-[14px] font-semibold leading-[1.3] text-ink">
                        {label}
                      </div>
                      <div className="mt-1 text-[12px] leading-snug text-ink-3">
                        {relativeDate(item.updated_at)}
                      </div>
                      <a
                        href={`/jobs/${item.job_id}`}
                        className="mt-2 inline-block text-[11px] text-cobalt hover:underline"
                      >
                        View job →
                      </a>
                    </div>
                  </div>
                );
              }}
            />
            {apps.length === 0 && (
              <div className="mt-8">
                <EmptyState
                  title="Nothing in your pipeline yet."
                  body="Save a job from a scan or evaluation to see it here."
                />
              </div>
            )}
          </div>
        )}
      </div>
    </WorkspaceShell>
  );
}
