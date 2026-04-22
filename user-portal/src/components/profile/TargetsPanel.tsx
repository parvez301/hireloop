import { useState } from 'react';

import { ChipSet } from '../ui/Chip';
import { GradientButton } from '../ui/GradientButton';
import { SegmentedControl } from '../ui/SegmentedControl';
import { SoftCard } from '../ui/SoftCard';
import type { Profile } from '../../lib/api';

type Props = {
  profile: Profile;
  saving: boolean;
  onSave: (patch: Partial<Profile>) => void;
};

type WorkArrangement = 'remote' | 'hybrid' | 'onsite';

export function TargetsPanel({ profile, saving, onSave }: Props) {
  const [roles, setRoles] = useState<string[]>(profile.target_roles ?? []);
  const [locations, setLocations] = useState<string[]>(profile.target_locations ?? []);
  const [industries, setIndustries] = useState<string[]>(
    profile.preferred_industries ?? [],
  );
  const [arrangement, setArrangement] = useState<WorkArrangement>(
    (profile.work_arrangement as WorkArrangement) || 'remote',
  );
  const [salary, setSalary] = useState<number>(profile.min_salary ?? 150_000);

  return (
    <div className="space-y-5">
      <SoftCard header="Target roles" padding="md">
        <ChipSet values={roles} onChange={setRoles} addLabel="+ Add role" />
        <p className="mt-3 text-[12px] text-ink-3">
          Grading algorithm uses these as the primary fit signal.
        </p>
      </SoftCard>

      <SoftCard header="Locations · work arrangement" padding="md">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <div>
            <div className="mb-2 text-[12px] font-medium text-ink-2">Locations</div>
            <ChipSet values={locations} onChange={setLocations} addLabel="+ Add location" />
          </div>
          <div>
            <div className="mb-2 text-[12px] font-medium text-ink-2">Work arrangement</div>
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
      </SoftCard>

      <div className="flex justify-end">
        <GradientButton
          disabled={saving}
          onClick={() =>
            onSave({
              target_roles: roles,
              target_locations: locations,
              preferred_industries: industries,
              work_arrangement: arrangement,
              min_salary: salary,
            })
          }
        >
          {saving ? 'Saving…' : 'Save targets'}
        </GradientButton>
      </div>
    </div>
  );
}
