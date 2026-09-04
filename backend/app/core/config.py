"""
Application configuration.

Loaded from environment variables (see .env.example at repo root for the
full list, per ENVIRONMENT_CONFIG.md). Phase 0 only *uses* the App/Database/
JWT/CORS values below; the remaining variables (Redis, Ollama, Groq, ESP,
Stripe, etc.) are declared here so the settings object is a single source of
truth from day one, but they are not read by any Phase 0 code path.
"""
from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    # --- App ---
    APP_ENV: Literal["development", "test", "production"] = "development"
    APP_SECRET_KEY: str = Field(..., min_length=1)
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 14

    # --- Database ---
    DATABASE_URL: str
    DATABASE_URL_TEST: str | None = None

    # --- Redis / Celery (declared now, used from Phase 1 onward) ---
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # --- LLM: Ollama / remote OpenAI-compatible gateway ---
    # LLM_LOCAL=true  → talk to local Ollama (OLLAMA_BASE_URL, default localhost)
    # LLM_LOCAL=false → talk to LLM_REMOTE_URL (Cloudflare tunnel / hosted inference)
    LLM_LOCAL: bool = True
    LLM_MODEL: str = "qwen3:14b"
    LLM_REMOTE_URL: str = ""
    OLLAMA_BASE_URL: str = "http://127.0.0.1:11434"
    OLLAMA_MODEL: str = "qwen3:14b"  # kept for backward compat; prefer LLM_MODEL
    OLLAMA_MAX_CONCURRENT_REQUESTS: int = 4
    OLLAMA_TIMEOUT_SECONDS: int = 120
    OLLAMA_SELF_HOSTED_OVERRIDE_ALLOWED: bool = True

    # --- LLM: Groq (declared now, used from Phase 3 onward) ---
    GROQ_ENABLED: bool = True
    GROQ_TIMEOUT_SECONDS: int = 15

    # --- Encryption for stored API credentials (used from Phase 5.5 onward) ---
    CREDENTIAL_ENCRYPTION_KEY: str = "changeme-generate-with-fernet-key"

    # --- Business Discovery (used from Phase 1 onward) ---
    OVERPASS_API_URL: str = "https://overpass-api.de/api/interpreter"
    OVERPASS_CACHE_TTL_DAYS: int = 7
    OVERPASS_QUERY_TIMEOUT_SEC: int = 90
    OVERPASS_HTTP_TIMEOUT_SEC: float = 100.0
    DISCOVERY_DEFAULT_LIMIT: int = 50
    DISCOVERY_MAX_LIMIT: int = 100
    GOOGLE_PLACES_ENABLED: bool = False
    GOOGLE_PLACES_API_KEY: str = ""  # optional; org/platform key, never required

    # --- Website Audit (used from Phase 2 onward) ---
    WEBSITE_FETCH_TIMEOUT_SECONDS: int = 10
    WEBSITE_FETCH_MAX_BYTES: int = 5_242_880
    WEBSITE_RECRAWL_TTL_DAYS: int = 30

    # --- Email / ESP (used from Phase 4 onward) ---
    ESP_PROVIDER: Literal["console", "resend", "smtp", "postmark", "ses"] = "console"
    ESP_API_KEY: str = "changeme"
    ESP_PLATFORM_SENDING_ROOT_DOMAIN: str = "mail.yourplatform.com"
    ESP_DAILY_SEND_CAP_PER_ORG: int = 100
    ESP_WEEKLY_SEND_CAP_PER_ORG: int = 500
    ESP_BOUNCE_RATE_PAUSE_THRESHOLD: float = 0.05
    ESP_COMPLAINT_RATE_PAUSE_THRESHOLD: float = 0.001
    ESP_FROM_EMAIL: str = "noreply@localhost"
    ESP_FROM_NAME: str = "Outreach"
    PUBLIC_APP_URL: str = "http://localhost:8000"
    # Optional SMTP (e.g. Mailhog on localhost:1025)
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 1025
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_USE_TLS: bool = False

    # --- Billing (used from Phase 5.5 onward) ---
    STRIPE_SECRET_KEY: str = "changeme"
    STRIPE_WEBHOOK_SECRET: str = "changeme"
    STRIPE_PRICE_ID_STARTER: str = "changeme"
    STRIPE_PRICE_ID_PRO: str = "changeme"
    TRIAL_LENGTH_DAYS: int = 14

    # --- Platform admin (comma-separated emails; full platform access) ---
    PLATFORM_ADMIN_EMAILS: str = ""

    # --- Observability ---
    LOG_LEVEL: str = "INFO"
    DKIM_SELECTOR: str = "default"
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_AUTH_PER_MIN: int = 20
    RATE_LIMIT_API_PER_MIN: int = 120
    SENTRY_DSN: str = ""

    # --- CORS ---
    ALLOWED_ORIGINS: str = "http://localhost:5173"

    @property
    def allowed_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton — env is read once per process."""
    return Settings()
