# CareerAgent Phase 1 — Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Scaffold the CareerAgent monorepo, stand up backend infrastructure (FastAPI + Postgres + Redis + Alembic), wire Cognito authentication, and implement the profile vault (user + profile + resume upload/parse). End state: A new user can sign up, upload a resume, and have it parsed into a structured profile.

**Architecture:** Monorepo with `backend/` (FastAPI), `user-portal/` (React+Vite, stub only in Phase 1), `admin-ui/` (stub), `marketing/` (stub), `pdf-render/` (stub), `infrastructure/cdk/`. Local dev via docker-compose (Postgres, Redis, Inngest dev server). Real AWS deployment is out of scope for Phase 1 — it's stubbed in CDK so Phase 5 can complete it.

**Tech Stack:** Python 3.12 + uv + FastAPI + SQLAlchemy 2.0 (async) + Alembic + asyncpg + Redis + python-jose (JWT) + pypdf + python-docx + optional Anthropic SDK for structured resume enrichment + pytest + pytest-asyncio + pytest-postgresql. Node 20 + pnpm 9 workspaces + React 18 + Vite 5 + TypeScript 5 + Tailwind 3. AWS CDK 2.x (TypeScript).

**Resume parsing strategy (foundation):** Prefer **deterministic extraction** (pypdf / python-docx text, light heuristics for sections). Optionally call **Claude** to structure text into `parsed_resume_json` when `ANTHROPIC_API_KEY` is set — keep behind a flag or post-MVP if cost/latency matters. Tests must not require a live LLM.

**Reference spec:** `docs/superpowers/specs/2026-04-10-careeragent-design.md` — in particular **§ Data Model** (Postgres schema), Appendices A (versions), B (env vars), D (AI prompts — not schema), H (indexes), I (state machines), J (error format), K (Cognito config), Q (migrations), U (docker-compose).

