import { useCallback, useEffect, useState } from 'react';
import { DndContext, type DragEndEvent } from '@dnd-kit/core';

import { AppShell } from '../components/layout/AppShell';
import { KanbanColumn } from '../components/pipeline/KanbanColumn';
import { PipelineFilters } from '../components/pipeline/PipelineFilters';
import { api, type Application } from '../lib/api';

const COLUMNS: Array<{ status: Application['status']; title: string }> = [
  { status: 'saved', title: 'Saved' },
  { status: 'applied', title: 'Applied' },
  { status: 'interviewing', title: 'Interviewing' },
  { status: 'offered', title: 'Offered' },
  { status: 'rejected', title: 'Rejected' },
  { status: 'withdrawn', title: 'Withdrawn' },
];

export default function PipelinePage() {
  const [apps, setApps] = useState<Application[]>([]);
  const [minGrade, setMinGrade] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [metaByJob, setMetaByJob] = useState<
    Record<string, { title: string; company: string | null; grade?: string }>
  >({});

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const resp = await api.applications.list(minGrade ? { min_grade: minGrade } : {});
      setApps(resp.data);
      setMetaByJob({});
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [minGrade]);

  useEffect(() => {
    void load();
  }, [load]);

  const handleDragEnd = async (event: DragEndEvent) => {
    const appId = String(event.active.id);
    const newStatus = event.over?.id as Application['status'] | undefined;
    if (!newStatus) return;
    const app = apps.find((a) => a.id === appId);
    if (!app || app.status === newStatus) return;

    const prev = apps;
    setApps(apps.map((a) => (a.id === appId ? { ...a, status: newStatus } : a)));
    try {
      await api.applications.update(appId, { status: newStatus });
    } catch (e) {
      setApps(prev);
      setError((e as Error).message);
    }
  };

  return (
    <AppShell>
      <div className="max-w-full">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-semibold">Pipeline</h1>
          <PipelineFilters minGrade={minGrade} onMinGradeChange={setMinGrade} />
        </div>

        {error && <p className="mt-4 text-sm text-[#e03e3e]">Error: {error}</p>}
        {loading && <p className="mt-4 text-sm text-[#787774]">Loading…</p>}

        <DndContext onDragEnd={handleDragEnd}>
          <div className="mt-6 flex gap-4 overflow-x-auto pb-4">
            {COLUMNS.map((col) => (
              <KanbanColumn
                key={col.status}
                status={col.status}
                title={col.title}
                applications={apps.filter((a) => a.status === col.status)}
                metaByJob={metaByJob}
              />
            ))}
          </div>
        </DndContext>
      </div>
    </AppShell>
  );
}
