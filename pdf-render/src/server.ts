import { fileURLToPath } from "node:url";

import Fastify from "fastify";

import { bearerAuth } from "./auth.js";
import { getBrowser, renderPdf } from "./render.js";
import { uploadPdf } from "./s3.js";

const PORT = Number(process.env.PORT ?? 4000);
const API_KEY = process.env.PDF_RENDER_API_KEY ?? "local-dev-key";

let chromiumReady = false;

const app = Fastify({ logger: true });

app.get("/health", async () => ({
  status: "ok",
  chromium_ready: chromiumReady,
}));

interface RenderRequestBody {
  markdown: string;
  template: "resume" | "cover_letter";
  user_id: string;
  output_key: string;
}

app.register(async (instance) => {
  instance.addHook("onRequest", bearerAuth(API_KEY));

  instance.post<{ Body: RenderRequestBody }>("/render", async (req, reply) => {
    const { markdown, output_key } = req.body ?? ({} as RenderRequestBody);
    if (!markdown || !output_key) {
      return reply.code(400).send({
        success: false,
        error: "BAD_REQUEST",
        message: "markdown and output_key required",
      });
    }
    try {
      const result = await renderPdf(markdown);
      await uploadPdf(output_key, result.buffer);
      return {
        success: true,
        s3_key: output_key,
        s3_bucket: process.env.AWS_S3_BUCKET ?? "hireloop-dev-assets",
        page_count: result.pageCount,
        size_bytes: result.buffer.length,
        render_ms: result.renderMs,
      };
    } catch (err) {
      req.log.error({ err }, "render failed");
      return reply.code(500).send({
        success: false,
        error: "CHROMIUM_CRASH",
        message: err instanceof Error ? err.message : "unknown",
      });
    }
  });
});

async function start() {
  try {
    await app.listen({ port: PORT, host: "0.0.0.0" });
    await getBrowser();
    chromiumReady = true;
    app.log.info("chromium ready");
  } catch (err) {
    app.log.error(err);
    process.exit(1);
  }
}

const __filename = fileURLToPath(import.meta.url);
if (process.argv[1] === __filename) {
  void start();
}

export { app };
