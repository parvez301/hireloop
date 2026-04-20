import { FAQ } from '../components/FAQ';
import { PricingCard } from '../components/PricingCard';
import { faqPricing } from '../content/faq-pricing';
import { sectionTitles } from '../content/copy';
import { metaDescriptions } from '../content/meta';
import { useDocumentTitle } from '../lib/useDocumentTitle';

export function PricingPage() {
  useDocumentTitle('Pricing — HireLoop', metaDescriptions.pricing);

  return (
    <>
      <section className="border-b border-border py-20 md:py-24">
        <div className="mx-auto max-w-3xl px-6 text-center">
          <h1 className="text-4xl font-bold tracking-tight md:text-5xl">Pricing</h1>
          <p className="mt-4 text-lg text-text-secondary leading-relaxed">
            One plan. Everything HireLoop does, no usage caps, 3-day free trial.
          </p>
        </div>
        <div className="mx-auto mt-12 max-w-md px-6">
          <PricingCard variant="full" />
        </div>
      </section>
      <section className="bg-sidebar py-20 md:py-24">
        <div className="mx-auto max-w-5xl px-6">
          <FAQ id="faq" title={sectionTitles.faqPricing} items={faqPricing} />
        </div>
      </section>
    </>
  );
}
