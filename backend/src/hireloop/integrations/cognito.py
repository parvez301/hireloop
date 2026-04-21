from functools import lru_cache
from typing import Any

import httpx
from jose import jwk, jwt
from jose.exceptions import JWTError

from hireloop.api.errors import AppError
from hireloop.config import get_settings
from hireloop.logging import get_logger

log = get_logger("hireloop.cognito")


class CognitoJwtVerifier:
    """Verifies Cognito-issued JWTs using the pool's JWKS."""

    def __init__(self, jwks_url: str, client_id: str, region: str, user_pool_id: str) -> None:
        self.jwks_url = jwks_url
        self.client_id = client_id
        self.issuer = f"https://cognito-idp.{region}.amazonaws.com/{user_pool_id}"
        self._jwks: dict[str, Any] | None = None

    async def _load_jwks(self) -> dict[str, Any]:
        if self._jwks is None:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(self.jwks_url)
                response.raise_for_status()
                self._jwks = response.json()
        return self._jwks

    async def verify(self, token: str) -> dict[str, Any]:
        try:
            header = jwt.get_unverified_header(token)
        except JWTError as e:
            raise AppError(401, "UNAUTHENTICATED", "Invalid token header") from e

        kid = header.get("kid")
        if not kid:
            raise AppError(401, "UNAUTHENTICATED", "Token missing kid")

        jwks = await self._load_jwks()
        key_data = next((k for k in jwks["keys"] if k["kid"] == kid), None)
        if key_data is None:
            raise AppError(401, "UNAUTHENTICATED", "Unknown signing key")

        public_key = jwk.construct(key_data)

        try:
            claims = jwt.decode(
                token,
                public_key.to_pem().decode(),
                algorithms=[key_data["alg"]],
                audience=self.client_id,
                issuer=self.issuer,
                options={"leeway": 30, "verify_at_hash": False},
            )
        except JWTError as e:
            try:
                unverified = jwt.get_unverified_claims(token)
            except JWTError:
                unverified = {}
            log.warning(
                "cognito_verify_failed",
                jose_error=str(e),
                token_use=unverified.get("token_use"),
                aud=unverified.get("aud"),
                iss=unverified.get("iss"),
                exp=unverified.get("exp"),
                iat=unverified.get("iat"),
                expected_aud=self.client_id,
                expected_iss=self.issuer,
                kid=kid,
                alg=key_data.get("alg"),
            )
            raise AppError(401, "UNAUTHENTICATED", f"Invalid token: {e}") from e

        return claims


@lru_cache(maxsize=1)
def get_verifier() -> CognitoJwtVerifier:
    settings = get_settings()
    return CognitoJwtVerifier(
        jwks_url=settings.cognito_jwks_url,
        client_id=settings.cognito_client_id,
        region=settings.cognito_region,
        user_pool_id=settings.cognito_user_pool_id,
    )
