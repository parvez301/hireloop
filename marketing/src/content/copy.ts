export const navCopy = {
  brand: 'HireLoop',
  pricing: 'Pricing',
  cta: 'Start free trial',
  menuLabel: 'Open menu',
} as const;

export const footerCopy = {
  tagline: 'AI-powered job search.',
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
  eyebrow: 'Put your job search on autopilot',
  headline: 'Spend your job hunt on interviews, not applications.',
  subhead:
    'HireLoop scans hundreds of openings, ranks them against your actual experience, and hands you a tailored résumé for the ones worth applying to.',
  primaryCta: 'Start 3-day free trial',
  secondaryCta: 'How it works →',
  micro: '3 days free · $4.99/mo · cancel anytime',
} as const;

export const pricingPreviewCopy = {
  headline: 'One plan. $4.99/month. Cancel anytime.',
  body: 'Everything the agent does, no usage caps, 3-day free trial.',
  link: 'See full pricing →',
} as const;

export const finalCtaCopy = {
  headline: 'Stop applying. Start interviewing.',
  button: 'Start 3-day free trial',
  micro: 'No credit card to start.',
} as const;

export const howItWorksSteps: { title: string; body: string }[] = [
  {
    title: 'Upload your master résumé.',
    body: 'One time. HireLoop extracts your experience into structured data.',
  },
  {
    title: 'Paste a job link or set up scanning.',
    body: 'Greenhouse, Ashby, Lever, or any URL.',
  },
  {
    title: 'Ask for what you need.',
    body: '"Evaluate this job." "Tailor my résumé." "Prep me for the interview." One chat. Six tools.',
  },
];

export const sectionTitles = {
  features: 'Everything you need for a focused search',
  howItWorks: 'How it works',
  faqHome: 'Questions',
  faqPricing: 'Questions',
} as const;
