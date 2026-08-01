from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant


async def get_tenant(db: AsyncSession, tenant_id: UUID) -> Tenant:
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None or not tenant.is_active:
        raise HTTPException(status_code=404, detail="Tenant not found.")
    return tenant
