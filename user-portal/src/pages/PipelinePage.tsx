import { useCallback, useEffect, useState } from 'react';

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

  return (
    <WorkspaceShell>
      <div className="mx-auto max-w-6xl space-y-6">
        <header>
          <h1 className="text-[28px] font-semibold tracking-tight">Pipeline</h1>
          <p className="mt-1 text-[13px] text-ink-3">
            Drag a role across columns as it moves through the process. Changes save automatically.
          </p>
        </header>

        {error && (
          <p
            role="alert"
            className="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-[13px] text-red-800"
          >
            {error}
          </p>
        )}

        {loading ? (
          <div className="text-ink-3">Loading pipeline…</div>
        ) : (
          <>
            <Kanban<Stage, Item>
              columns={COLUMNS}
              items={items}
              onStageChange={handleStageChange}
              emptyHint="Drop cards here"
              renderCard={(item) => (
                <div>
                  <div className="text-[14px] font-medium text-ink">
                    {item.notes ?? 'Saved role'}
                  </div>
                  <div className="mt-1 text-[11px] text-ink-3">
                    Updated {new Date(item.updated_at).toLocaleDateString()}
                  </div>
                  <a
                    href={`/jobs/${item.job_id}`}
                    className="mt-2 inline-block text-[11px] text-accent-cobalt hover:underline"
                  >
                    View job →
                  </a>
                </div>
              )}
            />
            {apps.length === 0 && (
              <EmptyState
                title="Nothing in your pipeline yet."
                body="Save a job from a scan or evaluation to see it here."
              />
            )}
          </>
        )}
      </div>
    </WorkspaceShell>
  );
}
