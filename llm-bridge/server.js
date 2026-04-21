// HireLoop LLM Bridge.
//
// Translates Anthropic Messages API requests into `claude -p` CLI invocations
// so backend services can consume a Claude subscription in place of a paid
// ANTHROPIC_API_KEY. Used for async batch work (L1/L2/CV/interview prep) where
// the ~250-500ms subprocess overhead and subscription rate-limits are
// tolerable.
//
// Inspired by an internal rsa-e.com deployment. Slimmed to Claude-only here —
// no cursor/agent backend.

import { createServer } from "node:http";
import { spawn } from "node:child_process";
import { randomUUID } from "node:crypto";

const PORT = parseInt(process.env.LLM_BRIDGE_PORT || "8019", 10);
const HOST = process.env.LLM_BRIDGE_HOST || "127.0.0.1";
const CLAUDE_BIN = process.env.CLAUDE_BIN || "claude";
const DEFAULT_MODEL = process.env.LLM_BRIDGE_DEFAULT_MODEL || "claude-sonnet-4-5";

// Shared-secret gate — if set, requests MUST send matching x-bridge-secret.
// Unset = no auth (fine for loopback, required before anything public).
const SHARED_SECRET = process.env.LLM_BRIDGE_SHARED_SECRET || "";

// ── Session tracking ─────────────────────────────────────────────
// Maps conversation → claude CLI session ID so multi-turn chats reuse state.
// Key = x-session-id header (preferred) OR hash of first user message.
const sessions = new Map();

setInterval(() => {
  const cutoff = Date.now() - 2 * 60 * 60 * 1000;
  for (const [key, val] of sessions) {
    if (val.lastUsed < cutoff) sessions.delete(key);
  }
}, 10 * 60 * 1000).unref();

function conversationKey(messages, sessionHeader) {
  if (sessionHeader) return sessionHeader;
  const firstUser = messages.find((m) => m.role === "user");
  if (!firstUser) return null;
  const content =
    typeof firstUser.content === "string"
      ? firstUser.content
      : JSON.stringify(firstUser.content);
  let hash = 0;
  for (let i = 0; i < content.length; i++) {
    hash = ((hash << 5) - hash + content.charCodeAt(i)) | 0;
  }
  return `conv_${hash.toString(36)}`;
}

function getLastUserMessage(messages) {
  for (let i = messages.length - 1; i >= 0; i--) {
    if (messages[i].role !== "user") continue;
    const content = messages[i].content;
    if (typeof content === "string") return content;
    if (Array.isArray(content)) {
      return content
        .map((b) => {
          if (b.type === "text") return b.text;
          if (b.type === "tool_result") {
            return typeof b.content === "string" ? b.content : JSON.stringify(b.content);
          }
          return "";
        })
        .filter(Boolean)
        .join("\n");
    }
  }
  return "";
}

function getSystemPrompt(system) {
  if (!system) return null;
  if (typeof system === "string") return system;
  if (Array.isArray(system)) return system.map((b) => b.text || "").join("\n");
  return null;
}

function sendJson(res, status, body) {
  res.writeHead(status, { "Content-Type": "application/json" });
  res.end(JSON.stringify(body));
}

