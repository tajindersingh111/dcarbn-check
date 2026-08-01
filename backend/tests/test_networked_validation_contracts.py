from pathlib import Path

import yaml


def repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_networked_workflow_contains_all_blocked_suites() -> None:
    root = repository_root()
    payload = yaml.safe_load(
        (
            root
            / ".github/workflows/networked-full-validation.yml"
        ).read_text(encoding="utf-8")
    )

    jobs = payload["jobs"]
    assert {
        "frontend-lockfile",
        "backend",
        "frontend",
        "containers",
        "kubernetes",
        "validation-summary",
    }.issubset(jobs)


def test_lockfile_is_generated_and_shared_as_an_artifact() -> None:
    root = repository_root()
    workflow = (
        root / ".github/workflows/networked-full-validation.yml"
    ).read_text(encoding="utf-8")

    assert "npm install" in workflow
    assert "--package-lock-only" in workflow
    assert "frontend/package-lock.json" in workflow
    assert "actions/upload-artifact@v4" in workflow
    assert "actions/download-artifact@v4" in workflow
    assert "sha256sum --check package-lock.json.sha256" in workflow


def test_backend_suite_includes_database_and_quality_gates() -> None:
    root = repository_root()
    workflow = (
        root / ".github/workflows/networked-full-validation.yml"
    ).read_text(encoding="utf-8")

    assert "postgres:16-alpine" in workflow
    assert "redis:7-alpine" in workflow
    assert "alembic upgrade head" in workflow
    assert "ruff check app tests" in workflow
    assert "mypy app" in workflow
    assert "--cov=app" in workflow


def test_frontend_suite_uses_exact_install_and_playwright() -> None:
    root = repository_root()
    workflow = (
        root / ".github/workflows/networked-full-validation.yml"
    ).read_text(encoding="utf-8")

    assert "npm ci --no-audit --no-fund" in workflow
    assert "npm run typecheck" in workflow
    assert "npm run lint" in workflow
    assert "npm run build" in workflow
    assert "npx playwright install --with-deps chromium" in workflow


def test_container_and_kubernetes_suites_are_release_gates() -> None:
    root = repository_root()
    workflow = (
        root / ".github/workflows/networked-full-validation.yml"
    ).read_text(encoding="utf-8")

    assert "docker build" in workflow
    assert "Runtime health smoke" in workflow
    assert "kubectl kustomize" in workflow
    assert "kubeconform" in workflow
    assert "kyverno apply" in workflow
    assert "raise SystemExit(0 if passed else 1)" in workflow


def test_frontend_container_requires_committed_lockfile() -> None:
    root = repository_root()
    dockerfile = (
        root / "frontend/Dockerfile"
    ).read_text(encoding="utf-8")

    assert "COPY package.json package-lock.json ./" in dockerfile
    assert "RUN npm ci --no-audit --no-fund" in dockerfile
