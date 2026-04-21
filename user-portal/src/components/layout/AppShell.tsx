import type { ReactNode } from 'react';

import { getUserEmail, logout as defaultLogout } from '../../lib/auth';

interface AppShellProps {
  children: ReactNode;
  userEmail?: string;
  onLogout?: () => void;
}

export function AppShell({ children, userEmail, onLogout }: AppShellProps) {
  const resolvedEmail = userEmail ?? getUserEmail();
  const resolvedLogout = onLogout ?? defaultLogout;

  return (
    <div className="min-h-screen bg-white text-[#37352f]">
      <header className="flex items-center justify-between border-b border-[#e3e2e0] px-6 py-3">
        <div className="flex items-center gap-2">
          <a href="/" className="text-lg font-semibold">
            HireLoop
          </a>
          <span className="rounded bg-[#f7f6f3] px-2 py-0.5 text-xs text-[#787774]">
            Phase 2d
          </span>
        </div>
        <div className="flex items-center gap-3 text-sm text-[#787774]">
          <a href="/pipeline" className="hover:text-[#37352f]">
            Pipeline
          </a>
          <a href="/scans" className="hover:text-[#37352f]">
            Scans
          </a>
          <a href="/story-bank" className="hover:text-[#37352f]">
            Stories
          </a>
          <a href="/interview-prep" className="hover:text-[#37352f]">
            Interview prep
          </a>
          <a href="/negotiations" className="hover:text-[#37352f]">
            Negotiations
          </a>
          <a href="/settings/billing" className="hover:text-[#37352f]">
            Billing
          </a>
          {resolvedEmail && <span>{resolvedEmail}</span>}
          <button
            type="button"
            onClick={resolvedLogout}
            className="rounded border border-[#e3e2e0] px-2 py-1 hover:bg-[#efefef]"
          >
            Log out
          </button>
        </div>
      </header>
      <main className="mx-auto max-w-3xl px-6 py-6">{children}</main>
    </div>
  );
}
