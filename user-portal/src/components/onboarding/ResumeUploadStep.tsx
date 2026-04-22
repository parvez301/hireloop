import { useRef, useState } from 'react';

import { api } from '../../lib/api';
import { GradientButton } from '../ui/GradientButton';

type Props = {
  onAdvance: () => void;
};

export function ResumeUploadStep({ onAdvance }: Props) {
  const [pasteMode, setPasteMode] = useState(false);
  const [text, setText] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  async function onFile(file: File) {
    setBusy(true);
    setError(null);
    try {
      const form = new FormData();
      form.append('file', file);
      await api.profile.uploadResume(form);
      onAdvance();
    } catch (e) {
      setError((e as Error).message);
      setPasteMode(true);
    } finally {
      setBusy(false);
    }
  }

  async function onPaste() {
    setBusy(true);
    setError(null);
    try {
      await api.profile.uploadResumeText(text);
      onAdvance();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <button
        type="button"
        onClick={() => fileRef.current?.click()}
        className="rounded-2xl border-2 border-dashed border-border p-12 text-center hover:bg-hover"
      >
        <p className="font-medium">Drag and drop your resume, or browse</p>
        <p className="mt-1 text-sm text-text-secondary">PDF or DOCX, up to 10MB</p>
        <input
          ref={fileRef}
          type="file"
          accept=".pdf,.docx"
          className="hidden"
          onChange={(event) => {
            const file = event.target.files?.[0];
            if (file) {
              void onFile(file);
            }
          }}
        />
      </button>

      <button
        type="button"
        className="self-start text-sm text-accent-cobalt hover:underline"
        onClick={() => setPasteMode((previous) => !previous)}
      >
        {pasteMode ? 'Upload a file instead' : 'Paste text instead'}
      </button>

      {pasteMode && (
        <div className="flex flex-col gap-2">
          <textarea
            value={text}
            onChange={(event) => setText(event.target.value)}
            rows={12}
            className="w-full rounded-lg border border-border p-3 font-mono text-sm"
            placeholder="Paste your resume as plain text or markdown…"
          />
          <GradientButton
            disabled={busy || !text.trim()}
            onClick={() => void onPaste()}
          >
            {busy ? 'Processing…' : 'Continue'}
          </GradientButton>
        </div>
      )}

      {error && (
        <p
          role="alert"
          className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800"
        >
          {error}
        </p>
      )}
    </div>
  );
}
