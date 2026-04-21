# HireLoop LLM Bridge

HTTP shim that translates Anthropic Messages API requests into `claude -p` CLI
invocations. Lets backend LLM calls consume a Claude subscription in place of a
paid `ANTHROPIC_API_KEY` — intended for **async batch work only** (L2
evaluation, CV generation, interview prep extraction + generation, negotiation
playbook).

## Routing split (important)

HireLoop's backend routes LLM calls in two pools:

| Route | Callers | Client | Notes |
|---|---|---|---|
| `realtime` | Chat / agent graph | Always `api.anthropic.com` | Subprocess latency kills SSE streaming; never routed through bridge |
| `batch` | interview_prep, negotiation, cv_optimizer, evaluation (L2) | `llm-bridge` when `ANTHROPIC_BASE_URL` is set, else real API | Safe to ride a Claude subscription |

The decision is at the call site via `complete_with_cache(..., route="batch")`
(see `backend/src/hireloop/core/llm/anthropic_client.py`). Chat never opts in
and always uses a real `ANTHROPIC_API_KEY`.

## Local dev

```bash
# Build + start
docker compose -f llm-bridge/docker-compose.yml up -d --build

# First-time auth inside the container (device-code flow → paste the URL into
# your browser, sign in with your Claude subscription, copy the code back).
docker exec -it llm-bridge claude login

# Verify
curl -s http://127.0.0.1:8019/health
# → {"status":"ok","claude_bin":"claude","active_sessions":0,"auth_required":false}

# Point the backend at it by adding to backend/.env:
#   ANTHROPIC_BASE_URL=http://127.0.0.1:8019
# Then restart the backend.

# Exercise via Playwright:
cd user-portal && pnpm exec playwright test
```

Auth state lives in the `claude-auth` named volume and survives `docker compose
down`. Run `docker volume rm llm-bridge_claude-auth` to wipe it and force a
fresh login.

## Deploy to EC2

Same image, different mount source. See `infrastructure/cdk/lib/app-stack.ts`
where the service is added to the `SseInstance` compose heredoc, with
`/opt/hireloop/claude-auth:/root/.claude` as the bind mount. After
`cdk deploy`:

```bash
aws ssm start-session --target $(aws ssm get-parameter \
  --name /hireloop/dev/sse-instance-id --query Parameter.Value --output text) \
  --profile hireloop
# inside the session:
sudo docker exec -it llm-bridge claude login
exit
```

Backend pulls `ANTHROPIC_BASE_URL=http://llm-bridge:8019` from the CDK-injected
env. No code change required.

## Security posture

- `LLM_BRIDGE_SHARED_SECRET` — set to require `x-bridge-secret` header on every
  request. Unset means no auth (only safe on loopback or private networks).
- Container binds to `127.0.0.1:8019` on the host locally. On EC2 the port is
  not published to the host at all — the backend container reaches it by
  compose-network DNS name `llm-bridge`.
- Anthropic ToS note: subscription-backed CLIs are licensed for interactive
  human use. Serving HTTP traffic is defensible for solo dogfood; production
  user traffic should not depend on this.

## Endpoints

- `POST /v1/messages` — Anthropic Messages API shape. Supports `stream: true`
  (SSE) and `stream: false` (JSON).
- `GET /health` — liveness.
- `GET /sessions` — active CLI session list (gated by shared secret if set).

## Why not systemd?

Symmetry with the rest of HireLoop infra (backend/caddy/redis all run as
compose services on the same EC2). Same image, same compose primitives, same
logging pattern.
