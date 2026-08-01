from pathlib import Path

import yaml


def repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_supply_chain_policy_requires_core_controls() -> None:
    root = repository_root()
    policy = yaml.safe_load(
        (root / "deploy/supply-chain/policy.yml").read_text(
            encoding="utf-8"
        )
    )

    assert policy["required_artifacts"]["signatures"][
        "require_cosign"
    ] is True
    assert policy["required_artifacts"]["signatures"][
        "require_digest_reference"
    ] is True
    assert "spdx-json" in policy["required_artifacts"]["sbom_formats"]
    assert "cyclonedx-json" in policy["required_artifacts"]["sbom_formats"]
    assert policy["release_gate"]["require_provenance"] is True


def test_vulnerability_exceptions_start_empty() -> None:
    root = repository_root()
    payload = yaml.safe_load(
        (
            root
            / "deploy"
            / "supply-chain"
            / "vulnerability-exceptions.yml"
        ).read_text(encoding="utf-8")
    )

    assert payload["exceptions"] == []


def test_release_gate_requires_supply_chain_evidence() -> None:
    root = repository_root()
    release_gate = (
        root / "deploy/release-gate/release-gate.py"
    ).read_text(encoding="utf-8")

    assert "validate_supply_chain_evidence" in release_gate
    assert "secret_scan" in release_gate
    assert "python_dependency_audit" in release_gate
    assert "node_dependency_audit" in release_gate
    assert "_signature" in release_gate
    assert "_provenance" in release_gate


def test_supply_chain_workflow_generates_and_signs_artifacts() -> None:
    root = repository_root()
    workflow = (
        root / ".github/workflows/supply-chain.yml"
    ).read_text(encoding="utf-8")

    assert "Generate SPDX SBOM" in workflow
    assert "Generate CycloneDX SBOM" in workflow
    assert "cosign sign --yes" in workflow
    assert "actions/attest-build-provenance@v2" in workflow
    assert "Evaluate vulnerability policy" in workflow
    assert "Evaluate license policy" in workflow


def test_admission_policy_requires_digest_and_signature() -> None:
    root = repository_root()
    policy = (
        root / "deploy/admission/kyverno-verify-images.yml"
    ).read_text(encoding="utf-8")

    assert "*@sha256:*" in policy
    assert "verifyImages" in policy
    assert "token.actions.githubusercontent.com" in policy
    assert "https://slsa.dev/provenance/v1" in policy
