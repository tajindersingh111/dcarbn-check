from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import urlsplit

ROUTE_PATTERN = re.compile(
    r'@router\.(?:get|post|put|patch|delete)\(\s*"([^"]+)"',
    re.DOTALL,
)
PREFIX_PATTERN = re.compile(r'APIRouter\(\s*prefix="([^"]*)"')
FRONTEND_ENDPOINT_PATTERN = re.compile(
    r'(?:apiRequest|useApiQuery(?:<[^>]+>)?)'
    r'\(\s*([`"\'])(.+?)\1',
    re.DOTALL,
)


@dataclass(frozen=True)
class ValidationResult:
    check: str
    passed: bool
    detail: str


def normalize_route(route: str) -> str:
    route = urlsplit(route).path
    route = re.sub(r"\$\{[^}]+\}", "{id}", route)
    route = re.sub(r"\{[^}/]+\}", "{id}", route)
    return route.rstrip("/") or "/"


def backend_routes(root: Path) -> set[str]:
    routes: set[str] = set()
    for path in (root / "backend/app/api/routes").glob("*.py"):
        text = path.read_text(encoding="utf-8")
        prefix_match = PREFIX_PATTERN.search(text)
        prefix = prefix_match.group(1) if prefix_match else ""
        routes.update(
            normalize_route(prefix + match.group(1))
            for match in ROUTE_PATTERN.finditer(text)
        )
    return routes


def frontend_endpoints(root: Path) -> list[tuple[Path, str]]:
    endpoints: list[tuple[Path, str]] = []
    for path in (root / "frontend").rglob("*.tsx"):
        text = path.read_text(encoding="utf-8")
        endpoints.extend(
            (path.relative_to(root), match.group(2))
            for match in FRONTEND_ENDPOINT_PATTERN.finditer(text)
        )
    return endpoints


def validate_api_contracts(root: Path) -> ValidationResult:
    routes = backend_routes(root)
    endpoints = frontend_endpoints(root)
    missing = [
        f"{path}: {endpoint}"
        for path, endpoint in endpoints
        if normalize_route(endpoint) not in routes
    ]
    return ValidationResult(
        check="frontend_backend_route_coverage",
        passed=not missing,
        detail=(
            f"{len(endpoints)} frontend endpoint references matched "
            f"{len(routes)} backend routes."
            if not missing
            else "Unmatched endpoints: " + "; ".join(missing)
        ),
    )


def validate_required_frontend_workflows(root: Path) -> ValidationResult:
    required = [
        "frontend/app/page.tsx",
        "frontend/app/organisations/page.tsx",
        "frontend/app/inventories/page.tsx",
        "frontend/app/activities/new/page.tsx",
        "frontend/app/data-reviews/page.tsx",
        "frontend/app/approvals/page.tsx",
        "frontend/app/audit-reports/page.tsx",
        "frontend/app/admin/users/page.tsx",
        "frontend/app/admin/security-events/page.tsx",
        "frontend/app/admin/operations/page.tsx",
    ]
    missing = [item for item in required if not (root / item).is_file()]
    return ValidationResult(
        check="required_frontend_workflows",
        passed=not missing,
        detail=(
            f"All {len(required)} required workflows exist."
            if not missing
            else "Missing: " + ", ".join(missing)
        ),
    )


def validate_migration_chain(root: Path) -> ValidationResult:
    revisions: dict[str, str | None] = {}
    for path in (root / "backend/alembic/versions").glob("*.py"):
        text = path.read_text(encoding="utf-8")
        revision_match = re.search(
            r'^revision:\s*str\s*=\s*"([^"]+)"',
            text,
            re.MULTILINE,
        )
        down_match = re.search(
            r'^down_revision:\s*str\s*\|\s*None\s*=\s*'
            r'(?:"([^"]+)"|None)',
            text,
            re.MULTILINE,
        )
        if revision_match:
            revisions[revision_match.group(1)] = (
                down_match.group(1) if down_match else None
            )

    children = {value for value in revisions.values() if value}
    heads = sorted(set(revisions) - children)
    missing_parents = sorted(
        value
        for value in revisions.values()
        if value and value not in revisions
    )
    passed = len(heads) == 1 and not missing_parents
    return ValidationResult(
        check="alembic_migration_chain",
        passed=passed,
        detail=(
            f"{len(revisions)} revisions; head={heads[0]}."
            if passed
            else f"heads={heads}; missing_parents={missing_parents}"
        ),
    )


def validate_no_embedded_secrets(root: Path) -> ValidationResult:
    candidates = [
        path
        for path in root.rglob("*")
        if path.is_file()
        and ".git" not in path.parts
        and "node_modules" not in path.parts
        and path.name not in {"package-lock.json"}
        and path.stat().st_size < 2_000_000
    ]
    patterns = [
        re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
        re.compile(r"AKIA[0-9A-Z]{16}"),
        re.compile(r"ghp_[A-Za-z0-9]{30,}"),
    ]
    findings: list[str] = []
    for path in candidates:
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if any(pattern.search(text) for pattern in patterns):
            findings.append(str(path.relative_to(root)))
    return ValidationResult(
        check="embedded_secret_patterns",
        passed=not findings,
        detail=(
            "No high-confidence embedded secret patterns found."
            if not findings
            else "Potential secrets: " + ", ".join(findings)
        ),
    )


def validate_frontend_lockfile(root: Path) -> ValidationResult:
    path = root / "frontend/package-lock.json"
    return ValidationResult(
        check="frontend_dependency_lockfile",
        passed=path.is_file(),
        detail=(
            "frontend/package-lock.json exists."
            if path.is_file()
            else (
                "frontend/package-lock.json is missing. npm ci, reproducible "
                "builds, and dependency provenance remain blocked."
            )
        ),
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    results = [
        validate_api_contracts(args.root),
        validate_required_frontend_workflows(args.root),
        validate_migration_chain(args.root),
        validate_no_embedded_secrets(args.root),
        validate_frontend_lockfile(args.root),
    ]
    payload = {
        "schema_version": 1,
        "result": (
            "passed"
            if all(item.passed for item in results)
            else "failed"
        ),
        "checks": [asdict(item) for item in results],
    }

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    print(json.dumps(payload, indent=2))
    raise SystemExit(0 if payload["result"] == "passed" else 1)


if __name__ == "__main__":
    main()