**Phase 1 scope (what's IN):**
- Monorepo structure + pnpm workspaces + uv
- docker-compose for Postgres + Redis + Inngest dev
- FastAPI backend skeleton with health checks, error handling, request IDs
- Alembic setup + initial schema migration (Phase 1 tables only)
- Cognito JWT middleware + `/auth/me` endpoint
- User + Profile + StarStory tables
- Profile CRUD endpoints (`GET /profile`, `PUT /profile`, `DELETE /profile`)
- Resume upload endpoint + PDF/DOCX parser + S3 storage abstraction (LocalStack for tests, real S3 later)
- Onboarding state machine
- GDPR export endpoint (data export to JSON)
- CDK stack skeletons (Network, Data, Auth) — not deployed
- CI workflow skeleton (lint, test)
- Frontend stubs (empty Vite apps with Tailwind + auth client) — no real pages yet

**Phase 1 scope (what's OUT):**
- Agent/LangGraph (Phase 2)
- Modules 1-6 (Phases 2-4)
- Inngest functions (Phase 3)
- Stripe subscriptions (Phase 2)
- Real AWS deployment (Phase 5)
- Full UX (Phase 5)

### Roadmap: this plan vs the design spec

The [design spec](../specs/2026-04-10-careeragent-design.md) uses “Phase 1 product” to mean **all six feature modules** in the first release. **This document** is the **foundation** milestone only (scaffold, auth, profile, resume). Later plans cover the agent, modules, Inngest, Stripe UX, and deployment.

| Engineering milestone | Scope (summary) |
|----------------------|-----------------|
| **This plan (foundation)** | Monorepo, FastAPI, Postgres, Redis, Alembic, Cognito JWT, profile + resume + GDPR, CDK stubs, CI, frontend stubs |
| Later (per upcoming plans) | LangGraph agent, six modules, Inngest, Stripe, AWS deploy, full UX |

### Security baseline (foundation)

- **CORS:** `allow_origins=["*"]` only in local dev; production uses `CORS_ORIGINS` from settings (see spec Appendix B).
- **Uploads:** Enforce max size (10MB per spec) and MIME allowlist before parsing.
- **Auth:** Every mutating route uses JWT dependency; no `user_id` from client body.
- **Malware scanning:** Out of scope for foundation; document if deferred to Phase 5+.

---

## File Structure Plan

```
career-agent/
├── .github/
│   └── workflows/
│       └── ci.yml                            [CREATE T2]
├── .gitignore                                [CREATE T1]
├── .editorconfig                             [CREATE T1]
├── README.md                                 [CREATE T1]
├── CLAUDE.md                                 [CREATE T1]
├── pnpm-workspace.yaml                       [CREATE T1]
├── package.json                              [CREATE T1]
├── docker-compose.yml                        [CREATE T3]
│
├── backend/
│   ├── pyproject.toml                        [CREATE T4]
│   ├── uv.lock                               [CREATE T4]
│   ├── .env.example                          [CREATE T4]
│   ├── alembic.ini                           [CREATE T8]
│   ├── Dockerfile                            [CREATE T4]
│   ├── entrypoint.sh                         [CREATE T4]
│   ├── migrations/
│   │   ├── env.py                            [CREATE T8]
│   │   ├── script.py.mako                    [CREATE T8]
│   │   └── versions/
│   │       └── 0001_phase1_schema.py         [CREATE T10]
│   ├── src/career_agent/
│   │   ├── __init__.py                       [CREATE T4]
│   │   ├── main.py                           [CREATE T5]
│   │   ├── config.py                         [CREATE T6]
│   │   ├── logging.py                        [CREATE T6]
│   │   ├── db.py                             [CREATE T7]
│   │   ├── api/
│   │   │   ├── __init__.py                   [CREATE T5]
│   │   │   ├── deps.py                       [CREATE T12]
│   │   │   ├── errors.py                     [CREATE T11]
│   │   │   ├── health.py                     [CREATE T5]
│   │   │   ├── auth.py                       [CREATE T13]
│   │   │   └── profile.py                    [CREATE T15, T16, T17]
│   │   ├── models/
│   │   │   ├── __init__.py                   [CREATE T9]
│   │   │   ├── base.py                       [CREATE T9]
│   │   │   ├── user.py                       [CREATE T9]
│   │   │   ├── subscription.py               [CREATE T9]
│   │   │   ├── profile.py                    [CREATE T9]
│   │   │   └── star_story.py                 [CREATE T9]
│   │   ├── schemas/
│   │   │   ├── __init__.py                   [CREATE T9]
│   │   │   ├── common.py                     [CREATE T9]
│   │   │   ├── user.py                       [CREATE T9]
│   │   │   ├── profile.py                    [CREATE T9]
│   │   │   └── error.py                      [CREATE T11]
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py                       [CREATE T12]
│   │   │   ├── profile.py                    [CREATE T15]
│   │   │   ├── resume_parser.py              [CREATE T16]
│   │   │   └── storage.py                    [CREATE T14]
│   │   └── integrations/
│   │       ├── __init__.py
│   │       ├── cognito.py                    [CREATE T12]
│   │       └── s3.py                         [CREATE T14]
│   └── tests/
│       ├── __init__.py
│       ├── conftest.py                       [CREATE T7]
│       ├── fixtures/
│       │   └── resumes/
│       │       ├── sample.pdf                [CREATE T16]
│       │       └── sample.docx               [CREATE T16]
│       ├── unit/
│       │   ├── test_config.py                [CREATE T6]
│       │   ├── test_resume_parser.py         [CREATE T16]
│       │   └── test_storage.py               [CREATE T14]
│       └── integration/
│           ├── test_health.py                [CREATE T5]
│           ├── test_auth_middleware.py       [CREATE T13]
│           ├── test_profile_crud.py          [CREATE T15]
│           ├── test_resume_upload.py         [CREATE T17]
│           └── test_gdpr_export.py           [CREATE T18]
│
├── user-portal/
│   ├── package.json                          [CREATE T19]
│   ├── tsconfig.json                         [CREATE T19]
│   ├── vite.config.ts                        [CREATE T19]
│   ├── tailwind.config.ts                    [CREATE T19]
│   ├── postcss.config.js                     [CREATE T19]
│   ├── index.html                            [CREATE T19]
│   ├── .env.example                          [CREATE T19]
│   └── src/
│       ├── main.tsx                          [CREATE T19]
│       ├── App.tsx                           [CREATE T19]
│       └── index.css                         [CREATE T19]
│
├── admin-ui/                                 [CREATE T20 - stub mirror of user-portal]
├── marketing/                                [CREATE T21 - stub mirror of user-portal]
├── pdf-render/
│   ├── package.json                          [CREATE T22]
│   ├── tsconfig.json                         [CREATE T22]
│   ├── Dockerfile                            [CREATE T22]
│   ├── .env.example                          [CREATE T22]
│   └── src/
│       ├── server.ts                         [CREATE T22]
│       └── render.ts                         [CREATE T22]
│
├── infrastructure/
│   └── cdk/
│       ├── package.json                      [CREATE T23]
│       ├── tsconfig.json                     [CREATE T23]
│       ├── cdk.json                          [CREATE T23]
│       ├── bin/
│       │   └── career-agent.ts               [CREATE T23]
│       └── lib/
│           ├── network-stack.ts              [CREATE T23]
│           ├── data-stack.ts                 [CREATE T23]
│           └── auth-stack.ts                 [CREATE T23]
│
└── docs/
    └── superpowers/
        ├── specs/
        │   └── 2026-04-10-careeragent-design.md   [EXISTS]
        └── plans/
            └── 2026-04-10-phase1-foundation.md    [THIS FILE]
```

---

## Task 1: Repository Initialization

**Files:**
- Create: `.gitignore`
- Create: `.editorconfig`
- Create: `README.md`
- Create: `CLAUDE.md`
- Create: `package.json`
- Create: `pnpm-workspace.yaml`

- [ ] **Step 1: Initialize git repo**

```bash
cd ~/projects/personal/career-agent
git init
```

- [ ] **Step 2: Create `.gitignore`**

```
# Python
__pycache__/
*.py[cod]
*$py.class
.Python
*.so
.venv/
.env
.env.local
.env.*.local
.pytest_cache/
.coverage
.mypy_cache/
.ruff_cache/
htmlcov/
dist/
build/
*.egg-info/

# Node
node_modules/
dist/
*.log
.turbo/

# CDK
cdk.out/
cdk.context.json

# IDE
.vscode/
.idea/
*.swp
.DS_Store

# Secrets
*.pem
*.key
.env*

# Superpowers
.superpowers/brainstorm/
```

- [ ] **Step 3: Create `.editorconfig`**

```
root = true

[*]
charset = utf-8
end_of_line = lf
insert_final_newline = true
indent_style = space
trim_trailing_whitespace = true

[*.{py}]
indent_size = 4
max_line_length = 100

[*.{ts,tsx,js,jsx,json,yml,yaml,md}]
indent_size = 2

[Makefile]
indent_style = tab
```

- [ ] **Step 4: Create root `package.json`**

```json
{
  "name": "career-agent",
  "private": true,
  "version": "0.1.0",
  "scripts": {
    "dev": "echo 'Run each service individually'",
    "lint": "pnpm -r lint",
    "build": "pnpm -r build",
    "test": "pnpm -r test"
  },
  "devDependencies": {
    "typescript": "^5.6.3"
  },
  "packageManager": "pnpm@9.12.0"
}
```

- [ ] **Step 5: Create `pnpm-workspace.yaml`**

```yaml
packages:
  - "user-portal"
  - "admin-ui"
  - "marketing"
  - "pdf-render"
  - "infrastructure/cdk"
```

- [ ] **Step 6: Create minimal `README.md`**

```markdown
# CareerAgent

Candidate-side AI career assistant SaaS. See `docs/superpowers/specs/2026-04-10-careeragent-design.md` for the full spec.

## Quick Start

\`\`\`bash
docker-compose up -d
cd backend && uv sync && uv run alembic upgrade head && uv run uvicorn career_agent.main:app --reload
cd user-portal && pnpm install && pnpm dev
\`\`\`
```

- [ ] **Step 7: Create `CLAUDE.md`**

```markdown
# CareerAgent

See `docs/superpowers/specs/2026-04-10-careeragent-design.md` for the full spec and Implementation Appendix.

## Code Conventions

- Python: ruff + black + mypy strict. Files under 300 lines. Async-first.
- TypeScript: strict mode, no `any`. Components under 200 lines.
- Every API endpoint has a Pydantic request/response schema.
- Every DB query scoped by `user_id` at the service layer.
- AI calls logged via `usage_events`.
- Tests required for every new module.

## Quick Start

\`\`\`bash
docker-compose up -d
cd backend && uv sync && uv run alembic upgrade head && uv run uvicorn career_agent.main:app --reload
\`\`\`
```

- [ ] **Step 8: Commit**

```bash
git add .gitignore .editorconfig README.md CLAUDE.md package.json pnpm-workspace.yaml
git commit -m "chore: initialize monorepo structure"
```

---

## Task 2: CI Workflow Skeleton

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Create CI workflow**

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  backend-test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: career_agent_test
        ports: ['5432:5432']
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      redis:
        image: redis:7-alpine
        ports: ['6379:6379']
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
        with:
          version: "latest"
      - name: Set up Python
        run: uv python install 3.12
      - name: Install dependencies
        working-directory: backend
        run: uv sync --all-extras --dev
      - name: Lint (ruff)
        working-directory: backend
        run: uv run ruff check src/ tests/
      - name: Format check (black)
        working-directory: backend
        run: uv run black --check src/ tests/
      - name: Type check (mypy)
        working-directory: backend
        run: uv run mypy src/
      - name: Run migrations
        working-directory: backend
        env:
          DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/career_agent_test
        run: uv run alembic upgrade head
      - name: Run tests
        working-directory: backend
        env:
          DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/career_agent_test
          REDIS_URL: redis://localhost:6379/0
          ENVIRONMENT: test
          COGNITO_USER_POOL_ID: us-east-1_test
          COGNITO_CLIENT_ID: testclient
          COGNITO_REGION: us-east-1
          COGNITO_JWKS_URL: http://localhost/jwks
          ANTHROPIC_API_KEY: test-key
        run: uv run pytest -v --cov=career_agent --cov-report=xml

  frontend-lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v4
        with:
          version: 9
      - uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: 'pnpm'
      - run: pnpm install --frozen-lockfile
      - run: pnpm -r build
```

After **Task 23** (CDK scaffold exists), add a **`cdk-synth`** job so broken infra fails CI:

```yaml
  cdk-synth:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v4
        with:
          version: 9
      - uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: 'pnpm'
          cache-dependency-path: infrastructure/cdk/pnpm-lock.yaml
      - name: Install CDK dependencies
        working-directory: infrastructure/cdk
        run: pnpm install --frozen-lockfile
      - name: CDK synth
        working-directory: infrastructure/cdk
        run: pnpm run synth
```

(If `pnpm-lock.yaml` is not yet committed in Task 2, add this job in the same commit as Task 23.)

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: add lint/test workflow"
```

---

## Task 3: docker-compose for Local Dev

**Files:**
- Create: `docker-compose.yml`

- [ ] **Step 1: Create `docker-compose.yml`** (matches Appendix U)

```yaml
version: "3.9"
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: career_agent
    ports: ["5432:5432"]
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
    command: redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  inngest:
    image: inngest/inngest:latest
    ports: ["8288:8288"]
    command: inngest dev -u http://host.docker.internal:8000/api/v1/inngest
    extra_hosts:
      - host.docker.internal:host-gateway
    profiles: ["inngest"]

volumes:
  postgres_data:
```

The **`inngest` service uses Docker Compose profile `inngest`**. It does **not** start with plain `docker-compose up -d` — use:

`docker-compose --profile inngest up -d`

(or add `inngest` to default services when you need the local Inngest UI at `http://localhost:8288`). Postgres + Redis start without the profile.

- [ ] **Step 2: Verify it comes up**

```bash
docker-compose up -d postgres redis
docker-compose ps
```
Expected: both containers `healthy`.

- [ ] **Step 3: Commit**

```bash
git add docker-compose.yml
git commit -m "chore: add docker-compose for local dev"
```

---

## Task 4: Backend Python Project Setup

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/uv.lock` (generated)
- Create: `backend/.env.example`
- Create: `backend/Dockerfile`
- Create: `backend/entrypoint.sh`
- Create: `backend/src/career_agent/__init__.py`

- [ ] **Step 1: Create `backend/pyproject.toml`**

```toml
[project]
name = "career-agent"
version = "0.1.0"
description = "CareerAgent backend — candidate-side AI career assistant"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.32.0",
    "sqlalchemy>=2.0.35",
    "asyncpg>=0.30.0",
    "alembic>=1.13.3",
    "pydantic>=2.9.0",
    "pydantic-settings>=2.6.0",
    "boto3>=1.35.0",
    "anthropic>=0.40.0",
    "redis>=5.1.0",
    "httpx>=0.27.0",
    "python-jose[cryptography]>=3.3.0",
    "pypdf>=5.1.0",
    "python-docx>=1.1.2",
    "python-multipart>=0.0.17",
    "structlog>=24.4.0",
    "sentry-sdk[fastapi]>=2.18.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.24.0",
    "pytest-cov>=6.0.0",
    "pytest-postgresql>=6.1.0",
    "respx>=0.21.0",
    "ruff>=0.7.0",
    "black>=24.10.0",
    "mypy>=1.13.0",
    "types-python-jose>=3.3.4",
    "moto[s3]>=5.0.0",
]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP", "B", "ASYNC"]

[tool.black]
line-length = 100
target-version = ["py312"]

[tool.mypy]
python_version = "3.12"
strict = true
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
pythonpath = ["src"]

[tool.coverage.run]
source = ["src/career_agent"]
branch = true

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/career_agent"]
```

- [ ] **Step 2: Create `backend/.env.example`** (matches Appendix B backend section)

```bash
# Environment
ENVIRONMENT=dev
LOG_LEVEL=DEBUG

# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/career_agent
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20

# Redis
REDIS_URL=redis://localhost:6379/0

# AWS
AWS_REGION=us-east-1
AWS_S3_BUCKET=career-agent-dev-assets

# Cognito
COGNITO_USER_POOL_ID=us-east-1_xxxxxxxxx
COGNITO_CLIENT_ID=xxxxxxxxxxxxxxxxxxxxxxxxxx
COGNITO_REGION=us-east-1
COGNITO_JWKS_URL=https://cognito-idp.us-east-1.amazonaws.com/us-east-1_xxxxxxxxx/.well-known/jwks.json

# AI Providers
ANTHROPIC_API_KEY=sk-ant-placeholder
GOOGLE_API_KEY=placeholder
CLAUDE_MODEL=claude-sonnet-4-6
GEMINI_MODEL=gemini-2.0-flash-exp
ENABLE_PROMPT_CACHING=true

# CORS
CORS_ORIGINS=http://localhost:5173,http://localhost:5174,http://localhost:5175

# Sentry
SENTRY_DSN=
SENTRY_ENVIRONMENT=dev
```

- [ ] **Step 3: Create `backend/Dockerfile` (local dev)**

```dockerfile
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY src/ ./src/
COPY migrations/ ./migrations/
COPY alembic.ini ./
COPY entrypoint.sh ./
RUN chmod +x entrypoint.sh

ENV PYTHONPATH=/app/src

ENTRYPOINT ["./entrypoint.sh"]
CMD ["uv", "run", "uvicorn", "career_agent.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 4: Create `backend/entrypoint.sh`**

```bash
#!/bin/sh
set -e

echo "Running migrations..."
uv run alembic upgrade head

echo "Starting server..."
exec "$@"
```

- [ ] **Step 5: Create `backend/src/career_agent/__init__.py`**

```python
"""CareerAgent backend package."""

__version__ = "0.1.0"
```

- [ ] **Step 6: Install dependencies**

```bash
cd backend
uv sync --all-extras --dev
```
Expected: `uv.lock` generated, `.venv/` created, no errors.

- [ ] **Step 7: Commit**

```bash
git add backend/pyproject.toml backend/uv.lock backend/.env.example backend/Dockerfile backend/entrypoint.sh backend/src/career_agent/__init__.py
git commit -m "feat(backend): initialize Python project with uv"
```

---

## Task 5: FastAPI App Skeleton + Health Check

**Files:**
- Create: `backend/src/career_agent/main.py`
- Create: `backend/src/career_agent/api/__init__.py`
- Create: `backend/src/career_agent/api/health.py`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/integration/__init__.py`
- Create: `backend/tests/integration/test_health.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/integration/test_health.py`:

```python
import pytest
from httpx import AsyncClient, ASGITransport
from career_agent.main import app


@pytest.mark.asyncio
async def test_health_endpoint_returns_ok():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_health_ready_endpoint_returns_ok_when_deps_up():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health/ready")
    # When deps are mocked up, this should be 200
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "checks" in body
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend
uv run pytest tests/integration/test_health.py -v
```
Expected: FAIL with `ModuleNotFoundError: No module named 'career_agent.main'` or similar.

- [ ] **Step 3: Create `backend/src/career_agent/api/__init__.py`**

```python
"""API routers."""
```

- [ ] **Step 4: Create `backend/src/career_agent/api/health.py`**

```python
from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def health() -> dict[str, str]:
    """Basic liveness check — returns 200 if the process is alive."""
    return {"status": "ok"}


@router.get("/ready")
async def ready() -> dict[str, object]:
    """Readiness check — verifies dependencies are reachable.

    Phase 1: stub returning ok. Later tasks add real DB/Redis checks.
    """
    checks: dict[str, str] = {
        "database": "ok",
        "redis": "ok",
    }
    return {"status": "ok", "checks": checks}
```

- [ ] **Step 5: Create `backend/src/career_agent/main.py`**

```python
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from career_agent.api import health


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan — startup and shutdown hooks."""
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="CareerAgent API",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS will be configured from settings in T6
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router, prefix="/api/v1")

    return app


app = create_app()
```

- [ ] **Step 6: Create `backend/tests/__init__.py` and `backend/tests/integration/__init__.py`**

Both are empty files:
```python
```

- [ ] **Step 7: Run test to verify it passes**

```bash
cd backend
uv run pytest tests/integration/test_health.py -v
```
Expected: Both tests PASS.

- [ ] **Step 8: Manually smoke test**

```bash
cd backend
uv run uvicorn career_agent.main:app --reload
# In another terminal:
curl http://localhost:8000/api/v1/health
curl http://localhost:8000/api/v1/health/ready
```
Expected: Both return `{"status": "ok", ...}`.

- [ ] **Step 9: Commit**

```bash
git add backend/src/career_agent/main.py backend/src/career_agent/api/__init__.py backend/src/career_agent/api/health.py backend/tests/__init__.py backend/tests/integration/__init__.py backend/tests/integration/test_health.py
git commit -m "feat(backend): add FastAPI app skeleton with health endpoints"
```

---

## Task 6: Settings (Pydantic) + Logging

**Files:**
- Create: `backend/src/career_agent/config.py`
- Create: `backend/src/career_agent/logging.py`
- Create: `backend/tests/unit/__init__.py`
- Create: `backend/tests/unit/test_config.py`
- Modify: `backend/src/career_agent/main.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/unit/__init__.py` (empty) and `backend/tests/unit/test_config.py`:

```python
import os
import pytest

from career_agent.config import Settings


def test_settings_loads_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("COGNITO_USER_POOL_ID", "us-east-1_abc")
    monkeypatch.setenv("COGNITO_CLIENT_ID", "client123")
    monkeypatch.setenv("COGNITO_REGION", "us-east-1")
    monkeypatch.setenv("COGNITO_JWKS_URL", "https://example.com/jwks")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:5174")

    settings = Settings()
    assert settings.environment == "test"
    assert settings.database_url == "postgresql+asyncpg://user:pass@localhost/db"
    assert settings.cors_origins == ["http://localhost:5173", "http://localhost:5174"]
    assert settings.is_dev is False
    assert settings.is_test is True


def test_settings_cors_origins_parsed_from_comma_list(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://x/x")
    monkeypatch.setenv("REDIS_URL", "redis://localhost")
    monkeypatch.setenv("COGNITO_USER_POOL_ID", "x")
    monkeypatch.setenv("COGNITO_CLIENT_ID", "x")
    monkeypatch.setenv("COGNITO_REGION", "x")
    monkeypatch.setenv("COGNITO_JWKS_URL", "https://x")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "x")
    monkeypatch.setenv("CORS_ORIGINS", "http://a.com, http://b.com")

    settings = Settings()
    assert settings.cors_origins == ["http://a.com", "http://b.com"]
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend
uv run pytest tests/unit/test_config.py -v
```
Expected: FAIL with ImportError on `Settings`.

- [ ] **Step 3: Create `backend/src/career_agent/config.py`**

```python
from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Environment
    environment: Literal["dev", "sandbox", "prod", "test"] = "dev"
    log_level: str = "INFO"

    # Database
    database_url: str
    database_pool_size: int = 10
    database_max_overflow: int = 20

    # Redis
    redis_url: str

    # AWS
    aws_region: str = "us-east-1"
    aws_s3_bucket: str = "career-agent-dev-assets"

    # Cognito
    cognito_user_pool_id: str
    cognito_client_id: str
    cognito_region: str
    cognito_jwks_url: str

    # AI
    anthropic_api_key: str
    google_api_key: str = ""
    claude_model: str = "claude-sonnet-4-6"
    gemini_model: str = "gemini-2.0-flash-exp"
    enable_prompt_caching: bool = True

    # CORS
    cors_origins: list[str] = Field(default_factory=list)

    # Sentry
    sentry_dsn: str = ""
    sentry_environment: str = "dev"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_cors_origins(cls, v: object) -> object:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @property
    def is_dev(self) -> bool:
        return self.environment == "dev"

    @property
    def is_test(self) -> bool:
        return self.environment == "test"

    @property
    def is_prod(self) -> bool:
        return self.environment == "prod"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
```

- [ ] **Step 4: Create `backend/src/career_agent/logging.py`**

```python
import logging
import sys

import structlog

from career_agent.config import get_settings


def configure_logging() -> None:
    settings = get_settings()
    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=level,
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer() if not settings.is_dev else structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)  # type: ignore[return-value]
```

- [ ] **Step 5: Wire settings into `main.py`**

Replace the existing `create_app` in `backend/src/career_agent/main.py`:

```python
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from career_agent.api import health
from career_agent.config import get_settings
from career_agent.logging import configure_logging, get_logger


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    log = get_logger("career_agent.main")
    settings = get_settings()
    log.info("startup", environment=settings.environment)
    yield
    log.info("shutdown")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="CareerAgent API",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router, prefix="/api/v1")

    return app


app = create_app()
```

- [ ] **Step 6: Run unit tests**

```bash
cd backend
uv run pytest tests/unit/test_config.py -v
```
Expected: Both tests PASS.

- [ ] **Step 7: Run full test suite**

```bash
cd backend
uv run pytest -v
```
Expected: All tests pass. Health endpoint tests may need env vars set — if they fail, add them to `conftest.py` in T7.

- [ ] **Step 8: Commit**

```bash
git add backend/src/career_agent/config.py backend/src/career_agent/logging.py backend/src/career_agent/main.py backend/tests/unit/__init__.py backend/tests/unit/test_config.py
git commit -m "feat(backend): add Pydantic settings and structured logging"
```

---

## Task 7: Database Session + conftest

**Files:**
- Create: `backend/src/career_agent/db.py`
- Create: `backend/tests/conftest.py`

- [ ] **Step 1: Create `backend/src/career_agent/db.py`**

```python
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
    AsyncEngine,
)

from career_agent.config import get_settings

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(
            settings.database_url,
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
            pool_pre_ping=True,
            echo=settings.is_dev,
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
    return _session_factory


async def get_db() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency that yields an AsyncSession."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def dispose_engine() -> None:
    """Dispose the engine — used in tests."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None
```

- [ ] **Step 2: Create `backend/tests/conftest.py`**

```python
import os
from typing import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Set minimal env before importing app
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault(
    "DATABASE_URL",
    os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/career_agent_test",
    ),
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("COGNITO_USER_POOL_ID", "us-east-1_test")
os.environ.setdefault("COGNITO_CLIENT_ID", "testclient")
os.environ.setdefault("COGNITO_REGION", "us-east-1")
os.environ.setdefault("COGNITO_JWKS_URL", "http://localhost/jwks")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:5173")

from career_agent.db import dispose_engine, get_engine  # noqa: E402
from career_agent.main import app  # noqa: E402


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncIterator[AsyncSession]:
    """Provide a clean DB session per test. Requires real Postgres running."""
    engine = get_engine()
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with engine.connect() as conn:
        async with conn.begin() as transaction:
            session = session_factory(bind=conn)
            try:
                yield session
            finally:
                await session.close()
                await transaction.rollback()


@pytest_asyncio.fixture(autouse=True, scope="session")
async def cleanup_engine() -> AsyncIterator[None]:
    yield
    await dispose_engine()
```

- [ ] **Step 3: Run tests to verify no regressions**

```bash
cd backend
docker-compose up -d postgres redis
uv run pytest -v
```
Expected: Existing tests still pass. DB fixture is not yet used by any test.

- [ ] **Step 4: Commit**

```bash
git add backend/src/career_agent/db.py backend/tests/conftest.py
git commit -m "feat(backend): add async DB session and test fixtures"
```

---

## Task 8: Alembic Setup

**Files:**
- Create: `backend/alembic.ini`
- Create: `backend/migrations/env.py`
- Create: `backend/migrations/script.py.mako`

- [ ] **Step 1: Create `backend/alembic.ini`**

```ini
[alembic]
script_location = migrations
prepend_sys_path = src
version_path_separator = os
sqlalchemy.url =

[post_write_hooks]
hooks = black
black.type = console_scripts
black.entrypoint = black
black.options = -l 100

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

- [ ] **Step 2: Create `backend/migrations/script.py.mako`**

```python
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

# revision identifiers, used by Alembic.
revision: str = ${repr(up_revision)}
down_revision: Union[str, None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
```

- [ ] **Step 3: Create `backend/migrations/env.py`**

```python
import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

from career_agent.config import get_settings
from career_agent.models.base import Base
from career_agent.models import *  # noqa: F401,F403 - register all models

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", get_settings().database_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
```

- [ ] **Step 4: Commit**

```bash
git add backend/alembic.ini backend/migrations/env.py backend/migrations/script.py.mako
git commit -m "feat(backend): wire Alembic migrations with async engine"
```

---

## Task 9: Phase 1 SQLAlchemy Models + Schemas

**Files:**
- Create: `backend/src/career_agent/models/__init__.py`
- Create: `backend/src/career_agent/models/base.py`
- Create: `backend/src/career_agent/models/user.py`
- Create: `backend/src/career_agent/models/subscription.py`
- Create: `backend/src/career_agent/models/profile.py`
- Create: `backend/src/career_agent/models/star_story.py`
- Create: `backend/src/career_agent/schemas/__init__.py`
- Create: `backend/src/career_agent/schemas/common.py`
- Create: `backend/src/career_agent/schemas/user.py`
- Create: `backend/src/career_agent/schemas/profile.py`

- [ ] **Step 1: Create `backend/src/career_agent/models/base.py`**

```python
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class UUIDPKMixin:
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
```

- [ ] **Step 2: Create `backend/src/career_agent/models/user.py`**

```python
from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from career_agent.models.base import Base, TimestampMixin, UUIDPKMixin

if TYPE_CHECKING:
    from career_agent.models.profile import Profile
    from career_agent.models.subscription import Subscription
    from career_agent.models.star_story import StarStory


class User(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "users"

    cognito_sub: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    profile: Mapped["Profile | None"] = relationship(
        "Profile", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    subscription: Mapped["Subscription | None"] = relationship(
        "Subscription", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    star_stories: Mapped[list["StarStory"]] = relationship(
        "StarStory", back_populates="user", cascade="all, delete-orphan"
    )
```

- [ ] **Step 3: Create `backend/src/career_agent/models/subscription.py`**

```python
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from career_agent.models.base import Base, TimestampMixin, UUIDPKMixin

if TYPE_CHECKING:
    from career_agent.models.user import User


class Subscription(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "subscriptions"

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), unique=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(255), unique=True)
    plan: Mapped[str] = mapped_column(String(50), nullable=False)  # 'trial' | 'pro' | 'cancelled'
    trial_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(50), nullable=False)  # 'active' | 'past_due' | 'cancelled'

    user: Mapped["User"] = relationship("User", back_populates="subscription")
```

- [ ] **Step 4: Create `backend/src/career_agent/models/profile.py`**

```python
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from career_agent.models.base import Base, TimestampMixin, UUIDPKMixin

if TYPE_CHECKING:
    from career_agent.models.user import User


class Profile(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "profiles"

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    master_resume_md: Mapped[str | None] = mapped_column(Text)
    master_resume_s3: Mapped[str | None] = mapped_column(String(500))
    parsed_resume_json: Mapped[dict | None] = mapped_column(JSONB)
    target_roles: Mapped[list | None] = mapped_column(JSONB)
    target_locations: Mapped[list | None] = mapped_column(JSONB)
    min_salary: Mapped[int | None] = mapped_column(Integer)
    preferred_industries: Mapped[list | None] = mapped_column(JSONB)
    linkedin_url: Mapped[str | None] = mapped_column(String(500))
    github_url: Mapped[str | None] = mapped_column(String(500))
    portfolio_url: Mapped[str | None] = mapped_column(String(500))
    onboarding_state: Mapped[str] = mapped_column(
        String(50), nullable=False, default="resume_upload"
    )  # 'resume_upload' | 'preferences' | 'done'

    user: Mapped["User"] = relationship("User", back_populates="profile")
```

- [ ] **Step 5: Create `backend/src/career_agent/models/star_story.py`**

```python
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from career_agent.models.base import Base, TimestampMixin, UUIDPKMixin

if TYPE_CHECKING:
    from career_agent.models.user import User


class StarStory(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "star_stories"

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    situation: Mapped[str] = mapped_column(Text, nullable=False)
    task: Mapped[str] = mapped_column(Text, nullable=False)
    action: Mapped[str] = mapped_column(Text, nullable=False)
    result: Mapped[str] = mapped_column(Text, nullable=False)
    reflection: Mapped[str | None] = mapped_column(Text)
    tags: Mapped[list | None] = mapped_column(JSONB)
    source: Mapped[str] = mapped_column(
        String(50), nullable=False, default="user_created"
    )  # 'ai_generated' | 'user_created'

    user: Mapped["User"] = relationship("User", back_populates="star_stories")
```

- [ ] **Step 6: Create `backend/src/career_agent/models/__init__.py`**

```python
from career_agent.models.base import Base
from career_agent.models.profile import Profile
from career_agent.models.star_story import StarStory
from career_agent.models.subscription import Subscription
from career_agent.models.user import User

__all__ = ["Base", "Profile", "StarStory", "Subscription", "User"]
```

- [ ] **Step 7: Create `backend/src/career_agent/schemas/common.py`**

```python
from datetime import datetime
from typing import Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class TimestampedORM(ORMModel):
    id: UUID
    created_at: datetime
    updated_at: datetime


class MetaModel(BaseModel):
    cached: bool | None = None
    tokens_used: int | None = None
    cost_cents: int | None = None


class Envelope(BaseModel, Generic[T]):
    data: T
    meta: MetaModel | None = None
```

- [ ] **Step 8: Create `backend/src/career_agent/schemas/user.py`**

```python
from career_agent.schemas.common import TimestampedORM


class UserResponse(TimestampedORM):
    cognito_sub: str
    email: str
    name: str
```

- [ ] **Step 9: Create `backend/src/career_agent/schemas/profile.py`**

```python
from typing import Any

from pydantic import Field

from career_agent.schemas.common import ORMModel, TimestampedORM


class ProfileUpdate(ORMModel):
    target_roles: list[str] | None = None
    target_locations: list[str] | None = None
    min_salary: int | None = Field(default=None, ge=0)
    preferred_industries: list[str] | None = None
    linkedin_url: str | None = None
    github_url: str | None = None
    portfolio_url: str | None = None


class ProfileResponse(TimestampedORM):
    master_resume_md: str | None
    master_resume_s3: str | None
    parsed_resume_json: dict[str, Any] | None
    target_roles: list[str] | None
    target_locations: list[str] | None
    min_salary: int | None
    preferred_industries: list[str] | None
    linkedin_url: str | None
    github_url: str | None
    portfolio_url: str | None
    onboarding_state: str
```

- [ ] **Step 10: Create `backend/src/career_agent/schemas/__init__.py`**

```python
from career_agent.schemas.common import Envelope, MetaModel
from career_agent.schemas.profile import ProfileResponse, ProfileUpdate
from career_agent.schemas.user import UserResponse

__all__ = [
    "Envelope",
    "MetaModel",
    "ProfileResponse",
    "ProfileUpdate",
    "UserResponse",
]
```

- [ ] **Step 11: Run tests**

```bash
cd backend
uv run pytest -v
```
Expected: Existing tests still pass. No new tests yet — schemas/models tested via migration + integration tests in later tasks.

- [ ] **Step 12: Commit**

```bash
git add backend/src/career_agent/models/ backend/src/career_agent/schemas/
git commit -m "feat(backend): add Phase 1 models and schemas (users, profiles, star_stories)"
```

---

## Task 10: Initial Migration

**Files:**
- Create: `backend/migrations/versions/0001_phase1_schema.py`

- [ ] **Step 1: Autogenerate the migration**

```bash
cd backend
docker-compose -f ../docker-compose.yml up -d postgres
uv run alembic revision --autogenerate -m "phase1_schema"
```

- [ ] **Step 2: Review the autogenerated file**

The file will be at `backend/migrations/versions/<hash>_phase1_schema.py`. Rename to `0001_phase1_schema.py` and verify it creates: `users`, `subscriptions`, `profiles`, `star_stories` tables with all columns and indexes.

If autogenerate missed any index from Appendix H (Phase 1 subset), add them manually:

```python
# In the upgrade() function, after create_table calls:
op.create_index("idx_users_cognito_sub", "users", ["cognito_sub"])
op.create_index("idx_users_email", "users", ["email"])
op.create_index("idx_subscriptions_user_id", "subscriptions", ["user_id"])
op.create_index("idx_subscriptions_stripe_customer", "subscriptions", ["stripe_customer_id"])
op.create_index(
    "idx_subscriptions_trial_ends",
    "subscriptions",
    ["trial_ends_at"],
    postgresql_where=sa.text("status = 'active'"),
)
op.create_index("idx_profiles_user_id", "profiles", ["user_id"])
op.create_index("idx_star_stories_user_id", "star_stories", ["user_id"])
op.create_index(
    "idx_star_stories_tags_gin",
    "star_stories",
    ["tags"],
    postgresql_using="gin",
)
```

And in `downgrade()` drop them in reverse order before dropping tables.

- [ ] **Step 3: Run migration**

```bash
cd backend
uv run alembic upgrade head
```
Expected: No errors, creates tables.

- [ ] **Step 4: Verify schema**

```bash
docker exec -it $(docker-compose -f ../docker-compose.yml ps -q postgres) \
  psql -U postgres -d career_agent -c '\dt'
```
Expected: `users`, `subscriptions`, `profiles`, `star_stories`, `alembic_version` listed.

- [ ] **Step 5: Test downgrade then upgrade again**

```bash
uv run alembic downgrade base
uv run alembic upgrade head
```
Expected: Both succeed without errors.

- [ ] **Step 6: Commit**

```bash
git add backend/migrations/versions/0001_phase1_schema.py
git commit -m "feat(backend): add phase 1 schema migration"
```

---

## Task 11: Error Response Format + Middleware

**Files:**
- Create: `backend/src/career_agent/schemas/error.py`
- Create: `backend/src/career_agent/api/errors.py`
- Modify: `backend/src/career_agent/main.py`
- Create: `backend/tests/integration/test_error_format.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/integration/test_error_format.py`:

```python
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_404_returns_standard_error_envelope(client: AsyncClient) -> None:
    response = await client.get("/api/v1/nonexistent-endpoint")
    assert response.status_code == 404
    body = response.json()
    assert "error" in body
    assert body["error"]["code"] == "RESOURCE_NOT_FOUND"
    assert "message" in body["error"]
    assert "request_id" in body["error"]


@pytest.mark.asyncio
async def test_422_validation_error_returns_standard_envelope(client: AsyncClient) -> None:
    # We don't have a POST endpoint yet, so this test is added as a placeholder
    # and enabled once Profile PUT exists. For now, test unknown method.
    response = await client.request("PATCH", "/api/v1/health")
    assert response.status_code in (404, 405)
    body = response.json()
    assert "error" in body
    assert "request_id" in body["error"]
```

- [ ] **Step 2: Run to verify it fails**

```bash
uv run pytest tests/integration/test_error_format.py -v
```
Expected: FAIL — default FastAPI errors don't have our envelope.

- [ ] **Step 3: Create `backend/src/career_agent/schemas/error.py`**

```python
from typing import Any

from pydantic import BaseModel


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict[str, Any] | None = None
    request_id: str


class ErrorResponse(BaseModel):
    error: ErrorDetail
```

- [ ] **Step 4: Create `backend/src/career_agent/api/errors.py`**

```python
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from career_agent.logging import get_logger

log = get_logger("career_agent.errors")


HTTP_CODE_TO_ERROR_CODE: dict[int, str] = {
    400: "VALIDATION_ERROR",
    401: "UNAUTHENTICATED",
    403: "FORBIDDEN",
    404: "RESOURCE_NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    413: "PAYLOAD_TOO_LARGE",
    422: "UNPROCESSABLE_ENTITY",
    429: "RATE_LIMIT_EXCEEDED",
    500: "INTERNAL_ERROR",
    502: "UPSTREAM_ERROR",
    503: "SERVICE_UNAVAILABLE",
}


class AppError(HTTPException):
    """Application-specific error with a machine-readable code."""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: dict | None = None,
    ) -> None:
        super().__init__(status_code=status_code, detail=message)
        self.code = code
        self.message = message
        self.details = details


def _build_response(
    *,
    status_code: int,
    code: str,
    message: str,
    request_id: str,
    details: dict | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "details": details,
                "request_id": request_id,
            }
        },
    )


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    request_id = getattr(request.state, "request_id", str(uuid4()))
    log.warning(
        "app_error",
        request_id=request_id,
        code=exc.code,
        status_code=exc.status_code,
    )
    return _build_response(
        status_code=exc.status_code,
        code=exc.code,
        message=exc.message,
        request_id=request_id,
        details=exc.details,
    )


async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", str(uuid4()))
    code = HTTP_CODE_TO_ERROR_CODE.get(exc.status_code, "INTERNAL_ERROR")
    return _build_response(
        status_code=exc.status_code,
        code=code,
        message=str(exc.detail) if exc.detail else "",
        request_id=request_id,
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", str(uuid4()))
    return _build_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        code="VALIDATION_ERROR",
        message="Request validation failed",
        request_id=request_id,
        details={"errors": exc.errors()},
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", str(uuid4()))
    log.exception("unhandled_error", request_id=request_id)
    return _build_response(
        status_code=500,
        code="INTERNAL_ERROR",
        message="An unexpected error occurred",
        request_id=request_id,
    )


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, app_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, unhandled_exception_handler)
```

- [ ] **Step 5: Add request ID middleware and register handlers in `main.py`**

Update `backend/src/career_agent/main.py`:

```python
from contextlib import asynccontextmanager
from typing import AsyncIterator
from uuid import uuid4

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from career_agent.api import health
from career_agent.api.errors import register_error_handlers
from career_agent.config import get_settings
from career_agent.logging import configure_logging, get_logger


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):  # type: ignore[override]
        request_id = request.headers.get("X-Request-Id") or str(uuid4())
        request.state.request_id = request_id
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)
        response = await call_next(request)
        response.headers["X-Request-Id"] = request_id
        return response


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    log = get_logger("career_agent.main")
    settings = get_settings()
    log.info("startup", environment=settings.environment)
    yield
    log.info("shutdown")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="CareerAgent API",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-Id"],
    )

    register_error_handlers(app)

    app.include_router(health.router, prefix="/api/v1")

    return app


app = create_app()
```

- [ ] **Step 6: Run tests**

```bash
uv run pytest tests/integration/test_error_format.py -v
```
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/src/career_agent/schemas/error.py backend/src/career_agent/api/errors.py backend/src/career_agent/main.py backend/tests/integration/test_error_format.py
git commit -m "feat(backend): add standard error envelope and request ID middleware"
```

---

## Task 12: Cognito JWT Auth Dependency

**JWKS in tests:** `COGNITO_JWKS_URL` in CI points at `http://localhost/jwks`, which is not a real server. Integration tests that call `verify()` must **mock** `httpx.AsyncClient.get` (e.g. `respx`) to return a synthetic JWKS + sign test tokens, or point `COGNITO_JWKS_URL` at a fixture HTTP server. Do not rely on network access to Cognito in unit/integration tests.

**Files:**
- Create: `backend/src/career_agent/integrations/__init__.py`
- Create: `backend/src/career_agent/integrations/cognito.py`
- Create: `backend/src/career_agent/services/__init__.py`
- Create: `backend/src/career_agent/services/auth.py`
- Create: `backend/src/career_agent/api/deps.py`

- [ ] **Step 1: Create `backend/src/career_agent/integrations/__init__.py`** (empty)

```python
```

- [ ] **Step 2: Create `backend/src/career_agent/integrations/cognito.py`**

```python
from functools import lru_cache
from typing import Any

import httpx
from jose import jwk, jwt
from jose.exceptions import JWTError

from career_agent.api.errors import AppError
from career_agent.config import get_settings


class CognitoJwtVerifier:
    """Verifies Cognito-issued JWTs using the pool's JWKS."""

    def __init__(self, jwks_url: str, client_id: str, region: str, user_pool_id: str) -> None:
        self.jwks_url = jwks_url
        self.client_id = client_id
        self.issuer = f"https://cognito-idp.{region}.amazonaws.com/{user_pool_id}"
        self._jwks: dict[str, Any] | None = None

    async def _load_jwks(self) -> dict[str, Any]:
        if self._jwks is None:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(self.jwks_url)
                response.raise_for_status()
                self._jwks = response.json()
        return self._jwks

    async def verify(self, token: str) -> dict[str, Any]:
        try:
            header = jwt.get_unverified_header(token)
        except JWTError as e:
            raise AppError(401, "UNAUTHENTICATED", "Invalid token header") from e

        kid = header.get("kid")
        if not kid:
            raise AppError(401, "UNAUTHENTICATED", "Token missing kid")

        jwks = await self._load_jwks()
        key_data = next((k for k in jwks["keys"] if k["kid"] == kid), None)
        if key_data is None:
            raise AppError(401, "UNAUTHENTICATED", "Unknown signing key")

        public_key = jwk.construct(key_data)

        try:
            claims = jwt.decode(
                token,
                public_key.to_pem().decode(),
                algorithms=[key_data["alg"]],
                audience=self.client_id,
                issuer=self.issuer,
            )
        except JWTError as e:
            raise AppError(401, "UNAUTHENTICATED", f"Invalid token: {e}") from e

        return claims


@lru_cache(maxsize=1)
def get_verifier() -> CognitoJwtVerifier:
    settings = get_settings()
    return CognitoJwtVerifier(
        jwks_url=settings.cognito_jwks_url,
        client_id=settings.cognito_client_id,
        region=settings.cognito_region,
        user_pool_id=settings.cognito_user_pool_id,
    )
```

- [ ] **Step 3: Create `backend/src/career_agent/services/__init__.py`** (empty)

```python
```

- [ ] **Step 4: Create `backend/src/career_agent/services/auth.py`**

```python
from dataclasses import dataclass
from typing import Any


@dataclass
class AuthUser:
    user_id: str  # DB user UUID from custom:user_id claim
    cognito_sub: str
    email: str
    role: str  # 'user' | 'admin'
    subscription_tier: str  # 'trial' | 'pro' | 'cancelled'


def extract_auth_user(claims: dict[str, Any]) -> AuthUser:
    return AuthUser(
        user_id=claims.get("custom:user_id") or claims["sub"],
        cognito_sub=claims["sub"],
        email=claims.get("email", ""),
        role=claims.get("custom:role", "user"),
        subscription_tier=claims.get("custom:subscription_tier", "trial"),
    )
```

- [ ] **Step 5: Create `backend/src/career_agent/api/deps.py`**

```python
from typing import Annotated, AsyncIterator
from uuid import UUID

from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from career_agent.api.errors import AppError
from career_agent.db import get_db
from career_agent.integrations.cognito import CognitoJwtVerifier, get_verifier
from career_agent.models.user import User
from career_agent.services.auth import AuthUser, extract_auth_user


DbSession = Annotated[AsyncSession, Depends(get_db)]


async def get_auth_user(
    authorization: Annotated[str | None, Header()] = None,
    verifier: CognitoJwtVerifier = Depends(get_verifier),
) -> AuthUser:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AppError(401, "UNAUTHENTICATED", "Missing or invalid Authorization header")

    token = authorization.split(" ", 1)[1]
    claims = await verifier.verify(token)
    return extract_auth_user(claims)


CurrentUser = Annotated[AuthUser, Depends(get_auth_user)]


async def get_current_db_user(
    auth: CurrentUser,
    db: DbSession,
) -> User:
    """Resolve AuthUser → DB User. Auto-provisions on first authenticated request."""
    try:
        user_uuid = UUID(auth.user_id)
    except ValueError:
        # First-time login: user_id claim may not be set. Look up by cognito_sub.
        user_uuid = None  # type: ignore[assignment]

    user: User | None = None
    if user_uuid is not None:
        user = await db.get(User, user_uuid)

    if user is None:
        result = await db.execute(select(User).where(User.cognito_sub == auth.cognito_sub))
        user = result.scalar_one_or_none()

    if user is None:
        user = User(
            cognito_sub=auth.cognito_sub,
            email=auth.email,
            name=auth.email.split("@")[0] or "User",
        )
        db.add(user)
        await db.flush()

    return user


CurrentDbUser = Annotated[User, Depends(get_current_db_user)]
```

- [ ] **Step 6: Commit**

```bash
git add backend/src/career_agent/integrations/ backend/src/career_agent/services/__init__.py backend/src/career_agent/services/auth.py backend/src/career_agent/api/deps.py
git commit -m "feat(backend): add Cognito JWT verifier and auth dependency"
```

---

## Task 13: Auth Endpoint + Middleware Test

**Files:**
- Create: `backend/src/career_agent/api/auth.py`
- Create: `backend/tests/integration/test_auth_middleware.py`
- Modify: `backend/src/career_agent/main.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/integration/test_auth_middleware.py`:

```python
import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_auth_me_requires_token(client: AsyncClient) -> None:
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "UNAUTHENTICATED"


@pytest.mark.asyncio
async def test_auth_me_returns_user_when_token_valid(client: AsyncClient) -> None:
    fake_claims = {
        "sub": "cognito-sub-abc",
        "email": "test@example.com",
        "custom:user_id": "",
        "custom:role": "user",
        "custom:subscription_tier": "trial",
    }

    with patch(
        "career_agent.integrations.cognito.CognitoJwtVerifier.verify",
        new=AsyncMock(return_value=fake_claims),
    ):
        response = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer fake-token"},
        )

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["email"] == "test@example.com"
    assert body["cognito_sub"] == "cognito-sub-abc"
```

- [ ] **Step 2: Create `backend/src/career_agent/api/auth.py`**

```python
from fastapi import APIRouter

from career_agent.api.deps import CurrentDbUser, DbSession
from career_agent.schemas.common import Envelope
from career_agent.schemas.user import UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me", response_model=Envelope[UserResponse])
async def me(user: CurrentDbUser, db: DbSession) -> Envelope[UserResponse]:
    return Envelope(data=UserResponse.model_validate(user))
```

- [ ] **Step 3: Register auth router in `main.py`**

Add to imports and `create_app`:

```python
from career_agent.api import auth, health
# ...
    app.include_router(health.router, prefix="/api/v1")
    app.include_router(auth.router, prefix="/api/v1")
```

- [ ] **Step 4: Run the test**

```bash
uv run alembic upgrade head
uv run pytest tests/integration/test_auth_middleware.py -v
```
Expected: Both tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/src/career_agent/api/auth.py backend/src/career_agent/main.py backend/tests/integration/test_auth_middleware.py
git commit -m "feat(backend): add /auth/me endpoint with JWT middleware"
```

---

## Task 14: S3 Storage Abstraction

**Files:**
- Create: `backend/src/career_agent/integrations/s3.py`
- Create: `backend/src/career_agent/services/storage.py`
- Create: `backend/tests/unit/test_storage.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/unit/test_storage.py`:

```python
import io

import pytest
from moto import mock_aws

from career_agent.services.storage import StorageService


@pytest.mark.asyncio
async def test_upload_and_download_bytes() -> None:
    with mock_aws():
        import boto3
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket="test-bucket")

        storage = StorageService(bucket="test-bucket", region="us-east-1")

        key = "resumes/user-1/file.pdf"
        content = b"fake pdf bytes"

        await storage.upload_bytes(key, content, content_type="application/pdf")
        downloaded = await storage.download_bytes(key)

        assert downloaded == content


@pytest.mark.asyncio
async def test_generate_presigned_url_for_download() -> None:
    with mock_aws():
        import boto3
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket="test-bucket")
        client.put_object(Bucket="test-bucket", Key="foo.pdf", Body=b"x")

        storage = StorageService(bucket="test-bucket", region="us-east-1")
        url = await storage.presigned_download_url("foo.pdf", expires_in=900)

        assert url.startswith("https://")
        assert "test-bucket" in url
        assert "foo.pdf" in url
