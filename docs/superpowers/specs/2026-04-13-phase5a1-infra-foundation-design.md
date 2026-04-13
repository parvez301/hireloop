# Phase 5a.1 — Infrastructure Foundation Design

> **Delta spec.** References the parent design doc at `specs/2026-04-10-careeragent-design.md`. Only specifies what 5a.1 adds or changes.

**Goal:** Stand up the minimum AWS foundation that later sub-phases (5a.2 backend compute, 5a.3 async/pdf-render, 5a.4 frontend CDN, 5a.5 CI/CD) build on top of, without deploying any application code. Also: rename the entire codebase from CareerAgent to HireLoop so AWS resource names are born correct.

**Phase context:** This is engineering Phase 5a.1 within the Phase 5 (polish + deploy) umbrella. See the phase roadmap in project memory for the full engineering phase decomposition. Parent design doc: `docs/superpowers/specs/2026-04-10-careeragent-design.md`.

---

## 1. Locked Decisions

| # | Decision | Rationale |
|---|---|---|
| D1 | Single AWS account | Solo dev, no org complexity yet |
| D2 | `dev` environment only in 5a.1 | Sandbox/prod infra added in later sub-phases |
| D3 | `us-east-1` region | Cheapest, most service availability, required for CloudFront + ACM |
| D4 | `hireloop.xyz` domain (already purchased) | Route53 hosted zone + ACM wildcard cert in scope |
| D5 | Full rename CareerAgent to HireLoop | AWS resource names are immutable once created; rename before first deploy |
| D6 | Wildcard cert `*.hireloop.xyz` + apex SAN | Covers all current + future subdomains; placeholder DNS for `app`/`api`/`admin` |
| D7 | Secret-per-key under `hireloop/{env}/*` | Fine-grained IAM, independent rotation; manual populate via script |
| D8 | One EC2 per env (only dev in 5a.1) | Real isolation between environments; EC2 provisioned in 5a.2 Compute stack |
| D9 | Inngest Cloud stays (no self-hosting) | Reduces 5a.1 scope; EC2 runs SSE backend only |
| D10 | ALB with path-based rules | Single origin `api.hireloop.xyz`; SSE paths to EC2, rest to Lambda; provisioned in 5a.2 |
| D11 | fck-nat on dedicated `t4g.nano` | Saves ~$29/mo vs NAT Gateway; provisioned in 5a.2 with Lambda |
| D12 | Shared infra substrate + per-env Auth/Config/Compute | One VPC, one RDS (3 DBs), per-DB users with strict GRANTs for isolation |

---

## 2. Architecture Overview

### Compute model (5a.2+ scope, documented here for context)

| Tier | Runs on | Contains |
|---|---|---|
| **Stateless API** | Lambda (via Mangum adapter, ALB target) | CRUD endpoints, billing webhooks, evaluations, CV outputs, interview preps, negotiations, feedback, auth, onboarding |
| **Stateful/streaming** | EC2 `t4g.small` per env | SSE endpoints (`POST /conversations/:id/messages`, `GET /conversations/:id/stream`), background workers, long-lived agent turns |
| **pdf-render** | TBD (Lambda container image or EC2) | Deferred to 5a.3 brainstorm |
| **Async fan-out** | Inngest Cloud (managed SaaS) | Job scanning, batch evaluation, L0/L1/L2 funnel |
| **Database** | RDS Postgres 16 (shared instance, 3 DBs) | `hireloop_dev`, `hireloop_sandbox`, `hireloop_prod` |
| **Assets** | S3 (shared bucket, `{env}/` prefix convention) | Resumes, CV PDFs, exports |
| **Auth** | Cognito (per-env user pool) | User auth, JWT issuance |
| **CDN** | CloudFront (5a.4 scope) | user-portal SPA, admin-ui SPA |

### What 5a.1 provisions

- Route53 hosted zone + ACM wildcard certificate
- VPC with subnets + security group shells
- RDS instance with 3 databases + per-database app users
- S3 assets bucket
- Cognito user pool + client (dev only)
- Secrets Manager skeletons + SSM parameters (dev only)
- Populate + smoke-test scripts

