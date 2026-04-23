"""Dev-only internal endpoints — guarded by a shared secret header.

Only mounted when `settings.environment == "dev"`. Every route requires
`x-dev-secret` to match `settings.dev_internal_secret`. These endpoints
are test-harness helpers, NOT user-facing surface.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, Header, Response, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hireloop.api.deps import DbSession
from hireloop.api.errors import AppError
from hireloop.config import get_settings
from hireloop.models.user import User
from hireloop.services.passwords import hash_password

router = APIRouter(prefix="/_internal", tags=["internal"], include_in_schema=False)


def _guard(header_value: str | None) -> None:
    settings = get_settings()
    if settings.environment != "dev":
        raise AppError(404, "NOT_FOUND", "Not Found")
    expected = settings.dev_internal_secret
    if not expected or header_value != expected:
        raise AppError(401, "UNAUTHENTICATED", "Invalid dev secret")


class EnsureSmokeUserRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=10, max_length=256)


@router.post("/ensure_smoke_user", status_code=status.HTTP_204_NO_CONTENT)
async def ensure_smoke_user(
    body: EnsureSmokeUserRequest,
    db: DbSession,
    x_dev_secret: str | None = Header(default=None, alias="x-dev-secret"),
) -> Response:
    """Idempotently create or update a verified smoke-test user.

    On conflict the existing row's password_hash + email_verified_at are
    overwritten so the smoke workflow can rotate DEV_SMOKE_PASSWORD without
    a manual DB step.
    """
    _guard(x_dev_secret)

    row = await _upsert_smoke_user(db, email=body.email, password=body.password)
    _ = row  # committed by DbSession wrapper
    return Response(status_code=status.HTTP_204_NO_CONTENT)


async def _upsert_smoke_user(
    db: AsyncSession, *, email: str, password: str
) -> User:
    existing = (
        await db.execute(select(User).where(User.email == email))
    ).scalar_one_or_none()
    password_hash = hash_password(password)
    now = datetime.now(UTC)
    if existing is not None:
        existing.password_hash = password_hash
        existing.email_verified_at = now
        await db.flush()
        return existing

    user = User(
        id=uuid4(),
        cognito_sub=f"smoke-{uuid4()}",
        email=email,
        name=email.split("@")[0],
        password_hash=password_hash,
        email_verified_at=now,
    )
    db.add(user)
    await db.flush()
    return user
