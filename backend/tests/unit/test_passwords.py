"""Unit tests for services/passwords.py."""

import pytest

from hireloop.services.passwords import (
    PasswordTooWeakError,
    hash_password,
    needs_rehash,
    verify_password,
)


def test_hash_password_returns_argon2id_encoding() -> None:
    encoded = hash_password("correcthorsebatterystaple")
    # argon2-cffi's PasswordHasher defaults to argon2id with the $argon2id$ prefix.
    assert encoded.startswith("$argon2id$")


def test_verify_password_accepts_correct_plaintext() -> None:
    encoded = hash_password("correcthorsebatterystaple")
    assert verify_password("correcthorsebatterystaple", encoded) is True


def test_verify_password_rejects_incorrect_plaintext() -> None:
    encoded = hash_password("correcthorsebatterystaple")
    assert verify_password("Tr0ub4dor&3", encoded) is False


def test_hash_produces_different_encodings_for_same_plaintext() -> None:
    """argon2 salts per-call, so the same plaintext must yield distinct hashes."""
    a = hash_password("correcthorsebatterystaple")
    b = hash_password("correcthorsebatterystaple")
    assert a != b


def test_hash_password_rejects_short_passwords() -> None:
    with pytest.raises(PasswordTooWeakError):
        hash_password("short")


def test_hash_password_rejects_none() -> None:
    with pytest.raises(PasswordTooWeakError):
        hash_password(None)  # type: ignore[arg-type]


def test_needs_rehash_is_false_for_current_params() -> None:
    encoded = hash_password("correcthorsebatterystaple")
    assert needs_rehash(encoded) is False


def test_needs_rehash_is_true_for_malformed_hash() -> None:
    # A malformed stored hash should be treated as needing rehash (not crash).
    assert needs_rehash("this-is-not-an-argon2-hash") is True


def test_verify_raises_value_error_on_malformed_stored_hash() -> None:
    with pytest.raises(ValueError):
        verify_password("whatever", "this-is-not-an-argon2-hash")
