"""Auth domain logic.

Contains both:
- `extract_auth_user(claims)` — the claims-unpacker used by every HTTP dep.
  Kept for backwards compatibility with the Cognito path and everywhere in
  integration tests.
- The in-house auth flows (`signup`, `login`, `verify_email`, `resend_code`,
  `forgot_password`, `reset_password`, `refresh`, `logout`) — exposed to the
  FastAPI router in api/auth.py.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hireloop.api.errors import AppError
from hireloop.config import Settings, get_settings
from hireloop.models.auth import (
    AuthRefreshToken,
    EmailVerificationCode,
    PasswordResetToken,
)
from hireloop.models.user import User
from hireloop.services.email import (
    EmailSender,
    get_email_sender,
    render_password_reset_email,
    render_verification_code_email,
)
from hireloop.services.passwords import (
    PasswordTooWeakError,
    hash_password,
    needs_rehash,
    verify_password,
)
from hireloop.services.tokens import (
    hash_secret,
    issue_access_token,
    issue_opaque_reset_token,
    issue_refresh_token,
    revoke_refresh_token,
)


# ---------------------------------------------------------------------------
# Existing claims-unpacker (Cognito-compatible shape) — don't break callers.
# ---------------------------------------------------------------------------


@dataclass
class AuthUser:
    user_id: str
    cognito_sub: str
    email: str
    role: str
    subscription_tier: str


def extract_auth_user(claims: dict[str, Any]) -> AuthUser:
    uid = claims.get("custom:user_id") or claims.get("user_id")
    if isinstance(uid, str) and uid.strip():
        user_id = uid.strip()
    else:
        user_id = claims["sub"]
    return AuthUser(
        user_id=user_id,
        cognito_sub=claims["sub"],
        email=claims.get("email", ""),
        role=claims.get("custom:role", "user"),
        subscription_tier=claims.get("custom:subscription_tier", "trial"),
    )


# ---------------------------------------------------------------------------
# In-house auth flows.
# ---------------------------------------------------------------------------

CODE_TTL = timedelta(minutes=10)
CODE_MAX_ATTEMPTS = 5
CODE_RESEND_COOLDOWN = timedelta(minutes=1)
RESET_TOKEN_TTL = timedelta(minutes=30)


def _now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True)
class AuthSession:
    id_token: str
    refresh_token: str
    expires_in: int


@dataclass(frozen=True)
class RefreshedAccess:
    id_token: str
    expires_in: int


def _six_digit_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


async def _user_by_email(db: AsyncSession, email: str) -> User | None:
    stmt = select(User).where(User.email == email)
    return (await db.execute(stmt)).scalar_one_or_none()


async def _issue_session(
    db: AsyncSession,
    user: User,
    *,
    user_agent: str | None,
    ip: str | None,
    settings: Settings,
) -> AuthSession:
    access_token, expires_in = issue_access_token(
        user_id=user.id,
        cognito_sub=user.cognito_sub,
        email=user.email,
        settings=settings,
    )
    refresh = await issue_refresh_token(
        db, user_id=user.id, user_agent=user_agent, ip=ip, settings=settings
    )
    return AuthSession(
        id_token=access_token, refresh_token=refresh, expires_in=expires_in
    )


async def _latest_live_code(
    db: AsyncSession, user_id: UUID
) -> EmailVerificationCode | None:
    stmt = (
        select(EmailVerificationCode)
        .where(
            EmailVerificationCode.user_id == user_id,
            EmailVerificationCode.consumed_at.is_(None),
        )
        .order_by(EmailVerificationCode.created_at.desc())
        .limit(1)
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def _create_and_send_code(
    db: AsyncSession,
    user: User,
    *,
    email_sender: EmailSender,
) -> None:
    code = _six_digit_code()
    row = EmailVerificationCode(
        id=uuid4(),
        user_id=user.id,
        code_hash=hash_secret(code),
        expires_at=_now() + CODE_TTL,
        attempts=0,
        created_at=_now(),
    )
    db.add(row)
    await db.flush()
    message = render_verification_code_email(code=code, email=user.email)
    await email_sender.send(message)


async def signup(
    db: AsyncSession,
    *,
    first_name: str,
    last_name: str,
    email: str,
    password: str,
    email_sender: EmailSender | None = None,
) -> UUID:
    """Create a pending-verification user, send the 6-digit code.

    On existing email we return the same shape with no side effects so the
    response is indistinguishable from a fresh signup (reduced enumeration).
    """
    sender = email_sender or get_email_sender()
    try:
        password_hash = hash_password(password)
    except PasswordTooWeakError as exc:
        raise AppError(422, "VALIDATION_ERROR", str(exc)) from exc

    existing = await _user_by_email(db, email)
    if existing is not None:
        return existing.id

    user = User(
        id=uuid4(),
        cognito_sub=f"custom-{uuid4()}",
        email=email,
        name=f"{first_name} {last_name}".strip() or email,
        password_hash=password_hash,
        email_verified_at=None,
    )
    db.add(user)
    await db.flush()

    await _create_and_send_code(db, user, email_sender=sender)
    return user.id


async def login(
    db: AsyncSession,
    *,
    email: str,
    password: str,
    user_agent: str | None = None,
    ip: str | None = None,
    settings: Settings | None = None,
) -> AuthSession:
    s = settings or get_settings()
    user = await _user_by_email(db, email)
    generic = AppError(401, "UNAUTHENTICATED", "Invalid email or password")
    if user is None or user.password_hash is None:
        raise generic
    if not verify_password(password, user.password_hash):
        raise generic
    if user.email_verified_at is None:
        raise AppError(403, "EMAIL_UNVERIFIED", "Verify your email to continue")
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)
    return await _issue_session(
        db, user, user_agent=user_agent, ip=ip, settings=s
    )


async def verify_email(
    db: AsyncSession,
    *,
    email: str,
    code: str,
    user_agent: str | None = None,
    ip: str | None = None,
    settings: Settings | None = None,
) -> AuthSession:
    s = settings or get_settings()
    user = await _user_by_email(db, email)
    invalid = AppError(400, "INVALID_CODE", "That code isn't valid")
    if user is None:
        raise invalid

    row = await _latest_live_code(db, user.id)
    if row is None:
        raise invalid
    if row.expires_at <= _now():
        raise AppError(400, "CODE_EXPIRED", "That code has expired")
    if row.attempts >= CODE_MAX_ATTEMPTS:
        raise AppError(
            429, "TOO_MANY_ATTEMPTS", "Too many attempts — request a new code"
        )
    row.attempts += 1
    if hash_secret(code) != row.code_hash:
        await db.flush()
        raise invalid

    row.consumed_at = _now()
    user.email_verified_at = _now()
    await db.flush()
    return await _issue_session(
        db, user, user_agent=user_agent, ip=ip, settings=s
    )


async def resend_code(
    db: AsyncSession,
    *,
    email: str,
    email_sender: EmailSender | None = None,
) -> None:
    sender = email_sender or get_email_sender()
    user = await _user_by_email(db, email)
    if user is None or user.email_verified_at is not None:
        return

    latest = await _latest_live_code(db, user.id)
    if latest is not None and (_now() - latest.created_at) < CODE_RESEND_COOLDOWN:
        raise AppError(
            429,
            "RESEND_TOO_SOON",
            "Please wait a moment before requesting another code",
        )
    await _create_and_send_code(db, user, email_sender=sender)


async def forgot_password(
    db: AsyncSession,
    *,
    email: str,
    email_sender: EmailSender | None = None,
) -> None:
    """Always a no-op externally — never leak whether an email is registered."""
    sender = email_sender or get_email_sender()
    user = await _user_by_email(db, email)
    if user is None:
        return

    plaintext, digest = issue_opaque_reset_token()
    row = PasswordResetToken(
        id=uuid4(),
        user_id=user.id,
        token_hash=digest,
        expires_at=_now() + RESET_TOKEN_TTL,
        created_at=_now(),
    )
    db.add(row)
    await db.flush()
    message = render_password_reset_email(email=user.email, token=plaintext)
    await sender.send(message)


async def reset_password(
    db: AsyncSession,
    *,
    token: str,
    password: str,
    user_agent: str | None = None,
    ip: str | None = None,
    settings: Settings | None = None,
) -> AuthSession:
    s = settings or get_settings()
    digest = hash_secret(token)
    stmt = select(PasswordResetToken).where(PasswordResetToken.token_hash == digest)
    row = (await db.execute(stmt)).scalar_one_or_none()
    invalid = AppError(400, "INVALID_TOKEN", "That reset link isn't valid")
    if row is None or row.consumed_at is not None:
        raise invalid
    if row.expires_at <= _now():
        raise AppError(400, "TOKEN_EXPIRED", "Reset link has expired")

    user = (
        await db.execute(select(User).where(User.id == row.user_id))
    ).scalar_one_or_none()
    if user is None:
        raise invalid

    try:
        user.password_hash = hash_password(password)
    except PasswordTooWeakError as exc:
        raise AppError(422, "VALIDATION_ERROR", str(exc)) from exc
    # Resetting the password is an implicit verification of inbox ownership.
    if user.email_verified_at is None:
        user.email_verified_at = _now()
    row.consumed_at = _now()
    await db.flush()
    return await _issue_session(
        db, user, user_agent=user_agent, ip=ip, settings=s
    )


async def refresh(
    db: AsyncSession,
    *,
    refresh_token: str,
    settings: Settings | None = None,
) -> RefreshedAccess:
    s = settings or get_settings()
    digest = hash_secret(refresh_token)
    stmt = select(AuthRefreshToken).where(AuthRefreshToken.token_hash == digest)
    row = (await db.execute(stmt)).scalar_one_or_none()
    invalid = AppError(401, "INVALID_REFRESH", "Refresh token is not valid")
    if row is None or row.revoked_at is not None or row.expires_at <= _now():
        raise invalid

    user = (
        await db.execute(select(User).where(User.id == row.user_id))
    ).scalar_one_or_none()
    if user is None:
        raise invalid

    access_token, expires_in = issue_access_token(
        user_id=user.id,
        cognito_sub=user.cognito_sub,
        email=user.email,
        settings=s,
    )
    return RefreshedAccess(id_token=access_token, expires_in=expires_in)


async def logout(db: AsyncSession, *, refresh_token: str) -> None:
    await revoke_refresh_token(db, refresh_token=refresh_token)
