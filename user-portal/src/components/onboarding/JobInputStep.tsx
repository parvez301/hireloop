import { useMemo, useRef, useState } from 'react';

import { GradientButton } from '../ui/GradientButton';

type JobInputValue = { type: 'url' | 'text'; value: string };

type Props = {
  onSubmit: (input: JobInputValue) => void;
  busy?: boolean;
  error?: string | null;
};

type DetectResult =
  | { kind: 'empty' }
  | { kind: 'url'; url: string }
  | { kind: 'text'; wordCount: number };

function detect(input: string): DetectResult {
  const trimmed = input.trim();
  if (!trimmed) return { kind: 'empty' };
  if (/^https?:\/\//i.test(trimmed)) {
    return { kind: 'url', url: trimmed };
  }
  const words = trimmed.split(/\s+/).filter(Boolean).length;
  return { kind: 'text', wordCount: words };
}

const SAMPLE_JOBS: { title: string; subline: string; body: string }[] = [
  {
    title: 'Senior Backend Engineer',
    subline: 'Series B fintech · Remote · $180–220k',
    body:
      'We are looking for a Senior Backend Engineer to build high-throughput payment rails in Python and Rust. 5+ years experience, familiarity with AWS, Postgres, Kafka. Remote-friendly; US/EU time zones. Mission-critical ownership expected. Comp $180k–$220k + equity.',
  },
  {
    title: 'Staff Platform Engineer',
    subline: 'Late-stage health tech · NYC hybrid · $230–270k',
    body:
      'Drive platform architecture across 20+ services. Deep Kubernetes, observability, and reliability engineering. Lead without managing. Hybrid in NYC 2 days/week. 8+ years, prior staff role preferred.',
  },
  {
    title: 'Engineering Manager, Growth',
    subline: 'Public SaaS · Remote · $210–240k',
    body:
      'Lead a 6-person team owning the self-serve signup + onboarding funnel. Partner with product, design, and data. Prior IC background required; we value engineers who still read code. Fully remote in the Americas.',
  },
];

