export type FeatureIconName = 'search' | 'document' | 'rss' | 'layers' | 'chat' | 'handshake';

export type FeatureAccent = 'blue' | 'violet' | 'emerald' | 'amber' | 'rose' | 'teal';

export interface FeatureEntry {
  title: string;
  summary: string;
  icon: FeatureIconName;
  accent: FeatureAccent;
  emoji: string;
}

export const features: FeatureEntry[] = [
  {
    title: 'Job evaluation',
    summary:
      'Paste any job link. Get an A–F grade across 10 dimensions — skills, comp, seniority, red flags — in under 10 seconds.',
    icon: 'search',
    accent: 'blue',
    emoji: '🎯',
  },
  {
    title: 'Résumé tailoring',
    summary:
      'Upload your master résumé once. Every job gets its own ATS-optimized PDF, rewritten to match without inventing experience.',
    icon: 'document',
    accent: 'violet',
    emoji: '✍️',
  },
  {
    title: 'Job scanning',
    summary:
      'Track 15 companies on Greenhouse, Ashby, and Lever. New openings are scored against your profile the moment they post.',
    icon: 'rss',
    accent: 'emerald',
    emoji: '📡',
  },
  {
    title: 'Batch evaluation',
    summary:
      'Drop hundreds of jobs in. Get "12 strong, 23 worth exploring, 165 skip" — sorted, reasoned, ready.',
    icon: 'layers',
    accent: 'amber',
    emoji: '⚡',
  },
  {
    title: 'Interview prep',
    summary:
      'A STAR story bank built from your real experience, plus role-specific questions with answer frameworks.',
    icon: 'chat',
    accent: 'rose',
    emoji: '💬',
  },
  {
    title: 'Negotiation playbooks',
    summary:
      'Market range research, counter-offer scripts, and pushback tactics — ready the day an offer lands.',
    icon: 'handshake',
    accent: 'teal',
    emoji: '🤝',
  },
];
