import { useEffect, useState } from 'react';

function gradientFor(value: number): string {
  if (value >= 80) return 'linear-gradient(90deg, #14b8a6 0%, #10b981 100%)';
  if (value >= 65) return 'linear-gradient(90deg, #14b8a6 0%, #2563eb 100%)';
  if (value >= 50) return 'linear-gradient(90deg, #2563eb 0%, #7c3aed 100%)';
  if (value >= 35) return 'linear-gradient(90deg, #7c3aed 0%, #a855f7 100%)';
  return 'linear-gradient(90deg, #c2410c 0%, #f59e0b 100%)';
}

type Props = {
  value: number; // 0–100
  label?: string;
  variant?: 'inline' | 'block';
  delayMs?: number;
};

export function GradeBar({ value, label, variant = 'block', delayMs = 150 }: Props) {
  const [width, setWidth] = useState(0);
  useEffect(() => {
    const id = setTimeout(() => setWidth(value), delayMs);
    return () => clearTimeout(id);
  }, [value, delayMs]);

  const gradient = gradientFor(value);

  if (variant === 'inline') {
    return (
      <span className="inline-flex items-center gap-1.5">
        <span className="relative inline-block h-1.5 w-16 overflow-hidden rounded-full bg-[#ece9e2]">
          <span
            className="absolute inset-y-0 left-0 transition-[width] duration-[1100ms] ease-[cubic-bezier(.2,.7,.2,1)] motion-reduce:transition-none"
            style={{ width: `${width}%`, backgroundImage: gradient }}
          />
        </span>
        <span className="text-[12px] tabular-nums text-ink">{value}</span>
      </span>
    );
  }

  return (
    <div>
      {label && (
        <div className="mb-1 flex items-baseline justify-between">
          <span className="text-[12px] text-ink-3">{label}</span>
          <span className="text-[12px] font-semibold tabular-nums text-ink">
            {value}
          </span>
        </div>
      )}
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-[#ece9e2]">
        <div
          className="h-full rounded-full transition-[width] duration-[1100ms] ease-[cubic-bezier(.2,.7,.2,1)] motion-reduce:transition-none"
          style={{ width: `${width}%`, backgroundImage: gradient }}
        />
      </div>
    </div>
  );
}
