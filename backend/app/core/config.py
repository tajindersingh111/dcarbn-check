from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


def _read_secret(name: str, current: str | None) -> str | None:
    file_variable = os.getenv(f"{name.upper()}_FILE")
    candidates = [
        Path(file_variable) if file_variable else None,
        Path("/run/secrets") / name.lower(),
    ]
    for candidate in candidates:
        if candidate and candidate.is_file():
            value = candidate.read_text(encoding="utf-8").strip()
            if value:
                return value
    return current


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: Literal["development", "test", "staging", "production"] = "development"
    app_name: str = "D-carbN Carbon Platform"
    api_v1_prefix: str = "/api/v1"
    secret_key: str = ""
    jwt_algorithm: str = "HS256"
    access_token_audience: str = "dcarbn-carbon-platform"
    access_token_issuer: str = "dcarbn-carbon-platform"
    access_token_minutes: int = Field(default=15, ge=5, le=60)
    refresh_token_days: int = Field(default=30, ge=1, le=90)
    invitation_hours: int = Field(default=72, ge=1, le=168)
    password_reset_minutes: int = Field(default=30, ge=5, le=120)
    mfa_challenge_minutes: int = Field(default=5, ge=1, le=15)
    mfa_max_attempts: int = Field(default=5, ge=3, le=10)
    mfa_issuer: str = "D-carbN"
    mfa_encryption_key: str = ""

    account_lockout_threshold: int = Field(default=5, ge=3, le=20)
    account_lockout_minutes: int = Field(default=30, ge=1, le=1440)
    account_failure_window_minutes: int = Field(default=15, ge=1, le=120)

    cookie_secure: bool = False
    cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    cookie_domain: str | None = None
    frontend_base_url: str = "http://localhost:3000"
    expose_tokens_in_api: bool = False

    database_url: str = ""
    redis_url: str = "redis://localhost:6379/0"
    redis_required: bool = False
    rate_limit_enabled: bool = True
    rate_limit_fail_open: bool = True
    rate_limit_general_requests: int = Field(default=300, ge=10)
    rate_limit_general_window_seconds: int = Field(default=60, ge=1)
    rate_limit_login_requests: int = Field(default=10, ge=1)
    rate_limit_login_window_seconds: int = Field(default=300, ge=10)
    rate_limit_mfa_requests: int = Field(default=10, ge=1)
    rate_limit_mfa_window_seconds: int = Field(default=300, ge=10)
    rate_limit_password_reset_requests: int = Field(default=5, ge=1)
    rate_limit_password_reset_window_seconds: int = Field(default=900, ge=10)
    rate_limit_refresh_requests: int = Field(default=60, ge=1)
    rate_limit_refresh_window_seconds: int = Field(default=300, ge=10)

    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:3000"]
    trusted_hosts: Annotated[list[str], NoDecode] = ["localhost", "127.0.0.1"]
    trusted_proxy_ips: Annotated[list[str], NoDecode] = ["127.0.0.1", "::1"]
    docs_enabled: bool = True
    hsts_enabled: bool = False
    hsts_max_age_seconds: int = 31536000
    hsts_include_subdomains: bool = True
    hsts_preload: bool = False
    content_security_policy: str = (
        "default-src 'self'; "
        "base-uri 'self'; "
        "frame-ancestors 'none'; "
        "form-action 'self'; "
        "object-src 'none'; "
        "img-src 'self' data:; "
        "font-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "script-src 'self'; "
        "connect-src 'self'"
    )

    email_provider: Literal["console", "smtp"] = "console"
    email_from_address: str = "no-reply@example.com"
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_use_tls: bool = False
    smtp_starttls: bool = False

    log_level: str = "INFO"
    otel_enabled: bool = False
    otel_service_name: str = "dcarbn-backend"
    otel_exporter_otlp_endpoint: str = "http://otel-collector:4317"
    otel_exporter_otlp_insecure: bool = True
    otel_metric_export_interval_ms: int = Field(default=30000, ge=5000)
    backup_status_file: str = "/var/run/dcarbn/backup-status.json"
    backup_max_age_seconds: int = Field(default=93600, ge=3600)
    wal_archive_status_file: str = "/var/run/dcarbn/wal-status.json"
    pitr_status_file: str = "/var/run/dcarbn/pitr-status.json"
    failover_state_file: str = "/var/run/dcarbn/failover.json"
    wal_archive_max_age_seconds: int = Field(default=300, ge=60)
    pitr_base_backup_max_age_seconds: int = Field(default=93600, ge=3600)
    slo_definitions_file: str = "/app/deploy/slo/slo-definitions.yml"
    release_evidence_directory: str = "/var/run/dcarbn-evidence"
    supply_chain_evidence_directory: str = "/var/run/dcarbn-supply-chain"
    gitops_evidence_directory: str = "/var/run/dcarbn-gitops"

    @field_validator(
        "cors_origins",
        "trusted_hosts",
        "trusted_proxy_ips",
        mode="before",
    )
    @classmethod
    def parse_csv_lists(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @model_validator(mode="after")
    def load_secrets_and_validate(self) -> "Settings":
        self.secret_key = _read_secret("secret_key", self.secret_key) or ""
        self.mfa_encryption_key = (
            _read_secret("mfa_encryption_key", self.mfa_encryption_key) or ""
        )
        self.database_url = _read_secret("database_url", self.database_url) or ""
        self.redis_url = _read_secret("redis_url", self.redis_url) or self.redis_url
        self.smtp_password = _read_secret("smtp_password", self.smtp_password)

        if len(self.secret_key) < 32:
            raise ValueError("SECRET_KEY must contain at least 32 characters.")
        if len(self.mfa_encryption_key) < 32:
            raise ValueError(
                "MFA_ENCRYPTION_KEY must contain at least 32 characters."
            )
        if not self.database_url:
            raise ValueError("DATABASE_URL is required.")

        if self.app_env in {"staging", "production"}:
            errors: list[str] = []
            if not self.cookie_secure:
                errors.append("COOKIE_SECURE must be true")
            if not self.hsts_enabled:
                errors.append("HSTS_ENABLED must be true")
            if self.docs_enabled:
                errors.append("DOCS_ENABLED must be false")
            if self.expose_tokens_in_api:
                errors.append("EXPOSE_TOKENS_IN_API must be false")
            if self.email_provider == "console":
                errors.append("EMAIL_PROVIDER must not be console")
            if "*" in self.cors_origins:
                errors.append("CORS_ORIGINS must not contain a wildcard")
            if "*" in self.trusted_hosts:
                errors.append("TRUSTED_HOSTS must not contain a wildcard")
            if self.rate_limit_fail_open:
                errors.append("RATE_LIMIT_FAIL_OPEN must be false")
            if not self.redis_required:
                errors.append("REDIS_REQUIRED must be true")
            if self.frontend_base_url.startswith("http://"):
                errors.append("FRONTEND_BASE_URL must use HTTPS")
            if "development" in self.secret_key.casefold():
                errors.append("SECRET_KEY must not use a development value")
            if "development" in self.mfa_encryption_key.casefold():
                errors.append(
                    "MFA_ENCRYPTION_KEY must not use a development value"
                )
            if errors:
                raise ValueError(
                    f"Unsafe {self.app_env} settings: " + "; ".join(errors)
                )

        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
