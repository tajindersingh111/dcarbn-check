import pytest
from pydantic import ValidationError

from app.core.config import Settings


def production_settings(**overrides: object) -> Settings:
    values = {
        "app_env": "production",
        "secret_key": "s" * 64,
        "mfa_encryption_key": "m" * 64,
        "database_url": "postgresql+asyncpg://user:pass@db:5432/app",
        "database_connection_limit": 50,
        "redis_url": "redis://:password@redis:6379/0",
        "redis_required": True,
        "rate_limit_fail_open": False,
        "cookie_secure": True,
        "hsts_enabled": True,
        "docs_enabled": False,
        "email_provider": "smtp",
        "smtp_host": "smtp.example.com",
        "smtp_username": "user",
        "smtp_password": "password",
        "frontend_base_url": "https://carbon.example.com",
        "cors_origins": ["https://carbon.example.com"],
        "trusted_hosts": ["carbon.example.com"],
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_safe_production_settings_are_accepted() -> None:
    settings = production_settings()

    assert settings.app_env == "production"
    assert settings.cookie_secure is True


def test_production_rejects_fail_open_rate_limiting() -> None:
    with pytest.raises(ValidationError, match="RATE_LIMIT_FAIL_OPEN"):
        production_settings(rate_limit_fail_open=True)


def test_production_rejects_wildcard_cors() -> None:
    with pytest.raises(ValidationError, match="CORS_ORIGINS"):
        production_settings(cors_origins=["*"])


def test_staging_rejects_unsafe_runtime_settings() -> None:
    with pytest.raises(ValidationError, match="Unsafe staging settings"):
        production_settings(
            app_env="staging",
            cookie_secure=False,
            rate_limit_fail_open=True,
        )


def test_production_requires_host_connection_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DATABASE_CONNECTION_LIMIT", raising=False)
    with pytest.raises(ValidationError, match="DATABASE_CONNECTION_LIMIT"):
        values = production_settings().model_dump()
        values.pop("database_connection_limit")
        Settings(_env_file=None, **values)
