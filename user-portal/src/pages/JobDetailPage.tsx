import { useEffect, useMemo, useState } from 'react';
import { ArrowLeft } from 'lucide-react';

import { GradeBar } from '../components/ui/GradeBar';
import { GradientButton } from '../components/ui/GradientButton';
import { ScoreRing } from '../components/ui/ScoreRing';
import { SoftCard } from '../components/ui/SoftCard';
import { WorkspaceShell } from '../components/workspace/WorkspaceShell';
import { api, type JobDetailResponse } from '../lib/api';

type Props = { id: string };

function safeSalary(min: number | null, max: number | null): string | null {
  if (min && max) return `$${(min / 1000).toFixed(0)}k – $${(max / 1000).toFixed(0)}k`;
  if (min) return `$${(min / 1000).toFixed(0)}k+`;
  if (max) return `up to $${(max / 1000).toFixed(0)}k`;
  return null;
}

export default function JobDetailPage({ id }: Props) {
  const [data, setData] = useState<JobDetailResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    let cancelled = false;
    api.jobs
      .get(id)
      .then((response) => {
        if (!cancelled) setData(response.data);
      })
      .catch((caught: Error) => {
        if (!cancelled) setError(caught.message);
      });
    return () => {
      cancelled = true;
    };
  }, [id]);

  const match = useMemo(() => {
    if (!data?.evaluation) return null;
    return Math.round(data.evaluation.match_score * 100);
  }, [data]);

  if (error) {
    return (
      <WorkspaceShell>
        <div role="alert" className="text-sm text-red-700">
          {error}
        </div>
      </WorkspaceShell>
    );
  }

  if (!data) {
    return (
      <WorkspaceShell>
        <p className="text-ink-3">Loading job…</p>
      </WorkspaceShell>
    );
  }

  const { job, evaluation } = data;
  const salary = safeSalary(job.salary_min, job.salary_max);

  async function savePipeline() {
    if (saving) return;
    setSaving(true);
    try {
      await api.applications.create({
        job_id: job.id,
        status: 'saved',
        evaluation_id: evaluation?.id,
      });
      window.location.assign('/pipeline');
    } catch (caught) {
      setError((caught as Error).message);
      setSaving(false);
    }
  }

  return (
    <WorkspaceShell>
      <div className="mx-auto max-w-5xl space-y-6">
        <a
          href="/scans"
          className="inline-flex items-center gap-1.5 text-[13px] text-ink-3 hover:text-ink"
        >
          <ArrowLeft size={14} /> Back
        </a>

        <SoftCard padding="lg" className="relative overflow-hidden">
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
              <div className="text-[11px] uppercase tracking-[0.18em] text-ink-3">
                {job.title}
              </div>
              <div className="mt-1 text-[22px] font-semibold text-ink">
                {job.company ?? 'Company'}{' '}
                <span className="font-normal text-ink-3">
                  · {job.location ?? '—'}
                </span>
              </div>
              {salary && (
                <div className="mt-2 text-[13px] text-ink-3">{salary}</div>
              )}
              {evaluation && match !== null && (
                <div className="mt-6 flex items-center gap-5">
                  <ScoreRing target={match} size={120} animate />
                  <div>
                    <div className="text-[11px] uppercase tracking-[0.18em] text-ink-4">
                      Grade
                    </div>
                    <div className="mt-1 text-[40px] font-semibold tabular-nums leading-none tracking-[-0.04em] text-ink">
                      {evaluation.overall_grade}
                    </div>
                  </div>
                </div>
              )}
            </div>

            <div className="md:col-span-8">
              {evaluation ? (
                <p className="text-[15px] leading-relaxed text-ink-2">
                  {evaluation.reasoning}
                </p>
              ) : (
                <p className="text-[13px] text-ink-3">
                  No evaluation yet for this job. Paste it into the onboarding
                  wizard to grade it.
                </p>
              )}
              {evaluation && evaluation.red_flags && evaluation.red_flags.length > 0 && (
                <div className="mt-6">
                  <div className="text-[11px] uppercase tracking-[0.18em] text-ink-3">
                    Watch-outs
                  </div>
                  <ul className="mt-2 space-y-2 text-[14px] text-ink-2">
                    {evaluation.red_flags.map((flag, index) => (
                      <li
                        key={index}
                        className="rounded-xl border border-line bg-white px-3 py-2"
                      >
                        ⚠ {flag}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              <div className="mt-6 flex flex-wrap items-center gap-3">
                {job.url && (
                  <a
                    href={job.url}
                    target="_blank"
                    rel="noreferrer"
                    className="rounded-full border border-line-2 bg-white px-4 py-2 text-[13px] text-ink-2 hover:bg-[#faf9f6]"
                  >
                    Open job posting ↗
                  </a>
                )}
                <GradientButton disabled={saving} onClick={() => void savePipeline()}>
                  {saving ? 'Saving…' : 'Save to pipeline'}
                </GradientButton>
              </div>
            </div>
          </div>

          {evaluation && (
            <div className="relative mt-8 border-t border-line pt-6">
              <div className="text-[11px] uppercase tracking-[0.18em] text-ink-3">
                Grade breakdown
              </div>
              <div className="mt-3 grid grid-cols-1 gap-4 md:grid-cols-3">
                {Object.entries(evaluation.dimension_scores ?? {})
                  .slice(0, 6)
                  .map(([key, value]) => {
                    const score = typeof value === 'object' && value !== null && 'score' in value
                      ? Math.round(Number((value as { score: number }).score) * 100)
                      : 0;
                    return (
                      <GradeBar
                        key={key}
                        label={key.replace(/_/g, ' ')}
                        value={score}
                      />
                    );
                  })}
              </div>
            </div>
          )}
        </SoftCard>

        <SoftCard header="Full job description" padding="lg">
          <div className="max-w-[640px] whitespace-pre-wrap text-[14px] leading-relaxed text-ink-2">
            {job.description_md}
          </div>
        </SoftCard>
      </div>
    </WorkspaceShell>
  );
}
