import { features } from '../content/features';
import { FeatureCard } from './FeatureCard';

export function FeatureGrid() {
  return (
    <section className="py-24 md:py-32" aria-labelledby="features-heading">
      <div className="mx-auto max-w-6xl px-6">
        <h2
          className="text-center text-4xl font-black leading-[1.05] tracking-tight md:text-6xl lg:text-7xl"
          id="features-heading"
        >
          <span className="text-text-primary">Everything you need </span>
          <span className="bg-gradient-to-br from-[#14b8a6] via-[#2563eb] to-[#7c3aed] bg-clip-text text-transparent">
            for a focused search.
          </span>
        </h2>
        <p className="mx-auto mt-6 max-w-2xl text-center text-lg text-text-secondary leading-relaxed md:text-xl">
          Six tools built for the only phase of hiring that still burns your nights and weekends.
        </p>
        <div className="mt-20 grid grid-cols-1 gap-12 md:grid-cols-2 md:gap-x-10 md:gap-y-14 lg:grid-cols-3">
          {features.map((f) => (
            <FeatureCard key={f.title} feature={f} />
          ))}
        </div>
      </div>
    </section>
  );
}
