import * as cdk from "aws-cdk-lib";
import * as cognito from "aws-cdk-lib/aws-cognito";
import { Construct } from "constructs";

export interface AuthStackProps extends cdk.StackProps {
  readonly environment: string;
}

export class AuthStack extends cdk.Stack {
  public readonly userPool: cognito.UserPool;
  public readonly userPoolClient: cognito.UserPoolClient;

  constructor(scope: Construct, id: string, props: AuthStackProps) {
    super(scope, id, props);

    this.userPool = new cognito.UserPool(this, "UserPool", {
      userPoolName: `HireLoop-Users-${props.environment}`,
      signInAliases: { email: true },
      selfSignUpEnabled: true,
      autoVerify: { email: true },
      passwordPolicy: {
        minLength: 10,
        requireLowercase: true,
        requireUppercase: true,
        requireDigits: true,
        requireSymbols: false,
      },
      standardAttributes: {
        email: { required: true, mutable: false },
        givenName: { required: true, mutable: true },
        familyName: { required: false, mutable: true },
      },
      customAttributes: {
        user_id: new cognito.StringAttribute({ mutable: false }),
        subscription_tier: new cognito.StringAttribute({ mutable: true }),
        role: new cognito.StringAttribute({ mutable: true }),
        onboarding_state: new cognito.StringAttribute({ mutable: true }),
      },
      mfa: cognito.Mfa.OPTIONAL,
      accountRecovery: cognito.AccountRecovery.EMAIL_ONLY,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    });

    this.userPool.addDomain("DefaultDomain", {
      cognitoDomain: {
        domainPrefix: `hireloop-${props.environment}`,
      },
    });

    const portalOrigin = `https://app.${props.environment}.hireloop.xyz`;

    this.userPoolClient = this.userPool.addClient("UserPoolClient", {
      userPoolClientName: `hireloop-${props.environment}-client`,
      authFlows: {
        userPassword: true,
        userSrp: true,
      },
      generateSecret: false,
      oAuth: {
        flows: {
          authorizationCodeGrant: true,
        },
        scopes: [
          cognito.OAuthScope.OPENID,
          cognito.OAuthScope.EMAIL,
          cognito.OAuthScope.PROFILE,
        ],
        callbackUrls: [
          `${portalOrigin}/auth/callback`,
          "http://localhost:5173/auth/callback",
        ],
        logoutUrls: [
          `${portalOrigin}/`,
          "http://localhost:5173/",
        ],
      },
      supportedIdentityProviders: [cognito.UserPoolClientIdentityProvider.COGNITO],
    });

    new cdk.CfnOutput(this, "UserPoolId", { value: this.userPool.userPoolId });
    new cdk.CfnOutput(this, "UserPoolClientId", { value: this.userPoolClient.userPoolClientId });
    new cdk.CfnOutput(this, "UserPoolArn", { value: this.userPool.userPoolArn });
    new cdk.CfnOutput(this, "CognitoDomain", {
      value: `hireloop-${props.environment}.auth.${this.region}.amazoncognito.com`,
    });
  }
}
