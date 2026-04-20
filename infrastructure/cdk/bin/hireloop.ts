#!/usr/bin/env node
import "source-map-support/register";
import * as cdk from "aws-cdk-lib";
import { AdminPortalStack } from "../lib/admin-portal-stack";
import { AppStack } from "../lib/app-stack";
import { AuthStack } from "../lib/auth-stack";
import { ConfigStack } from "../lib/config-stack";
import { DataStack } from "../lib/data-stack";
import { DnsStack } from "../lib/dns-stack";
import { MarketingStack } from "../lib/marketing-stack";
import { NetworkStack } from "../lib/network-stack";
import { UserPortalStack } from "../lib/user-portal-stack";

const app = new cdk.App();
const env = {
  account: process.env.CDK_DEFAULT_ACCOUNT,
  region: process.env.CDK_DEFAULT_REGION ?? "us-east-1",
};

const dns = new DnsStack(app, "HireLoop-DNS", { env });

const marketing = new MarketingStack(app, "HireLoop-Marketing", { env });
marketing.addDependency(dns);

const userPortalDev = new UserPortalStack(app, "HireLoop-UserPortal-dev", {
  env,
  environment: "dev",
});
userPortalDev.addDependency(dns);

const adminPortalDev = new AdminPortalStack(app, "HireLoop-AdminPortal-dev", {
  env,
  environment: "dev",
});
adminPortalDev.addDependency(dns);

const network = new NetworkStack(app, "HireLoop-Network", { env });

const data = new DataStack(app, "HireLoop-Data", {
  env,
  vpc: network.vpc,
  securityGroupRds: network.securityGroups.rds,
});
data.addDependency(network);

const authDev = new AuthStack(app, "HireLoop-Auth-dev", {
  env,
  environment: "dev",
});

const configDev = new ConfigStack(app, "HireLoop-Config-dev", {
  env,
  environment: "dev",
  userPool: authDev.userPool,
  userPoolClient: authDev.userPoolClient,
  assetsBucketName: data.assetsBucket.bucketName,
  dbEndpoint: data.database.dbInstanceEndpointAddress,
  dbPort: data.database.dbInstanceEndpointPort,
});
configDev.addDependency(data);
configDev.addDependency(authDev);

if (process.env.CI !== "true") {
  const appDev = new AppStack(app, "HireLoop-App-dev", {
    env,
    environment: "dev",
  });
  appDev.addDependency(network);
  appDev.addDependency(data);
  appDev.addDependency(authDev);
  appDev.addDependency(configDev);
}
