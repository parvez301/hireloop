import type { FaqItem } from './faq-home';

export const faqPricing: FaqItem[] = [
  {
    q: 'Why $4.99?',
    a: 'Priced to break even on typical usage. Heavy users cost us more; light users cost us less. We\'d rather have you here than churn on price.',
  },
  {
    q: 'Is there an annual plan?',
    a: 'Not yet. Monthly only while we\'re learning what usage looks like.',
  },
  {
    q: 'What counts as "unlimited"?',
    a: 'All six features have no per-action caps during a subscription. We reserve the right to rate-limit abusive usage (thousands of requests per hour) but you\'ll never hit that in normal job-seeking.',
  },
  {
    q: 'Do you offer refunds?',
    a: 'If something broke on our end in your first 30 days, email support@hireloop.xyz and we\'ll refund the month. Outside that, cancellation stops future charges.',
  },
  {
    q: 'I don\'t want to pay with Stripe.',
    a: 'Stripe is the only payment processor we support. They handle card data; we don\'t store it.',
  },
];
