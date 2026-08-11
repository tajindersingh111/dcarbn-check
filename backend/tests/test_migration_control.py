from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from app.db.migration_control import (
    MigrationLockUnavailable,
    MigrationPolicyError,
    SUPPORTED_RUNTIME_REVISIONS,
    assert_supported_schema_version,
    load_release_manifest,
    migration_lock,
    validate_release_policy,
    verify_recovery_evidence,
)


def _manifest_path() -> Path:
    return Path(__file__).resolve().parents[1] / "app" / "db" / "migration_releases.json"


def test_manifest_schema_contract_matches_runtime_guard() -> None:
    payload = json.loads(_manifest_path().read_text(encoding="utf-8"))

    assert set(payload["schema_contract"]["runtime_compatible_revisions"]) == set(
        SUPPORTED_RUNTIME_REVISIONS
    )


def test_manifest_classifies_rls_as_contract_release() -> None:
    release = load_release_manifest(_manifest_path())["0022"]

    assert release.phase == "contract"
    assert release.requires_old_replicas_retired is True
    assert release.requires_recovery_evidence is True


def test_contract_release_fails_closed_while_old_replicas_exist() -> None:
    releases = load_release_manifest(_manifest_path())

    with pytest.raises(MigrationPolicyError, match="old application replicas"):
        validate_release_policy(
            releases,
            target="0022",
            requested_phase="contract",
            old_replicas_retired=False,
        )


def test_unreviewed_target_and_phase_are_rejected() -> None:
    releases = load_release_manifest(_manifest_path())

    with pytest.raises(MigrationPolicyError, match="not present"):
        validate_release_policy(
            releases,
            target="head",
            requested_phase="expand",
            old_replicas_retired=True,
        )
    with pytest.raises(MigrationPolicyError, match="phase mismatch"):
        validate_release_policy(
            releases,
            target="0022",
            requested_phase="expand",
            old_replicas_retired=True,
        )


def test_runtime_schema_contract_is_exact() -> None:
    assert_supported_schema_version("0022")

    with pytest.raises(MigrationPolicyError, match="Unsupported"):
        assert_supported_schema_version("0021")
    with pytest.raises(MigrationPolicyError, match="Unsupported"):
        assert_supported_schema_version(None)


def test_recovery_evidence_must_be_verified_and_fresh(tmp_path: Path) -> None:
    now = datetime(2026, 8, 11, 7, 0, tzinfo=UTC)
    backup_path = tmp_path / "backup.json"
    pitr_path = tmp_path / "pitr.json"
    backup_path.write_text(
        json.dumps(
            {
                "verified": True,
                "latest_success_at": (now - timedelta(minutes=10)).isoformat(),
            }
        ),
        encoding="utf-8",
    )
    pitr_path.write_text(
        json.dumps(
            {
                "verified": True,
                "latest_base_backup_at": (now - timedelta(minutes=20)).isoformat(),
            }
        ),
        encoding="utf-8",
    )

    evidence = verify_recovery_evidence(
        backup_path=backup_path,
        pitr_path=pitr_path,
        now=now,
        backup_max_age_seconds=3_600,
        pitr_max_age_seconds=3_600,
    )

    assert evidence["backup_verified"] is True
    assert evidence["pitr_verified"] is True

    backup_path.write_text(
        json.dumps(
            {
                "verified": True,
                "latest_success_at": (now - timedelta(hours=2)).isoformat(),
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(MigrationPolicyError, match="stale"):
        verify_recovery_evidence(
            backup_path=backup_path,
            pitr_path=pitr_path,
            now=now,
            backup_max_age_seconds=3_600,
            pitr_max_age_seconds=3_600,
        )


@pytest.mark.asyncio
async def test_postgres_advisory_lock_allows_only_one_migrator(
) -> None:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url or not database_url.startswith("postgresql"):
        pytest.skip("PostgreSQL is required for advisory-lock validation.")

    async with migration_lock(database_url, timeout_seconds=1):
        with pytest.raises(MigrationLockUnavailable):
            async with migration_lock(database_url, timeout_seconds=0):
                pytest.fail("A second migrator acquired the same advisory lock.")