```

- [ ] **Step 2: Run to verify it fails**

```bash
uv run pytest tests/unit/test_storage.py -v
```
Expected: FAIL — `StorageService` not defined.

- [ ] **Step 3: Create `backend/src/career_agent/integrations/s3.py`**

```python
from functools import lru_cache

import boto3
from botocore.config import Config
from mypy_boto3_s3 import S3Client  # type: ignore[import-untyped]


@lru_cache(maxsize=1)
def get_s3_client(region: str) -> S3Client:
    return boto3.client(
        "s3",
        region_name=region,
        config=Config(signature_version="s3v4", retries={"max_attempts": 3}),
    )
```

If `mypy_boto3_s3` is not installed, use plain typing:

```python
from typing import Any
from functools import lru_cache

import boto3
from botocore.config import Config


@lru_cache(maxsize=1)
def get_s3_client(region: str) -> Any:
    return boto3.client(
        "s3",
        region_name=region,
        config=Config(signature_version="s3v4", retries={"max_attempts": 3}),
    )
```

- [ ] **Step 4: Create `backend/src/career_agent/services/storage.py`**

```python
import asyncio
from typing import Any

from career_agent.config import get_settings
from career_agent.integrations.s3 import get_s3_client


class StorageService:
    def __init__(self, bucket: str, region: str) -> None:
        self.bucket = bucket
        self.region = region
        self._client: Any = get_s3_client(region)

    async def upload_bytes(
        self,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> str:
        await asyncio.to_thread(
            self._client.put_object,
            Bucket=self.bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
            ServerSideEncryption="AES256",
        )
        return key

    async def download_bytes(self, key: str) -> bytes:
        response = await asyncio.to_thread(
            self._client.get_object,
            Bucket=self.bucket,
            Key=key,
        )
        return response["Body"].read()  # type: ignore[no-any-return]

    async def delete(self, key: str) -> None:
        await asyncio.to_thread(
            self._client.delete_object,
            Bucket=self.bucket,
            Key=key,
        )

    async def presigned_download_url(self, key: str, expires_in: int = 900) -> str:
        return await asyncio.to_thread(
            self._client.generate_presigned_url,
            ClientMethod="get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=expires_in,
        )


def get_storage_service() -> StorageService:
    settings = get_settings()
    return StorageService(bucket=settings.aws_s3_bucket, region=settings.aws_region)
```

- [ ] **Step 5: Run test**

```bash
uv run pytest tests/unit/test_storage.py -v
```
Expected: Both tests PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/src/career_agent/integrations/s3.py backend/src/career_agent/services/storage.py backend/tests/unit/test_storage.py
git commit -m "feat(backend): add S3 storage service"
```

---

## Task 15: Profile Service + GET/PUT Endpoints

**Files:**
- Create: `backend/src/career_agent/services/profile.py`
- Create: `backend/src/career_agent/api/profile.py`
- Create: `backend/tests/integration/test_profile_crud.py`
- Modify: `backend/src/career_agent/main.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/integration/test_profile_crud.py`:

```python
import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch


FAKE_CLAIMS = {
    "sub": "cognito-sub-xyz",
    "email": "crud@example.com",
    "custom:role": "user",
    "custom:subscription_tier": "trial",
}


@pytest.mark.asyncio
async def test_get_profile_creates_empty_profile_on_first_access(client: AsyncClient) -> None:
    with patch(
        "career_agent.integrations.cognito.CognitoJwtVerifier.verify",
        new=AsyncMock(return_value=FAKE_CLAIMS),
    ):
        response = await client.get(
            "/api/v1/profile",
            headers={"Authorization": "Bearer fake"},
        )
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["onboarding_state"] == "resume_upload"
    assert body["target_roles"] is None


@pytest.mark.asyncio
async def test_put_profile_updates_preferences(client: AsyncClient) -> None:
    with patch(
        "career_agent.integrations.cognito.CognitoJwtVerifier.verify",
        new=AsyncMock(return_value=FAKE_CLAIMS),
    ):
        # Create via GET
        await client.get("/api/v1/profile", headers={"Authorization": "Bearer fake"})

        # Update
        response = await client.put(
            "/api/v1/profile",
            headers={"Authorization": "Bearer fake"},
            json={
                "target_roles": ["Senior Backend Engineer"],
                "target_locations": ["Remote", "Dubai"],
                "min_salary": 120000,
                "linkedin_url": "https://linkedin.com/in/test",
            },
        )

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["target_roles"] == ["Senior Backend Engineer"]
    assert body["target_locations"] == ["Remote", "Dubai"]
    assert body["min_salary"] == 120000
    assert body["onboarding_state"] in ("preferences", "done")


@pytest.mark.asyncio
async def test_put_profile_rejects_negative_salary(client: AsyncClient) -> None:
    with patch(
        "career_agent.integrations.cognito.CognitoJwtVerifier.verify",
        new=AsyncMock(return_value=FAKE_CLAIMS),
    ):
        response = await client.put(
            "/api/v1/profile",
            headers={"Authorization": "Bearer fake"},
            json={"min_salary": -1},
        )
    assert response.status_code == 422
```

- [ ] **Step 2: Create `backend/src/career_agent/services/profile.py`**

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from career_agent.models.profile import Profile
from career_agent.models.user import User
from career_agent.schemas.profile import ProfileUpdate


async def get_or_create_profile(db: AsyncSession, user: User) -> Profile:
    result = await db.execute(select(Profile).where(Profile.user_id == user.id))
    profile = result.scalar_one_or_none()
    if profile is None:
        profile = Profile(user_id=user.id, onboarding_state="resume_upload")
        db.add(profile)
        await db.flush()
    return profile


async def update_profile(
    db: AsyncSession,
    profile: Profile,
    data: ProfileUpdate,
) -> Profile:
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(profile, field, value)

    # Advance onboarding state if user set key preferences
    if profile.onboarding_state == "resume_upload" and profile.master_resume_md:
        profile.onboarding_state = "preferences"
    if (
        profile.onboarding_state == "preferences"
        and profile.target_roles
        and profile.target_locations
    ):
        profile.onboarding_state = "done"

    await db.flush()
    return profile


async def delete_profile_cascade(db: AsyncSession, user: User) -> None:
    """Delete a user and all their associated data (GDPR)."""
    await db.delete(user)
    await db.flush()
```

- [ ] **Step 3: Create `backend/src/career_agent/api/profile.py`**

```python
from fastapi import APIRouter

from career_agent.api.deps import CurrentDbUser, DbSession
from career_agent.schemas.common import Envelope
from career_agent.schemas.profile import ProfileResponse, ProfileUpdate
from career_agent.services.profile import (
    delete_profile_cascade,
    get_or_create_profile,
    update_profile,
)

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("", response_model=Envelope[ProfileResponse])
async def get_profile(user: CurrentDbUser, db: DbSession) -> Envelope[ProfileResponse]:
    profile = await get_or_create_profile(db, user)
    return Envelope(data=ProfileResponse.model_validate(profile))


@router.put("", response_model=Envelope[ProfileResponse])
async def put_profile(
    data: ProfileUpdate,
    user: CurrentDbUser,
    db: DbSession,
) -> Envelope[ProfileResponse]:
    profile = await get_or_create_profile(db, user)
    profile = await update_profile(db, profile, data)
    return Envelope(data=ProfileResponse.model_validate(profile))


@router.delete("", status_code=204)
async def delete_profile(user: CurrentDbUser, db: DbSession) -> None:
    await delete_profile_cascade(db, user)
```

- [ ] **Step 4: Register router in `main.py`**

```python
from career_agent.api import auth, health, profile
# ...
    app.include_router(profile.router, prefix="/api/v1")
```

- [ ] **Step 5: Run the tests**

```bash
uv run alembic upgrade head
uv run pytest tests/integration/test_profile_crud.py -v
```
Expected: All three tests PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/src/career_agent/services/profile.py backend/src/career_agent/api/profile.py backend/src/career_agent/main.py backend/tests/integration/test_profile_crud.py
git commit -m "feat(backend): add profile CRUD endpoints with onboarding state"
```

---

## Task 16: Resume Parser

Implement **`parse_resume_bytes`** as deterministic text extraction first (see **Resume parsing strategy** at top of this plan). Optional LLM structuring can be a follow-up commit if you add `parsed_resume_json` enrichment — keep tests hermetic without `ANTHROPIC_API_KEY`.

**Files:**
- Create: `backend/src/career_agent/services/resume_parser.py`
- Create: `backend/tests/fixtures/resumes/sample.pdf`
- Create: `backend/tests/fixtures/resumes/sample.docx`
- Create: `backend/tests/unit/test_resume_parser.py`

- [ ] **Step 1: Create test fixtures**

Generate minimal test fixtures:

```bash
cd backend
mkdir -p tests/fixtures/resumes
uv run python -c "
from pypdf import PdfWriter
from io import BytesIO
writer = PdfWriter()
writer.add_blank_page(width=612, height=792)
with open('tests/fixtures/resumes/sample.pdf', 'wb') as f:
    writer.write(f)
"
uv run python -c "
from docx import Document
doc = Document()
doc.add_heading('Jane Doe', 0)
doc.add_paragraph('Senior Backend Engineer')
doc.add_heading('Experience', 1)
doc.add_paragraph('Acme Corp — Staff Engineer, 2020-2024')
doc.add_paragraph('Built distributed systems serving 10M users')
doc.save('tests/fixtures/resumes/sample.docx')
"
```

For the PDF, also write a version with text to enable parsing tests. Use `reportlab` or similar — or just assert on empty PDF extraction:

- [ ] **Step 2: Write the failing test**

Create `backend/tests/unit/test_resume_parser.py`:

```python
from pathlib import Path

import pytest

from career_agent.services.resume_parser import (
    parse_resume_bytes,
    ResumeParseError,
)

FIXTURES = Path(__file__).parent.parent / "fixtures" / "resumes"


def test_parse_docx_extracts_text() -> None:
    data = (FIXTURES / "sample.docx").read_bytes()
    result = parse_resume_bytes(data, filename="sample.docx")
    assert "Jane Doe" in result["text"]
    assert "Senior Backend Engineer" in result["text"]
    assert result["content_type"] == "docx"


def test_parse_pdf_returns_result_even_if_empty() -> None:
    data = (FIXTURES / "sample.pdf").read_bytes()
    result = parse_resume_bytes(data, filename="sample.pdf")
    assert result["content_type"] == "pdf"
    # Blank PDF has no text but should not error
    assert "text" in result


def test_parse_unsupported_filetype_raises() -> None:
    with pytest.raises(ResumeParseError) as exc_info:
        parse_resume_bytes(b"some text", filename="resume.txt")
    assert "unsupported" in str(exc_info.value).lower()


def test_parse_corrupted_bytes_raises() -> None:
    with pytest.raises(ResumeParseError):
        parse_resume_bytes(b"not a real pdf", filename="resume.pdf")
```

- [ ] **Step 3: Run to verify it fails**

```bash
uv run pytest tests/unit/test_resume_parser.py -v
```
Expected: FAIL — module doesn't exist.

- [ ] **Step 4: Create `backend/src/career_agent/services/resume_parser.py`**

```python
import io
from typing import Any

import pypdf
from docx import Document


class ResumeParseError(Exception):
    pass


def parse_resume_bytes(data: bytes, filename: str) -> dict[str, Any]:
    """Parse a resume PDF or DOCX into structured data.

    Returns:
        {
            "text": str,           # Plain text extract
            "markdown": str,       # Markdown-ish representation (for DOCX)
            "content_type": str,   # 'pdf' | 'docx'
            "page_count": int | None,
        }
    """
    lower = filename.lower()
    if lower.endswith(".pdf"):
        return _parse_pdf(data)
    if lower.endswith(".docx"):
        return _parse_docx(data)
    raise ResumeParseError(f"Unsupported file type: {filename}")


def _parse_pdf(data: bytes) -> dict[str, Any]:
    try:
        reader = pypdf.PdfReader(io.BytesIO(data))
    except Exception as e:
        raise ResumeParseError(f"Failed to read PDF: {e}") from e

    text_parts: list[str] = []
    for page in reader.pages:
        try:
            text_parts.append(page.extract_text() or "")
        except Exception:
            continue

    text = "\n".join(text_parts).strip()
    return {
        "text": text,
        "markdown": text,
        "content_type": "pdf",
        "page_count": len(reader.pages),
    }


def _parse_docx(data: bytes) -> dict[str, Any]:
    try:
        doc = Document(io.BytesIO(data))
    except Exception as e:
        raise ResumeParseError(f"Failed to read DOCX: {e}") from e

    parts: list[str] = []
    md_parts: list[str] = []
    for paragraph in doc.paragraphs:
        text = paragraph.text.strip()
        if not text:
            continue
        parts.append(text)
        style = (paragraph.style.name or "").lower()
        if "heading 1" in style or style == "title":
            md_parts.append(f"# {text}")
        elif "heading 2" in style:
            md_parts.append(f"## {text}")
        elif "heading 3" in style:
            md_parts.append(f"### {text}")
        else:
            md_parts.append(text)

    return {
        "text": "\n".join(parts),
        "markdown": "\n\n".join(md_parts),
        "content_type": "docx",
        "page_count": None,
    }
```

- [ ] **Step 5: Run tests**

```bash
uv run pytest tests/unit/test_resume_parser.py -v
```
Expected: All four tests PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/tests/fixtures/resumes/sample.pdf backend/tests/fixtures/resumes/sample.docx backend/src/career_agent/services/resume_parser.py backend/tests/unit/test_resume_parser.py
git commit -m "feat(backend): add resume parser (PDF + DOCX)"
```

---

## Task 17: Resume Upload Endpoint

**Files:**
- Modify: `backend/src/career_agent/api/profile.py`
- Modify: `backend/src/career_agent/services/profile.py`
- Create: `backend/tests/integration/test_resume_upload.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/integration/test_resume_upload.py`:

```python
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from moto import mock_aws

FIXTURES = Path(__file__).parent.parent / "fixtures" / "resumes"

FAKE_CLAIMS = {
    "sub": "cognito-sub-upload",
    "email": "upload@example.com",
    "custom:role": "user",
    "custom:subscription_tier": "trial",
}


@pytest.mark.asyncio
async def test_upload_docx_resume_stores_and_parses(client: AsyncClient) -> None:
    with mock_aws():
        import boto3
        boto3.client("s3", region_name="us-east-1").create_bucket(Bucket="career-agent-dev-assets")

        with patch(
            "career_agent.integrations.cognito.CognitoJwtVerifier.verify",
            new=AsyncMock(return_value=FAKE_CLAIMS),
        ):
            with (FIXTURES / "sample.docx").open("rb") as f:
                response = await client.post(
                    "/api/v1/profile/resume",
                    headers={"Authorization": "Bearer fake"},
                    files={"file": ("sample.docx", f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
                )

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["master_resume_s3"] is not None
    assert body["master_resume_md"] is not None
    assert "Jane Doe" in body["master_resume_md"]


@pytest.mark.asyncio
async def test_upload_rejects_unsupported_filetype(client: AsyncClient) -> None:
    with patch(
        "career_agent.integrations.cognito.CognitoJwtVerifier.verify",
        new=AsyncMock(return_value=FAKE_CLAIMS),
    ):
        response = await client.post(
            "/api/v1/profile/resume",
            headers={"Authorization": "Bearer fake"},
            files={"file": ("resume.txt", b"hello", "text/plain")},
        )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "UNPROCESSABLE_ENTITY"


@pytest.mark.asyncio
async def test_upload_rejects_file_too_large(client: AsyncClient) -> None:
    big_bytes = b"x" * (11 * 1024 * 1024)  # 11MB, over 10MB limit
    with patch(
        "career_agent.integrations.cognito.CognitoJwtVerifier.verify",
        new=AsyncMock(return_value=FAKE_CLAIMS),
    ):
        response = await client.post(
            "/api/v1/profile/resume",
            headers={"Authorization": "Bearer fake"},
            files={"file": ("big.pdf", big_bytes, "application/pdf")},
        )
    assert response.status_code == 413
```

- [ ] **Step 2: Add service function to `services/profile.py`**

Append to `backend/src/career_agent/services/profile.py`:

```python
from uuid import uuid4

from career_agent.services.resume_parser import ResumeParseError, parse_resume_bytes
from career_agent.services.storage import StorageService
from career_agent.api.errors import AppError

MAX_RESUME_BYTES = 10 * 1024 * 1024  # 10 MB
ALLOWED_RESUME_EXTENSIONS = {".pdf", ".docx"}


async def upload_resume(
    db,  # type: ignore[no-untyped-def]
    storage: StorageService,
    profile: Profile,
    filename: str,
    data: bytes,
) -> Profile:
    if len(data) > MAX_RESUME_BYTES:
        raise AppError(413, "PAYLOAD_TOO_LARGE", "Resume exceeds 10MB limit")

    lower = filename.lower()
    if not any(lower.endswith(ext) for ext in ALLOWED_RESUME_EXTENSIONS):
        raise AppError(
            422, "UNPROCESSABLE_ENTITY", "Only PDF and DOCX files are supported"
        )

    try:
        parsed = parse_resume_bytes(data, filename)
    except ResumeParseError as e:
        raise AppError(422, "UNPROCESSABLE_ENTITY", str(e)) from e

    s3_key = f"resumes/{profile.user_id}/{uuid4()}{lower[lower.rfind('.'):]}"
    content_type = (
        "application/pdf"
        if lower.endswith(".pdf")
        else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    await storage.upload_bytes(s3_key, data, content_type=content_type)

    profile.master_resume_s3 = s3_key
    profile.master_resume_md = parsed["markdown"]
    profile.parsed_resume_json = {"text": parsed["text"], "content_type": parsed["content_type"]}
    if profile.onboarding_state == "resume_upload":
        profile.onboarding_state = "preferences"

    await db.flush()
    return profile
```

- [ ] **Step 3: Add endpoint to `api/profile.py`**

Append to `backend/src/career_agent/api/profile.py`:

```python
from fastapi import Depends, File, UploadFile

from career_agent.services.storage import StorageService, get_storage_service
from career_agent.services.profile import upload_resume


@router.post("/resume", response_model=Envelope[ProfileResponse])
async def upload_resume_endpoint(
    file: UploadFile,
    user: CurrentDbUser,
    db: DbSession,
    storage: StorageService = Depends(get_storage_service),
) -> Envelope[ProfileResponse]:
    contents = await file.read()
    profile = await get_or_create_profile(db, user)
    profile = await upload_resume(
        db, storage, profile, file.filename or "resume.pdf", contents
    )
    return Envelope(data=ProfileResponse.model_validate(profile))
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/integration/test_resume_upload.py -v
```
Expected: All three tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/src/career_agent/services/profile.py backend/src/career_agent/api/profile.py backend/tests/integration/test_resume_upload.py
git commit -m "feat(backend): add resume upload with S3 storage and parsing"
```

---

## Task 18: GDPR Export + Delete Account

**Files:**
- Modify: `backend/src/career_agent/api/profile.py`
- Modify: `backend/src/career_agent/services/profile.py`
- Create: `backend/tests/integration/test_gdpr_export.py`

- [ ] **Step 1: Write the failing test**

Create `backend/tests/integration/test_gdpr_export.py`:

```python
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


FAKE_CLAIMS = {
    "sub": "cognito-sub-gdpr",
    "email": "gdpr@example.com",
    "custom:role": "user",
    "custom:subscription_tier": "trial",
}


@pytest.mark.asyncio
async def test_export_returns_user_data_as_json(client: AsyncClient) -> None:
    with patch(
        "career_agent.integrations.cognito.CognitoJwtVerifier.verify",
        new=AsyncMock(return_value=FAKE_CLAIMS),
    ):
        # Ensure profile exists
        await client.get("/api/v1/profile", headers={"Authorization": "Bearer fake"})

        response = await client.post(
            "/api/v1/profile/export",
            headers={"Authorization": "Bearer fake"},
        )

    assert response.status_code == 200
    body = response.json()["data"]
    assert "user" in body
    assert "profile" in body
    assert body["user"]["email"] == "gdpr@example.com"


@pytest.mark.asyncio
async def test_delete_account_removes_user(client: AsyncClient) -> None:
    with patch(
        "career_agent.integrations.cognito.CognitoJwtVerifier.verify",
        new=AsyncMock(return_value=FAKE_CLAIMS),
    ):
        await client.get("/api/v1/profile", headers={"Authorization": "Bearer fake"})
        response = await client.delete(
            "/api/v1/profile",
            headers={"Authorization": "Bearer fake"},
        )

    assert response.status_code == 204
```

- [ ] **Step 2: Add export service**

Append to `backend/src/career_agent/services/profile.py`:

```python
from typing import Any


async def export_user_data(db, user: User) -> dict[str, Any]:  # type: ignore[no-untyped-def]
    profile = await get_or_create_profile(db, user)
    return {
        "user": {
            "id": str(user.id),
            "email": user.email,
            "name": user.name,
            "cognito_sub": user.cognito_sub,
            "created_at": user.created_at.isoformat(),
        },
        "profile": {
            "target_roles": profile.target_roles,
            "target_locations": profile.target_locations,
            "min_salary": profile.min_salary,
            "preferred_industries": profile.preferred_industries,
            "linkedin_url": profile.linkedin_url,
            "github_url": profile.github_url,
            "portfolio_url": profile.portfolio_url,
            "master_resume_md": profile.master_resume_md,
            "onboarding_state": profile.onboarding_state,
        },
        "star_stories": [],
    }
```

- [ ] **Step 3: Add export endpoint to `api/profile.py`**

```python
from career_agent.services.profile import export_user_data


@router.post("/export", response_model=Envelope[dict])
async def export_profile(user: CurrentDbUser, db: DbSession) -> Envelope[dict]:
    data = await export_user_data(db, user)
    return Envelope(data=data)
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/integration/test_gdpr_export.py -v
```
Expected: Both tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/src/career_agent/services/profile.py backend/src/career_agent/api/profile.py backend/tests/integration/test_gdpr_export.py
git commit -m "feat(backend): add GDPR export and account delete endpoints"
```

---

## Task 19: User Portal Skeleton

**Files:**
- Create: `user-portal/package.json`
- Create: `user-portal/tsconfig.json`
- Create: `user-portal/tsconfig.node.json`
- Create: `user-portal/vite.config.ts`
- Create: `user-portal/tailwind.config.ts`
- Create: `user-portal/postcss.config.js`
- Create: `user-portal/index.html`
- Create: `user-portal/.env.example`
- Create: `user-portal/src/main.tsx`
- Create: `user-portal/src/App.tsx`
- Create: `user-portal/src/index.css`

- [ ] **Step 1: Create `user-portal/package.json`**

```json
{
  "name": "@career-agent/user-portal",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview",
    "lint": "tsc --noEmit"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^6.28.0"
  },
  "devDependencies": {
    "@types/react": "^18.3.12",
    "@types/react-dom": "^18.3.1",
    "@vitejs/plugin-react": "^4.3.3",
    "autoprefixer": "^10.4.20",
    "postcss": "^8.4.49",
    "tailwindcss": "^3.4.14",
    "typescript": "^5.6.3",
    "vite": "^5.4.11"
  }
}
```

- [ ] **Step 2: Create `user-portal/tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "useDefineForClassFields": true,
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

- [ ] **Step 3: Create `user-portal/tsconfig.node.json`**

```json
{
  "compilerOptions": {
    "composite": true,
    "skipLibCheck": true,
    "module": "ESNext",
    "moduleResolution": "bundler",
    "allowSyntheticDefaultImports": true,
    "strict": true
  },
  "include": ["vite.config.ts"]
}
```

- [ ] **Step 4: Create `user-portal/vite.config.ts`**

```typescript
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true,
  },
});
```

- [ ] **Step 5: Create `user-portal/tailwind.config.ts`**

```typescript
import type { Config } from 'tailwindcss';

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // Notion palette
        bg: '#ffffff',
        sidebar: '#fbfbfa',
        card: '#f7f6f3',
        'text-primary': '#37352f',
        'text-secondary': '#787774',
        accent: '#2383e2',
        border: '#e3e2e0',
        hover: '#efefef',
      },
    },
  },
  plugins: [],
} satisfies Config;
```

- [ ] **Step 6: Create `user-portal/postcss.config.js`**

```javascript
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};
```

- [ ] **Step 7: Create `user-portal/index.html`**

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/vite.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>CareerAgent</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 8: Create `user-portal/.env.example`** (matches Appendix B)

```
VITE_API_URL=http://localhost:8000
VITE_COGNITO_USER_POOL_ID=us-east-1_xxxxxxxxx
VITE_COGNITO_CLIENT_ID=xxxxxxxxxxxxxxxxxxxxxxxxxx
VITE_COGNITO_REGION=us-east-1
VITE_ENVIRONMENT=dev
```

- [ ] **Step 9: Create `user-portal/src/index.css`**

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

html, body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
  @apply text-text-primary bg-bg;
}
```

- [ ] **Step 10: Create `user-portal/src/main.tsx`**

```typescript
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './index.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
```

- [ ] **Step 11: Create `user-portal/src/App.tsx`**

```typescript
export default function App() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-sidebar">
      <div className="text-center">
        <h1 className="text-3xl font-semibold text-text-primary">CareerAgent</h1>
        <p className="mt-2 text-text-secondary">User portal — Phase 1 scaffold</p>
      </div>
    </div>
  );
}
```

- [ ] **Step 12: Install and build**

```bash
cd user-portal
pnpm install
pnpm build
```
Expected: `dist/` created, no errors.

- [ ] **Step 13: Commit**

```bash
git add user-portal/
git commit -m "feat(user-portal): scaffold React+Vite+Tailwind skeleton"
```

---

## Task 20: Admin UI Skeleton

**Files:**
- Create: `admin-ui/package.json`
- Create: `admin-ui/tsconfig.json`
- Create: `admin-ui/tsconfig.node.json`
- Create: `admin-ui/vite.config.ts`
- Create: `admin-ui/tailwind.config.ts`
- Create: `admin-ui/postcss.config.js`
- Create: `admin-ui/index.html`
- Create: `admin-ui/.env.example`
- Create: `admin-ui/src/main.tsx`
- Create: `admin-ui/src/App.tsx`
- Create: `admin-ui/src/index.css`

- [ ] **Step 1: Mirror the user-portal structure**

Copy all files from Task 19 with these changes:
- `package.json` name: `@career-agent/admin-ui`
- `vite.config.ts` port: `5174`
- `index.html` title: `CareerAgent Admin`
- `src/App.tsx` body text: `Admin UI — Phase 1 scaffold`

- [ ] **Step 2: Install and build**

```bash
cd admin-ui
pnpm install
pnpm build
```

- [ ] **Step 3: Commit**

```bash
git add admin-ui/
git commit -m "feat(admin-ui): scaffold React+Vite+Tailwind skeleton"
```

---

## Task 21: Marketing Site Skeleton

**Files:**
- Create: `marketing/package.json`
- Create: `marketing/tsconfig.json`
- Create: `marketing/tsconfig.node.json`
- Create: `marketing/vite.config.ts`
- Create: `marketing/tailwind.config.ts`
- Create: `marketing/postcss.config.js`
- Create: `marketing/index.html`
- Create: `marketing/.env.example`
- Create: `marketing/src/main.tsx`
- Create: `marketing/src/App.tsx`
- Create: `marketing/src/index.css`

- [ ] **Step 1: Mirror the user-portal structure**

Same pattern as admin-ui with changes:
- `package.json` name: `@career-agent/marketing`
- `vite.config.ts` port: `5175`
- `index.html` title: `CareerAgent — AI Career Assistant`
- `src/App.tsx`:
  ```typescript
  export default function App() {
    return (
      <div className="min-h-screen bg-bg text-text-primary">
        <header className="border-b border-border p-6">
          <h1 className="text-2xl font-semibold">CareerAgent</h1>
        </header>
        <main className="max-w-4xl mx-auto p-8">
          <h2 className="text-4xl font-bold">Your AI career assistant</h2>
          <p className="mt-4 text-text-secondary text-lg">
            Phase 1 marketing scaffold. Landing content TBD in Phase 5.
          </p>
        </main>
      </div>
    );
  }
  ```
- `marketing/.env.example`:
  ```
  VITE_APP_URL=http://localhost:5173
  VITE_ENVIRONMENT=dev
  ```

- [ ] **Step 2: Install and build**

```bash
cd marketing
pnpm install
pnpm build
```

- [ ] **Step 3: Commit**

```bash
git add marketing/
git commit -m "feat(marketing): scaffold marketing site skeleton"
```

---

## Task 22: PDF Render Service Stub

**Files:**
- Create: `pdf-render/package.json`
- Create: `pdf-render/tsconfig.json`
- Create: `pdf-render/Dockerfile`
- Create: `pdf-render/.env.example`
- Create: `pdf-render/src/server.ts`
- Create: `pdf-render/src/render.ts`

- [ ] **Step 1: Create `pdf-render/package.json`**

```json
{
  "name": "@career-agent/pdf-render",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "tsx watch src/server.ts",
    "build": "tsc",
    "start": "node dist/server.js",
    "lint": "tsc --noEmit"
  },
  "dependencies": {
    "fastify": "^5.1.0",
    "@fastify/helmet": "^12.0.1",
    "playwright": "^1.48.2",
    "zod": "^3.23.8"
  },
  "devDependencies": {
    "@types/node": "^22.9.0",
    "tsx": "^4.19.2",
    "typescript": "^5.6.3"
  }
}
```

- [ ] **Step 2: Create `pdf-render/tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ES2022",
    "moduleResolution": "bundler",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "outDir": "dist",
    "rootDir": "src",
    "resolveJsonModule": true
  },
  "include": ["src/**/*"]
}
```

- [ ] **Step 3: Create `pdf-render/.env.example`**

```
PORT=4000
PDF_RENDER_API_KEY=local-dev-key
LOG_LEVEL=info
```

- [ ] **Step 4: Create `pdf-render/src/render.ts`**

```typescript
// Phase 1 stub — real implementation in Phase 2 (CV Optimization module)
export async function renderMarkdownToPdf(markdown: string): Promise<Buffer> {
  // Placeholder - returns empty buffer. Implemented in Phase 2.
  return Buffer.from('');
}
```

- [ ] **Step 5: Create `pdf-render/src/server.ts`**

```typescript
import Fastify from 'fastify';