### What 5a.1 does NOT provision

- Any compute (EC2, Lambda, ALB, fck-nat) — 5a.2
- Fastify pdf-render — 5a.3
- CloudFront distributions, S3 frontend buckets — 5a.4
- CI/CD pipelines — 5a.5
- Prod/sandbox-specific resources beyond database creation
- WAF, backup vaults, observability stack, Cognito custom domain

---

## 3. Task 0: CareerAgent to HireLoop Rename

Runs before any CDK work. Must leave all ~165 backend tests + ~25 frontend tests green. Single bundled commit.

### What changes

| Surface | From | To |
|---|---|---|
| Python package | `backend/src/career_agent/` | `backend/src/hireloop/` |
| Python imports | `from career_agent.*` | `from hireloop.*` |
| `pyproject.toml` name | `career-agent` | `hireloop` |
| FastAPI app | `career_agent.main:app` | `hireloop.main:app` |
| Docker compose services | `career-agent-*` | `hireloop-*` |
| Docker compose DB name | `career_agent` | `hireloop` |
| CDK app entry | `bin/career-agent.ts` | `bin/hireloop.ts` |
| CDK stack names | `CareerAgent-*` | `HireLoop-*` |
| CDK construct IDs | `CareerAgent*` | `HireLoop*` |
| Frontend `package.json` name | `career-agent-user-portal` | `hireloop-user-portal` |
| pdf-render `package.json` name | `career-agent-pdf-render` | `hireloop-pdf-render` |
| Env var prefixes (if any) | `CAREER_AGENT_*` | `HIRELOOP_*` |
| `CLAUDE.md` + README | `CareerAgent` references | `HireLoop` |
| Cognito user pool name (CDK) | `CareerAgent-Users-dev` | `HireLoop-Users-dev` |
| Log-line prefixes, error codes, comments | `career_agent` / `CareerAgent` | `hireloop` / `HireLoop` |

### What stays unchanged

- Historical specs + plans (`docs/superpowers/specs/2026-04-*-careeragent-*.md`) — dated artifacts, not rewritten
- Git history (no force rewrite)
- Alembic migration table names (`alembic_version` table, migration filenames)
- Alembic migration content (these reference table names, not package names)

### Risk callouts

- **Alembic `env.py`** — imports the Python package for metadata. Breaks on rename.
- **IDE/editor** — must restart Cursor/Claude Code after rename (stale file handles + import maps).
- **`.vscode/settings.json`**, `.idea/` — may hold stale paths.
- **Claude Code memory directory** — `~/.claude/projects/-Users-parvez-projects-personal-career-agent/` path depends on repo directory name. If the parent dir renames, Claude Code creates a new project directory. Memory files need manual copy.

---

## 4. CDK Stack Topology

Five stacks deployed in order. Shared infra has no env suffix; per-env stacks are suffixed.

```
HireLoop-DNS              (Route53 zone + ACM wildcard cert)
      |
HireLoop-Network          (VPC, subnets, SG shells, S3 gateway endpoint)
      |
HireLoop-Data             (RDS + DB bootstrap custom resource + S3 assets)
      |
HireLoop-Auth-dev         (Cognito user pool + client)
      |
HireLoop-Config-dev       (Secrets Manager skeletons + SSM params)
```

### 4.1 `HireLoop-DNS`

- `route53.PublicHostedZone` for `hireloop.xyz`
  - Output: `nameServers` (human must transfer at registrar)
- `acm.Certificate` for `hireloop.xyz` + SAN `*.hireloop.xyz`
  - DNS validation via the hosted zone (auto-creates CNAME records)
  - Region: us-east-1 (required for CloudFront + Cognito custom domain compatibility)
