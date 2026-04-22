from functools import lru_cache
from typing import Literal

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    environment: Literal["dev", "sandbox", "prod", "test"] = "dev"
    log_level: str = "INFO"

    database_url: str
    database_pool_size: int = 10
    database_max_overflow: int = 20

    redis_url: str = ""

    aws_region: str = "us-east-1"
    aws_s3_bucket: str = "hireloop-dev-assets"
    aws_endpoint_url: str | None = None
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    aws_session_token: str | None = None

    cognito_user_pool_id: str
    cognito_client_id: str
    cognito_region: str
    cognito_jwks_url: str

    # In-house auth (feature flag: AUTH_MODE='cognito'|'custom').
    # Default is 'custom' — Cognito path stays available behind the flag for
    # rollback and for legacy test harnesses that mock CognitoJwtVerifier.
    auth_mode: str = "custom"
    jwt_signing_secret: str = "dev-secret-change-me"
    jwt_issuer: str = "hireloop"
    jwt_audience: str = "hireloop-users"
    jwt_access_ttl_minutes: int = 60
    jwt_refresh_ttl_days: int = 30
    app_base_url: str = "http://localhost:5173"

    # Email transport. 'log' writes to structlog (dev default). 'ses' uses
    # AWS SES via boto3 — requires the sender identity below to be verified
    # and the Lambda role to have ses:SendEmail on it.
    email_provider: str = "log"
    email_from: str = "no-reply@hireloop.xyz"
    email_from_name: str = "HireLoop"

    anthropic_api_key: str = ""
    # When set, the Anthropic SDK is pointed at this URL instead of
    # api.anthropic.com. Used to route LLM calls through the llm-bridge
    # (claude-subscription-backed) proxy. Leave empty to use the real API.
    anthropic_base_url: str = ""
    # Optional shared secret sent as x-bridge-secret header if llm-bridge
    # requires one. Ignored when anthropic_base_url is empty.
    anthropic_bridge_secret: str = ""
    google_api_key: str = ""
    # Provider model IDs — confirm against Anthropic / Google docs when upgrading.
    claude_model: str = "claude-sonnet-4-6"
    gemini_model: str = "gemini-2.0-flash"
    enable_prompt_caching: bool = True
    llm_classifier_timeout_s: float = 3.0
    llm_evaluation_timeout_s: float = 60.0
    llm_cv_optimize_timeout_s: float = 90.0

    agent_message_rate_limit_per_minute: int = 10
    agent_max_history_messages: int = 20

    # Billing (Phase 2b) — leave secrets empty in dev until Stripe is wired
    app_url: str = "http://localhost:5173"
    disable_paywall: bool = False
    trial_period_days: int = 3
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_pro_monthly: str = ""
    stripe_price_pro_annual: str = ""

    # Inngest + scanning limits (Phase 2c)
    inngest_event_key: str = ""
    inngest_signing_key: str = ""
    inngest_dev: bool = True
    feature_scan_scheduling: bool = False

    scan_max_listings_per_run: int = 500
    scan_board_rate_limit_reqs_per_sec: float = 1.0
    scan_l1_concurrency: int = 5
    batch_l2_concurrency: int = 10
    batch_l1_relevance_threshold: float = 0.5

    cors_origins: str = ""

    sentry_dsn: str = ""
    sentry_environment: str = "dev"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def cors_origins_list(self) -> list[str]:
        if not self.cors_origins.strip():
            return []
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_dev(self) -> bool:
        return self.environment == "dev"

    @property
    def is_test(self) -> bool:
        return self.environment == "test"

    @property
    def is_prod(self) -> bool:
        return self.environment == "prod"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
