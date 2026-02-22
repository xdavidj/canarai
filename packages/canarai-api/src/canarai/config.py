"""Application configuration via environment variables."""

from functools import lru_cache
from typing import ClassVar

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    database_url: str = "sqlite+aiosqlite:///./canarai.db"
    api_secret_key: str = "change-me"
    api_host: str = "0.0.0.0"
    api_port: int = 8787
    cors_origins: str = "*"
    environment: str = "development"
    webhook_timeout_seconds: int = 10
    webhook_max_retries: int = 3
    script_base_url: str = "http://localhost:8787"

    # Feed aggregation settings
    feed_snapshot_staleness_seconds: int = 900
    feed_min_visits: int = 50
    feed_min_sites: int = 3
    feed_rate_limit_per_minute: int = 60

    # Provider settings
    provider_rate_limit_per_hour: int = 5

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    INSECURE_SECRETS: ClassVar[set[str]] = {"change-me", "change-me-in-production", "secret", ""}

    def validate_production(self) -> None:
        """Raise if running in production with an insecure default secret key."""
        if self.environment == "production" and self.api_secret_key in self.INSECURE_SECRETS:
            raise RuntimeError(
                "API_SECRET_KEY must be changed from default in production. "
                'Generate one: python -c "import secrets; print(secrets.token_hex(32))"'
            )


@lru_cache
def get_settings() -> Settings:
    """Return cached settings singleton."""
    return Settings()
