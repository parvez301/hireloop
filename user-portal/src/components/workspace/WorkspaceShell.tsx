import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import {
  Briefcase,
  ChevronDown,
  FileText,
  LayoutDashboard,
  LogOut,
  MessageSquare,
  Plus,
  Radar,
  Receipt,
  Search,
  Settings,
  Sparkles,
  TrendingUp,
} from 'lucide-react';

import { Sidebar, type SidebarSection } from '../ui/Sidebar';
import { getUserEmail, logout } from '../../lib/auth';

function moduleFromPath(pathname: string): string {
  if (pathname === '/' || pathname.startsWith('/dashboard')) return 'dashboard';
  if (pathname.startsWith('/pipeline')) return 'pipeline';
  if (pathname.startsWith('/scans')) return 'scans';
  if (pathname.startsWith('/interview-prep')) return 'interview';
  if (pathname.startsWith('/story-bank')) return 'stories';
  if (pathname.startsWith('/negotiations')) return 'negotiation';
  if (pathname.startsWith('/chat') || pathname.startsWith('/ask')) return 'chat';
  if (pathname.startsWith('/jobs/')) return 'job-detail';
  if (pathname.startsWith('/settings/billing') || pathname.startsWith('/billing'))
    return 'billing';
  if (pathname.startsWith('/profile')) return 'profile';
  return 'dashboard';
}

const MODULE_LABELS: Record<string, string> = {
  dashboard: 'Dashboard',
  chat: 'Assistant',
  pipeline: 'Pipeline',
  scans: 'Scans',
  'job-detail': 'Job detail',
  interview: 'Interview prep',
  stories: 'Story bank',
  negotiation: 'Negotiation',
  billing: 'Billing',
  profile: 'Profile',
};

const SECTIONS: SidebarSection[] = [
  {
    label: 'Workspace',
    items: [
      { id: 'dashboard', label: 'Dashboard', href: '/', icon: LayoutDashboard },
      { id: 'chat', label: 'Assistant', href: '/ask', icon: MessageSquare },
      { id: 'pipeline', label: 'Pipeline', href: '/pipeline', icon: Briefcase },
      { id: 'scans', label: 'Scans', href: '/scans', icon: Radar },
      {
        id: 'interview',
        label: 'Interview prep',
        href: '/interview-prep',
        icon: Sparkles,
      },
      { id: 'stories', label: 'Story bank', href: '/story-bank', icon: FileText },
      {
        id: 'negotiation',
        label: 'Negotiation',
        href: '/negotiations',
        icon: TrendingUp,
      },
    ],
  },
  {
    label: 'Account',
    items: [
      { id: 'billing', label: 'Billing', href: '/settings/billing', icon: Receipt },
      { id: 'profile', label: 'Profile', href: '/profile/basics', icon: Settings },
    ],
  },
];

type Props = {
  children: ReactNode;
  activeOverride?: string;
  dense?: boolean;
  /** Override the breadcrumb tail text (defaults to the active module label). */
  crumb?: string;
  /** Optional right-side actions in the topbar (e.g. "+ Add job"). */
  topbarActions?: ReactNode;
};

