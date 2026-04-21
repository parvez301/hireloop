import * as fs from "fs";
import * as path from "path";
import * as cdk from "aws-cdk-lib";
import * as acm from "aws-cdk-lib/aws-certificatemanager";
import * as cloudfront from "aws-cdk-lib/aws-cloudfront";
import * as origins from "aws-cdk-lib/aws-cloudfront-origins";
import * as ec2 from "aws-cdk-lib/aws-ec2";
import * as ecr from "aws-cdk-lib/aws-ecr";
import * as iam from "aws-cdk-lib/aws-iam";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as route53 from "aws-cdk-lib/aws-route53";
import * as targets from "aws-cdk-lib/aws-route53-targets";
import * as secretsmanager from "aws-cdk-lib/aws-secretsmanager";
import * as ssm from "aws-cdk-lib/aws-ssm";
import { Construct } from "constructs";

export interface AppStackProps extends cdk.StackProps {
  readonly environment: "dev";
}

interface LambdaEnvContext {
  readonly dbEndpoint: string;
  readonly assetsBucketName: string;
  readonly userPoolId: string;
  readonly userPoolClientId: string;
}

function buildApiEnv(scope: Construct, env: string, props: LambdaEnvContext): Record<string, string> {
  // Use SecretValue.secretsManager (name-based CFN dynamic ref) rather than
  // Secret.fromSecretNameV2().secretValueFromJson(), which generates an ARN
  // without the random suffix and fails at deploy time with "secret not found".
  const readJson = (path: string, key: string) =>
    cdk.SecretValue.secretsManager(path, { jsonField: key }).unsafeUnwrap();

  const region = cdk.Stack.of(scope).region;
  return {
    ENVIRONMENT: env,
    DATABASE_URL: `postgresql+asyncpg://hireloop_${env}_app:${readJson(`hireloop/${env}/db-app-password`, "password")}@${props.dbEndpoint}:5432/hireloop_${env}?ssl=require`,
    REDIS_URL: "",
    ANTHROPIC_API_KEY: readJson(`hireloop/${env}/anthropic-api-key`, "key"),
    GOOGLE_API_KEY: readJson(`hireloop/${env}/google-api-key`, "key"),
    STRIPE_SECRET_KEY: readJson(`hireloop/${env}/stripe-secret-key`, "key"),
    STRIPE_WEBHOOK_SECRET: readJson(`hireloop/${env}/stripe-webhook-secret`, "key"),
    INNGEST_EVENT_KEY: readJson(`hireloop/${env}/inngest-event-key`, "key"),
    INNGEST_SIGNING_KEY: readJson(`hireloop/${env}/inngest-signing-key`, "key"),
    COGNITO_USER_POOL_ID: props.userPoolId,
    COGNITO_CLIENT_ID: props.userPoolClientId,
    COGNITO_REGION: region,
    COGNITO_JWKS_URL: `https://cognito-idp.${region}.amazonaws.com/${props.userPoolId}/.well-known/jwks.json`,
    AWS_S3_BUCKET: props.assetsBucketName,
    DISABLE_PAYWALL: "false",
  };
}

export class AppStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: AppStackProps) {
    super(scope, id, props);

    const env = props.environment;

    const hostedZoneId = ssm.StringParameter.valueForStringParameter(
      this,
      "/hireloop/shared/dns/hosted-zone-id",
    );
    const certificateArn = ssm.StringParameter.valueForStringParameter(
      this,
      "/hireloop/shared/dns/certificate-arn",
    );
    const vpcId = ssm.StringParameter.valueForStringParameter(this, "/hireloop/shared/network/vpc-id");
    const publicSubnet0Id = ssm.StringParameter.valueForStringParameter(
      this,
      "/hireloop/shared/network/public-subnet-0-id",
    );
    const publicSubnet1Id = ssm.StringParameter.valueForStringParameter(
      this,
      "/hireloop/shared/network/public-subnet-1-id",
    );
    const sgEc2BackendId = ssm.StringParameter.valueForStringParameter(
      this,
      "/hireloop/shared/network/sg-ec2-backend-id",
    );
    const dbEndpoint = ssm.StringParameter.valueForStringParameter(this, `/hireloop/${env}/db/endpoint`);
    const assetsBucketName = ssm.StringParameter.valueForStringParameter(
      this,
      `/hireloop/${env}/s3/assets-bucket-name`,
    );
    const userPoolId = ssm.StringParameter.valueForStringParameter(
      this,
      `/hireloop/${env}/cognito/user-pool-id`,
    );
    const userPoolClientId = ssm.StringParameter.valueForStringParameter(
      this,
      `/hireloop/${env}/cognito/user-pool-client-id`,
    );

