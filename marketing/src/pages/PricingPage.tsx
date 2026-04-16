import { FAQ } from '../components/FAQ';
import { PricingCard } from '../components/PricingCard';
import { faqPricing } from '../content/faq-pricing';
import { sectionTitles } from '../content/copy';
import { metaDescriptions } from '../content/meta';
import { useDocumentTitle } from '../lib/useDocumentTitle';

export function PricingPage() {
  useDocumentTitle('Pricing — HireLoop', metaDescriptions.pricing);

  return (
    <div className="mx-auto max-w-5xl px-6 py-12">
      <h1 className="text-3xl font-semibold tracking-tight">Pricing</h1>
      <div className="mx-auto mt-8 max-w-md">
        <PricingCard variant="full" />
      </div>
      <FAQ id="faq" title={sectionTitles.faqPricing} items={faqPricing} />
    </div>
  );
}
