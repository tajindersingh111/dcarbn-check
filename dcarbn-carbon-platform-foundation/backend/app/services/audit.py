from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentPrincipal
from app.models.audit import AuditEvent


async def record_audit_event(
    db: AsyncSession,
    principal: CurrentPrincipal,
    *,
    action: str,
    entity_type: str,
    entity_id: UUID,
    event_data: dict[str, Any],
) -> None:
    db.add(
        AuditEvent(
            tenant_id=principal.tenant_id,
            actor_type="user",
            actor_id=principal.subject,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id),
            source_system="carbon-platform",
            event_data=event_data,
        )
    )
