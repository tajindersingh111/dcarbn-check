import pytest
from sqlalchemy import select

from app.models.identity import TenantMembership, User
from app.models.tenant import Tenant
from app.scripts.bootstrap_platform_admin import bootstrap_platform_admin


@pytest.mark.asyncio
async def test_bootstrap_creates_initial_platform_admin(db_session) -> None:
    user = await bootstrap_platform_admin(
        db_session,
        tenant_name="D-carbN Administration",
        tenant_slug="dcarbn-admin",
        email="admin@example.com",
        full_name="Initial Administrator",
        password="x" * 32,
    )

    tenant = await db_session.scalar(
        select(Tenant).where(Tenant.slug == "dcarbn-admin")
    )
    membership = await db_session.scalar(
        select(TenantMembership).where(
            TenantMembership.tenant_id == tenant.id,
            TenantMembership.user_id == user.id,
        )
    )

    assert user.is_platform_admin is True
    assert membership is not None
    assert membership.is_active is True


@pytest.mark.asyncio
async def test_bootstrap_refuses_second_platform_admin(db_session) -> None:
    values = {
        "tenant_name": "D-carbN Administration",
        "tenant_slug": "dcarbn-admin",
        "email": "admin@example.com",
        "full_name": "Initial Administrator",
        "password": "x" * 32,
    }
    await bootstrap_platform_admin(db_session, **values)

    with pytest.raises(RuntimeError, match="already exists"):
        await bootstrap_platform_admin(
            db_session,
            tenant_name="Second Administration",
            tenant_slug="second-admin",
            email="second@example.com",
            full_name="Second Administrator",
            password="y" * 32,
        )
