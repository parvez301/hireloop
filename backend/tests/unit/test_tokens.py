"""Unit tests for services/tokens.py issuance helpers (non-DB paths)."""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from jose import jwt

from hireloop.config import Settings
from hireloop.services.tokens import (
    hash_secret,
    issue_access_token,
    issue_opaque_reset_token,
)


def _settings() -> Settings:
    return Settings(
        database_url="postgresql+asyncpg://u:p@localhost/x",
        cognito_user_pool_id="pool",
        cognito_client_id="client",
        cognito_region="us-east-1",
        cognito_jwks_url="https://example.invalid/jwks.json",
        jwt_signing_secret="unit-test-signing-secret",
        jwt_issuer="hireloop-test",
        jwt_audience="hireloop-users-test",
        jwt_access_ttl_minutes=60,
        jwt_refresh_ttl_days=30,
    )


def test_issue_access_token_encodes_expected_claims() -> None:
    settings = _settings()
    user_id: UUID = uuid4()
    token, expires_in = issue_access_token(
        user_id=user_id,
        cognito_sub="cognito-sub-abc",
        email="jane@example.com",
        role="admin",
        subscription_tier="pro",
        settings=settings,
    )
    assert expires_in == settings.jwt_access_ttl_minutes * 60
    decoded = jwt.decode(
        token,
        settings.jwt_signing_secret,
        algorithms=["HS256"],
        audience=settings.jwt_audience,
        issuer=settings.jwt_issuer,
    )
    assert decoded["sub"] == "cognito-sub-abc"
    assert decoded["email"] == "jane@example.com"
    assert decoded["custom:role"] == "admin"
    assert decoded["custom:subscription_tier"] == "pro"
    assert decoded["user_id"] == str(user_id)
    assert decoded["token_use"] == "access"


def test_issue_access_token_defaults_role_and_tier() -> None:
    settings = _settings()
    token, _ = issue_access_token(
        user_id=uuid4(),
        cognito_sub="s",
        email="e@example.com",
        settings=settings,
    )
    decoded = jwt.decode(
        token,
        settings.jwt_signing_secret,
        algorithms=["HS256"],
        audience=settings.jwt_audience,
        issuer=settings.jwt_issuer,
    )
    assert decoded["custom:role"] == "user"
    assert decoded["custom:subscription_tier"] == "trial"


def test_issue_opaque_reset_token_pair_matches() -> None:
    plaintext, digest = issue_opaque_reset_token()
    assert len(plaintext) > 20
    assert len(digest) == 64  # SHA-256 hex length
    assert hash_secret(plaintext) == digest


def test_issue_opaque_reset_token_is_unique() -> None:
    a, _ = issue_opaque_reset_token()
    b, _ = issue_opaque_reset_token()
    assert a != b


@pytest.mark.parametrize("value", ["a", "a very long value " * 20])
def test_hash_secret_deterministic(value: str) -> None:
    assert hash_secret(value) == hash_secret(value)
