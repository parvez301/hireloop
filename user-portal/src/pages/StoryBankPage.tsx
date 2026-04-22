import { useCallback, useEffect, useState } from 'react';

import { WorkspaceShell } from '../components/workspace/WorkspaceShell';
import { ApiError, api, type StarStory } from '../lib/api';

export default function StoryBankPage() {
  const [rows, setRows] = useState<StarStory[]>([]);
  const [error, setError] = useState<string | null>(null);
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
    if (!title.trim() || !situation.trim() || !task.trim() || !action.trim() || !result.trim()) {
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
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Failed to save');
    }
  }

  return (
    <WorkspaceShell>
      <h1 className="text-xl font-semibold">Story bank</h1>
      <p className="mt-1 text-sm text-[#787774]">
        STAR stories power interview prep. Add or edit your accomplishments here.
      </p>

      {error && <p className="mt-2 text-sm text-[#e03e3e]">{error}</p>}

      <form onSubmit={(e) => void addStory(e)} className="mt-6 space-y-2 rounded border border-[#e3e2e0] p-4">
        <p className="text-sm font-medium">Add story</p>
        <input
          className="w-full rounded border border-[#e3e2e0] px-2 py-1 text-sm"
          placeholder="Title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
        />
        <textarea
          className="w-full rounded border border-[#e3e2e0] px-2 py-1 text-sm"
          placeholder="Situation"
          rows={2}
          value={situation}
          onChange={(e) => setSituation(e.target.value)}
        />
        <textarea
          className="w-full rounded border border-[#e3e2e0] px-2 py-1 text-sm"
          placeholder="Task"
          rows={2}
          value={task}
          onChange={(e) => setTask(e.target.value)}
        />
        <textarea
          className="w-full rounded border border-[#e3e2e0] px-2 py-1 text-sm"
          placeholder="Action"
          rows={2}
          value={action}
          onChange={(e) => setAction(e.target.value)}
        />
        <textarea
          className="w-full rounded border border-[#e3e2e0] px-2 py-1 text-sm"
          placeholder="Result"
          rows={2}
          value={result}
          onChange={(e) => setResult(e.target.value)}
        />
        <button type="submit" className="rounded bg-[#2383e2] px-3 py-1 text-sm text-white">
          Save story
        </button>
      </form>

      <ul className="mt-8 space-y-3">
        {rows.map((s) => (
          <li key={s.id} className="rounded border border-[#e3e2e0] bg-[#fbfbfa] p-3 text-sm">
            <p className="font-semibold">{s.title}</p>
            <p className="text-[#787774]">
              {s.tags?.length ? s.tags.join(', ') : s.source}
            </p>
          </li>
        ))}
      </ul>
    </WorkspaceShell>
  );
}
