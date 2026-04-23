import { useCallback, useEffect, useState } from 'react';

import { EmptyState } from '../components/ui/EmptyState';
import { SoftCard } from '../components/ui/SoftCard';
import { WorkspaceShell } from '../components/workspace/WorkspaceShell';
import { ApiError, api, type StarStory } from '../lib/api';

export default function StoryBankPage() {
  const [rows, setRows] = useState<StarStory[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);
  const [title, setTitle] = useState('');
  const [situation, setSituation] = useState('');
  const [task, setTask] = useState('');
  const [action, setAction] = useState('');
  const [result, setResult] = useState('');

  const load = useCallback(async () => {
    setError(null);
    try {
      const r = await api.starStories.list();
      setRows(r.data);
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function addStory(e: React.FormEvent) {
    e.preventDefault();
    if (
      !title.trim() ||
      !situation.trim() ||
      !task.trim() ||
      !action.trim() ||
      !result.trim()
    ) {
      return;
    }
    try {
      await api.starStories.create({
        title: title.trim(),
        situation: situation.trim(),
        task: task.trim(),
        action: action.trim(),
        result: result.trim(),
      });
      setTitle('');
      setSituation('');
      setTask('');
      setAction('');
      setResult('');
      setAdding(false);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Failed to save');
    }
  }

  return (
    <WorkspaceShell>
      <div className="mx-auto max-w-5xl">
        <div className="flex items-end justify-between gap-4">
          <div>
            <p className="text-[11px] uppercase tracking-[0.18em] text-ink-3">
              Reusable across jobs
            </p>
            <h1 className="mt-1 text-[28px] font-semibold tracking-[-0.02em] text-ink">
              Story bank
            </h1>
            <p className="mt-2 max-w-xl text-[14px] text-ink-3">
              STAR stories are global — one story can power many prep packs.
              Add your accomplishments here so the assistant can weave them
              into every interview.
            </p>
          </div>
          <button
            type="button"
            onClick={() => setAdding((previous) => !previous)}
            style={{
              backgroundImage:
                'linear-gradient(135deg, #0f766e 0%, #1d4ed8 45%, #6d28d9 100%)',
            }}
            className="inline-flex items-center gap-1 rounded-lg px-4 py-2 text-[13px] font-semibold text-white shadow-[0_14px_30px_-16px_rgba(37,99,235,0.55),inset_0_1px_0_rgba(255,255,255,0.15)]"
          >
            {adding ? 'Cancel' : '+ New story'}
          </button>
        </div>

        {error && (
          <p
            role="alert"
            className="mt-5 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-[13px] text-red-800"
          >
            {error}
          </p>
        )}

        {adding && (
          <SoftCard className="mt-6 p-5">
            <form onSubmit={(e) => void addStory(e)} className="space-y-3">
              <p className="text-[13px] font-semibold text-ink">Add story</p>
              <input
                className="w-full rounded-lg border border-line-2 bg-white px-3 py-2 text-[14px] text-ink placeholder:text-ink-4 focus:border-ink focus:outline-none focus:ring-4 focus:ring-black/5"
                placeholder="Title (e.g. Scaled design system across 4 squads)"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
              />
              <textarea
                className="w-full rounded-lg border border-line-2 bg-white px-3 py-2 text-[14px] text-ink placeholder:text-ink-4 focus:border-ink focus:outline-none focus:ring-4 focus:ring-black/5"
                placeholder="Situation"
                rows={2}
                value={situation}
                onChange={(e) => setSituation(e.target.value)}
              />
              <textarea
                className="w-full rounded-lg border border-line-2 bg-white px-3 py-2 text-[14px] text-ink placeholder:text-ink-4 focus:border-ink focus:outline-none focus:ring-4 focus:ring-black/5"
                placeholder="Task"
                rows={2}
                value={task}
                onChange={(e) => setTask(e.target.value)}
              />
              <textarea
                className="w-full rounded-lg border border-line-2 bg-white px-3 py-2 text-[14px] text-ink placeholder:text-ink-4 focus:border-ink focus:outline-none focus:ring-4 focus:ring-black/5"
                placeholder="Action"
                rows={2}
                value={action}
                onChange={(e) => setAction(e.target.value)}
              />
              <textarea
                className="w-full rounded-lg border border-line-2 bg-white px-3 py-2 text-[14px] text-ink placeholder:text-ink-4 focus:border-ink focus:outline-none focus:ring-4 focus:ring-black/5"
                placeholder="Result (quantify it)"
                rows={2}
                value={result}
                onChange={(e) => setResult(e.target.value)}
              />
              <button
                type="submit"
                className="rounded-lg bg-ink px-3 py-2 text-[13px] font-semibold text-white hover:bg-ink-2"
              >
                Save story
              </button>
            </form>
          </SoftCard>
        )}

        {rows.length === 0 && !adding ? (
          <div className="mt-6">
            <EmptyState
              title="No stories yet."
              body="Add 6–8 STAR stories to cover the classic interview bucket — leadership, scope, conflict, metrics, ambiguity, failure."
            />
          </div>
        ) : (
          <ul className="mt-6 grid gap-3 md:grid-cols-2">
            {rows.map((story) => (
              <li key={story.id}>
                <SoftCard className="p-5">
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] uppercase tracking-[0.18em] text-ink-3">
                      {story.source ?? 'Manual'}
                    </span>
                  </div>
                  <div className="mt-3 text-[16px] font-semibold text-ink">
                    {story.title}
                  </div>
                  {story.tags && story.tags.length > 0 && (
                    <div className="mt-3 flex flex-wrap gap-1.5">
                      {story.tags.map((tag) => (
                        <span
                          key={tag}
                          className="inline-flex items-center rounded-full border border-line bg-white px-2.5 py-0.5 text-[11.5px] text-ink-3"
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  )}
                </SoftCard>
              </li>
            ))}
          </ul>
        )}
      </div>
    </WorkspaceShell>
  );
}
