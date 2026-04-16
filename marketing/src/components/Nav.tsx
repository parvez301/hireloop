import { Link, NavLink } from 'react-router-dom';

import { navCopy } from '../content/copy';
import { signupUrl } from '../lib/config';

const linkClass = ({ isActive }: { isActive: boolean }) =>
  `text-sm font-medium transition-colors ${isActive ? 'text-text-primary' : 'text-text-secondary hover:text-text-primary'}`;

export function Nav() {
  return (
    <header className="border-b border-border">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-6 py-4">
        <Link className="text-lg font-semibold text-text-primary" to="/">
          {navCopy.brand}
        </Link>

        <nav className="hidden items-center gap-6 md:flex" aria-label="Primary">
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
            <div className="absolute right-0 z-10 mt-2 w-48 rounded-md border border-border bg-bg p-2 shadow-sm">
              <NavLink className="block rounded-md px-3 py-2 text-sm font-medium text-text-primary hover:bg-hover" to="/pricing">
                {navCopy.pricing}
              </NavLink>
            </div>
          </details>

          <a
            className="bg-accent text-white px-4 py-2 rounded-md text-sm font-medium transition-opacity hover:opacity-90 md:px-5 md:py-2.5"
            href={signupUrl()}
          >
            {navCopy.cta}
          </a>
        </div>
      </div>
    </header>
  );
}