    const envProps: LambdaEnvContext = {
      dbEndpoint,
      assetsBucketName,
      userPoolId,
      userPoolClientId,
    };

    const tagParam = ssm.StringParameter.fromStringParameterName(
      this,
      "CurrentImageTagParam",
      `/hireloop/${env}/current-image-tag`,
    );

    // ECR repos are managed outside this stack (via infrastructure/scripts/
    // ensure-ecr-repos.sh) so that rollback of App-dev doesn't delete images
    // or leave orphan repos that block redeploy. Lifecycle + scan config are
    // set at repo-creation time by that script.
    const backendRepo = ecr.Repository.fromRepositoryName(this, "BackendRepo", "hireloop-backend");
    const caddyRepo = ecr.Repository.fromRepositoryName(this, "CaddyRepo", "hireloop-caddy");
    const llmBridgeRepo = ecr.Repository.fromRepositoryName(
      this,
      "LlmBridgeRepo",
      "hireloop-llm-bridge",
    );

    new ssm.StringParameter(this, "EcrBackendRepoUri", {
      parameterName: `/hireloop/${env}/ecr-repo-uri`,
      stringValue: backendRepo.repositoryUri,
    });

    const lambdaEnv = buildApiEnv(this, env, envProps);

    const apiFn = new lambda.DockerImageFunction(this, "ApiFn", {
      functionName: `hireloop-api-${env}`,
      code: lambda.DockerImageCode.fromEcr(backendRepo, {
        tagOrDigest: tagParam.stringValue,
      }),
      memorySize: 1024,
      timeout: cdk.Duration.minutes(15),
      architecture: lambda.Architecture.ARM_64,
      // reservedConcurrentExecutions omitted: fresh AWS accounts have a 10
      // concurrency cap and reserving any amount would leave 0 unreserved
      // (< 10 required). Restore the cap once account quota > 100 is granted.
      environment: lambdaEnv,
    });

    // Migrations connect as the RDS master user because the per-env app user
    // is provisioned CRUD-only (no schema DDL) by the Data stack's DbBootstrap.
    // Master-secret ARN is published by Data stack to SSM at synth-time.
    const masterSecretArn = ssm.StringParameter.valueForStringParameter(
      this,
      "/hireloop/shared/rds/master-secret-arn",
    );
    const masterSecret = secretsmanager.Secret.fromSecretCompleteArn(
      this,
      "RdsMasterSecret",
      masterSecretArn,
    );
    const masterUser = cdk.SecretValue.secretsManager(masterSecretArn, { jsonField: "username" }).unsafeUnwrap();
    const masterPassword = cdk.SecretValue.secretsManager(masterSecretArn, { jsonField: "password" }).unsafeUnwrap();
    const migrationLambdaEnv = {
      ...lambdaEnv,
      MIGRATION_MODE: "true",
      DATABASE_URL: `postgresql+asyncpg://${masterUser}:${masterPassword}@${dbEndpoint}:5432/hireloop_${env}?ssl=require`,
    };

    const migrationFn = new lambda.DockerImageFunction(this, "MigrationFn", {
      functionName: `hireloop-migration-${env}`,
      code: lambda.DockerImageCode.fromEcr(backendRepo, {
        tagOrDigest: tagParam.stringValue,
      }),
      memorySize: 1024,
      timeout: cdk.Duration.minutes(15),
      architecture: lambda.Architecture.ARM_64,
      environment: migrationLambdaEnv,
    });
    masterSecret.grantRead(migrationFn);
    const migrationCfn = migrationFn.node.defaultChild as lambda.CfnFunction;
    migrationCfn.addPropertyOverride("ImageConfig.Command", ["hireloop.aws_lambda_adapter.migration_handler"]);

    const furl = apiFn.addFunctionUrl({
      authType: lambda.FunctionUrlAuthType.NONE,
      invokeMode: lambda.InvokeMode.BUFFERED,
    });

    const hostedZone = route53.HostedZone.fromHostedZoneAttributes(this, "Zone", {
      hostedZoneId,
      zoneName: "hireloop.xyz",
    });

