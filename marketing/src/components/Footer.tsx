import { Link } from 'react-router-dom';

import { footerCopy } from '../content/copy';

export function Footer() {
  const year = new Date().getFullYear();
  return (
    <footer className="border-t border-border bg-sidebar">
      <div className="mx-auto max-w-6xl px-6 py-16">
        <div className="grid grid-cols-2 gap-10 md:grid-cols-4">
          <div className="col-span-2 md:col-span-1">
            <div className="flex items-center gap-2">
              <span
                aria-hidden
                className="inline-flex h-7 w-7 items-center justify-center rounded-md bg-gradient-to-br from-[#14b8a6] via-[#2563eb] to-[#7c3aed] text-sm font-bold text-white shadow-[0_4px_12px_-4px_rgba(37,99,235,0.45)]"
              >
                H
              </span>
              <p className="text-lg font-semibold tracking-tight">HireLoop</p>
            </div>
            <p className="mt-3 max-w-xs text-sm text-text-secondary leading-relaxed">{footerCopy.tagline}</p>
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-text-primary">
              {footerCopy.productHeading}
            </p>
            <ul className="mt-4 space-y-2.5 text-sm">
              <li>
                <Link className="text-text-secondary transition-colors hover:text-text-primary" to="/">
                  {footerCopy.links.home}
                </Link>
              </li>
              <li>
                <a className="text-text-secondary transition-colors hover:text-text-primary" href="/#features-heading">
                  Features
                </a>
              </li>
              <li>
                <a className="text-text-secondary transition-colors hover:text-text-primary" href="/#how-it-works">
                  How it works
                </a>
              </li>
              <li>
                <Link className="text-text-secondary transition-colors hover:text-text-primary" to="/pricing">
                  {footerCopy.links.pricing}
                </Link>
              </li>
            </ul>
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-text-primary">Company</p>
            <ul className="mt-4 space-y-2.5 text-sm">
              <li>
                <a className="text-text-secondary transition-colors hover:text-text-primary" href="mailto:hi@hireloop.com">
                  Contact
                </a>
              </li>
            </ul>
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-text-primary">
              {footerCopy.legalHeading}
            </p>
            <ul className="mt-4 space-y-2.5 text-sm">
              <li>
                <Link className="text-text-secondary transition-colors hover:text-text-primary" to="/terms">
                  {footerCopy.links.terms}
                </Link>
              </li>
              <li>
                <Link className="text-text-secondary transition-colors hover:text-text-primary" to="/privacy">
                  {footerCopy.links.privacy}
                </Link>
              </li>
            </ul>
          </div>
        </div>
        <div className="mt-12 flex flex-col gap-3 border-t border-border pt-6 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-sm text-text-secondary">{footerCopy.copyright(year)}</p>
          <p className="text-sm text-text-secondary">Built for job seekers who ship.</p>
        </div>
      </div>
    </footer>
  );
}
