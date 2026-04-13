from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from moto import mock_aws

FIXTURES = Path(__file__).parent.parent / "fixtures" / "resumes"

FAKE_CLAIMS = {
    "sub": "cognito-sub-upload",
    "email": "upload@example.com",
    "custom:role": "user",
    "custom:subscription_tier": "trial",
}


@pytest.mark.asyncio
async def test_upload_docx_resume_stores_and_parses(client: AsyncClient) -> None:
    with mock_aws():
        import boto3

        boto3.client("s3", region_name="us-east-1").create_bucket(Bucket="hireloop-dev-assets")

        with patch(
            "hireloop.integrations.cognito.CognitoJwtVerifier.verify",
            new=AsyncMock(return_value=FAKE_CLAIMS),
        ):
            with (FIXTURES / "sample.docx").open("rb") as f:
                response = await client.post(
                    "/api/v1/profile/resume",
                    headers={"Authorization": "Bearer fake"},
                    files={
                        "file": (
                            "sample.docx",
                            f,
                            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        )
                    },
                )

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["master_resume_s3"] is not None
    assert body["master_resume_md"] is not None
    assert "Jane Doe" in body["master_resume_md"]


@pytest.mark.asyncio
async def test_upload_rejects_unsupported_filetype(client: AsyncClient) -> None:
    with patch(
        "hireloop.integrations.cognito.CognitoJwtVerifier.verify",
        new=AsyncMock(return_value=FAKE_CLAIMS),
    ):
        response = await client.post(
            "/api/v1/profile/resume",
            headers={"Authorization": "Bearer fake"},
            files={"file": ("resume.txt", b"hello", "text/plain")},
        )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "UNPROCESSABLE_ENTITY"


@pytest.mark.asyncio
async def test_upload_rejects_file_too_large(client: AsyncClient) -> None:
    big_bytes = b"x" * (11 * 1024 * 1024)
    with patch(
        "hireloop.integrations.cognito.CognitoJwtVerifier.verify",
        new=AsyncMock(return_value=FAKE_CLAIMS),
    ):
        response = await client.post(
            "/api/v1/profile/resume",
            headers={"Authorization": "Bearer fake"},
            files={"file": ("big.pdf", big_bytes, "application/pdf")},
        )
    assert response.status_code == 413
