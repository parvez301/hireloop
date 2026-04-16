import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { faqHome } from '../src/content/faq-home.ts';
import { faqPricing } from '../src/content/faq-pricing.ts';
import { features } from '../src/content/features.ts';
import {
  finalCtaCopy,
  footerCopy,
  heroCopy,
  howItWorksSteps,
  navCopy,
  pricingPreviewCopy,
  sectionTitles,
} from '../src/content/copy.ts';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const marketingRoot = path.resolve(__dirname, '..');

export function buildLlmsTxt(): string {
  return `# HireLoop

> AI-powered job search for anyone looking for their next role. Scans Greenhouse, Ashby, and Lever; evaluates jobs across 10 dimensions with an A–F grade; writes ATS-optimized résumés tailored to each job; preps interviews with a STAR story bank; generates negotiation playbooks. $4.99/month after a 3-day free trial.

## Product
- [Home](https://hireloop.xyz/): overview and features
- [Pricing](https://hireloop.xyz/pricing): single plan — $4.99/month, cancel anytime

## Legal
- [Terms of Service](https://hireloop.xyz/terms)
- [Privacy Policy](https://hireloop.xyz/privacy): HireLoop never trains AI on user data

## Optional
- [llms-full.txt](https://hireloop.xyz/llms-full.txt): full text of all pages
`;
}

function formatFaq(items: { q: string; a: string }[]): string {
  return items.map((item) => `### ${item.q}\n\n${item.a}`).join('\n\n');
}

export function buildLlmsFullTxt(): string {
  const termsMd = readFileSync(path.join(marketingRoot, 'src/content/terms.md'), 'utf8');
  const privacyMd = readFileSync(path.join(marketingRoot, 'src/content/privacy.md'), 'utf8');

  const featureBlock = features
    .map((f) => `### ${f.title}\n\n${f.summary}`)
    .join('\n\n');

  const howBlock = howItWorksSteps
    .map((s, i) => `### Step ${i + 1}: ${s.title}\n\n${s.body}`)
    .join('\n\n');

  return `# Home

## ${heroCopy.eyebrow}

**${heroCopy.headline}**

${heroCopy.subhead}

- Primary CTA: ${heroCopy.primaryCta}
- Secondary CTA: ${heroCopy.secondaryCta}
- ${heroCopy.micro}

## ${sectionTitles.features}

${featureBlock}

## ${sectionTitles.howItWorks}

${howBlock}

## Pricing preview

**${pricingPreviewCopy.headline}** ${pricingPreviewCopy.body} (${pricingPreviewCopy.link})

## ${sectionTitles.faqHome}

${formatFaq(faqHome)}

## Final CTA

**${finalCtaCopy.headline}** — ${finalCtaCopy.button}. ${finalCtaCopy.micro}

## Footer

${footerCopy.tagline}

Nav: ${navCopy.brand} · ${navCopy.pricing} · ${navCopy.cta}

---

# Pricing

Single plan: **$4.99/mo**. CTA: **Start 3-day free trial**.

## Included

- Unlimited job evaluations
- Tailored résumé PDFs
- Job scanning (Greenhouse, Ashby, Lever)
- Batch evaluation of hundreds of jobs at once
- Interview prep + STAR story bank
- Negotiation playbooks

## ${sectionTitles.faqPricing}

${formatFaq(faqPricing)}

---

# Terms of Service (markdown source)

${termsMd}

---

# Privacy Policy (markdown source)

${privacyMd}
`;
}

export function writeLlmsFiles(publicDir: string): void {
  mkdirSync(publicDir, { recursive: true });
  writeFileSync(path.join(publicDir, 'llms.txt'), buildLlmsTxt(), 'utf8');
  writeFileSync(path.join(publicDir, 'llms-full.txt'), buildLlmsFullTxt(), 'utf8');
}

function main(): void {
  writeLlmsFiles(path.join(marketingRoot, 'public'));
}

main();
