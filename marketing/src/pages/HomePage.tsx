import { FAQ } from '../components/FAQ';
import { FeatureGrid } from '../components/FeatureGrid';
import { FeatureDeepDives } from '../components/FeatureDeepDives';
import { FinalCTA } from '../components/FinalCTA';
import { Hero } from '../components/Hero';
import { HowItWorks } from '../components/HowItWorks';
import { LiveDemo } from '../components/LiveDemo';
import { PricingPreview } from '../components/PricingPreview';
import { ProductPreview } from '../components/ProductPreview';
import { faqHome } from '../content/faq-home';
import { sectionTitles } from '../content/copy';
import { metaDescriptions } from '../content/meta';
import { useDocumentTitle } from '../lib/useDocumentTitle';

export function HomePage() {
  useDocumentTitle('HireLoop — AI-powered job search', metaDescriptions.home);

  return (
    <>
      <Hero />
      <LiveDemo />
      <FeatureGrid />
      <FeatureDeepDives />
      <HowItWorks />
      <ProductPreview />
      <PricingPreview />
      <section className="bg-sidebar border-y border-border">
        <div className="mx-auto max-w-5xl px-6">
          <FAQ title={sectionTitles.faqHome} items={faqHome} />
        </div>
      </section>
      <FinalCTA />
    </>
  );
}
