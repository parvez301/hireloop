import { useState } from 'react';

import { SoftCard } from '../ui/SoftCard';
import { TextField } from '../ui/InputField';
import { GradientButton } from '../ui/GradientButton';
import { getUserEmail } from '../../lib/auth';
import type { Profile } from '../../lib/api';

type Props = {
  profile: Profile;
  saving: boolean;
  onSave: (patch: Partial<Profile>) => void;
};

export function BasicsPanel({ profile, saving, onSave }: Props) {
  const [linkedin, setLinkedin] = useState(profile.linkedin_url ?? '');
  const email = getUserEmail() ?? '—';
  const initials = (email.split('@')[0] ?? '??').slice(0, 2).toUpperCase();

  return (
    <SoftCard header="Basics" padding="md">
      <div className="grid grid-cols-[220px_1fr] gap-6">
        <div className="flex flex-col items-center gap-2">
          <div
            aria-hidden
            className="flex h-20 w-20 items-center justify-center rounded-2xl text-[20px] font-semibold text-white"
            style={{
              backgroundImage:
                'linear-gradient(135deg, #14b8a6 0%, #2563eb 45%, #7c3aed 100%)',
            }}
          >
            {initials}
          </div>
          <span className="text-[11px] text-ink-3">Avatar is derived from your email.</span>
        </div>
        <div className="space-y-3">
          <TextField
            label="Email"
            value={email}
            disabled
            helper="Change the account email from Security (coming soon)."
          />
          <TextField
            label="LinkedIn URL"
            value={linkedin}
            onChange={(event) => setLinkedin(event.target.value)}
            placeholder="https://linkedin.com/in/…"
          />
          <div className="pt-1">
            <GradientButton
              disabled={saving}
              onClick={() => onSave({ linkedin_url: linkedin || null })}
            >
              {saving ? 'Saving…' : 'Save basics'}
            </GradientButton>
          </div>
        </div>
      </div>
    </SoftCard>
  );
}
