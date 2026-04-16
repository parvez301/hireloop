import { describe, expect, it } from 'vitest';

import { buildLlmsFullTxt, buildLlmsTxt } from '../../scripts/generate-llms-txt';

describe('generate-llms-txt', () => {
  it('builds llms.txt with expected sections', () => {
    const txt = buildLlmsTxt();
    expect(txt).toContain('# HireLoop');
    expect(txt).toContain('https://hireloop.xyz/pricing');
    expect(txt).toContain('llms-full.txt');
  });

  it('builds llms-full.txt with home, pricing, and legal sources', () => {
    const full = buildLlmsFullTxt();
    expect(full).toContain('# Home');
    expect(full).toContain('# Pricing');
    expect(full).toContain('Who we are');
    expect(full).toContain('AI training');
  });
});
