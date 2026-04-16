import { Link } from 'react-router-dom';

import { pricingPreviewCopy } from '../content/copy';
import { PricingCard } from './PricingCard';

export function PricingPreview() {
  return (
    <section className="py-12" aria-labelledby="pricing-preview-heading">
      <h2 className="text-3xl font-semibold tracking-tight" id="pricing-preview-heading">
        Pricing
      </h2>
      <div className="mx-auto mt-8 max-w-md">
        <PricingCard variant="compact" />
        <div className="mt-6 text-center">
          <Link className="font-medium text-accent transition-opacity hover:opacity-80" to="/pricing">
            {pricingPreviewCopy.link}
          </Link>
        </div>
      </div>
    </section>
  );
}
