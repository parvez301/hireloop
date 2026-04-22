import { useState } from 'react';
import {
  BriefcaseBusiness,
  CircleCheckBig,
  Inbox,
  LayoutDashboard,
  Search,
  Sparkles,
} from 'lucide-react';

import { AppHeader } from '../components/ui/AppHeader';
import { Chip, ChipSet } from '../components/ui/Chip';
import { EmptyState } from '../components/ui/EmptyState';
import { GradeBar } from '../components/ui/GradeBar';
import { GradientBadge } from '../components/ui/GradientBadge';
import { GradientButton } from '../components/ui/GradientButton';
import { Kanban } from '../components/ui/Kanban';
import { ScoreRing } from '../components/ui/ScoreRing';
import { SegmentedControl } from '../components/ui/SegmentedControl';
import { Sidebar, type SidebarItem } from '../components/ui/Sidebar';
import { SoftCard } from '../components/ui/SoftCard';
import { Sparkline } from '../components/ui/Sparkline';
import {
  SelectField,
  TextField,
  TextareaField,
} from '../components/ui/InputField';

const SIDEBAR_ITEMS: SidebarItem[] = [
  { id: 'dashboard', label: 'Dashboard', href: '#', icon: LayoutDashboard },
  { id: 'pipeline', label: 'Pipeline', href: '#', icon: BriefcaseBusiness, counter: 12 },
  { id: 'scans', label: 'Scans', href: '#', icon: Search, counter: 3 },
  { id: 'stories', label: 'Story bank', href: '#', icon: Sparkles },
  { id: 'inbox', label: 'Inbox', href: '#', icon: Inbox, counter: '!' },
];

type Stage = 'saved' | 'applied' | 'phone' | 'onsite' | 'offer';

export default function DevPrimitivesPage() {
  const [roles, setRoles] = useState<string[]>(['Senior Backend Engineer']);
  const [arrangement, setArrangement] = useState<'remote' | 'hybrid' | 'onsite'>(
    'remote',
  );
  const [items, setItems] = useState([
    { id: 'a', stage: 'saved' as Stage, title: 'Acme — Senior Backend' },
    { id: 'b', stage: 'applied' as Stage, title: 'Stripe — Platform' },
    { id: 'c', stage: 'phone' as Stage, title: 'Figma — SRE' },
  ]);

  return (
    <div className="min-h-screen bg-bg text-ink [font-feature-settings:'ss01','cv11']">
      <AppHeader
        right={
          <div className="flex items-center gap-2 text-[12px] text-ink-3">
            dev · primitives
          </div>
        }
      />
      <div className="mx-auto flex max-w-6xl gap-8 px-6 py-8">
        <Sidebar items={SIDEBAR_ITEMS} activeId="dashboard" />

        <main className="flex-1 space-y-8">
          <section>
            <h1 className="text-[28px] font-semibold tracking-tight">UI primitives</h1>
            <p className="mt-1 text-[13px] text-ink-3">
              A quick render of each primitive for sanity checks. Not shipped to
              production routes.
            </p>
          </section>

          <SoftCard header="SoftCard · GradientButton · GradientBadge">
            <div className="flex flex-wrap items-center gap-6">
              <GradientButton>Primary CTA</GradientButton>
              <GradientButton disabled>Disabled</GradientButton>
              <GradientButton shape="card">Card-shaped CTA</GradientButton>
              <GradientBadge grade="A" score={94} />
              <GradientBadge grade="B+" score={75} />
              <GradientBadge grade="C" score={55} />
            </div>
          </SoftCard>

          <SoftCard header="ChipSet · SegmentedControl · InputField">
            <div className="space-y-4">
              <div>
                <div className="mb-2 text-[12px] font-medium text-ink-2">
                  Target roles
                </div>
                <ChipSet
                  values={roles}
                  suggestions={['Staff Engineer', 'Platform Lead']}
                  onChange={setRoles}
                  addLabel="+ Add role"
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
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <TextField label="Full name" placeholder="Jane Doe" />
                <TextField
                  label="Email"
                  type="email"
                  placeholder="jane@example.com"
                  helper="We never show this publicly."
                />
                <SelectField label="Timezone" defaultValue="ET">
                  <option value="PT">Pacific</option>
                  <option value="ET">Eastern</option>
                </SelectField>
                <TextField label="Salary floor" type="number" error="Must be ≥ 40000" />
              </div>
              <TextareaField
                label="Bio"
                rows={3}
                placeholder="One sentence about what you're looking for…"
              />
            </div>
          </SoftCard>

          <SoftCard header="GradeBar · ScoreRing · Sparkline">
            <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
              <div className="space-y-3">
                <GradeBar value={82} label="Experience match" />
                <GradeBar value={68} label="Scope & seniority" />
                <GradeBar value={54} label="Specific requirements" />
                <div className="flex items-center gap-4">
                  <GradeBar value={74} variant="inline" />
                  <Sparkline values={[3, 5, 2, 8, 6, 9, 12]} label="Last 7 days" />
                </div>
              </div>
              <div className="flex justify-center">
                <ScoreRing target={76} subline="and climbing" />
              </div>
            </div>
          </SoftCard>

          <SoftCard header="Kanban">
            <Kanban<Stage, (typeof items)[number]>
              columns={[
                { id: 'saved', label: 'Saved' },
                { id: 'applied', label: 'Applied' },
                { id: 'phone', label: 'Phone' },
                { id: 'onsite', label: 'Onsite' },
                { id: 'offer', label: 'Offer' },
              ]}
              items={items}
              onStageChange={(id, stage) =>
                setItems((previous) =>
                  previous.map((item) =>
                    item.id === id ? { ...item, stage } : item,
                  ),
                )
              }
              renderCard={(item) => (
                <div>
                  <div className="text-[14px] font-medium text-ink">
                    {item.title}
                  </div>
                  <div className="mt-0.5 text-[11px] text-ink-3">drag me</div>
                </div>
              )}
            />
          </SoftCard>

          <SoftCard header="EmptyState · Chip variants">
            <div className="space-y-5">
              <div className="flex flex-wrap gap-2">
                <Chip label="On" variant="on" onRemove={() => {}} />
                <Chip label="Add" variant="add" />
                <Chip label="Suggested" variant="suggest" />
              </div>
              <EmptyState
                title="Nothing here yet"
                body="Once your scans run you'll see graded jobs appear."
                cta={
                  <GradientButton>
                    <CircleCheckBig size={16} className="mr-1.5" />
                    Run a scan
                  </GradientButton>
                }
              />
            </div>
          </SoftCard>
        </main>
      </div>
    </div>
  );
}
