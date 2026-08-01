from pathlib import Path

import yaml


def repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_primary_compose_contains_wal_and_pitr_services() -> None:
    root = repository_root()
    payload = yaml.safe_load(
        (root / "docker-compose.production.yml").read_text(
            encoding="utf-8"
        )
    )

    services = payload["services"]
    assert "pitr-base-backup" in services
    assert "pitr-restore" in services
    assert "primary-region-status" in services
    assert "archive_command=/usr/local/bin/archive-wal.sh %p %f" in (
        services["postgres"]["command"]
    )


def test_standby_compose_requires_fencing_before_promotion() -> None:
    root = repository_root()
    failover = (
        root / "deploy" / "failover" / "failover.sh"
    ).read_text(encoding="utf-8")
    standby = yaml.safe_load(
        (root / "docker-compose.region-standby.yml").read_text(
            encoding="utf-8"
        )
    )

    assert "PRIMARY_FENCING_HOOK is required" in failover
    assert "pg_promote" in failover
    assert "failover-controller" in standby["services"]
    assert "regional-app" in standby["services"]["regional-backend"]["profiles"]


def test_pitr_restore_accepts_only_one_target() -> None:
    root = repository_root()
    restore = (
        root / "deploy" / "pitr" / "restore-pitr.sh"
    ).read_text(encoding="utf-8")

    assert "Configure only one PITR recovery target" in restore
    assert "recovery_target_timeline" in restore
    assert "recovery.signal" in restore


def test_wal_archives_are_encrypted_and_checksummed() -> None:
    root = repository_root()
    archive = (
        root / "deploy" / "postgres" / "archive-wal.sh"
    ).read_text(encoding="utf-8")
    restore = (
        root / "deploy" / "postgres" / "restore-wal.sh"
    ).read_text(encoding="utf-8")

    assert "age --encrypt" in archive
    assert "sha256sum" in archive
    assert "age --decrypt" in restore
    assert "WAL checksum verification failed" in restore
