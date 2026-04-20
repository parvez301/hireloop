import * as cdk from "aws-cdk-lib";
import * as acm from "aws-cdk-lib/aws-certificatemanager";
import * as route53 from "aws-cdk-lib/aws-route53";
import * as ssm from "aws-cdk-lib/aws-ssm";
import { Construct } from "constructs";

export class DnsStack extends cdk.Stack {
  public readonly hostedZone: route53.PublicHostedZone;
  public readonly certificate: acm.Certificate;

  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    this.hostedZone = new route53.PublicHostedZone(this, "HostedZone", {
      zoneName: "hireloop.xyz",
    });

    this.certificate = new acm.Certificate(this, "WildcardCert", {
      domainName: "hireloop.xyz",
      subjectAlternativeNames: [
        "*.hireloop.xyz",
        "*.dev.hireloop.xyz",
        "*.staging.hireloop.xyz",
        "*.prod.hireloop.xyz",
      ],
      validation: acm.CertificateValidation.fromDns(this.hostedZone),
    });

    const loopback = route53.RecordTarget.fromIpAddresses("127.0.0.1");
    new route53.ARecord(this, "PlaceholderApp", {
      zone: this.hostedZone,
      recordName: "app",
      target: loopback,
    });
    new route53.ARecord(this, "PlaceholderApi", {
      zone: this.hostedZone,
      recordName: "api",
      target: loopback,
    });
    new route53.ARecord(this, "PlaceholderAdmin", {
      zone: this.hostedZone,
      recordName: "admin",
      target: loopback,
    });

    new ssm.StringParameter(this, "ParamHostedZoneId", {
      parameterName: "/hireloop/shared/dns/hosted-zone-id",
      stringValue: this.hostedZone.hostedZoneId,
    });

    new ssm.StringParameter(this, "ParamCertificateArn", {
      parameterName: "/hireloop/shared/dns/certificate-arn",
      stringValue: this.certificate.certificateArn,
    });

    new cdk.CfnOutput(this, "NameServers", {
      value: cdk.Fn.join("\n", this.hostedZone.hostedZoneNameServers ?? []),
      description: "Add these NS records at your domain registrar",
    });
  }
}
