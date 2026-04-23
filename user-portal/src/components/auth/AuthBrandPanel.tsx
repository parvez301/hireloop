import { useEffect, useState } from 'react';

import { GradientBadge, type Grade } from '../ui/GradientBadge';
import { PROOF_CARDS } from './ProofCardData';

const ROTATE_MS = 4200;

function toBadgeGrade(raw?: string): Grade {
  if (!raw) return 'B+';
  if ((['A', 'A-', 'B+', 'B', 'C'] as const).includes(raw as Grade)) {
    return raw as Grade;
  }
  return 'B+';
}

export function AuthBrandPanel() {
  const [activeIndex, setActiveIndex] = useState(0);
  const [paused, setPaused] = useState(false);

  useEffect(() => {
    if (paused) return;
    const id = setInterval(() => {
      setActiveIndex((previous) => (previous + 1) % PROOF_CARDS.length);
    }, ROTATE_MS);
    return () => clearInterval(id);
  }, [paused]);

  const active = PROOF_CARDS[activeIndex] ?? PROOF_CARDS[0];
  const badgeGrade = toBadgeGrade(active.grade);

  return (
    <aside
      className="relative hidden min-h-screen w-[44%] max-w-[640px] flex-col justify-center gap-10 bg-card px-12 py-16 lg:flex"
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
      aria-label="Customer proof"
    >
      <div
        aria-hidden
        className="pointer-events-none absolute -right-20 -top-20 h-72 w-72 rounded-full opacity-30 blur-3xl"
        style={{
          backgroundImage:
            'radial-gradient(circle at 30% 30%, #14b8a6, transparent 55%), radial-gradient(circle at 70% 40%, #2563eb, transparent 55%), radial-gradient(circle at 50% 80%, #7c3aed, transparent 55%)',
        }}
      />

      <div className="relative">
        <div className="text-[11px] uppercase tracking-[0.18em] text-ink-3">
          What members are saying
        </div>
        <h2 className="mt-3 max-w-md text-[28px] font-semibold leading-tight tracking-[-0.015em] text-ink">
          Grades the jobs you're thinking about. Tells you where to push.
        </h2>
        <ul className="mt-8 space-y-3 text-[14px] leading-relaxed text-ink-2">
          {[
            'Grade every saved job by actual fit to your resume.',
            'Coaches you on the watch-outs before you apply.',
            'Runs daily scans in the background while you sleep.',
          ].map((item, index) => (
            <li key={item} className="flex items-start gap-3">
              <span className="mt-0.5 flex h-5 w-5 flex-none items-center justify-center rounded-md bg-ink text-[11px] font-semibold text-white">
                {index + 1}
              </span>
              {item}
            </li>
          ))}
        </ul>
      </div>

      <div className="relative">
        <div
          key={active.id}
          className="rounded-3xl border border-[#ece9e2] bg-white p-6 shadow-[0_1px_0_rgba(31,29,26,0.02),0_24px_48px_-28px_rgba(31,29,26,0.18)] animate-fade-up motion-reduce:animate-none"
        >
          <p className="text-[15px] leading-relaxed text-ink-2">
            "{active.quote}"
          </p>
          <div className="mt-4 flex items-center gap-3">
            <div
              className="flex h-10 w-10 flex-none items-center justify-center rounded-full text-[12px] font-semibold text-white"
              style={{
                backgroundImage:
                  'linear-gradient(135deg, #14b8a6 0%, #2563eb 45%, #7c3aed 100%)',
              }}
            >
              {active.author
                .split(' ')
                .map((part) => part[0] ?? '')
                .join('')
                .slice(0, 2)
                .toUpperCase()}
            </div>
            <div className="flex-1">
              <div className="text-[13px] font-semibold text-ink">
                {active.author}
              </div>
              <div className="text-[11px] text-ink-3">{active.role}</div>
            </div>
            {active.score !== undefined && (
              <GradientBadge grade={badgeGrade} score={active.score} size="sm" />
            )}
          </div>
        </div>

        <div className="mt-4 flex items-center gap-1.5" aria-hidden>
          {PROOF_CARDS.map((card, index) => (
            <span
              key={card.id}
              className={
                'h-1 rounded-full transition-all duration-200 motion-reduce:transition-none ' +
                (index === activeIndex ? 'w-6 bg-ink' : 'w-1.5 bg-line-2')
              }
            />
          ))}
        </div>
      </div>
    </aside>
  );
}
