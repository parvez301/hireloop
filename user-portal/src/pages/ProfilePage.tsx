import { useEffect, useMemo, useRef, useState } from 'react';

import { SoftCard } from '../components/ui/SoftCard';
import { WorkspaceShell } from '../components/workspace/WorkspaceShell';
import { BasicsPanel } from '../components/profile/BasicsPanel';
import { PrivacyPanel } from '../components/profile/PrivacyPanel';
import { ResumePanel } from '../components/profile/ResumePanel';
import { SocialPanel } from '../components/profile/SocialPanel';
import { TargetsPanel } from '../components/profile/TargetsPanel';
import { api, type Profile } from '../lib/api';
import { getUserEmail } from '../lib/auth';

type TabId = 'basics' | 'resume' | 'targets' | 'social' | 'privacy';

const TABS: { id: TabId; label: string; badge?: string }[] = [
  { id: 'basics', label: 'Basics' },
  { id: 'resume', label: 'Resume' },
  { id: 'targets', label: 'Target roles' },
  { id: 'social', label: 'Social profiles', badge: 'NEW' },
  { id: 'privacy', label: 'Data & privacy' },
];

function tabFromPath(pathname: string): TabId {
  const match = /^\/profile\/([a-z]+)/.exec(pathname);
  const found = match?.[1];
  return TABS.find((tab) => tab.id === found)?.id ?? 'basics';
}

type Completion = {
  pct: number;
  items: { label: string; done: boolean }[];
};

function computeCompletion(profile: Profile): Completion {
  const items = [
    { label: 'Master resume uploaded', done: Boolean(profile.master_resume_md) },
    {
      label: 'Target roles set',
      done: (profile.target_roles?.length ?? 0) > 0,
    },
    {
      label: 'Target locations set',
      done: (profile.target_locations?.length ?? 0) > 0,
    },
    { label: 'LinkedIn connected', done: Boolean(profile.linkedin_url) },
    { label: 'GitHub profile added', done: Boolean(profile.github_url) },
    { label: 'Portfolio URL added', done: Boolean(profile.portfolio_url) },
  ];
  const done = items.filter((item) => item.done).length;
  const pct = Math.round((done / items.length) * 100);
  return { pct, items };
}

function initialsOf(email: string | null): string {
  if (!email) return '?';
  const local = email.split('@')[0] ?? '';
  const parts = local.split(/[._-]+/).filter(Boolean);
  if (parts.length === 0) return local.slice(0, 2).toUpperCase();
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[1][0]).toUpperCase();
}

function displayNameFrom(email: string | null): string {
  if (!email) return 'Account';
  const local = email.split('@')[0] ?? '';
  return local.replace(/[._-]+/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

function memberSince(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'short',
    });
  } catch {
    return iso;
  }
}

type Props = { tab?: TabId };

