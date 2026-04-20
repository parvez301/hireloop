import { Link, NavLink } from 'react-router-dom';

import { navCopy } from '../content/copy';
import { signupUrl } from '../lib/config';

const linkClass = ({ isActive }: { isActive: boolean }) =>
  `text-sm font-medium transition-colors ${isActive ? 'text-text-primary' : 'text-text-secondary hover:text-text-primary'}`;

export function Nav() {
  return (
    <header className="sticky top-0 z-30 border-b border-border bg-bg/80 backdrop-blur-md">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-6 py-3.5">
        <Link className="flex items-center gap-2 text-lg font-semibold tracking-tight text-text-primary" to="/">
          <span
            aria-hidden
            className="inline-flex h-7 w-7 items-center justify-center rounded-md bg-gradient-to-br from-[#14b8a6] via-[#2563eb] to-[#7c3aed] text-sm font-bold text-white shadow-[0_4px_12px_-4px_rgba(37,99,235,0.45)]"
          >
            H
          </span>
          {navCopy.brand}
        </Link>

        <nav className="hidden items-center gap-7 md:flex" aria-label="Primary">
          <a className="text-sm font-medium text-text-secondary transition-colors hover:text-text-primary" href="/#features-heading">
            Features
          </a>
          <a className="text-sm font-medium text-text-secondary transition-colors hover:text-text-primary" href="/#how-it-works">
            How it works
          </a>
          <NavLink className={linkClass} to="/pricing">
            {navCopy.pricing}
          </NavLink>
        </nav>

        <div className="flex items-center gap-2">
          <details className="relative md:hidden">
            <summary
              className="list-none rounded-md border border-border bg-bg px-3 py-2 text-sm font-medium text-text-primary [&::-webkit-details-marker]:hidden"
              aria-label={navCopy.menuLabel}
            >
              <span aria-hidden>☰</span>
            </summary>
            <div className="absolute right-0 z-10 mt-2 w-52 rounded-md border border-border bg-bg p-2 shadow-sm">
              <a className="block rounded-md px-3 py-2 text-sm font-medium text-text-primary hover:bg-hover" href="/#features-heading">
                Features
              </a>
              <a className="block rounded-md px-3 py-2 text-sm font-medium text-text-primary hover:bg-hover" href="/#how-it-works">
                How it works
              </a>
              <NavLink className="block rounded-md px-3 py-2 text-sm font-medium text-text-primary hover:bg-hover" to="/pricing">
                {navCopy.pricing}
              </NavLink>
            </div>
          </details>

          <a
            className="rounded-full bg-gradient-to-r from-[#14b8a6] via-[#2563eb] to-[#7c3aed] px-4 py-2 text-sm font-semibold text-white shadow-[0_6px_20px_-8px_rgba(37,99,235,0.5)] transition-all hover:-translate-y-0.5 md:px-5 md:py-2.5"
            href={signupUrl()}
          >
            {navCopy.cta}
          </a>
        </div>
      </div>
    </header>
  );
}
