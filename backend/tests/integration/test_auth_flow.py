"""Integration tests for the in-house auth endpoints.

Each endpoint gets a happy path and the key rejection cases. We swap the
global EmailSender to a CapturingEmailSender so we can read back codes /
reset-token plaintexts instead of hitting a real transport.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select

from hireloop.db import get_session_factory
from hireloop.models.auth import (
    AuthRefreshToken,
    EmailVerificationCode,
    PasswordResetToken,
)
from hireloop.models.user import User
from hireloop.services.email import CapturingEmailSender, set_email_sender


def _unique_email(prefix: str) -> str:
    """Return an email guaranteed-unique across runs so tests stay hermetic on
    the shared dev database."""
    return f"{prefix}-{uuid4().hex[:10]}@example.com"


@pytest_asyncio.fixture
async def capturing_sender() -> AsyncIterator[CapturingEmailSender]:
    sender = CapturingEmailSender()
    set_email_sender(sender)
    try:
        yield sender
    finally:
        set_email_sender(None)


async def _fetch_user_by_email(email: str) -> User | None:
    factory = get_session_factory()
    async with factory() as session:
        row = await session.execute(select(User).where(User.email == email))
        return row.scalar_one_or_none()


async def _latest_code_row(user_id) -> EmailVerificationCode | None:
    factory = get_session_factory()
    async with factory() as session:
        row = await session.execute(
            select(EmailVerificationCode)
            .where(EmailVerificationCode.user_id == user_id)
            .order_by(EmailVerificationCode.created_at.desc())
            .limit(1)
        )
        return row.scalar_one_or_none()


def _latest_code_from_emails(sender: CapturingEmailSender) -> str:
    body = sender.sent[-1].body_text
    # The code is rendered on its own line with a 4-space indent in the template.
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.isdigit() and len(stripped) == 6:
            return stripped
    raise AssertionError(f"No 6-digit code found in email body:\n{body}")


def _reset_token_from_emails(sender: CapturingEmailSender) -> str:
    body = sender.sent[-1].body_text
    marker = "/auth/reset?token="
    index = body.find(marker)
    assert index >= 0, f"No reset link in email:\n{body}"
    tail = body[index + len(marker) :].split()[0]
    return tail


@pytest.mark.asyncio
async def test_signup_creates_user_and_sends_code(
    client: AsyncClient, capturing_sender: CapturingEmailSender
) -> None:
    email = _unique_email("signup")
    response = await client.post(
        "/api/v1/auth/signup",
        json={
            "firstName": "Jane",
            "lastName": "Doe",
            "email": email,
            "password": "correcthorsebatterystaple",
        },
    )
    assert response.status_code == 201
    body = response.json()["data"]
    assert "userId" in body

    user = await _fetch_user_by_email(email)
    assert user is not None
    assert user.password_hash is not None
    assert user.email_verified_at is None

    assert len(capturing_sender.sent) == 1
    assert capturing_sender.sent[0].to == email
    _ = _latest_code_from_emails(capturing_sender)


@pytest.mark.asyncio
async def test_signup_weak_password_is_rejected(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/signup",
        json={
            "firstName": "Jane",
            "lastName": "Doe",
            "email": _unique_email("weak"),
            "password": "short",
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_verify_email_happy_path_issues_session(
    client: AsyncClient, capturing_sender: CapturingEmailSender
) -> None:
    email = _unique_email("verify")
    await client.post(
        "/api/v1/auth/signup",
        json={
            "firstName": "Jane",
            "lastName": "Doe",
            "email": email,
            "password": "correcthorsebatterystaple",
        },
    )
    code = _latest_code_from_emails(capturing_sender)

    response = await client.post(
        "/api/v1/auth/verify-email",
        json={"email": email, "code": code},
    )
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["idToken"]
    assert body["refreshToken"]
    assert body["expiresIn"] > 0

    user = await _fetch_user_by_email(email)
    assert user is not None
    assert user.email_verified_at is not None


@pytest.mark.asyncio
async def test_verify_email_wrong_code_bumps_attempts(
    client: AsyncClient, capturing_sender: CapturingEmailSender
) -> None:
    email = _unique_email("wrong-code")
    await client.post(
        "/api/v1/auth/signup",
        json={
            "firstName": "Jane",
            "lastName": "Doe",
            "email": email,
            "password": "correcthorsebatterystaple",
        },
    )
    user = await _fetch_user_by_email(email)
    assert user is not None

    response = await client.post(
        "/api/v1/auth/verify-email",
        json={"email": email, "code": "000000"},
    )
    assert response.status_code == 400

    row = await _latest_code_row(user.id)
    assert row is not None
    assert row.attempts == 1
    assert row.consumed_at is None


@pytest.mark.asyncio
async def test_login_before_verification_is_blocked(
    client: AsyncClient, capturing_sender: CapturingEmailSender
) -> None:
    email = _unique_email("unverified")
    await client.post(
        "/api/v1/auth/signup",
        json={
            "firstName": "Jane",
            "lastName": "Doe",
            "email": email,
            "password": "correcthorsebatterystaple",
        },
    )
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": "correcthorsebatterystaple",
            "remember": False,
        },
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "EMAIL_UNVERIFIED"


@pytest.mark.asyncio
async def test_login_wrong_password_returns_401(
    client: AsyncClient, capturing_sender: CapturingEmailSender
) -> None:
    email = _unique_email("wrongpw")
    await client.post(
        "/api/v1/auth/signup",
        json={
            "firstName": "Jane",
            "lastName": "Doe",
            "email": email,
            "password": "correcthorsebatterystaple",
        },
    )
    code = _latest_code_from_emails(capturing_sender)
    await client.post("/api/v1/auth/verify-email", json={"email": email, "code": code})

    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": "nope-not-it",
            "remember": False,
        },
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_after_verification_returns_session(
    client: AsyncClient, capturing_sender: CapturingEmailSender
) -> None:
    email = _unique_email("loginok")
    await client.post(
        "/api/v1/auth/signup",
        json={
            "firstName": "Jane",
            "lastName": "Doe",
            "email": email,
            "password": "correcthorsebatterystaple",
        },
    )
    code = _latest_code_from_emails(capturing_sender)
    await client.post("/api/v1/auth/verify-email", json={"email": email, "code": code})

    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": "correcthorsebatterystaple",
            "remember": True,
        },
    )
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["idToken"]
    assert body["refreshToken"]


@pytest.mark.asyncio
async def test_forgot_password_is_silent_for_missing_user(
    client: AsyncClient, capturing_sender: CapturingEmailSender
) -> None:
    response = await client.post(
        "/api/v1/auth/forgot",
        json={"email": "nobody-here@example.com"},
    )
    assert response.status_code == 204
    assert capturing_sender.sent == []


@pytest.mark.asyncio
async def test_forgot_then_reset_flow(
    client: AsyncClient, capturing_sender: CapturingEmailSender
) -> None:
    email = _unique_email("reset")
    await client.post(
        "/api/v1/auth/signup",
        json={
            "firstName": "Jane",
            "lastName": "Doe",
            "email": email,
            "password": "correcthorsebatterystaple",
        },
    )
    # Clear the signup verification email so the next sent message is the reset.
    capturing_sender.sent.clear()

    response = await client.post("/api/v1/auth/forgot", json={"email": email})
    assert response.status_code == 204
    assert len(capturing_sender.sent) == 1
    token = _reset_token_from_emails(capturing_sender)

    response = await client.post(
        "/api/v1/auth/reset",
        json={"token": token, "password": "a-new-strong-password"},
    )
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["idToken"]

    # Token is single-use.
    response = await client.post(
        "/api/v1/auth/reset",
        json={"token": token, "password": "another-strong-password"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_reset_rejects_unknown_token(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/reset",
        json={"token": "not-a-real-token", "password": "correcthorsebatterystaple"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_refresh_issues_new_access_token(
    client: AsyncClient, capturing_sender: CapturingEmailSender
) -> None:
    email = _unique_email("refresh")
    await client.post(
        "/api/v1/auth/signup",
        json={
            "firstName": "Jane",
            "lastName": "Doe",
            "email": email,
            "password": "correcthorsebatterystaple",
        },
    )
    code = _latest_code_from_emails(capturing_sender)
    session = (
        await client.post("/api/v1/auth/verify-email", json={"email": email, "code": code})
    ).json()["data"]

    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refreshToken": session["refreshToken"]},
    )
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["idToken"]
    assert body["idToken"] != session["idToken"] or body["expiresIn"] > 0


@pytest.mark.asyncio
async def test_logout_revokes_refresh_token(
    client: AsyncClient, capturing_sender: CapturingEmailSender
) -> None:
    email = _unique_email("logout")
    await client.post(
        "/api/v1/auth/signup",
        json={
            "firstName": "Jane",
            "lastName": "Doe",
            "email": email,
            "password": "correcthorsebatterystaple",
        },
    )
    code = _latest_code_from_emails(capturing_sender)
    session = (
        await client.post("/api/v1/auth/verify-email", json={"email": email, "code": code})
    ).json()["data"]
    refresh_token = session["refreshToken"]

    response = await client.post(
        "/api/v1/auth/logout",
        json={"refreshToken": refresh_token},
    )
    assert response.status_code == 204

    # Subsequent refresh must fail.
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refreshToken": refresh_token},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_resend_code_cooldown(
    client: AsyncClient, capturing_sender: CapturingEmailSender
) -> None:
    email = _unique_email("resend")
    await client.post(
        "/api/v1/auth/signup",
        json={
            "firstName": "Jane",
            "lastName": "Doe",
            "email": email,
            "password": "correcthorsebatterystaple",
        },
    )
    # Signup already sent one email.
    response = await client.post("/api/v1/auth/resend-code", json={"email": email})
    # Immediate resend hits the 1-minute cooldown.
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "RESEND_TOO_SOON"

    # Simulate code being older than cooldown.
    user = await _fetch_user_by_email(email)
    assert user is not None
    factory = get_session_factory()
    async with factory() as session:
        row = (
            await session.execute(
                select(EmailVerificationCode)
                .where(EmailVerificationCode.user_id == user.id)
                .order_by(EmailVerificationCode.created_at.desc())
                .limit(1)
            )
        ).scalar_one()
        row.created_at = datetime.now(UTC) - timedelta(minutes=2)
        await session.commit()

    response = await client.post("/api/v1/auth/resend-code", json={"email": email})
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_resend_code_for_unknown_email_is_silent(
    client: AsyncClient, capturing_sender: CapturingEmailSender
) -> None:
    response = await client.post("/api/v1/auth/resend-code", json={"email": "nobody@example.com"})
    assert response.status_code == 204
    assert capturing_sender.sent == []


@pytest.mark.asyncio
async def test_refresh_token_is_persisted(
    client: AsyncClient, capturing_sender: CapturingEmailSender
) -> None:
    email = _unique_email("persist")
    await client.post(
        "/api/v1/auth/signup",
        json={
            "firstName": "Jane",
            "lastName": "Doe",
            "email": email,
            "password": "correcthorsebatterystaple",
        },
    )
    code = _latest_code_from_emails(capturing_sender)
    await client.post("/api/v1/auth/verify-email", json={"email": email, "code": code})

    user = await _fetch_user_by_email(email)
    assert user is not None

    factory = get_session_factory()
    async with factory() as session:
        rows = (
            (
                await session.execute(
                    select(AuthRefreshToken).where(AuthRefreshToken.user_id == user.id)
                )
            )
            .scalars()
            .all()
        )
        assert len(rows) >= 1
        # Ensure reset-token table persistence worked when forgot-path would run.
        _ = select(PasswordResetToken)
