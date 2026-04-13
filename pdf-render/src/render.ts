import { randomBytes } from "node:crypto";
import { unlink, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

import Handlebars from "handlebars";
import { marked } from "marked";
import { chromium, type Browser } from "playwright";

const __dirname = dirname(fileURLToPath(import.meta.url));
const TEMPLATE_PATH = join(__dirname, "templates/resume.html");
export const templatePath = TEMPLATE_PATH;
const TEMPLATE_DIR = dirname(TEMPLATE_PATH);

let compiledTemplate: HandlebarsTemplateDelegate | null = null;

async function getTemplate(): Promise<HandlebarsTemplateDelegate> {
  if (compiledTemplate) return compiledTemplate;
  const { readFile } = await import("node:fs/promises");
  const raw = await readFile(TEMPLATE_PATH, "utf8");
  compiledTemplate = Handlebars.compile(raw);
  return compiledTemplate;
}

export async function markdownToHtml(markdownSource: string): Promise<string> {
  const template = await getTemplate();
  const body = await marked.parse(markdownSource);
  return template({
    body,
    generatedAt: new Date().toISOString().slice(0, 16).replace("T", " "),
  });
}

let browser: Browser | null = null;
const RENDER_CONCURRENCY = 2;
let inFlight = 0;
const waiters: Array<() => void> = [];

export async function getBrowser(): Promise<Browser> {
  if (browser) return browser;
  browser = await chromium.launch({
    args: ["--no-sandbox", "--disable-dev-shm-usage"],
  });
  return browser;
}

async function acquire(): Promise<void> {
  if (inFlight < RENDER_CONCURRENCY) {
    inFlight += 1;
    return;
  }
  await new Promise<void>((resolve) => waiters.push(resolve));
  inFlight += 1;
}

function release(): void {
  inFlight -= 1;
  const next = waiters.shift();
  if (next) next();
}

export interface RenderResult {
  buffer: Buffer;
  pageCount: number;
  renderMs: number;
}

export async function renderPdf(markdownSource: string): Promise<RenderResult> {
  const html = await markdownToHtml(markdownSource);
  const start = Date.now();
  await acquire();
  const tmpName = `_render_${randomBytes(8).toString("hex")}.html`;
  const tmpPath = join(TEMPLATE_DIR, tmpName);
  await writeFile(tmpPath, html, "utf8");
  try {
    const b = await getBrowser();
    const context = await b.newContext();
    const page = await context.newPage();
    const fileUrl = pathToFileURL(tmpPath).href;
    await page.goto(fileUrl, { waitUntil: "load", timeout: 60_000 });
    const pdfBuffer = await page.pdf({
      format: "A4",
      printBackground: true,
      margin: { top: "0.5in", bottom: "0.5in", left: "0.5in", right: "0.5in" },
    });
    const pageCount = await page.evaluate(() => {
      return Math.max(1, Math.ceil(document.body.scrollHeight / 1050));
    });
    await context.close();
    return {
      buffer: Buffer.from(pdfBuffer),
      pageCount,
      renderMs: Date.now() - start,
    };
  } finally {
    await unlink(tmpPath).catch(() => {});
    release();
  }
}
