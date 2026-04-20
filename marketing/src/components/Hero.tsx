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
      {/* Organic gradient blob — extends from ~center to past the right viewport edge. */}
      {/* Uses a skewed + rotated rounded rect for an off-axis, less-boxy shape. */}
      <div
        aria-hidden
        className="pointer-events-none absolute -z-10 hidden lg:block"
        style={{ top: '2rem', bottom: '2rem', left: '38%', right: '-8%' }}
      >
        <div className="absolute inset-0 origin-center -rotate-3 skew-y-[-2deg] rounded-[3.5rem] bg-gradient-to-br from-[#14b8a6] via-[#2563eb] to-[#7c3aed]" />
        <div className="absolute inset-0 origin-center -rotate-3 skew-y-[-2deg] rounded-[3.5rem] bg-[radial-gradient(circle_at_22%_12%,rgba(255,255,255,0.28),transparent_50%),radial-gradient(circle_at_85%_90%,rgba(0,0,0,0.18),transparent_55%)]" />
        {/* Grainy dot pattern for texture */}
        <div
          className="absolute inset-0 origin-center -rotate-3 skew-y-[-2deg] rounded-[3.5rem] opacity-[0.12] mix-blend-overlay"
          style={{
            backgroundImage:
              'radial-gradient(rgba(255,255,255,0.9) 1px, transparent 1px)',
            backgroundSize: '18px 18px',
          }}
        />
        {/* soft outer halo */}
        <div className="absolute -inset-10 origin-center -rotate-3 skew-y-[-2deg] rounded-[4rem] bg-gradient-to-br from-[#14b8a6]/40 via-[#2563eb]/35 to-[#7c3aed]/35 blur-3xl -z-10" />
      </div>

      {/* tiny accent dots scattered across the gradient panel */}
      <div
        aria-hidden
        className="pointer-events-none absolute -z-[5] hidden lg:block"
        style={{ top: '10%', left: '52%', right: '5%', height: '80%' }}
      >
        <span className="absolute left-[8%] top-[12%] h-2 w-2 rounded-full bg-white/70 shadow-[0_0_12px_rgba(255,255,255,0.8)]" />
        <span className="absolute left-[78%] top-[22%] h-1.5 w-1.5 rounded-full bg-white/60" />
        <span className="absolute left-[18%] top-[70%] h-1.5 w-1.5 rounded-full bg-white/60" />
        <span className="absolute left-[88%] top-[78%] h-2 w-2 rounded-full bg-white/60 shadow-[0_0_10px_rgba(255,255,255,0.7)]" />
      </div>

      <div className="relative mx-auto grid max-w-7xl grid-cols-1 items-center gap-14 px-6 py-24 md:py-32 lg:grid-cols-[1fr,1.3fr] lg:gap-8 xl:gap-14">
        <div className="relative">
          <p className="inline-flex items-center gap-2 rounded-full border border-border bg-bg px-3 py-1 text-xs font-medium uppercase tracking-wider text-text-secondary">
            <span className="h-1.5 w-1.5 rounded-full bg-accent" aria-hidden />
            {heroCopy.eyebrow}
          </p>
          <h1 className="mt-6 text-[2.75rem] font-black leading-[0.95] tracking-tight md:text-6xl lg:text-[5rem]">
            <span className="block text-text-primary">Apply to 5 jobs.</span>
            <span className="block bg-gradient-to-br from-[#14b8a6] via-[#2563eb] to-[#7c3aed] bg-clip-text text-transparent">
              Skip the other 495.
            </span>
            <span className="block text-text-primary">Land the one.</span>
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

        <div className="relative lg:-ml-8 lg:-mr-16 xl:-mr-28">
          {/* mobile backdrop since the gradient blob is lg-only */}
          <div
            aria-hidden
            className="pointer-events-none absolute -inset-6 -z-10 rounded-[2rem] bg-gradient-to-br from-[#14b8a6]/20 via-[#2563eb]/20 to-[#7c3aed]/20 blur-2xl lg:hidden"
          />

          {/* Secondary screenshot — pipeline — peeks from behind bottom-right, tilted the other way */}
          <figure
            aria-hidden
            className="absolute left-[18%] top-[38%] z-0 hidden w-[56%] overflow-hidden rounded-xl border border-white/60 bg-card shadow-[0_25px_60px_-20px_rgba(20,184,166,0.6)] md:block lg:left-[22%] lg:top-[48%] lg:rotate-[5deg]"
          >
            <div className="flex items-center gap-1 border-b border-border bg-sidebar px-3 py-2">
              <span className="h-1.5 w-1.5 rounded-full bg-[#ff5f57]" />
              <span className="h-1.5 w-1.5 rounded-full bg-[#febc2e]" />
              <span className="h-1.5 w-1.5 rounded-full bg-[#28c840]" />
              <span className="ml-2 text-[10px] text-text-secondary">pipeline</span>
            </div>
            <img
              src="/screenshots/pipeline.png"
              alt=""
              loading="lazy"
              className="block w-full bg-white"
            />
          </figure>

          {/* floating score chip — top-left, on the gradient */}
          <div className="absolute -left-3 top-2 z-30 hidden items-center gap-2 rounded-xl border border-white/40 bg-white/95 px-3 py-2 text-xs font-semibold text-text-primary shadow-[0_12px_30px_-8px_rgba(37,99,235,0.5)] backdrop-blur md:flex">
            <span className="inline-flex h-6 w-6 items-center justify-center rounded-lg bg-gradient-to-br from-[#14b8a6] to-[#2563eb] text-[11px] font-bold text-white">
              A
            </span>
            <div className="flex flex-col leading-tight">
              <span>92% match</span>
              <span className="text-[10px] font-normal text-text-secondary">Stripe · Senior SWE</span>
            </div>
          </div>

          {/* floating speed chip — bottom-right */}
          <div className="absolute -bottom-4 right-4 z-30 hidden items-center gap-2 rounded-xl border border-white/40 bg-white/95 px-3 py-2 text-xs font-semibold text-text-primary shadow-[0_12px_30px_-8px_rgba(124,58,237,0.5)] backdrop-blur md:flex">
            <span className="relative inline-flex h-6 w-6 items-center justify-center rounded-lg bg-gradient-to-br from-[#2563eb] to-[#7c3aed] text-white">
              <svg viewBox="0 0 24 24" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth={3} strokeLinecap="round" strokeLinejoin="round">
                <polyline points="20 6 9 17 4 12" />
              </svg>
            </span>
            <div className="flex flex-col leading-tight">
              <span>Graded this job</span>
              <span className="text-[10px] font-normal text-text-secondary">in 8 seconds</span>
            </div>
          </div>

          {/* Primary screenshot — chat — sits in front, tilted opposite direction */}
          <figure className="relative z-10 overflow-hidden rounded-2xl border border-white/50 bg-card shadow-[0_40px_100px_-20px_rgba(37,99,235,0.55),0_20px_60px_-20px_rgba(124,58,237,0.35)] transition-transform duration-700 ease-out lg:rotate-[-2deg] lg:hover:rotate-0 lg:hover:scale-[1.01]">
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
