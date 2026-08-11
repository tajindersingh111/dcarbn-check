from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from app.db.migration_control import (
    MigrationPolicyError,
    current_schema_revision,
    load_release_manifest,
    migration_lock,
    validate_release_policy,
    verify_recovery_evidence,
)

RELEASE_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
BACKEND_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = BACKEND_ROOT / "app" / "db" / "migration_releases.json"
ALEMBIC_INI = BACKEND_ROOT / "alembic.ini"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run exactly one reviewed Alembic release under a PostgreSQL lock."
    )
    parser.add_argument("--target", default=os.getenv("MIGRATION_TARGET", ""))
    parser.add_argument("--phase", default=os.getenv("MIGRATION_PHASE", ""))
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=int(os.getenv("MIGRATION_TIMEOUT_SECONDS", "600")),
    )
    parser.add_argument(
        "--lock-timeout-seconds",
        type=float,
        default=float(os.getenv("MIGRATION_LOCK_TIMEOUT_SECONDS", "30")),
    )
    parser.add_argument(
        "--evidence-file",
        type=Path,
        default=Path(
            os.getenv(
                "MIGRATION_EVIDENCE_FILE",
                "/var/run/dcarbn-evidence/migration.json",
            )
        ),
    )
    return parser.parse_args()


async def run() -> int:
    args = parse_args()
    started_at = datetime.now(UTC)
    started = time.monotonic()
    release_sha = os.getenv("RELEASE_SHA", "").lower()
    evidence: dict[str, object] = {
        "release_sha": release_sha,
        "target_revision": args.target,
        "phase": args.phase,
        "started_at": started_at.isoformat(),
        "status": "failed",
    }

    try:
        if not RELEASE_SHA_PATTERN.fullmatch(release_sha):
            raise MigrationPolicyError("RELEASE_SHA must be an exact 40-character SHA.")
        if args.timeout_seconds < 1 or args.timeout_seconds > 3_600:
            raise MigrationPolicyError("Migration timeout must be between 1 and 3600 seconds.")
        if args.lock_timeout_seconds < 0 or args.lock_timeout_seconds > 300:
            raise MigrationPolicyError("Migration lock timeout must be between 0 and 300 seconds.")

        database_url = _read_database_url()
        releases = load_release_manifest(MANIFEST_PATH)
        release = validate_release_policy(
            releases,
            target=args.target,
            requested_phase=args.phase,
            old_replicas_retired=_env_flag("OLD_REPLICAS_RETIRED"),
        )
        if release.requires_recovery_evidence:
            evidence["recovery"] = verify_recovery_evidence(
                backup_path=Path(
                    os.getenv(
                        "BACKUP_STATUS_FILE",
                        "/var/run/dcarbn-evidence/backup-status.json",
                    )
                ),
                pitr_path=Path(
                    os.getenv(
                        "PITR_STATUS_FILE",
                        "/var/run/dcarbn-evidence/pitr-status.json",
                    )
                ),
            )

        async with migration_lock(
            database_url,
            timeout_seconds=args.lock_timeout_seconds,
        ) as connection:
            previous_revision = await current_schema_revision(connection)
            evidence["previous_revision"] = previous_revision
            process = await asyncio.create_subprocess_exec(
                sys.executable,
                "-m",
                "alembic",
                "-c",
                str(ALEMBIC_INI),
                "upgrade",
                args.target,
                cwd=BACKEND_ROOT,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            try:
                output, _ = await asyncio.wait_for(
                    process.communicate(),
                    timeout=args.timeout_seconds,
                )
            except TimeoutError as exc:
                process.kill()
                await process.wait()
                raise MigrationPolicyError("Migration exceeded its approved timeout.") from exc

            if output:
                print(output.decode("utf-8", errors="replace"), end="")
            if process.returncode != 0:
                raise MigrationPolicyError(
                    f"Alembic exited with status {process.returncode}."
                )

            current_revision = await current_schema_revision(connection)
            evidence["current_revision"] = current_revision
            if current_revision != args.target:
                raise MigrationPolicyError(
                    "Database revision does not match the approved target."
                )

        evidence["status"] = "succeeded"
        print(f"Controlled migration completed at revision {args.target}.")
        return 0
    except Exception as exc:
        evidence["error_type"] = type(exc).__name__
        evidence["error"] = "Controlled migration failed; inspect protected workflow logs."
        print(f"Controlled migration failed: {exc}", file=sys.stderr)
        return 1
    finally:
        evidence["finished_at"] = datetime.now(UTC).isoformat()
        evidence["duration_seconds"] = round(time.monotonic() - started, 3)
        _write_evidence(args.evidence_file, evidence)


def _read_database_url() -> str:
    file_path = os.getenv("DATABASE_URL_FILE")
    if file_path:
        value = Path(file_path).read_text(encoding="utf-8").strip()
    else:
        value = os.getenv("DATABASE_URL", "").strip()
    if not value:
        raise MigrationPolicyError("DATABASE_URL or DATABASE_URL_FILE is required.")
    return value


def _env_flag(name: str) -> bool:
    return os.getenv(name, "").strip().casefold() in {"1", "true", "yes"}


def _write_evidence(path: Path, evidence: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))
