"""Unit tests for integrations/auth_jwt.py."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from jose import jwt

from hireloop.api.errors import AppError
from hireloop.integrations.auth_jwt import JwtVerifier

SECRET = "unit-test-signing-secret"
ISSUER = "hireloop-test"
AUDIENCE = "hireloop-users-test"


def _encode(**overrides: Any) -> str:
    now = datetime.now(UTC)
    claims: dict[str, Any] = {
        "sub": "sub-123",
        "user_id": "00000000-0000-0000-0000-000000000001",
        "email": "user@example.com",
        "custom:role": "user",
        "custom:subscription_tier": "trial",
        "iss": ISSUER,
        "aud": AUDIENCE,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=60)).timestamp()),
        "token_use": "access",
    }
    claims.update(overrides)
    secret = overrides.pop("_secret", SECRET)
    return jwt.encode(claims, secret, algorithm="HS256")


def _verifier() -> JwtVerifier:
    return JwtVerifier(signing_secret=SECRET, issuer=ISSUER, audience=AUDIENCE)


@pytest.mark.asyncio
async def test_verify_accepts_valid_access_token() -> None:
    token = _encode()
    claims = await _verifier().verify(token)
    assert claims["sub"] == "sub-123"
    assert claims["email"] == "user@example.com"
    assert claims["custom:role"] == "user"
    assert claims["custom:subscription_tier"] == "trial"


@pytest.mark.asyncio
async def test_verify_rejects_wrong_signature() -> None:
    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "sub": "x",
            "iss": ISSUER,
            "aud": AUDIENCE,
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=60)).timestamp()),
            "token_use": "access",
        },
        "a-different-secret",
        algorithm="HS256",
    )
    with pytest.raises(AppError) as excinfo:
        await _verifier().verify(token)
    assert excinfo.value.status_code == 401
    assert excinfo.value.code == "UNAUTHENTICATED"


@pytest.mark.asyncio
async def test_verify_rejects_wrong_audience() -> None:
    token = _encode(aud="some-other-audience")
    with pytest.raises(AppError):
        await _verifier().verify(token)


@pytest.mark.asyncio
async def test_verify_rejects_wrong_issuer() -> None:
    token = _encode(iss="https://not-us.example.com")
    with pytest.raises(AppError):
        await _verifier().verify(token)


@pytest.mark.asyncio
async def test_verify_rejects_expired_token() -> None:
    past = datetime.now(UTC) - timedelta(minutes=61)
    token = _encode(
        iat=int(past.timestamp()),
        exp=int((past + timedelta(minutes=1)).timestamp()),
    )
    with pytest.raises(AppError):
        await _verifier().verify(token)


@pytest.mark.asyncio
async def test_verify_rejects_refresh_token_shape() -> None:
    # Token carries token_use=refresh — the access-path verifier must refuse it.
    token = _encode(token_use="refresh")
    with pytest.raises(AppError) as excinfo:
        await _verifier().verify(token)
    assert "access" in excinfo.value.message.lower()


@pytest.mark.asyncio
async def test_verify_rejects_garbage() -> None:
    with pytest.raises(AppError):
        await _verifier().verify("not-a-jwt")
