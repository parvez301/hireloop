# Phase 5a.2 — Backend Compute Design

> **Delta spec.** References the parent design doc at `docs/superpowers/specs/2026-04-10-careeragent-design.md` and the 5a.1 foundation at `docs/superpowers/specs/2026-04-13-phase5a1-infra-foundation-design.md`. Only specifies what 5a.2 adds, removes, or amends.

**Goal:** Deploy the HireLoop backend to AWS `dev` for the first time. Stand up: Lambda-based stateless API behind CloudFront on `api.dev.hireloop.xyz`, EC2-based SSE backend on `sse.dev.hireloop.xyz`, a CDK-declared migration Lambda, and a 6-job GitHub Actions deploy workflow. Dogfood-ready after one manual `cdk deploy` + first workflow run.

**Phase context:** 5a.2 within the Phase 5 (polish + deploy) umbrella. Consumes 5 stacks from 5a.1, adds a single new app-layer stack, and amends the 5a.1 Network + Data stacks. 5a.3 (async/pdf-render), 5a.4 (frontend CDN), and 5a.5 (CI/CD formalization) remain out of scope.

**Definition of done:** Code merged to main, one manual `cdk deploy HireLoop-App-dev`, first green GitHub Actions workflow run against dev, smoke test passes against `api.dev.hireloop.xyz` + `sse.dev.hireloop.xyz`. Stack stays standing.

---

## 1. Locked Decisions

| # | Decision | Rationale |
|---|---|---|
| D1 | Target **dev only** in 5a.2 (prod scoped to a later sub-phase) | Minimize blast radius of first deploy; prod adds approval gates + real keys that deserve separate attention. |
| D2 | **CloudFront + Lambda FURL** for bounded API on `api.dev.hireloop.xyz` | Cheapest edge; FURL BUFFERED mode simpler than API Gateway; free tier covers dev traffic. |
| D3 | **Direct A-record to EC2** on `sse.dev.hireloop.xyz` (not via CloudFront) | CloudFront 60s origin read timeout forces EventSource reconnects on long agent turns. Direct A record + Caddy + Let's Encrypt avoids the reconnect dance. |
| D4 | **EC2 `t4g.small`** for SSE host | $12/mo flat vs Lambda GB-seconds compounding on 60-90s streaming turns. At ~10k MAU Lambda would cross into hundreds of $/mo. |
| D5 | **Public RDS + Lambda out of VPC** (reverses 5a.1 §4.3) | Matches ShipRate pattern. Eliminates NAT cost. Trade-off: SG must open `5432/tcp` to `0.0.0.0/0` (Lambda has no stable egress ranges); access control reduces to `force_ssl=1` + strong app-user password + per-DB user isolation. See §3.1 for full rationale. |
| D6 | **Drop fck-nat** (reverses 5a.1 D11) | Follows from D5. Saves ~$3/mo and removes a single-point-of-failure. |
| D7 | **CDK-declared Migration Lambda** (1024 MB, `MIGRATION_MODE=true`, same image as API) | Mirrors ShipRate. GH Actions invokes it; CDK keeps it declared so redeploys get latest code via image update. |
| D8 | **CDK-time secret injection** via `secretValueFromJson().unsafeUnwrap()` | Reverses my initial runtime-fetch proposal. Matches ShipRate, keeps handler code simple. Values appear in Lambda config + stack JSON — acceptable for dev; revisit before prod. |
| D9 | **Single `HireLoop-App-dev` stack** (no Compute/Edge split) | YAGNI. Split later when 5a.4 grows Edge concerns. |
| D10 | **6-job GH Actions workflow** — `determine-env → build-image → migrate → deploy-sse → deploy-api → smoke-test` | OIDC auth, matrix strategy scoped to `["dev"]`, 1-line change for prod. |
| D11 | **Sequential deploy**: SSE before API | Fragile path (SSH + docker pull) fails early. Prevents partial deploys and matches rollback mental model. |
| D12 | **Smoke test: shallow probes + `/auth/me` DB round-trip** | Catches 80% of real deployment failures (bad secrets, SG, migrations out of sync) in ~30s, without Anthropic spend. |
| D13 | **Manual-only rollback** via `workflow_dispatch` with `rollback_to_sha` input | Dev cost of surprise auto-rollback > cost of 20min broken deploy. Prior green SHA tracked at SSM `/hireloop/dev/last-green-sha`. |
| D14 | **Alembic round-trip CI check** on every PR | Fresh Postgres → `upgrade head` → `downgrade -1` → `upgrade head`. Enforces expand-contract rule before merge. |

---

## 2. Architecture Overview

### Topology (dev)

