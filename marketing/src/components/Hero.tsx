import { heroCopy } from '../content/copy';
import { signupUrl } from '../lib/config';

export function Hero() {
  return (
    <section className="relative overflow-hidden border-b border-border">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 -z-10 bg-[radial-gradient(ellipse_at_top_left,rgba(20,184,166,0.16),transparent_55%),radial-gradient(ellipse_at_bottom_right,rgba(124,58,237,0.14),transparent_60%),radial-gradient(circle_at_65%_35%,rgba(37,99,235,0.12),transparent_45%)]"
      />
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-0 top-0 -z-10 h-[2px] bg-gradient-to-r from-transparent via-[#2563eb] to-transparent opacity-60"
      />
      <div className="mx-auto grid max-w-6xl grid-cols-1 items-center gap-12 px-6 py-24 md:py-32 lg:grid-cols-[1.15fr,1fr]">
        <div>
          <p className="inline-flex items-center gap-2 rounded-full border border-border bg-bg px-3 py-1 text-xs font-medium uppercase tracking-wider text-text-secondary">
            <span className="h-1.5 w-1.5 rounded-full bg-accent" aria-hidden />
            {heroCopy.eyebrow}
          </p>
          <h1 className="mt-6 text-[2.75rem] font-black leading-[0.95] tracking-tight md:text-6xl lg:text-[5.25rem]">
            <span className="block text-text-primary">Spend your job hunt</span>
            <span className="block bg-gradient-to-br from-[#14b8a6] via-[#2563eb] to-[#7c3aed] bg-clip-text text-transparent">
              on interviews,
            </span>
            <span className="block text-text-primary">not applications.</span>
          </h1>
          <p className="mt-7 max-w-xl text-lg text-text-secondary leading-relaxed md:text-xl">
            {heroCopy.subhead}
          </p>
          <div className="mt-9 flex flex-col items-start gap-3 sm:flex-row sm:items-center">
            <a
              className="inline-flex items-center justify-center rounded-full bg-gradient-to-r from-[#14b8a6] via-[#2563eb] to-[#7c3aed] px-7 py-3.5 text-base font-semibold text-white shadow-[0_10px_30px_-10px_rgba(37,99,235,0.5)] transition-all hover:-translate-y-0.5 hover:shadow-[0_18px_45px_-12px_rgba(124,58,237,0.7)]"
              href={signupUrl()}
            >
              {heroCopy.primaryCta}
            </a>
            <a
              className="inline-flex items-center justify-center rounded-full border-2 border-border bg-bg px-7 py-3 text-base font-semibold text-text-primary transition-colors hover:border-[#2563eb] hover:text-[#2563eb]"
              href="#how-it-works"
            >
              {heroCopy.secondaryCta}
            </a>
          </div>
          <p className="mt-5 text-sm text-text-secondary">{heroCopy.micro}</p>
        </div>

        <div className="relative">
          <div
            aria-hidden
            className="absolute -inset-6 -z-10 rounded-3xl bg-gradient-to-br from-[#14b8a6]/25 via-[#2563eb]/20 to-[#7c3aed]/20 blur-2xl"
          />
          <div
            aria-hidden
            className="absolute -right-8 -top-8 -z-10 h-40 w-40 rounded-full bg-[#7c3aed]/18 blur-3xl"
          />
          <figure className="relative overflow-hidden rounded-2xl border border-border bg-card shadow-[0_30px_80px_-25px_rgba(55,53,47,0.35)]">
            <div className="flex items-center gap-1.5 border-b border-border bg-sidebar px-4 py-3">
              <span className="h-2.5 w-2.5 rounded-full bg-[#ff5f57]" aria-hidden />
              <span className="h-2.5 w-2.5 rounded-full bg-[#febc2e]" aria-hidden />
              <span className="h-2.5 w-2.5 rounded-full bg-[#28c840]" aria-hidden />
              <span className="ml-3 text-xs text-text-secondary">app.hireloop.com</span>
            </div>
            <img
              src="/screenshots/chat.png"
              alt="HireLoop agent chat — a user asks to evaluate a Stripe Senior Software Engineer role and receives an A-grade evaluation"
              loading="eager"
              className="block w-full bg-white"
            />
          </figure>
        </div>
      </div>

      <div className="border-t border-border bg-sidebar">
        <div className="mx-auto max-w-6xl px-6 py-8">
          <div className="flex flex-col items-center gap-5 md:flex-row md:items-center md:justify-between md:gap-8">
            <p className="text-xs font-bold uppercase tracking-[0.2em] text-text-secondary">
              Scans every new job on
            </p>
            <div className="flex flex-wrap items-center justify-center gap-x-7 gap-y-4 md:gap-x-9">
              {[
                { name: 'Greenhouse', mono: 'G', color: '#24A148' },
                { name: 'Ashby', mono: 'A', color: '#6D28D9' },
                { name: 'Lever', mono: 'L', color: '#111827' },
                { name: 'Workday', mono: 'W', color: '#0875E1' },
                { name: 'LinkedIn', mono: 'in', color: '#0A66C2' },
              ].map((src) => (
                <div key={src.name} className="flex items-center gap-2.5">
                  <span
                    aria-hidden
                    className="inline-flex h-7 w-7 items-center justify-center rounded-md text-[11px] font-bold text-white"
                    style={{ backgroundColor: src.color }}
                  >
                    {src.mono}
                  </span>
                  <span className="text-[15px] font-semibold tracking-tight text-text-primary">
                    {src.name}
                  </span>
                </div>
              ))}
              <div className="flex items-center gap-2.5">
                <span
                  aria-hidden
                  className="inline-flex h-7 w-7 items-center justify-center rounded-md border border-dashed border-text-secondary/60 text-[11px] font-bold text-text-secondary"
                >
                  +
                </span>
                <span className="text-[15px] font-semibold tracking-tight text-text-secondary">
                  any URL
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