const PORT = Number(process.env.PORT ?? 4000);
const API_KEY = process.env.PDF_RENDER_API_KEY ?? 'local-dev-key';

const app = Fastify({ logger: true });

app.get('/health', async () => ({ status: 'ok', chromium_ready: false }));

app.post('/render', async (request, reply) => {
  const auth = request.headers.authorization;
  if (auth !== `Bearer ${API_KEY}`) {
    return reply.code(401).send({ error: 'Unauthorized' });
  }
  return reply.code(501).send({
    error: 'NOT_IMPLEMENTED',
    message: 'PDF render stub - implemented in Phase 2',
  });
});

app.listen({ port: PORT, host: '0.0.0.0' }, (err) => {
  if (err) {
    app.log.error(err);
    process.exit(1);
  }
});
```

- [ ] **Step 6: Create `pdf-render/Dockerfile`**

```dockerfile
FROM mcr.microsoft.com/playwright:v1.48.2-jammy

WORKDIR /app

COPY package.json pnpm-lock.yaml* ./
RUN corepack enable && pnpm install --frozen-lockfile

COPY tsconfig.json ./
COPY src/ ./src/

RUN pnpm build

EXPOSE 4000
CMD ["node", "dist/server.js"]
```

- [ ] **Step 7: Install and build**

```bash
cd pdf-render
pnpm install
pnpm build
```
Expected: `dist/server.js` created.

- [ ] **Step 8: Commit**

```bash
git add pdf-render/
git commit -m "feat(pdf-render): add Fastify stub service"
```

---

## Task 23: CDK Stack Skeletons

**Files:**
- Create: `infrastructure/cdk/package.json`
- Create: `infrastructure/cdk/tsconfig.json`
- Create: `infrastructure/cdk/cdk.json`
- Create: `infrastructure/cdk/bin/career-agent.ts`
- Create: `infrastructure/cdk/lib/network-stack.ts`
- Create: `infrastructure/cdk/lib/data-stack.ts`
- Create: `infrastructure/cdk/lib/auth-stack.ts`

- [ ] **Step 1: Create `infrastructure/cdk/package.json`**

```json
{
  "name": "@career-agent/cdk",
  "private": true,
  "version": "0.1.0",
  "scripts": {
    "build": "tsc",
    "watch": "tsc -w",
    "synth": "cdk synth",
    "diff": "cdk diff",
    "deploy": "cdk deploy",
    "lint": "tsc --noEmit"
  },
  "dependencies": {
    "aws-cdk-lib": "^2.160.0",
    "constructs": "^10.4.2"
  },
  "devDependencies": {
    "@types/node": "^22.9.0",
    "aws-cdk": "^2.160.0",
    "typescript": "^5.6.3",
    "ts-node": "^10.9.2"
  }
}
```

- [ ] **Step 2: Create `infrastructure/cdk/tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "NodeNext",
    "moduleResolution": "NodeNext",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "experimentalDecorators": true,
    "emitDecoratorMetadata": true,
    "outDir": "dist",
    "resolveJsonModule": true
  },
  "include": ["bin/**/*", "lib/**/*"]
}
```

- [ ] **Step 3: Create `infrastructure/cdk/cdk.json`**

```json
{
  "app": "npx ts-node --prefer-ts-exts bin/career-agent.ts",
  "watch": { "include": ["**"], "exclude": ["README.md", "cdk*.json", "**/*.d.ts", "**/*.js", "tsconfig.json", "package*.json", "yarn.lock", "node_modules", "dist"] },
  "context": {
    "@aws-cdk/aws-lambda:recognizeLayerVersion": true,
    "@aws-cdk/core:checkSecretUsage": true,
    "@aws-cdk/core:target-partitions": ["aws", "aws-cn"]
  }
}
```

- [ ] **Step 4: Create `infrastructure/cdk/lib/network-stack.ts`**

```typescript
import * as cdk from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import { Construct } from 'constructs';

