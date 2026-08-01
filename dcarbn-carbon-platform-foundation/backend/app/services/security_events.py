from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.security import SecurityEvent, SecurityEventSeverity
from app.core.observability import SECURITY_EVENTS


async def record_security_event(
    db: AsyncSession,
    *,
    event_type: str,
    description: str,
    success: bool,
    severity: SecurityEventSeverity = SecurityEventSeverity.INFO,
    tenant_id: UUID | None = None,
    user_id: UUID | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    correlation_id: str | None = None,
    event_data: dict[str, Any] | None = None,
) -> SecurityEvent:
    event = SecurityEvent(
        tenant_id=tenant_id,
        user_id=user_id,
        event_type=event_type,
        severity=severity,
        success=success,
        ip_address=ip_address,
        user_agent=user_agent,
        correlation_id=correlation_id,
        description=description,
        event_data=event_data or {},
        occurred_at=datetime.now(UTC),
    )
    db.add(event)
    SECURITY_EVENTS.labels(
        event_type=event_type,
        severity=severity.value,
        success=str(success).lower(),
    ).inc()
    await db.flush()
    return event


async def list_security_events(
    db: AsyncSession,
    *,
    tenant_id: UUID | None,
    platform_admin: bool,
    limit: int,
    offset: int,
    severity: SecurityEventSeverity | None,
    event_type: str | None,
) -> tuple[list[SecurityEvent], int]:
    conditions = []
    if not platform_admin:
        conditions.append(SecurityEvent.tenant_id == tenant_id)
    if severity:
        conditions.append(SecurityEvent.severity == severity)
    if event_type:
        conditions.append(SecurityEvent.event_type == event_type)

    query = (
        select(SecurityEvent)
        .where(*conditions)
        .order_by(SecurityEvent.occurred_at.desc())
        .limit(limit)
        .offset(offset)
    )
    count_query = select(func.count()).select_from(SecurityEvent).where(*conditions)
    items = list((await db.scalars(query)).all())
    total = int((await db.scalar(count_query)) or 0)
    return items, total