function sendSSE(res, event, data) {
  res.write(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`);
}

function parseCliOutput(stdout) {
  const trimmed = stdout.trim();
  if (!trimmed) return [];
  if (trimmed.startsWith("[")) return JSON.parse(trimmed);
  return trimmed
    .split("\n")
    .filter((l) => l.trim())
    .map((l) => JSON.parse(l));
}

function eventsToAnthropicResponse(events, model) {
  const result = events.findLast((e) => e.type === "result");
  const assistants = events.filter((e) => e.type === "assistant" && e.message?.content);

  let text = "";
  if (result?.result) {
    text = result.result;
  } else if (assistants.length > 0) {
    const last = assistants[assistants.length - 1];
    text = last.message.content
      .filter((b) => b.type === "text")
      .map((b) => b.text)
      .join("");
  }

  let usage = { input_tokens: 0, output_tokens: 0 };
  if (result?.usage) {
    const u = result.usage;
    usage = {
      input_tokens: u.input_tokens ?? u.inputTokens ?? 0,
      output_tokens: u.output_tokens ?? u.outputTokens ?? 0,
      cache_creation_input_tokens: u.cache_creation_input_tokens ?? 0,
      cache_read_input_tokens: u.cache_read_input_tokens ?? 0,
    };
  }

  return {
    id: `msg_${randomUUID().replace(/-/g, "").slice(0, 24)}`,
    type: "message",
    role: "assistant",
    content: [{ type: "text", text }],
    model,
    stop_reason: "end_turn",
    stop_sequence: null,
    usage,
  };
}

function buildCliArgs({ stream, cliModel, existingSession, isFirstTurn, systemPrompt }) {
  const args = ["-p", "--output-format", stream ? "stream-json" : "json", "--verbose", "--tools", ""];
  if (cliModel) args.push("--model", cliModel);
  if (existingSession?.cliSessionId) args.push("--resume", existingSession.cliSessionId);
  if (isFirstTurn && systemPrompt) args.push("--system-prompt", systemPrompt);
  return args;
}

function handleBlocking(args, userPrompt, model, res, convKey) {
  const child = spawn(CLAUDE_BIN, args, {
    stdio: ["pipe", "pipe", "pipe"],
    env: { ...process.env, NO_COLOR: "1" },
  });

  child.stdin.write(userPrompt);
  child.stdin.end();

  let stdout = "";
  let stderr = "";
  child.stdout.on("data", (d) => (stdout += d));
  child.stderr.on("data", (d) => (stderr += d));

  child.on("error", (err) => {
    console.error("spawn error:", err);
    sendJson(res, 502, {
      type: "error",
      error: { type: "api_error", message: `Failed to spawn claude: ${err.message}` },
    });
  });

  child.on("close", (code) => {
    if (code !== 0) {
      console.error(`claude exited ${code}: ${stderr.slice(0, 300)}`);
      sendJson(res, 502, {
        type: "error",
        error: {
          type: "api_error",
          message: `claude CLI exited ${code}: ${stderr.slice(0, 500)}`,
        },
      });
      return;
    }

    try {
      const events = parseCliOutput(stdout);
      const result = events.findLast((e) => e.type === "result");
      if (convKey && result?.session_id) {
        sessions.set(convKey, { cliSessionId: result.session_id, lastUsed: Date.now() });
      }
      sendJson(res, 200, eventsToAnthropicResponse(events, model));
    } catch (err) {
      console.error("parse error:", err.message);
      sendJson(res, 502, {
        type: "error",
        error: { type: "api_error", message: `Bridge failed to parse CLI output: ${err.message}` },
      });
    }
  });
}

function handleStreaming(args, userPrompt, model, res, convKey) {
  const child = spawn(CLAUDE_BIN, args, {
    stdio: ["pipe", "pipe", "pipe"],
    env: { ...process.env, NO_COLOR: "1" },
  });

  child.stdin.write(userPrompt);
  child.stdin.end();

  res.writeHead(200, {
    "Content-Type": "text/event-stream",
    "Cache-Control": "no-cache",
    Connection: "keep-alive",
  });

  const msgId = `msg_${randomUUID().replace(/-/g, "").slice(0, 24)}`;
  sendSSE(res, "message_start", {
    type: "message_start",
    message: {
      id: msgId,
      type: "message",
      role: "assistant",
      content: [],
      model,
      stop_reason: null,
      stop_sequence: null,
      usage: { input_tokens: 0, output_tokens: 0 },
    },
  });
  sendSSE(res, "content_block_start", {
    type: "content_block_start",
    index: 0,
    content_block: { type: "text", text: "" },
  });

  let fullText = "";
  let allStdout = "";

  child.stdout.on("data", (chunk) => {
    allStdout += chunk.toString();
    const lines = allStdout.split("\n").filter((l) => l.trim());
    for (const line of lines) {
      try {
        const event = JSON.parse(line);
        if (event.type === "assistant" && event.message?.content) {
          for (const block of event.message.content) {
            if (block.type === "text" && block.text) {
              const newText = block.text.slice(fullText.length);
              if (newText) {
                fullText = block.text;
                sendSSE(res, "content_block_delta", {
                  type: "content_block_delta",
                  index: 0,
                  delta: { type: "text_delta", text: newText },
                });
              }
            }
          }
        }
      } catch {
        // mid-line partial read — ignore
      }
    }
  });

  child.on("close", () => {
    try {
      const events = parseCliOutput(allStdout);
      const result = events.findLast((e) => e.type === "result");
      if (result?.result) {
        const tail = result.result.slice(fullText.length);
        if (tail) {
          sendSSE(res, "content_block_delta", {
            type: "content_block_delta",
            index: 0,
            delta: { type: "text_delta", text: tail },
          });
        }
      }
      if (convKey && result?.session_id) {
        sessions.set(convKey, { cliSessionId: result.session_id, lastUsed: Date.now() });
      }
      const usage = result?.usage
        ? { output_tokens: result.usage.output_tokens ?? result.usage.outputTokens ?? 1 }
        : { output_tokens: 1 };

      sendSSE(res, "content_block_stop", { type: "content_block_stop", index: 0 });
      sendSSE(res, "message_delta", {
        type: "message_delta",
        delta: { stop_reason: "end_turn", stop_sequence: null },
        usage,
      });
      sendSSE(res, "message_stop", { type: "message_stop" });
    } catch {
      // best-effort close on parse failure
    }
    res.end();
  });
}

function requireSecret(req) {
  if (!SHARED_SECRET) return true;
  return req.headers["x-bridge-secret"] === SHARED_SECRET;
}

function handleRequest(req, res) {
  if (req.method === "GET" && req.url === "/health") {
    sendJson(res, 200, {
      status: "ok",
      claude_bin: CLAUDE_BIN,
      active_sessions: sessions.size,
      auth_required: Boolean(SHARED_SECRET),
    });
    return;
  }

  if (req.method === "GET" && req.url === "/sessions") {
    if (!requireSecret(req)) return sendJson(res, 401, { error: "unauthorized" });
    const list = [...sessions.entries()].map(([key, val]) => ({
      key,
      ...val,
      lastUsed: new Date(val.lastUsed).toISOString(),
    }));
    sendJson(res, 200, list);
    return;
  }

  if (req.method !== "POST" || !req.url.startsWith("/v1/messages")) {
    sendJson(res, 404, { error: "Not found. POST /v1/messages or GET /health" });
    return;
  }

  if (!requireSecret(req)) return sendJson(res, 401, { error: "unauthorized" });

  let body = "";
  req.on("data", (chunk) => (body += chunk));
  req.on("end", () => {
    let request;
    try {
      request = JSON.parse(body);
    } catch {
      return sendJson(res, 400, { error: "Invalid JSON body" });
    }

    const stream = request.stream ?? false;
    const cliModel = request.model || DEFAULT_MODEL;
    const sessionHeader = req.headers["x-session-id"] ?? null;
    const convKey = conversationKey(request.messages || [], sessionHeader);
    const existingSession = convKey ? sessions.get(convKey) : null;
    const isFirstTurn = !existingSession;
    const systemPrompt = getSystemPrompt(request.system);
    const userPrompt = getLastUserMessage(request.messages || []);

    console.log(
      `[${new Date().toISOString()}] model=${cliModel} stream=${stream} turns=${(request.messages ?? []).length} session=${existingSession?.cliSessionId ?? "NEW"} prompt=${userPrompt.slice(0, 60).replace(/\n/g, " ")}...`,
    );

    const args = buildCliArgs({ stream, cliModel, existingSession, isFirstTurn, systemPrompt });
    if (stream) handleStreaming(args, userPrompt, cliModel, res, convKey);
    else handleBlocking(args, userPrompt, cliModel, res, convKey);
  });
}

const server = createServer(handleRequest);
server.listen(PORT, HOST, () => {
  console.log(
    [
      "┌────────────────────────────────────────────────────┐",
      `│  HireLoop LLM Bridge — http://${HOST}:${PORT}`.padEnd(53) + "│",
      "├────────────────────────────────────────────────────┤",
      `│  claude-bin: ${CLAUDE_BIN}`.padEnd(53) + "│",
      `│  default-model: ${DEFAULT_MODEL}`.padEnd(53) + "│",
      `│  shared-secret: ${SHARED_SECRET ? "enabled" : "disabled (loopback-only)"}`.padEnd(53) + "│",
      "├────────────────────────────────────────────────────┤",
      "│  POST /v1/messages    — Anthropic Messages API     │",
      "│  GET  /health         — liveness                   │",
      "│  GET  /sessions       — active CLI sessions        │",
      "└────────────────────────────────────────────────────┘",
    ].join("\n"),
  );
});

function shutdown(sig) {
  console.log(`${sig} received, shutting down`);
  server.close(() => process.exit(0));
  setTimeout(() => process.exit(1), 5000).unref();
}
process.on("SIGINT", () => shutdown("SIGINT"));
process.on("SIGTERM", () => shutdown("SIGTERM"));
