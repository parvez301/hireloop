"""Access + refresh token issuance for the in-house auth flow.

Access tokens are short-lived JWTs carrying the same claim shape the app
already reads from Cognito (`sub`, `email`, `custom:role`, `custom:subscription_tier`).
Refresh tokens are opaque URL-safe random strings; we persist a SHA-256 hash
so compromised DB rows can't be replayed against the token endpoint.
"""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from jose import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hireloop.config import Settings, get_settings
from hireloop.models.auth import AuthRefreshToken


@dataclass(frozen=True)
class IssuedTokens:
    id_token: str
    refresh_token: str
    expires_in: int  # seconds until id_token expiry


def _now() -> datetime:
    return datetime.now(UTC)


def _hash_refresh(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _build_access_claims(
    *,
    user_id: UUID,
    cognito_sub: str,
    email: str,
    role: str,
    subscription_tier: str,
    settings: Settings,
) -> dict[str, Any]:
    now = _now()
    expires_at = now + timedelta(minutes=settings.jwt_access_ttl_minutes)
    return {
        "sub": cognito_sub,
        "user_id": str(user_id),
        "email": email,
        "custom:role": role,
        "custom:subscription_tier": subscription_tier,
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
        "token_use": "access",
    }


def issue_access_token(
    *,
    user_id: UUID,
    cognito_sub: str,
    email: str,
    role: str = "user",
    subscription_tier: str = "trial",
    settings: Settings | None = None,
) -> tuple[str, int]:
    """Sign and return (access_token, expires_in_seconds)."""
    s = settings or get_settings()
    claims = _build_access_claims(
        user_id=user_id,
        cognito_sub=cognito_sub,
        email=email,
        role=role,
        subscription_tier=subscription_tier,
        settings=s,
    )
    token = jwt.encode(claims, s.jwt_signing_secret, algorithm="HS256")
    return token, s.jwt_access_ttl_minutes * 60


async def issue_refresh_token(
    db: AsyncSession,
    *,
    user_id: UUID,
    user_agent: str | None = None,
    ip: str | None = None,
    settings: Settings | None = None,
) -> str:
    """Mint a new refresh token, persist its hash, return the plaintext.

    Plaintext is the ONLY time the caller sees the token — the DB stores only
    a SHA-256 digest so compromised rows can't be replayed.
    """
    s = settings or get_settings()
    plaintext = secrets.token_urlsafe(48)  # 64 chars of url-safe entropy
    row = AuthRefreshToken(
        id=uuid4(),
        user_id=user_id,
        token_hash=_hash_refresh(plaintext),
        expires_at=_now() + timedelta(days=s.jwt_refresh_ttl_days),
        user_agent=user_agent,
        ip=ip,
    )
    db.add(row)
    await db.flush()
    return plaintext


async def find_live_refresh_row(
    db: AsyncSession,
    *,
    refresh_token: str,
) -> AuthRefreshToken | None:
    """Look up a non-revoked, non-expired refresh token by its plaintext."""
    digest = _hash_refresh(refresh_token)
    stmt = select(AuthRefreshToken).where(AuthRefreshToken.token_hash == digest)
    row = (await db.execute(stmt)).scalar_one_or_none()
    if row is None:
        return None
    if row.revoked_at is not None:
        return None
    if row.expires_at <= _now():
        return None
    return row


async def revoke_refresh_token(
    db: AsyncSession,
    *,
    refresh_token: str,
) -> None:
    """Mark a refresh token revoked; silently ignore if not present."""
    row = await find_live_refresh_row(db, refresh_token=refresh_token)
    if row is not None:
        row.revoked_at = _now()
        await db.flush()


def issue_opaque_reset_token() -> tuple[str, str]:
    """Return (plaintext, sha256_hex) for a password-reset token."""
    plaintext = secrets.token_urlsafe(32)
    return plaintext, _hash_refresh(plaintext)


def hash_secret(plaintext: str) -> str:
    """Public alias for the SHA-256 helper — used by code/token stores."""
    return _hash_refresh(plaintext)
