from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentPrincipal, get_current_principal, require_roles
from app.auth.mfa import (
    consume_recovery_code,
    decrypt_secret,
    encode_recovery_hashes,
    encrypt_secret,
    generate_recovery_codes,
    generate_totp_secret,
    provisioning_uri,
    verify_totp,
)
from app.auth.security import generate_opaque_token, hash_opaque_token, hash_password, verify_password
from app.core.client_ip import get_client_ip
from app.core.config import get_settings
from app.db.session import get_db
from app.models.identity import User
from app.models.security import MfaChallenge, PasswordResetStatus, PasswordResetToken
from app.models.security import SecurityEventSeverity
from app.schemas.security import (
    MfaDisableRequest,
    MfaEnrollmentConfirmRequest,
    MfaEnrollmentConfirmResponse,
    MfaEnrollmentStartResponse,
    PasswordResetConfirm,
    PasswordResetRequest,
    SecurityEventListResponse,
    SecurityEventResponse,
)
from app.services.email_delivery import send_password_reset_email
from app.services.session_auth import revoke_all_user_sessions
from app.services.security_events import list_security_events, record_security_event

router = APIRouter()


@router.post("/auth/mfa/enroll", response_model=MfaEnrollmentStartResponse)
async def start_mfa_enrollment(
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> MfaEnrollmentStartResponse:
    user = await db.get(User, UUID(principal.subject))
    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")
    secret = generate_totp_secret()
    user.mfa_pending_secret_encrypted = encrypt_secret(secret)
    await db.commit()
    return MfaEnrollmentStartResponse(
        secret=secret,
        provisioning_uri=provisioning_uri(secret, user.email),
    )


@router.post("/auth/mfa/confirm", response_model=MfaEnrollmentConfirmResponse)
async def confirm_mfa_enrollment(
    payload: MfaEnrollmentConfirmRequest,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> MfaEnrollmentConfirmResponse:
    user = await db.get(User, UUID(principal.subject))
    secret = decrypt_secret(user.mfa_pending_secret_encrypted if user else None)
    if user is None or secret is None or not verify_totp(secret, payload.code):
        raise HTTPException(status_code=400, detail="Invalid MFA enrollment code.")

    recovery_codes = generate_recovery_codes()
    user.mfa_secret_encrypted = encrypt_secret(secret)
    user.mfa_pending_secret_encrypted = None
    user.mfa_recovery_codes_hashes = encode_recovery_hashes(recovery_codes)
    user.mfa_enabled = True
    user.mfa_enabled_at = datetime.now(UTC)
    user.token_version += 1
    await revoke_all_user_sessions(db, user.id)
    await record_security_event(
        db,
        event_type="mfa.enabled",
        description="Multi-factor authentication was enabled.",
        success=True,
        tenant_id=principal.tenant_id,
        user_id=user.id,
    )
    await db.commit()
    return MfaEnrollmentConfirmResponse(recovery_codes=recovery_codes)


@router.post("/auth/mfa/disable", status_code=status.HTTP_204_NO_CONTENT)
async def disable_mfa(
    payload: MfaDisableRequest,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> None:
    user = await db.get(User, UUID(principal.subject))
    secret = decrypt_secret(user.mfa_secret_encrypted if user else None)
    valid_code = bool(secret and verify_totp(secret, payload.code))
    recovery_valid = False
    if user and not valid_code:
        recovery_valid, updated = consume_recovery_code(
            user.mfa_recovery_codes_hashes,
            payload.code,
        )
        if recovery_valid:
            user.mfa_recovery_codes_hashes = updated

    if (
        user is None
        or not verify_password(user.password_hash, payload.password)
        or not (valid_code or recovery_valid)
    ):
        raise HTTPException(status_code=400, detail="Password or MFA code is invalid.")

    user.mfa_enabled = False
    user.mfa_secret_encrypted = None
    user.mfa_pending_secret_encrypted = None
    user.mfa_recovery_codes_hashes = None
    user.mfa_enabled_at = None
    user.token_version += 1
    await revoke_all_user_sessions(db, user.id)
    await record_security_event(
        db,
        event_type="mfa.disabled",
        description="Multi-factor authentication was disabled.",
        success=True,
        severity=SecurityEventSeverity.WARNING,
        tenant_id=principal.tenant_id,
        user_id=user.id,
    )
    await db.commit()


@router.post("/auth/password-reset/request", status_code=status.HTTP_202_ACCEPTED)
async def request_password_reset(
    payload: PasswordResetRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    from app.auth.security import normalize_email
    from app.models.identity import TenantMembership
    from app.models.tenant import Tenant

    tenant = await db.scalar(select(Tenant).where(Tenant.slug == payload.tenant_slug))
    user = await db.scalar(
        select(User).where(User.email_normalized == normalize_email(str(payload.email)))
    )
    if tenant and user:
        membership = await db.scalar(
            select(TenantMembership).where(
                TenantMembership.tenant_id == tenant.id,
                TenantMembership.user_id == user.id,
                TenantMembership.is_active.is_(True),
            )
        )
        if membership:
            raw_token = generate_opaque_token()
            reset = PasswordResetToken(
                user_id=user.id,
                tenant_id=tenant.id,
                token_hash=hash_opaque_token(raw_token),
                status=PasswordResetStatus.PENDING,
                expires_at=datetime.now(UTC)
                + timedelta(minutes=get_settings().password_reset_minutes),
                requested_ip=get_client_ip(request),
            )
            db.add(reset)
            await record_security_event(
                db,
                event_type="password_reset.requested",
                description="A password reset was requested.",
                success=True,
                tenant_id=tenant.id,
                user_id=user.id,
                ip_address=get_client_ip(request),
                user_agent=request.headers.get("user-agent"),
            )
            await db.commit()
            await send_password_reset_email(
                to_address=user.email,
                full_name=user.full_name,
                reset_url=f"{get_settings().frontend_base_url}/reset-password?token={raw_token}",
            )
    return {"message": "If the account exists, password reset instructions have been sent."}


@router.post("/auth/password-reset/confirm", status_code=status.HTTP_204_NO_CONTENT)
async def confirm_password_reset(
    payload: PasswordResetConfirm,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> None:
    reset = await db.scalar(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == hash_opaque_token(payload.token)
        )
    )
    now = datetime.now(UTC)
    if (
        reset is None
        or reset.status != PasswordResetStatus.PENDING
        or reset.expires_at <= now
    ):
        raise HTTPException(status_code=400, detail="Password reset token is invalid or expired.")

    user = await db.get(User, reset.user_id)
    if user is None:
        raise HTTPException(status_code=400, detail="Password reset token is invalid.")

    user.password_hash = hash_password(payload.password)
    user.password_changed_at = now
    user.token_version += 1
    reset.status = PasswordResetStatus.USED
    reset.used_at = now
    await revoke_all_user_sessions(db, user.id)
    await record_security_event(
        db,
        event_type="password_reset.completed",
        description="Password reset completed and all sessions were revoked.",
        success=True,
        severity=SecurityEventSeverity.WARNING,
        tenant_id=reset.tenant_id,
        user_id=user.id,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    await db.commit()


@router.get(
    "/security/events",
    response_model=SecurityEventListResponse,
    dependencies=[Depends(require_roles("tenant_admin", "auditor"))],
)
async def security_events(
    severity: SecurityEventSeverity | None = None,
    event_type: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> SecurityEventListResponse:
    items, total = await list_security_events(
        db,
        tenant_id=principal.tenant_id,
        platform_admin=principal.is_platform_admin,
        limit=limit,
        offset=offset,
        severity=severity,
        event_type=event_type,
    )
    return SecurityEventListResponse(
        items=[SecurityEventResponse.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )
