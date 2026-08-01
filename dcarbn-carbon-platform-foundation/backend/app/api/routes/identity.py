from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Cookie, Depends, Query, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentPrincipal, get_current_principal, require_roles
from app.core.config import get_settings
from app.db.session import get_db
from app.models.identity import Role
from app.models.tenant import Tenant
from app.schemas.identity import (
    ChangePasswordRequest,
    CurrentUserResponse,
    InvitationAccept,
    InvitationCreate,
    InvitationCreatedResponse,
    LoginRequest,
    MembershipListResponse,
    MembershipResponse,
    MembershipRolesUpdate,
    MembershipStatusUpdate,
    RoleCreate,
    RoleResponse,
    TenantOnboardingRequest,
    TenantOnboardingResponse,
)
from app.schemas.security import CookieSessionResponse, MfaVerifyLoginRequest
from app.services.email_delivery import send_invitation_email
from app.services.identity import (
    accept_invitation,
    change_password,
    create_invitation,
    current_user,
    ensure_system_roles,
    list_memberships,
    onboard_tenant,
    update_membership_roles,
    update_membership_status,
    unlock_membership_account,
)
from app.services.session_auth import (
    authenticate_for_cookie_session,
    complete_mfa_login,
    revoke_refresh_cookie_session,
    rotate_cookie_session,
)

router = APIRouter()
tenant_admin = Depends(require_roles("tenant_admin"))


def _client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",", 1)[0].strip()
    return request.client.host if request.client else None


def _set_session_cookies(response: Response, session: object) -> None:
    settings = get_settings()
    secure = settings.cookie_secure
    response.set_cookie(
        "dcarbn_access",
        session.access_token,
        max_age=settings.access_token_minutes * 60,
        httponly=True,
        secure=secure,
        samesite=settings.cookie_samesite,
        path="/",
        domain=settings.cookie_domain,
    )
    response.set_cookie(
        "dcarbn_refresh",
        session.refresh_token,
        max_age=settings.refresh_token_days * 86400,
        httponly=True,
        secure=secure,
        samesite=settings.cookie_samesite,
        path=f"{settings.api_v1_prefix}/auth",
        domain=settings.cookie_domain,
    )
    response.set_cookie(
        "dcarbn_csrf",
        session.csrf_token,
        max_age=settings.refresh_token_days * 86400,
        httponly=False,
        secure=secure,
        samesite=settings.cookie_samesite,
        path="/",
        domain=settings.cookie_domain,
    )


def _clear_session_cookies(response: Response) -> None:
    settings = get_settings()
    for name, path in (
        ("dcarbn_access", "/"),
        ("dcarbn_refresh", f"{settings.api_v1_prefix}/auth"),
        ("dcarbn_csrf", "/"),
    ):
        response.delete_cookie(
            name,
            path=path,
            domain=settings.cookie_domain,
            secure=settings.cookie_secure,
            samesite=settings.cookie_samesite,
        )


