import { useEffect, useState } from 'react';

const PROGRESS_STEPS = [
  'Parsing job description',
  'Comparing to your profile',
  'Writing evaluation',
];

export function EvaluationProgressStep() {
  const [activeIndex, setActiveIndex] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setActiveIndex((previous) => Math.min(previous + 1, PROGRESS_STEPS.length - 1));
    }, 20_000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center gap-8">
      <div className="relative h-16 w-16">
        <div className="absolute inset-0 animate-spin rounded-full border-4 border-transparent border-t-accent-cobalt" />
        <div
          className="absolute inset-0 animate-spin rounded-full border-4 border-transparent border-b-accent-violet"
          style={{ animationDuration: '1.2s', animationDirection: 'reverse' }}
        />
      </div>
      <ul className="flex flex-col gap-2">
        {PROGRESS_STEPS.map((label, index) => (
          <li
            key={label}
            data-testid={`progress-step-${index + 1}`}
            className={
              index <= activeIndex
                ? 'text-text-primary font-medium'
                : 'text-text-secondary'
            }
          >
            {index < activeIndex ? '✓' : index === activeIndex ? '→' : '○'} {label}
          </li>
        ))}
      </ul>
    </div>
  );
}