```
                       Route53: hireloop.xyz (zone, 5a.1)
                             |
             +---------------+---------------+
             |                               |
  api.dev.hireloop.xyz              sse.dev.hireloop.xyz
  (A ALIAS → CloudFront)            (A → EC2 EIP)
             |                               |
        CloudFront                      EC2 t4g.small
   (CACHING_DISABLED,                (Caddy + Let's Encrypt,
    ALL_VIEWER_EXCEPT_               uvicorn in docker,
     HOST_HEADER forward)             public subnet, EIP)
             |                               |
     Lambda Function URL                     |
     (BUFFERED, 900s timeout)                |
             |                               |
             +--------------+----------------+
                            |
                    RDS Postgres 16
                  (PUBLIC subnet, SSL-only,
                    SG: 5432 from 0.0.0.0/0
                    + SG-EC2-Backend)
```

### What 5a.2 provisions (new `HireLoop-App-dev` stack)

- **ECR repositories** — `hireloop-backend` (lifecycle: retain last 20 images; covers Lambda + EC2 backend tags) and `hireloop-caddy` (lifecycle: retain last 3 images; custom Caddy build rarely changes). Two repos — not one with tag prefixes — because ECR lifecycle rules count all tags in a repo and a `maxImageCount` of 20 would eventually evict the only Caddy image once backend deploys exceed 20. Separate repos is simpler than tag-prefix filters.
- **Lambda: `hireloop-api-dev`** — container image (Lambda base `public.ecr.aws/lambda/python:3.12`, ARM64), FURL BUFFERED, 900s timeout, 1024 MB, no VPC, secrets injected via env vars, `reservedConcurrentExecutions: 10` (caps burst at 10 concurrent requests; intentional cost guardrail for dev, raise for prod)
- **Lambda: `hireloop-migration-dev`** — same image as API (different CMD), 1024 MB, no VPC, `MIGRATION_MODE=true`, 900s timeout
- **EC2 `t4g.small` instance** — Amazon Linux 2023 ARM, EIP, in public subnet, SG-EC2-Backend, cloud-init installs Caddy + Docker + Compose. Runs a **separate image** (regular `python:3.12-slim` + uvicorn, ARM64, tagged `hireloop-backend:<sha>-ec2` in the same ECR repo). IAM instance profile grants SSM + ECR pull + Secrets Manager read.
- **CloudFront distribution** — single origin (Lambda FURL), `CACHING_DISABLED`, `ALL_VIEWER_EXCEPT_HOST_HEADER` origin request policy, alternate domain `api.dev.hireloop.xyz`, ACM cert from 5a.1 SSM
- **Route53 records** — `api.dev` → CloudFront alias, `sse.dev` → EC2 EIP A-record (replaces the 5a.1 placeholder `127.0.0.1`)
- **SSM parameter** `/hireloop/dev/last-green-sha` — updated on smoke-test success
- **IAM role `hireloop-github-oidc`** — trusts GitHub OIDC, scoped to this repo + dev environment, grants ECR push, Lambda update, SSM run-command, SSM param read/write

### What 5a.2 does NOT provision

- pdf-render compute — 5a.3
- Inngest Cloud wiring (staying on current dev Inngest account) — 5a.3
- Frontend CDN (user-portal + admin-ui) — 5a.4
- Sandbox or prod environments — separate sub-phase (D1)
- Backup vaults, WAF, observability stack, centralized logging — Phase 5b
- ASG for SSE HA — prod concern, single EC2 accepted for dev

---

## 3. Amendments to 5a.1

5a.2 changes, not adds. Must be called out explicitly because deployed 5a.1 resources will need CFN updates.

### 3.1 NetworkStack amendments

- **Drop `PrivateEgress` subnet tier** — Lambda now runs out-of-VPC.
- **Drop `Isolated` subnet tier** — RDS moves to public.
- **Drop SGs**: `SG-Lambda`, `SG-FckNat`, `SG-DbBootstrap`.
- **Keep**: VPC, 2 public `/24` subnets, `SG-EC2-Backend`, `SG-RDS`, S3 gateway endpoint.
- **Amend `SG-RDS` ingress**: `5432 from SG-EC2-Backend` (SSE host) + `5432 from 0.0.0.0/0` (Lambda out-of-VPC, no stable egress IPs).

**On public-RDS access control (D5 trade-off):** SG opens `5432/tcp` to the internet because Lambda out-of-VPC has no stable egress ranges to pin. Access control reduces to (1) `rds.force_ssl=1` (TLS required), (2) `hireloop_dev_app` 32-char random password stored in Secrets Manager, (3) per-database user isolation — `dev_app` cannot `CONNECT` to `sandbox` or `prod` databases, (4) no master credential used by app code. Accepted risks: résumé PII exposure if app-user credentials leak, brute-force surface on `5432/tcp`. Before prod promotion, move RDS private and use IAM DB auth or attach Lambda to VPC. CloudTrail logging on the DB master secret is already on by default.

### 3.2 DataStack amendments

- **RDS `publiclyAccessible: true`** (was `false`).
- **RDS `vpcSubnets: { subnetType: ec2.SubnetType.PUBLIC }`** (was `PRIVATE_ISOLATED`).
- **Add parameter group** with `rds.force_ssl=1`.
- **Remove DbBootstrap custom resource** from isolated subnet path — it now runs out of VPC (no VPC config on the Lambda) and connects to the public RDS endpoint over TLS. Keep the custom resource itself — just drop the VPC config.
- **Keep**: assets bucket, master secret, per-env app user secret, SSM parameters.