export interface NetworkStackProps extends cdk.StackProps {
  environment: string;
}

export class NetworkStack extends cdk.Stack {
  public readonly vpc: ec2.Vpc;

  constructor(scope: Construct, id: string, props: NetworkStackProps) {
    super(scope, id, props);

    this.vpc = new ec2.Vpc(this, 'CareerAgentVpc', {
      vpcName: `career-agent-${props.environment}`,
      maxAzs: 3,
      natGateways: props.environment === 'prod' ? 1 : 0,
      subnetConfiguration: [
        { name: 'Public', subnetType: ec2.SubnetType.PUBLIC, cidrMask: 24 },
        { name: 'Private', subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS, cidrMask: 24 },
        { name: 'Isolated', subnetType: ec2.SubnetType.PRIVATE_ISOLATED, cidrMask: 24 },
      ],
    });
  }
}
```

- [ ] **Step 5: Create `infrastructure/cdk/lib/data-stack.ts`**

```typescript
import * as cdk from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as rds from 'aws-cdk-lib/aws-rds';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as elasticache from 'aws-cdk-lib/aws-elasticache';
import { Construct } from 'constructs';

export interface DataStackProps extends cdk.StackProps {
  environment: string;
  vpc: ec2.Vpc;
}

export class DataStack extends cdk.Stack {
  public readonly database: rds.DatabaseInstance;
  public readonly assetsBucket: s3.Bucket;
  public readonly redisEndpoint: string;

