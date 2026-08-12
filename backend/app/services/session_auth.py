from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth.mfa import consume_recovery_code, decrypt_secret, verify_totp
from app.auth.security import (
    create_access_token,
    generate_opaque_token,
    hash_opaque_token,
    normalize_email,
    password_needs_rehash,
    hash_password,
    verify_password,
)
from app.core.config import get_settings
from app.db.tenant_context import bootstrap_auth_tenant, set_tenant_context
from app.models.identity import (
    MembershipRole,
    RefreshSession,
    TenantMembership,
    User,
    UserStatus,
)
from app.models.security import MfaChallenge, SecurityEventSeverity
from app.models.tenant import Tenant
from app.schemas.identity import LoginRequest
from app.services.security_events import record_security_event


@dataclass(frozen=True, slots=True)
class IssuedSession:
    access_token: str
    refresh_token: str
    csrf_token: str
    access_expires_at: datetime
    refresh_expires_at: datetime


@dataclass(frozen=True, slots=True)
class LoginOutcome:
    requires_mfa: bool
    challenge_token: str | None
    session: IssuedSession | None


async def authenticate_for_cookie_session(
    db: AsyncSession,
    payload: LoginRequest,
    *,
    user_agent: str | None,
    ip_address: str | None,
    correlation_id: str | None,
) -> LoginOutcome:
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
    if tenant is not None:
        await set_tenant_context(db, tenant.id)

    now = datetime.now(UTC)
    if user is not None and user.locked_until is not None and user.locked_until > now:
        await record_security_event(
            db,
            event_type="login.account_locked",
            description="Login was blocked because the account is temporarily locked.",
            success=False,
            severity=SecurityEventSeverity.WARNING,
            tenant_id=tenant.id if tenant else None,
            user_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
            correlation_id=correlation_id,
            event_data={"locked_until": user.locked_until.isoformat()},
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="The account is temporarily locked. Try again later.",
        )

    valid = (
        tenant is not None
        and user is not None
        and verify_password(user.password_hash, payload.password)
    )
    if not valid:
        if user is not None:
            settings = get_settings()
            window = timedelta(minutes=settings.account_failure_window_minutes)
            if (
                user.last_failed_login_at is None
                or user.last_failed_login_at < now - window
            ):
                user.failed_login_count = 0
            user.failed_login_count += 1
            user.last_failed_login_at = now

            if user.failed_login_count >= settings.account_lockout_threshold:
                user.locked_until = now + timedelta(
                    minutes=settings.account_lockout_minutes
                )
                await record_security_event(
                    db,
                    event_type="account.locked",
                    description="The account was locked after repeated failed login attempts.",
                    success=False,
                    severity=SecurityEventSeverity.CRITICAL,
                    tenant_id=tenant.id if tenant else None,
                    user_id=user.id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    correlation_id=correlation_id,
                    event_data={
                        "failed_login_count": user.failed_login_count,
                        "locked_until": user.locked_until.isoformat(),
                    },
                )

        await record_security_event(
            db,
            event_type="login.failed",
            description="Login failed because the supplied credentials or tenant were invalid.",
            success=False,
            severity=SecurityEventSeverity.WARNING,
            tenant_id=tenant.id if tenant else None,
            user_id=user.id if user else None,
            ip_address=ip_address,
            user_agent=user_agent,
            correlation_id=correlation_id,
            event_data={"tenant_slug": payload.tenant_slug},
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email, password, or tenant.",
        )

    assert tenant is not None
    assert user is not None

    user.failed_login_count = 0
    user.last_failed_login_at = None
    user.locked_until = None

    if user.status != UserStatus.ACTIVE:
        await record_security_event(
            db,
            event_type="login.blocked",
            description="Login was blocked because the user account is not active.",
            success=False,
            severity=SecurityEventSeverity.WARNING,
            tenant_id=tenant.id,
            user_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
            correlation_id=correlation_id,
        )
        await db.commit()
        raise HTTPException(status_code=403, detail="The user account is not active.")

    membership = await _membership(db, user.id, tenant.id)
    if membership is None:
        await record_security_event(
            db,
            event_type="login.blocked",
            description="Login was blocked because no active tenant membership exists.",
            success=False,
            severity=SecurityEventSeverity.WARNING,
            tenant_id=tenant.id,
            user_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
            correlation_id=correlation_id,
        )
        await db.commit()
        raise HTTPException(status_code=403, detail="No active tenant membership exists.")

    if user.password_hash and password_needs_rehash(user.password_hash):
        user.password_hash = hash_password(payload.password)

    if user.mfa_enabled:
        challenge_token = generate_opaque_token()
        challenge = MfaChallenge(
            user_id=user.id,
            tenant_id=tenant.id,
            token_hash=hash_opaque_token(challenge_token),
            expires_at=datetime.now(UTC)
            + timedelta(minutes=get_settings().mfa_challenge_minutes),
            attempts=0,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        db.add(challenge)
        await record_security_event(
            db,
            event_type="login.mfa_required",
            description="Primary credentials were accepted and MFA verification is required.",
            success=True,
            tenant_id=tenant.id,
            user_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
            correlation_id=correlation_id,
        )
        await db.commit()
        return LoginOutcome(
            requires_mfa=True,
            challenge_token=challenge_token,
            session=None,
        )

    session = await issue_session(
        db,
        user=user,
        membership=membership,
        tenant_id=tenant.id,
        user_agent=user_agent,
        ip_address=ip_address,
    )
    user.last_login_at = datetime.now(UTC)
    await record_security_event(
        db,
        event_type="login.succeeded",
        description="User signed in successfully.",
        success=True,
        tenant_id=tenant.id,
        user_id=user.id,
        ip_address=ip_address,
        user_agent=user_agent,
        correlation_id=correlation_id,
    )
    await db.commit()
    return LoginOutcome(requires_mfa=False, challenge_token=None, session=session)


async def complete_mfa_login(
    db: AsyncSession,
    *,
    challenge_token: str,
    code: str,
    ip_address: str | None,
    user_agent: str | None,
    correlation_id: str | None,
) -> IssuedSession:
    challenge_hash = hash_opaque_token(challenge_token)
    await bootstrap_auth_tenant(
        db,
        purpose="mfa_challenge",
        token_hash=challenge_hash,
    )
    now = datetime.now(UTC)
    challenge = await db.scalar(
        select(MfaChallenge).where(
            MfaChallenge.token_hash == challenge_hash
        )
    )
    if (
        challenge is None
        or challenge.completed_at is not None
        or challenge.expires_at <= now
    ):
        raise HTTPException(status_code=401, detail="MFA challenge is invalid or expired.")

    challenge.attempts += 1
    user = await db.get(User, challenge.user_id)
    membership = await _membership(db, challenge.user_id, challenge.tenant_id)
    secret = decrypt_secret(user.mfa_secret_encrypted if user else None)

    valid = bool(secret and verify_totp(secret, code))
    if user and not valid:
        recovery_valid, updated_hashes = consume_recovery_code(
            user.mfa_recovery_codes_hashes,
            code,
        )
        if recovery_valid:
            user.mfa_recovery_codes_hashes = updated_hashes
            valid = True

    if user is None or membership is None or not valid:
        severity = (
            SecurityEventSeverity.CRITICAL
            if challenge.attempts >= get_settings().mfa_max_attempts
            else SecurityEventSeverity.WARNING
        )
        await record_security_event(
            db,
            event_type="mfa.challenge_failed",
            description="MFA verification failed.",
            success=False,
            severity=severity,
            tenant_id=challenge.tenant_id,
            user_id=challenge.user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            correlation_id=correlation_id,
            event_data={"attempts": challenge.attempts},
        )
        if challenge.attempts >= get_settings().mfa_max_attempts:
            challenge.completed_at = now
        await db.commit()
        raise HTTPException(status_code=401, detail="Invalid MFA code.")

    challenge.completed_at = now
    user.last_login_at = now
    session = await issue_session(
        db,
        user=user,
        membership=membership,
        tenant_id=challenge.tenant_id,
        user_agent=user_agent,
        ip_address=ip_address,
    )
    await record_security_event(
        db,
        event_type="mfa.challenge_succeeded",
        description="MFA verification succeeded.",
        success=True,
        tenant_id=challenge.tenant_id,
        user_id=user.id,
        ip_address=ip_address,
        user_agent=user_agent,
        correlation_id=correlation_id,
    )
    await db.commit()
    return session


async def rotate_cookie_session(
    db: AsyncSession,
    *,
    refresh_token: str,
    user_agent: str | None,
    ip_address: str | None,
    correlation_id: str | None,
) -> IssuedSession:
    refresh_hash = hash_opaque_token(refresh_token)
    await bootstrap_auth_tenant(
        db,
        purpose="refresh_session",
        token_hash=refresh_hash,
    )
    now = datetime.now(UTC)
    session = await db.scalar(
        select(RefreshSession)
        .options(selectinload(RefreshSession.user))
        .where(RefreshSession.token_hash == refresh_hash)
    )
    if session is None:
        raise HTTPException(status_code=401, detail="Invalid refresh session.")

    if session.revoked_at is not None:
        await record_security_event(
            db,
            event_type="session.reuse_detected",
            description="A revoked refresh token was presented.",
            success=False,
            severity=SecurityEventSeverity.CRITICAL,
            tenant_id=session.tenant_id,
            user_id=session.user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            correlation_id=correlation_id,
        )
        await revoke_all_user_sessions(db, session.user_id)
        await db.commit()
        raise HTTPException(status_code=401, detail="Refresh session reuse detected.")

    if session.expires_at <= now:
        raise HTTPException(status_code=401, detail="Refresh session has expired.")

    user = session.user
    membership = await _membership(db, user.id, session.tenant_id)
    tenant = await db.scalar(
        select(Tenant).where(
            Tenant.id == session.tenant_id,
            Tenant.is_active.is_(True),
        )
    )
    if (
        user.status != UserStatus.ACTIVE
        or membership is None
        or tenant is None
    ):
        raise HTTPException(status_code=403, detail="Session access is no longer active.")

    session.revoked_at = now
    session.last_used_at = now
    replacement = await issue_session(
        db,
        user=user,
        membership=membership,
        tenant_id=session.tenant_id,
        user_agent=user_agent,
        ip_address=ip_address,
    )
    replacement_row = await db.scalar(
        select(RefreshSession).where(
            RefreshSession.token_hash == hash_opaque_token(replacement.refresh_token)
        )
    )
    session.replaced_by_session_id = replacement_row.id if replacement_row else None
    await record_security_event(
        db,
        event_type="session.refreshed",
        description="Refresh session was rotated.",
        success=True,
        tenant_id=session.tenant_id,
        user_id=user.id,
        ip_address=ip_address,
        user_agent=user_agent,
        correlation_id=correlation_id,
    )
    await db.commit()
    return replacement


async def issue_session(
    db: AsyncSession,
    *,
    user: User,
    membership: TenantMembership,
    tenant_id: UUID,
    user_agent: str | None,
    ip_address: str | None,
) -> IssuedSession:
    roles = sorted(
        item.role.name
        for item in membership.roles
        if item.role.is_active
    )
    access_token, access_expires_at = create_access_token(
        user_id=user.id,
        tenant_id=tenant_id,
        roles=roles,
        is_platform_admin=user.is_platform_admin,
        token_version=user.token_version,
    )
    refresh_token = generate_opaque_token()
    csrf_token = generate_opaque_token()
    refresh_expires_at = datetime.now(UTC) + timedelta(
        days=get_settings().refresh_token_days
    )
    db.add(
        RefreshSession(
            user_id=user.id,
            tenant_id=tenant_id,
            token_hash=hash_opaque_token(refresh_token),
            expires_at=refresh_expires_at,
            user_agent=user_agent,
            ip_address=ip_address,
        )
    )
    await db.flush()
    return IssuedSession(
        access_token=access_token,
        refresh_token=refresh_token,
        csrf_token=csrf_token,
        access_expires_at=access_expires_at,
        refresh_expires_at=refresh_expires_at,
    )


async def revoke_all_user_sessions(db: AsyncSession, user_id: UUID) -> None:
    now = datetime.now(UTC)
    rows = list(
        (
            await db.scalars(
                select(RefreshSession).where(
                    RefreshSession.user_id == user_id,
                    RefreshSession.revoked_at.is_(None),
                )
            )
        ).all()
    )
    for row in rows:
        row.revoked_at = now


async def revoke_refresh_cookie_session(
    db: AsyncSession,
    refresh_token: str | None,
) -> None:
    if not refresh_token:
        return
    refresh_hash = hash_opaque_token(refresh_token)
    await bootstrap_auth_tenant(
        db,
        purpose="refresh_session",
        token_hash=refresh_hash,
    )
    row = await db.scalar(
        select(RefreshSession).where(
            RefreshSession.token_hash == refresh_hash
        )
    )
    if row and row.revoked_at is None:
        row.revoked_at = datetime.now(UTC)
        await db.commit()


async def _membership(
    db: AsyncSession,
    user_id: UUID,
    tenant_id: UUID,
) -> TenantMembership | None:
    membership: TenantMembership | None = await db.scalar(
        select(TenantMembership)
        .options(
            selectinload(TenantMembership.roles).selectinload(MembershipRole.role)
        )
        .where(
            TenantMembership.user_id == user_id,
            TenantMembership.tenant_id == tenant_id,
            TenantMembership.is_active.is_(True),
        )
    )
    return membership
