import { SoftCard } from '../ui/SoftCard';
import { EmptyState } from '../ui/EmptyState';
import type { Profile } from '../../lib/api';

type Props = { profile: Profile };

export function ResumePanel({ profile }: Props) {
  const parsed = profile.parsed_resume_json ?? null;
  const skills = Array.isArray((parsed as { skills?: unknown })?.skills)
    ? ((parsed as { skills: string[] }).skills ?? [])
    : [];

  if (!profile.master_resume_md) {
    return (
      <SoftCard header="Master resume">
        <EmptyState
          title="No resume uploaded yet."
          body="Upload a PDF or paste markdown from the onboarding flow."
          cta={
            <a
              href="/onboarding"
              className="text-[13px] text-accent-cobalt hover:underline"
            >
              Open onboarding →
            </a>
          }
        />
      </SoftCard>
    );
  }

  return (
    <SoftCard header="Master resume" padding="md">
      <div className="grid grid-cols-1 gap-6 md:grid-cols-[2fr_1fr]">
        <div className="relative max-h-[480px] overflow-hidden rounded-2xl border border-line bg-card p-5 text-[13px] leading-relaxed text-ink-2">
          <pre className="whitespace-pre-wrap font-mono">{profile.master_resume_md}</pre>
          <div className="pointer-events-none absolute inset-x-0 bottom-0 h-16 bg-gradient-to-t from-card to-transparent" />
        </div>
        <div className="space-y-4">
          <div>
            <div className="text-[11px] uppercase tracking-[0.18em] text-ink-3">
              Skills ({skills.length})
            </div>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {skills.slice(0, 30).map((skill) => (
                <span
                  key={skill}
                  className="rounded-full border border-line bg-white px-2.5 py-0.5 text-[11px] text-ink-2"
                >
                  {skill}
                </span>
              ))}
              {skills.length === 0 && (
                <span className="text-[12px] text-ink-3">No skills parsed.</span>
              )}
            </div>
          </div>
          <div className="flex flex-col gap-2">
            <a
              href="/onboarding"
              className="rounded-full border border-line-2 bg-white px-3 py-1.5 text-center text-[12px] text-ink-2 hover:bg-[#faf9f6]"
            >
              Re-upload resume
            </a>
            <button
              type="button"
              onClick={() => {
                const blob = new Blob([profile.master_resume_md ?? ''], {
                  type: 'text/markdown',
                });
                const url = URL.createObjectURL(blob);
                const link = document.createElement('a');
                link.href = url;
                link.download = 'resume.md';
                link.click();
                URL.revokeObjectURL(url);
              }}
              className="rounded-full border border-line-2 bg-white px-3 py-1.5 text-[12px] text-ink-2 hover:bg-[#faf9f6]"
            >
              Download markdown
            </button>
          </div>
        </div>
      </div>
    </SoftCard>
  );
}
