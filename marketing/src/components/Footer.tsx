import { Link } from 'react-router-dom';

import { footerCopy } from '../content/copy';

export function Footer() {
  const year = new Date().getFullYear();
  return (
    <footer className="border-t border-border py-12">
      <div className="mx-auto max-w-6xl px-6">
        <div className="grid grid-cols-1 gap-10 md:grid-cols-3">
          <div>
            <p className="text-lg font-semibold">HireLoop</p>
            <p className="mt-2 text-sm text-text-secondary leading-relaxed">{footerCopy.tagline}</p>
          </div>
          <div>
            <p className="text-xs font-medium uppercase tracking-wider text-text-secondary">{footerCopy.productHeading}</p>
            <ul className="mt-3 space-y-2 text-sm">
              <li>
                <Link className="text-text-primary hover:underline" to="/">
                  {footerCopy.links.home}
                </Link>
              </li>
              <li>
                <Link className="text-text-primary hover:underline" to="/pricing">
                  {footerCopy.links.pricing}
                </Link>
              </li>
            </ul>
          </div>
          <div>
            <p className="text-xs font-medium uppercase tracking-wider text-text-secondary">{footerCopy.legalHeading}</p>
            <ul className="mt-3 space-y-2 text-sm">
              <li>
                <Link className="text-text-primary hover:underline" to="/terms">
                  {footerCopy.links.terms}
                </Link>
              </li>
              <li>
                <Link className="text-text-primary hover:underline" to="/privacy">
                  {footerCopy.links.privacy}
                </Link>
              </li>
            </ul>
          </div>
        </div>
        <p className="mt-10 text-sm text-text-secondary">{footerCopy.copyright(year)}</p>
      </div>
    </footer>
  );
}
