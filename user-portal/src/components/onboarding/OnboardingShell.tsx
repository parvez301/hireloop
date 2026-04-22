import type { ReactNode } from 'react';

import { getUserEmail } from '../../lib/auth';

export type OnboardingStepName =
  | 'resume'
  | 'job'
  | 'evaluating'
  | 'confirm'
  | 'payoff';

const STEP_ORDER: OnboardingStepName[] = [
  'resume',
  'job',
  'evaluating',
  'confirm',
  'payoff',
];
const STEP_LABELS: Record<OnboardingStepName, string> = {
  resume: 'RESUME',
  job: 'JOB',
  evaluating: 'EVALUATING',
  confirm: 'CONFIRM',
  payoff: 'RESULT',
};

type Props = {
  activeStep: OnboardingStepName;
  children: ReactNode;
};

export function OnboardingShell({ activeStep, children }: Props) {
  const email = getUserEmail();
  const activeIndex = STEP_ORDER.indexOf(activeStep);
  const label = STEP_LABELS[activeStep];

  return (
    <div className="min-h-screen bg-bg text-ink [font-feature-settings:'ss01','cv11']">
      <header className="sticky top-0 z-20 border-b border-line/70 bg-bg/80 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-8">
          <div className="flex items-center gap-3">
            <span
              aria-hidden
              className="h-6 w-6 rounded-md shadow-[inset_0_1px_0_rgba(255,255,255,0.2)]"
              style={{
                backgroundImage:
                  'linear-gradient(135deg, #14b8a6 0%, #2563eb 45%, #7c3aed 100%)',
              }}
            />
            <span className="text-[15px] font-semibold tracking-tight text-ink">
              HireLoop
            </span>
          </div>
          {email && (
            <span className="text-xs text-ink-3">
              Signed in as <span className="text-ink-2">{email}</span>
            </span>
          )}
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-8 pt-10 pb-24 animate-fade-up motion-reduce:animate-none">
        <nav
          aria-label="Onboarding progress"
          className="mb-10 flex items-center gap-4"
        >
          <ol className="flex items-center gap-2" role="list">
            {STEP_ORDER.map((step, index) => {
              const isActive = index === activeIndex;
              const isDone = index < activeIndex;
              return (
                <li key={step} aria-current={isActive ? 'step' : undefined}>
                  <span
                    className={
                      'block h-1.5 rounded-full transition-all duration-300 ease-out motion-reduce:transition-none ' +
                      (isActive ? 'w-7' : 'w-1.5') +
                      ' ' +
                      (isDone ? 'bg-ink' : isActive ? '' : 'bg-line-2')
                    }
                    style={
                      isActive
                        ? {
                            backgroundImage:
                              'linear-gradient(135deg, #14b8a6 0%, #2563eb 45%, #7c3aed 100%)',
                          }
                        : undefined
                    }
                  />
                </li>
              );
            })}
          </ol>
          <div className="text-[12px] tracking-[0.14em]">
            <span className="text-ink-4">
              STEP {activeIndex + 1} OF {STEP_ORDER.length} ·{' '}
            </span>
            <span className="text-ink-2">{label}</span>
          </div>
        </nav>

        {children}
      </main>
    </div>
  );
}
