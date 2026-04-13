import { PutObjectCommand, S3Client } from "@aws-sdk/client-s3";

const REGION = process.env.AWS_REGION ?? "us-east-1";
const ENDPOINT = process.env.AWS_ENDPOINT_URL;
const BUCKET = process.env.AWS_S3_BUCKET ?? "hireloop-dev-assets";

let client: S3Client | null = null;

function getClient(): S3Client {
  if (!client) {
    client = new S3Client({
      region: REGION,
      ...(ENDPOINT ? { endpoint: ENDPOINT, forcePathStyle: true } : {}),
    });
  }
  return client;
}

export async function uploadPdf(key: string, body: Buffer): Promise<void> {
  await getClient().send(
    new PutObjectCommand({
      Bucket: BUCKET,
      Key: key,
      Body: body,
      ContentType: "application/pdf",
    }),
  );
}
