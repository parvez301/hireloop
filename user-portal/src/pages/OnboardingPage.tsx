import { useEffect, useState } from 'react';

import { EvaluationProgressStep } from '../components/onboarding/EvaluationProgressStep';
import { JobInputStep } from '../components/onboarding/JobInputStep';
import { ResumeUploadStep } from '../components/onboarding/ResumeUploadStep';
import { api } from '../lib/api';

type WizardStep = 'loading' | 'resume' | 'job' | 'evaluating' | 'failed-skip';

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

  return (
    <div className="mx-auto flex min-h-screen max-w-2xl flex-col gap-8 px-6 py-16">
      <header>
        <h1 className="text-3xl font-semibold">
          <span className="bg-gradient-to-br from-accent-teal via-accent-cobalt to-accent-violet bg-clip-text text-transparent">
            Let's get you set up
          </span>
        </h1>
        <p className="mt-2 text-text-secondary">
          Less than a minute. We'll turn one job into a full evaluation so you can see what we do.
        </p>
      </header>

      {step === 'loading' && <p className="text-text-secondary">Loading…</p>}
      {step === 'resume' && <ResumeUploadStep onAdvance={() => setStep('job')} />}
      {step === 'job' && (
        <JobInputStep onSubmit={submitJob} busy={evalBusy} error={jobError} />
      )}
      {step === 'evaluating' && <EvaluationProgressStep />}
      {step === 'failed-skip' && (
        <div className="flex flex-col gap-3 rounded-xl border border-border p-6">
          <p>
            Our evaluation service is having a rough moment. You can skip this and
            evaluate jobs from the main app.
          </p>
          <button
            type="button"
            className="self-start text-accent-cobalt hover:underline"
            onClick={skipEvaluation}
          >
            Skip this step →
          </button>
        </div>
      )}
    </div>
  );
}
