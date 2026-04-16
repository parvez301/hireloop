import { heroCopy } from '../content/copy';
import { signupUrl } from '../lib/config';

export function Hero() {
  return (
    <section className="py-16 md:py-24">
      <div className="mx-auto max-w-3xl text-center">
        <p className="text-xs font-medium uppercase tracking-wider text-text-secondary">{heroCopy.eyebrow}</p>
        <h1 className="mt-4 text-4xl font-bold tracking-tight leading-[1.1] md:text-5xl">{heroCopy.headline}</h1>
        <p className="mt-6 text-base text-text-secondary leading-relaxed">{heroCopy.subhead}</p>
        <div className="mt-8 flex flex-col items-center justify-center gap-3 md:flex-row">
          <a className="bg-accent text-white px-5 py-2.5 rounded-md font-medium transition-opacity hover:opacity-90" href={signupUrl()}>
            {heroCopy.primaryCta}
          </a>
          <a
            className="text-text-primary px-4 py-2.5 rounded-md font-medium hover:bg-hover transition-colors"
            href="#how-it-works"
          >
            {heroCopy.secondaryCta}
          </a>
        </div>
        <p className="mt-4 text-sm text-text-secondary">{heroCopy.micro}</p>
      </div>
    </section>
  );
}
