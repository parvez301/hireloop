import { useEffect, useState } from 'react';

import { SoftCard } from '../ui/SoftCard';
import { GradientButton } from '../ui/GradientButton';
import { getUserEmail } from '../../lib/auth';
import type { Profile } from '../../lib/api';

type Props = {
  profile: Profile;
  saving: boolean;
  onSave: (patch: Partial<Profile>) => void;
};

const INPUT_CLS =
  'mt-1.5 block w-full rounded-xl border border-line-2 bg-white px-3.5 py-2.5 text-[14px] text-ink placeholder:text-ink-4 focus:border-ink focus:outline-none focus:ring-4 focus:ring-black/5';
const READONLY_CLS =
  'flex-1 rounded-xl border border-line-2 bg-card px-3.5 py-2.5 text-[14px] text-ink';

export function BasicsPanel({ profile, saving, onSave }: Props) {
  const email = getUserEmail() ?? '—';
  const [fullName, setFullName] = useState(profile.full_name ?? '');
  const [headline, setHeadline] = useState(profile.headline ?? '');
  const [location, setLocation] = useState(profile.current_location ?? '');

  useEffect(() => {
    setFullName(profile.full_name ?? '');
    setHeadline(profile.headline ?? '');
    setLocation(profile.current_location ?? '');
  }, [profile]);

  const initials = (() => {
    const source = fullName || email.split('@')[0] || '';
    const parts = source.trim().split(/\s+/).filter(Boolean);
    if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
    if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
    return '??';
  })();

  const dirty =
    fullName !== (profile.full_name ?? '') ||
    headline !== (profile.headline ?? '') ||
    location !== (profile.current_location ?? '');

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
                {fullName || email.split('@')[0]}
              </div>
              <div className="truncate text-[11.5px] text-ink-3">{email}</div>
              <div className="mt-2 inline-flex items-center gap-1 rounded-full border border-line bg-white px-2 py-0.5 text-[10.5px] text-ink-2">
                <span className="h-1.5 w-1.5 rounded-full bg-teal" /> Verified
              </div>
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label className="block text-[12px] font-medium text-ink-2">
                Full name
              </label>
              <input
                className={INPUT_CLS}
                placeholder="Ava Chen"
                value={fullName}
                onChange={(event) => setFullName(event.target.value)}
              />
            </div>
            <div>
              <label className="block text-[12px] font-medium text-ink-2">
                Email{' '}
                <span className="font-normal text-ink-4">· verified</span>
              </label>
              <div className="mt-1.5 flex gap-2">
                <input value={email} readOnly className={READONLY_CLS} />
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
                Headline
              </label>
              <input
                className={INPUT_CLS}
                placeholder="Senior Product Designer · Fintech, B2B SaaS"
                value={headline}
                onChange={(event) => setHeadline(event.target.value)}
              />
              <p className="mt-1 text-[11.5px] text-ink-4">
                Shown on every tailored resume header.
              </p>
            </div>
            <div>
              <label className="block text-[12px] font-medium text-ink-2">
                Current location
              </label>
              <input
                className={INPUT_CLS}
                placeholder="New York, NY"
                value={location}
                onChange={(event) => setLocation(event.target.value)}
              />
              <p className="mt-1 text-[11.5px] text-ink-4">
                Where you are today. Target locations live on the Target roles
                tab.
              </p>
            </div>
            <div className="md:col-span-2">
              <label className="block text-[12px] font-medium text-ink-2">
                Member since
              </label>
              <input value={memberSince} readOnly className={READONLY_CLS} />
            </div>
          </div>
        </div>
        <div className="mt-5 flex justify-end">
          <GradientButton
            disabled={saving || !dirty}
            onClick={() =>
              onSave({
                full_name: fullName.trim() || null,
                headline: headline.trim() || null,
                current_location: location.trim() || null,
              })
            }
          >
            {saving ? 'Saving…' : dirty ? 'Save basics' : 'Saved'}
          </GradientButton>
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