export function WorkspaceShell({
  children,
  activeOverride,
  dense = false,
  crumb,
  topbarActions,
}: Props) {
  const [path, setPath] = useState<string>(() => window.location.pathname);
  useEffect(() => {
    const handler = () => setPath(window.location.pathname);
    window.addEventListener('popstate', handler);
    return () => window.removeEventListener('popstate', handler);
  }, []);

  const activeId = activeOverride ?? moduleFromPath(path);
  const email = getUserEmail();
  const initials = useMemo(() => {
    if (!email) return '?';
    const name = email.split('@')[0];
    return name.slice(0, 2).toUpperCase();
  }, [email]);
  const displayName = useMemo(() => {
    if (!email) return 'Account';
    return email.split('@')[0].replace(/[._-]/g, ' ');
  }, [email]);

  const [paletteOpen, setPaletteOpen] = useState(false);
  useEffect(() => {
    const listener = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        setPaletteOpen((previous) => !previous);
      }
      if (event.key === 'Escape') setPaletteOpen(false);
    };
    window.addEventListener('keydown', listener);
    return () => window.removeEventListener('keydown', listener);
  }, []);

  const crumbText = crumb ?? MODULE_LABELS[activeId] ?? 'Dashboard';

  return (
    <div className="flex min-h-screen bg-bg text-ink [font-feature-settings:'ss01','cv11']">
      <Sidebar
        sections={SECTIONS}
        activeId={activeId}
        header={
          <a href="/" className="flex items-center gap-2.5 px-1 py-1">
            <span
              aria-hidden
              className="h-7 w-7 rounded-md"
              style={{
                backgroundImage:
                  'linear-gradient(135deg, #14b8a6 0%, #2563eb 45%, #7c3aed 100%)',
              }}
            />
            <span className="text-[15px] font-semibold tracking-tight text-ink">
              HireLoop
            </span>
          </a>
        }
        footer={
          <div className="rounded-xl border border-line bg-white p-3">
            <div className="flex items-center gap-2">
              <div
                aria-hidden
                className="flex h-8 w-8 flex-none items-center justify-center rounded-full text-[12px] font-semibold text-white"
                style={{
                  backgroundImage:
                    'linear-gradient(135deg, #14b8a6 0%, #2563eb 45%, #7c3aed 100%)',
                }}
              >
                {initials}
              </div>
              <div className="min-w-0">
                <div className="truncate text-[13px] font-medium capitalize text-ink">
                  {displayName}
                </div>
                {email && (
                  <div className="truncate text-[11px] text-ink-3">{email}</div>
                )}
              </div>
            </div>
            <div className="mt-2 flex items-center justify-between text-[11px] text-ink-3">
              <span className="inline-flex items-center gap-1">
                <span className="h-1.5 w-1.5 rounded-full bg-teal" />
                Trial
              </span>
              <a
                href="/settings/billing"
                className="text-ink underline decoration-dotted underline-offset-4 hover:decoration-solid"
              >
                Upgrade
              </a>
            </div>
          </div>
        }
      />

      <main className="flex min-w-0 flex-1 flex-col">
        <div className="sticky top-0 z-30 border-b border-line bg-bg/80 backdrop-blur">
          <div className="flex items-center justify-between gap-4 px-6 py-3">
            <div className="flex min-w-0 items-center gap-2">
              <span className="text-[12px] text-ink-4">HireLoop</span>
              <span className="text-[12px] text-ink-4">/</span>
              <span className="truncate text-[13px] font-medium text-ink">
                {crumbText}
              </span>
            </div>

            <button
              type="button"
              onClick={() => setPaletteOpen(true)}
              className="hidden md:flex flex-1 max-w-md items-center gap-2 rounded-full border border-line bg-white px-3 py-1.5 text-[12.5px] text-ink-3 hover:text-ink"
            >
              <Search size={14} />
              <span className="flex-1 text-left">
                Search jobs, companies, stories…
              </span>
              <kbd className="rounded border border-line px-1.5 text-[10px] text-ink-4">
                ⌘K
              </kbd>
            </button>

            <div className="flex items-center gap-1.5">
              {topbarActions ?? (
                <a
                  href="/pipeline"
                  className="inline-flex items-center gap-1 rounded-lg border border-line-2 bg-white px-2.5 py-1.5 text-[12px] font-medium text-ink hover:bg-card"
                >
                  <Plus size={12} strokeWidth={2.2} />
                  Add job
                </a>
              )}
              <div className="mx-1 h-6 w-px bg-line" />
              <button
                type="button"
                aria-label="Account"
                className="flex items-center gap-2 rounded-lg px-2 py-1 hover:bg-card"
              >
                <div
                  aria-hidden
                  className="flex h-6 w-6 items-center justify-center rounded-full text-[10px] font-semibold text-white"
                  style={{
                    backgroundImage:
                      'linear-gradient(135deg, #14b8a6 0%, #2563eb 45%, #7c3aed 100%)',
                  }}
                >
                  {initials}
                </div>
                <ChevronDown size={12} className="text-ink-3" strokeWidth={1.8} />
              </button>
              <button
                type="button"
                onClick={logout}
                aria-label="Sign out"
                className="inline-flex h-8 w-8 items-center justify-center rounded-lg text-ink-3 hover:bg-card hover:text-ink"
              >
                <LogOut size={16} />
              </button>
            </div>
          </div>
        </div>

        <div className={dense ? 'px-6 py-6' : 'px-8 py-10'}>{children}</div>
      </main>

      {paletteOpen && <CommandPaletteStub onClose={() => setPaletteOpen(false)} />}
    </div>
  );
}

function CommandPaletteStub({ onClose }: { onClose: () => void }) {
  const inputRef = useRef<HTMLInputElement>(null);
  useEffect(() => {
    inputRef.current?.focus();
  }, []);
  const [query, setQuery] = useState('');

  const suggestions: { label: string; href: string }[] = [
    { label: 'Dashboard', href: '/' },
    { label: 'Pipeline', href: '/pipeline' },
    { label: 'Scans', href: '/scans' },
    { label: 'Interview prep', href: '/interview-prep' },
    { label: 'Story bank', href: '/story-bank' },
    { label: 'Negotiation', href: '/negotiations' },
    { label: 'Billing', href: '/settings/billing' },
    { label: 'Profile · Basics', href: '/profile/basics' },
    { label: 'Profile · Targets', href: '/profile/targets' },
  ].filter(
    (entry) =>
      query.trim() === '' ||
      entry.label.toLowerCase().includes(query.toLowerCase()),
  );

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center bg-black/30 px-6 pt-[12vh]"
      onClick={onClose}
    >
      <div
        onClick={(event) => event.stopPropagation()}
        className="w-full max-w-lg overflow-hidden rounded-2xl bg-white shadow-2xl"
      >
        <div className="border-b border-line px-3 py-2">
          <input
            ref={inputRef}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Navigate to…"
            className="w-full border-0 bg-transparent px-2 py-1 text-[14px] text-ink placeholder:text-ink-4 focus:outline-none"
          />
        </div>
        <ul className="max-h-72 overflow-y-auto py-1">
          {suggestions.map((entry) => (
            <li key={entry.href}>
              <a
                href={entry.href}
                className="block px-3 py-2 text-[13px] text-ink-2 hover:bg-card"
              >
                {entry.label}
              </a>
            </li>
          ))}
        </ul>
        <div className="border-t border-line px-3 py-2 text-[11px] text-ink-4">
          Press Esc to close
        </div>
      </div>
    </div>
  );
}
