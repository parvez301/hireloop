#!/usr/bin/env bash
# Idempotently create the two ECR repos App-dev expects to exist. Run once
# before `cdk deploy HireLoop-App-dev` on a fresh account.
# Requires: AWS credentials (AWS_PROFILE=hireloop) + aws CLI.

set -euo pipefail

REGION="${AWS_REGION:-us-east-1}"

ensure() {
  local name=$1
  local max=$2
  if aws ecr describe-repositories --repository-names "$name" --region "$REGION" >/dev/null 2>&1; then
    echo "ECR repo '$name' already exists — skipping"
  else
    aws ecr create-repository \
      --repository-name "$name" \
      --image-scanning-configuration scanOnPush=true \
      --region "$REGION" >/dev/null
    echo "Created ECR repo '$name'"
  fi
  aws ecr put-lifecycle-policy \
    --repository-name "$name" \
    --lifecycle-policy-text "{\"rules\":[{\"rulePriority\":1,\"description\":\"keep-last-$max\",\"selection\":{\"tagStatus\":\"any\",\"countType\":\"imageCountMoreThan\",\"countNumber\":$max},\"action\":{\"type\":\"expire\"}}]}" \
    --region "$REGION" >/dev/null
  echo "  lifecycle: retain last $max images"
}

ensure hireloop-backend 20
ensure hireloop-caddy 3
ensure hireloop-llm-bridge 5
