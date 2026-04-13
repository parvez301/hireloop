import pytest

from hireloop.config import Settings


def test_settings_loads_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("COGNITO_USER_POOL_ID", "us-east-1_abc")
    monkeypatch.setenv("COGNITO_CLIENT_ID", "client123")
    monkeypatch.setenv("COGNITO_REGION", "us-east-1")
    monkeypatch.setenv("COGNITO_JWKS_URL", "https://example.com/jwks")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:5174")

    settings = Settings()  # type: ignore[call-arg]
    assert settings.environment == "test"
    assert settings.database_url == "postgresql+asyncpg://user:pass@localhost/db"
    assert settings.cors_origins_list == ["http://localhost:5173", "http://localhost:5174"]
    assert settings.is_dev is False
    assert settings.is_test is True


def test_settings_cors_origins_parsed_from_comma_list(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://x/x")
    monkeypatch.setenv("REDIS_URL", "redis://localhost")
    monkeypatch.setenv("COGNITO_USER_POOL_ID", "x")
    monkeypatch.setenv("COGNITO_CLIENT_ID", "x")
    monkeypatch.setenv("COGNITO_REGION", "x")
    monkeypatch.setenv("COGNITO_JWKS_URL", "https://x")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "x")
    monkeypatch.setenv("CORS_ORIGINS", "http://a.com, http://b.com")

    settings = Settings()  # type: ignore[call-arg]
    assert settings.cors_origins_list == ["http://a.com", "http://b.com"]
