from __future__ import annotations

import secrets
from collections.abc import Callable
from dataclasses import dataclass
from uuid import UUID

import jwt
from fastapi import Cookie, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_db
from app.db.tenant_context import set_tenant_context
from app.models.identity import TenantMembership, User, UserStatus
from app.models.tenant import Tenant

bearer = HTTPBearer(auto_error=False)
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


class TokenClaims(BaseModel):
    sub: UUID
    tenant_id: UUID
    roles: list[str] = Field(default_factory=list)
    platform_admin: bool = False
    token_version: int
    aud: str
    iss: str


@dataclass(frozen=True, slots=True)
class CurrentPrincipal:
    subject: str
    tenant_id: UUID
    roles: frozenset[str]
    is_platform_admin: bool = False


async def get_current_principal(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    access_cookie: str | None = Cookie(default=None, alias="dcarbn_access"),
    csrf_cookie: str | None = Cookie(default=None, alias="dcarbn_csrf"),
    db: AsyncSession = Depends(get_db),
) -> CurrentPrincipal:
    settings = get_settings()
    token = credentials.credentials if credentials else access_cookie
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )

    if access_cookie and request.method not in SAFE_METHODS:
        csrf_header = request.headers.get("x-csrf-token")
        if not csrf_cookie or not csrf_header or not secrets.compare_digest(
            csrf_cookie,
            csrf_header,
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="CSRF validation failed.",
            )

    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
            audience=settings.access_token_audience,
            issuer=settings.access_token_issuer,
        )
        claims = TokenClaims.model_validate(payload)
    except (InvalidTokenError, ValidationError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token.",
        ) from exc

    await set_tenant_context(db, claims.tenant_id)

    user = await db.scalar(
        select(User).where(
            User.id == claims.sub,
            User.status == UserStatus.ACTIVE,
            User.token_version == claims.token_version,
        )
    )
    tenant = await db.scalar(
        select(Tenant).where(
            Tenant.id == claims.tenant_id,
            Tenant.is_active.is_(True),
        )
    )
    membership = await db.scalar(
        select(TenantMembership).where(
            TenantMembership.user_id == claims.sub,
            TenantMembership.tenant_id == claims.tenant_id,
            TenantMembership.is_active.is_(True),
        )
    )
    if user is None or tenant is None or membership is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="The authenticated account or tenant is no longer active.",
        )

    return CurrentPrincipal(
        subject=str(claims.sub),
        tenant_id=claims.tenant_id,
        roles=frozenset(claims.roles),
        is_platform_admin=claims.platform_admin,
    )


def require_roles(*required_roles: str) -> Callable[[CurrentPrincipal], CurrentPrincipal]:
    async def dependency(
        principal: CurrentPrincipal = Depends(get_current_principal),
    ) -> CurrentPrincipal:
        if principal.is_platform_admin:
            return principal
        if not principal.roles.intersection(required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions.",
            )
        return principal

    return dependency