    const apiDist = new cloudfront.Distribution(this, "ApiDist", {
      defaultBehavior: {
        origin: new origins.FunctionUrlOrigin(furl),
        cachePolicy: cloudfront.CachePolicy.CACHING_DISABLED,
        originRequestPolicy: cloudfront.OriginRequestPolicy.ALL_VIEWER_EXCEPT_HOST_HEADER,
        viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
        allowedMethods: cloudfront.AllowedMethods.ALLOW_ALL,
      },
      domainNames: [`api.${env}.hireloop.xyz`],
      certificate: acm.Certificate.fromCertificateArn(this, "Cert", certificateArn),
      minimumProtocolVersion: cloudfront.SecurityPolicyProtocol.TLS_V1_2_2021,
    });

    new route53.ARecord(this, "ApiAlias", {
      zone: hostedZone,
      recordName: `api.${env}`,
      target: route53.RecordTarget.fromAlias(new targets.CloudFrontTarget(apiDist)),
    });

    const azs = cdk.Stack.of(this).availabilityZones;
    const vpc = ec2.Vpc.fromVpcAttributes(this, "ImportedVpc", {
      vpcId,
      availabilityZones: [azs[0], azs[1]],
      publicSubnetIds: [publicSubnet0Id, publicSubnet1Id],
    });

    const sgEc2 = ec2.SecurityGroup.fromSecurityGroupId(this, "SgEc2", sgEc2BackendId);

