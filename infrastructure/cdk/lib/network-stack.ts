import * as cdk from "aws-cdk-lib";
import * as ec2 from "aws-cdk-lib/aws-ec2";
import { Construct } from "constructs";

export interface NetworkStackProps extends cdk.StackProps {}

/** Security group shells — ingress refined in 5a.2 compute. */
export interface HireLoopSecurityGroups {
  readonly alb: ec2.SecurityGroup;
  readonly ec2Backend: ec2.SecurityGroup;
  readonly lambda: ec2.SecurityGroup;
  readonly dbBootstrap: ec2.SecurityGroup;
  readonly rds: ec2.SecurityGroup;
  readonly fckNat: ec2.SecurityGroup;
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
        {
          name: "PrivateEgress",
          subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
          cidrMask: 20,
        },
        {
          name: "Isolated",
          subnetType: ec2.SubnetType.PRIVATE_ISOLATED,
          cidrMask: 22,
        },
      ],
    });

    this.vpc.addGatewayEndpoint("S3Endpoint", {
      service: ec2.GatewayVpcEndpointAwsService.S3,
    });

    const sgAlb = new ec2.SecurityGroup(this, "SgAlb", {
      vpc: this.vpc,
      securityGroupName: "hireloop-sg-alb",
      description: "SG-ALB — ALB (5a.2)",
      allowAllOutbound: true,
    });

    const sgEc2 = new ec2.SecurityGroup(this, "SgEc2Backend", {
      vpc: this.vpc,
      securityGroupName: "hireloop-sg-ec2-backend",
      description: "SG-EC2-Backend — SSE host (5a.2)",
      allowAllOutbound: true,
    });

    const sgLambda = new ec2.SecurityGroup(this, "SgLambda", {
      vpc: this.vpc,
      securityGroupName: "hireloop-sg-lambda",
      description: "SG-Lambda — Lambda ENIs (5a.2)",
      allowAllOutbound: true,
    });

    const sgDbBootstrap = new ec2.SecurityGroup(this, "SgDbBootstrap", {
      vpc: this.vpc,
      securityGroupName: "hireloop-sg-db-bootstrap",
      description: "SG-DbBootstrap — RDS bootstrap Lambda + custom resources",
      allowAllOutbound: true,
    });

    const sgRds = new ec2.SecurityGroup(this, "SgRds", {
      vpc: this.vpc,
      securityGroupName: "hireloop-sg-rds",
      description: "SG-RDS — PostgreSQL",
      allowAllOutbound: true,
    });

    const sgFckNat = new ec2.SecurityGroup(this, "SgFckNat", {
      vpc: this.vpc,
      securityGroupName: "hireloop-sg-fck-nat",
      description: "SG-FckNat — NAT instance (5a.2)",
      allowAllOutbound: true,
    });

    sgRds.connections.allowFrom(sgDbBootstrap, ec2.Port.tcp(5432), "Bootstrap Lambda");
    sgRds.connections.allowFrom(sgLambda, ec2.Port.tcp(5432), "Lambda (5a.2)");
    sgRds.connections.allowFrom(sgEc2, ec2.Port.tcp(5432), "SSE EC2 (5a.2)");

    this.securityGroups = {
      alb: sgAlb,
      ec2Backend: sgEc2,
      lambda: sgLambda,
      dbBootstrap: sgDbBootstrap,
      rds: sgRds,
      fckNat: sgFckNat,
    };

    new cdk.CfnOutput(this, "VpcId", { value: this.vpc.vpcId });
  }
}