@router.post("/auth/login", response_model=CookieSessionResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> CookieSessionResponse:
    outcome = await authenticate_for_cookie_session(
        db,
        payload,
        user_agent=request.headers.get("user-agent"),
        ip_address=_client_ip(request),
        correlation_id=request.headers.get("x-correlation-id"),
    )
    if outcome.requires_mfa:
        return CookieSessionResponse(
            authenticated=False,
            requires_mfa=True,
            mfa_challenge_token=outcome.challenge_token,
        )
    assert outcome.session is not None
    _set_session_cookies(response, outcome.session)
    return CookieSessionResponse(
        authenticated=True,
        requires_mfa=False,
        access_token_expires_at=outcome.session.access_expires_at,
    )


@router.post("/auth/mfa/verify", response_model=CookieSessionResponse)
async def verify_login_mfa(
    payload: MfaVerifyLoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> CookieSessionResponse:
    session = await complete_mfa_login(
        db,
        challenge_token=payload.challenge_token,
        code=payload.code,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
        correlation_id=request.headers.get("x-correlation-id"),
    )
    _set_session_cookies(response, session)
    return CookieSessionResponse(
        authenticated=True,
        requires_mfa=False,
        access_token_expires_at=session.access_expires_at,
    )


@router.post("/auth/refresh", response_model=CookieSessionResponse)
async def refresh(
    request: Request,
    response: Response,
    refresh_token: str | None = Cookie(default=None, alias="dcarbn_refresh"),
    db: AsyncSession = Depends(get_db),
) -> CookieSessionResponse:
    if not refresh_token:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Refresh session is missing.")
    session = await rotate_cookie_session(
        db,
        refresh_token=refresh_token,
        user_agent=request.headers.get("user-agent"),
        ip_address=_client_ip(request),
        correlation_id=request.headers.get("x-correlation-id"),
    )
    _set_session_cookies(response, session)
    return CookieSessionResponse(
        authenticated=True,
        access_token_expires_at=session.access_expires_at,
    )


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    refresh_token: str | None = Cookie(default=None, alias="dcarbn_refresh"),
    db: AsyncSession = Depends(get_db),
) -> None:
    await revoke_refresh_cookie_session(db, refresh_token)
    _clear_session_cookies(response)


@router.get("/auth/me", response_model=CurrentUserResponse)
async def me(
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> CurrentUserResponse:
    return await current_user(db, principal)


@router.post("/auth/invitations/accept", status_code=status.HTTP_204_NO_CONTENT)
async def accept(
    payload: InvitationAccept,
    db: AsyncSession = Depends(get_db),
) -> None:
    await accept_invitation(db, payload)


@router.post("/auth/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def update_password(
    payload: ChangePasswordRequest,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> None:
    await change_password(
        db,
        principal,
        payload.current_password,
        payload.new_password,
    )


@router.post(
    "/users/invitations",
    response_model=InvitationCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[tenant_admin],
)
async def invite_user(
    payload: InvitationCreate,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> InvitationCreatedResponse:
    invitation, token = await create_invitation(db, principal, payload)
    tenant = await db.get(Tenant, principal.tenant_id)
    await send_invitation_email(
        to_address=invitation.email,
        full_name=invitation.full_name,
        invitation_url=f"{get_settings().frontend_base_url}/accept-invitation?token={token}",
        tenant_name=tenant.name if tenant else "D-carbN",
    )
    return InvitationCreatedResponse(
        id=invitation.id,
        tenant_id=invitation.tenant_id,
        email=invitation.email,
        full_name=invitation.full_name,
        status=invitation.status,
        role_names=[name for name in invitation.role_names.split(",") if name],
        expires_at=invitation.expires_at,
        created_at=invitation.created_at,
        invitation_token=token if get_settings().expose_tokens_in_api else "",
    )


@router.get("/users", response_model=MembershipListResponse, dependencies=[tenant_admin])
async def users(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> MembershipListResponse:
    items, total = await list_memberships(db, principal.tenant_id, limit, offset)
    return MembershipListResponse(items=items, total=total, limit=limit, offset=offset)


@router.patch(
    "/users/{membership_id}/roles",
    response_model=MembershipResponse,
    dependencies=[tenant_admin],
)
async def update_roles(
    membership_id: UUID,
    payload: MembershipRolesUpdate,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> MembershipResponse:
    return await update_membership_roles(
        db,
        principal,
        membership_id,
        payload.role_names,
    )


@router.patch(
    "/users/{membership_id}/status",
    response_model=MembershipResponse,
    dependencies=[tenant_admin],
)
async def update_status(
    membership_id: UUID,
    payload: MembershipStatusUpdate,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> MembershipResponse:
    return await update_membership_status(
        db,
        principal,
        membership_id,
        payload.is_active,
    )


@router.post(
    "/users/{membership_id}/unlock",
    response_model=MembershipResponse,
    dependencies=[tenant_admin],
)
async def unlock_account(
    membership_id: UUID,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> MembershipResponse:
    return await unlock_membership_account(
        db,
        principal,
        membership_id,
    )


@router.get("/roles", response_model=list[RoleResponse], dependencies=[tenant_admin])
async def roles(
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> list[RoleResponse]:
    await ensure_system_roles(db, principal.tenant_id)
    await db.commit()
    items = list(
        (
            await db.scalars(
                select(Role)
                .where(Role.tenant_id == principal.tenant_id)
                .order_by(Role.display_name)
            )
        ).all()
    )
    return [RoleResponse.model_validate(item) for item in items]


@router.post(
    "/roles",
    response_model=RoleResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[tenant_admin],
)
async def create_role(
    payload: RoleCreate,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> RoleResponse:
    role = Role(
        tenant_id=principal.tenant_id,
        name=payload.name,
        display_name=payload.display_name,
        description=payload.description,
        is_system=False,
        is_active=True,
    )
    db.add(role)
    await db.commit()
    await db.refresh(role)
    return RoleResponse.model_validate(role)


@router.post(
    "/platform/tenants/onboard",
    response_model=TenantOnboardingResponse,
    status_code=status.HTTP_201_CREATED,
)
async def onboard(
    payload: TenantOnboardingRequest,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> TenantOnboardingResponse:
    tenant, invitation, token = await onboard_tenant(db, principal, payload)
    await send_invitation_email(
        to_address=invitation.email,
        full_name=invitation.full_name,
        invitation_url=f"{get_settings().frontend_base_url}/accept-invitation?token={token}",
        tenant_name=tenant.name,
    )
    return TenantOnboardingResponse(
        tenant_id=tenant.id,
        tenant_name=tenant.name,
        tenant_slug=tenant.slug,
        owner_email=invitation.email,
        invitation_token=token if get_settings().expose_tokens_in_api else "",
        invitation_expires_at=invitation.expires_at,
    )