export default function ProfilePage({ tab: override }: Props = {}) {
  const [tab, setTab] = useState<TabId>(
    override ?? tabFromPath(window.location.pathname),
  );
  const [profile, setProfile] = useState<Profile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [dirty, setDirty] = useState<Partial<Profile>>({});
  const pendingTimerRef = useRef<number | null>(null);

  useEffect(() => {
    let cancelled = false;
    api.profile
      .get()
      .then((response) => {
        if (!cancelled) setProfile(response.data);
      })
      .catch((caught: Error) => {
        if (!cancelled) setError(caught.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  function selectTab(nextTab: TabId) {
    setTab(nextTab);
    window.history.pushState({}, '', `/profile/${nextTab}`);
  }

  async function saveProfile(patch: Partial<Profile>) {
    if (!profile) return;
    setSaving(true);
    setError(null);
    try {
      const response = await api.profile.update(patch);
      setProfile(response.data);
      setDirty({});
    } catch (caught) {
      setError((caught as Error).message);
    } finally {
      setSaving(false);
    }
  }

  function saveNow() {
    if (pendingTimerRef.current !== null) {
      window.clearTimeout(pendingTimerRef.current);
      pendingTimerRef.current = null;
    }
    if (Object.keys(dirty).length > 0) {
      void saveProfile(dirty);
    }
  }

  const email = getUserEmail();
  const initials = useMemo(() => initialsOf(email), [email]);
  const displayName = useMemo(() => displayNameFrom(email), [email]);
  const completion = useMemo(
    () => (profile ? computeCompletion(profile) : null),
    [profile],
  );

  const hasPendingChanges = Object.keys(dirty).length > 0;

  return (
    <WorkspaceShell
      crumb="Profile"
      topbarActions={
        <>
          <button
            type="button"
            className="inline-flex items-center rounded-lg border border-line-2 bg-white px-2.5 py-1.5 text-[12px] font-medium text-ink hover:bg-card"
          >
            Preview as recruiter sees
          </button>
          <button
            type="button"
            onClick={saveNow}
            disabled={saving || !hasPendingChanges}
            style={{
              backgroundImage: hasPendingChanges
                ? 'linear-gradient(135deg, #0f766e 0%, #1d4ed8 45%, #6d28d9 100%)'
                : undefined,
            }}
            className={
              'inline-flex items-center rounded-lg px-3 py-1.5 text-[12px] font-semibold transition-opacity ' +
              (hasPendingChanges
                ? 'text-white shadow-[0_8px_20px_-12px_rgba(37,99,235,0.55),inset_0_1px_0_rgba(255,255,255,0.15)] disabled:opacity-60'
                : 'border border-line-2 bg-white text-ink-3')
            }
          >
            {saving ? 'Saving…' : hasPendingChanges ? 'Save changes' : 'Saved'}
          </button>
        </>
      }
    >
      <div className="mx-auto max-w-[1100px]">
        <div className="flex flex-wrap items-start justify-between gap-6">
          <div className="flex items-start gap-4">
            <div
              aria-hidden
              className="flex h-16 w-16 flex-none items-center justify-center rounded-2xl text-[22px] font-semibold text-white"
              style={{
                backgroundImage:
                  'linear-gradient(135deg, #14b8a6 0%, #2563eb 45%, #7c3aed 100%)',
              }}
            >
              {initials}
            </div>
            <div>
              <p className="text-[11px] uppercase tracking-[0.18em] text-ink-3">
                Account
              </p>
              <h1 className="mt-1 text-[28px] font-semibold tracking-[-0.02em] text-ink">
                {displayName}
              </h1>
              <p className="mt-1 text-[13px] text-ink-3">
                {email ?? '—'}
                {profile && (
                  <>
                    {' · '}
                    <span>Member since {memberSince(profile.created_at)}</span>
                  </>
                )}
              </p>
              {completion && (
                <div className="mt-2 flex flex-wrap items-center gap-1.5">
                  <span className="inline-flex items-center gap-1 rounded-full border border-line bg-white px-2 py-0.5 text-[11px] text-ink-2">
                    <span className="h-1.5 w-1.5 rounded-full bg-teal" /> Profile{' '}
                    {completion.pct}% complete
                  </span>
                  {profile?.onboarding_state === 'done' && (
                    <span className="inline-flex items-center rounded-full border border-line bg-white px-2 py-0.5 text-[11px] text-ink-2">
                      Onboarding done
                    </span>
                  )}
                </div>
              )}
            </div>
          </div>

          {completion && (
            <div className="hidden md:block">
              <SoftCard className="w-[260px] p-3.5">
                <div className="flex items-center justify-between">
                  <p className="text-[11px] uppercase tracking-[0.18em] text-ink-3">
                    Completeness
                  </p>
                  <span className="text-[12px] font-semibold text-ink">
                    {completion.pct}%
                  </span>
                </div>
                <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-line">
                  <div
                    className="h-full rounded-full"
                    style={{
                      width: `${completion.pct}%`,
                      backgroundImage:
                        'linear-gradient(90deg, #14b8a6, #2563eb, #7c3aed)',
                    }}
                  />
                </div>
                <ul className="mt-3 space-y-1 text-[12px] text-ink-3">
                  {completion.items.map((item) => (
                    <li key={item.label} className="flex items-center gap-1.5">
                      <span className={item.done ? 'text-teal' : 'text-amber'}>
                        {item.done ? '✓' : '!'}
                      </span>
                      {item.label}
                    </li>
                  ))}
                </ul>
              </SoftCard>
            </div>
          )}
        </div>

        <div className="mt-8 border-b border-line">
          <div className="flex items-center gap-1 overflow-x-auto" role="tablist">
            {TABS.map((item) => {
              const isActive = item.id === tab;
              return (
                <button
                  key={item.id}
                  type="button"
                  role="tab"
                  aria-selected={isActive}
                  onClick={() => selectTab(item.id)}
                  className={
                    '-mb-px whitespace-nowrap border-b-2 px-3.5 py-2.5 text-[13px] font-medium transition-colors duration-150 motion-reduce:transition-none ' +
                    (isActive
                      ? 'border-cobalt text-ink'
                      : 'border-transparent text-ink-3 hover:text-ink')
                  }
                >
                  {item.label}
                  {item.badge && (
                    <span
                      className="ml-1.5 rounded-[4px] px-1.5 py-0.5 text-[9.5px] font-bold uppercase tracking-wider text-cobalt"
                      style={{
                        backgroundColor: 'rgba(37,99,235,0.12)',
                      }}
                    >
                      {item.badge}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </div>

        <section className="mt-6 min-w-0">
          {loading ? (
            <p className="text-ink-3">Loading your profile…</p>
          ) : error ? (
            <SoftCard className="p-5">
              <p role="alert" className="text-[13px] text-red-800">
                {error}
              </p>
            </SoftCard>
          ) : profile ? (
            <div
              key={tab}
              className="animate-fade-up motion-reduce:animate-none"
            >
              {tab === 'basics' && (
                <BasicsPanel
                  profile={profile}
                  saving={saving}
                  onSave={(patch) => void saveProfile(patch)}
                />
              )}
              {tab === 'resume' && <ResumePanel profile={profile} />}
              {tab === 'targets' && (
                <TargetsPanel
                  profile={profile}
                  saving={saving}
                  onSave={(patch) => void saveProfile(patch)}
                />
              )}
              {tab === 'social' && (
                <SocialPanel
                  profile={profile}
                  saving={saving}
                  onSave={(patch) => void saveProfile(patch)}
                />
              )}
              {tab === 'privacy' && <PrivacyPanel />}
            </div>
          ) : null}
        </section>
      </div>
    </WorkspaceShell>
  );
}
