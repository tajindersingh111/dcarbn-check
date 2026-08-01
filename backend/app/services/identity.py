from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.dependencies import CurrentPrincipal
from app.auth.security import (
    create_access_token,
    generate_opaque_token,
    hash_opaque_token,
    hash_password,
    normalize_email,
    password_needs_rehash,
    verify_password,
)
from app.core.config import get_settings
from app.models.identity import (
    InvitationStatus,
    MembershipRole,
    RefreshSession,
    Role,
    TenantMembership,
    User,
    UserInvitation,
    UserStatus,
)
from app.models.tenant import Tenant
from app.schemas.identity import (
    CurrentUserResponse,
    InvitationAccept,
    InvitationCreate,
    LoginRequest,
    MembershipResponse,
    TenantOnboardingRequest,
    TokenResponse,
)
from app.services.audit import record_audit_event
from app.services.security_events import record_security_event

SYSTEM_ROLES: dict[str, tuple[str, str]] = {
    "tenant_admin": ("Tenant administrator", "Manage tenant configuration and users."),
    "sustainability_manager": ("Sustainability manager", "Manage inventories and calculations."),
    "data_contributor": ("Data contributor", "Create and update activity data."),
    "data_reviewer": ("Data reviewer", "Review imported operational data."),
    "inventory_approver": ("Inventory approver", "Approve and lock inventories."),
    "integration_client": ("Integration client", "Submit authenticated integration payloads."),
    "auditor": ("Auditor", "Read audit-ready inventory evidence and reports."),
}


async def ensure_system_roles(db: AsyncSession, tenant_id: UUID) -> dict[str, Role]:
    existing = list(
        (
            await db.scalars(
                select(Role).where(Role.tenant_id == tenant_id)
            )
        ).all()
    )
    by_name = {role.name: role for role in existing}
    for name, (display_name, description) in SYSTEM_ROLES.items():
        if name not in by_name:
            role = Role(
                tenant_id=tenant_id,
                name=name,
                display_name=display_name,
                description=description,
                is_system=True,
                is_active=True,
            )
            db.add(role)
            by_name[name] = role
    await db.flush()
    return by_name


async def authenticate(
    db: AsyncSession,
    payload: LoginRequest,
    *,
    user_agent: str | None,
    ip_address: str | None,
) -> TokenResponse:
    tenant = await db.scalar(
        select(Tenant).where(
            Tenant.slug == payload.tenant_slug,
            Tenant.is_active.is_(True),
        )
    )
    user = await db.scalar(
        select(User).where(
            User.email_normalized == normalize_email(str(payload.email))
        )
    )
    if tenant is None or user is None or not verify_password(user.password_hash, payload.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email, password, or tenant.",
        )
    if user.status != UserStatus.ACTIVE:
        raise HTTPException(status_code=403, detail="The user account is not active.")

    membership = await db.scalar(
        select(TenantMembership)
        .options(
            selectinload(TenantMembership.roles).selectinload(MembershipRole.role)
        )
        .where(
            TenantMembership.tenant_id == tenant.id,
            TenantMembership.user_id == user.id,
            TenantMembership.is_active.is_(True),
        )
    )
    if membership is None:
        raise HTTPException(status_code=403, detail="No active tenant membership exists.")

    roles = sorted(
        item.role.name
        for item in membership.roles
        if item.role.is_active
    )
    if user.password_hash and password_needs_rehash(user.password_hash):
        user.password_hash = hash_password(payload.password)

    now = datetime.now(UTC)
    user.last_login_at = now
    access_token, access_expires_at = create_access_token(
        user_id=user.id,
        tenant_id=tenant.id,
        roles=roles,
        is_platform_admin=user.is_platform_admin,
        token_version=user.token_version,
    )
    refresh_token, refresh_expires_at = await _create_refresh_session(
        db,
        user=user,
        tenant_id=tenant.id,
        user_agent=user_agent,
        ip_address=ip_address,
    )
    await db.commit()
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        access_token_expires_at=access_expires_at,
        refresh_token_expires_at=refresh_expires_at,
    )


