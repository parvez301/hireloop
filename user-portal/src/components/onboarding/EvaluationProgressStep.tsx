import { useEffect, useMemo, useState } from 'react';

type Thought = {
  id: string;
  label: string;
  sub?: string;
  chips?: string[];
};

type ProgressRow = {
  key: 'job_fetched' | 'requirements_extracted' | 'matching' | 'written';
  label: string;
};

const PROGRESS_ROWS: ProgressRow[] = [
  { key: 'job_fetched', label: 'Job pulled' },
  { key: 'requirements_extracted', label: 'Requirements extracted' },
  { key: 'matching', label: 'Matching against profile' },
  { key: 'written', label: 'Evaluation written' },
];

// Kept in a constant so tests can import and assert on specific labels.
export const EVALUATING_THOUGHTS: Thought[] = [
  {
    id: 't1',
    label: 'Parsing job description',
    sub: 'Title, seniority, stack, and scope signals',
  },
  {
    id: 't2',
    label: 'Comparing to your profile',
    sub: 'Experience, recent roles, domain overlap',
    chips: ['Python', 'Distributed systems', 'AWS'],
  },
  {
    id: 't3',
    label: 'Writing evaluation',
    sub: 'Balancing signal vs. noise, flagging watch-outs',
  },
];

// Timings: 0.1s / 0.6s / 1.2s per spec (+ a final optional 1.8s reveal if
// a 4th thought ever lands).
const THOUGHT_DELAYS_MS = [100, 600, 1200, 1800];

function useCountUp(target: number) {
  const [value, setValue] = useState(40);
  useEffect(() => {
    const reduced =
      typeof window !== 'undefined' &&
      window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    if (reduced) {
      setValue(target);
      return;
    }
    let current = 40;
    const id = setInterval(() => {
      const step = Math.max(1, Math.min(3, Math.round((target - current) / 10)));
      current = Math.min(target, current + step);
      setValue(current);
      if (current >= target) {
        clearInterval(id);
      }
    }, 220);
    return () => clearInterval(id);
  }, [target]);
  return value;
}

