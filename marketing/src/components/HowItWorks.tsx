import { howItWorksSteps } from '../content/copy';

export function HowItWorks() {
  return (
    <section className="py-24 md:py-32 scroll-mt-24" id="how-it-works" aria-labelledby="how-heading">
      <div className="mx-auto max-w-6xl px-6">
        <h2
          className="text-center text-4xl font-black leading-[1.05] tracking-tight md:text-6xl lg:text-7xl"
          id="how-heading"
        >
          <span className="text-text-primary">Three steps from </span>
          <span className="bg-gradient-to-br from-[#14b8a6] via-[#2563eb] to-[#7c3aed] bg-clip-text text-transparent">
            cold start to offers.
          </span>
        </h2>
        <p className="mx-auto mt-6 max-w-2xl text-center text-lg text-text-secondary leading-relaxed md:text-xl">
          The middle is just conversations.
        </p>

        <ol className="relative mt-20 grid grid-cols-1 gap-10 md:grid-cols-3 md:gap-6">
          <div
            aria-hidden
            className="pointer-events-none absolute left-0 right-0 top-6 hidden h-px bg-gradient-to-r from-transparent via-border to-transparent md:block"
          />
          {howItWorksSteps.map((step, index) => (
            <li key={step.title} className="relative">
              <div className="relative z-10 flex h-12 w-12 items-center justify-center rounded-full border border-border bg-bg text-lg font-semibold text-accent shadow-sm">
                {index + 1}
              </div>
              <h3 className="mt-5 text-xl font-semibold tracking-tight">{step.title}</h3>
              <p className="mt-2 text-base text-text-secondary leading-relaxed">{step.body}</p>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}