  constructor(scope: Construct, id: string, props: DataStackProps) {
    super(scope, id, props);

    const isProd = props.environment === 'prod';

    this.database = new rds.DatabaseInstance(this, 'CareerAgentDb', {
      engine: rds.DatabaseInstanceEngine.postgres({
        version: rds.PostgresEngineVersion.VER_16,
      }),
      instanceType: ec2.InstanceType.of(
        ec2.InstanceClass.BURSTABLE4_GRAVITON,
        isProd ? ec2.InstanceSize.LARGE : ec2.InstanceSize.SMALL,
      ),
      vpc: props.vpc,
      vpcSubnets: { subnetType: ec2.SubnetType.PRIVATE_ISOLATED },
      multiAz: isProd,
      allocatedStorage: isProd ? 100 : 20,
      maxAllocatedStorage: isProd ? 500 : 50,
      storageEncrypted: true,
      backupRetention: cdk.Duration.days(isProd ? 14 : 1),
      deletionProtection: isProd,
      removalPolicy: isProd ? cdk.RemovalPolicy.RETAIN : cdk.RemovalPolicy.DESTROY,
      databaseName: 'career_agent',
      credentials: rds.Credentials.fromGeneratedSecret('postgres'),
    });

    this.assetsBucket = new s3.Bucket(this, 'CareerAgentAssets', {
      bucketName: `career-agent-${props.environment}-assets`,
      encryption: s3.BucketEncryption.S3_MANAGED,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      versioned: isProd,
      removalPolicy: isProd ? cdk.RemovalPolicy.RETAIN : cdk.RemovalPolicy.DESTROY,
      lifecycleRules: [
        {
          id: 'expire-exports',
          prefix: 'exports/',
          expiration: cdk.Duration.days(30),
        },
      ],
    });

    const redisSubnetGroup = new elasticache.CfnSubnetGroup(this, 'RedisSubnetGroup', {
      description: 'CareerAgent Redis subnet group',
      subnetIds: props.vpc.selectSubnets({ subnetType: ec2.SubnetType.PRIVATE_ISOLATED }).subnetIds,
    });

    const redisCluster = new elasticache.CfnCacheCluster(this, 'CareerAgentRedis', {
      cacheNodeType: isProd ? 'cache.r6g.large' : 'cache.t4g.micro',
      engine: 'redis',
      numCacheNodes: 1,
      cacheSubnetGroupName: redisSubnetGroup.ref,
    });
    redisCluster.addDependency(redisSubnetGroup);

    this.redisEndpoint = redisCluster.attrRedisEndpointAddress;
  }
}
```

- [ ] **Step 6: Create `infrastructure/cdk/lib/auth-stack.ts`**

```typescript
import * as cdk from 'aws-cdk-lib';
import * as cognito from 'aws-cdk-lib/aws-cognito';
import { Construct } from 'constructs';

