import { useEffect, useState } from 'react';

import { EvaluationProgressStep } from '../components/onboarding/EvaluationProgressStep';
import { JobInputStep } from '../components/onboarding/JobInputStep';
import {
  OnboardingShell,
  type OnboardingStepName,
} from '../components/onboarding/OnboardingShell';
import { ResumeUploadStep } from '../components/onboarding/ResumeUploadStep';
import { api } from '../lib/api';

type WizardStep = 'loading' | 'resume' | 'job' | 'evaluating' | 'failed-skip';

function shellStepFor(step: WizardStep): OnboardingStepName {
  if (step === 'resume') return 'resume';
  if (step === 'evaluating') return 'evaluating';
  if (step === 'failed-skip') return 'job';
  return 'job';
}

export default function OnboardingPage() {
  const [step, setStep] = useState<WizardStep>('loading');
  const [jobError, setJobError] = useState<string | null>(null);
  const [evalBusy, setEvalBusy] = useState(false);
  const [failCount, setFailCount] = useState(0);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const { data } = await api.profile.get();
        if (cancelled) return;
        setStep(data.onboarding_state === 'done' ? 'job' : 'resume');
      } catch {
        if (!cancelled) setStep('resume');
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  async function submitJob(input: { type: 'url' | 'text'; value: string }) {
    setEvalBusy(true);
    setJobError(null);
    setStep('evaluating');
    try {
      const response = await api.onboarding.firstEvaluation({ job_input: input });
      const evaluationId = response.data.evaluation.id;
      try {
        sessionStorage.setItem(
          `onboarding-payoff-${evaluationId}`,
          JSON.stringify(response.data),
        );
      } catch {
        // sessionStorage may fail in private mode; payoff page falls back to API fetch.
      }
      window.history.pushState({}, '', `/onboarding/evaluation/${evaluationId}`);
      window.dispatchEvent(new PopStateEvent('popstate'));
    } catch (error) {
      const nextFailCount = failCount + 1;
      setFailCount(nextFailCount);
      setJobError((error as Error).message);
      setStep(nextFailCount >= 3 ? 'failed-skip' : 'job');
    } finally {
      setEvalBusy(false);
    }
  }

  function skipEvaluation() {
    window.location.assign('/');
  }

  if (step === 'loading') {
    return (
      <OnboardingShell activeStep="resume">
        <p className="text-ink-3">Loading…</p>
      </OnboardingShell>
    );
  }

  return (
    <OnboardingShell activeStep={shellStepFor(step)}>
      {step === 'resume' && <ResumeUploadStep onAdvance={() => setStep('job')} />}
      {step === 'job' && (
        <JobInputStep onSubmit={submitJob} busy={evalBusy} error={jobError} />
      )}
      {step === 'evaluating' && <EvaluationProgressStep />}
      {step === 'failed-skip' && (
        <div className="mx-auto flex max-w-xl flex-col gap-3 rounded-2xl border border-line p-6">
          <p className="text-[15px] leading-relaxed text-ink-2">
            Our evaluation service is having a rough moment. You can skip this
            and evaluate jobs from the main app.
          </p>
          <button
            type="button"
            className="self-start text-[13px] text-accent-cobalt underline decoration-dotted underline-offset-4 hover:text-ink-2"
            onClick={skipEvaluation}
          >
            Skip this step →
          </button>
        </div>
      )}
    </OnboardingShell>
  );
}
