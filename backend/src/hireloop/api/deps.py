from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hireloop.api.errors import AppError
from hireloop.config import get_settings
from hireloop.db import get_db
from hireloop.integrations.auth_jwt import JwtVerifier
from hireloop.integrations.auth_jwt import get_verifier as get_custom_verifier
from hireloop.integrations.cognito import CognitoJwtVerifier
from hireloop.integrations.cognito import get_verifier as get_cognito_verifier
from hireloop.models.user import User
from hireloop.services.auth import AuthUser, extract_auth_user
from hireloop.services.rate_limit import InMemoryRateLimiter, RateLimiter, SupportsRateCheck
from hireloop.services.subscription import ensure_subscription, is_entitled, utc_now

DbSession = Annotated[AsyncSession, Depends(get_db)]

get_db_session = get_db

_redis: Redis | None = None
_in_memory_message_limiter_singleton: InMemoryRateLimiter | None = None


async def get_redis_client() -> Redis:
    global _redis
    settings = get_settings()
    if not settings.redis_url.strip():
        raise RuntimeError("REDIS_URL is not set")
    if _redis is None:
        _redis = Redis.from_url(settings.redis_url, decode_responses=True)
    return _redis


async def get_redis_optional() -> Redis | None:
    if not get_settings().redis_url.strip():
        return None
    return await get_redis_client()


def _message_rate_limiter_from_redis(redis: Redis) -> RateLimiter:
    settings = get_settings()
    cap = settings.agent_message_rate_limit_per_minute
    return RateLimiter(
        redis,
        capacity=cap,
        refill_per_second=cap / 60.0,
        bucket_name="msg",
    )


def _get_in_memory_message_limiter() -> InMemoryRateLimiter:
    global _in_memory_message_limiter_singleton
    if _in_memory_message_limiter_singleton is None:
        settings = get_settings()
        cap = settings.agent_message_rate_limit_per_minute
        _in_memory_message_limiter_singleton = InMemoryRateLimiter(
            capacity=cap,
            refill_per_second=cap / 60.0,
            bucket_name="msg",
        )
    return _in_memory_message_limiter_singleton


async def get_message_rate_limiter(
    redis: Annotated[Redis | None, Depends(get_redis_optional)],
) -> SupportsRateCheck:
    if redis is None:
        return _get_in_memory_message_limiter()
    return _message_rate_limiter_from_redis(redis)


RedisClient = Annotated[Redis, Depends(get_redis_client)]

_DEV_BYPASS_TOKEN = "dev-bypass"

_DEV_BYPASS_USER = AuthUser(
    user_id="dev-local-user",
    cognito_sub="dev-local-sub",
    email="dev@hireloop.local",
    role="user",
    subscription_tier="pro",
)


def get_active_verifier() -> CognitoJwtVerifier | JwtVerifier:
    """Pick the JWT verifier implementation based on AUTH_MODE.

    'cognito' (default) keeps the Hosted-UI flow alive; 'custom' routes to
    the in-house HS256 verifier. Swap the env var to cutover an environment
    without a code deploy.
    """
    mode = get_settings().auth_mode.lower()
    if mode == "custom":
        return get_custom_verifier()
    return get_cognito_verifier()


async def get_auth_user(
    verifier: Annotated[
        CognitoJwtVerifier | JwtVerifier, Depends(get_active_verifier)
    ],
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
