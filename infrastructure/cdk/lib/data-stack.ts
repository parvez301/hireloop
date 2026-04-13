import * as path from "node:path";
import * as cdk from "aws-cdk-lib";
import * as ec2 from "aws-cdk-lib/aws-ec2";
import * as lambda from "aws-cdk-lib/aws-lambda";
import { NodejsFunction } from "aws-cdk-lib/aws-lambda-nodejs";
import * as rds from "aws-cdk-lib/aws-rds";
import * as s3 from "aws-cdk-lib/aws-s3";
import * as secretsmanager from "aws-cdk-lib/aws-secretsmanager";
import * as cr from "aws-cdk-lib/custom-resources";
import * as ssm from "aws-cdk-lib/aws-ssm";
import { Construct } from "constructs";

export interface DataStackProps extends cdk.StackProps {
  readonly vpc: ec2.IVpc;
  readonly securityGroupRds: ec2.ISecurityGroup;
  readonly securityGroupDbBootstrap: ec2.ISecurityGroup;
}

export class DataStack extends cdk.Stack {
  public readonly database: rds.DatabaseInstance;
  public readonly assetsBucket: s3.Bucket;
  public readonly dbAppDevSecret: secretsmanager.ISecret;

  constructor(scope: Construct, id: string, props: DataStackProps) {
    super(scope, id, props);

    this.assetsBucket = new s3.Bucket(this, "SharedAssets", {
      bucketName: `hireloop-shared-assets-${cdk.Aws.ACCOUNT_ID}`,
      encryption: s3.BucketEncryption.S3_MANAGED,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      versioned: false,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
      lifecycleRules: [
        { id: "expire-exports", prefix: "exports/", expiration: cdk.Duration.days(30) },
        { id: "expire-temp", prefix: "temp/", expiration: cdk.Duration.days(7) },
      ],
    });

    this.database = new rds.DatabaseInstance(this, "Postgres", {
      engine: rds.DatabaseInstanceEngine.postgres({
        version: rds.PostgresEngineVersion.VER_16,
      }),
      instanceType: ec2.InstanceType.of(
        ec2.InstanceClass.BURSTABLE4_GRAVITON,
        ec2.InstanceSize.SMALL,
      ),
      vpc: props.vpc,
      vpcSubnets: { subnetType: ec2.SubnetType.PRIVATE_ISOLATED },
      securityGroups: [props.securityGroupRds],
      multiAz: false,
      allocatedStorage: 20,
      storageType: rds.StorageType.GP3,
      storageEncrypted: true,
      backupRetention: cdk.Duration.days(7),
      autoMinorVersionUpgrade: true,
      publiclyAccessible: false,
      deletionProtection: false,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
      databaseName: "hireloop_dev",
      credentials: rds.Credentials.fromGeneratedSecret("postgres"),
    });

    const masterSecret = this.database.secret!;
    this.dbAppDevSecret = new secretsmanager.Secret(this, "DevDbAppPassword", {
      secretName: "hireloop/dev/db-app-password",
      description: "hireloop_dev_app password (written by DB bootstrap)",
      secretStringValue: cdk.SecretValue.unsafePlainText('{"password":"pending-bootstrap"}'),
    });

    const bootstrapFn = new NodejsFunction(this, "DbBootstrapFn", {
      runtime: lambda.Runtime.NODEJS_20_X,
      entry: path.join(__dirname, "db-bootstrap-handler.ts"),
      handler: "handler",
      timeout: cdk.Duration.minutes(5),
      vpc: props.vpc,
      vpcSubnets: { subnetType: ec2.SubnetType.PRIVATE_ISOLATED },
      securityGroups: [props.securityGroupDbBootstrap],
      environment: {},
      bundling: {
        minify: true,
        sourceMap: true,
      },
    });

    masterSecret.grantRead(bootstrapFn);
    this.dbAppDevSecret.grantWrite(bootstrapFn);

    const provider = new cr.Provider(this, "DbBootstrapProvider", {
      onEventHandler: bootstrapFn,
    });

    const bootstrap = new cdk.CustomResource(this, "DbBootstrap", {
      serviceToken: provider.serviceToken,
      properties: {
        MasterSecretArn: masterSecret.secretArn,
        DbEndpoint: this.database.dbInstanceEndpointAddress,
        DbPort: this.database.dbInstanceEndpointPort,
        DbAppSecretArn: this.dbAppDevSecret.secretArn,
      },
    });
    bootstrap.node.addDependency(this.database);

    new ssm.StringParameter(this, "ParamMasterSecretArn", {
      parameterName: "/hireloop/shared/rds/master-secret-arn",
      stringValue: masterSecret.secretArn,
    });

    new cdk.CfnOutput(this, "DbEndpoint", {
      value: this.database.dbInstanceEndpointAddress,
    });
    new cdk.CfnOutput(this, "AssetsBucketName", {
      value: this.assetsBucket.bucketName,
    });
  }
}
