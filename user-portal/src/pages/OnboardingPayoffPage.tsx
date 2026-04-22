import { useEffect, useState } from 'react';

import { GradientButton } from '../components/ui/GradientButton';
import { GradientBadge, type Grade } from '../components/ui/GradientBadge';
import {
  api,
  type EvaluationDetail,
  type FirstEvaluationResponse,
} from '../lib/api';

type Props = { id: string };

const KNOWN_GRADES: readonly Grade[] = ['A', 'A-', 'B+', 'B', 'C'];

function toBadgeGrade(raw: string): Grade {
  if ((KNOWN_GRADES as readonly string[]).includes(raw)) {
    return raw as Grade;
  }
  if (raw === 'B-' || raw === 'C+' || raw === 'C-') return 'B';
  return 'C';
}

function readHandoff(id: string): FirstEvaluationResponse | null {
  try {
    const raw = sessionStorage.getItem(`onboarding-payoff-${id}`);
    if (!raw) return null;
    return JSON.parse(raw) as FirstEvaluationResponse;
  } catch {
    return null;
  }
}

export default function OnboardingPayoffPage({ id }: Props) {
  const [evaluation, setEvaluation] = useState<EvaluationDetail | null>(null);
  const [jobHeader, setJobHeader] = useState<{
    title: string;
    company: string | null;
    location: string | null;
  } | null>(null);
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState<'cv' | 'prep' | 'save' | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const handoff = readHandoff(id);
    if (handoff) {
      setEvaluation(handoff.evaluation as unknown as EvaluationDetail);
      setJobHeader({
        title: handoff.job.title,
        company: handoff.job.company ?? null,
        location: handoff.job.location ?? null,
      });
      return;
    }
    let cancelled = false;
    api.evaluations
      .get(id)
      .then((response) => {
        if (!cancelled) setEvaluation(response.data);
      })
      .catch((caught) => {
        if (!cancelled) setError((caught as Error).message);
      });
    return () => {
      cancelled = true;
    };
  }, [id]);

  if (error) {
    return (
      <div className="p-8 text-sm text-red-700" role="alert">
        {error}
      </div>
    );
  }

  if (!evaluation) {
    return <p className="p-8 text-text-secondary">Loading…</p>;
  }

  const badgeGrade = toBadgeGrade(evaluation.overall_grade);
  const badgeScore = Math.round(evaluation.match_score * 100);

  async function onTailorCv() {
    if (busy) return;
    setBusy('cv');
    try {
      const conversation = await api.createConversation('Tailor CV');
      await api.sendMessage(
        conversation.data.id,
        `Tailor my CV for job ${evaluation!.job_id}`,
      );
      window.location.assign('/');
    } catch (caught) {
      setError((caught as Error).message);
      setBusy(null);
    }
  }

  async function onPrep() {
    if (busy || !evaluation?.job_id) return;
    setBusy('prep');
    try {
      const response = await api.interviewPreps.create({ job_id: evaluation.job_id });
      window.location.assign(`/interview-prep/${response.data.id}`);
    } catch (caught) {
      setError((caught as Error).message);
      setBusy(null);
    }
  }

  async function onSave() {
    if (busy || !evaluation?.job_id) return;
    setBusy('save');
    try {
      await api.applications.create({
        job_id: evaluation.job_id,
        status: 'saved',
        evaluation_id: evaluation.id,
      });
      setSaved(true);
    } catch (caught) {
      setError((caught as Error).message);
    } finally {
      setBusy(null);
    }
  }

  function onUnlockScanning() {
    window.location.assign('/scans');
  }

  const redFlags = evaluation.red_flags ?? [];

  return (
    <div className="mx-auto max-w-6xl px-6 py-12">
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[2fr_1fr]">
        <section className="rounded-2xl border border-border bg-card p-6 shadow-[0_4px_16px_-8px_rgba(0,0,0,0.08)]">
          <div className="flex items-start justify-between gap-4">
            <div>
              <div className="text-lg font-semibold">
                {jobHeader?.title ?? 'Your evaluation is ready'}
              </div>
              {jobHeader && (
                <div className="text-sm text-text-secondary">
                  {[jobHeader.company, jobHeader.location].filter(Boolean).join(' · ')}
                </div>
              )}
            </div>
            <GradientBadge grade={badgeGrade} score={badgeScore} />
          </div>

          <p className="mt-6 text-sm">{evaluation.reasoning}</p>

          {redFlags.length > 0 && (
            <div className="mt-4">
              <div className="text-xs uppercase tracking-wide text-red-700">
                Watch-outs
              </div>
              <ul className="mt-1 space-y-1 text-sm">
                {redFlags.map((flag, index) => (
                  <li key={index}>⚠ {flag}</li>
                ))}
              </ul>
            </div>
          )}
        </section>

        <aside className="flex flex-col gap-4">
          <div className="text-xs uppercase tracking-wide text-text-secondary">
            What's next?
          </div>
          <GradientButton disabled={busy !== null} onClick={() => void onTailorCv()}>
            Tailor my CV
          </GradientButton>
          <button
            type="button"
            disabled={busy !== null}
            onClick={() => void onPrep()}
            className="rounded-lg border border-border bg-white px-4 py-3 text-left font-medium hover:bg-hover disabled:opacity-50"
          >
            Generate interview prep
          </button>
          <button
            type="button"
            disabled={busy !== null || saved}
            onClick={() => void onSave()}
            className="rounded-lg border border-border bg-white px-4 py-3 text-left font-medium hover:bg-hover disabled:opacity-50"
          >
            {saved ? 'Saved ✓' : 'Save to pipeline'}
          </button>
          <div className="mt-2 border-t border-dashed border-border pt-4">
            <button
              type="button"
              onClick={onUnlockScanning}
              className="w-full rounded-lg bg-[rgba(37,99,235,0.08)] px-4 py-3 text-left"
            >
              <div className="font-semibold text-accent-cobalt">
                🎯 Unlock job scanning
              </div>
              <div className="text-xs text-text-secondary">
                Tell us where you want to work — we'll find more jobs like this.
              </div>
            </button>
          </div>
        </aside>
      </div>
    </div>
  );
}
