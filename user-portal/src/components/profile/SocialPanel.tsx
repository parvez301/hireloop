import { useState } from 'react';
import { Globe, Link2, SquareCode } from 'lucide-react';

import { ScoreRing } from '../ui/ScoreRing';
import { SoftCard } from '../ui/SoftCard';
import { TextField } from '../ui/InputField';
import { GradientButton } from '../ui/GradientButton';
import type { Profile } from '../../lib/api';

type Props = {
  profile: Profile;
  saving: boolean;
  onSave: (patch: Partial<Profile>) => void;
};

type LinkId = 'linkedin' | 'github' | 'portfolio';

type Row = {
  id: LinkId;
  title: string;
  reason: string;
  icon: typeof Globe;
};

const ROWS: Row[] = [
  {
    id: 'linkedin',
    title: 'LinkedIn',
    reason: 'Boosts the grade for recruiter-listed roles.',
    icon: Link2,
  },
  {
    id: 'github',
    title: 'GitHub',
    reason: 'Unlocks "show me your work" proof on tailored CVs.',
    icon: SquareCode,
  },
  {
    id: 'portfolio',
    title: 'Portfolio',
    reason: 'Interviewers cite this more than any other link.',
    icon: Globe,
  },
];

export function SocialPanel({ profile, saving, onSave }: Props) {
  const [linkedin, setLinkedin] = useState(profile.linkedin_url ?? '');
  const [github, setGithub] = useState(profile.github_url ?? '');
  const [portfolio, setPortfolio] = useState(profile.portfolio_url ?? '');

  const filled = [linkedin, github, portfolio].filter((value) => value.trim().length > 0).length;
  const score = Math.round((filled / 3) * 100);

  return (
    <div className="space-y-5">
      <SoftCard header="Social score" padding="md">
        <div className="flex items-center gap-6">
          <ScoreRing
            target={score}
            size={120}
            eyebrow="SOCIAL"
            subline={`${filled} of 3 connected`}
            animate
          />
          <div className="text-[13px] text-ink-3">
            {filled === 3
              ? 'All three external proofs connected. Grades get a small boost on relevant roles.'
              : 'Add missing links to get extra signal on recruiter-listed roles and tailored CVs.'}
          </div>
        </div>
      </SoftCard>

      <SoftCard header="External profiles" padding="md">
        <div className="divide-y divide-line">
          {ROWS.map((row) => {
            const Icon = row.icon;
            const value =
              row.id === 'linkedin'
                ? linkedin
                : row.id === 'github'
                  ? github
                  : portfolio;
            const setValue =
              row.id === 'linkedin'
                ? setLinkedin
                : row.id === 'github'
                  ? setGithub
                  : setPortfolio;
            const connected = value.trim().length > 0;
            return (
              <div
                key={row.id}
                className="grid grid-cols-[auto_1fr_auto] items-center gap-4 py-4 first:pt-0 last:pb-0"
              >
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-card text-ink-2">
                  <Icon size={18} strokeWidth={1.6} />
                </div>
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-[14px] font-medium text-ink">{row.title}</span>
                    <span
                      className={
                        'rounded-full px-2 py-0.5 text-[10.5px] font-medium ' +
                        (connected
                          ? 'bg-teal/10 text-teal'
                          : 'bg-card text-ink-3')
                      }
                    >
                      {connected ? 'Connected' : 'Not set'}
                    </span>
                  </div>
                  <p className="mt-0.5 text-[12px] text-ink-3">{row.reason}</p>
                  <div className="mt-2">
                    <TextField
                      label=""
                      value={value}
                      onChange={(event) => setValue(event.target.value)}
                      placeholder={`https://${row.id === 'linkedin' ? 'linkedin.com/in/…' : row.id === 'github' ? 'github.com/…' : 'your.site'}`}
                    />
                  </div>
                </div>
              </div>
            );
          })}
        </div>
        <div className="mt-4 flex justify-end">
          <GradientButton
            disabled={saving}
            onClick={() =>
              onSave({
                linkedin_url: linkedin || null,
                github_url: github || null,
                portfolio_url: portfolio || null,
              })
            }
          >
            {saving ? 'Saving…' : 'Save links'}
          </GradientButton>
        </div>
      </SoftCard>
    </div>
  );
}
