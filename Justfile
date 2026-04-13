# HireLoop development task runner
# Install: brew install just
# Usage:  just <recipe>    e.g. just dev, just test

set dotenv-load := false

backend := "backend"
portal  := "user-portal"
cdk     := "infrastructure/cdk"

# ─── Backend ──────────────────────────────────────────────

# Start backend with hot reload
dev:
    cd {{backend}} && uv run uvicorn hireloop.main:app --reload --port 8000

# Run full test suite
test *args='':
    cd {{backend}} && uv run pytest -v {{args}}

# Run tests, stop on first failure
test-fast *args='':
    cd {{backend}} && uv run pytest -x -q {{args}}

# Lint (ruff + black + mypy)
lint:
    cd {{backend}} && uv run ruff check src/ tests/ && uv run black --check src/ tests/ && uv run mypy src/

# Auto-format (ruff fix + black)
fmt:
    cd {{backend}} && uv run ruff check --fix src/ tests/ && uv run black src/ tests/

# Run alembic migrations
migrate:
    cd {{backend}} && uv run alembic upgrade head

# Create a new migration
migration name:
    cd {{backend}} && uv run alembic revision --autogenerate -m "{{name}}"

# Drop and recreate the local database, then migrate
reset-db:
    psql -h localhost -d postgres -c "DROP DATABASE IF EXISTS hireloop;"
    psql -h localhost -d postgres -c "CREATE DATABASE hireloop;"
    cd {{backend}} && uv run alembic upgrade head

# Install backend dependencies
install:
    cd {{backend}} && uv sync --all-extras --dev

# ─── Frontend ─────────────────────────────────────────────

# Start user-portal dev server
fe:
    cd {{portal}} && pnpm dev

# Run frontend tests
fe-test:
    cd {{portal}} && pnpm test

# ─── Infrastructure ───────────────────────────────────────

# Docker compose up (postgres, redis, inngest, localstack, pdf-render)
up:
    docker-compose up -d

# Docker compose down
down:
    docker-compose down

# CDK synth (validate all stacks)
synth:
    cd {{cdk}} && npx cdk synth

# ─── Convenience ──────────────────────────────────────────

# Check everything before commit (lint + test)
check: lint test

# Quick curl test (requires backend running + ENVIRONMENT=dev)
curl-test endpoint='/api/v1/profile':
    curl -s -H "Authorization: Bearer dev-bypass" http://localhost:8000{{endpoint}} | python3 -m json.tool
