import { useState } from 'react';

interface Preview {
  key: string;
  label: string;
  src: string;
  alt: string;
  caption: string;
  body: string;
}

const previews: Preview[] = [
  {
    key: 'chat',
    label: 'Agent chat',
    src: '/screenshots/chat.png',
    alt: 'HireLoop agent chat — a user asks "Evaluate this for me" and the agent replies with an A-grade evaluation card for a Stripe Senior Software Engineer role',
    caption: 'One chat. Every tool.',
    body: 'Paste a job link, ask for a tailored résumé, drop a batch of listings, prep for an interview, draft a counter-offer — all in the same conversation.',
  },
  {
    key: 'scans',
    label: 'Scanning',
    src: '/screenshots/scans.png',
    alt: 'Scan dashboard showing a 15-company scan config with a last run of 187 jobs found, 23 new',
    caption: 'Scanning runs in the background.',
    body: 'Track 15 companies across Greenhouse, Ashby, and Lever. Every new listing is scored against your profile the moment it posts.',
  },
  {
    key: 'pipeline',
    label: 'Pipeline',
    src: '/screenshots/pipeline.png',
    alt: 'Application pipeline kanban board showing saved, applied, and interviewing columns with real jobs from Stripe, Anthropic, Linear, Vercel, and Figma',
    caption: 'Your pipeline stays organized.',
    body: 'Every application lands on a kanban with the A–F grade baked in. Move cards through stages as you go.',
  },
  {
    key: 'stories',
    label: 'Story bank',
    src: '/screenshots/stories.png',
    alt: 'Story bank showing three STAR stories with tags',
    caption: 'A story bank, built from your real work.',
    body: 'STAR stories become reusable ammunition for interviews — tagged, searchable, ready to drop into prep for any role.',
  },
];

export function ProductPreview() {
  const [activeKey, setActiveKey] = useState<string>(previews[0].key);
  const active = previews.find((p) => p.key === activeKey) ?? previews[0];

  return (
    <section id="product-preview" className="bg-sidebar border-y border-border py-20 md:py-28 scroll-mt-24">
      <div className="mx-auto max-w-6xl px-6">
      <div className="mb-16 text-center">
        <h2 className="text-4xl font-black leading-[1.05] tracking-tight md:text-6xl lg:text-7xl">
          <span className="text-text-primary">A real product, </span>
          <span className="bg-gradient-to-br from-[#14b8a6] via-[#2563eb] to-[#7c3aed] bg-clip-text text-transparent">
            shipping today.
          </span>
        </h2>
        <p className="mx-auto mt-6 max-w-2xl text-lg text-text-secondary leading-relaxed md:text-xl">
          One place to manage the job search pipeline across the entire internet. These are live screens — not mockups.
        </p>
      </div>

      <div className="mx-auto max-w-4xl">
        <div
          role="tablist"
          aria-label="Product screens"
          className="flex flex-wrap gap-6 border-b border-border"
        >
          {previews.map((p) => {
            const isActive = p.key === activeKey;
            return (
              <button
                key={p.key}
                type="button"
                role="tab"
                id={`tab-${p.key}`}
                aria-selected={isActive}
                aria-controls={`panel-${p.key}`}
                tabIndex={isActive ? 0 : -1}
                onClick={() => setActiveKey(p.key)}
                className={
                  'relative -mb-px pb-3 text-sm font-medium transition-colors ' +
                  (isActive
                    ? 'text-text-primary border-b-2 border-accent'
                    : 'text-text-secondary hover:text-text-primary border-b-2 border-transparent')
                }
              >
                {p.label}
              </button>
            );
          })}
        </div>

        {previews.map((p) => {
          const isActive = p.key === activeKey;
          return (
            <div
              key={p.key}
              role="tabpanel"
              id={`panel-${p.key}`}
              aria-labelledby={`tab-${p.key}`}
              hidden={!isActive}
              className="mt-6"
            >
              <figure className="overflow-hidden rounded-lg border border-border bg-card">
                <img
                  src={p.src}
                  alt={p.alt}
                  loading={p.key === previews[0].key ? 'eager' : 'lazy'}
                  className="block w-full border-b border-border bg-white"
                />
                <figcaption className="p-5">
                  <p className="text-base font-semibold">{active.caption}</p>
                  <p className="mt-1 text-sm text-text-secondary leading-relaxed">{active.body}</p>
                </figcaption>
              </figure>
            </div>
          );
        })}
      </div>
      </div>
    </section>
  );
}
