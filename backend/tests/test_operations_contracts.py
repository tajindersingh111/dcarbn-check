import json
from pathlib import Path


def test_grafana_dashboard_is_valid_json() -> None:
    root = Path(__file__).resolve().parents[2]
    path = (
        root
        / "deploy"
        / "observability"
        / "grafana"
        / "dashboards"
        / "dcarbn-operations.json"
    )

    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["uid"] == "dcarbn-operations"
    assert len(payload["panels"]) >= 6


def test_alert_rules_reference_runbooks() -> None:
    root = Path(__file__).resolve().parents[2]
    rules = (
        root
        / "deploy"
        / "observability"
        / "rules"
        / "platform-alerts.yml"
    ).read_text(encoding="utf-8")

    assert "runbook_url:" in rules
    assert "DCarbnBackupStale" in rules
    assert "DCarbnRefreshTokenReuse" in rules


def test_backup_scripts_require_confirmation_for_restore() -> None:
    root = Path(__file__).resolve().parents[2]
    restore = (
        root / "deploy" / "backup" / "restore.sh"
    ).read_text(encoding="utf-8")

    assert "RESTORE_CONFIRMATION=RESTORE-D-CARBN" in restore
    assert "sha256sum" in restore
    assert "pg_restore --list" in restore
