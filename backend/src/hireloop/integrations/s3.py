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
    # Only pass explicit creds when NOT running under Lambda. Lambda injects
    # AKID + SECRET + SESSION_TOKEN env vars for the exec role's temp creds;
    # if we only forward AKID+SECRET to boto3 (dropping the session token),
    # STS rejects them with InvalidAccessKeyId. Letting boto3's default
    # credential chain handle Lambda lets it pick up all three automatically.
    if settings.aws_endpoint_url and settings.aws_access_key_id:
        kwargs["aws_access_key_id"] = settings.aws_access_key_id
        if settings.aws_secret_access_key:
            kwargs["aws_secret_access_key"] = settings.aws_secret_access_key
        if settings.aws_session_token:
            kwargs["aws_session_token"] = settings.aws_session_token
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
