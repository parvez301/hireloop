#!/usr/bin/env bash
set -euo pipefail
# One-time / version-bump: build xcaddy + Route53 and push to hireloop-caddy ECR.
# Usage: AWS_REGION=us-east-1 AWS_ACCOUNT_ID=... ./build-and-push.sh

ROOT="$(cd "$(dirname "$0")" && pwd)"
REGION="${AWS_REGION:-us-east-1}"
ACCOUNT="${AWS_ACCOUNT_ID:?Set AWS_ACCOUNT_ID}"
REPO="${ECR_CADDY_REPO:-hireloop-caddy}"
TAG="${CADDY_TAG:-2-route53}"

aws ecr describe-repositories --repository-names "$REPO" --region "$REGION" >/dev/null 2>&1 \
  || aws ecr create-repository --repository-name "$REPO" --region "$REGION"

aws ecr get-login-password --region "$REGION" \
  | docker login --username AWS --password-stdin "${ACCOUNT}.dkr.ecr.${REGION}.amazonaws.com"

docker buildx build --platform linux/arm64 -t "${REPO}:${TAG}" -f "${ROOT}/Dockerfile" "${ROOT}"
docker tag "${REPO}:${TAG}" "${ACCOUNT}.dkr.ecr.${REGION}.amazonaws.com/${REPO}:${TAG}"
docker push "${ACCOUNT}.dkr.ecr.${REGION}.amazonaws.com/${REPO}:${TAG}"
