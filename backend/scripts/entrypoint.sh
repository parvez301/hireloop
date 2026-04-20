#!/bin/sh
set -e
# Migrations run in the MigrationFn Lambda (see deploy.yml migrate job),
# not here — the EC2 backend connects as a CRUD-only app user.
exec uvicorn hireloop.main:app --host 0.0.0.0 --port 8000
