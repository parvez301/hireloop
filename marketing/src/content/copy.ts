export const navCopy = {
  brand: 'HireLoop',
  pricing: 'Pricing',
  cta: 'Start free trial',
  menuLabel: 'Open menu',
} as const;

export const footerCopy = {
  tagline: 'Apply to fewer jobs. Land better ones.',
  productHeading: 'Product',
  legalHeading: 'Legal',
  copyright: (year: number) => `© ${year} HireLoop`,
  links: {
    home: 'Home',
    pricing: 'Pricing',
    terms: 'Terms',
    privacy: 'Privacy',
  },
} as const;

export const heroCopy = {
  eyebrow: 'Grade any job in under 10 seconds',
  headline: 'Apply to 5 jobs. Skip the other 495. Land the one.',
  subhead:
    'HireLoop reads every new opening, scores it against your real experience, and hands you a tailored résumé for the ~5% worth your time. You apply with signal, not spray.',
  primaryCta: 'Start free — 3 days, no card',
  secondaryCta: 'How it works →',
  micro: '3 days free · $4.99/mo · cancel anytime',
} as const;

export const pricingPreviewCopy = {
  headline: '$4.99/month. One plan. Every tool.',
  body: 'Unlimited scans, unlimited résumés, unlimited interview prep. 3-day trial, no card.',
  link: 'See full pricing →',
} as const;

export const finalCtaCopy = {
  headline: 'Your next interview is in the queue. You just haven\u2019t seen it yet.',
  button: 'Start free — 3 days, no card',
  micro: '3 days free. No card. Cancel in two clicks.',
} as const;

export const howItWorksSteps: { title: string; body: string }[] = [
  {
    title: 'Feed it your career, once.',
    body: 'One résumé upload. HireLoop parses your real experience into structured signal — not keywords.',
  },
  {
    title: 'Point it at the openings that matter.',
    body: 'Greenhouse, Ashby, Lever, LinkedIn, or any URL. Set it and walk away.',
  },
  {
    title: 'Ask. It does the work.',
    body: '"Evaluate this job." "Tailor my résumé." "Prep me for the interview." One chat. Six tools.',
  },
];

export const sectionTitles = {
  features: 'Every tool. One agent. No tabs.',
  howItWorks: 'How it works',
  faqHome: 'Questions',
  faqPricing: 'Questions',
} as const;
