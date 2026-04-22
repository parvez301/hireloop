import { useEffect, useState } from 'react';

import { OnboardingShell } from '../components/onboarding/OnboardingShell';
import { GradientButton } from '../components/ui/GradientButton';
import {
  api,
  type EvaluationDetail,
  type FirstEvaluationResponse,
} from '../lib/api';

type Props = { id: string };

type MatchLabel = 'Strong match' | 'Solid match' | 'Reach';

function matchLabelFor(grade: string): MatchLabel {
  if (grade === 'A' || grade === 'A-') return 'Strong match';
  if (grade === 'B+' || grade === 'B') return 'Solid match';
  return 'Reach';
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

// Pull three proxy sub-scores out of existing dimension_scores. If the
// backend later returns explicit experience/scope/requirements scores, the
// UI will pick them up automatically.
function deriveSubScores(evaluation: EvaluationDetail): {
  experience: number;
  scope: number;
  requirements: number;
} {
  const dimensions = evaluation.dimension_scores ?? {};
  function pick(key: string, fallback: number): number {
    const dim = dimensions[key as keyof typeof dimensions];
    const raw = (dim as { score?: number } | undefined)?.score;
    if (typeof raw === 'number') {
      return Math.round(raw * 100);
    }
    return fallback;
  }
  const base = Math.round(evaluation.match_score * 100);
  return {
    experience: pick('experience_fit', base),
    scope: pick('role_match', Math.max(40, base - 10)),
    requirements: pick('skills_match', Math.max(40, base - 5)),
  };
}

function AnimatedBar({
  value,
  gradient,
  delayMs,
}: {
  value: number;
  gradient: string;
  delayMs: number;
}) {
  const [width, setWidth] = useState(0);
  useEffect(() => {
    const timer = setTimeout(() => setWidth(value), delayMs);
    return () => clearTimeout(timer);
  }, [value, delayMs]);
  return (
    <div className="h-1.5 w-full overflow-hidden rounded-full bg-[#ece9e2]">
      <div
        className="h-full rounded-full transition-[width] duration-[1100ms] ease-[cubic-bezier(.2,.7,.2,1)] motion-reduce:transition-none"
        style={{ width: `${width}%`, backgroundImage: gradient }}
      />
    </div>
  );
}

function HeroCard({
  evaluation,
  jobHeader,
  subScores,
  countedScore,
}: {
  evaluation: EvaluationDetail;
  jobHeader: {
    title: string;
    company: string | null;
    location: string | null;
  } | null;
  subScores: ReturnType<typeof deriveSubScores>;
  countedScore: number;
}) {
  const matchLabel = matchLabelFor(evaluation.overall_grade);
  const grade = evaluation.overall_grade;
  return (
    <section className="relative overflow-hidden rounded-[24px] border border-line bg-white p-8 shadow-[0_1px_0_rgba(31,29,26,0.02),0_24px_48px_-28px_rgba(31,29,26,0.18)]">
      <div
        aria-hidden
        className="pointer-events-none absolute -right-16 -top-16 h-56 w-56 rounded-full opacity-30 blur-3xl"
        style={{
          backgroundImage:
            'radial-gradient(circle at 30% 30%, #14b8a6, transparent 55%), radial-gradient(circle at 70% 40%, #2563eb, transparent 55%), radial-gradient(circle at 50% 80%, #7c3aed, transparent 55%)',
        }}
      />

      <div className="relative grid grid-cols-1 gap-8 md:grid-cols-12">
        <div className="md:col-span-4">
          <div className="flex items-center gap-2 text-[11px] uppercase tracking-[0.18em] text-accent-teal">
            <span className="h-1.5 w-1.5 rounded-full bg-accent-teal" />
            {matchLabel}
          </div>
          <div className="mt-4 flex items-baseline gap-2">
            <span
              className="bg-clip-text text-[112px] font-semibold leading-none tabular-nums tracking-[-0.05em] text-transparent"
              style={{
                backgroundImage:
                  'linear-gradient(135deg, #14b8a6 0%, #2563eb 45%, #7c3aed 100%)',
              }}
            >
              {countedScore}
            </span>
            <span className="text-[24px] font-medium text-ink-3">/100</span>
          </div>
          <div className="mt-4 inline-flex items-center gap-2 rounded-full bg-card px-3 py-1 text-[12px] text-ink-2">
            <span
              aria-hidden
              className="h-1.5 w-1.5 rounded-full"
              style={{
                backgroundImage:
                  'linear-gradient(135deg, #14b8a6 0%, #2563eb 45%, #7c3aed 100%)',
              }}
            />
            Grade {grade} · first evaluation
          </div>
        </div>

        <div className="md:col-span-8">
          {jobHeader && (
            <>
              <div className="text-[11px] uppercase tracking-[0.18em] text-ink-4">
                {jobHeader.title}
              </div>
              <div className="mt-1 text-[22px] font-semibold text-ink">
                {jobHeader.company ?? 'Company'}{' '}
                <span className="font-normal text-ink-3">
                  · {jobHeader.location ?? 'Location not specified'}
                </span>
              </div>
            </>
          )}
          <p className="mt-4 max-w-2xl text-[16px] leading-relaxed text-ink-2">
            {evaluation.reasoning}
          </p>
        </div>
      </div>

      <div className="relative mt-8 border-t border-line pt-6">
        <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
          {[
            {
              label: 'Experience match',
              value: subScores.experience,
              gradient:
                'linear-gradient(90deg, #14b8a6 0%, #10b981 100%)',
              delay: 150,
            },
            {
              label: 'Scope & seniority',
              value: subScores.scope,
              gradient:
                'linear-gradient(90deg, #2563eb 0%, #7c3aed 100%)',
              delay: 250,
            },
            {
              label: 'Specific requirements',
              value: subScores.requirements,
              gradient:
                'linear-gradient(90deg, #c2410c 0%, #f59e0b 100%)',
              delay: 350,
            },
          ].map((bar) => (
            <div key={bar.label}>
              <div className="flex items-baseline justify-between">
                <span className="text-[13px] text-ink-3">{bar.label}</span>
                <span className="text-[13px] font-bold tabular-nums text-ink">
                  {bar.value}
                </span>
              </div>
              <div className="mt-2">
                <AnimatedBar
                  value={bar.value}
                  gradient={bar.gradient}
                  delayMs={bar.delay}
                />
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
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
  const [countedScore, setCountedScore] = useState(0);

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

  useEffect(() => {
    if (!evaluation) return;
    const target = Math.round(evaluation.match_score * 100);
    const reduced =
      typeof window !== 'undefined' &&
      window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    if (reduced) {
      setCountedScore(target);
      return;
    }
    let current = 0;
    const id = setInterval(() => {
      const step = Math.max(1, Math.min(4, Math.round((target - current) / 10)));
      current = Math.min(target, current + step);
      setCountedScore(current);
      if (current >= target) clearInterval(id);
    }, 40);
    return () => clearInterval(id);
  }, [evaluation]);

  if (error) {
    return (
      <OnboardingShell activeStep="payoff">
        <div className="p-8 text-sm text-red-700" role="alert">
          {error}
        </div>
      </OnboardingShell>
    );
  }

  if (!evaluation) {
    return (
      <OnboardingShell activeStep="payoff">
        <p className="p-8 text-text-secondary">Loading…</p>
      </OnboardingShell>
    );
  }

  const subScores = deriveSubScores(evaluation);
  const redFlags = evaluation.red_flags ?? [];
  const watchOuts = redFlags.length > 0 ? redFlags : [];

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

  return (
    <OnboardingShell activeStep="payoff">
      <HeroCard
        evaluation={evaluation}
        jobHeader={jobHeader}
        subScores={subScores}
        countedScore={countedScore}
      />

      <div className="mt-8 grid grid-cols-1 gap-8 lg:grid-cols-12">
        <section className="lg:col-span-7">
          <div className="flex items-baseline justify-between">
            <div className="text-[11px] uppercase tracking-[0.18em] text-ink-3">
              Watch-outs · {watchOuts.length}
            </div>
            <div className="text-[12px] text-ink-4">
              Things to address before you apply
            </div>
          </div>
          {watchOuts.length === 0 ? (
            <p className="mt-4 rounded-2xl border border-dashed border-line-2 p-6 text-[13px] text-ink-3">
              Nothing the evaluator flagged on this pass.
            </p>
          ) : (
            <ul className="mt-4 space-y-3">
              {watchOuts.map((flag, index) => (
                <li
                  key={index}
                  className="flex gap-4 rounded-2xl border border-line bg-white p-5"
                >
                  <span className="flex h-6 w-6 flex-none items-center justify-center rounded-full border border-amber/30 bg-amber/10 text-[11px] font-semibold text-amber">
                    {index + 1}
                  </span>
                  <div>
                    <div className="text-[15px] font-medium text-ink">
                      {flag}
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>

        <aside className="lg:col-span-5">
          <div className="text-[11px] uppercase tracking-[0.18em] text-ink-3">
            What's next
          </div>
          <div className="mt-4 flex flex-col gap-3">
            <GradientButton
              disabled={busy !== null}
              onClick={() => void onTailorCv()}
              shape="card"
              className="w-full justify-between px-5 py-4 text-left text-base"
            >
              <span className="flex flex-col items-start">
                <span>Tailor my CV for this role</span>
                <span className="text-[12px] font-normal text-white/80">
                  Rewrite 3 bullets · 45 seconds
                </span>
              </span>
              <span aria-hidden className="text-xl">→</span>
            </GradientButton>

            <button
              type="button"
              disabled={busy !== null}
              onClick={() => void onPrep()}
              className="flex w-full items-center justify-between rounded-2xl border border-line-2 bg-white px-5 py-4 text-left hover:bg-[#faf9f6] disabled:opacity-50 motion-reduce:transition-none"
            >
              <span className="flex flex-col">
                <span className="text-[15px] font-medium text-ink">
                  Generate interview prep
                </span>
                <span className="text-[12px] text-ink-3">
                  Likely questions + your story bank
                </span>
              </span>
              <span aria-hidden className="text-ink-3">→</span>
            </button>

            <button
              type="button"
              disabled={busy !== null || saved}
              onClick={() => void onSave()}
              className="flex w-full items-center justify-between rounded-2xl border border-line-2 bg-white px-5 py-4 text-left hover:bg-[#faf9f6] disabled:opacity-50 motion-reduce:transition-none"
            >
              <span className="flex flex-col">
                <span className="text-[15px] font-medium text-ink">
                  {saved ? 'Saved ✓' : 'Save to pipeline'}
                </span>
                <span className="text-[12px] text-ink-3">
                  Track it without applying yet
                </span>
              </span>
              <span aria-hidden className="text-ink-3">
                {saved ? '✓' : '+'}
              </span>
            </button>
          </div>

          <div className="mt-6 rounded-2xl border border-dashed border-line-2 p-5">
            <div className="flex items-center gap-2">
              <span
                aria-hidden
                className="h-1.5 w-1.5 rounded-full"
                style={{
                  backgroundImage:
                    'linear-gradient(135deg, #14b8a6 0%, #2563eb 45%, #7c3aed 100%)',
                }}
              />
              <div className="text-[13px] font-medium text-ink-2">
                Find more like this
              </div>
            </div>
            <div className="mt-1 text-[12px] text-ink-3">
              Tell us where you want to work and we'll scan boards for similar
              roles.
            </div>
            <button
              type="button"
              onClick={onUnlockScanning}
              className="mt-3 text-[12px] text-accent-cobalt underline decoration-dotted underline-offset-4 hover:text-ink-2"
            >
              Unlock job scanning →
            </button>
          </div>
        </aside>
      </div>
    </OnboardingShell>
  );
}
