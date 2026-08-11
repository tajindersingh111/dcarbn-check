from __future__ import annotations

import asyncio
import json
import time
from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import asyncpg

MIGRATION_LOCK_ID = 4_444_227_701
SUPPORTED_RUNTIME_REVISIONS = frozenset({"0022"})


class MigrationPolicyError(RuntimeError):
    """Raised when a deployment migration does not satisfy release policy."""


class MigrationLockUnavailable(RuntimeError):
    """Raised when another deployment owns the migration advisory lock."""


@dataclass(frozen=True)
class MigrationRelease:
    target: str
    phase: str
    requires_old_replicas_retired: bool
    requires_recovery_evidence: bool


def load_release_manifest(path: Path) -> dict[str, MigrationRelease]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    releases = payload.get("releases")
    if not isinstance(releases, dict) or not releases:
        raise MigrationPolicyError("Migration release manifest has no releases.")

    parsed: dict[str, MigrationRelease] = {}
    for target, raw_release in releases.items():
        if not isinstance(target, str) or not isinstance(raw_release, dict):
            raise MigrationPolicyError("Migration release manifest is invalid.")
        phase = raw_release.get("phase")
        if phase not in {"expand", "backfill", "contract"}:
            raise MigrationPolicyError(
                f"Migration release {target!r} has an invalid phase."
            )
        parsed[target] = MigrationRelease(
            target=target,
            phase=phase,
            requires_old_replicas_retired=bool(
                raw_release.get("requires_old_replicas_retired", False)
            ),
            requires_recovery_evidence=bool(
                raw_release.get("requires_recovery_evidence", False)
            ),
        )
    return parsed


def validate_release_policy(
    releases: Mapping[str, MigrationRelease],
    *,
    target: str,
    requested_phase: str,
    old_replicas_retired: bool,
) -> MigrationRelease:
    release = releases.get(target)
    if release is None:
        raise MigrationPolicyError(
            "Migration target is not present in the reviewed release manifest."
        )
    if release.phase != requested_phase:
        raise MigrationPolicyError(
            f"Migration phase mismatch: manifest={release.phase}, "
            f"requested={requested_phase}."
        )
    if release.requires_old_replicas_retired and not old_replicas_retired:
        raise MigrationPolicyError(
            "Contract migration is blocked until old application replicas are retired."
        )
    return release


def assert_supported_schema_version(version: str | None) -> None:
    if version not in SUPPORTED_RUNTIME_REVISIONS:
        supported = ", ".join(sorted(SUPPORTED_RUNTIME_REVISIONS))
        raise MigrationPolicyError(
            f"Unsupported database schema revision {version!r}; supported: {supported}."
        )


def verify_recovery_evidence(
    *,
    backup_path: Path,
    pitr_path: Path,
    now: datetime | None = None,
    backup_max_age_seconds: int = 93_600,
    pitr_max_age_seconds: int = 93_600,
) -> dict[str, object]:
    checked_at = now or datetime.now(UTC)
    backup = _read_evidence(backup_path, "backup")
    pitr = _read_evidence(pitr_path, "PITR")

    backup_at = _verified_timestamp(
        backup,
        timestamp_key="latest_success_at",
        label="backup",
    )
    pitr_at = _verified_timestamp(
        pitr,
        timestamp_key="latest_base_backup_at",
        label="PITR",
    )
    backup_age = _age_seconds(checked_at, backup_at)
    pitr_age = _age_seconds(checked_at, pitr_at)
    if backup_age > backup_max_age_seconds:
        raise MigrationPolicyError("Backup evidence is stale.")
    if pitr_age > pitr_max_age_seconds:
        raise MigrationPolicyError("PITR evidence is stale.")

    return {
        "backup_verified": True,
        "backup_age_seconds": backup_age,
        "pitr_verified": True,
        "pitr_age_seconds": pitr_age,
    }


@asynccontextmanager
async def migration_lock(
    database_url: str,
    *,
    timeout_seconds: float,
) -> AsyncIterator[asyncpg.Connection]:
    connection = await asyncpg.connect(_asyncpg_dsn(database_url), timeout=10)
    deadline = time.monotonic() + timeout_seconds
    acquired = False
    try:
        while True:
            acquired = bool(
                await connection.fetchval(
                    "SELECT pg_try_advisory_lock($1)",
                    MIGRATION_LOCK_ID,
                )
            )
            if acquired:
                break
            if time.monotonic() >= deadline:
                raise MigrationLockUnavailable(
                    "Another controlled migration job owns the database lock."
                )
            await asyncio.sleep(min(1.0, max(deadline - time.monotonic(), 0.0)))
        yield connection
    finally:
        if acquired:
            await connection.execute(
                "SELECT pg_advisory_unlock($1)",
                MIGRATION_LOCK_ID,
            )
        await connection.close()


async def current_schema_revision(connection: asyncpg.Connection) -> str | None:
    exists = await connection.fetchval(
        "SELECT to_regclass('public.alembic_version') IS NOT NULL"
    )
    if not exists:
        return None
    value = await connection.fetchval("SELECT version_num FROM alembic_version LIMIT 1")
    return str(value) if value is not None else None


def _asyncpg_dsn(database_url: str) -> str:
    prefix = "postgresql+asyncpg://"
    if database_url.startswith(prefix):
        return "postgresql://" + database_url[len(prefix) :]
    if database_url.startswith("postgresql://"):
        return database_url
    raise MigrationPolicyError("Controlled migrations require PostgreSQL.")


def _read_evidence(path: Path, label: str) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MigrationPolicyError(f"Valid {label} evidence is required.") from exc
    if not isinstance(payload, dict):
        raise MigrationPolicyError(f"Valid {label} evidence is required.")
    return payload


def _verified_timestamp(
    payload: Mapping[str, object],
    *,
    timestamp_key: str,
    label: str,
) -> datetime:
    if payload.get("verified") is not True:
        raise MigrationPolicyError(f"{label} evidence is not verified.")
    raw_value = payload.get(timestamp_key)
    try:
        timestamp = datetime.fromisoformat(str(raw_value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise MigrationPolicyError(f"{label} evidence timestamp is invalid.") from exc
    if timestamp.tzinfo is None:
        raise MigrationPolicyError(f"{label} evidence timestamp must include a timezone.")
    return timestamp.astimezone(UTC)


def _age_seconds(now: datetime, timestamp: datetime) -> int:
    return max(int((now.astimezone(UTC) - timestamp).total_seconds()), 0)
