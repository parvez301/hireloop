from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hireloop.api.errors import AppError
from hireloop.config import get_settings
from hireloop.db import get_db
from hireloop.integrations.cognito import CognitoJwtVerifier, get_verifier
from hireloop.models.user import User
from hireloop.services.auth import AuthUser, extract_auth_user
from hireloop.services.subscription import ensure_subscription, is_entitled, utc_now

DbSession = Annotated[AsyncSession, Depends(get_db)]

get_db_session = get_db

_redis: Redis | None = None


async def get_redis_client() -> Redis:
    global _redis
    if _redis is None:
        _redis = Redis.from_url(get_settings().redis_url, decode_responses=True)
    return _redis


RedisClient = Annotated[Redis, Depends(get_redis_client)]


_DEV_BYPASS_TOKEN = "dev-bypass"

_DEV_BYPASS_USER = AuthUser(
    user_id="dev-local-user",
    cognito_sub="dev-local-sub",
    email="dev@hireloop.local",
    role="user",
    subscription_tier="pro",
)


async def get_auth_user(
    verifier: Annotated[CognitoJwtVerifier, Depends(get_verifier)],
    authorization: Annotated[str | None, Header()] = None,
) -> AuthUser:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AppError(401, "UNAUTHENTICATED", "Missing or invalid Authorization header")

    token = authorization.split(" ", 1)[1]

    settings = get_settings()
    if settings.environment == "dev" and token == _DEV_BYPASS_TOKEN:
        return _DEV_BYPASS_USER

    claims = await verifier.verify(token)
    return extract_auth_user(claims)


CurrentUser = Annotated[AuthUser, Depends(get_auth_user)]


async def get_current_db_user(
    auth: CurrentUser,
    db: DbSession,
) -> User:
    try:
        user_uuid = UUID(auth.user_id)
    except ValueError:
        user_uuid = None

    user: User | None = None
    if user_uuid is not None:
        user = await db.get(User, user_uuid)

    if user is None:
        result = await db.execute(select(User).where(User.cognito_sub == auth.cognito_sub))
        user = result.scalar_one_or_none()

    if user is None:
        user = User(
            cognito_sub=auth.cognito_sub,
            email=auth.email,
            name=auth.email.split("@")[0] or "User",
        )
        db.add(user)
        await db.flush()

    return user


CurrentDbUser = Annotated[User, Depends(get_current_db_user)]


async def require_entitled_user(
    user: CurrentDbUser,
    session: DbSession,
) -> User:
    settings = get_settings()
    if settings.disable_paywall:
        return user
    sub = await ensure_subscription(session, user.id, settings)
    if not is_entitled(sub, utc_now()):
        raise AppError(
            403,
            "TRIAL_EXPIRED",
            "Your trial has ended. Subscribe to continue using HireLoop.",
        )
    return user


EntitledDbUser = Annotated[User, Depends(require_entitled_user)]
