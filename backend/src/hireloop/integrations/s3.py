from functools import lru_cache
from typing import Any

import boto3
from botocore.config import Config

from hireloop.config import get_settings


@lru_cache(maxsize=1)
def get_s3_client() -> Any:
    settings = get_settings()
    kwargs: dict[str, Any] = {
        "service_name": "s3",
        "region_name": settings.aws_region,
        "config": Config(signature_version="s3v4", retries={"max_attempts": 3}),
    }
    if settings.aws_endpoint_url:
        kwargs["endpoint_url"] = settings.aws_endpoint_url
    if settings.aws_access_key_id:
        kwargs["aws_access_key_id"] = settings.aws_access_key_id
    if settings.aws_secret_access_key:
        kwargs["aws_secret_access_key"] = settings.aws_secret_access_key
    return boto3.client(**kwargs)


def get_presigned_url(key: str, *, expires_in: int = 900) -> str:
    settings = get_settings()
    client = get_s3_client()
    url: str = client.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.aws_s3_bucket, "Key": key},
        ExpiresIn=expires_in,
    )
    return url
