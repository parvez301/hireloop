import * as cdk from "aws-cdk-lib";
import * as cognito from "aws-cdk-lib/aws-cognito";
import * as ssm from "aws-cdk-lib/aws-ssm";
import * as secretsmanager from "aws-cdk-lib/aws-secretsmanager";
import { Construct } from "constructs";

export interface ConfigStackProps extends cdk.StackProps {
  readonly environment: string;
  readonly userPool: cognito.IUserPool;
  readonly userPoolClient: cognito.IUserPoolClient;
  readonly assetsBucketName: string;
  readonly dbEndpoint: string;
  readonly dbPort: string;
}

export class ConfigStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: ConfigStackProps) {
    super(scope, id, props);

    const env = props.environment;
    const prefix = `hireloop/${env}`;

    const emptyJson = (purpose: string) =>
      new secretsmanager.Secret(this, purpose.replace(/[^a-zA-Z0-9]/g, ""), {
        secretName: `${prefix}/${purpose}`,
        secretStringValue: cdk.SecretValue.unsafePlainText("{}"),
        removalPolicy: cdk.RemovalPolicy.RETAIN,
      });

    emptyJson("anthropic-api-key");
    emptyJson("google-api-key");
    emptyJson("stripe-secret-key");
    emptyJson("stripe-webhook-secret");
    emptyJson("pdf-render-shared-secret");
    emptyJson("inngest-event-key");
    emptyJson("inngest-signing-key");

    new ssm.StringParameter(this, "CognitoUserPoolId", {
      parameterName: `/hireloop/${env}/cognito/user-pool-id`,
      stringValue: props.userPool.userPoolId,
    });
    new ssm.StringParameter(this, "CognitoUserPoolClientId", {
      parameterName: `/hireloop/${env}/cognito/user-pool-client-id`,
      stringValue: props.userPoolClient.userPoolClientId,
    });
    new ssm.StringParameter(this, "CognitoRegion", {
      parameterName: `/hireloop/${env}/cognito/region`,
      stringValue: this.region,
    });
    new ssm.StringParameter(this, "AwsRegion", {
      parameterName: `/hireloop/${env}/aws/region`,
      stringValue: this.region,
    });
    new ssm.StringParameter(this, "S3AssetsBucket", {
      parameterName: `/hireloop/${env}/s3/assets-bucket-name`,
      stringValue: props.assetsBucketName,
    });
    new ssm.StringParameter(this, "DbEndpoint", {
      parameterName: `/hireloop/${env}/db/endpoint`,
      stringValue: props.dbEndpoint,
    });
    new ssm.StringParameter(this, "DbPort", {
      parameterName: `/hireloop/${env}/db/port`,
      stringValue: props.dbPort,
    });
    new ssm.StringParameter(this, "DbDatabaseName", {
      parameterName: `/hireloop/${env}/db/database-name`,
      stringValue: "hireloop_dev",
    });
    new ssm.StringParameter(this, "DbAppUser", {
      parameterName: `/hireloop/${env}/db/app-user`,
      stringValue: "hireloop_dev_app",
    });

    new ssm.StringParameter(this, "LastGreenSha", {
      parameterName: `/hireloop/${env}/last-green-sha`,
      stringValue: "bootstrap",
    });

    new ssm.StringParameter(this, "CurrentImageTag", {
      parameterName: `/hireloop/${env}/current-image-tag`,
      stringValue: "bootstrap",
      description: "Bootstrap placeholder; replace with real ECR tag before first HireLoop-App deploy",
    });
  }
}
