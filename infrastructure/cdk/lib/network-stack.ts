import * as cdk from "aws-cdk-lib";
import * as ec2 from "aws-cdk-lib/aws-ec2";
import * as ssm from "aws-cdk-lib/aws-ssm";
import { Construct } from "constructs";

export interface NetworkStackProps extends cdk.StackProps {}

/** Security groups for 5a.2 — EC2 SSE host + RDS only. */
export interface HireLoopSecurityGroups {
  readonly ec2Backend: ec2.SecurityGroup;
  readonly rds: ec2.SecurityGroup;
}

export class NetworkStack extends cdk.Stack {
  public readonly vpc: ec2.Vpc;
  public readonly securityGroups: HireLoopSecurityGroups;

  constructor(scope: Construct, id: string, props?: NetworkStackProps) {
    super(scope, id, props);

    this.vpc = new ec2.Vpc(this, "Vpc", {
      vpcName: "hireloop-shared",
      ipAddresses: ec2.IpAddresses.cidr("10.0.0.0/16"),
      maxAzs: 2,
      natGateways: 0,
      subnetConfiguration: [
        { name: "Public", subnetType: ec2.SubnetType.PUBLIC, cidrMask: 24 },
      ],
    });

    this.vpc.addGatewayEndpoint("S3Endpoint", {
      service: ec2.GatewayVpcEndpointAwsService.S3,
    });

    const sgEc2 = new ec2.SecurityGroup(this, "SgEc2Backend", {
      vpc: this.vpc,
      securityGroupName: "hireloop-sg-ec2-backend",
      description: "SG-EC2-Backend — SSE host (5a.2)",
      allowAllOutbound: true,
    });
    sgEc2.addIngressRule(ec2.Peer.anyIpv4(), ec2.Port.tcp(443), "HTTPS (Caddy)");
    sgEc2.addIngressRule(ec2.Peer.anyIpv4(), ec2.Port.tcp(80), "HTTP redirect / ACME");

    const sgRds = new ec2.SecurityGroup(this, "SgRds", {
      vpc: this.vpc,
      securityGroupName: "hireloop-sg-rds",
      description: "SG-RDS — PostgreSQL (5a.2 public + Lambda out-of-VPC)",
      allowAllOutbound: true,
    });
    sgRds.addIngressRule(sgEc2, ec2.Port.tcp(5432), "SSE EC2");
    sgRds.addIngressRule(ec2.Peer.anyIpv4(), ec2.Port.tcp(5432), "Lambda (no stable egress IPs)");

    this.securityGroups = {
      ec2Backend: sgEc2,
      rds: sgRds,
    };

    new ssm.StringParameter(this, "ParamVpcId", {
      parameterName: "/hireloop/shared/network/vpc-id",
      stringValue: this.vpc.vpcId,
    });
    this.vpc.publicSubnets.forEach((subnet, i) => {
      new ssm.StringParameter(this, `ParamPublicSubnet${i}`, {
        parameterName: `/hireloop/shared/network/public-subnet-${i}-id`,
        stringValue: subnet.subnetId,
      });
    });
    new ssm.StringParameter(this, "ParamSgEc2BackendId", {
      parameterName: "/hireloop/shared/network/sg-ec2-backend-id",
      stringValue: sgEc2.securityGroupId,
    });

    new cdk.CfnOutput(this, "VpcId", { value: this.vpc.vpcId });
  }
}
