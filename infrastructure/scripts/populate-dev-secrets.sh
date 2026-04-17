#!/usr/bin/env bash
# Populate hireloop/dev/* secrets from a local env file (never commit real values).
# Usage: copy infrastructure/.env.deploy.local.example to infrastructure/.env.deploy.local, fill in keys, then:
#   bash infrastructure/scripts/populate-dev-secrets.sh

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_FILE="${ENV_FILE:-$ROOT/infrastructure/.env.deploy.local}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing $ENV_FILE — copy infrastructure/.env.deploy.local.example and fill values." >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

require() {
  local name=$1
  if [[ -z "${!name:-}" ]]; then
    echo "Missing required var: $name" >&2
    exit 1
  fi
}

require ANTHROPIC_API_KEY
require GOOGLE_API_KEY
require STRIPE_SECRET_KEY
require STRIPE_WEBHOOK_SECRET
require INNGEST_EVENT_KEY
require INNGEST_SIGNING_KEY

put_json_key() {
  # Writes {"key": "<value>"} — matches the JSON shape `buildApiEnv` reads via
  # `.secretValueFromJson("key").unsafeUnwrap()` in infrastructure/cdk/lib/app-stack.ts.
  local secret_id=$1
  local val=$2
  local payload
  payload=$(jq -n --arg v "$val" '{key: $v}')
  aws secretsmanager put-secret-value \
    --secret-id "$secret_id" \
    --secret-string "$payload" \
    --region "${AWS_REGION:-us-east-1}"
}

put_json_key "hireloop/dev/anthropic-api-key" "$ANTHROPIC_API_KEY"
put_json_key "hireloop/dev/google-api-key" "$GOOGLE_API_KEY"
put_json_key "hireloop/dev/stripe-secret-key" "$STRIPE_SECRET_KEY"
put_json_key "hireloop/dev/stripe-webhook-secret" "$STRIPE_WEBHOOK_SECRET"
put_json_key "hireloop/dev/inngest-event-key" "$INNGEST_EVENT_KEY"
put_json_key "hireloop/dev/inngest-signing-key" "$INNGEST_SIGNING_KEY"

echo "Updated 6 manual secrets under hireloop/dev/* (db-app-password is written by the HireLoop-Data bootstrap)."