### 3.3 ConfigStack amendments

- **Add SSM parameter** `/hireloop/dev/last-green-sha` (initial value `"bootstrap"`, written by CDK, updated by smoke-test job).
- **Add SSM parameter** `/hireloop/dev/ecr-repo-uri` — written by App stack after ECR creation (value: `<acct>.dkr.ecr.us-east-1.amazonaws.com/hireloop-backend`). Read by GH Actions for image tagging.
- **Add SSM parameter** `/hireloop/dev/current-image-tag` — bootstrap-only. Written manually on first deploy (§11 step 4). **NOT read at steady state**: GH Actions updates Lambda code directly via `aws lambda update-function-code`, bypassing CDK. See §4.3 for the full ownership model.

### 3.4 DNS stack — no changes

Wildcard cert + hosted zone already cover both `api.dev.hireloop.xyz` and `sse.dev.hireloop.xyz`.

---

## 4. New Stack: `HireLoop-App-dev`

Single stack, consumes 5a.1 outputs via SSM or stack-reference imports. Deployed after all 5a.1 stacks.

### 4.1 Props shape

```typescript
interface AppStackProps extends cdk.StackProps {
  readonly environment: 'dev';              // D1 — prod added in later sub-phase
  readonly hostedZoneId: string;            // SSM: /hireloop/shared/dns/hosted-zone-id
  readonly certificateArn: string;          // SSM: /hireloop/shared/dns/certificate-arn
  readonly vpcId: string;                   // SSM: /hireloop/shared/network/vpc-id
  readonly publicSubnetIds: string[];       // SSM: /hireloop/shared/network/public-subnet-ids
  readonly sgEc2BackendId: string;          // SSM: /hireloop/shared/network/sg-ec2-backend-id
  readonly dbEndpoint: string;              // SSM: /hireloop/dev/db/endpoint
  readonly dbAppSecretArn: string;          // SSM: /hireloop/dev/db/app-secret-arn
  readonly assetsBucketName: string;        // SSM: /hireloop/dev/s3/assets-bucket-name
  readonly userPoolId: string;              // SSM: /hireloop/dev/cognito/user-pool-id
  readonly userPoolClientId: string;        // SSM: /hireloop/dev/cognito/user-pool-client-id
}
```

All cross-stack values come via SSM `StringParameter.valueForStringParameter()` — no hard CFN exports to avoid coupling.

### 4.2 Resources

**ECR repositories**

```typescript
const backendRepo = new ecr.Repository(this, 'BackendRepo', {
  repositoryName: 'hireloop-backend',
  lifecycleRules: [{ maxImageCount: 20 }],
  imageScanOnPush: true,
});

const caddyRepo = new ecr.Repository(this, 'CaddyRepo', {
  repositoryName: 'hireloop-caddy',
  lifecycleRules: [{ maxImageCount: 3 }],
  imageScanOnPush: true,
});
```

**Lambda: API**

```typescript
const apiFn = new lambda.DockerImageFunction(this, 'ApiFn', {
  functionName: `hireloop-api-${environment}`,
  code: lambda.DockerImageCode.fromEcr(ecr, {
    tagOrDigest: ssm.StringParameter.valueForStringParameter(
      this, `/hireloop/${environment}/current-image-tag`,
    ),
  }),
  memorySize: 1024,
  timeout: cdk.Duration.minutes(15),
  architecture: lambda.Architecture.ARM_64,
  reservedConcurrentExecutions: 10,
  environment: buildApiEnv(environment, props),   // see §5
});
const furl = apiFn.addFunctionUrl({
  authType: lambda.FunctionUrlAuthType.NONE,
  invokeMode: lambda.InvokeMode.BUFFERED,
});
```

**Lambda: Migration**

```typescript
const migrationFn = new lambda.DockerImageFunction(this, 'MigrationFn', {
  functionName: `hireloop-migration-${environment}`,
  code: lambda.DockerImageCode.fromEcr(ecr, { tagOrDigest: /* same */ }),
  memorySize: 1024,
  timeout: cdk.Duration.minutes(15),
  architecture: lambda.Architecture.ARM_64,
  reservedConcurrentExecutions: 1,
  environment: { ...buildMigrationEnv(environment, props), MIGRATION_MODE: 'true' },
  cmd: ['hireloop.aws_lambda_adapter.migration_handler'],
});
```

**Lambda container lifecycle:** the image uses `public.ecr.aws/lambda/python:3.12` as base; `awslambdaric` is the ENTRYPOINT. CMD selects the handler — `handler` for API, `migration_handler` for migrations. Both Lambdas share the same image; only CMD differs. This matches the Lambda runtime contract (long-lived process, per-invocation handler call), so no `entrypoint.sh` rewrite is needed for Lambda.

