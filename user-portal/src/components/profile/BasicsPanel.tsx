import { SoftCard } from '../ui/SoftCard';
import { getUserEmail } from '../../lib/auth';
import type { Profile } from '../../lib/api';

type Props = {
  profile: Profile;
  saving: boolean;
  onSave: (patch: Partial<Profile>) => void;
};

export function BasicsPanel({ profile }: Props) {
  const email = getUserEmail() ?? '—';
  const initials = (email.split('@')[0] ?? '??').slice(0, 2).toUpperCase();
  const memberSince = (() => {
    try {
      return new Date(profile.created_at).toLocaleDateString(undefined, {
        year: 'numeric',
        month: 'short',
      });
    } catch {
      return '—';
    }
  })();

  return (
    <div className="space-y-5">
      <SoftCard
        padding="md"
        header={
          <div className="flex items-center justify-between">
            <span className="flex items-center gap-2">
              Identity
              <span className="text-[11px] normal-case tracking-normal text-ink-3">
                · appears on every tailored resume
              </span>
            </span>
          </div>
        }
      >
        <div className="grid items-start gap-6 md:grid-cols-[220px_1fr]">
          <div className="flex items-center gap-4 md:block">
            <div className="relative">
              <div
                aria-hidden
                className="flex h-20 w-20 items-center justify-center rounded-2xl text-[22px] font-semibold text-white"
                style={{
                  backgroundImage:
                    'linear-gradient(135deg, #14b8a6 0%, #2563eb 45%, #7c3aed 100%)',
                }}
              >
                {initials}
              </div>
            </div>
            <div className="md:mt-3">
              <div className="text-[13px] font-semibold text-ink">
                {email.split('@')[0]}
              </div>
              <div className="truncate text-[11.5px] text-ink-3">{email}</div>
              <div className="mt-2 inline-flex items-center gap-1 rounded-full border border-line bg-white px-2 py-0.5 text-[10.5px] text-ink-2">
                <span className="h-1.5 w-1.5 rounded-full bg-teal" /> Verified
              </div>
            </div>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-[12px] font-medium text-ink-2">
                Email{' '}
                <span className="font-normal text-ink-4">· verified</span>
              </label>
              <div className="mt-1.5 flex gap-2">
                <input
                  value={email}
                  readOnly
                  className="flex-1 rounded-xl border border-line-2 bg-card px-3.5 py-2.5 text-[14px] text-ink"
                />
                <button
                  type="button"
                  disabled
                  title="Email changes coming soon — contact support to change yours now."
                  className="whitespace-nowrap rounded-lg border border-line-2 bg-white px-3 text-[12px] font-medium text-ink disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Change
                </button>
              </div>
            </div>
            <div>
              <label className="block text-[12px] font-medium text-ink-2">
                Member since
              </label>
              <input
                value={memberSince}
                readOnly
                className="mt-1.5 block w-full rounded-xl border border-line-2 bg-card px-3.5 py-2.5 text-[14px] text-ink"
              />
            </div>
          </div>
        </div>
      </SoftCard>

      <SoftCard
        padding="md"
        header={
          <div className="flex items-center justify-between">
            <span className="flex items-center gap-2">
              Links
              <span className="text-[11px] normal-case tracking-normal text-ink-3">
                ·{' '}
                {[
                  profile.linkedin_url,
                  profile.github_url,
                  profile.portfolio_url,
                ].filter(Boolean).length}{' '}
                of 3 connected
              </span>
            </span>
          </div>
        }
      >
        <p className="text-[12.5px] text-ink-3">
          LinkedIn, GitHub, and Portfolio are edited from the{' '}
          <a
            href="/profile/social"
            className="text-ink underline decoration-dotted underline-offset-4 hover:decoration-solid"
          >
            Social profiles
          </a>{' '}
          tab. They power the recruiter-listed signal and the "show me your
          work" proof on tailored CVs.
        </p>
      </SoftCard>
    </div>
  );
}
