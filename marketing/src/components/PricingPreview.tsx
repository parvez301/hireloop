import { Link } from 'react-router-dom';

import { pricingPreviewCopy } from '../content/copy';
import { PricingCard } from './PricingCard';

export function PricingPreview() {
  return (
    <section className="py-20 md:py-28" aria-labelledby="pricing-preview-heading">
      <div className="mx-auto max-w-6xl px-6">
        <div className="text-center">
          <h2
            className="text-4xl font-black leading-[1.05] tracking-tight md:text-6xl lg:text-7xl"
            id="pricing-preview-heading"
          >
            <span className="text-text-primary">One plan. </span>
            <span className="bg-gradient-to-br from-[#14b8a6] via-[#2563eb] to-[#7c3aed] bg-clip-text text-transparent">
              $4.99/month.
            </span>
          </h2>
          <p className="mx-auto mt-6 max-w-xl text-lg text-text-secondary leading-relaxed md:text-xl">
            {pricingPreviewCopy.body}
          </p>
        </div>
        <div className="mx-auto mt-12 max-w-md">
          <PricingCard variant="compact" />
          <div className="mt-6 text-center">
            <Link className="font-medium text-accent transition-opacity hover:opacity-80" to="/pricing">
              {pricingPreviewCopy.link}
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}