export function JobInputStep({ onSubmit, busy = false, error = null }: Props) {
  const [value, setValue] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const detection = useMemo(() => detect(value), [value]);

  function submit() {
    const trimmed = value.trim();
    if (!trimmed) return;
    const type: 'url' | 'text' = /^https?:\/\//i.test(trimmed) ? 'url' : 'text';
    onSubmit({ type, value: trimmed });
  }

  async function fromClipboard() {
    try {
      const pasted = await navigator.clipboard.readText();
      if (pasted) {
        setValue(pasted);
        textareaRef.current?.focus();
      }
    } catch {
      // Clipboard access may be denied — ignore silently; user can paste manually.
    }
  }

  function useSample(body: string) {
    setValue(body);
    textareaRef.current?.focus();
  }

  let detectorLabel = 'Paste a URL or description to begin';
  let detectorTone = 'text-ink-4';
  if (detection.kind === 'url') {
    detectorLabel =
      "Detected: URL — we'll fetch the job page in the background";
    detectorTone = 'text-ink-2';
  } else if (detection.kind === 'text') {
    detectorLabel = `Detected: Description · ${detection.wordCount.toLocaleString()} words`;
    detectorTone = 'text-ink-2';
  }

  return (
    <div className="grid grid-cols-1 gap-10 lg:grid-cols-12">
      <div className="lg:col-span-7">
        <div className="text-xs uppercase tracking-[0.18em] text-ink-3">
          Pick any role
        </div>
        <h1 className="mt-3 text-[46px] font-semibold leading-[1.02] tracking-[-0.02em] text-ink">
          Paste a job.
          <br />
          See how you{' '}
          <span
            className="bg-clip-text text-transparent"
            style={{
              backgroundImage:
                'linear-gradient(135deg, #14b8a6 0%, #2563eb 45%, #7c3aed 100%)',
            }}
          >
            actually stack up
          </span>
          .
        </h1>
        <p className="mt-4 max-w-md text-[15px] leading-relaxed text-ink-3">
          URL or full description — either works. We read the whole thing,
          including the parts between the lines.
        </p>

        <div className="mt-8 rounded-2xl border border-line-2 bg-white focus-within:border-ink focus-within:ring-4 focus-within:ring-black/5 transition-shadow motion-reduce:transition-none">
          <div className="flex items-center gap-2 border-b border-line px-4 py-2.5">
            <span
              aria-hidden
              className={
                'h-1.5 w-1.5 flex-none rounded-full ' +
                (detection.kind === 'empty' ? 'bg-line-2' : 'bg-accent-teal')
              }
            />
            <span className={`text-[12px] ${detectorTone}`}>
              {detectorLabel}
            </span>
          </div>
          <textarea
            ref={textareaRef}
            value={value}
            onChange={(event) => setValue(event.target.value)}
            rows={5}
            placeholder="https://example.com/jobs/123 — or paste the full job description"
            className="block w-full resize-y border-0 bg-transparent px-4 py-3 text-[15px] leading-relaxed text-ink placeholder:text-ink-4 focus:outline-none"
          />
          <div className="flex items-center justify-between gap-3 border-t border-line px-3 py-2.5">
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => void fromClipboard()}
                className="rounded-full border border-line-2 bg-white px-3 py-1.5 text-[12px] text-ink-2 hover:bg-[#faf9f6]"
              >
                From clipboard
              </button>
              <button
                type="button"
                onClick={() => useSample(SAMPLE_JOBS[0].body)}
                className="rounded-full border border-line-2 bg-white px-3 py-1.5 text-[12px] text-ink-2 hover:bg-[#faf9f6]"
              >
                Try a sample
              </button>
            </div>
            <GradientButton
              disabled={busy || detection.kind === 'empty'}
              onClick={submit}
              shape="pill"
              className="px-5 py-2 text-sm"
            >
              {busy ? 'Evaluating…' : 'Evaluate →'}
            </GradientButton>
          </div>
        </div>

        {error && (
          <p
            role="alert"
            className="mt-4 rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-800"
          >
            {error}
          </p>
        )}

        <div className="mt-10">
          <div className="text-[11px] uppercase tracking-[0.18em] text-ink-4">
            Or try one of these
          </div>
          <ul className="mt-3 space-y-2">
            {SAMPLE_JOBS.map((sample) => (
              <li key={sample.title}>
                <button
                  type="button"
                  onClick={() => useSample(sample.body)}
                  className="group flex w-full items-center justify-between rounded-xl border border-line bg-white px-4 py-3 text-left transition-colors hover:border-ink-2 motion-reduce:transition-none"
                >
                  <div>
                    <div className="text-[14px] font-medium text-ink">
                      {sample.title}
                    </div>
                    <div className="mt-0.5 text-[12px] text-ink-3">
                      {sample.subline}
                    </div>
                  </div>
                  <span className="text-[12px] text-ink-4 group-hover:text-ink-2">
                    Use this →
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </div>
      </div>

      <aside className="lg:col-span-5">
        <div className="rounded-3xl border border-[#ece9e2] bg-white p-6 shadow-[0_1px_0_rgba(31,29,26,0.02),0_24px_48px_-28px_rgba(31,29,26,0.18)]">
          <div className="text-xs uppercase tracking-[0.18em] text-ink-3">
            What we're about to read
          </div>
          <ul className="mt-4 space-y-2 text-[14px] leading-relaxed text-ink-2">
            {[
              'Required experience vs. your seniority',
              'Stack / tooling overlap',
              'Comp range (if listed) vs. your floor',
              'Team shape & scope clues',
              'Red flags: vague scope, churn signals',
            ].map((item) => (
              <li key={item}>
                {item} <span className="text-ink-4">·</span>
              </li>
            ))}
          </ul>
          <div className="my-5 border-t border-line" />
          <p className="text-[12px] text-ink-3">
            The first evaluation usually takes about 40 seconds. You only do
            this onboarding once.
          </p>
        </div>
      </aside>
    </div>
  );
}