`migration_handler(event, context)` shells out: `subprocess.run(["alembic", "upgrade", "head"], capture_output=True, text=True)`, then `alembic current` to capture head. **Always returns a JSON dict, never raises.** Shape: `{"status": "ok" | "failed", "head": "<rev>" | null, "stdout": "...", "stderr": "...", "returncode": <int>}`. The GH Actions `migrate` job parses `status` — treats `ok` as success, anything else as failure. No reliance on Lambda `FunctionError` semantics (which are awkward to detect from `aws lambda invoke` exit code).

**EC2 entrypoint (non-Lambda)** — `backend/scripts/entrypoint.sh` runs `alembic upgrade head` then `exec uvicorn hireloop.main:app --host 0.0.0.0 --port 8000`.

**On double-upgrade:** the Migration Lambda is the authoritative migration path (invoked by CI before SSE/API deploy). EC2 `entrypoint.sh` also runs `alembic upgrade head` on every container start as a defense-in-depth safety net — this matters when the SSE host is restarted out of band (AWS instance reboot, manual `docker compose restart`) without a fresh CI run. Alembic `upgrade head` is idempotent: if the DB is already at head, it's a fast no-op (single query against `alembic_version`). Double-run is always safe.

**EC2 SSE host**

```typescript
const sseInstance = new ec2.Instance(this, 'SseInstance', {
  vpc,
  vpcSubnets: { subnets: [publicSubnets[0]] },  // single AZ is fine for dev
  securityGroup: sgEc2Backend,
  instanceType: ec2.InstanceType.of(ec2.InstanceClass.BURSTABLE4_GRAVITON, ec2.InstanceSize.SMALL),
  machineImage: ec2.MachineImage.latestAmazonLinux2023({ cpuType: ec2.AmazonLinuxCpuType.ARM_64 }),
  userData: ec2.UserData.forLinux(),   // see below
  ssmSessionPermissions: true,
});
const eip = new ec2.CfnEIP(this, 'SseEip');
new ec2.CfnEIPAssociation(this, 'SseEipAssoc', {
  instanceId: sseInstance.instanceId,
  eip: eip.ref,
});

// IAM grants
ecr.grantPull(sseInstance.role);
apiSecretsList.forEach(s => s.grantRead(sseInstance.role));
sseInstance.role.addManagedPolicy(
  iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonSSMManagedInstanceCore'),
);
```

**User-data** (cloud-init):
1. Install Docker + Docker Compose plugin via `dnf`.
2. Install SSM agent (pre-installed on Amazon Linux 2023, verify running).
3. Write `/etc/hireloop/docker-compose.yml` and `/etc/hireloop/Caddyfile` from templates.
4. `docker compose up -d` to bring up `backend` + `caddy` + `redis` containers.

**Everything on the SSE host runs in containers — no native Caddy install.** The docker-compose services:

| Service | Image | Role |
|---|---|---|
| `backend` | `<ecr>/hireloop-backend:<sha>-ec2` | uvicorn serving FastAPI on `:8000` |
| `caddy` | `<ecr>/hireloop-caddy:2-route53` | TLS termination on `:443`, reverse-proxy to `backend:8000` |
| `redis` | `redis:7-alpine` | Rate-limit counters + SSE event buffer (see §5 REDIS_URL note) |

`Caddyfile`:

```caddy
sse.dev.hireloop.xyz {
  reverse_proxy backend:8000 {
    flush_interval -1
    transport http { read_timeout 900s }
  }
  tls {
    dns route53
  }
}
```

