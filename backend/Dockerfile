# syntax=docker/dockerfile:1
# Targets: `lambda` (AWS Lambda container) and `ec2` (SSE host). Default: `ec2`.
FROM python:3.12-slim AS builder
WORKDIR /build
RUN pip install --no-cache-dir uv
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY src ./src
COPY migrations ./migrations
COPY alembic.ini ./

FROM public.ecr.aws/lambda/python:3.12 AS lambda
# WeasyPrint runtime deps: Cairo, Pango, HarfBuzz, fontconfig + shared-mime-info.
# microdnf is the package manager on AWS Lambda's AL2023-based image.
RUN microdnf install -y \
      cairo \
      pango \
      harfbuzz \
      fontconfig \
      shared-mime-info \
 && microdnf clean all

WORKDIR /var/task
COPY --from=builder /build/.venv /var/task/.venv
COPY --from=builder /build/src ./src
COPY --from=builder /build/migrations ./migrations
COPY --from=builder /build/alembic.ini ./

# fontconfig needs a writable cache; Lambda's $HOME is read-only at runtime.
# Bake the cache at image build time pointing at /tmp so the first cold start
# doesn't spend time regenerating it (and doesn't fail on read-only paths).
ENV XDG_CACHE_HOME=/tmp/fontconfig
RUN mkdir -p /tmp/fontconfig && fc-cache -f 2>/dev/null || true

# PYTHONPATH must include .venv site-packages — the Lambda runtime's python
# doesn't read PATH for module imports, only PYTHONPATH.
ENV PYTHONPATH=/var/task/src:/var/task/.venv/lib/python3.12/site-packages
ENV PATH="/var/task/.venv/bin:${PATH}"
CMD ["hireloop.aws_lambda_adapter.handler"]

FROM python:3.12-slim AS ec2
# WeasyPrint runtime deps (Debian package names for python:3.12-slim).
RUN apt-get update && apt-get install -y --no-install-recommends \
      libcairo2 \
      libpango-1.0-0 \
      libpangoft2-1.0-0 \
      libharfbuzz0b \
      libfontconfig1 \
      fontconfig \
      shared-mime-info \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /build/.venv /app/.venv
COPY --from=builder /build/src ./src
COPY --from=builder /build/migrations ./migrations
COPY --from=builder /build/alembic.ini ./
COPY scripts/entrypoint.sh ./scripts/entrypoint.sh
RUN chmod +x ./scripts/entrypoint.sh

ENV XDG_CACHE_HOME=/tmp/fontconfig
RUN mkdir -p /tmp/fontconfig && fc-cache -f 2>/dev/null || true

ENV PYTHONPATH=/app/src
ENV PATH="/app/.venv/bin:${PATH}"
ENTRYPOINT ["./scripts/entrypoint.sh"]