    const sseRole = new iam.Role(this, "SseInstanceRole", {
      assumedBy: new iam.ServicePrincipal("ec2.amazonaws.com"),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName("AmazonSSMManagedInstanceCore"),
      ],
    });
    backendRepo.grantPull(sseRole);
    caddyRepo.grantPull(sseRole);
    llmBridgeRepo.grantPull(sseRole);
    sseRole.addToPolicy(
      new iam.PolicyStatement({
        actions: ["ssm:GetParameter"],
        resources: [
          `arn:aws:ssm:${this.region}:${this.account}:parameter/hireloop/${env}/*`,
        ],
      }),
    );
    const secretArns = [
      `hireloop/${env}/db-app-password`,
      `hireloop/${env}/anthropic-api-key`,
      `hireloop/${env}/google-api-key`,
      `hireloop/${env}/stripe-secret-key`,
      `hireloop/${env}/stripe-webhook-secret`,
      `hireloop/${env}/inngest-event-key`,
      `hireloop/${env}/inngest-signing-key`,
    ];
    for (const name of secretArns) {
      secretsmanager.Secret.fromSecretNameV2(this, `Grant-${name.replace(/[^a-zA-Z0-9]/g, "")}`, name).grantRead(
        sseRole,
      );
    }

    const fetchEnvScript = fs.readFileSync(
      path.join(__dirname, "..", "..", "scripts", "hireloop-fetch-env.sh"),
      "utf8",
    );

    const userData = ec2.UserData.forLinux();
    userData.addCommands(
      "#!/bin/bash",
      "set -euxo pipefail",
      "dnf install -y docker",
      "mkdir -p /usr/local/lib/docker/cli-plugins",
      "curl -fsSL https://github.com/docker/compose/releases/download/v2.29.7/docker-compose-linux-aarch64 -o /usr/local/lib/docker/cli-plugins/docker-compose",
      "chmod +x /usr/local/lib/docker/cli-plugins/docker-compose",
      "systemctl enable --now docker",
      "usermod -aG docker ec2-user",
      `aws ecr get-login-password --region ${cdk.Stack.of(this).region} | docker login --username AWS --password-stdin ${cdk.Aws.ACCOUNT_ID}.dkr.ecr.${cdk.Stack.of(this).region}.amazonaws.com`,
      "mkdir -p /etc/hireloop /opt/hireloop",
      `cat >/etc/hireloop/docker-compose.yml <<'COMPOSE'
services:
  backend:
    image: \${BACKEND_IMAGE}
    env_file: /opt/hireloop/.env.secrets
    environment:
      # Route async LLM calls through the llm-bridge (claude-subscription CLI)
      # instead of paying per-token. Only reachable inside compose network.
      ANTHROPIC_BASE_URL: "http://llm-bridge:8019"
    ports:
      - "8000:8000"
    depends_on:
      - redis
      - llm-bridge
  llm-bridge:
    image: \${LLM_BRIDGE_IMAGE}
    environment:
      LLM_BRIDGE_PORT: "8019"
      LLM_BRIDGE_HOST: "0.0.0.0"
    volumes:
      # Persist Claude Code auth state across container restarts. First-time
      # setup: aws ssm start-session → sudo docker exec -it llm-bridge claude
      # setup-token, then paste the code returned by the browser flow.
      - /opt/hireloop/claude-auth:/root/.claude
    restart: unless-stopped
  caddy:
    image: \${CADDY_IMAGE}
    ports:
      - "443:443"
      - "80:80"
    volumes:
      - /etc/hireloop/Caddyfile:/etc/caddy/Caddyfile:ro
    depends_on:
      - backend
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
COMPOSE`,
      "mkdir -p /opt/hireloop/claude-auth",
      `cat >/etc/hireloop/Caddyfile <<'CADDY'
sse.${env}.hireloop.xyz {
  reverse_proxy backend:8000 {
    flush_interval -1
    transport http {
      read_timeout 900s
    }
  }
  tls {
    dns route53
  }
}
CADDY`,
      `cat >/opt/hireloop/fetch-env.sh <<'FETCHENV'
${fetchEnvScript}FETCHENV`,
      "chmod +x /opt/hireloop/fetch-env.sh",
      `ENVIRONMENT=${env} AWS_REGION=${cdk.Stack.of(this).region} /opt/hireloop/fetch-env.sh`,
      `echo "BACKEND_IMAGE=${backendRepo.repositoryUri}:bootstrap-ec2" >> /etc/hireloop/bootstrap.env`,
      `echo "CADDY_IMAGE=${cdk.Aws.ACCOUNT_ID}.dkr.ecr.${cdk.Stack.of(this).region}.amazonaws.com/hireloop-caddy:2-route53" >> /etc/hireloop/bootstrap.env`,
      `echo "LLM_BRIDGE_IMAGE=${llmBridgeRepo.repositoryUri}:bootstrap-ec2" >> /etc/hireloop/bootstrap.env`,
      "set -a && source /etc/hireloop/bootstrap.env && set +a && docker compose -f /etc/hireloop/docker-compose.yml pull || true",
      "set -a && source /etc/hireloop/bootstrap.env && set +a && docker compose -f /etc/hireloop/docker-compose.yml up -d || true",
    );

    const sseInstance = new ec2.Instance(this, "SseInstance", {
      vpc,
      vpcSubnets: { subnets: [vpc.publicSubnets[0]] },
      securityGroup: sgEc2,
      instanceType: ec2.InstanceType.of(ec2.InstanceClass.BURSTABLE4_GRAVITON, ec2.InstanceSize.SMALL),
      machineImage: ec2.MachineImage.latestAmazonLinux2023({
        cpuType: ec2.AmazonLinuxCpuType.ARM_64,
      }),
      userData,
      userDataCausesReplacement: true,
      role: sseRole,
      ssmSessionPermissions: true,
      requireImdsv2: true,
    });

    sseRole.addToPolicy(
      new iam.PolicyStatement({
        actions: ["route53:GetChange", "route53:ChangeResourceRecordSets"],
        resources: [
          `arn:aws:route53:::hostedzone/${hostedZoneId}`,
          "arn:aws:route53:::change/*",
        ],
      }),
    );
    // caddy-dns/route53 plugin looks up the zone by domain name before
    // upserting the _acme-challenge record. ListHostedZonesByName has no
    // resource-level support, so the resource must be "*".
    sseRole.addToPolicy(
      new iam.PolicyStatement({
        actions: ["route53:ListHostedZonesByName"],
        resources: ["*"],
      }),
    );

    const eip = new ec2.CfnEIP(this, "SseEip");
    new ec2.CfnEIPAssociation(this, "SseEipAssoc", {
      instanceId: sseInstance.instanceId,
      allocationId: eip.attrAllocationId,
    });

    new route53.ARecord(this, "SseA", {
      zone: hostedZone,
      recordName: `sse.${env}`,
      target: route53.RecordTarget.fromIpAddresses(eip.attrPublicIp),
    });

    new ssm.StringParameter(this, "SseInstanceId", {
      parameterName: `/hireloop/${env}/sse-instance-id`,
      stringValue: sseInstance.instanceId,
    });

    const githubRepo =
      process.env.GITHUB_REPOSITORY ?? this.node.tryGetContext("githubRepository") ?? "";
    if (!githubRepo || githubRepo.split("/").length !== 2) {
      throw new Error(
        "Set GITHUB_REPOSITORY (owner/repo) or cdk context githubRepository for the GitHub OIDC role",
      );
    }

    const githubOrg = githubRepo.split("/")[0];
    const githubRepoName = githubRepo.split("/")[1];

    // Import the account-level OIDC provider created manually via
    //   aws iam create-open-id-connect-provider
    //     --url https://token.actions.githubusercontent.com
    //     --client-id-list sts.amazonaws.com
    // Managed outside CDK for two reasons: (1) it's a global account resource
    // with exactly one instance per IdP URL, (2) avoids the CDK Lambda-backed
    // custom resource that creates it (extra Lambda + concurrency-quota
    // footprint on fresh accounts).
    const githubOidc = iam.OpenIdConnectProvider.fromOpenIdConnectProviderArn(
      this,
      "GitHubOidc",
      `arn:aws:iam::${this.account}:oidc-provider/token.actions.githubusercontent.com`,
    );

    const oidcRole = new iam.Role(this, "GitHubOidcRole", {
      roleName: "hireloop-github-oidc",
      assumedBy: new iam.WebIdentityPrincipal(githubOidc.openIdConnectProviderArn, {
        StringEquals: {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
        },
        StringLike: {
          "token.actions.githubusercontent.com:sub": `repo:${githubOrg}/${githubRepoName}:*`,
        },
      }),
    });

    // GetAuthorizationToken is an account-scoped action; all per-repo actions
    // are scoped to the two ECR repos this stack owns.
    oidcRole.addToPolicy(
      new iam.PolicyStatement({
        actions: ["ecr:GetAuthorizationToken"],
        resources: ["*"],
      }),
    );
    oidcRole.addToPolicy(
      new iam.PolicyStatement({
        actions: [
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:DescribeImages",
          "ecr:PutImage",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload",
        ],
        resources: [backendRepo.repositoryArn, caddyRepo.repositoryArn],
      }),
    );
    oidcRole.addToPolicy(
      new iam.PolicyStatement({
        actions: ["lambda:UpdateFunctionCode", "lambda:GetFunction", "lambda:GetFunctionConfiguration", "lambda:InvokeFunction"],
        resources: [apiFn.functionArn, migrationFn.functionArn],
      }),
    );
    // SendCommand is scoped to the SSE instance + the one shell-script document
    // GH Actions actually uses. GetCommandInvocation has no resource-level
    // controls and must stay at "*" (AWS API limitation).
    oidcRole.addToPolicy(
      new iam.PolicyStatement({
        actions: ["ssm:SendCommand"],
        resources: [
          `arn:aws:ec2:${this.region}:${this.account}:instance/${sseInstance.instanceId}`,
          `arn:aws:ssm:${this.region}::document/AWS-RunShellScript`,
        ],
      }),
    );
    oidcRole.addToPolicy(
      new iam.PolicyStatement({
        actions: ["ssm:GetCommandInvocation", "ssm:ListCommandInvocations"],
        resources: ["*"],
      }),
    );
    oidcRole.addToPolicy(
      new iam.PolicyStatement({
        actions: ["ssm:PutParameter", "ssm:GetParameter"],
        resources: [`arn:aws:ssm:${this.region}:${this.account}:parameter/hireloop/${env}/*`],
      }),
    );
    oidcRole.addToPolicy(
      new iam.PolicyStatement({
        actions: ["ec2:DescribeInstances"],
        resources: ["*"],
      }),
    );

    // SPA deploy permissions: sync Vite bundles to the three per-app buckets
    // and invalidate the matching CloudFront distributions. Bucket names are
    // known at this stack's synth time via predictable naming (see
    // marketing-stack / user-portal-stack / admin-portal-stack). CreateInvalidation
    // has no meaningful resource-level scoping, so it stays at "*".
    const spaBuckets = [
      `hireloop-marketing-${this.account}`,
      `hireloop-user-portal-${env}-${this.account}`,
      `hireloop-admin-ui-${env}-${this.account}`,
    ];
    oidcRole.addToPolicy(
      new iam.PolicyStatement({
        actions: ["s3:ListBucket", "s3:GetBucketLocation"],
        resources: spaBuckets.map((b) => `arn:aws:s3:::${b}`),
      }),
    );
    oidcRole.addToPolicy(
      new iam.PolicyStatement({
        actions: ["s3:PutObject", "s3:DeleteObject", "s3:GetObject"],
        resources: spaBuckets.map((b) => `arn:aws:s3:::${b}/*`),
      }),
    );
    oidcRole.addToPolicy(
      new iam.PolicyStatement({
        actions: ["cloudfront:CreateInvalidation", "cloudfront:GetInvalidation"],
        resources: ["*"],
      }),
    );

    new cdk.CfnOutput(this, "ApiUrl", {
      value: `https://api.${env}.hireloop.xyz`,
    });
    new cdk.CfnOutput(this, "GitHubOidcRoleArn", {
      value: oidcRole.roleArn,
      description: "Use with aws-actions/configure-aws-credentials (OIDC)",
    });
  }
}
