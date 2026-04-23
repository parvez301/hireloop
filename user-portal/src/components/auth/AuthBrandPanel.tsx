import { useEffect, useState } from 'react';
import { Check, CircleAlert, X } from 'lucide-react';

import { LIVE_EVAL_CARDS, type LiveEvaluationCard, type MatchRowType } from './ProofCardData';

const ROTATE_MS = 5200;

function tierDot(tier: LiveEvaluationCard['tier']): string {
  if (tier === 'strong') return 'bg-teal';
  if (tier === 'okay') return 'bg-amber';
  return 'bg-[#9a9894]';
}

function matchGlyph(type: MatchRowType) {
  if (type === 'ok')
    return (
      <span className="flex h-4 w-4 flex-none items-center justify-center rounded-full bg-teal/10 text-teal">
        <Check size={11} strokeWidth={2.4} />
      </span>
    );
  if (type === 'warn')
    return (
      <span className="flex h-4 w-4 flex-none items-center justify-center rounded-full bg-amber/10 text-amber">
        <CircleAlert size={11} strokeWidth={2.4} />
      </span>
    );
  return (
    <span className="flex h-4 w-4 flex-none items-center justify-center rounded-full bg-red-100 text-red-600">
      <X size={11} strokeWidth={2.4} />
    </span>
  );
}

function Bar({ value, gradient, delayMs }: { value: number; gradient: string; delayMs: number }) {
  const [width, setWidth] = useState(0);
  useEffect(() => {
    const id = setTimeout(() => setWidth(value), delayMs);
    return () => clearTimeout(id);
  }, [value, delayMs]);
  return (
    <div className="h-1 w-full overflow-hidden rounded-full bg-[#ece9e2]">
      <div
        className="h-full rounded-full transition-[width] duration-[1100ms] ease-[cubic-bezier(.2,.7,.2,1)] motion-reduce:transition-none"
        style={{ width: `${width}%`, backgroundImage: gradient }}
      />
    </div>
  );
}

function EvalCard({ card }: { card: LiveEvaluationCard }) {
  return (
    <div className="animate-fade-up motion-reduce:animate-none rounded-3xl border border-[#ece9e2] bg-white p-6 shadow-[0_1px_0_rgba(31,29,26,0.02),0_24px_48px_-28px_rgba(31,29,26,0.18)]">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-[11px] uppercase tracking-[0.18em] text-ink-3">
            <span className={`h-1.5 w-1.5 rounded-full ${tierDot(card.tier)}`} />
            {card.tierLabel}
          </div>
          <div className="mt-3 text-[16px] font-semibold text-ink">{card.title}</div>
          <div className="mt-0.5 text-[12px] text-ink-3">{card.meta}</div>
        </div>
        <div className="flex items-baseline tabular-nums">
          <span
            className="bg-clip-text text-[44px] font-semibold leading-none tracking-[-0.04em] text-transparent"
            style={{
              backgroundImage:
                'linear-gradient(135deg, #14b8a6 0%, #2563eb 45%, #7c3aed 100%)',
            }}
          >
            {card.score}
          </span>
          <span className="text-[14px] text-ink-3">/100</span>
        </div>
      </div>

      <div className="mt-5 space-y-3">
        {card.bars.map((bar, index) => (
          <div key={bar.label}>
            <div className="flex items-baseline justify-between">
              <span className="text-[12px] text-ink-3">{bar.label}</span>
              <span className="text-[12px] font-semibold tabular-nums text-ink">
                {bar.value}
              </span>
            </div>
            <div className="mt-1">
              <Bar value={bar.value} gradient={bar.gradient} delayMs={200 + index * 100} />
            </div>
          </div>
        ))}
      </div>

      <div className="mt-5 border-t border-line pt-4">
        <div className="text-[11px] uppercase tracking-[0.18em] text-ink-3">
          Matched against your resume
        </div>
        <ul className="mt-3 space-y-2.5 text-[13px] leading-relaxed text-ink-2">
          {card.matches.map((row, index) => (
            <li key={index} className="flex gap-2.5">
              <span className="mt-0.5">{matchGlyph(row.type)}</span>
              <span>
                {row.text}
                <span className="text-ink-4"> · {row.cite}</span>
              </span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

export function AuthBrandPanel() {
  const [activeIndex, setActiveIndex] = useState(0);
  const [paused, setPaused] = useState(false);

  useEffect(() => {
    if (paused) return;
    const id = setInterval(() => {
      setActiveIndex((previous) => (previous + 1) % LIVE_EVAL_CARDS.length);
    }, ROTATE_MS);
    return () => clearInterval(id);
  }, [paused]);

  const card = LIVE_EVAL_CARDS[activeIndex] ?? LIVE_EVAL_CARDS[0];

  return (
    <aside
      className="relative hidden overflow-hidden border-l border-line bg-bg lg:block"
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
      aria-label="Live evaluation preview"
    >
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0"
        style={{
          backgroundImage:
            'radial-gradient(900px 500px at 85% 10%, rgba(37,99,235,0.18), transparent 60%), radial-gradient(600px 400px at 15% 90%, rgba(20,184,166,0.15), transparent 60%), radial-gradient(500px 400px at 65% 85%, rgba(124,58,237,0.14), transparent 60%)',
        }}
      />

      <div className="relative flex h-full flex-col justify-between p-14">
        <div>
          <p className="text-[11px] uppercase tracking-[0.18em] text-ink-3">
            The loop
          </p>
          <h2 className="mt-4 max-w-md text-[44px] font-semibold leading-[1.05] tracking-[-0.02em] text-ink">
            Every job,{' '}
            <span
              className="bg-clip-text text-transparent"
              style={{
                backgroundImage:
                  'linear-gradient(135deg, #14b8a6 0%, #2563eb 45%, #7c3aed 100%)',
              }}
            >
              evaluated
            </span>{' '}
            against the real you.
          </h2>
          <p className="mt-4 max-w-md text-[15px] leading-relaxed text-ink-3">
            Paste any role. Get a grade, a plain-English verdict, and the exact
            watch-outs to raise on the call. No keyword games.
          </p>
        </div>

        <div className="relative max-w-md" key={card.id}>
          <EvalCard card={card} />
          <div className="mt-4 flex items-center justify-between text-[11px] text-ink-4">
            <div className="flex items-center gap-1.5">
              {LIVE_EVAL_CARDS.map((entry, index) => (
                <button
                  key={entry.id}
                  type="button"
                  onClick={() => setActiveIndex(index)}
                  aria-label={`Show card ${index + 1}`}
                  className={
                    'h-1.5 rounded-full transition-all duration-200 motion-reduce:transition-none ' +
                    (index === activeIndex ? 'w-6 bg-ink/70' : 'w-1.5 bg-line-2')
                  }
                />
              ))}
            </div>
            <span className="uppercase tracking-[0.12em]">
              Live evaluation · {activeIndex + 1} / {LIVE_EVAL_CARDS.length}
            </span>
          </div>
        </div>

        <div className="max-w-md">
          <p className="text-[16px] leading-relaxed text-ink-2">
            "I stopped guessing which jobs were worth my time. HireLoop tells me
            in 40 seconds."
          </p>
          <p className="mt-3 text-[12px] text-ink-3">
            — Morgan L., product designer · 3 offers in 5 weeks
          </p>
          <div className="mt-8 flex items-center gap-4 text-[11px] uppercase tracking-[0.16em] text-ink-4">
            <span>SOC&nbsp;2</span>
            <span>·</span>
            <span>GDPR</span>
            <span>·</span>
            <span>Your data, deletable</span>
          </div>
        </div>
      </div>
    </aside>
  );
}
