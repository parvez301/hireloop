import { useEffect, useState } from 'react';

type Props = {
  target: number;
  size?: number;
  eyebrow?: string;
  subline?: string;
  animate?: boolean;
};

export function ScoreRing({
  target,
  size = 176,
  eyebrow = 'ESTIMATED',
  subline,
  animate = true,
}: Props) {
  const [value, setValue] = useState(animate ? 40 : target);

  useEffect(() => {
    if (!animate) return;
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
      if (current >= target) clearInterval(id);
    }, 60);
    return () => clearInterval(id);
  }, [target, animate]);

  const px = size;
  const conic = {
    background:
      'conic-gradient(from -90deg, #14b8a6 0%, #2563eb 45%, #7c3aed 87%, #ece9e2 87% 100%)',
  };

  return (
    <div
      className="relative flex items-center justify-center"
      style={{ width: px, height: px }}
      role="progressbar"
      aria-valuenow={value}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-label="Score"
    >
      <div
        className="absolute inset-0 rounded-full animate-ring-spin motion-reduce:animate-none"
        style={conic}
      />
      <div className="absolute inset-[2px] rounded-full bg-white" />
      <div className="relative flex flex-col items-center">
        <span className="text-[11px] uppercase tracking-[0.18em] text-ink-4">
          {eyebrow}
        </span>
        <span className="mt-1 text-[40px] font-semibold tabular-nums leading-none tracking-[-0.04em] text-ink">
          {value}
        </span>
        {subline && <span className="mt-1 text-[11px] text-ink-4">{subline}</span>}
      </div>
    </div>
  );
}
