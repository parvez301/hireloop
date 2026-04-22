"""In-house JWT verifier for the custom auth flow.

Mirrors the CognitoJwtVerifier contract: `.verify(token)` returns a claims
dict (including `sub`, `email`, `custom:role`, `custom:subscription_tier`) or
raises AppError(401). Signed HS256 with a secret from settings.

Custom tokens carry the same custom:* claim names Cognito used so the rest
of the app doesn't need to rebranch on token source.
"""

from typing import Any

from jose import jwt
from jose.exceptions import JWTError

from hireloop.api.errors import AppError
from hireloop.config import get_settings
from hireloop.logging import get_logger

log = get_logger("hireloop.auth_jwt")


class JwtVerifier:
    """Verifies HS256 JWTs issued by this backend."""

    def __init__(
        self,
        *,
        signing_secret: str,
        issuer: str,
        audience: str,
    ) -> None:
        self._signing_secret = signing_secret
        self._issuer = issuer
        self._audience = audience

    async def verify(self, token: str) -> dict[str, Any]:
        try:
            claims = jwt.decode(
                token,
                self._signing_secret,
                algorithms=["HS256"],
                audience=self._audience,
                issuer=self._issuer,
                options={"leeway": 30},
            )
        except JWTError as exc:
            try:
                unverified = jwt.get_unverified_claims(token)
            except JWTError:
                unverified = {}
            log.warning(
                "jwt_verify_failed",
                jose_error=str(exc),
                aud=unverified.get("aud"),
                iss=unverified.get("iss"),
                exp=unverified.get("exp"),
                iat=unverified.get("iat"),
                token_type=unverified.get("token_use"),
                expected_aud=self._audience,
                expected_iss=self._issuer,
            )
            raise AppError(401, "UNAUTHENTICATED", f"Invalid token: {exc}") from exc

        if claims.get("token_use") != "access":
            raise AppError(401, "UNAUTHENTICATED", "Token is not an access token")

        return claims


_verifier: JwtVerifier | None = None


def get_verifier() -> JwtVerifier:
    """Lazy-built verifier keyed off current settings."""
    global _verifier
    if _verifier is None:
        settings = get_settings()
        _verifier = JwtVerifier(
            signing_secret=settings.jwt_signing_secret,
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
        )
    return _verifier


def reset_verifier_cache() -> None:
    """Testing hook — force rebuild on next get_verifier() call."""
    global _verifier
    _verifier = None
