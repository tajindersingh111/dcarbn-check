from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from sqlalchemy.pool import NullPool

from app.db.pooling import (
    create_database_engine,
    create_operator_engine,
    database_budget,
)


def settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "secret_key": "s" * 64,
        "mfa_encryption_key": "m" * 64,
        "database_url": "postgresql+asyncpg://user:pass@database.invalid/app",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_default_budget_is_internally_consistent() -> None:
    budget = database_budget(settings())

    assert budget.api_connections == 12
    assert budget.worker_connections == 9
    assert budget.fixed_connections == 8
    assert budget.safety_margin == 20
    assert budget.required_connections == 49
    assert budget.connection_limit == 50


def test_aggregate_pool_budget_fails_closed() -> None:
    with pytest.raises(ValidationError, match="Unsafe database connection budget"):
        settings(database_api_pool_size=4)


def test_direct_api_engine_uses_only_its_process_budget() -> None:
    configured = settings(database_process_role="api")
    fake_engine = Mock()

    with (
        patch("app.db.pooling.create_async_engine", return_value=fake_engine) as create,
        patch("app.db.pooling.configure_pool_metrics"),
    ):
        assert create_database_engine(configured) is fake_engine

    kwargs = create.call_args.kwargs
    assert kwargs["pool_size"] == 3
    assert kwargs["max_overflow"] == 1
    assert kwargs["pool_timeout"] == 5.0
    assert kwargs["connect_args"] == {}


def test_pgbouncer_transaction_mode_disables_connection_caches() -> None:
    configured = settings(
        database_process_role="worker",
        database_pool_mode="pgbouncer_transaction",
    )
    fake_engine = Mock()

    with (
        patch("app.db.pooling.create_async_engine", return_value=fake_engine) as create,
        patch("app.db.pooling.configure_pool_metrics"),
    ):
        assert create_database_engine(configured) is fake_engine

    kwargs = create.call_args.kwargs
    assert kwargs["pool_size"] == 2
    assert kwargs["max_overflow"] == 1
    assert kwargs["connect_args"] == {
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0,
    }


def test_sqlite_portable_engine_does_not_receive_postgres_pool_options() -> None:
    configured = settings(database_url="sqlite+aiosqlite://")
    fake_engine = Mock()

    with patch("app.db.pooling.create_async_engine", return_value=fake_engine) as create:
        assert create_database_engine(configured) is fake_engine

    assert create.call_args.kwargs == {"pool_pre_ping": True}


def test_operator_engine_is_separate_and_bounded_by_operator_reserve() -> None:
    configured = settings(database_pool_mode="pgbouncer_transaction")
    fake_engine = Mock()

    with patch("app.db.pooling.create_async_engine", return_value=fake_engine) as create:
        assert create_operator_engine(configured) is fake_engine

    assert create.call_args.kwargs == {
        "pool_size": configured.database_operator_reserve,
        "max_overflow": 0,
        "pool_timeout": configured.database_pool_timeout_seconds,
        "pool_recycle": configured.database_pool_recycle_seconds,
        "pool_pre_ping": True,
        "pool_use_lifo": True,
        "connect_args": {
            "statement_cache_size": 0,
            "prepared_statement_cache_size": 0,
        },
    }


def test_operator_reserve_is_validated_in_aggregate_budget() -> None:
    with pytest.raises(ValidationError, match="Unsafe database connection budget"):
        settings(database_operator_reserve=7)


def test_non_postgres_operator_engine_remains_disposable() -> None:
    configured = settings(database_url="sqlite+aiosqlite://")
    fake_engine = Mock()

    with patch("app.db.pooling.create_async_engine", return_value=fake_engine) as create:
        assert create_operator_engine(configured) is fake_engine

    assert create.call_args.kwargs == {
        "poolclass": NullPool,
        "pool_pre_ping": True,
        "connect_args": {},
    }


def test_pgbouncer_template_defaults_to_private_verified_tls() -> None:
    template = (
        Path(__file__).resolve().parents[2]
        / "config"
        / "pgbouncer"
        / "pgbouncer.ini.example"
    ).read_text(encoding="utf-8")

    assert "listen_addr = 127.0.0.1" in template
    assert "listen_addr = 0.0.0.0" not in template
    assert "auth_type = scram-sha-256" in template
    assert "client_tls_sslmode = verify-full" in template
    assert "server_tls_sslmode = verify-full" in template
    for unsafe_mode in ("disable", "allow", "prefer", "require"):
        assert f"client_tls_sslmode = {unsafe_mode}" not in template
        assert f"server_tls_sslmode = {unsafe_mode}" not in template
    assert "client_tls_key_file = /run/secrets/" in template
    assert "client_tls_cert_file = /run/secrets/" in template
    assert "client_tls_ca_file = /run/secrets/" in template
    assert "server_tls_key_file = /run/secrets/" in template
    assert "server_tls_cert_file = /run/secrets/" in template
    assert "server_tls_ca_file = /run/secrets/" in template
