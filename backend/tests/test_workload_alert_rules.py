from pathlib import Path
from typing import Any

import yaml

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
RULES_PATH = REPOSITORY_ROOT / "deploy" / "monitoring" / "workload-alerts.yml"
RUNBOOK_PATH = REPOSITORY_ROOT / "docs" / "operations" / "workload-pilot-runbook.md"


def _rules() -> list[dict[str, Any]]:
    document = yaml.safe_load(RULES_PATH.read_text(encoding="utf-8"))
    return document["groups"][0]["rules"]


def test_workload_alert_rules_are_complete_and_tenant_safe() -> None:
    rules = _rules()
    alerts = {rule["alert"] for rule in rules}

    assert alerts == {
        "DcarbnWorkloadQueueAgeWarning",
        "DcarbnWorkloadQueueAgeCritical",
        "DcarbnWorkloadDeadLetterGrowth",
        "DcarbnWorkloadFailureRate",
        "DcarbnWorkloadStalled",
    }

    for rule in rules:
        expression = str(rule["expr"]).casefold()
        assert "tenant" not in expression
        assert rule["for"]
        assert rule["labels"]["severity"] in {"warning", "critical"}
        assert rule["annotations"]["runbook_url"].endswith(
            "docs/operations/workload-pilot-runbook.md#"
            + {
                "DcarbnWorkloadQueueAgeWarning": "queue-age",
                "DcarbnWorkloadQueueAgeCritical": "queue-age",
                "DcarbnWorkloadDeadLetterGrowth": "dead-letter-growth",
                "DcarbnWorkloadFailureRate": "failure-rate",
                "DcarbnWorkloadStalled": "stalled-processing",
            }[rule["alert"]]
        )


def test_stalled_alert_handles_an_absent_success_series() -> None:
    stalled = next(
        rule for rule in _rules() if rule["alert"] == "DcarbnWorkloadStalled"
    )
    expression = " ".join(str(stalled["expr"]).casefold().split())

    assert "unless on (workload_type)" in expression
    assert 'status="queued"' in expression
    assert 'status="succeeded"' in expression


def test_workload_alert_runbook_exists() -> None:
    assert RUNBOOK_PATH.is_file()
