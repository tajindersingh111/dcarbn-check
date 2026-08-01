from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class DependencyStatus(BaseModel):
    status: str
    latency_ms: float | None = None
    detail: str | None = None


class BackupStatus(BaseModel):
    status: str
    latest_success_at: datetime | None = None
    age_seconds: int | None = None
    backup_id: str | None = None
    verified: bool | None = None


class OperationalHealthResponse(BaseModel):
    status: str
    timestamp: datetime
    database: DependencyStatus
    redis: DependencyStatus
    backup: BackupStatus


class WalArchiveStatus(BaseModel):
    status: str
    latest_wal: str | None = None
    latest_archived_at: datetime | None = None
    age_seconds: int | None = None
    region: str | None = None


class PitrStatus(BaseModel):
    status: str
    latest_base_backup_id: str | None = None
    latest_base_backup_at: datetime | None = None
    age_seconds: int | None = None
    verified: bool | None = None
    region: str | None = None


class FailoverStatus(BaseModel):
    status: str
    active_region: str | None = None
    region: str | None = None
    in_recovery: bool | None = None
    current_lsn: str | None = None
    replay_timestamp: datetime | None = None
    timeline: int | None = None
    checked_at: datetime | None = None


class RecoveryReadinessResponse(BaseModel):
    status: str
    timestamp: datetime
    wal_archive: WalArchiveStatus
    pitr: PitrStatus
    failover: FailoverStatus
