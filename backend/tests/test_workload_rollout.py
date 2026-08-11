from __future__ import annotations

from uuid import UUID

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.models.workload import WorkloadType
from app.services.workload_rollout import (
    WorkloadRolloutDisabled,
    WorkloadRolloutNotAllowed,
    allowed_tenant_ids,
    allowed_workload_types,
    require_workload_rollout,
)

TENANT_A = UUID("11111111-1111-1111-1111-111111111111")
TENANT_B = UUID("22222222-2222-2222-2222-222222222222")


def _settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "secret_key": "s" * 32,
        "mfa_encryption_key": "m" * 32,
        "database_url": "sqlite+aiosqlite://",
        "async_workloads_enabled": False,
        "methodology_packs_enabled": False,
        "async_workload_allowed_tenant_ids": [],
        "async_workload_allowed_types": [],
    }
    values.update(overrides)
    return Settings(**values)


def test_enabled_rollout_requires_explicit_scope() -> None:
    with pytest.raises(
        ValidationError,
        match="ASYNC_WORKLOAD_ALLOWED_TENANT_IDS",
    ):
        _settings(
            async_workloads_enabled=True,
            methodology_packs_enabled=True,
        )


def test_enabled_calculation_rollout_requires_methodology_packs() -> None:
    with pytest.raises(
        ValidationError,
        match="METHODOLOGY_PACKS_ENABLED",
    ):
        _settings(
            async_workloads_enabled=True,
            async_workload_allowed_tenant_ids=[TENANT_A],
            async_workload_allowed_types=["calculation"],
        )


def test_rollout_policy_allows_only_approved_tenant_and_type() -> None:
    settings = _settings(
        async_workloads_enabled=True,
        methodology_packs_enabled=True,
        async_workload_allowed_tenant_ids=[TENANT_A],
        async_workload_allowed_types=["calculation"],
    )

    require_workload_rollout(
        settings,
        tenant_id=TENANT_A,
        workload_type=WorkloadType.CALCULATION,
        require_methodology_packs=True,
    )

    with pytest.raises(WorkloadRolloutNotAllowed, match="tenant"):
        require_workload_rollout(
            settings,
            tenant_id=TENANT_B,
            workload_type=WorkloadType.CALCULATION,
            require_methodology_packs=True,
        )

    with pytest.raises(WorkloadRolloutNotAllowed, match="workload type"):
        require_workload_rollout(
            settings,
            tenant_id=TENANT_A,
            workload_type=WorkloadType.DATA_IMPORT,
        )


def test_disabled_rollout_exposes_no_worker_scope() -> None:
    settings = _settings()

    with pytest.raises(WorkloadRolloutDisabled, match="not enabled"):
        require_workload_rollout(
            settings,
            tenant_id=TENANT_A,
            workload_type=WorkloadType.CALCULATION,
        )
    assert allowed_tenant_ids(settings) == ()
    assert allowed_workload_types(settings) == ()


def test_enabled_rollout_exposes_exact_worker_scope() -> None:
    settings = _settings(
        async_workloads_enabled=True,
        methodology_packs_enabled=True,
        async_workload_allowed_tenant_ids=[TENANT_A],
        async_workload_allowed_types=["calculation"],
    )

    assert allowed_tenant_ids(settings) == (TENANT_A,)
    assert allowed_workload_types(settings) == (WorkloadType.CALCULATION,)
