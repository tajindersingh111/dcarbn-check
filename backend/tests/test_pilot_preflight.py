from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import UUID

import pytest

from app.core.config import Settings
from app.services.pilot_preflight import (
    PilotApprovalEvidence,
    evaluate_pilot_preflight,
)

TENANT_A = UUID("11111111-1111-1111-1111-111111111111")
TENANT_B = UUID("22222222-2222-2222-2222-222222222222")
RELEASE_SHA = "a" * 40


def _settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "app_env": "staging",
        "secret_key": "s" * 32,
        "mfa_encryption_key": "m" * 32,
        "database_url": "sqlite+aiosqlite://",
        "redis_required": True,
        "cookie_secure": True,
        "hsts_enabled": True,
        "docs_enabled": False,
        "email_provider": "smtp",
        "frontend_base_url": "https://staging.example.test",
        "rate_limit_enabled": True,
        "rate_limit_fail_open": False,
        "async_workloads_enabled": False,
        "methodology_packs_enabled": False,
        "async_workload_allowed_tenant_ids": [TENANT_A],
        "async_workload_allowed_types": ["calculation"],
        "worker_lease_seconds": 60,
        "worker_per_tenant_limit": 2,
    }
    values.update(overrides)
    return Settings(**values)


def _evidence(**overrides: bool) -> PilotApprovalEvidence:
    values = {
        "hosting_ready": True,
        "business_scope_approved": True,
        "application_release_approved": True,
        "security_controls_approved": True,
        "monitoring_ready": True,
        "rollback_ready": True,
        "activation_window_recorded": True,
        "methodology_pack_evidence_recorded": True,
        "factor_set_evidence_recorded": True,
    }
    values.update(overrides)
    return PilotApprovalEvidence(**values)


def test_complete_dark_configuration_is_ready_for_go_review() -> None:
    report = evaluate_pilot_preflight(
        _settings(),
        _evidence(),
        release_sha=RELEASE_SHA,
        now=datetime(2026, 8, 11, tzinfo=UTC),
    )

    assert report.decision == "READY_FOR_GO_REVIEW"
    assert all(check.passed for check in report.checks)
    assert report.tenant_count == 1
    assert report.workload_types == ("calculation",)


@pytest.mark.parametrize(
    ("settings", "failed_check"),
    [
        (_settings(async_workload_allowed_tenant_ids=[]), "single_tenant_scope"),
        (
            _settings(async_workload_allowed_tenant_ids=[TENANT_A, TENANT_B]),
            "single_tenant_scope",
        ),
        (
            _settings(
                async_workloads_enabled=True,
                methodology_packs_enabled=True,
            ),
            "deploy_dark",
        ),
        (_settings(worker_per_tenant_limit=3), "worker_limits"),
    ],
)
def test_unsafe_configuration_fails_closed(
    settings: Settings,
    failed_check: str,
) -> None:
    report = evaluate_pilot_preflight(
        settings,
        _evidence(),
        release_sha=RELEASE_SHA,
    )

    assert report.decision == "NO_GO"
    assert not next(
        check for check in report.checks if check.name == failed_check
    ).passed


def test_incomplete_approval_evidence_fails_closed() -> None:
    report = evaluate_pilot_preflight(
        _settings(),
        _evidence(hosting_ready=False),
        release_sha=RELEASE_SHA,
    )

    assert report.decision == "NO_GO"
    assert not next(
        check for check in report.checks if check.name == "hosting_ready"
    ).passed


def test_invalid_release_sha_fails_closed() -> None:
    report = evaluate_pilot_preflight(
        _settings(),
        _evidence(),
        release_sha="main",
    )

    assert report.decision == "NO_GO"
    assert not next(
        check for check in report.checks if check.name == "release_sha"
    ).passed


def test_redacted_report_never_contains_tenant_identifier() -> None:
    report = evaluate_pilot_preflight(
        _settings(),
        _evidence(),
        release_sha=RELEASE_SHA,
    )

    rendered = json.dumps(report.as_dict())
    assert str(TENANT_A) not in rendered
    assert report.as_dict()["configuration"] == {
        "tenant_count": 1,
        "workload_types": ["calculation"],
    }


def test_approval_evidence_requires_exact_boolean_fields() -> None:
    with pytest.raises(ValueError, match="missing fields"):
        PilotApprovalEvidence.from_mapping({"hosting_ready": True})

    complete = {
        "hosting_ready": True,
        "business_scope_approved": True,
        "application_release_approved": True,
        "security_controls_approved": True,
        "monitoring_ready": True,
        "rollback_ready": True,
        "activation_window_recorded": True,
        "methodology_pack_evidence_recorded": True,
        "factor_set_evidence_recorded": True,
        "unexpected": True,
    }
    with pytest.raises(ValueError, match="unexpected fields"):
        PilotApprovalEvidence.from_mapping(complete)

    complete.pop("unexpected")
    complete["hosting_ready"] = "yes"
    with pytest.raises(ValueError, match="must be booleans"):
        PilotApprovalEvidence.from_mapping(complete)
