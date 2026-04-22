"""Password hashing service — argon2id.

Parameters tuned per the auth redesign handoff: time_cost=3, memory_cost=64 MiB,
parallelism=4. Bumping the cost is an opaque operation thanks to argon2's
self-describing hash format, so we re-hash on verify when the existing hash's
parameters fall behind the current defaults.
"""

from argon2 import PasswordHasher
from argon2.exceptions import (
    InvalidHashError,
    VerificationError,
    VerifyMismatchError,
)

# Module-scoped singleton — PasswordHasher is thread-safe and stateless.
_HASHER = PasswordHasher(
    time_cost=3,
    memory_cost=64 * 1024,  # 64 MiB
    parallelism=4,
)


class PasswordTooWeakError(ValueError):
    """Raised when a caller tries to hash a password below policy thresholds."""


MIN_PASSWORD_LENGTH = 10


def hash_password(plaintext: str) -> str:
    """Hash a plaintext password with argon2id; returns the encoded hash.

    The encoded hash includes the algorithm, cost params, salt, and tag — safe
    to store as a single opaque string in `users.password_hash`.
    """
    if plaintext is None or len(plaintext) < MIN_PASSWORD_LENGTH:
        raise PasswordTooWeakError(
            f"Password must be at least {MIN_PASSWORD_LENGTH} characters"
        )
    return _HASHER.hash(plaintext)


def verify_password(plaintext: str, encoded_hash: str) -> bool:
    """Return True iff plaintext matches the given encoded hash.

    Never raises on wrong password — returns False. Raises only on a hash we
    can't parse (caller's bug, not user input).
    """
    try:
        _HASHER.verify(encoded_hash, plaintext)
        return True
    except (VerifyMismatchError, VerificationError):
        return False
    except InvalidHashError as exc:
        raise ValueError(f"Stored hash is malformed: {exc}") from exc


def needs_rehash(encoded_hash: str) -> bool:
    """Whether an existing hash used weaker params than our current defaults.

    Call after a successful verify: if True, re-hash with `hash_password` and
    update the stored value so future logins benefit from the new cost.
    """
    try:
        return _HASHER.check_needs_rehash(encoded_hash)
    except InvalidHashError:
        return True
