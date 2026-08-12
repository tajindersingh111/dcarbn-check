from __future__ import annotations

import re
import tomllib
from pathlib import Path


GOVERNED_MODULES = (
    "app.api.routes.identity",
    "app.auth.dependencies",
    "app.core.logging",
    "app.core.observability",
    "app.middleware.rate_limit",
    "app.middleware.security_headers",
    "app.services.activities",
    "app.services.boundaries",
    "app.services.calculations",
    "app.services.data_integration",
    "app.services.data_review",
    "app.services.email_delivery",
    "app.services.factor_resolution",
    "app.services.inventory_governance",
    "app.services.operational_health",
    "app.services.organisations",
    "app.services.session_auth",
)
EXPLAINED_TYPE_IGNORE = re.compile(
    r"# type: ignore\[[a-z0-9-]+\]\s+# external typing limitation: .+"
)


def backend_root() -> Path:
    return Path(__file__).resolve().parents[1]


def module_path(module: str) -> Path:
    return backend_root() / (module.replace(".", "/") + ".py")


def test_mypy_is_strict_without_error_exemptions() -> None:
    pyproject = (backend_root() / "pyproject.toml").read_text(encoding="utf-8")
    config = tomllib.loads(pyproject)["tool"]["mypy"]

    assert config["strict"] is True
    assert config.get("exclude") == ["alembic"]
    assert "ignore_errors" not in pyproject
    assert all(
        override.get("ignore_errors") is not True
        for override in config.get("overrides", [])
    )


def test_all_governed_modules_exist_and_remain_unsuppressed() -> None:
    for module in GOVERNED_MODULES:
        path = module_path(module)
        assert path.is_file(), f"Governed module is missing: {module}"

        for line_number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(),
            start=1,
        ):
            if "# type: ignore" in line:
                assert EXPLAINED_TYPE_IGNORE.search(line), (
                    f"{module}:{line_number} has an unexplained type suppression"
                )


def test_architecture_policy_records_every_governed_module() -> None:
    policy = (
        backend_root().parent / "docs" / "architecture" / "strict-type-safety.md"
    ).read_text(encoding="utf-8")

    for module in GOVERNED_MODULES:
        assert f"`{module}`" in policy