export interface AuthStackProps extends cdk.StackProps {
  environment: string;
}

export class AuthStack extends cdk.Stack {
  public readonly userPool: cognito.UserPool;
  public readonly userPoolClient: cognito.UserPoolClient;

  constructor(scope: Construct, id: string, props: AuthStackProps) {
    super(scope, id, props);

    const isProd = props.environment === 'prod';

    this.userPool = new cognito.UserPool(this, 'CareerAgentUserPool', {
      userPoolName: `career-agent-${props.environment}`,
      signInAliases: { email: true },
      selfSignUpEnabled: true,
      autoVerify: { email: true },
      passwordPolicy: {
        minLength: 10,
        requireLowercase: true,
        requireUppercase: true,
        requireDigits: true,
        requireSymbols: false,
      },
      standardAttributes: {
        email: { required: true, mutable: false },
        fullname: { required: true, mutable: true },
      },
      customAttributes: {
        user_id: new cognito.StringAttribute({ mutable: false }),
        subscription_tier: new cognito.StringAttribute({ mutable: true }),
        role: new cognito.StringAttribute({ mutable: true }),
        onboarding_state: new cognito.StringAttribute({ mutable: true }),
      },
      mfa: cognito.Mfa.OPTIONAL,
      accountRecovery: cognito.AccountRecovery.EMAIL_ONLY,
      removalPolicy: isProd ? cdk.RemovalPolicy.RETAIN : cdk.RemovalPolicy.DESTROY,
    });

    this.userPoolClient = this.userPool.addClient('CareerAgentClient', {
      userPoolClientName: `career-agent-${props.environment}-client`,
      authFlows: {
        userPassword: true,
        userSrp: true,
      },
      oAuth: {
        flows: { authorizationCodeGrant: true },
        scopes: [cognito.OAuthScope.EMAIL, cognito.OAuthScope.OPENID, cognito.OAuthScope.PROFILE],
      },
    });

    new cdk.CfnOutput(this, 'UserPoolId', { value: this.userPool.userPoolId });
    new cdk.CfnOutput(this, 'UserPoolClientId', { value: this.userPoolClient.userPoolClientId });
  }
}
```

- [ ] **Step 7: Create `infrastructure/cdk/bin/career-agent.ts`**

```typescript
#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { NetworkStack } from '../lib/network-stack';
import { DataStack } from '../lib/data-stack';
import { AuthStack } from '../lib/auth-stack';

