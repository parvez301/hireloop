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
WORKDIR /var/task
COPY --from=builder /build/.venv /var/task/.venv
COPY --from=builder /build/src ./src
COPY --from=builder /build/migrations ./migrations
COPY --from=builder /build/alembic.ini ./
# PYTHONPATH must include .venv site-packages — the Lambda runtime's python
# doesn't read PATH for module imports, only PYTHONPATH.
ENV PYTHONPATH=/var/task/src:/var/task/.venv/lib/python3.12/site-packages
ENV PATH="/var/task/.venv/bin:${PATH}"
CMD ["hireloop.aws_lambda_adapter.handler"]

FROM python:3.12-slim AS ec2
WORKDIR /app
COPY --from=builder /build/.venv /app/.venv
COPY --from=builder /build/src ./src
COPY --from=builder /build/migrations ./migrations
COPY --from=builder /build/alembic.ini ./
COPY scripts/entrypoint.sh ./scripts/entrypoint.sh
RUN chmod +x ./scripts/entrypoint.sh
ENV PYTHONPATH=/app/src
ENV PATH="/app/.venv/bin:${PATH}"
ENTRYPOINT ["./scripts/entrypoint.sh"]
