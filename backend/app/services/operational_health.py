from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from pathlib import Path

from redis.exceptions import RedisError
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.observability import (
    BACKUP_AGE_SECONDS,
    BACKUP_SUCCESS,
    DEPENDENCY_HEALTH,
    FAILOVER_REGION_STATE,
    PITR_BASE_BACKUP_AGE_SECONDS,
    PITR_READINESS,
    WAL_ARCHIVE_AGE_SECONDS,
    WAL_ARCHIVE_HEALTH,
)
from app.core.redis import get_redis
from app.schemas.operations import (
    BackupStatus,
    DependencyStatus,
    OperationalHealthResponse,
    FailoverStatus,
    PitrStatus,
    RecoveryReadinessResponse,
    WalArchiveStatus,
)


async def operational_health(
    db: AsyncSession,
) -> OperationalHealthResponse:
    database = await _database_health(db)
    redis = await _redis_health()
    backup = _backup_health()
    overall = (
        "ok"
        if database.status == "ok"
        and redis.status == "ok"
        and backup.status == "ok"
        else "degraded"
    )
    return OperationalHealthResponse(
        status=overall,
        timestamp=datetime.now(UTC),
        database=database,
        redis=redis,
        backup=backup,
    )


async def _database_health(db: AsyncSession) -> DependencyStatus:
    started = time.perf_counter()
    try:
        await db.execute(text("SELECT 1"))
    except Exception as exc:
        DEPENDENCY_HEALTH.labels(dependency="postgresql").set(0)
        return DependencyStatus(status="error", detail=type(exc).__name__)

    latency_ms = (time.perf_counter() - started) * 1000
    DEPENDENCY_HEALTH.labels(dependency="postgresql").set(1)
    return DependencyStatus(status="ok", latency_ms=round(latency_ms, 2))


async def _redis_health() -> DependencyStatus:
    started = time.perf_counter()
    try:
        await get_redis().ping()
    except RedisError as exc:
        DEPENDENCY_HEALTH.labels(dependency="redis").set(0)
        return DependencyStatus(status="error", detail=type(exc).__name__)

    latency_ms = (time.perf_counter() - started) * 1000
    DEPENDENCY_HEALTH.labels(dependency="redis").set(1)
    return DependencyStatus(status="ok", latency_ms=round(latency_ms, 2))


def _backup_health() -> BackupStatus:
    settings = get_settings()
    path = Path(settings.backup_status_file)
    if not path.is_file():
        BACKUP_SUCCESS.set(0)
        return BackupStatus(status="unknown")

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        success_at = datetime.fromisoformat(
            str(payload["latest_success_at"]).replace("Z", "+00:00")
        )
        age_seconds = max(
            int((datetime.now(UTC) - success_at.astimezone(UTC)).total_seconds()),
            0,
        )
        verified = bool(payload.get("verified"))
        fresh = age_seconds <= settings.backup_max_age_seconds
        healthy = verified and fresh
        BACKUP_SUCCESS.set(1 if healthy else 0)
        BACKUP_AGE_SECONDS.set(age_seconds)
        return BackupStatus(
            status="ok" if healthy else "stale",
            latest_success_at=success_at,
            age_seconds=age_seconds,
            backup_id=payload.get("backup_id"),
            verified=verified,
        )
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        BACKUP_SUCCESS.set(0)
        return BackupStatus(status="invalid")



def recovery_readiness() -> RecoveryReadinessResponse:
    wal = _wal_archive_health()
    pitr = _pitr_health()
    failover = _failover_health()

    healthy = (
        wal.status == "ok"
        and pitr.status == "ok"
        and failover.status in {"primary", "standby", "promoted"}
    )
    return RecoveryReadinessResponse(
        status="ok" if healthy else "degraded",
        timestamp=datetime.now(UTC),
        wal_archive=wal,
        pitr=pitr,
        failover=failover,
    )


def _wal_archive_health() -> WalArchiveStatus:
    settings = get_settings()
    payload = _read_json(settings.wal_archive_status_file)
    if payload is None:
        WAL_ARCHIVE_HEALTH.set(0)
        return WalArchiveStatus(status="unknown")

    timestamp = _parse_timestamp(payload.get("latest_archived_at"))
    if timestamp is None:
        WAL_ARCHIVE_HEALTH.set(0)
        return WalArchiveStatus(status="invalid")

    age_seconds = _age_seconds(timestamp)
    healthy = age_seconds <= settings.wal_archive_max_age_seconds
    WAL_ARCHIVE_AGE_SECONDS.set(age_seconds)
    WAL_ARCHIVE_HEALTH.set(1 if healthy else 0)
    return WalArchiveStatus(
        status="ok" if healthy else "stale",
        latest_wal=payload.get("latest_wal"),
        latest_archived_at=timestamp,
        age_seconds=age_seconds,
        region=payload.get("region"),
    )


def _pitr_health() -> PitrStatus:
    settings = get_settings()
    payload = _read_json(settings.pitr_status_file)
    if payload is None:
        PITR_READINESS.set(0)
        return PitrStatus(status="unknown")

    timestamp = _parse_timestamp(payload.get("latest_base_backup_at"))
    if timestamp is None:
        PITR_READINESS.set(0)
        return PitrStatus(status="invalid")

    age_seconds = _age_seconds(timestamp)
    verified = bool(payload.get("verified"))
    healthy = (
        verified
        and age_seconds <= settings.pitr_base_backup_max_age_seconds
    )
    PITR_BASE_BACKUP_AGE_SECONDS.set(age_seconds)
    PITR_READINESS.set(1 if healthy else 0)
    return PitrStatus(
        status="ok" if healthy else "stale",
        latest_base_backup_id=payload.get("latest_base_backup_id"),
        latest_base_backup_at=timestamp,
        age_seconds=age_seconds,
        verified=verified,
        region=payload.get("region"),
    )


def _failover_health() -> FailoverStatus:
    settings = get_settings()
    payload = _read_json(settings.failover_state_file)
    if payload is None:
        return FailoverStatus(status="unknown")

    status = str(payload.get("status", "unknown"))
    region = payload.get("region") or payload.get("active_region")
    if region:
        if status in {"primary", "promoted"}:
            FAILOVER_REGION_STATE.labels(region=region).set(1)
        elif status == "standby":
            FAILOVER_REGION_STATE.labels(region=region).set(0)
        else:
            FAILOVER_REGION_STATE.labels(region=region).set(-1)

    return FailoverStatus(
        status=status,
        active_region=payload.get("active_region"),
        region=payload.get("region"),
        in_recovery=payload.get("in_recovery"),
        current_lsn=payload.get("current_lsn"),
        replay_timestamp=_parse_timestamp(payload.get("replay_timestamp")),
        timeline=_optional_int(payload.get("timeline")),
        checked_at=_parse_timestamp(
            payload.get("checked_at") or payload.get("promoted_at")
        ),
    )


def _read_json(path_value: str) -> dict[str, object] | None:
    path = Path(path_value)
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _parse_timestamp(value: object) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _age_seconds(timestamp: datetime) -> int:
    return max(
        int(
            (
                datetime.now(UTC)
                - timestamp.astimezone(UTC)
            ).total_seconds()
        ),
        0,
    )


def _optional_int(value: object) -> int | None:
    if not isinstance(value, (str, bytes, bytearray, int, float)):
        return None
    try:
        return int(value)
    except ValueError:
        return None
