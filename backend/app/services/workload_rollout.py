from __future__ import annotations

from uuid import UUID

from app.core.config import Settings
from app.models.workload import WorkloadType


class WorkloadRolloutDisabled(RuntimeError):
    """Raised when the global rollout controls are disabled."""


class WorkloadRolloutNotAllowed(RuntimeError):
    """Raised when a tenant or workload type is outside the approved scope."""


def require_workload_rollout(
    settings: Settings,
    *,
    tenant_id: UUID,
    workload_type: WorkloadType,
    require_methodology_packs: bool = False,
) -> None:
    """Fail closed unless every global and scoped rollout gate is satisfied."""
    if not settings.async_workloads_enabled:
        raise WorkloadRolloutDisabled(
            "Asynchronous workload processing is not enabled."
        )
    if require_methodology_packs and not settings.methodology_packs_enabled:
        raise WorkloadRolloutDisabled(
            "Methodology-pack execution is not enabled."
        )
    if tenant_id not in settings.async_workload_allowed_tenant_ids:
        raise WorkloadRolloutNotAllowed(
            "This tenant is not approved for asynchronous workload processing."
        )
    if workload_type.value not in settings.async_workload_allowed_types:
        raise WorkloadRolloutNotAllowed(
            "This workload type is not approved for asynchronous processing."
        )


def allowed_tenant_ids(settings: Settings) -> tuple[UUID, ...]:
    """Return the configured worker tenant scope; an empty tuple leases nothing."""
    if not settings.async_workloads_enabled:
        return ()
    return tuple(settings.async_workload_allowed_tenant_ids)


def allowed_workload_types(settings: Settings) -> tuple[WorkloadType, ...]:
    """Return reviewed workload types that workers may lease."""
    if not settings.async_workloads_enabled:
        return ()
    return tuple(
        WorkloadType(value) for value in settings.async_workload_allowed_types
    )
