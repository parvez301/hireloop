import { finalCtaCopy } from '../content/copy';
import { signupUrl } from '../lib/config';

export function FinalCTA() {
  return (
    <section className="py-20 md:py-24">
      <div className="mx-auto max-w-6xl px-6">
        <div className="relative overflow-hidden rounded-3xl border border-border bg-gradient-to-br from-[#14b8a6]/12 via-[#2563eb]/10 to-card px-8 py-20 text-center md:px-16">
          <div
            aria-hidden
            className="pointer-events-none absolute inset-0 -z-10 bg-[radial-gradient(circle_at_20%_20%,rgba(20,184,166,0.18),transparent_45%),radial-gradient(circle_at_80%_80%,rgba(124,58,237,0.2),transparent_45%)]"
          />
          <h2 className="mx-auto max-w-4xl text-4xl font-black leading-[1.05] tracking-tight md:text-6xl lg:text-7xl">
            <span className="text-text-primary">Stop applying. </span>
            <span className="bg-gradient-to-br from-[#14b8a6] via-[#2563eb] to-[#7c3aed] bg-clip-text text-transparent">
              Start interviewing.
            </span>
          </h2>
          <a
            className="mt-10 inline-flex items-center justify-center rounded-full bg-gradient-to-r from-[#14b8a6] via-[#2563eb] to-[#7c3aed] px-8 py-4 text-base font-semibold text-white shadow-[0_10px_30px_-10px_rgba(37,99,235,0.5)] transition-all hover:-translate-y-0.5 hover:shadow-[0_18px_45px_-12px_rgba(124,58,237,0.7)]"
            href={signupUrl()}
          >
            {finalCtaCopy.button}
          </a>
          <p className="mt-4 text-sm text-text-secondary">{finalCtaCopy.micro}</p>
        </div>
      </div>
    </section>
  );
}
