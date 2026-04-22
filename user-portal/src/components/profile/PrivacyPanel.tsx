import { useState } from 'react';

import { SoftCard } from '../ui/SoftCard';
import { logout } from '../../lib/auth';

function Toggle({
  checked,
  onChange,
}: {
  checked: boolean;
  onChange: (next: boolean) => void;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      className={
        'relative h-6 w-10 rounded-full transition-colors duration-150 motion-reduce:transition-none ' +
        (checked ? 'bg-teal' : 'bg-line-2')
      }
    >
      <span
        aria-hidden
        className={
          'absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition-transform duration-150 motion-reduce:transition-none ' +
          (checked ? 'translate-x-4' : 'translate-x-0.5')
        }
      />
    </button>
  );
}

type Row = {
  id: string;
  title: string;
  body: string;
};

const ROWS: Row[] = [
  {
    id: 'share',
    title: 'Share profile with employers',
    body: "Recruiters at matched companies can see your name + headline (never resume).",
  },
  {
    id: 'contact',
    title: 'Let recruiters cold-contact me',
    body: "We route them through our inbox so your personal email stays private.",
  },
  {
    id: 'benchmarks',
    title: 'Opt into anonymized benchmarks',
    body: 'Share aggregated comp numbers to power market bands. Never identifiable.',
  },
  {
    id: 'partners',
    title: 'Share resume with partner services',
    body: 'e.g. vetted recruiters. Off by default; you pick each one.',
  },
];

export function PrivacyPanel() {
  const [values, setValues] = useState<Record<string, boolean>>({});

  return (
    <div className="space-y-5">
      <SoftCard header="Data sharing" padding="md">
        <ul className="divide-y divide-line">
          {ROWS.map((row) => (
            <li key={row.id} className="flex items-start gap-4 py-3 first:pt-0 last:pb-0">
              <div className="flex-1">
                <div className="text-[14px] font-medium text-ink">{row.title}</div>
                <p className="mt-0.5 text-[12px] text-ink-3">{row.body}</p>
              </div>
              <Toggle
                checked={!!values[row.id]}
                onChange={(next) =>
                  setValues((current) => ({ ...current, [row.id]: next }))
                }
              />
            </li>
          ))}
        </ul>
      </SoftCard>

      <SoftCard header="Account actions" padding="md">
        <div className="flex flex-wrap gap-3">
          <a
            href="/api/v1/profile/export"
            className="rounded-full border border-line-2 bg-white px-4 py-2 text-[13px] text-ink-2 hover:bg-[#faf9f6]"
          >
            Export my data
          </a>
          <button
            type="button"
            onClick={() => {
              if (
                confirm(
                  'This signs you out. Deleting the account is coming soon — contact support@hireloop.xyz to delete now.',
                )
              ) {
                logout();
              }
            }}
            className="rounded-full border border-red-300 bg-white px-4 py-2 text-[13px] text-red-700 hover:bg-red-50"
          >
            Delete account
          </button>
        </div>
      </SoftCard>
    </div>
  );
}
