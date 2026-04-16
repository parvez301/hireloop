#!/usr/bin/env bash
# Build the marketing site and deploy to AWS S3 + CloudFront.
# Requires: AWS credentials, MarketingStack deployed (see infrastructure/cdk/lib/marketing-stack.ts).
#
# Usage: bash marketing/scripts/deploy.sh

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

REGION="${AWS_REGION:-us-east-1}"

echo "--> Looking up bucket + distribution from SSM"
BUCKET=$(aws ssm get-parameter \
  --name /hireloop/marketing/bucket-name \
  --region "$REGION" \
  --query Parameter.Value --output text)
DIST_ID=$(aws ssm get-parameter \
  --name /hireloop/marketing/distribution-id \
  --region "$REGION" \
  --query Parameter.Value --output text)
echo "    bucket=$BUCKET"
echo "    distribution=$DIST_ID"

echo "--> Installing deps + building"
pnpm install --frozen-lockfile
pnpm build

echo "--> Syncing dist/ to s3://$BUCKET/"
aws s3 sync dist/ "s3://$BUCKET/" \
  --delete \
  --region "$REGION" \
  --cache-control "public, max-age=300" \
  --exclude "assets/*"
# Long cache for hashed assets
aws s3 sync dist/assets/ "s3://$BUCKET/assets/" \
  --region "$REGION" \
  --cache-control "public, max-age=31536000, immutable"

echo "--> Invalidating CloudFront"
INVAL_ID=$(aws cloudfront create-invalidation \
  --distribution-id "$DIST_ID" \
  --paths "/*" \
  --query 'Invalidation.Id' --output text)
echo "    invalidation=$INVAL_ID"

echo
echo "Done. The site will be live at:"
echo "  https://hireloop.xyz"
echo "  https://www.hireloop.xyz"
echo
echo "Allow a minute or two for the invalidation to finish propagating."
