import { features } from '../content/features';
import { sectionTitles } from '../content/copy';
import { FeatureCard } from './FeatureCard';

export function FeatureGrid() {
  return (
    <section className="py-12" aria-labelledby="features-heading">
      <h2 className="text-3xl font-semibold tracking-tight" id="features-heading">
        {sectionTitles.features}
      </h2>
      <div className="mt-10 grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
        {features.map((f) => (
          <FeatureCard key={f.title} feature={f} />
        ))}
      </div>
    </section>
  );
}
