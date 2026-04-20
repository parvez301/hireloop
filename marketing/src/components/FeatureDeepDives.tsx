interface DeepDive {
  eyebrow: string;
  headline: string;
  body: string;
  bullets: string[];
  image: string;
  imageAlt: string;
}

const deepDives: DeepDive[] = [
  {
    eyebrow: 'Evaluate anything',
    headline: 'Grade any job in under 10 seconds.',
    body: 'Paste a link. Get an A–F grade across ten dimensions — skills fit, compensation, seniority, stack, red flags. Every verdict shows its work.',
    bullets: [
      'Ten-factor ensemble score, not vibes',
      'Catches red flags humans miss (ghost roles, comp bait, title inflation)',
      'One tap to tailor a résumé for any A or B grade',
    ],
    image: '/screenshots/chat.png',
    imageAlt: 'HireLoop agent returns an A-grade evaluation card for a Stripe Senior Software Engineer role',
  },
  {
    eyebrow: 'Scanning',
    headline: 'New openings, scored before you see them.',
    body: 'Point HireLoop at 15 companies on Greenhouse, Ashby, or Lever. Every new listing is scored against your profile the moment it posts — no more refreshing careers pages.',
    bullets: [
      'Background scans across every major ATS',
      'Score + reasoning attached to each new listing',
      'Surface only matches worth your attention',
    ],
    image: '/screenshots/scans.png',
    imageAlt: 'Scan dashboard showing a 15-company scan config with 187 jobs found, 23 new',
  },
  {
    eyebrow: 'Pipeline',
    headline: 'One board for every application.',
    body: 'Every job you engage with lands on a kanban with its A–F grade baked in. Drag through stages, revisit reasoning, never lose track of a thread.',
    bullets: [
      'Saved · Applied · Interviewing, drag-and-drop',
      'Grade and rationale visible at a glance',
      'Attaches tailored résumé + prep notes per card',
    ],
    image: '/screenshots/pipeline.png',
    imageAlt: 'Application pipeline kanban showing saved, applied, and interviewing columns',
  },
];

export function FeatureDeepDives() {
  return (
    <section className="relative bg-sidebar border-y border-border py-20 md:py-28">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-0 top-0 h-[2px] bg-gradient-to-r from-transparent via-[#2563eb] to-transparent opacity-40"
      />
      <div className="mx-auto flex max-w-6xl flex-col gap-20 px-6 md:gap-28">
        {deepDives.map((dive, index) => {
          const reverse = index % 2 === 1;
          return (
            <div
              key={dive.headline}
              className={
                'grid grid-cols-1 items-center gap-10 lg:grid-cols-2 lg:gap-16 ' +
                (reverse ? 'lg:[&>*:first-child]:order-2' : '')
              }
            >
              <div>
                <p className="text-xs font-medium uppercase tracking-wider text-accent">{dive.eyebrow}</p>
                <h3 className="mt-3 text-3xl font-bold tracking-tight md:text-4xl">{dive.headline}</h3>
                <p className="mt-4 text-lg text-text-secondary leading-relaxed">{dive.body}</p>
                <ul className="mt-6 space-y-3">
                  {dive.bullets.map((b) => (
                    <li key={b} className="flex gap-3 text-base text-text-primary">
                      <svg
                        className="mt-1 h-4 w-4 shrink-0 text-accent"
                        viewBox="0 0 20 20"
                        fill="none"
                        aria-hidden
                      >
                        <path
                          d="m5 10 3.5 3.5L15 7"
                          stroke="currentColor"
                          strokeWidth="2"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        />
                      </svg>
                      <span>{b}</span>
                    </li>
                  ))}
                </ul>
              </div>
              <div className="relative">
                <div
                  aria-hidden
                  className="absolute -inset-3 -z-10 rounded-2xl bg-gradient-to-br from-accent/10 to-transparent blur-lg"
                />
                <figure className="overflow-hidden rounded-xl border border-border bg-bg shadow-[0_15px_45px_-20px_rgba(55,53,47,0.2)]">
                  <img src={dive.image} alt={dive.imageAlt} loading="lazy" className="block w-full" />
                </figure>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
