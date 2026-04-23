import { useEffect, useState } from 'react';

import { EmptyState } from '../components/ui/EmptyState';
import { GradeBar } from '../components/ui/GradeBar';
import { GradientButton } from '../components/ui/GradientButton';
import { SoftCard } from '../components/ui/SoftCard';
import { Sparkline } from '../components/ui/Sparkline';
import { WorkspaceShell } from '../components/workspace/WorkspaceShell';
import { api, type BriefingData, type BriefingTopJob } from '../lib/api';
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

function humanDateHeader(): string {
  const now = new Date();
  const weekday = now.toLocaleDateString(undefined, { weekday: 'long' });
  const day = now.toLocaleDateString(undefined, { day: 'numeric', month: 'short' });
  const time = now.toLocaleTimeString(undefined, {
    hour: 'numeric',
    minute: '2-digit',
  });
  return `${weekday}, ${day} · ${time}`;
}

function topGrade(jobs: BriefingTopJob[]): string {
  if (jobs.length === 0) return '—';
  return jobs[0].overall_grade ?? '—';
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
  const interviewing = pipelineCounts.interviewing ?? 0;
  const applied = pipelineCounts.applied ?? 0;
  const topJobs = data?.top_jobs ?? [];

  const focusItems = topJobs.slice(0, 3);
  const overnight = topJobs.slice(3, 7);

  return (
    <WorkspaceShell>
      <div className="mx-auto max-w-6xl">
        <p className="text-[11px] uppercase tracking-[0.18em] text-ink-3">
          {humanDateHeader()}
        </p>
        <h1 className="mt-2 text-[38px] font-semibold leading-[1.05] tracking-[-0.02em] text-ink">
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
        </h1>
        <p className="mt-2 max-w-xl text-[14px] text-ink-3">
          {topJobs.length > 0
            ? `${topJobs.length} fresh matches graded. ${applied > 0 ? `${applied} application${applied === 1 ? '' : 's'} waiting on a reply.` : 'Pipeline idle — start a scan or paste a role.'}`
            : 'A quick read of your search. Start a scan or paste a role to warm things up.'}
        </p>

        {loading ? (
          <div className="mt-10 text-ink-3">Loading your briefing…</div>
        ) : (
          <>
            <div className="mt-8 grid grid-cols-2 gap-4 lg:grid-cols-4">
              <SoftCard className="p-5">
                <div className="text-[11px] uppercase tracking-[0.18em] text-ink-3">
                  In pipeline
                </div>
                <div className="mt-1 flex items-baseline gap-1.5">
                  <span className="text-[32px] font-semibold tabular-nums tracking-[-0.02em] text-ink">
                    {pipelineTotal}
                  </span>
                  {interviewing > 0 && (
                    <span className="text-[12px] font-medium text-teal">
                      {interviewing} interviewing
                    </span>
                  )}
                </div>
                <div className="mt-3">
                  <Sparkline values={pipelineHeat} label="Pipeline heat" />
                </div>
              </SoftCard>

              <SoftCard className="p-5">
                <div className="text-[11px] uppercase tracking-[0.18em] text-ink-3">
                  Top grade
                </div>
                <div className="mt-1 flex items-baseline gap-1.5">
                  <span
                    className="bg-clip-text text-[32px] font-semibold tabular-nums tracking-[-0.02em] text-transparent"
                    style={{
                      backgroundImage:
                        'linear-gradient(135deg, #14b8a6 0%, #2563eb 45%, #7c3aed 100%)',
                    }}
                  >
                    {topGrade(topJobs)}
                  </span>
                  <span className="text-[12px] font-medium text-ink-3">
                    across {topJobs.length} eval{topJobs.length === 1 ? '' : 's'}
                  </span>
                </div>
                <div className="mt-4 flex h-10 items-end gap-1.5">
                  <div className="w-3 rounded-sm bg-line" style={{ height: '20%' }} />
                  <div className="w-3 rounded-sm bg-line" style={{ height: '35%' }} />
                  <div className="w-3 rounded-sm bg-teal" style={{ height: '55%' }} />
                  <div className="w-3 rounded-sm bg-cobalt" style={{ height: '75%' }} />
                  <div className="w-3 rounded-sm bg-violet" style={{ height: '95%' }} />
                </div>
              </SoftCard>

              <SoftCard className="p-5">
                <div className="text-[11px] uppercase tracking-[0.18em] text-ink-3">
                  Interviewing
                </div>
                <div className="mt-1 flex items-baseline gap-2">
                  <span className="text-[32px] font-semibold tabular-nums tracking-[-0.02em] text-ink">
                    {interviewing}
                  </span>
                  {interviewing > 0 && (
                    <span className="inline-flex h-2 w-2 rounded-full bg-teal animate-pulse" />
                  )}
                </div>
                <div className="mt-3 text-[12px] text-ink-3">
                  {interviewing > 0
                    ? 'Loops in progress — keep them warm.'
                    : 'No active loops. Apply to pull one in.'}
                </div>
              </SoftCard>

              <SoftCard className="p-5">
                <div className="text-[11px] uppercase tracking-[0.18em] text-ink-3">
                  Awaiting reply
                </div>
                <div className="mt-1 flex items-baseline gap-1.5">
                  <span
                    className={
                      'text-[32px] font-semibold tabular-nums tracking-[-0.02em] ' +
                      (applied > 0 ? 'text-amber' : 'text-ink')
                    }
                  >
                    {applied}
                  </span>
                  {applied > 0 && (
                    <span className="text-[12px] font-medium text-amber">
                      Follow up
                    </span>
                  )}
                </div>
                <div className="mt-3 text-[12px] text-ink-3">
                  {applied > 0
                    ? 'Nudge recruiters past the 3-day mark.'
                    : 'Inbox clear. Ship the next application.'}
                </div>
              </SoftCard>
            </div>

            <div className="mt-6 grid gap-6 lg:grid-cols-12">
              <SoftCard className="p-6 lg:col-span-7">
                <div className="flex items-center justify-between">
                  <h3 className="text-[15px] font-semibold text-ink">Today's focus</h3>
                  <span className="text-[11px] uppercase tracking-[0.18em] text-ink-3">
                    {focusItems.length} item{focusItems.length === 1 ? '' : 's'}
                  </span>
                </div>
                {focusItems.length === 0 ? (
                  <p className="mt-4 text-[13px] text-ink-3">
                    Nothing queued. Paste a job to generate your first focus item.
                  </p>
                ) : (
                  <div className="mt-4 space-y-3">
                    {focusItems.map((job) => (
                      <div
                        key={job.evaluation_id}
                        className="flex items-start gap-3 rounded-xl border border-line p-4"
                      >
                        <GradeBar
                          variant="inline"
                          value={Math.round(job.match_score * 100)}
                        />
                        <div className="min-w-0 flex-1">
                          <a
                            href={`/jobs/${job.job_id}`}
                            className="block truncate text-[14px] font-medium text-ink hover:underline"
                          >
                            {job.title}
                          </a>
                          <div className="mt-0.5 truncate text-[12px] text-ink-3">
                            {job.company ?? '—'}
                            {job.location ? ` · ${job.location}` : ''}
                          </div>
                        </div>
                        <a
                          href={`/jobs/${job.job_id}`}
                          className="rounded-lg border border-line-2 bg-white px-3 py-1.5 text-[12px] font-medium text-ink hover:bg-card"
                        >
                          Open
                        </a>
                      </div>
                    ))}
                  </div>
                )}
              </SoftCard>

              <SoftCard className="p-6 lg:col-span-5">
                <div className="flex items-center justify-between">
                  <h3 className="text-[15px] font-semibold text-ink">
                    Fresh overnight
                  </h3>
                  {topJobs.length > 4 && (
                    <a
                      href="/pipeline"
                      className="text-[12px] text-ink underline decoration-dotted underline-offset-4 hover:decoration-solid"
                    >
                      See all {topJobs.length} →
                    </a>
                  )}
                </div>
                {overnight.length === 0 ? (
                  <p className="mt-4 text-[13px] text-ink-3">
                    No overnight pulls yet. Schedule a scan to fill this in.
                  </p>
                ) : (
                  <ul className="mt-4 space-y-2">
                    {overnight.map((job) => (
                      <li key={job.evaluation_id}>
                        <a
                          href={`/jobs/${job.job_id}`}
                          className="flex items-center gap-3 rounded-xl px-3 py-2.5 hover:bg-card"
                        >
                          <GradeBar
                            variant="inline"
                            value={Math.round(job.match_score * 100)}
                          />
                          <div className="min-w-0 flex-1">
                            <div className="truncate text-[13.5px] font-medium text-ink">
                              {job.title}
                            </div>
                            <div className="truncate text-[11.5px] text-ink-3">
                              {job.company ?? '—'}
                              {job.location ? ` · ${job.location}` : ''}
                            </div>
                          </div>
                        </a>
                      </li>
                    ))}
                  </ul>
                )}
              </SoftCard>
            </div>

            {pipelineTotal === 0 && topJobs.length === 0 && (
              <div className="mt-8">
                <EmptyState
                  title="Slow day."
                  body="Nothing in your pipeline and nothing graded this week. Start a scan or paste a job to warm things up."
                  cta={
                    <a href="/scans">
                      <GradientButton>Start a scan</GradientButton>
                    </a>
                  }
                />
              </div>
            )}
          </>
        )}
      </div>
    </WorkspaceShell>
  );
}
