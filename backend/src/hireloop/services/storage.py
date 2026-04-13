import asyncio
from typing import Any

from hireloop.config import get_settings
from hireloop.integrations.s3 import get_s3_client


class StorageService:
    def __init__(self, bucket: str, region: str) -> None:
        self.bucket = bucket
        self.region = region
        self._client: Any = get_s3_client()

    async def upload_bytes(
        self,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> str:
        await asyncio.to_thread(
            self._client.put_object,
            Bucket=self.bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
            ServerSideEncryption="AES256",
        )
        return key

    async def download_bytes(self, key: str) -> bytes:
        response = await asyncio.to_thread(
            self._client.get_object,
            Bucket=self.bucket,
            Key=key,
        )
        return response["Body"].read()  # type: ignore[no-any-return]

    async def delete(self, key: str) -> None:
        await asyncio.to_thread(
            self._client.delete_object,
            Bucket=self.bucket,
            Key=key,
        )

    async def presigned_download_url(self, key: str, expires_in: int = 900) -> str:
        return await asyncio.to_thread(
            self._client.generate_presigned_url,
            ClientMethod="get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=expires_in,
        )


def get_storage_service() -> StorageService:
    settings = get_settings()
    return StorageService(bucket=settings.aws_s3_bucket, region=settings.aws_region)
