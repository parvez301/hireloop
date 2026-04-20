import { useEffect, useMemo, useRef, useState } from 'react';
import { signupUrl } from '../lib/config';

type Grade = 'A' | 'A-' | 'B+' | 'B';

type Sample = {
  id: string;
  company: string;
  role: string;
  url: string;
  grade: Grade;
  matchPercent: number;
  summary: string;
  strengths: [string, string, string];
  concern: string;
  dims: { label: string; score: number }[];
};

const SAMPLES: Sample[] = [
  {
    id: 'stripe',
    company: 'Stripe',
    role: 'Senior Platform Engineer',
    url: 'stripe.com/jobs/senior-platform-engineer',
    grade: 'A',
    matchPercent: 92,
    summary: 'Strong match on platform engineering fundamentals. Comp range aligns with senior IC expectations. Remote-friendly.',
    strengths: [
      '8 yrs of backend platform work at similar scale',
      'Comp band $180K–$240K matches your target',
      'Remote-US with flexible hours',
    ],
    concern: 'Light exposure to payments/fintech domain — tailor résumé to emphasize transactional systems.',
    dims: [
      { label: 'Platform fit', score: 94 },
      { label: 'Compensation', score: 91 },
      { label: 'Location', score: 100 },
      { label: 'Domain', score: 72 },
    ],
  },
  {
    id: 'anthropic',
    company: 'Anthropic',
    role: 'Research Engineer, Alignment',
    url: 'anthropic.com/careers/research-engineer',
    grade: 'A-',
    matchPercent: 86,
    summary: 'Solid ML infra background, gap on alignment-specific research. Apply with a tailored résumé emphasizing evaluation pipelines.',
    strengths: [
      'Experience shipping ML systems to production',
      'Python + distributed training overlap',
      'Comp well above your floor',
    ],
    concern: 'No published alignment research — may need a referral to clear the bar.',
    dims: [
      { label: 'ML infra fit', score: 90 },
      { label: 'Research depth', score: 68 },
      { label: 'Compensation', score: 95 },
      { label: 'Location', score: 88 },
    ],
  },
  {
    id: 'linear',
    company: 'Linear',
    role: 'Senior Product Engineer',
    url: 'linear.app/careers/senior-product-engineer',
    grade: 'B+',
    matchPercent: 78,
    summary: 'Product engineering skills match well. Comp is lower than your target — negotiate or pass.',
    strengths: [
      'React + TypeScript front-to-back experience',
      'Small-team, high-ownership environment fits your preferences',
      'Remote-friendly',
    ],
    concern: 'Base comp $160K–$190K is below your $200K floor. Worth a conversation only if equity is strong.',
    dims: [
      { label: 'Product-eng fit', score: 92 },
      { label: 'Compensation', score: 58 },
      { label: 'Team size', score: 88 },
      { label: 'Location', score: 100 },
    ],
  },
];

type Stage = 'idle' | 'reading' | 'matching' | 'scoring' | 'done';

const STAGE_LABELS: Record<Exclude<Stage, 'idle'>, string> = {
  reading: 'Reading the job description…',
  matching: 'Matching against your profile…',
  scoring: 'Scoring 4 dimensions…',
  done: 'Graded.',
};

const STAGE_ORDER: Exclude<Stage, 'idle'>[] = ['reading', 'matching', 'scoring', 'done'];

const GRADE_COLORS: Record<Grade, string> = {
  A: 'from-[#14b8a6] to-[#22c55e]',
  'A-': 'from-[#14b8a6] to-[#2563eb]',
  'B+': 'from-[#2563eb] to-[#7c3aed]',
  B: 'from-[#7c3aed] to-[#a855f7]',
};

function usePrefersReducedMotion(): boolean {
  const [reduced, setReduced] = useState(false);
  useEffect(() => {
    if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return;
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)');
    setReduced(mq.matches);
    const handler = (e: MediaQueryListEvent) => setReduced(e.matches);
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
  }, []);
  return reduced;
}

