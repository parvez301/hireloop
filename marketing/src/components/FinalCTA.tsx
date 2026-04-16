import { finalCtaCopy } from '../content/copy';
import { signupUrl } from '../lib/config';

export function FinalCTA() {
  return (
    <section className="py-12">
      <div className="rounded-lg border border-border bg-sidebar px-8 py-10 text-center">
        <h2 className="text-3xl font-semibold tracking-tight">{finalCtaCopy.headline}</h2>
        <a
          className="mt-6 inline-flex items-center justify-center bg-accent text-white px-5 py-2.5 rounded-md font-medium transition-opacity hover:opacity-90"
          href={signupUrl()}
        >
          {finalCtaCopy.button}
        </a>
        <p className="mt-3 text-sm text-text-secondary">{finalCtaCopy.micro}</p>
      </div>
    </section>
  );
}
