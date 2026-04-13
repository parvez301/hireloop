#!/usr/bin/env bash
# Post-deploy smoke checks for Phase 5a.1 (read-only AWS CLI queries).
set -euo pipefail

REGION="${AWS_REGION:-us-east-1}"
export AWS_PAGER=""

echo "== Route53 hosted zone hireloop.xyz =="
aws route53 list-hosted-zones-by-name --dns-name hireloop.xyz --query 'HostedZones[0].Id' --output text

echo "== ACM certificates (ISSUED, hireloop) =="
aws acm list-certificates --region "$REGION" \
  --query "CertificateSummaryList[?contains(DomainName, \`hireloop\`) && Status==\`ISSUED\`]" \
  --output table

echo "== VPC default filter hireloop-shared =="
aws ec2 describe-vpcs --region "$REGION" \
  --filters "Name=tag:Name,Values=hireloop-shared" \
  --query 'Vpcs[0].{Cidr:CidrBlock,Id:VpcId}' --output table

echo "== RDS instances (engine postgres) =="
aws rds describe-db-instances --region "$REGION" \
  --query 'DBInstances[?Engine==`postgres`].{Id:DBInstanceIdentifier,Status:DBInstanceStatus}' \
  --output table

echo "== Cognito user pool HireLoop-Users-dev =="
aws cognito-idp list-user-pools --max-results 20 --region "$REGION" \
  --query "UserPools[?Name==\`HireLoop-Users-dev\`]" --output table

echo "== Secrets Manager hireloop/dev/* (expect 8) =="
aws secretsmanager list-secrets --region "$REGION" \
  --query "SecretList[?starts_with(Name, \`hireloop/dev/\`)].Name" --output text | tr '\t' '\n' | wc -l

echo "== SSM /hireloop/ parameters (expect 12+) =="
aws ssm describe-parameters --region "$REGION" \
  --parameter-filters "Key=Name,Option=BeginsWith,Values=/hireloop/" \
  --query 'length(Parameters)' --output text

echo "Smoke script finished (manual: verify secret count 8 + 1 DatabaseSecret = 9 total)."