async def rotate_refresh_token(
    db: AsyncSession,
    refresh_token: str,
    *,
    user_agent: str | None,
    ip_address: str | None,
) -> TokenResponse:
    now = datetime.now(UTC)
    session = await db.scalar(
        select(RefreshSession)
        .options(selectinload(RefreshSession.user))
        .where(RefreshSession.token_hash == hash_opaque_token(refresh_token))
    )
    if session is None or session.revoked_at is not None or session.expires_at <= now:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token.")

    user = session.user
    if user.status != UserStatus.ACTIVE:
        raise HTTPException(status_code=403, detail="The user account is not active.")

    tenant = await db.scalar(
        select(Tenant).where(
            Tenant.id == session.tenant_id,
            Tenant.is_active.is_(True),
        )
    )
    membership = await db.scalar(
        select(TenantMembership)
        .options(
            selectinload(TenantMembership.roles).selectinload(MembershipRole.role)
        )
        .where(
            TenantMembership.tenant_id == session.tenant_id,
            TenantMembership.user_id == user.id,
            TenantMembership.is_active.is_(True),
        )
    )
    if tenant is None or membership is None:
        raise HTTPException(status_code=403, detail="Tenant access is no longer active.")

    roles = sorted(item.role.name for item in membership.roles if item.role.is_active)
    session.revoked_at = now
    session.last_used_at = now
    new_token, new_expires_at = await _create_refresh_session(
        db,
        user=user,
        tenant_id=session.tenant_id,
        user_agent=user_agent,
        ip_address=ip_address,
    )
    replacement = await db.scalar(
        select(RefreshSession).where(
            RefreshSession.token_hash == hash_opaque_token(new_token)
        )
    )
    session.replaced_by_session_id = replacement.id if replacement else None

    access_token, access_expires_at = create_access_token(
        user_id=user.id,
        tenant_id=session.tenant_id,
        roles=roles,
        is_platform_admin=user.is_platform_admin,
        token_version=user.token_version,
    )
    await db.commit()
    return TokenResponse(
        access_token=access_token,
        refresh_token=new_token,
        access_token_expires_at=access_expires_at,
        refresh_token_expires_at=new_expires_at,
    )


async def revoke_refresh_token(db: AsyncSession, refresh_token: str) -> None:
    session = await db.scalar(
        select(RefreshSession).where(
            RefreshSession.token_hash == hash_opaque_token(refresh_token)
        )
    )
    if session is not None and session.revoked_at is None:
        session.revoked_at = datetime.now(UTC)
        await db.commit()


async def current_user(
    db: AsyncSession,
    principal: CurrentPrincipal,
) -> CurrentUserResponse:
    user = await db.get(User, UUID(principal.subject))
    tenant = await db.get(Tenant, principal.tenant_id)
    if user is None or tenant is None:
        raise HTTPException(status_code=404, detail="User context was not found.")
    return CurrentUserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        tenant_id=tenant.id,
        tenant_name=tenant.name,
        tenant_slug=tenant.slug,
        roles=sorted(principal.roles),
        is_platform_admin=user.is_platform_admin,
    )


async def create_invitation(
    db: AsyncSession,
    principal: CurrentPrincipal,
    payload: InvitationCreate,
) -> tuple[UserInvitation, str]:
    roles = await _get_roles(db, principal.tenant_id, payload.role_names)
    normalized = normalize_email(str(payload.email))
    now = datetime.now(UTC)
    existing = await db.scalar(
        select(UserInvitation).where(
            UserInvitation.tenant_id == principal.tenant_id,
            UserInvitation.email_normalized == normalized,
            UserInvitation.status == InvitationStatus.PENDING,
            UserInvitation.expires_at > now,
        )
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="A pending invitation already exists.")

    raw_token = generate_opaque_token()
    invitation = UserInvitation(
        tenant_id=principal.tenant_id,
        email=str(payload.email),
        email_normalized=normalized,
        full_name=payload.full_name,
        token_hash=hash_opaque_token(raw_token),
        status=InvitationStatus.PENDING,
        role_names=",".join(sorted(role.name for role in roles)),
        invited_by_user_id=UUID(principal.subject),
        expires_at=now + timedelta(hours=get_settings().invitation_hours),
    )
    db.add(invitation)
    await record_audit_event(
        db,
        principal,
        action="identity.invitation.created",
        entity_type="user_invitation",
        entity_id=invitation.id,
        event_data={"email": invitation.email, "roles": payload.role_names},
    )
    await record_security_event(
        db,
        event_type="invitation.created",
        description="A tenant user invitation was created.",
        success=True,
        tenant_id=principal.tenant_id,
        user_id=UUID(principal.subject),
        event_data={"email": invitation.email, "roles": payload.role_names},
    )
    await db.commit()
    await db.refresh(invitation)
    return invitation, raw_token


