import { useEffect, useMemo, useState } from 'react';
import {
  FileText,
  IdCard,
  Link2,
  ShieldCheck,
  Target,
} from 'lucide-react';

import { SoftCard } from '../components/ui/SoftCard';
import { WorkspaceShell } from '../components/workspace/WorkspaceShell';
import { BasicsPanel } from '../components/profile/BasicsPanel';
import { PrivacyPanel } from '../components/profile/PrivacyPanel';
import { ResumePanel } from '../components/profile/ResumePanel';
import { SocialPanel } from '../components/profile/SocialPanel';
import { TargetsPanel } from '../components/profile/TargetsPanel';
import { api, type Profile } from '../lib/api';

type TabId = 'basics' | 'resume' | 'targets' | 'privacy' | 'social';

const TABS: {
  id: TabId;
  label: string;
  sub: string;
  icon: typeof IdCard;
}[] = [
  { id: 'basics', label: 'Basics', sub: 'Identity + contact', icon: IdCard },
  { id: 'resume', label: 'Resume', sub: 'Master + tailored copies', icon: FileText },
  { id: 'targets', label: 'Targets', sub: 'What we grade against', icon: Target },
  { id: 'privacy', label: 'Privacy', sub: 'Data + visibility', icon: ShieldCheck },
  { id: 'social', label: 'Social', sub: 'External links', icon: Link2 },
];

function tabFromPath(pathname: string): TabId {
  const match = /^\/profile\/([a-z]+)/.exec(pathname);
  const found = match?.[1];
  return (TABS.find((tab) => tab.id === found)?.id) ?? 'basics';
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
    } catch (caught) {
      setError((caught as Error).message);
    } finally {
      setSaving(false);
    }
  }

  const activeTab = useMemo(() => TABS.find((item) => item.id === tab) ?? TABS[0], [tab]);

  return (
    <WorkspaceShell>
      <div className="mx-auto max-w-6xl">
        <header className="mb-6">
          <h1 className="text-[28px] font-semibold tracking-tight">Profile</h1>
          <p className="mt-1 text-[13px] text-ink-3">
            Everything we use to grade jobs and write your pitch. Edit anytime;
            nothing is shown to employers.
          </p>
        </header>

        <div className="flex gap-8">
          <nav className="w-[220px] flex-none">
            <ul className="space-y-1">
              {TABS.map((item) => {
                const Icon = item.icon;
                const isActive = item.id === tab;
                return (
                  <li key={item.id}>
                    <button
                      type="button"
                      onClick={() => selectTab(item.id)}
                      className={
                        'flex w-full items-start gap-2 rounded-lg px-3 py-2 text-left transition-colors duration-150 motion-reduce:transition-none ' +
                        (isActive
                          ? 'bg-ink text-white'
                          : 'text-ink-2 hover:bg-card')
                      }
                    >
                      <Icon
                        size={16}
                        strokeWidth={1.6}
                        className={isActive ? 'text-white' : 'text-ink-3'}
                      />
                      <span>
                        <span className="block text-[13px] font-medium">{item.label}</span>
                        <span
                          className={
                            'block text-[11px] ' + (isActive ? 'text-white/70' : 'text-ink-3')
                          }
                        >
                          {item.sub}
                        </span>
                      </span>
                    </button>
                  </li>
                );
              })}
            </ul>
          </nav>

          <section className="min-w-0 flex-1 space-y-5">
            {loading ? (
              <p className="text-ink-3">Loading your profile…</p>
            ) : error ? (
              <SoftCard>
                <p role="alert" className="text-[13px] text-red-800">
                  {error}
                </p>
              </SoftCard>
            ) : profile ? (
              <div key={activeTab.id} className="animate-fade-up motion-reduce:animate-none">
                {activeTab.id === 'basics' && (
                  <BasicsPanel
                    profile={profile}
                    saving={saving}
                    onSave={(patch) => void saveProfile(patch)}
                  />
                )}
                {activeTab.id === 'resume' && <ResumePanel profile={profile} />}
                {activeTab.id === 'targets' && (
                  <TargetsPanel
                    profile={profile}
                    saving={saving}
                    onSave={(patch) => void saveProfile(patch)}
                  />
                )}
                {activeTab.id === 'privacy' && <PrivacyPanel />}
                {activeTab.id === 'social' && (
                  <SocialPanel
                    profile={profile}
                    saving={saving}
                    onSave={(patch) => void saveProfile(patch)}
                  />
                )}
              </div>
            ) : null}
          </section>
        </div>
      </div>
    </WorkspaceShell>
  );
}