export function EvaluationProgressStep() {
  const [revealed, setRevealed] = useState(0);
  const [progressIndex, setProgressIndex] = useState(0);
  const target = 76;

  useEffect(() => {
    const timers: ReturnType<typeof setTimeout>[] = [];
    EVALUATING_THOUGHTS.forEach((_, index) => {
      timers.push(
        setTimeout(
          () => setRevealed(index + 1),
          THOUGHT_DELAYS_MS[index] ?? 2400,
        ),
      );
    });
    timers.push(setTimeout(() => setProgressIndex(1), 1200));
    timers.push(setTimeout(() => setProgressIndex(2), 3000));
    timers.push(setTimeout(() => setProgressIndex(3), 7000));
    return () => {
      for (const timer of timers) clearTimeout(timer);
    };
  }, []);

  const countedUp = useCountUp(target);
  const runningThoughtIndex =
    revealed > 0 && revealed < EVALUATING_THOUGHTS.length ? revealed - 1 : -1;

  const conicStyle = useMemo(
    () => ({
      background:
        'conic-gradient(from -90deg, #14b8a6 0%, #2563eb 45%, #7c3aed 87%, #ece9e2 87% 100%)',
    }),
    [],
  );

  return (
    <div className="grid grid-cols-1 gap-10 lg:grid-cols-12">
      <div className="lg:col-span-7">
        <div className="text-xs uppercase tracking-[0.18em] text-ink-3">
          Reading · comparing · grading
        </div>
        <h1 className="mt-3 text-[46px] font-semibold leading-[1.02] tracking-[-0.02em] text-ink">
          Working on your{' '}
          <span
            className="bg-clip-text text-transparent"
            style={{
              backgroundImage:
                'linear-gradient(135deg, #14b8a6 0%, #2563eb 45%, #7c3aed 100%)',
            }}
          >
            first read
          </span>
          …
        </h1>

        <ul
          aria-live="polite"
          className="mt-10 space-y-5 text-[15px] leading-relaxed text-ink-2"
        >
          {EVALUATING_THOUGHTS.slice(0, revealed).map((thought, index) => {
            const isRunning = index === runningThoughtIndex;
            return (
              <li
                key={thought.id}
                data-testid={`progress-step-${index + 1}`}
                className={
                  'flex gap-4 animate-thought-in motion-reduce:animate-none ' +
                  (isRunning ? 'opacity-70' : 'opacity-100')
                }
              >
                <span
                  aria-hidden
                  className={
                    'mt-2 block h-1.5 w-1.5 flex-none rounded-full ' +
                    (isRunning
                      ? 'bg-accent-cobalt animate-pulse motion-reduce:animate-none'
                      : 'bg-ink')
                  }
                />
                <div>
                  <div className="text-ink">{thought.label}</div>
                  {thought.sub && (
                    <div className="mt-1 text-[12px] text-ink-4">
                      {thought.sub}
                    </div>
                  )}
                  {thought.chips && thought.chips.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-2">
                      {thought.chips.map((chip) => (
                        <span
                          key={chip}
                          className="rounded-full border border-line bg-white px-2.5 py-0.5 text-[12px] text-ink-2"
                        >
                          {chip}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      </div>

      <aside className="lg:col-span-5">
        <div className="relative overflow-hidden rounded-3xl border border-[#ece9e2] bg-white p-6 shadow-[0_1px_0_rgba(31,29,26,0.02),0_24px_48px_-28px_rgba(31,29,26,0.18)]">
          <div
            aria-hidden
            className="pointer-events-none absolute -right-10 -top-10 h-40 w-40 rounded-full opacity-30 blur-3xl"
            style={{
              backgroundImage:
                'radial-gradient(circle at 30% 30%, #14b8a6, transparent 55%), radial-gradient(circle at 70% 40%, #2563eb, transparent 55%), radial-gradient(circle at 50% 80%, #7c3aed, transparent 55%)',
            }}
          />
          <div className="relative text-[11px] uppercase tracking-[0.18em] text-ink-3">
            Live
          </div>

          <div
            className="relative mx-auto mt-5 flex h-44 w-44 items-center justify-center"
            role="progressbar"
            aria-valuenow={countedUp}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label="Estimated evaluation score"
          >
            <div
              className="absolute inset-0 rounded-full animate-ring-spin motion-reduce:animate-none"
              style={conicStyle}
            />
            <div className="absolute inset-[2px] rounded-full bg-white" />
            <div className="relative flex flex-col items-center">
              <span className="text-[11px] uppercase tracking-[0.18em] text-ink-4">
                Estimated
              </span>
              <span className="mt-1 text-[40px] font-semibold tabular-nums leading-none tracking-[-0.04em] text-ink">
                {countedUp}
              </span>
              <span className="mt-1 text-[11px] text-ink-4">and climbing</span>
            </div>
          </div>

          <ul className="relative mt-6 space-y-2 text-[13px] text-ink-2">
            {PROGRESS_ROWS.map((row, index) => {
              const done = index < progressIndex;
              const running =
                index === progressIndex && progressIndex < PROGRESS_ROWS.length;
              return (
                <li
                  key={row.key}
                  className="flex items-center justify-between"
                  data-testid={`ring-row-${index + 1}`}
                >
                  <span className={done || running ? 'text-ink' : 'text-ink-4'}>
                    {row.label}
                  </span>
                  <span className="text-[12px]">
                    {done ? (
                      <span className="text-ink">✓</span>
                    ) : running ? (
                      <span className="inline-flex items-center gap-1.5 text-accent-teal">
                        <span className="h-1.5 w-1.5 rounded-full bg-accent-teal animate-pulse motion-reduce:animate-none" />
                        running
                      </span>
                    ) : (
                      <span className="text-ink-4">—</span>
                    )}
                  </span>
                </li>
              );
            })}
          </ul>

          <div className="relative my-5 border-t border-line" />
          <p className="relative text-[12px] text-ink-3">
            Evaluations are cached. Re-running this exact job later is free and
            instant.
          </p>
        </div>
      </aside>
    </div>
  );
}
