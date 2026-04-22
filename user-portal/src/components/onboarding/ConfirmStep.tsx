import { useState } from 'react';

import { ChipSet } from '../ui/Chip';
import { GradientButton } from '../ui/GradientButton';
import { SegmentedControl } from '../ui/SegmentedControl';
import { SoftCard } from '../ui/SoftCard';
import { TextField } from '../ui/InputField';
import { api, type Profile } from '../../lib/api';

type WorkArrangement = 'remote' | 'hybrid' | 'onsite';

type Props = {
  initial: Profile;
  onSaved: () => void;
};

export function ConfirmStep({ initial, onSaved }: Props) {
  const [targetRoles, setTargetRoles] = useState<string[]>(initial.target_roles ?? []);
  const [locations, setLocations] = useState<string[]>(initial.target_locations ?? []);
  const [industries, setIndustries] = useState<string[]>(initial.preferred_industries ?? []);
  const [salary, setSalary] = useState<number>(initial.min_salary ?? 150_000);
  const [arrangement, setArrangement] = useState<WorkArrangement>(
    (initial.work_arrangement as WorkArrangement) || 'remote',
  );
  const [linkedin, setLinkedin] = useState(initial.linkedin_url ?? '');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function save(skipOptional: boolean) {
    setBusy(true);
    setError(null);
    try {
      await api.profile.update({
        target_roles: targetRoles,
        target_locations: skipOptional ? null : locations,
        preferred_industries: skipOptional ? null : industries,
        min_salary: skipOptional ? null : salary,
        work_arrangement: skipOptional ? null : arrangement,
        linkedin_url: linkedin || null,
      });
      onSaved();
    } catch (caught) {
      setError((caught as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid grid-cols-1 gap-10 lg:grid-cols-12">
      <div className="space-y-4 lg:col-span-7">
        <SoftCard header="Identity · from your resume" padding="md">
          <div className="flex items-start gap-4">
            <div
              aria-hidden
              className="flex h-12 w-12 flex-none items-center justify-center rounded-xl text-[14px] font-semibold text-white"
              style={{
                backgroundImage:
                  'linear-gradient(135deg, #14b8a6 0%, #2563eb 45%, #7c3aed 100%)',
              }}
            >
              {(initial.linkedin_url ?? initial.target_roles?.[0] ?? 'HL')
                .replace(/[^A-Za-z]/g, '')
                .slice(0, 2)
                .toUpperCase()}
            </div>
            <div className="flex-1 space-y-2">
              <TextField
                label="LinkedIn URL"
                placeholder="https://linkedin.com/in/…"
                value={linkedin}
                onChange={(event) => setLinkedin(event.target.value)}
              />
            </div>
          </div>
        </SoftCard>

        <SoftCard header="Target roles · required" padding="md">
          <ChipSet
            values={targetRoles}
            suggestions={[]}
            onChange={setTargetRoles}
            addLabel="+ Add role"
          />
          <p className="mt-3 text-[12px] text-ink-3">
            We grade every job against these and demote ones that don't match.
          </p>
        </SoftCard>

        <SoftCard header="Locations · work arrangement" padding="md">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div>
              <div className="mb-2 text-[12px] font-medium text-ink-2">Locations</div>
              <ChipSet
                values={locations}
                onChange={setLocations}
                addLabel="+ Add location"
              />
            </div>
            <div>
              <div className="mb-2 text-[12px] font-medium text-ink-2">
                Work arrangement
              </div>
              <SegmentedControl
                options={[
                  { value: 'remote', label: 'Remote only' },
                  { value: 'hybrid', label: 'Hybrid OK' },
                  { value: 'onsite', label: 'On-site OK' },
                ]}
                value={arrangement}
                onChange={setArrangement}
              />
            </div>
          </div>
        </SoftCard>

        <SoftCard header="Preferred industries" padding="md">
          <ChipSet
            values={industries}
            suggestions={['Consumer', 'Healthcare', 'Fintech', 'Developer tools']}
            onChange={setIndustries}
            addLabel="+ Add industry"
          />
        </SoftCard>

        <SoftCard header="Minimum salary" padding="md">
          <div className="flex items-baseline gap-3">
            <span className="text-[28px] font-semibold tabular-nums tracking-[-0.02em] text-ink">
              ${salary.toLocaleString()}
            </span>
          </div>
          <input
            type="range"
            min={60_000}
            max={400_000}
            step={5_000}
            value={salary}
            onChange={(event) => setSalary(Number(event.target.value))}
            className="mt-3 w-full"
          />
          <p className="mt-3 text-[12px] text-ink-3">
            Jobs below your floor get demoted in the grade.
          </p>
        </SoftCard>

        {error && (
          <p
            role="alert"
            className="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-[13px] text-red-800"
          >
            {error}
          </p>
        )}

        <div className="flex items-center justify-between pt-2">
          <button
            type="button"
            onClick={() => void save(true)}
            disabled={busy}
            className="text-[13px] text-ink-3 underline decoration-dotted underline-offset-4 hover:text-ink-2"
          >
            Skip — I'll do this in Settings
          </button>
          <GradientButton
            disabled={busy || targetRoles.length === 0}
            onClick={() => void save(false)}
          >
            {busy ? 'Saving…' : "Looks right — show my first grade →"}
          </GradientButton>
        </div>
      </div>

      <aside className="lg:col-span-5">
        <SoftCard header="What this unlocks" padding="md">
          <ol className="space-y-3 text-[14px] text-ink-2">
            {[
              'Grade engine knows your floor.',
              'Scans go wider than keyword match.',
              'Negotiation coach has numbers.',
            ].map((item, index) => (
              <li key={item} className="flex gap-3">
                <span className="flex h-5 w-5 flex-none items-center justify-center rounded-md bg-ink text-[11px] font-semibold text-white">
                  {index + 1}
                </span>
                {item}
              </li>
            ))}
          </ol>
        </SoftCard>
        <div className="mt-4 rounded-2xl border border-dashed border-line-2 p-5 text-[12px] text-ink-3">
          None of this is shown to employers. It's only used to filter and grade
          jobs on your side.
        </div>
      </aside>
    </div>
  );
}
