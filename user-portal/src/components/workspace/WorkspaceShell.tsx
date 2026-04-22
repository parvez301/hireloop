import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import {
  Bell,
  Briefcase,
  FileText,
  LayoutDashboard,
  LogOut,
  MessageSquare,
  Radar,
  Receipt,
  Search,
  Settings,
  Sparkles,
  TrendingUp,
} from 'lucide-react';

import { AppHeader } from '../ui/AppHeader';
import { Sidebar, type SidebarItem } from '../ui/Sidebar';
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

const MODULE_ITEMS: SidebarItem[] = [
  { id: 'dashboard', label: 'Dashboard', href: '/', icon: LayoutDashboard },
  { id: 'chat', label: 'Ask', href: '/ask', icon: MessageSquare },
  { id: 'pipeline', label: 'Pipeline', href: '/pipeline', icon: Briefcase },
  { id: 'scans', label: 'Scans', href: '/scans', icon: Radar },
  { id: 'interview', label: 'Interview prep', href: '/interview-prep', icon: Sparkles },
  { id: 'stories', label: 'Story bank', href: '/story-bank', icon: FileText },
  { id: 'negotiation', label: 'Negotiation', href: '/negotiations', icon: TrendingUp },
  { id: 'billing', label: 'Billing', href: '/settings/billing', icon: Receipt },
  { id: 'profile', label: 'Profile', href: '/profile/basics', icon: Settings },
];

type Props = {
  children: ReactNode;
  activeOverride?: string;
  dense?: boolean;
};

export function WorkspaceShell({ children, activeOverride, dense = false }: Props) {
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

  return (
    <div className="min-h-screen bg-bg text-ink [font-feature-settings:'ss01','cv11']">
      <AppHeader
        middle={
          <div className="flex items-center justify-center">
            <button
              type="button"
              onClick={() => setPaletteOpen(true)}
              className="inline-flex items-center gap-2 rounded-full border border-line bg-white px-3 py-1 text-[12px] text-ink-3 hover:text-ink"
            >
              <Search size={14} />
              Search
              <span className="rounded-md bg-card px-1 text-[10px] font-medium text-ink-3">
                ⌘K
              </span>
            </button>
          </div>
        }
        right={
          <div className="flex items-center gap-3">
            <button
              type="button"
              className="relative inline-flex h-8 w-8 items-center justify-center rounded-full text-ink-3 hover:text-ink"
              aria-label="Notifications"
            >
              <Bell size={16} />
            </button>
            <div
              aria-label={email ?? 'account'}
              className="inline-flex h-7 w-7 items-center justify-center rounded-full bg-ink text-[11px] font-semibold text-white"
            >
              {initials}
            </div>
            <button
              type="button"
              onClick={logout}
              className="inline-flex h-8 w-8 items-center justify-center rounded-full text-ink-3 hover:text-ink"
              aria-label="Sign out"
            >
              <LogOut size={16} />
            </button>
          </div>
        }
      />

      <div className="mx-auto flex max-w-7xl">
        <Sidebar items={MODULE_ITEMS} activeId={activeId} />
        <main className={dense ? 'flex-1 px-6 py-6' : 'flex-1 px-8 py-10'}>
          {children}
        </main>
      </div>

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
