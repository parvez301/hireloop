import { useState } from 'react';

import { GradientButton } from '../ui/GradientButton';

type JobInputValue = { type: 'url' | 'text'; value: string };

type Props = {
  onSubmit: (input: JobInputValue) => void;
  busy?: boolean;
  error?: string | null;
};

export function JobInputStep({ onSubmit, busy = false, error = null }: Props) {
  const [value, setValue] = useState('');

  function submit() {
    const trimmed = value.trim();
    if (!trimmed) return;
    const type: 'url' | 'text' = /^https?:\/\//i.test(trimmed) ? 'url' : 'text';
    onSubmit({ type, value: trimmed });
  }

  return (
    <div className="flex flex-col gap-4">
      <h3 className="text-lg font-semibold">
        Paste a job you're curious about. We'll show you how you stack up.
      </h3>
      <textarea
        value={value}
        onChange={(event) => setValue(event.target.value)}
        rows={6}
        placeholder="https://example.com/jobs/123  — or paste the job description"
        className="w-full rounded-lg border border-border p-3 text-sm"
      />
      <GradientButton disabled={busy || !value.trim()} onClick={submit}>
        {busy ? 'Evaluating…' : 'Evaluate'}
      </GradientButton>
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