- Placeholder A records: `app.hireloop.xyz`, `api.hireloop.xyz`, `admin.hireloop.xyz` all pointing to `127.0.0.1` (holds the DNS names so they don't return NXDOMAIN; 5a.2 and 5a.4 replace with real ALB/CloudFront alias records)
- Outputs exported to SSM:
  - `/hireloop/shared/dns/hosted-zone-id`
  - `/hireloop/shared/dns/certificate-arn`

### 4.2 `HireLoop-Network`

- `ec2.Vpc` — 2 AZs, CIDR `10.0.0.0/16`
- Subnets per AZ:
  - Public `/24` — for ALB, fck-nat, SSE EC2 (5a.2)
  - Private-egress `/20` — for Lambda ENIs (5a.2)
  - Private-isolated `/22` — for RDS
- **No NAT in 5a.1** — fck-nat EC2 lands with Compute in 5a.2
- Security groups (pre-declared, empty ingress rules populated by 5a.2):
  - `SG-ALB` — will allow 443 from `0.0.0.0/0`
  - `SG-EC2-Backend` — will allow 8000 from SG-ALB
  - `SG-Lambda` — outbound only
  - `SG-DbBootstrap` — egress 5432 to SG-RDS + egress to S3 gateway prefix list (used by Data stack custom resource Lambda)
  - `SG-RDS` — will allow 5432 from SG-Lambda + SG-EC2-Backend + SG-DbBootstrap
  - `SG-FckNat` — will allow from private-egress, egress `0.0.0.0/0`
- VPC endpoints: S3 gateway endpoint (free)
- Outputs: `vpcId`, subnet IDs, SG IDs

### 4.3 `HireLoop-Data`

**RDS instance:**
- Engine: PostgreSQL 16
- Instance class: `t4g.small` (Graviton, 2 vCPU / 2 GB RAM)
- Storage: `gp3` 20 GB, encrypted (AWS-managed KMS key)
- Single-AZ
- `publiclyAccessible: false`
- Subnet group: private-isolated
- Security group: `SG-RDS`
- Backup retention: 7 days
- Auto minor version upgrade: on
- Master credentials: CDK-managed `DatabaseSecret` (rotation off for dev)
- `RemovalPolicy.RETAIN`

**Database bootstrap custom resource:**

A one-shot Lambda (CDK `Provider` framework) placed in the **private-isolated subnet** alongside RDS. Connects via master credentials and runs as the master user, connecting to each database in turn.

**Networking note:** The Provider framework Lambda responds to CloudFormation via a pre-signed S3 URL. The S3 gateway endpoint (already provisioned in `HireLoop-Network`) handles this traffic — no NAT or interface VPC endpoints required. CloudWatch Logs delivery will silently fail from the isolated subnet (no Logs endpoint), which is acceptable for a one-shot bootstrap Lambda. The Lambda uses a dedicated `SG-DbBootstrap` security group with egress to `SG-RDS` on port 5432 and egress to the S3 gateway prefix list. `SG-RDS` must allow ingress from `SG-DbBootstrap` in addition to the existing `SG-Lambda` + `SG-EC2-Backend` rules.

```sql
-- Create databases
CREATE DATABASE hireloop_dev;
CREATE DATABASE hireloop_sandbox;
CREATE DATABASE hireloop_prod;

-- Create per-env app users
CREATE USER hireloop_dev_app WITH PASSWORD '<random>';
CREATE USER hireloop_sandbox_app WITH PASSWORD '<random>';
CREATE USER hireloop_prod_app WITH PASSWORD '<random>';

-- Grant isolation (bootstrap connects as master to each database in turn)
-- Connected to hireloop_dev as master:
GRANT CONNECT ON DATABASE hireloop_dev TO hireloop_dev_app;
GRANT USAGE ON SCHEMA public TO hireloop_dev_app;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO hireloop_dev_app;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO hireloop_dev_app;
ALTER DEFAULT PRIVILEGES FOR ROLE <master_user> IN SCHEMA public
  GRANT ALL PRIVILEGES ON TABLES TO hireloop_dev_app;
ALTER DEFAULT PRIVILEGES FOR ROLE <master_user> IN SCHEMA public
  GRANT ALL PRIVILEGES ON SEQUENCES TO hireloop_dev_app;

-- (same pattern for sandbox_app on hireloop_sandbox, prod_app on hireloop_prod)
-- NO cross-database grants. dev_app cannot CONNECT to hireloop_sandbox or hireloop_prod.
-- REVOKE CONNECT ON DATABASE hireloop_sandbox FROM PUBLIC; (repeat per DB, then grant only to its app user)
```

Per-env app user passwords stored in Secrets Manager: `hireloop/{env}/db-app-password`.

**S3 assets bucket:**
- Name: `hireloop-shared-assets-<accountId>`
- Versioning: off
- Encryption: SSE-S3
- Block all public access: on
- Lifecycle rules: `exports/*` expire 30d, `temp/*` expire 7d
- Prefix convention: `{env}/resumes/`, `{env}/cv-outputs/`, `{env}/exports/`
- `RemovalPolicy.RETAIN`

**Outputs:** `dbEndpoint`, `dbPort`, `masterSecretArn`, `assetsBucketName`, `assetsBucketArn`

### 4.4 `HireLoop-Auth-dev`

- `cognito.UserPool` — name `HireLoop-Users-dev`
  - Sign-in: email
  - Password policy: 10 chars, mixed case, digit required
  - MFA: optional
  - Self-signup: on (dev only)
  - Custom attributes: `custom:user_id`, `custom:subscription_tier`, `custom:role`, `custom:onboarding_state` (Cognito auto-prefixes `custom:` — these must match the existing JWT claim mapping in `backend/src/hireloop/api/deps.py` and profile onboarding flow; verify attribute names after rename)
  - Account recovery: email only
  - `RemovalPolicy.RETAIN` (negligible cost; teardown is manual — acceptable for dev, required for user safety in prod)
- `cognito.UserPoolClient` — no client secret
  - Auth flows: SRP + refresh token + `ALLOW_USER_PASSWORD_AUTH` (dev convenience)
  - Default Cognito domain: `hireloop-dev.auth.us-east-1.amazoncognito.com`
- Outputs: `userPoolId`, `userPoolClientId`, `userPoolArn`

### 4.5 `HireLoop-Config-dev`

**Secrets Manager (empty skeletons, placeholder `{}`):**

| Secret path | Purpose | Populated by |
|---|---|---|
| `hireloop/dev/anthropic-api-key` | Claude API | Manual (populate script) |
| `hireloop/dev/google-api-key` | Gemini API | Manual |
| `hireloop/dev/stripe-secret-key` | Stripe billing | Manual |
| `hireloop/dev/stripe-webhook-secret` | Stripe webhooks | Manual |
| `hireloop/dev/pdf-render-shared-secret` | Backend-pdf-render HMAC | Manual |
| `hireloop/dev/inngest-event-key` | Inngest Cloud | Manual |
| `hireloop/dev/inngest-signing-key` | Inngest Cloud | Manual |
| `hireloop/dev/db-app-password` | RDS hireloop_dev_app password | CDK custom resource (Data stack) |

**SSM Parameter Store:**

| Parameter path | Value source |
|---|---|
| `/hireloop/dev/cognito/user-pool-id` | Auth stack output |
| `/hireloop/dev/cognito/user-pool-client-id` | Auth stack output |
| `/hireloop/dev/cognito/region` | `us-east-1` |
| `/hireloop/dev/aws/region` | `us-east-1` |
| `/hireloop/dev/s3/assets-bucket-name` | Data stack output |
| `/hireloop/dev/db/endpoint` | Data stack output |
| `/hireloop/dev/db/port` | `5432` |
| `/hireloop/dev/db/database-name` | `hireloop_dev` |
| `/hireloop/dev/db/app-user` | `hireloop_dev_app` |
| `/hireloop/shared/dns/hosted-zone-id` | DNS stack output |
| `/hireloop/shared/dns/certificate-arn` | DNS stack output |
| `/hireloop/shared/rds/master-secret-arn` | Data stack output |

---

## 5. CDK App Wiring

```typescript
// bin/hireloop.ts
import * as cdk from 'aws-cdk-lib';
import { DnsStack } from '../lib/dns-stack';
import { NetworkStack } from '../lib/network-stack';
import { DataStack } from '../lib/data-stack';
import { AuthStack } from '../lib/auth-stack';
import { ConfigStack } from '../lib/config-stack';

const app = new cdk.App();
const env = { account: process.env.CDK_DEFAULT_ACCOUNT, region: 'us-east-1' };

// Shared infrastructure (no env suffix)
const dns = new DnsStack(app, 'HireLoop-DNS', { env });
const network = new NetworkStack(app, 'HireLoop-Network', { env });
const data = new DataStack(app, 'HireLoop-Data', {
  env,
  vpc: network.vpc,
  sgRds: network.securityGroups.rds,
  isolatedSubnets: network.isolatedSubnets,
});

// Per-environment (only dev in 5a.1)
const authDev = new AuthStack(app, 'HireLoop-Auth-dev', { env, environment: 'dev' });
new ConfigStack(app, 'HireLoop-Config-dev', {
  env,
  environment: 'dev',
  userPool: authDev.userPool,
  userPoolClient: authDev.userPoolClient,
  assetsBucketName: data.assetsBucket.bucketName,
  dbEndpoint: data.dbInstance.dbInstanceEndpointAddress,
  dbPort: data.dbInstance.dbInstanceEndpointPort,
  hostedZoneId: dns.hostedZone.hostedZoneId,
  certificateArn: dns.certificate.certificateArn,
  masterSecretArn: data.masterSecret.secretArn,
});
```

---

## 6. Deployment Flow

### Prerequisites (human actions)

1. `aws sts get-caller-identity` — confirm correct account
2. `npx cdk bootstrap aws://<account>/us-east-1` — one-time CDK toolkit stack
3. After `HireLoop-DNS` deploys: update registrar nameservers for `hireloop.xyz` (manual, cannot be automated)
4. After `HireLoop-Config-dev` deploys: run `infrastructure/scripts/populate-dev-secrets.sh`

### Deploy sequence

```bash
cd infrastructure/cdk && npm ci
npx cdk synth                         # Sanity check all 5 stacks
npx cdk deploy HireLoop-DNS           # ~5 min
# >>> HUMAN: transfer NS at registrar, wait for propagation <<<
npx cdk deploy HireLoop-Network       # ~2 min
npx cdk deploy HireLoop-Data          # ~12 min (RDS + custom resource)
npx cdk deploy HireLoop-Auth-dev      # ~1 min
npx cdk deploy HireLoop-Config-dev    # ~30 sec
# >>> HUMAN: populate secrets <<<
bash ../scripts/populate-dev-secrets.sh
```

Total: ~20 min CDK + NS propagation wait.

### Smoke tests (`infrastructure/scripts/smoke-test-infra.sh`)

1. Route53 zone exists for `hireloop.xyz`
2. ACM cert status `ISSUED`
3. VPC exists with expected CIDR
4. RDS instance status `available`
5. Cognito pool `HireLoop-Users-dev` exists
6. 8 Secrets Manager entries under `hireloop/dev/*` (7 manual + 1 auto db-app-password) + 1 CDK-managed `DatabaseSecret` (auto-named, outside `hireloop/dev/` namespace) = 9 total secrets
7. 12+ SSM parameters under `/hireloop/`
8. DB connectivity: `SELECT 1` on each database via per-env app user (uses Data stack custom resource Lambda or a dedicated smoke-test Lambda)

### Rollback / teardown

- RDS: `RETAIN` — manual `aws rds delete-db-instance --skip-final-snapshot` required
- S3 assets: `RETAIN` — manual empty + delete
- Cognito user pool: `RETAIN` — don't accidentally delete user accounts
- All other resources: `DESTROY` — safe to `cdk destroy` and redeploy

---

## 7. Cost Estimate

### 5a.1 alone (no compute running)

| Item | Monthly |
|---|---|
| RDS `t4g.small` + 20 GB gp3 | ~$18 |
| S3 assets | <$1 |
| Route53 hosted zone | $0.50 |
| ACM certificate | Free |
| Cognito (free tier) | Free |
| Secrets Manager (9 total: 8 under `hireloop/dev/*` + 1 CDK DatabaseSecret) | ~$3.60 |
| SSM Parameter Store | Free |
| S3 gateway VPC endpoint | Free |
| **5a.1 subtotal** | **~$23/mo** |

### With 5a.2 compute added (reference, not 5a.1 scope)

| Item | Monthly |
|---|---|
| 5a.1 base | ~$23 |
| SSE EC2 `t4g.small` (dev) | ~$12 |
| fck-nat `t4g.nano` | ~$4 |
| ALB + LCUs | ~$22 |
| Lambda invocations (dev) | <$1 |
| Inngest Cloud (free tier) | Free |
| **5a.1 + 5a.2 combined** | **~$63/mo** |

### Cost-cutting levers (not applied, documented)

- Drop VPC interface endpoints: already done (using fck-nat for all outbound)
- RDS nightly stop via EventBridge: saves ~$9/mo, DB unreachable at night
- Smaller RDS `t4g.micro`: saves ~$6/mo, 1 GB RAM is tight for 3 databases
- Drop ALB, two-hostname split: saves ~$22/mo, CORS complexity

---

## 8. Explicit Tech Debt

Logged here for future phases to address:

| Item | Phase to address | Risk if deferred |
|---|---|---|
| Shared RDS across dev/sandbox/prod | Before real users (prod promotion) | Noisy-neighbor, shared maintenance, blast radius |
| RDS single-AZ | Before prod traffic | Downtime on AZ failure |
| No WAF on ALB | Before prod traffic | No L7 protection |
| No observability (CloudWatch dashboards, alarms) | 5a.5 or later | Blind to issues |
| No backup vault / cross-region backups | Before real users | DR gap |
| Cognito default domain (not custom `auth.hireloop.xyz`) | Nice-to-have | Ugly login URL |
| `DISABLE_PAYWALL=true` no boot-time assertion | Before prod | Risk of accidentally disabling paywall in prod |
| SSE runs synchronously in POST /messages | Phase 5+ polish | Not a scale issue at dev traffic |
| Agent uses custom TOOL_CALL JSON envelope | Phase 5+ polish | Works, but non-standard |
| No per-user usage cap | After cost telemetry | Heavy users may exceed unit economics |

---

## 9. File Structure (new files in 5a.1)

```
infrastructure/
  cdk/
    bin/hireloop.ts                  # CDK app entry (renamed from career-agent.ts)
    lib/
      dns-stack.ts                   # Route53 + ACM
      network-stack.ts               # VPC, subnets, SGs (modified from existing)
      data-stack.ts                  # RDS + S3 (modified from existing)
      auth-stack.ts                  # Cognito (modified from existing)
      config-stack.ts                # Secrets Manager + SSM (new)
      constructs/
        db-bootstrap.ts              # Custom resource for CREATE DATABASE + users
    test/
      dns-stack.test.ts              # Snapshot test
      network-stack.test.ts          # Snapshot test
      data-stack.test.ts             # Snapshot test
      auth-stack.test.ts             # Snapshot test
      config-stack.test.ts           # Snapshot test
  scripts/
    populate-dev-secrets.sh          # Reads .env.deploy.local, calls put-secret-value
    smoke-test-infra.sh              # Post-deploy verification
  .env.deploy.local.example          # Template (gitignored, .example is committed)
```

---

## 10. 5a.1 Task Summary

| Task | Description | Depends on |
|---|---|---|
| 0 | CareerAgent to HireLoop rename | Nothing (gates everything) |
| 1 | CDK project restructure (`bin/hireloop.ts`, shared types) | Task 0 |
| 2 | `HireLoop-DNS` stack | Task 1 |
| 3 | `HireLoop-Network` stack | Task 1 |
| 4 | `HireLoop-Data` stack + DB bootstrap custom resource | Task 3 |
| 5 | `HireLoop-Auth-dev` stack | Task 1 |
| 6 | `HireLoop-Config-dev` stack | Tasks 4, 5 |
| 7 | `populate-dev-secrets.sh` + `smoke-test-infra.sh` | Task 6 |
| 8 | CDK synth validation + snapshot tests | Tasks 2-6 |
