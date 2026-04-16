import { howItWorksSteps, sectionTitles } from '../content/copy';

export function HowItWorks() {
  return (
    <section className="py-12 scroll-mt-24" id="how-it-works" aria-labelledby="how-heading">
      <h2 className="text-3xl font-semibold tracking-tight" id="how-heading">
        {sectionTitles.howItWorks}
      </h2>
      <div className="mt-10 grid grid-cols-1 gap-8 md:grid-cols-3">
        {howItWorksSteps.map((step, index) => (
          <div key={step.title}>
            <p className="text-xs font-medium uppercase tracking-wider text-text-secondary">Step {index + 1}</p>
            <h3 className="mt-2 text-xl font-semibold">{step.title}</h3>
            <p className="mt-2 text-base text-text-secondary leading-relaxed">{step.body}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
