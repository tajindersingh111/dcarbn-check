from pathlib import Path

import yaml


def repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def documents(path: Path) -> list[dict[str, object]]:
    return [
        item
        for item in yaml.safe_load_all(path.read_text(encoding="utf-8"))
        if isinstance(item, dict)
    ]


def test_production_overlay_uses_digest_images() -> None:
    root = repository_root()
    payload = yaml.safe_load(
        (
            root
            / "deploy/kubernetes/overlays/production-primary/kustomization.yml"
        ).read_text(encoding="utf-8")
    )

    images = payload["images"]
    assert all(str(item["digest"]).startswith("sha256:") for item in images)


def test_backend_rollout_has_canary_analysis_and_security_controls() -> None:
    root = repository_root()
    payload = yaml.safe_load(
        (
            root / "deploy/kubernetes/base/backend-rollout.yml"
        ).read_text(encoding="utf-8")
    )

    canary = payload["spec"]["strategy"]["canary"]
    container = payload["spec"]["template"]["spec"]["containers"][0]

    assert canary["stableService"] == "dcarbn-backend-stable"
    assert canary["canaryService"] == "dcarbn-backend-canary"
    assert any("analysis" in step for step in canary["steps"])
    assert container["securityContext"]["readOnlyRootFilesystem"] is True
    assert container["securityContext"]["capabilities"]["drop"] == ["ALL"]
    assert container["readinessProbe"]
    assert container["livenessProbe"]


def test_argocd_production_application_self_heals() -> None:
    root = repository_root()
    payload = yaml.safe_load(
        (
            root
            / "deploy/gitops/argocd/production-primary-application.yml"
        ).read_text(encoding="utf-8")
    )

    automated = payload["spec"]["syncPolicy"]["automated"]
    assert automated["prune"] is True
    assert automated["selfHeal"] is True


def test_kyverno_requires_digest_and_restricted_runtime() -> None:
    root = repository_root()
    text = (
        root / "deploy/policies/kyverno/workload-security.yml"
    ).read_text(encoding="utf-8")

    assert "*@sha256:*" in text
    assert "runAsNonRoot: true" in text
    assert "readOnlyRootFilesystem: true" in text
    assert "allowPrivilegeEscalation: false" in text
    assert "drop:" in text


def test_gitops_workflow_validates_rendered_manifests() -> None:
    root = repository_root()
    text = (
        root / ".github/workflows/gitops.yml"
    ).read_text(encoding="utf-8")

    assert "kustomize build" in text
    assert "kubeconform" in text
    assert "kyverno apply" in text
    assert "Reject mutable images" in text
