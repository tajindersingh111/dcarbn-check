from __future__ import annotations

import argparse
import asyncio
import getpass
import re
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import hash_password, normalize_email
from app.db.session import AsyncSessionFactory
from app.models.identity import MembershipRole, TenantMembership, User, UserStatus
from app.models.tenant import Tenant
from app.services.identity import ensure_system_roles

TENANT_SLUG_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{1,98}[a-z0-9]$")


async def bootstrap_platform_admin(
    db: AsyncSession,
    *,
    tenant_name: str,
    tenant_slug: str,
    email: str,
    full_name: str,
    password: str,
) -> User:
    if await db.scalar(select(User).where(User.is_platform_admin.is_(True))):
        raise RuntimeError("A platform administrator already exists; bootstrap is disabled.")
    if await db.scalar(select(Tenant).where(Tenant.slug == tenant_slug)):
        raise RuntimeError("The requested bootstrap tenant slug already exists.")
    if not TENANT_SLUG_PATTERN.fullmatch(tenant_slug):
        raise ValueError("Tenant slug must contain lowercase letters, numbers and hyphens.")
    if len(password) < 12:
        raise ValueError("Password must contain at least 12 characters.")

    now = datetime.now(UTC)
    tenant = Tenant(name=tenant_name, slug=tenant_slug, is_active=True)
    db.add(tenant)
    await db.flush()
    roles = await ensure_system_roles(db, tenant.id)

    user = User(
        email=email.strip(),
        email_normalized=normalize_email(email),
        full_name=full_name.strip(),
        password_hash=hash_password(password),
        status=UserStatus.ACTIVE,
        is_platform_admin=True,
        email_verified_at=now,
        password_changed_at=now,
    )
    db.add(user)
    await db.flush()

    membership = TenantMembership(
        tenant_id=tenant.id,
        user_id=user.id,
        is_active=True,
        joined_at=now,
    )
    db.add(membership)
    await db.flush()
    db.add(MembershipRole(membership_id=membership.id, role_id=roles["tenant_admin"].id))
    await db.commit()
    await db.refresh(user)
    return user


def _read_password(path: str | None) -> str:
    if path:
        password = Path(path).read_text(encoding="utf-8").strip()
        if not password:
            raise ValueError("The password file is empty.")
        return password
    first = getpass.getpass("Initial administrator password: ")
    second = getpass.getpass("Confirm password: ")
    if first != second:
        raise ValueError("Passwords do not match.")
    return first


async def _run(args: argparse.Namespace) -> None:
    password = _read_password(args.password_file)
    async with AsyncSessionFactory() as db:
        user = await bootstrap_platform_admin(
            db,
            tenant_name=args.tenant_name,
            tenant_slug=args.tenant_slug,
            email=args.email,
            full_name=args.full_name,
            password=password,
        )
    print(f"Platform administrator created for {user.email}.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create the one-time initial tenant and platform administrator."
    )
    parser.add_argument("--tenant-name", required=True)
    parser.add_argument("--tenant-slug", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--full-name", required=True)
    parser.add_argument(
        "--password-file",
        help="Read the password from a protected file; otherwise prompt securely.",
    )
    asyncio.run(_run(parser.parse_args()))


if __name__ == "__main__":
    main()
