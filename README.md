# HireLoop

Candidate-side AI career assistant SaaS. See `docs/superpowers/specs/2026-04-10-careeragent-design.md` for the full spec.

## Quick Start

```bash
docker-compose up -d
cd backend && uv sync && uv run alembic upgrade head && uv run uvicorn hireloop.main:app --reload
cd user-portal && pnpm install && pnpm dev
```
