import { afterAll, beforeAll, describe, expect, it, vi } from "vitest";

import { app } from "../src/server.js";

vi.mock("../src/s3.js", () => ({
  uploadPdf: vi.fn(async () => undefined),
}));

beforeAll(async () => {
  await app.ready();
});

afterAll(async () => {
  await app.close();
});

describe("POST /render", () => {
  it("renders a PDF and returns metadata", async () => {
    const response = await app.inject({
      method: "POST",
      url: "/render",
      headers: {
        authorization: "Bearer local-dev-key",
        "content-type": "application/json",
      },
      payload: {
        markdown: "# Jane Doe\n\n## Experience\n\n- Led migration at Acme",
        template: "resume",
        user_id: "usr_test",
        output_key: "cv-outputs/usr_test/abc.pdf",
      },
    });

    expect(response.statusCode).toBe(200);
    const body = response.json();
    expect(body.success).toBe(true);
    expect(body.s3_key).toBe("cv-outputs/usr_test/abc.pdf");
    expect(body.size_bytes).toBeGreaterThan(500);
  }, 60_000);

  it("rejects missing bearer token", async () => {
    const response = await app.inject({
      method: "POST",
      url: "/render",
      payload: { markdown: "x", template: "resume", user_id: "u", output_key: "k" },
    });
    expect(response.statusCode).toBe(401);
  });
});