const app = new cdk.App();
const environment = app.node.tryGetContext('environment') ?? 'dev';

const env = {
  account: process.env.CDK_DEFAULT_ACCOUNT,
  region: process.env.CDK_DEFAULT_REGION ?? 'us-east-1',
};

const network = new NetworkStack(app, `CareerAgent-Network-${environment}`, {
  env,
  environment,
});

new DataStack(app, `CareerAgent-Data-${environment}`, {
  env,
  environment,
  vpc: network.vpc,
});

new AuthStack(app, `CareerAgent-Auth-${environment}`, {
  env,
  environment,
});
```

- [ ] **Step 8: Install and synth**

```bash
cd infrastructure/cdk
pnpm install
pnpm synth
```
Expected: CDK synthesizes successfully, produces CloudFormation templates in `cdk.out/`. No deploy.

- [ ] **Step 9: Commit**

```bash
git add infrastructure/
git commit -m "feat(cdk): scaffold Network, Data, and Auth stacks"
```

- [ ] **Step 10: Wire `cdk-synth` into CI (if not done in Task 2)**

Add the `cdk-synth` job from **Task 2** to `.github/workflows/ci.yml` so `pnpm run synth` runs on every PR once `infrastructure/cdk` exists. Commit:

```bash
git add .github/workflows/ci.yml
git commit -m "ci: add CDK synth job"
```

---

## Task 24: Phase 1 Integration Smoke Test

**Files:**
- Modify: `backend/tests/integration/test_health.py` (add readiness DB check)

- [ ] **Step 1: Add a DB connectivity check to `/health/ready`**

Update `backend/src/career_agent/api/health.py`:

```python
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from career_agent.db import get_db

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
async def ready(db: AsyncSession = Depends(get_db)) -> dict[str, object]:
    checks: dict[str, str] = {}
    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:  # noqa: BLE001
        checks["database"] = f"error: {type(e).__name__}"

    status = "ok" if all(v == "ok" for v in checks.values()) else "degraded"
    return {"status": status, "checks": checks}
```

- [ ] **Step 2: Update readiness test**

Update `backend/tests/integration/test_health.py`:

```python
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_endpoint_returns_ok(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_health_ready_endpoint_returns_ok_with_db(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["checks"]["database"] == "ok"
```

- [ ] **Step 3: Run the full backend suite**

```bash
cd backend
uv run alembic upgrade head
uv run pytest -v
```
Expected: All tests pass end-to-end.

- [ ] **Step 4: Manual smoke test**

```bash
cd backend
uv run uvicorn career_agent.main:app --reload
# In another terminal:
curl http://localhost:8000/api/v1/health
curl http://localhost:8000/api/v1/health/ready
# Both return ok with database check
```

- [ ] **Step 5: Frontend build smoke test**

```bash
cd ~/projects/personal/career-agent
pnpm install
pnpm -r build
```
Expected: All 4 frontend projects (user-portal, admin-ui, marketing, pdf-render) + CDK build cleanly.

- [ ] **Step 6: Commit**

```bash
git add backend/src/career_agent/api/health.py backend/tests/integration/test_health.py
git commit -m "feat(backend): add DB check to /health/ready"
```

---

## Task 25: Phase 1 Completion Verification

- [ ] **Step 1: Run all tests**

```bash
cd backend
uv run pytest -v --cov=career_agent --cov-report=term-missing
```
Expected: 100% of tests pass.

- [ ] **Step 2: Run linters**

```bash
cd backend
uv run ruff check src/ tests/
uv run black --check src/ tests/
uv run mypy src/
```
Expected: All pass.

- [ ] **Step 3: Verify full frontend builds**

```bash
cd ~/projects/personal/career-agent
pnpm -r build
```

- [ ] **Step 4: Verify CDK synth**

```bash
cd infrastructure/cdk
pnpm synth -c environment=dev
```
Expected: 3 stacks synthesized.

- [ ] **Step 5: Final commit marker**

```bash
git tag phase1-complete -m "Phase 1 foundation complete — backend scaffolded with auth, profile, resume upload"
git log --oneline
```

- [ ] **Step 6: Acceptance checklist**

Verify each of these is working:

- [ ] docker-compose brings up Postgres + Redis
- [ ] Backend starts with `uv run uvicorn career_agent.main:app --reload`
- [ ] `GET /api/v1/health` returns `{"status":"ok"}`
- [ ] `GET /api/v1/health/ready` returns ok with database check
- [ ] `GET /api/v1/auth/me` requires valid JWT and returns user data
- [ ] `GET /api/v1/profile` auto-creates empty profile on first access
- [ ] `PUT /api/v1/profile` updates preferences and advances onboarding state
- [ ] `POST /api/v1/profile/resume` uploads PDF/DOCX, parses text, stores in S3
- [ ] `POST /api/v1/profile/export` returns user + profile JSON
- [ ] `DELETE /api/v1/profile` removes user account
- [ ] All errors follow `{"error":{"code","message","request_id"}}` envelope
- [ ] Alembic migrations apply cleanly both up and down
- [ ] All 4 frontend projects build with `pnpm -r build`
- [ ] CDK synthesizes 3 stacks without errors
- [ ] CI workflow passes on a PR

---

## Phase 1 Summary

**What's built:**
- Monorepo scaffolding with pnpm workspaces + uv
- FastAPI backend with: config, logging, error envelope, request IDs, health checks, auth (Cognito JWT), profile CRUD, resume upload with PDF/DOCX parsing + S3 storage, GDPR export/delete
- Alembic migrations for Phase 1 tables (users, subscriptions, profiles, star_stories) with indexes from Appendix H
- CDK stacks scaffolded but not deployed: Network, Data (RDS, S3, Redis), Auth (Cognito)
- 4 frontend skeletons (user-portal, admin-ui, marketing, pdf-render) with Tailwind + Notion palette
- docker-compose for local dev
- CI workflow (lint + test)
- ~15 integration tests + ~10 unit tests covering the full foundation

**What's deferred to later phases:**
- LangGraph agent + conversations (Phase 2)
- All 6 feature modules (Phases 2-4)
- Stripe billing integration (Phase 2)
- Inngest functions (Phase 3)
- Full frontend UX (Phase 5)
- Real AWS deployment (Phase 5)

**Next phase:** Phase 2 — Agent + Module 1 (Evaluation) + Module 2 (CV Optimization) + Stripe billing.
