from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Literal, Mapping

from app.core.config import Settings

Decision = Literal["NO_GO", "READY_FOR_GO_REVIEW"]

_RELEASE_SHA = re.compile(r"^[0-9a-f]{40}$")
_REQUIRED_EVIDENCE_FIELDS = (
    "hosting_ready",
    "business_scope_approved",
    "application_release_approved",
    "security_controls_approved",
    "monitoring_ready",
    "rollback_ready",
    "activation_window_recorded",
    "methodology_pack_evidence_recorded",
    "factor_set_evidence_recorded",
)


@dataclass(frozen=True)
class PilotApprovalEvidence:
    """Non-sensitive readiness decisions held outside source control."""

    hosting_ready: bool
    business_scope_approved: bool
    application_release_approved: bool
    security_controls_approved: bool
    monitoring_ready: bool
    rollback_ready: bool
    activation_window_recorded: bool
    methodology_pack_evidence_recorded: bool
    factor_set_evidence_recorded: bool

    @classmethod
    def from_mapping(cls, value: Mapping[str, object]) -> PilotApprovalEvidence:
        missing = [field for field in _REQUIRED_EVIDENCE_FIELDS if field not in value]
        unexpected = sorted(set(value) - set(_REQUIRED_EVIDENCE_FIELDS))
        if missing or unexpected:
            parts: list[str] = []
            if missing:
                parts.append("missing fields: " + ", ".join(missing))
            if unexpected:
                parts.append("unexpected fields: " + ", ".join(unexpected))
            raise ValueError("; ".join(parts))

        non_boolean = [
            field for field in _REQUIRED_EVIDENCE_FIELDS if not isinstance(value[field], bool)
        ]
        if non_boolean:
            raise ValueError(
                "evidence fields must be booleans: " + ", ".join(non_boolean)
            )

        return cls(
            hosting_ready=bool(value["hosting_ready"]),
            business_scope_approved=bool(value["business_scope_approved"]),
            application_release_approved=bool(
                value["application_release_approved"]
            ),
            security_controls_approved=bool(
                value["security_controls_approved"]
            ),
            monitoring_ready=bool(value["monitoring_ready"]),
            rollback_ready=bool(value["rollback_ready"]),
            activation_window_recorded=bool(
                value["activation_window_recorded"]
            ),
            methodology_pack_evidence_recorded=bool(
                value["methodology_pack_evidence_recorded"]
            ),
            factor_set_evidence_recorded=bool(
                value["factor_set_evidence_recorded"]
            ),
        )


@dataclass(frozen=True)
class PreflightCheck:
    name: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class PilotPreflightReport:
    generated_at: str
    release_sha: str
    decision: Decision
    tenant_count: int
    workload_types: tuple[str, ...]
    checks: tuple[PreflightCheck, ...]

    def as_dict(self) -> dict[str, object]:
        """Return a redacted report that never includes tenant identifiers."""
        return {
            "generated_at": self.generated_at,
            "release_sha": self.release_sha,
            "decision": self.decision,
            "configuration": {
                "tenant_count": self.tenant_count,
                "workload_types": list(self.workload_types),
            },
            "checks": [asdict(check) for check in self.checks],
        }


def _evidence_checks(evidence: PilotApprovalEvidence) -> list[PreflightCheck]:
    labels = {
        "hosting_ready": "Hosting handover is complete",
        "business_scope_approved": "Business pilot scope is approved",
        "application_release_approved": "Application release is approved",
        "security_controls_approved": "Security controls are approved",
        "monitoring_ready": "Monitoring and alert routing are ready",
        "rollback_ready": "Rollback has been rehearsed",
        "activation_window_recorded": "Activation window is recorded",
        "methodology_pack_evidence_recorded": (
            "Methodology-pack evidence is recorded"
        ),
        "factor_set_evidence_recorded": "Factor-set evidence is recorded",
    }
    values = asdict(evidence)
    return [
        PreflightCheck(name=field, passed=bool(values[field]), detail=labels[field])
        for field in _REQUIRED_EVIDENCE_FIELDS
    ]


def evaluate_pilot_preflight(
    settings: Settings,
    evidence: PilotApprovalEvidence,
    *,
    release_sha: str,
    now: datetime | None = None,
) -> PilotPreflightReport:
    """Evaluate staging readiness without exposing tenant IDs or enabling work."""
    workload_types = tuple(settings.async_workload_allowed_types)
    checks = [
        PreflightCheck(
            name="release_sha",
            passed=bool(_RELEASE_SHA.fullmatch(release_sha)),
            detail="An exact 40-character lowercase release SHA is recorded",
        ),
        PreflightCheck(
            name="staging_environment",
            passed=settings.app_env == "staging",
            detail="APP_ENV is staging",
        ),
        PreflightCheck(
            name="deploy_dark",
            passed=(
                not settings.async_workloads_enabled
                and not settings.methodology_packs_enabled
            ),
            detail="Both workload feature flags remain false before GO",
        ),
        PreflightCheck(
            name="single_tenant_scope",
            passed=len(settings.async_workload_allowed_tenant_ids) == 1,
            detail="Exactly one protected pilot tenant is configured",
        ),
        PreflightCheck(
            name="calculation_only",
            passed=workload_types == ("calculation",),
            detail="Only the reviewed calculation workload type is allowed",
        ),
        PreflightCheck(
            name="worker_limits",
            passed=(
                settings.worker_lease_seconds == 60
                and settings.worker_per_tenant_limit == 2
            ),
            detail="Initial lease and per-tenant worker limits are unchanged",
        ),
        PreflightCheck(
            name="redis_fail_closed",
            passed=settings.redis_required,
            detail="Managed Redis is required",
        ),
        PreflightCheck(
            name="rate_limit_fail_closed",
            passed=(
                settings.rate_limit_enabled
                and not settings.rate_limit_fail_open
            ),
            detail="Rate limiting is enabled and fails closed",
        ),
    ]
    checks.extend(_evidence_checks(evidence))
    decision: Decision = (
        "READY_FOR_GO_REVIEW" if all(check.passed for check in checks) else "NO_GO"
    )
    timestamp = (now or datetime.now(UTC)).astimezone(UTC).isoformat()
    return PilotPreflightReport(
        generated_at=timestamp,
        release_sha=release_sha,
        decision=decision,
        tenant_count=len(settings.async_workload_allowed_tenant_ids),
        workload_types=workload_types,
        checks=tuple(checks),
    )
