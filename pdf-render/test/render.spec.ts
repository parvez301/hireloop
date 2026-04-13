import { describe, expect, it } from "vitest";

import { markdownToHtml } from "../src/render.js";

describe("markdownToHtml", () => {
  it("wraps markdown content in the resume template", async () => {
    const md = "# Jane Doe\n\n## Experience\n\n- Led migration";
    const html = await markdownToHtml(md);

    expect(html).toContain("<h1>Jane Doe</h1>");
    expect(html).toContain("<h2>Experience</h2>");
    expect(html).toContain("Led migration");
    expect(html).toContain("@font-face");
    expect(html).toContain("generated-at");
  });

  it("handles empty markdown without crashing", async () => {
    const html = await markdownToHtml("");
    expect(html).toContain("<!doctype html>");
  });
});
