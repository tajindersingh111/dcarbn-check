from __future__ import annotations

import re
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

_ROLE_PATTERN = re.compile(r"^[a-z_][a-z0-9_]{0,62}$")
_AUTH_RESOLVERS = frozenset(
    {
        "refresh_session",
        "mfa_challenge",
        "user_invitation",
        "password_reset",
    }
)


def _is_postgresql(session: AsyncSession) -> bool:
    return session.get_bind().dialect.name == "postgresql"


async def activate_database_role(session: AsyncSession, role: str) -> None:
    """Enter the restricted application role for the current transaction."""
    if not _is_postgresql(session):
        return
    if not _ROLE_PATTERN.fullmatch(role):
        raise ValueError("Database application role is invalid.")
    await session.execute(text(f'SET LOCAL ROLE "{role}"'))


async def set_tenant_context(session: AsyncSession, tenant_id: UUID) -> None:
    """Bind this transaction to one verified tenant for PostgreSQL RLS."""
    session.info["tenant_id"] = tenant_id
    if not _is_postgresql(session):
        return
    await session.execute(
        text(
            "SELECT set_config("
            "'app.current_tenant_id', :tenant_id, true"
            ")"
        ),
        {"tenant_id": str(tenant_id)},
    )


async def bootstrap_auth_tenant(
    session: AsyncSession,
    *,
    purpose: str,
    token_hash: str,
) -> UUID | None:
    """Resolve an opaque authentication token through a constrained DB function."""
    if purpose not in _AUTH_RESOLVERS:
        raise ValueError("Authentication tenant resolver is invalid.")
    if not _is_postgresql(session):
        return None
    value = await session.scalar(
        text(
            "SELECT public.dcarbn_resolve_auth_tenant("
            ":purpose, :token_hash"
            ")"
        ),
        {"purpose": purpose, "token_hash": token_hash},
    )
    if value is None:
        return None
    tenant_id = value if isinstance(value, UUID) else UUID(str(value))
    await set_tenant_context(session, tenant_id)
    return tenant_id


def clear_tenant_context(session: AsyncSession) -> None:
    """Clear Python-side context; PostgreSQL SET LOCAL clears at transaction end."""
    session.info.pop("tenant_id", None)
