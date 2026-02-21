"""Tests for canarai.config (Settings and get_settings)."""

import pytest

from canarai.config import Settings, get_settings


class TestDefaultSettings:
    def test_default_api_port(self):
        s = Settings()
        assert s.api_port == 8787

    def test_default_environment_is_development(self):
        s = Settings()
        assert s.environment == "development"

    def test_default_api_host(self):
        s = Settings()
        assert s.api_host == "0.0.0.0"

    def test_default_api_secret_key(self):
        s = Settings()
        assert s.api_secret_key == "change-me"

    def test_default_webhook_timeout_seconds(self):
        s = Settings()
        assert s.webhook_timeout_seconds == 10

    def test_default_webhook_max_retries(self):
        s = Settings()
        assert s.webhook_max_retries == 3

    def test_default_database_url_is_sqlite(self):
        s = Settings()
        assert "sqlite" in s.database_url


class TestInsecureSecrets:
    def test_insecure_secrets_contains_change_me(self):
        assert "change-me" in Settings.INSECURE_SECRETS

    def test_insecure_secrets_contains_empty_string(self):
        assert "" in Settings.INSECURE_SECRETS

    def test_insecure_secrets_contains_secret(self):
        assert "secret" in Settings.INSECURE_SECRETS

    def test_insecure_secrets_contains_change_me_in_production(self):
        assert "change-me-in-production" in Settings.INSECURE_SECRETS


class TestValidateProduction:
    def test_production_with_insecure_secret_raises_runtime_error(self):
        s = Settings(environment="production", api_secret_key="change-me")
        with pytest.raises(RuntimeError, match="API_SECRET_KEY"):
            s.validate_production()

    def test_production_with_empty_secret_raises_runtime_error(self):
        s = Settings(environment="production", api_secret_key="")
        with pytest.raises(RuntimeError):
            s.validate_production()

    def test_production_with_custom_secret_passes(self):
        s = Settings(
            environment="production",
            api_secret_key="a" * 64,
        )
        # Should not raise
        s.validate_production()

    def test_development_with_insecure_secret_does_not_raise(self):
        s = Settings(environment="development", api_secret_key="change-me")
        # Must not raise in development
        s.validate_production()


class TestGetSettings:
    def test_get_settings_returns_settings_instance(self):
        get_settings.cache_clear()
        s = get_settings()
        assert isinstance(s, Settings)

    def test_get_settings_cached_returns_same_object(self):
        get_settings.cache_clear()
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2

    def test_cache_clear_allows_reload(self):
        get_settings.cache_clear()
        s1 = get_settings()
        get_settings.cache_clear()
        s2 = get_settings()
        # Both should be Settings instances; equality not guaranteed (new object)
        assert isinstance(s2, Settings)
        assert s1 is not s2
