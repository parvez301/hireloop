#!/bin/sh
set -e
# uv is not in the ec2 image — .venv/bin is on PATH via Dockerfile.
alembic upgrade head
exec uvicorn hireloop.main:app --host 0.0.0.0 --port 8000