export function LiveDemo() {
  const [selectedId, setSelectedId] = useState<string>(SAMPLES[0].id);
  const [customUrl, setCustomUrl] = useState('');
  const [mode, setMode] = useState<'sample' | 'custom'>('sample');
  const [stage, setStage] = useState<Stage>('idle');
  const [elapsed, setElapsed] = useState(0);
  const timers = useRef<number[]>([]);
  const tickerRef = useRef<number | null>(null);
  const reducedMotion = usePrefersReducedMotion();

  const selected = useMemo(
    () => SAMPLES.find((s) => s.id === selectedId) ?? SAMPLES[0],
    [selectedId],
  );

  useEffect(
    () => () => {
      timers.current.forEach(clearTimeout);
      if (tickerRef.current !== null) clearInterval(tickerRef.current);
    },
    [],
  );

  const startGrading = () => {
    timers.current.forEach(clearTimeout);
    if (tickerRef.current !== null) clearInterval(tickerRef.current);
    setElapsed(0);
    setStage('reading');

    const base = reducedMotion ? 80 : 1;
    const schedule: [Stage, number][] = [
      ['matching', 1800 * base],
      ['scoring', 4200 * base],
      ['done', 7400 * base],
    ];
    timers.current = schedule.map(([s, delay]) =>
      window.setTimeout(() => setStage(s), delay),
    );

    const startedAt = performance.now();
    tickerRef.current = window.setInterval(() => {
      setElapsed((performance.now() - startedAt) / 1000);
    }, 80);
    timers.current.push(
      window.setTimeout(() => {
        if (tickerRef.current !== null) clearInterval(tickerRef.current);
      }, 8000 * base),
    );
  };

  const reset = () => {
    timers.current.forEach(clearTimeout);
    if (tickerRef.current !== null) clearInterval(tickerRef.current);
    setStage('idle');
    setElapsed(0);
  };

  const isCustom = mode === 'custom';
  const displayUrl = isCustom ? customUrl : selected.url;
  const canGrade = stage === 'idle' && (isCustom ? customUrl.trim().length > 4 : true);
  const currentStageIndex = stage === 'idle' ? -1 : STAGE_ORDER.indexOf(stage);

  return (
    <section className="relative overflow-hidden border-b border-border bg-bg py-20 md:py-28" id="demo">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 -z-10 bg-[radial-gradient(ellipse_at_top,rgba(20,184,166,0.08),transparent_55%),radial-gradient(ellipse_at_bottom,rgba(124,58,237,0.08),transparent_55%)]"
      />
      <div className="mx-auto max-w-5xl px-6">
        <div className="text-center">
          <p className="inline-flex items-center gap-2 rounded-full border border-border bg-bg px-3 py-1 text-xs font-medium uppercase tracking-wider text-text-secondary">
            <span className="h-1.5 w-1.5 rounded-full bg-accent" aria-hidden />
            Try it
          </p>
          <h2 className="mt-5 text-4xl font-black tracking-tight md:text-5xl">
            Grade a job in{' '}
            <span className="bg-gradient-to-br from-[#14b8a6] via-[#2563eb] to-[#7c3aed] bg-clip-text text-transparent">
              under 10 seconds.
            </span>
          </h2>
          <p className="mx-auto mt-4 max-w-2xl text-lg text-text-secondary">
            Pick a real opening below, or paste your own URL. Watch HireLoop parse, match, and score it in real time.
          </p>
        </div>

        <div className="relative mt-12 overflow-hidden rounded-3xl border border-border bg-card shadow-[0_30px_80px_-30px_rgba(37,99,235,0.35)]">
          <div className="flex flex-wrap gap-2 border-b border-border bg-sidebar px-4 py-3 md:px-6">
            {SAMPLES.map((s) => (
              <button
                key={s.id}
                type="button"
                onClick={() => {
                  setMode('sample');
                  setSelectedId(s.id);
                  reset();
                }}
                className={`rounded-full border px-3 py-1.5 text-xs font-semibold transition-colors ${
                  mode === 'sample' && selectedId === s.id
                    ? 'border-[#2563eb] bg-white text-[#2563eb]'
                    : 'border-border bg-white text-text-secondary hover:border-[#2563eb]/60 hover:text-text-primary'
                }`}
              >
                {s.company} · {s.role}
              </button>
            ))}
            <button
              type="button"
              onClick={() => {
                setMode('custom');
                reset();
              }}
              className={`rounded-full border px-3 py-1.5 text-xs font-semibold transition-colors ${
                mode === 'custom'
                  ? 'border-[#7c3aed] bg-white text-[#7c3aed]'
                  : 'border-border bg-white text-text-secondary hover:border-[#7c3aed]/60 hover:text-text-primary'
              }`}
            >
              + Try your own URL
            </button>
          </div>

          <div className="grid gap-6 p-6 md:grid-cols-[1fr,1fr] md:p-8 lg:gap-10">
            <div>
              <label className="text-xs font-bold uppercase tracking-wider text-text-secondary">
                Job URL
              </label>
              <div className="mt-2 flex overflow-hidden rounded-xl border border-border bg-white">
                <span className="inline-flex items-center border-r border-border bg-sidebar px-3 text-sm text-text-secondary">
                  https://
                </span>
                <input
                  type="text"
                  value={displayUrl}
                  onChange={(e) => {
                    if (isCustom) setCustomUrl(e.target.value);
                  }}
                  readOnly={!isCustom}
                  placeholder={isCustom ? 'company.com/careers/senior-role' : ''}
                  className="flex-1 bg-transparent px-3 py-3 text-sm text-text-primary outline-none placeholder:text-text-secondary/60"
                />
              </div>

              <button
                type="button"
                onClick={startGrading}
                disabled={!canGrade}
                className="mt-4 inline-flex w-full items-center justify-center gap-2 rounded-full bg-gradient-to-r from-[#14b8a6] via-[#2563eb] to-[#7c3aed] px-6 py-3 text-base font-semibold text-white shadow-[0_10px_30px_-10px_rgba(37,99,235,0.5)] transition-all hover:-translate-y-0.5 hover:shadow-[0_18px_45px_-12px_rgba(124,58,237,0.7)] disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:translate-y-0"
              >
                {stage === 'idle' ? 'Grade it →' : stage === 'done' ? 'Grade another' : `Grading… ${elapsed.toFixed(1)}s`}
                {stage === 'done' && (
                  <span onClick={(e) => { e.stopPropagation(); reset(); }} aria-hidden />
                )}
              </button>

              <ul className="mt-6 space-y-3">
                {STAGE_ORDER.map((s, i) => {
                  const isActive = currentStageIndex === i && stage !== 'done';
                  const isDone = currentStageIndex > i || stage === 'done';
                  return (
                    <li key={s} className="flex items-center gap-3 text-sm">
                      <span
                        className={`inline-flex h-5 w-5 items-center justify-center rounded-full border transition-colors ${
                          isDone
                            ? 'border-[#2563eb] bg-[#2563eb] text-white'
                            : isActive
                            ? 'border-[#2563eb] bg-white text-[#2563eb]'
                            : 'border-border bg-white text-text-secondary'
                        }`}
                      >
                        {isDone ? (
                          <svg viewBox="0 0 16 16" className="h-3 w-3" fill="none" stroke="currentColor" strokeWidth={3} strokeLinecap="round" strokeLinejoin="round">
                            <polyline points="3 8 7 12 13 4" />
                          </svg>
                        ) : isActive ? (
                          <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-[#2563eb]" />
                        ) : null}
                      </span>
                      <span className={isDone || isActive ? 'text-text-primary' : 'text-text-secondary'}>
                        {STAGE_LABELS[s]}
                      </span>
                    </li>
                  );
                })}
              </ul>
            </div>

            <div className="relative min-h-[320px] rounded-2xl border border-dashed border-border bg-sidebar p-6">
              {stage !== 'done' && !isCustom && (
                <div className="flex h-full items-center justify-center text-center text-sm text-text-secondary">
                  {stage === 'idle'
                    ? 'Click "Grade it" to run a live grading on this opening.'
                    : 'Generating grade card…'}
                </div>
              )}
              {stage !== 'done' && isCustom && (
                <div className="flex h-full items-center justify-center text-center text-sm text-text-secondary">
                  {stage === 'idle'
                    ? 'Paste a job URL and click "Grade it".'
                    : 'Parsing your URL…'}
                </div>
              )}
              {stage === 'done' && isCustom && (
                <div className="flex h-full flex-col items-center justify-center gap-4 text-center">
                  <span className="text-sm font-semibold text-text-primary">Ready to grade this one for real?</span>
                  <p className="text-sm text-text-secondary">
                    Grading your URL against <em>your</em> experience takes a résumé on file. Sign up in 30 seconds and HireLoop will score this job in under 10.
                  </p>
                  <a
                    href={signupUrl()}
                    className="inline-flex items-center justify-center rounded-full bg-gradient-to-r from-[#14b8a6] via-[#2563eb] to-[#7c3aed] px-5 py-2.5 text-sm font-semibold text-white shadow-[0_10px_30px_-10px_rgba(37,99,235,0.5)] transition-all hover:-translate-y-0.5"
                  >
                    Grade this job free →
                  </a>
                </div>
              )}
              {stage === 'done' && !isCustom && (
                <div className="flex flex-col gap-4">
                  <div className="flex items-start gap-4">
                    <div className={`flex h-16 w-16 flex-none items-center justify-center rounded-2xl bg-gradient-to-br ${GRADE_COLORS[selected.grade]} text-2xl font-black text-white shadow-[0_12px_28px_-10px_rgba(37,99,235,0.6)]`}>
                      {selected.grade}
                    </div>
                    <div className="flex-1">
                      <div className="flex items-baseline gap-2">
                        <span className="text-sm font-semibold text-text-primary">{selected.role}</span>
                        <span className="text-xs text-text-secondary">· {selected.company}</span>
                      </div>
                      <div className="mt-1 text-sm font-semibold text-[#2563eb]">{selected.matchPercent}% match</div>
                      <p className="mt-2 text-sm text-text-secondary leading-relaxed">{selected.summary}</p>
                    </div>
                  </div>
                  <div>
                    <p className="text-[11px] font-bold uppercase tracking-wider text-text-secondary">Why this fits</p>
                    <ul className="mt-2 space-y-1.5">
                      {selected.strengths.map((s) => (
                        <li key={s} className="flex gap-2 text-sm text-text-primary">
                          <span className="mt-1 inline-block h-1.5 w-1.5 flex-none rounded-full bg-emerald-500" />
                          <span>{s}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <p className="text-[11px] font-bold uppercase tracking-wider text-text-secondary">One thing to tailor</p>
                    <p className="mt-1 text-sm text-text-primary">{selected.concern}</p>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    {selected.dims.map((d) => (
                      <div key={d.label}>
                        <div className="flex items-baseline justify-between">
                          <span className="text-[11px] font-semibold text-text-secondary">{d.label}</span>
                          <span className="text-[11px] font-bold text-text-primary">{d.score}</span>
                        </div>
                        <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-border/60">
                          <div
                            className="h-full rounded-full bg-gradient-to-r from-[#14b8a6] via-[#2563eb] to-[#7c3aed] transition-[width] duration-700 ease-out"
                            style={{ width: `${d.score}%` }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        <p className="mt-6 text-center text-xs text-text-secondary">
          Demo uses sample profiles. Your real grades are scored against your résumé — upload it and the first 10-second grade is free.
        </p>
      </div>
    </section>
  );
}
