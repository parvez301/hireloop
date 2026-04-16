export interface FaqItem {
  q: string;
  a: string;
}

export const faqHome: FaqItem[] = [
  {
    q: 'What happens during the free trial?',
    a: 'Full access to everything — evaluations, résumé tailoring, scanning, batch, interview prep, negotiation. No credit card required to start. When the 3 days end, you\'ll see a paywall until you subscribe.',
  },
  {
    q: 'Do you train AI on my data?',
    a: 'No. Your résumé, conversations, and job evaluations are never used to train or fine-tune any AI model. We use API providers (Anthropic, Google) with zero-retention settings enabled.',
  },
  {
    q: 'What job boards does scanning support?',
    a: 'Greenhouse, Ashby, and Lever — which covers most modern tech and mid-market companies. We\'re adding more boards as users request them.',
  },
  {
    q: 'Can I cancel anytime?',
    a: 'Yes. Cancellation is one click in the Stripe customer portal. You keep access until the end of your current billing period, then we stop charging.',
  },
  {
    q: 'What happens to my data if I delete my account?',
    a: 'All personal data (résumé content, job evaluations, conversations) is deleted within 30 days. Aggregate, anonymized job listings stay in our shared scanning pool so future users benefit from dedup.',
  },
];