async def accept_invitation(
    db: AsyncSession,
    payload: InvitationAccept,
) -> User:
    now = datetime.now(UTC)
    invitation = await db.scalar(
        select(UserInvitation).where(
            UserInvitation.token_hash == hash_opaque_token(payload.token)
        )
    )
    if (
        invitation is None
        or invitation.status != InvitationStatus.PENDING
        or invitation.expires_at <= now
    ):
        raise HTTPException(status_code=400, detail="Invitation is invalid or expired.")

    user = await db.scalar(
        select(User).where(User.email_normalized == invitation.email_normalized)
    )
    if user is None:
        user = User(
            email=invitation.email,
            email_normalized=invitation.email_normalized,
            full_name=invitation.full_name,
            status=UserStatus.ACTIVE,
            password_hash=hash_password(payload.password),
            email_verified_at=now,
            password_changed_at=now,
        )
        db.add(user)
        await db.flush()
    else:
        user.full_name = invitation.full_name
        user.password_hash = hash_password(payload.password)
        user.status = UserStatus.ACTIVE
        user.email_verified_at = now
        user.password_changed_at = now
        user.token_version += 1

    membership = await db.scalar(
        select(TenantMembership).where(
            TenantMembership.tenant_id == invitation.tenant_id,
            TenantMembership.user_id == user.id,
        )
    )
    if membership is None:
        membership = TenantMembership(
            tenant_id=invitation.tenant_id,
            user_id=user.id,
            is_active=True,
            invited_by_user_id=invitation.invited_by_user_id,
            joined_at=now,
        )
        db.add(membership)
        await db.flush()
    else:
        membership.is_active = True
        membership.joined_at = membership.joined_at or now

    role_names = [name for name in invitation.role_names.split(",") if name]
    roles = await _get_roles(db, invitation.tenant_id, role_names)
    await db.execute(
        delete(MembershipRole).where(MembershipRole.membership_id == membership.id)
    )
    for role in roles:
        db.add(MembershipRole(membership_id=membership.id, role_id=role.id))

    invitation.status = InvitationStatus.ACCEPTED
    invitation.accepted_at = now
    await db.commit()
    await db.refresh(user)
    return user