**Caddy + Route53 DNS-01:** the stock `caddy:2` image doesn't bundle DNS providers. We build a one-time custom image using [Caddy's xcaddy-based build](https://caddyserver.com/docs/build#xcaddy) with the `github.com/caddy-dns/route53` module, push it to ECR as `hireloop-caddy:2-route53`, and reference it from `docker-compose.yml`. Rebuild only when Caddy version changes. IAM: EC2 instance profile grants `route53:ChangeResourceRecordSets` + `route53:GetChange` on the `hireloop.xyz` hosted zone; Caddy picks up credentials via IMDSv2.

**CloudFront distribution**

```typescript
const apiDist = new cloudfront.Distribution(this, 'ApiDist', {
  defaultBehavior: {
    origin: new origins.FunctionUrlOrigin(furl),
    cachePolicy: cloudfront.CachePolicy.CACHING_DISABLED,
    originRequestPolicy: cloudfront.OriginRequestPolicy.ALL_VIEWER_EXCEPT_HOST_HEADER,
    viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
    allowedMethods: cloudfront.AllowedMethods.ALLOW_ALL,
  },
  domainNames: [`api.${environment}.hireloop.xyz`],
  certificate: acm.Certificate.fromCertificateArn(this, 'Cert', certificateArn),
  minimumProtocolVersion: cloudfront.SecurityPolicyProtocol.TLS_V1_2_2021,
});
```

**Route53 records**

```typescript
new route53.ARecord(this, 'ApiAlias', {
  zone,
  recordName: `api.${environment}`,
  target: route53.RecordTarget.fromAlias(new targets.CloudFrontTarget(apiDist)),
});
new route53.ARecord(this, 'SseAlias', {
  zone,
  recordName: `sse.${environment}`,
  target: route53.RecordTarget.fromIpAddresses(eip.ref),
});
```

**Last-green SHA param** (D13)

```typescript
new ssm.StringParameter(this, 'LastGreenSha', {
  parameterName: `/hireloop/${environment}/last-green-sha`,
  stringValue: 'bootstrap',      // CI overwrites on first smoke success
});
```

### 4.3 Image-tag ownership (who writes what, when)

| Param / resource | Owner (bootstrap) | Owner (steady state) | Read by |
|---|---|---|---|
| ECR repo `hireloop-backend` | CDK (creates) | CDK (immutable) | GH Actions push, CDK imports |
| `/hireloop/dev/ecr-repo-uri` | CDK (writes on App stack first apply) | CDK (immutable) | GH Actions (tag construction) |
| `/hireloop/dev/current-image-tag` | Operator (manual write before first `cdk deploy`) | **Unused** — see note | CDK synth → Lambda initial image |
| Lambda `hireloop-api-dev` image | CDK (initial deploy) | GH Actions (`aws lambda update-function-code --image-uri <ecr>@<digest>`) | — |
| Lambda `hireloop-migration-dev` image | CDK (initial deploy) | GH Actions | — |
| EC2 container image | n/a (pulled on boot + on SSM run-command) | GH Actions (`docker pull` + restart) | EC2 at runtime |
| `/hireloop/dev/last-green-sha` | CDK (seeds `"bootstrap"`) | GH Actions (writes after smoke-test) | Operator (rollback reference) |

**Why `current-image-tag` is bootstrap-only:** CDK needs *some* image to stand up the Lambda on first apply. After that, `cdk deploy` would try to reset the Lambda to whatever `current-image-tag` points at — so we never run `cdk deploy HireLoop-App-dev` as part of the code-deploy workflow. Only run it for infra changes (new IAM, CloudFront config, etc.), and when doing so, first write the latest image tag to the param so `cdk deploy` is a no-op on Lambda code.

**Alternative considered:** have GH Actions write to `current-image-tag` on every deploy, keep CDK and reality in sync, allow `cdk deploy` any time. Rejected because it makes the `aws lambda update-function-code` call optional (CDK could do it on next deploy), which splits "who deploys code" across two tools. The chosen model is simpler: **CDK owns infra, GH Actions owns code.**

---

## 5. Secrets & Config (CDK-time injection)

Per D8, secrets are read from Secrets Manager at **synth time** and injected as plain env vars into the Lambda. Backend code reads them via `os.environ` — no runtime AWS SDK calls to Secrets Manager.

**CDK note:** `buildApiEnv` below must run within a `Construct` scope (either a method on the Stack class or a function taking `scope: Construct` as first arg). The sketch uses `scope` explicitly to make that requirement obvious.

```typescript
function buildApiEnv(scope: Construct, env: string, props: AppStackProps): Record<string, string> {
  const readJson = (path: string, key: string) =>
    secretsmanager.Secret.fromSecretNameV2(scope, `S-${path}`, path)
      .secretValueFromJson(key).unsafeUnwrap();

  return {
    ENVIRONMENT: env,
    DATABASE_URL: `postgresql+asyncpg://hireloop_${env}_app:${readJson(`hireloop/${env}/db-app-password`, 'password')}@${props.dbEndpoint}:5432/hireloop_${env}?ssl=require`,
    REDIS_URL: '',  // Phase 5a.3 adds ElastiCache or drops redis dep
    ANTHROPIC_API_KEY: readJson(`hireloop/${env}/anthropic-api-key`, 'key'),
    GOOGLE_API_KEY: readJson(`hireloop/${env}/google-api-key`, 'key'),
    STRIPE_SECRET_KEY: readJson(`hireloop/${env}/stripe-secret-key`, 'key'),
    STRIPE_WEBHOOK_SECRET: readJson(`hireloop/${env}/stripe-webhook-secret`, 'key'),
    PDF_RENDER_SHARED_SECRET: readJson(`hireloop/${env}/pdf-render-shared-secret`, 'key'),
    INNGEST_EVENT_KEY: readJson(`hireloop/${env}/inngest-event-key`, 'key'),
    INNGEST_SIGNING_KEY: readJson(`hireloop/${env}/inngest-signing-key`, 'key'),
    COGNITO_USER_POOL_ID: props.userPoolId,
    COGNITO_CLIENT_ID: props.userPoolClientId,
    COGNITO_REGION: cdk.Stack.of(scope).region,
    COGNITO_JWKS_URL: `https://cognito-idp.${cdk.Stack.of(scope).region}.amazonaws.com/${props.userPoolId}/.well-known/jwks.json`,
    S3_ASSETS_BUCKET: props.assetsBucketName,
    DISABLE_PAYWALL: 'false',
    PDF_RENDER_URL: '',   // 5a.3
  };
}
```

**Known trade-off:** secret values appear in Lambda console env vars and in `cdk.out/*.template.json`. Acceptable for dev; prod will move to runtime fetch before promotion. Flagged in §8.

**REDIS_URL note:** current backend uses Redis for rate limiting and SSE event storage. Phase 5a.2 ships with `REDIS_URL=""` **for the Lambda only**; the EC2 SSE host runs Redis locally in docker-compose and its container's `REDIS_URL=redis://redis:6379/0` is set by the `/etc/hireloop/env` file. Lambda (API) code must handle absent Redis gracefully: rate limiter falls back to an in-memory per-warm-container limiter (documented as "not shared across Lambda invocations"). **Any code path that requires Redis for correctness must run on EC2, not Lambda** — at 5a.2 this is only the SSE event storage (already on EC2 by design). Rate limiting is the only shared-state feature affected, and dev traffic volume makes per-container limiting acceptable. If this surfaces as a blocker, 5a.3 adds ElastiCache `t4g.micro` and both Lambda + EC2 point at it.

EC2 SSE host env comes from a separate `/etc/hireloop/env` file populated at user-data time by a small helper script that reads Secrets Manager at boot. Same variable names as Lambda. Rationale: EC2 has a stable identity (instance profile), runtime fetch is cheap and keeps secrets out of AMI/cloud-init logs.

---

## 6. GitHub Actions Deploy Workflow

New file: `.github/workflows/deploy.yml`. OIDC auth, matrix strategy.

### 6.1 Trigger

```yaml
on:
  push: { branches: [main] }
  workflow_dispatch:
    inputs:
      environment:
        type: choice
        options: [dev]              # D1 — prod added in later sub-phase
        default: dev
      rollback_to_sha:
        description: 'Commit SHA to roll back to. Leave empty for normal deploy.'
        required: false
        type: string
```

### 6.2 Concurrency

```yaml
concurrency:
  group: deploy-${{ github.event.inputs.environment || 'dev' }}
  cancel-in-progress: false
```

### 6.3 Jobs (sequential per D11)

| # | Job | Needs | Purpose |
|---|---|---|---|
| 1 | `determine-environment` | — | Resolves env from `inputs.environment` or defaults `dev`. Outputs `env`, `deploy_sha` (either `github.sha` or `inputs.rollback_to_sha`). |
| 2 | `build-image` | 1 | `runs-on: ubuntu-24.04-arm` (native ARM64, no QEMU). Builds **two** images from the same Dockerfile via different target stages: `hireloop-backend:<sha>-lambda` (Lambda base) and `hireloop-backend:<sha>-ec2` (slim base). Pushes both to ECR. Skips if rollback (images already exist). Outputs `lambda_digest`, `ec2_digest`. |
| 3 | `migrate` | 2 | Updates `hireloop-migration-dev` Lambda to `<sha>-lambda` image. Waits `aws lambda wait function-updated`. Invokes. Parses response JSON, fails if `status != "ok"`. 900s timeout. |
| 4 | `deploy-sse` | 3 | SSM run-command on EC2 instance: `docker pull <ecr-uri>@<ec2_digest> && docker compose up -d`. Polls `aws ssm get-command-invocation` until status `Success`; fails if any other state. Uses digest, not tag, for reproducibility. |
| 5 | `deploy-api` | 4 | Updates `hireloop-api-dev` Lambda to `<sha>-lambda` image (by digest). Waits `function-updated`. No invocation needed. |
| 6 | `smoke-test` | 5 | Runs the 3-step smoke (§6.4). On success, writes `deploy_sha` to SSM `/hireloop/dev/last-green-sha`. |

### 6.4 Smoke test (D12)

```bash
set -euo pipefail
API=https://api.dev.hireloop.xyz
SSE=https://sse.dev.hireloop.xyz

curl -fsS --max-time 10 "$API/healthz"
curl -fsS --max-time 10 "$SSE/healthz"
curl -fsS --max-time 10 -H "Authorization: Bearer $DEV_SMOKE_TOKEN" "$API/auth/me" \
  | jq -e '.data.email == "smoke@hireloop.internal"'
```

**Response contract:** `/auth/me` returns `{"data": {"cognito_sub": "...", "email": "...", "name": "..."}, "meta": null}` per `backend/src/hireloop/schemas/user.py::UserResponse` wrapped in `Envelope[T]`. The smoke assertion must be updated in lockstep if the schema changes; treat the test as part of the API contract.

`DEV_SMOKE_TOKEN` stored in GH Actions org secret `DEV_SMOKE_TOKEN`. Token is a long-lived Cognito JWT for fixed test user `smoke@hireloop.internal` (created manually once via AWS console; documented in runbook).

**On failure:** workflow marks job red, leaves deploy in place (D13). No auto-rollback.

### 6.5 Rollback path

Operator triggers `workflow_dispatch` with `rollback_to_sha=<prior-sha>`. Workflow:
- `build-image` job sees rollback input, skips build.
- `migrate` runs normally — migrations are backward-compatible (D14 guarantees this), so running an older `alembic upgrade head` is a no-op if DB is already at or ahead of that revision's head.
- `deploy-sse` pulls old digest.
- `deploy-api` updates Lambda to old image.
- `smoke-test` validates.

**Edge case:** if rollback target SHA's image was pruned from ECR (lifecycle rule = 20 images), workflow fails at `deploy-sse`. Mitigation: keep 20 images covering ~1-2 weeks of commits; manual `docker push` to rehydrate if needed.

**Caveat — DB downgrade is out of scope.** D14 forces expand-contract migrations at PR time, so rolling code back is almost always safe without a DB change. If a production incident ever requires an actual `alembic downgrade` (e.g., a dropped column whose data must be restored), this workflow does not do it. That path is an operational runbook that pairs manual `alembic downgrade` with a point-in-time-restore of the RDS snapshot, written separately when prod lands.

### 6.6 Required GH Actions org secrets

| Secret | Purpose |
|---|---|
| `AWS_ACCOUNT_ID` | For OIDC role ARN construction |
| `DEV_SMOKE_TOKEN` | Long-lived Cognito JWT for smoke test user |

(No AWS keys — OIDC role assumed via `aws-actions/configure-aws-credentials@v4`.)

### 6.7 Alembic round-trip CI check (D14)

Separate workflow file: `.github/workflows/migration-check.yml`. Runs on every PR targeting `main`. Steps:

1. Spin Postgres 16 service container.
2. `uv run alembic upgrade head`
3. `uv run alembic downgrade -1`
4. `uv run alembic upgrade head`
5. Exit 0.

Fails PR if any step exits non-zero. Catches non-reversible migrations (a raw `DROP COLUMN` without a `downgrade()` body).

---

## 7. Cost Projection (dev)

All figures **approximate** — list prices as of 2026-04, us-east-1, solo dev traffic patterns. Real monthly bills will drift based on data transfer, CloudFront edge cache misses, and request volume. Do not budget to the dollar from this table.

| Line item | ~$/mo |
|---|---|
| RDS t4g.small (public subnet, `force_ssl=1`) | $12 |
| EC2 t4g.small (SSE, public subnet, EIP) | $12 |
| Lambda (API container, no VPC) | $1 |
| Lambda (Migration, no VPC) | ~$0 |
| CloudFront (free tier covers 1M req/mo for dev) | ~$0 |
| Secrets Manager (~7 secrets × $0.40/mo) | $2.80 |
| Route53 hosted zone + queries | $0.50 |
| ECR storage (~20 images × ~500MB × $0.10/GB/mo) | $1 |
| **Total** | **~$29/mo** |

Saves ~$22/mo vs the original 5a.1 ALB+fck-nat topology (~$51/mo).

---

## 8. Divergences from Parent Design Spec

Called out so a reader of `docs/superpowers/specs/2026-04-10-careeragent-design.md` isn't confused:

1. **No ALB.** CloudFront replaces for API; direct A-record for SSE. Parent spec committed to a single `api.hireloop.xyz` origin via ALB path-based routing.
2. **No NAT.** Public RDS + Lambda out of VPC. Parent spec implied private RDS.
3. **No fck-nat.** Reverses 5a.1 D11.
4. **RDS publicly accessible.** Reverses 5a.1 §4.3.
5. **Dev-only explicit.** Prod scoped to a later sub-phase.
6. **Single `HireLoop-App-dev` stack.** Parent spec implied per-concern stacks (Compute, Edge).
7. **Split topology: two hostnames.** `api.dev.*` via CloudFront, `sse.dev.*` direct to EC2. Parent spec committed to single `api.*` origin.

Each divergence reduces cost or scope for dev and is reversible when prod promotion happens.

---

## 9. Known Open Concerns (flagged, accepted for 5a.2)

| Concern | Why accepted |
|---|---|
| Résumé PII in public RDS | TLS + strong password + per-env app user + CloudTrail audit on master secret. Acceptable for dev; prod moves RDS private with IAM DB auth or VPC-attached Lambda. |
| Single-EC2 SSE = SPOF | Dev only. Prod adds ASG of 2 behind NLB or moves SSE to ECS Fargate. |
| CDK-time secret injection leaks secrets to Lambda console + CFN templates | Documented in D8. Dev threat model: only repo collaborators + AWS account owners see these. Prod moves to runtime fetch. |
| REDIS_URL empty means Lambda rate limiter is per-warm-container, not shared | In-memory fallback is correct for low dev traffic. 5a.3 adds ElastiCache if needed. |
| Caddy + Let's Encrypt adds dependency on LE's rate limits | DNS-01 via Route53 is far more reliable than HTTP-01 for an EC2 behind a dynamic EIP. |
| Lambda FURL lacks WAF/rate-limit | Acceptable for dev (low traffic); prod adds CloudFront WAF or moves to API Gateway with usage plans. |
| No observability stack | Lambda + CloudWatch default logs only. Phase 5b adds structured logging, metrics dashboard, alerting. |

---

## 10. Testing

### 10.1 Local / pre-deploy

- `cd infrastructure/cdk && pnpm run synth` — must succeed with no errors or warnings.
- `cd infrastructure/cdk && pnpm run typecheck` — `tsc --noEmit` green.
- `cd backend && uv run alembic upgrade head && uv run alembic downgrade -1 && uv run alembic upgrade head` — local Alembic round-trip before push.
- Backend test suite — 165 tests must stay green. No code paths in the backend should change for 5a.2 beyond the new `aws_lambda_adapter` module, the EC2 `entrypoint.sh`, and the in-memory rate-limit fallback.

### 10.2 Post-deploy smoke (definition of done)

- Smoke-test job passes (see §6.4).
- Manual: open `https://api.dev.hireloop.xyz/docs` — FastAPI swagger renders.
- Manual: `aws logs tail /aws/lambda/hireloop-api-dev --since 5m` shows no errors.
- Manual: SSM Session Manager into SSE host. `docker compose -f /etc/hireloop/docker-compose.yml ps` shows `backend`, `caddy`, `redis` all `running`. `docker compose -f /etc/hireloop/docker-compose.yml logs caddy --tail=50` shows `certificate obtained successfully` for `sse.dev.hireloop.xyz`. Caddy runs in a container, **not** as an AL2023 systemd unit — `journalctl -u caddy` won't work.
- Manual: one authenticated `curl https://sse.dev.hireloop.xyz/conversations/<id>/stream` with a real Cognito token and confirm SSE events flow.

---

## 11. Rollout Checklist

1. Merge this spec + plan to `main`.
2. Populate 5a.1 secrets (`./scripts/populate-dev-secrets.sh`) — skip anything already present.
3. Deploy 5a.1 amendments (Network + Data) if not already deployed with amendments: `cdk deploy HireLoop-Network HireLoop-Data`.
4. **Deploy App stack shell first** (creates both ECR repos): `cdk deploy HireLoop-App-dev`. This will fail at the Lambda-image step because ECR has no images yet — that's expected.
5. **Bootstrap Caddy image (one-time, manual):** `cd infrastructure/caddy && ./build-and-push.sh`. Script uses `xcaddy` to build a Caddy 2 binary with the `caddy-dns/route53` module, wraps it in a minimal Dockerfile, tags as `hireloop-caddy:2-route53`, pushes to the `hireloop-caddy` ECR repo. Rerun only when Caddy version bumps.
6. **Bootstrap backend image (one-time, manual):** `docker buildx build --platform linux/arm64 --target lambda -t hireloop-backend:bootstrap-lambda ./backend && docker push ...` plus the `ec2` target. Write the resulting tag to `/hireloop/dev/current-image-tag` param.
7. **Re-run `cdk deploy HireLoop-App-dev`** — now succeeds with real images.
8. Create fixed Cognito smoke test user via AWS console; mint long-lived JWT; store as `DEV_SMOKE_TOKEN` org secret.
9. Trigger GH Actions workflow manually (`workflow_dispatch` on `main`) to validate end-to-end.
10. On green smoke: validate DNS resolution (`dig api.dev.hireloop.xyz`), Swagger load, single SSE turn. Mark DoD met.

---

## 12. What Changes in the Backend Code

Minimal, contained in a single PR:

- `backend/src/hireloop/aws_lambda_adapter.py` — new module. Two exports: `handler` (Mangum-wrapped FastAPI app for API Lambda) and `migration_handler` (subprocess shell-out to Alembic for Migration Lambda). ~40 lines.
- `backend/Dockerfile` — multi-stage: a `lambda` target built `FROM public.ecr.aws/lambda/python:3.12` (ARM64, CMD defaults to `hireloop.aws_lambda_adapter.handler`), and an `ec2` target built `FROM python:3.12-slim` (ARM64, ENTRYPOINT `/app/scripts/entrypoint.sh`). Shared `builder` stage installs deps once. GH Actions `build-image` job builds both targets.
- `backend/scripts/entrypoint.sh` — new file for EC2 only. `alembic upgrade head && exec uvicorn hireloop.main:app --host 0.0.0.0 --port 8000`. ~5 lines.
- `backend/src/hireloop/core/rate_limit.py` — fallback to in-memory limiter when `REDIS_URL` is empty. ~15 lines. Document that this is per-warm-container on Lambda.
- `backend/pyproject.toml` — add `mangum>=0.17` to dependencies.
- `infrastructure/caddy/` — new directory. `Dockerfile` uses `caddy:2-builder` xcaddy base, adds `github.com/caddy-dns/route53`, produces a minimal Alpine runtime image. `build-and-push.sh` tags + pushes to `hireloop-caddy:2-route53` ECR. Built once, rebuilt only on Caddy version bumps.

No changes to business logic, tests, or API contracts. All 165 backend tests must stay green.
