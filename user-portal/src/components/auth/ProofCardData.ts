export type MatchRowType = 'ok' | 'warn' | 'miss';

export type MatchRow = {
  type: MatchRowType;
  text: string;
  cite: string;
};

export type Bar = {
  label: string;
  value: number; // 0–100
  gradient: string;
};

export type LiveEvaluationCard = {
  id: string;
  tier: 'strong' | 'okay' | 'weak';
  tierLabel: string;
  score: number;
  title: string;
  meta: string;
  bars: Bar[];
  matches: MatchRow[];
};

export const LIVE_EVAL_CARDS: LiveEvaluationCard[] = [
  {
    id: 'strong',
    tier: 'strong',
    tierLabel: 'Strong match',
    score: 87,
    title: 'Senior Product Designer',
    meta: 'Acme Corp · Remote (US)',
    bars: [
      { label: 'Experience', value: 92, gradient: 'linear-gradient(90deg,#14b8a6,#2563eb)' },
      { label: 'Scope & seniority', value: 88, gradient: 'linear-gradient(90deg,#2563eb,#7c3aed)' },
      { label: 'Requirements', value: 74, gradient: 'linear-gradient(90deg,#2563eb,#14b8a6)' },
    ],
    matches: [
      { type: 'ok', text: 'Led design system adoption across 4 squads', cite: 'Resume · Stripe, 2022' },
      { type: 'ok', text: 'Shipped Figma token pipeline used by 30+ PMs', cite: 'Resume · Stripe, 2023' },
      { type: 'warn', text: 'Only 2 yrs management vs. 3+ preferred', cite: 'Gap · coachable' },
    ],
  },
  {
    id: 'stretch',
    tier: 'okay',
    tierLabel: 'Stretch role',
    score: 64,
    title: 'Staff Product Manager, Growth',
    meta: 'Northwind · Hybrid (NYC)',
    bars: [
      { label: 'Experience', value: 72, gradient: 'linear-gradient(90deg,#d97706,#2563eb)' },
      { label: 'Scope & seniority', value: 58, gradient: 'linear-gradient(90deg,#d97706,#7c3aed)' },
      { label: 'Requirements', value: 61, gradient: 'linear-gradient(90deg,#f59e0b,#d97706)' },
    ],
    matches: [
      { type: 'ok', text: 'A/B tested activation funnel: +18% WAU', cite: 'Resume · Linear, 2024' },
      { type: 'warn', text: 'Growth PM title new — adjacent PLG work counts', cite: 'Reframe suggested' },
      { type: 'miss', text: 'No SQL/Amplitude bullet — add one line', cite: 'Quick fix' },
    ],
  },
  {
    id: 'long-shot',
    tier: 'weak',
    tierLabel: 'Long shot',
    score: 38,
    title: 'Director of Engineering',
    meta: 'Helios Labs · On-site (SF)',
    bars: [
      { label: 'Experience', value: 44, gradient: 'linear-gradient(90deg,#c2410c,#d97706)' },
      { label: 'Scope & seniority', value: 32, gradient: 'linear-gradient(90deg,#c2410c,#9a9894)' },
      { label: 'Requirements', value: 40, gradient: 'linear-gradient(90deg,#c2410c,#d97706)' },
    ],
    matches: [
      { type: 'ok', text: '3 yrs IC engineering at a high-growth startup', cite: 'Resume · Ramp, 2019–22' },
      { type: 'miss', text: 'No direct reports listed — role needs 15+', cite: 'Likely blocker' },
      { type: 'miss', text: 'Infra ownership (Kafka/K8s) not on resume', cite: 'Role requires' },
    ],
  },
];