async def list_memberships(
    db: AsyncSession,
    tenant_id: UUID,
    limit: int,
    offset: int,
) -> tuple[list[MembershipResponse], int]:
    query = (
        select(TenantMembership)
        .options(
            selectinload(TenantMembership.user),
            selectinload(TenantMembership.roles).selectinload(MembershipRole.role),
        )
        .where(TenantMembership.tenant_id == tenant_id)
        .order_by(TenantMembership.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    count_query = (
        select(func.count())
        .select_from(TenantMembership)
        .where(TenantMembership.tenant_id == tenant_id)
    )
    memberships = list((await db.scalars(query)).all())
    total = int((await db.scalar(count_query)) or 0)
    return [
        MembershipResponse(
            id=item.id,
            user_id=item.user.id,
            tenant_id=item.tenant_id,
            email=item.user.email,
            full_name=item.user.full_name,
            user_status=item.user.status,
            is_active=item.is_active,
            roles=sorted(
                membership_role.role.name
                for membership_role in item.roles
                if membership_role.role.is_active
            ),
            joined_at=item.joined_at,
            last_login_at=item.user.last_login_at,
            failed_login_count=item.user.failed_login_count,
            locked_until=item.user.locked_until,
        )
        for item in memberships
    ], total


async def update_membership_roles(
    db: AsyncSession,
    principal: CurrentPrincipal,
    membership_id: UUID,
    role_names: list[str],
) -> MembershipResponse:
    membership = await _get_membership(db, principal.tenant_id, membership_id)
    roles = await _get_roles(db, principal.tenant_id, role_names)
    if membership.user_id == UUID(principal.subject) and "tenant_admin" not in role_names:
        raise HTTPException(
            status_code=409,
            detail="You cannot remove your own tenant administrator role.",
        )

    await db.execute(
        delete(MembershipRole).where(MembershipRole.membership_id == membership.id)
    )
    for role in roles:
        db.add(MembershipRole(membership_id=membership.id, role_id=role.id))
    membership.user.token_version += 1
    await _revoke_user_sessions(db, membership.user_id, principal.tenant_id)
    await record_audit_event(
        db,
        principal,
        action="identity.membership.roles_updated",
        entity_type="tenant_membership",
        entity_id=membership.id,
        event_data={"roles": role_names},
    )
    await record_security_event(
        db,
        event_type="membership.roles_updated",
        description="Tenant membership roles were updated.",
        success=True,
        tenant_id=principal.tenant_id,
        user_id=membership.user_id,
        event_data={"roles": role_names},
    )
    await db.commit()
    items, _ = await list_memberships(db, principal.tenant_id, 200, 0)
    return next(item for item in items if item.id == membership.id)


async def update_membership_status(
    db: AsyncSession,
    principal: CurrentPrincipal,
    membership_id: UUID,
    is_active: bool,
) -> MembershipResponse:
    membership = await _get_membership(db, principal.tenant_id, membership_id)
    if membership.user_id == UUID(principal.subject) and not is_active:
        raise HTTPException(status_code=409, detail="You cannot deactivate yourself.")
    membership.is_active = is_active
    membership.user.token_version += 1
    if not is_active:
        await _revoke_user_sessions(db, membership.user_id, principal.tenant_id)
    await record_audit_event(
        db,
        principal,
        action="identity.membership.status_updated",
        entity_type="tenant_membership",
        entity_id=membership.id,
        event_data={"is_active": is_active},
    )
    await record_security_event(
        db,
        event_type="membership.status_updated",
        description="Tenant membership access status was updated.",
        success=True,
        tenant_id=principal.tenant_id,
        user_id=membership.user_id,
        event_data={"is_active": is_active},
    )
    await db.commit()
    items, _ = await list_memberships(db, principal.tenant_id, 200, 0)
    return next(item for item in items if item.id == membership.id)


async def unlock_membership_account(
    db: AsyncSession,
    principal: CurrentPrincipal,
    membership_id: UUID,
) -> MembershipResponse:
    membership = await _get_membership(
        db,
        principal.tenant_id,
        membership_id,
    )
    membership.user.failed_login_count = 0
    membership.user.last_failed_login_at = None
    membership.user.locked_until = None

    await record_audit_event(
        db,
        principal,
        action="identity.account.unlocked",
        entity_type="tenant_membership",
        entity_id=membership.id,
        event_data={"user_id": str(membership.user_id)},
    )
    await record_security_event(
        db,
        event_type="account.unlocked",
        description="A tenant administrator manually unlocked the account.",
        success=True,
        tenant_id=principal.tenant_id,
        user_id=membership.user_id,
        event_data={"membership_id": str(membership.id)},
    )
    await db.commit()

    items, _ = await list_memberships(db, principal.tenant_id, 200, 0)
    return next(item for item in items if item.id == membership.id)


async def change_password(
    db: AsyncSession,
    principal: CurrentPrincipal,
    current_password: str,
    new_password: str,
) -> None:
    user = await db.get(User, UUID(principal.subject))
    if user is None or not verify_password(user.password_hash, current_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect.")
    user.password_hash = hash_password(new_password)
    user.password_changed_at = datetime.now(UTC)
    user.token_version += 1
    await _revoke_user_sessions(db, user.id, principal.tenant_id)
    await db.commit()


async def onboard_tenant(
    db: AsyncSession,
    principal: CurrentPrincipal,
    payload: TenantOnboardingRequest,
) -> tuple[Tenant, UserInvitation, str]:
    if not principal.is_platform_admin:
        raise HTTPException(status_code=403, detail="Platform administrator access required.")
    existing = await db.scalar(select(Tenant).where(Tenant.slug == payload.tenant_slug))
    if existing is not None:
        raise HTTPException(status_code=409, detail="Tenant slug is already in use.")

    tenant = Tenant(name=payload.tenant_name, slug=payload.tenant_slug, is_active=True)
    db.add(tenant)
    await db.flush()
    await ensure_system_roles(db, tenant.id)

    token = generate_opaque_token()
    invitation = UserInvitation(
        tenant_id=tenant.id,
        email=str(payload.owner_email),
        email_normalized=normalize_email(str(payload.owner_email)),
        full_name=payload.owner_full_name,
        token_hash=hash_opaque_token(token),
        status=InvitationStatus.PENDING,
        role_names="tenant_admin",
        invited_by_user_id=UUID(principal.subject),
        expires_at=datetime.now(UTC) + timedelta(hours=get_settings().invitation_hours),
    )
    db.add(invitation)
    await record_audit_event(
        db,
        principal,
        action="tenant.onboarded",
        entity_type="tenant",
        entity_id=tenant.id,
        event_data={
            "tenant_slug": tenant.slug,
            "owner_email": invitation.email,
        },
    )
    await db.commit()
    await db.refresh(tenant)
    await db.refresh(invitation)
    return tenant, invitation, token


async def _create_refresh_session(
    db: AsyncSession,
    *,
    user: User,
    tenant_id: UUID,
    user_agent: str | None,
    ip_address: str | None,
) -> tuple[str, datetime]:
    token = generate_opaque_token()
    expires_at = datetime.now(UTC) + timedelta(days=get_settings().refresh_token_days)
    session = RefreshSession(
        user_id=user.id,
        tenant_id=tenant_id,
        token_hash=hash_opaque_token(token),
        expires_at=expires_at,
        user_agent=user_agent,
        ip_address=ip_address,
    )
    db.add(session)
    await db.flush()
    return token, expires_at


async def _get_roles(
    db: AsyncSession,
    tenant_id: UUID,
    role_names: list[str],
) -> list[Role]:
    roles = list(
        (
            await db.scalars(
                select(Role).where(
                    Role.tenant_id == tenant_id,
                    Role.name.in_(role_names),
                    Role.is_active.is_(True),
                )
            )
        ).all()
    )
    if {role.name for role in roles} != set(role_names):
        raise HTTPException(status_code=422, detail="One or more roles are invalid.")
    return roles


async def _get_membership(
    db: AsyncSession,
    tenant_id: UUID,
    membership_id: UUID,
) -> TenantMembership:
    membership = await db.scalar(
        select(TenantMembership)
        .options(
            selectinload(TenantMembership.user),
            selectinload(TenantMembership.roles).selectinload(MembershipRole.role),
        )
        .where(
            TenantMembership.id == membership_id,
            TenantMembership.tenant_id == tenant_id,
        )
    )
    if membership is None:
        raise HTTPException(status_code=404, detail="Membership not found.")
    return membership


async def _revoke_user_sessions(
    db: AsyncSession,
    user_id: UUID,
    tenant_id: UUID,
) -> None:
    now = datetime.now(UTC)
    sessions = list(
        (
            await db.scalars(
                select(RefreshSession).where(
                    RefreshSession.user_id == user_id,
                    RefreshSession.tenant_id == tenant_id,
                    RefreshSession.revoked_at.is_(None),
                )
            )
        ).all()
    )
    for session in sessions:
        session.revoked_at = now
