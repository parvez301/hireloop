import { pricingPreviewCopy } from '../content/copy';
import { signupUrl } from '../lib/config';

const includedFull = [
  'Unlimited job evaluations',
  'Tailored résumé PDFs',
  'Job scanning (Greenhouse, Ashby, Lever)',
  'Batch evaluation of hundreds of jobs at once',
  'Interview prep + STAR story bank',
  'Negotiation playbooks',
] as const;

interface PricingCardProps {
  variant: 'full' | 'compact';
}

export function PricingCard({ variant }: PricingCardProps) {
  if (variant === 'compact') {
    return (
      <div className="bg-card border border-border rounded-lg p-6 text-center">
        <p className="text-lg font-semibold text-text-primary">{pricingPreviewCopy.headline}</p>
        <p className="mt-2 text-base text-text-secondary leading-relaxed">{pricingPreviewCopy.body}</p>
        <a
          className="mt-6 inline-flex w-full items-center justify-center bg-accent text-white px-5 py-2.5 rounded-md font-medium transition-opacity hover:opacity-90"
          href={signupUrl()}
        >
          Start 3-day free trial
        </a>
      </div>
    );
  }

  return (
    <div className="bg-card border border-border rounded-lg p-8">
      <p className="text-xs font-medium uppercase tracking-wider text-text-secondary">PRO</p>
      <p className="mt-4 text-4xl font-semibold tracking-tight">$4.99/mo</p>
      <a
        className="mt-6 flex w-full items-center justify-center bg-accent text-white px-5 py-2.5 rounded-md font-medium transition-opacity hover:opacity-90"
        href={signupUrl()}
      >
        Start 3-day free trial
      </a>
      <ul className="mt-8 space-y-3 text-left text-base text-text-secondary leading-relaxed">
        {includedFull.map((item) => (
          <li key={item} className="flex gap-2">
            <span className="text-accent" aria-hidden>
              ✓
            </span>
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
