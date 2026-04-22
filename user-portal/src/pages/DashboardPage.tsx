import { useEffect, useState } from 'react';
import { Briefcase, Sparkles, TrendingUp } from 'lucide-react';

import { EmptyState } from '../components/ui/EmptyState';
import { GradeBar } from '../components/ui/GradeBar';
import { GradientButton } from '../components/ui/GradientButton';
import { SoftCard } from '../components/ui/SoftCard';
import { Sparkline } from '../components/ui/Sparkline';
import { WorkspaceShell } from '../components/workspace/WorkspaceShell';
import { api, type BriefingData } from '../lib/api';
import { getUserEmail } from '../lib/auth';

function firstName(email: string | null): string {
  if (!email) return 'there';
  const local = email.split('@')[0] ?? '';
  const part = local.split(/[.\-_]/)[0] ?? '';
  if (!part) return 'there';
  return part.charAt(0).toUpperCase() + part.slice(1);
}

function greet(): string {
  const hour = new Date().getHours();
  if (hour < 12) return 'Good morning';
  if (hour < 18) return 'Good afternoon';
  return 'Good evening';
}

export default function DashboardPage() {
  const [data, setData] = useState<BriefingData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    api.me
      .briefing()
      .then((response) => {
        if (!cancelled) setData(response.data);
      })
      .catch(() => {
        /* surface gracefully via empty states below */
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const name = firstName(getUserEmail());
  const pipelineCounts = data?.pipeline_counts ?? {};
  const pipelineTotal = Object.values(pipelineCounts).reduce((sum, count) => sum + count, 0);
  const pipelineHeat = [
    pipelineCounts.saved ?? 0,
    pipelineCounts.applied ?? 0,
    pipelineCounts.interviewing ?? 0,
    pipelineCounts.offered ?? 0,
    pipelineCounts.rejected ?? 0,
    pipelineCounts.withdrawn ?? 0,
    pipelineTotal,
  ];

  return (
    <WorkspaceShell>
      <div className="mx-auto max-w-5xl space-y-10">
        <header>
          <h1 className="text-[46px] font-semibold leading-[1.02] tracking-[-0.02em]">
            {greet()},{' '}
            <span
              className="bg-clip-text text-transparent"
              style={{
                backgroundImage:
                  'linear-gradient(135deg, #14b8a6 0%, #2563eb 45%, #7c3aed 100%)',
              }}
            >
              {name}
            </span>
            .
          </h1>
          <p className="mt-2 text-[15px] text-ink-3">
            A quick read of your search today. Keep moving forward.
          </p>
        </header>

        {loading ? (
          <div className="text-ink-3">Loading your briefing…</div>
        ) : (
          <>
            <div className="grid grid-cols-1 gap-5 md:grid-cols-3">
              <SoftCard>
                <div className="flex items-center gap-2 text-[11px] uppercase tracking-[0.18em] text-ink-3">
                  <Sparkles size={14} />
                  Today's prep
                </div>
                {data?.next_prep ? (
                  <div className="mt-3">
                    <div className="text-[15px] font-semibold text-ink">
                      {data.next_prep.custom_role ?? 'Interview prep pack'}
                    </div>
                    <div className="mt-1 text-[12px] text-ink-3">
                      Last worked on {new Date(data.next_prep.created_at).toLocaleDateString()}
                    </div>
                    <a
                      href={`/interview-prep/${data.next_prep.id}`}
                      className="mt-3 inline-block text-[13px] text-accent-cobalt hover:underline"
                    >
                      Open pack →
                    </a>
                  </div>
                ) : (
                  <p className="mt-3 text-[13px] text-ink-3">
                    No prep scheduled. Run one after you save a role.
                  </p>
                )}
              </SoftCard>

              <SoftCard>
                <div className="flex items-center gap-2 text-[11px] uppercase tracking-[0.18em] text-ink-3">
                  <Briefcase size={14} />
                  Pipeline heat
                </div>
                <div className="mt-3 flex items-baseline gap-3">
                  <span className="text-[32px] font-semibold tabular-nums tracking-[-0.02em] text-ink">
                    {pipelineTotal}
                  </span>
                  <span className="text-[12px] text-ink-3">roles in flight</span>
                </div>
                <div className="mt-3">
                  <Sparkline values={pipelineHeat} label="Pipeline heat" />
                </div>
                <a
                  href="/pipeline"
                  className="mt-3 inline-block text-[13px] text-accent-cobalt hover:underline"
                >
                  Open pipeline →
                </a>
              </SoftCard>

              <SoftCard>
                <div className="flex items-center gap-2 text-[11px] uppercase tracking-[0.18em] text-ink-3">
                  <TrendingUp size={14} />
                  Top-graded today
                </div>
                {data && data.top_jobs.length > 0 ? (
                  <ul className="mt-3 space-y-3">
                    {data.top_jobs.slice(0, 3).map((job) => (
                      <li
                        key={job.evaluation_id}
                        className="flex items-center justify-between gap-3"
                      >
                        <div className="min-w-0">
                          <a
                            href={`/jobs/${job.job_id}`}
                            className="block truncate text-[13px] font-medium text-ink hover:underline"
                          >
                            {job.title}
                          </a>
                          <div className="truncate text-[11px] text-ink-3">
                            {job.company ?? '—'}
                          </div>
                        </div>
                        <GradeBar
                          variant="inline"
                          value={Math.round(job.match_score * 100)}
                        />
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="mt-3 text-[13px] text-ink-3">
                    No jobs graded in the last 7 days. Paste one to kick things off.
                  </p>
                )}
              </SoftCard>
            </div>

            {pipelineTotal === 0 && (!data || data.top_jobs.length === 0) && (
              <EmptyState
                title="Slow day."
                body="Nothing in your pipeline and nothing graded this week. Start a scan or paste a job to warm things up."
                cta={
                  <a href="/scans">
                    <GradientButton>Start a scan</GradientButton>
                  </a>
                }
              />
            )}
          </>
        )}
      </div>
    </WorkspaceShell>
  );
}
