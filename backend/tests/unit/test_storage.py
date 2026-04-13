import pytest
from moto import mock_aws

from hireloop.services.storage import StorageService


@pytest.mark.asyncio
async def test_upload_and_download_bytes() -> None:
    with mock_aws():
        import boto3

        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket="test-bucket")

        storage = StorageService(bucket="test-bucket", region="us-east-1")

        key = "resumes/user-1/file.pdf"
        content = b"fake pdf bytes"

        await storage.upload_bytes(key, content, content_type="application/pdf")
        downloaded = await storage.download_bytes(key)

        assert downloaded == content


@pytest.mark.asyncio
async def test_generate_presigned_url_for_download() -> None:
    with mock_aws():
        import boto3

        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket="test-bucket")
        client.put_object(Bucket="test-bucket", Key="foo.pdf", Body=b"x")

        storage = StorageService(bucket="test-bucket", region="us-east-1")
        url = await storage.presigned_download_url("foo.pdf", expires_in=900)

        assert url.startswith("https://")
        assert "test-bucket" in url
        assert "foo.pdf" in url
