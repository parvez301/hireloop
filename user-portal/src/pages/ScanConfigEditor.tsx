import { useState, type FormEvent } from 'react';

import { api, type CompanyRef, type ScanConfig } from '../lib/api';

interface Props {
  existing?: ScanConfig;
  onSave: (config: ScanConfig) => void;
  onCancel: () => void;
}

const PLATFORMS = ['greenhouse', 'ashby', 'lever'] as const;

export default function ScanConfigEditor({ existing, onSave, onCancel }: Props) {
  const [name, setName] = useState(existing?.name ?? '');
  const [companies, setCompanies] = useState<CompanyRef[]>(existing?.companies ?? []);
  const [keywordInput, setKeywordInput] = useState((existing?.keywords ?? []).join(', '));
  const [excludeInput, setExcludeInput] = useState(
    (existing?.exclude_keywords ?? []).join(', '),
  );
  const [newCompany, setNewCompany] = useState<CompanyRef>({
    name: '',
    platform: 'greenhouse',
    board_slug: '',
  });
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function addCompany() {
    if (!newCompany.name || !newCompany.board_slug) return;
    setCompanies([...companies, newCompany]);
    setNewCompany({ name: '', platform: 'greenhouse', board_slug: '' });
  }

  function removeCompany(idx: number) {
    setCompanies(companies.filter((_, i) => i !== idx));
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setPending(true);
    setError(null);
    const keywords = keywordInput
      .split(',')
      .map((k) => k.trim())
      .filter(Boolean);
    const exclude_keywords = excludeInput
      .split(',')
      .map((k) => k.trim())
      .filter(Boolean);
    try {
      if (existing) {
        const resp = await api.scanConfigs.update(existing.id, {
          name,
          companies,
          keywords: keywords.length ? keywords : null,
          exclude_keywords: exclude_keywords.length ? exclude_keywords : null,
        });
        onSave(resp.data);
      } else {
        const resp = await api.scanConfigs.create({
          name,
          companies,
          keywords: keywords.length ? keywords : null,
          exclude_keywords: exclude_keywords.length ? exclude_keywords : null,
          schedule: 'manual',
        });
        onSave(resp.data);
      }
    } catch (err) {
      setError((err as Error).message);
      setPending(false);
      return;
    }
    setPending(false);
  }

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/40 p-4">
      <form
        onSubmit={handleSubmit}
        className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-lg bg-white p-6 shadow-xl"
      >
        <h2 className="text-xl font-semibold">
          {existing ? 'Edit scan config' : 'New scan config'}
        </h2>

        <label className="mt-4 block text-sm font-medium">Name</label>
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
          className="mt-1 w-full rounded border border-[#e3e2e0] px-3 py-2 text-sm"
        />

        <h3 className="mt-6 text-sm font-medium">Companies ({companies.length})</h3>
        <ul className="mt-2 max-h-48 overflow-y-auto rounded border border-[#e3e2e0] bg-[#fbfbfa] p-2 text-sm">
          {companies.length === 0 && (
            <li className="text-[#787774]">No companies yet — add one below.</li>
          )}
          {companies.map((c, i) => (
            <li key={i} className="flex items-center justify-between py-1">
              <span>
                <strong>{c.name}</strong>{' '}
                <span className="text-[#787774]">
                  ({c.platform}:{c.board_slug})
                </span>
              </span>
              <button
                type="button"
                onClick={() => removeCompany(i)}
                className="text-xs text-[#e03e3e]"
              >
                Remove
              </button>
            </li>
          ))}
        </ul>

        <div className="mt-3 grid grid-cols-3 gap-2">
          <input
            placeholder="Name"
            value={newCompany.name}
            onChange={(e) => setNewCompany({ ...newCompany, name: e.target.value })}
            className="rounded border border-[#e3e2e0] px-2 py-1 text-sm"
          />
          <select
            value={newCompany.platform}
            onChange={(e) =>
              setNewCompany({
                ...newCompany,
                platform: e.target.value as CompanyRef['platform'],
              })
            }
            className="rounded border border-[#e3e2e0] px-2 py-1 text-sm"
          >
            {PLATFORMS.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
          <input
            placeholder="board_slug"
            value={newCompany.board_slug}
            onChange={(e) =>
              setNewCompany({ ...newCompany, board_slug: e.target.value })
            }
            className="rounded border border-[#e3e2e0] px-2 py-1 text-sm"
          />
        </div>
        <button
          type="button"
          onClick={addCompany}
          className="mt-2 rounded border border-[#e3e2e0] px-3 py-1 text-xs"
        >
          Add company
        </button>

        <label className="mt-6 block text-sm font-medium">
          Keywords (comma-separated)
        </label>
        <input
          value={keywordInput}
          onChange={(e) => setKeywordInput(e.target.value)}
          className="mt-1 w-full rounded border border-[#e3e2e0] px-3 py-2 text-sm"
        />

        <label className="mt-4 block text-sm font-medium">
          Exclude keywords (comma-separated)
        </label>
        <input
          value={excludeInput}
          onChange={(e) => setExcludeInput(e.target.value)}
          className="mt-1 w-full rounded border border-[#e3e2e0] px-3 py-2 text-sm"
        />

        {error && <p className="mt-4 text-sm text-[#e03e3e]">{error}</p>}

        <div className="mt-6 flex justify-end gap-2">
          <button
            type="button"
            onClick={onCancel}
            className="rounded border border-[#e3e2e0] px-4 py-2 text-sm"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={pending || !name || companies.length === 0}
            className="rounded bg-[#2383e2] px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            {pending ? 'Saving…' : 'Save'}
          </button>
        </div>
      </form>
    </div>
  );
}
