/**
 * Custom resource onEvent handler for RDS database + user bootstrap.
 * Invoked by aws-cdk-lib custom-resources Provider.
 */
import {
  GetSecretValueCommand,
  PutSecretValueCommand,
  SecretsManagerClient,
} from "@aws-sdk/client-secrets-manager";
import type { CloudFormationCustomResourceEvent } from "aws-lambda";
import { Client } from "pg";
import * as crypto from "node:crypto";

const sm = new SecretsManagerClient({});

function randomPassword(): string {
  return crypto.randomBytes(24).toString("base64url") + "Aa1!";
}

async function getMasterJson(secretArn: string): Promise<{
  username: string;
  password: string;
}> {
  const out = await sm.send(new GetSecretValueCommand({ SecretId: secretArn }));
  const raw = out.SecretString;
  if (!raw) throw new Error("Master secret has no SecretString");
  const j = JSON.parse(raw) as { username?: string; password?: string };
  if (!j.username || !j.password) throw new Error("Master secret missing username/password");
  return { username: j.username, password: j.password };
}

async function ensureDatabase(client: Client, name: string): Promise<void> {
  const r = await client.query("SELECT 1 FROM pg_database WHERE datname = $1", [name]);
  if (r.rowCount === 0) {
    await client.query(`CREATE DATABASE ${quoteIdent(name)}`);
  }
}

function quoteIdent(name: string): string {
  return '"' + name.replace(/"/g, '""') + '"';
}

function quoteLiteral(value: string): string {
  return "'" + value.replace(/'/g, "''") + "'";
}

async function ensureUser(client: Client, role: string, password: string): Promise<void> {
  // PostgreSQL does not accept bind parameters for CREATE/ALTER USER ... WITH PASSWORD.
  // The password must be an inlined string literal.
  const pw = quoteLiteral(password);
  const r = await client.query("SELECT 1 FROM pg_roles WHERE rolname = $1", [role]);
  if (r.rowCount === 0) {
    await client.query(`CREATE USER ${quoteIdent(role)} WITH PASSWORD ${pw}`);
  } else {
    await client.query(`ALTER USER ${quoteIdent(role)} WITH PASSWORD ${pw}`);
  }
}

export async function handler(event: CloudFormationCustomResourceEvent): Promise<{
  PhysicalResourceId: string;
  Data: Record<string, string>;
}> {
  const masterArn = event.ResourceProperties.MasterSecretArn as string;
  const dbAppSecretArn = event.ResourceProperties.DbAppSecretArn as string;
  const endpoint = event.ResourceProperties.DbEndpoint as string;
  const port = Number(event.ResourceProperties.DbPort ?? 5432);

  const physicalId = "hireloop-db-bootstrap";

  if (event.RequestType === "Delete") {
    return { PhysicalResourceId: physicalId, Data: {} };
  }

  const master = await getMasterJson(masterArn);
  const devPw = randomPassword();
  const sandboxPw = randomPassword();
  const prodPw = randomPassword();

  const adminUrl = `postgresql://${encodeURIComponent(master.username)}:${encodeURIComponent(master.password)}@${endpoint}:${port}/postgres`;

  const admin = new Client({
    connectionString: adminUrl,
    ssl: { rejectUnauthorized: false },
  });
  await admin.connect();

  await ensureDatabase(admin, "hireloop_dev");
  await ensureDatabase(admin, "hireloop_sandbox");
  await ensureDatabase(admin, "hireloop_prod");

  await ensureUser(admin, "hireloop_dev_app", devPw);
  await ensureUser(admin, "hireloop_sandbox_app", sandboxPw);
  await ensureUser(admin, "hireloop_prod_app", prodPw);

  await admin.query(`REVOKE CONNECT ON DATABASE ${quoteIdent("hireloop_dev")} FROM PUBLIC`);
  await admin.query(`REVOKE CONNECT ON DATABASE ${quoteIdent("hireloop_sandbox")} FROM PUBLIC`);
  await admin.query(`REVOKE CONNECT ON DATABASE ${quoteIdent("hireloop_prod")} FROM PUBLIC`);

  await admin.query(`GRANT CONNECT ON DATABASE ${quoteIdent("hireloop_dev")} TO ${quoteIdent("hireloop_dev_app")}`);
  await admin.query(
    `GRANT CONNECT ON DATABASE ${quoteIdent("hireloop_sandbox")} TO ${quoteIdent("hireloop_sandbox_app")}`,
  );
  await admin.query(
    `GRANT CONNECT ON DATABASE ${quoteIdent("hireloop_prod")} TO ${quoteIdent("hireloop_prod_app")}`,
  );

  await admin.end();

  const masterUser = master.username;

  const grantDb = async (db: string, appUser: string) => {
    const c = new Client({
      connectionString: `postgresql://${encodeURIComponent(master.username)}:${encodeURIComponent(master.password)}@${endpoint}:${port}/${db}`,
      ssl: { rejectUnauthorized: false },
    });
    await c.connect();
    await c.query(`GRANT USAGE ON SCHEMA public TO ${quoteIdent(appUser)}`);
    await c.query(`GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO ${quoteIdent(appUser)}`);
    await c.query(`GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO ${quoteIdent(appUser)}`);
    await c.query(
      `ALTER DEFAULT PRIVILEGES FOR ROLE ${quoteIdent(masterUser)} IN SCHEMA public GRANT ALL PRIVILEGES ON TABLES TO ${quoteIdent(appUser)}`,
    );
    await c.query(
      `ALTER DEFAULT PRIVILEGES FOR ROLE ${quoteIdent(masterUser)} IN SCHEMA public GRANT ALL PRIVILEGES ON SEQUENCES TO ${quoteIdent(appUser)}`,
    );
    await c.end();
  };

  await grantDb("hireloop_dev", "hireloop_dev_app");
  await grantDb("hireloop_sandbox", "hireloop_sandbox_app");
  await grantDb("hireloop_prod", "hireloop_prod_app");

  await sm.send(
    new PutSecretValueCommand({
      SecretId: dbAppSecretArn,
      SecretString: JSON.stringify({ password: devPw }),
    }),
  );

  return {
    PhysicalResourceId: physicalId,
    Data: {},
  };
}
