import * as cdk from "aws-cdk-lib";
import * as acm from "aws-cdk-lib/aws-certificatemanager";
import * as cloudfront from "aws-cdk-lib/aws-cloudfront";
import * as origins from "aws-cdk-lib/aws-cloudfront-origins";
import * as route53 from "aws-cdk-lib/aws-route53";
import * as targets from "aws-cdk-lib/aws-route53-targets";
import * as s3 from "aws-cdk-lib/aws-s3";
import * as ssm from "aws-cdk-lib/aws-ssm";
import { Construct } from "constructs";

export interface AdminPortalStackProps extends cdk.StackProps {
  readonly environment: string;
}

export class AdminPortalStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: AdminPortalStackProps) {
    super(scope, id, props);

    const env = props.environment;
    const domainName = `admin.${env}.hireloop.xyz`;

    const hostedZoneId = ssm.StringParameter.valueForStringParameter(
      this,
      "/hireloop/shared/dns/hosted-zone-id",
    );
    const certificateArn = ssm.StringParameter.valueForStringParameter(
      this,
      "/hireloop/shared/dns/certificate-arn",
    );

    const hostedZone = route53.HostedZone.fromHostedZoneAttributes(this, "Zone", {
      hostedZoneId,
      zoneName: "hireloop.xyz",
    });
    const certificate = acm.Certificate.fromCertificateArn(this, "Cert", certificateArn);

    const bucket = new s3.Bucket(this, "Bucket", {
      bucketName: `hireloop-admin-ui-${env}-${cdk.Aws.ACCOUNT_ID}`,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      encryption: s3.BucketEncryption.S3_MANAGED,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    });

    const distribution = new cloudfront.Distribution(this, "Distribution", {
      defaultBehavior: {
        origin: origins.S3BucketOrigin.withOriginAccessControl(bucket),
        viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
        cachePolicy: cloudfront.CachePolicy.CACHING_OPTIMIZED,
        compress: true,
      },
      defaultRootObject: "index.html",
      domainNames: [domainName],
      certificate,
      minimumProtocolVersion: cloudfront.SecurityPolicyProtocol.TLS_V1_2_2021,
      priceClass: cloudfront.PriceClass.PRICE_CLASS_100,
      errorResponses: [
        { httpStatus: 403, responseHttpStatus: 200, responsePagePath: "/index.html", ttl: cdk.Duration.minutes(5) },
        { httpStatus: 404, responseHttpStatus: 200, responsePagePath: "/index.html", ttl: cdk.Duration.minutes(5) },
      ],
    });

    new route53.ARecord(this, "AliasRecord", {
      zone: hostedZone,
      recordName: domainName,
      target: route53.RecordTarget.fromAlias(new targets.CloudFrontTarget(distribution)),
    });

    new ssm.StringParameter(this, "ParamBucketName", {
      parameterName: `/hireloop/${env}/admin-ui/bucket-name`,
      stringValue: bucket.bucketName,
    });
    new ssm.StringParameter(this, "ParamDistributionId", {
      parameterName: `/hireloop/${env}/admin-ui/distribution-id`,
      stringValue: distribution.distributionId,
    });

    new cdk.CfnOutput(this, "BucketName", { value: bucket.bucketName });
    new cdk.CfnOutput(this, "DistributionId", { value: distribution.distributionId });
    new cdk.CfnOutput(this, "DistributionDomain", { value: distribution.distributionDomainName });
    new cdk.CfnOutput(this, "Url", { value: `https://${domainName}` });
  }
}
