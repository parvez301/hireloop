from dataclasses import dataclass
from typing import Any


@dataclass
class AuthUser:
    user_id: str
    cognito_sub: str
    email: str
    role: str
    subscription_tier: str


def extract_auth_user(claims: dict[str, Any]) -> AuthUser:
    uid = claims.get("custom:user_id")
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
