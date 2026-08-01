from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentPrincipal, get_current_principal
from app.db.session import get_db
from app.schemas.tenant import TenantResponse
from app.services.tenants import get_tenant

router = APIRouter()


@router.get("/current", response_model=TenantResponse)
async def current_tenant(
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> TenantResponse:
    tenant = await get_tenant(db, principal.tenant_id)
    return TenantResponse.model_validate(tenant)
