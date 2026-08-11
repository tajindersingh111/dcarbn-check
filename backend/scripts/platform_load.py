from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
import re
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

from app.performance.load_metrics import LoadThresholds, RequestSample, summarize_samples

APPROVAL_PATTERN = re.compile(r"^[A-Za-z0-9._-]{3,100}$")
ENV_PATTERN = re.compile(r"\$\{([A-Z][A-Z0-9_]*)\}")
RUN_CONFIRMATION = "RUN-APPROVED-NON-PRODUCTION-LOAD-TEST"
MUTATION_CONFIRMATION = "USE-DISPOSABLE-STAGING-DATA"


class LoadTestPolicyError(RuntimeError):
    """Raised when a requested load test falls outside the approved safety boundary."""


@dataclass(frozen=True)
class Scenario:
    name: str
    method: str
    path: str
    weight: int
    tenant_alias: str
    token_env: str | None
    expected_statuses: frozenset[int]
    json_body_env: str | None


def _load_profile(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise LoadTestPolicyError("Load profile must use schema_version 1.")
    return payload


def _validate_target(base_url: str, profile: dict[str, Any]) -> str:
    parsed = urlparse(base_url)
    host = (parsed.hostname or "").lower()
    environment = str(profile.get("environment", "")).lower()
    approved_hosts = {
        str(item).lower() for item in profile.get("approved_hosts", [])
    }
    if parsed.scheme not in {"http", "https"} or not host:
        raise LoadTestPolicyError("A valid HTTP(S) target is required.")
    if environment not in {"local", "staging", "pilot"}:
        raise LoadTestPolicyError("Load tests are restricted to local, staging or pilot.")
    if host not in approved_hosts:
        raise LoadTestPolicyError("Target host is absent from the reviewed profile.")
    if os.getenv("DCARBN_LOAD_TEST_CONFIRMATION") != RUN_CONFIRMATION:
        raise LoadTestPolicyError("The non-production load-test confirmation is missing.")
    approval_id = os.getenv("DCARBN_LOAD_TEST_APPROVAL_ID", "")
    if not APPROVAL_PATTERN.fullmatch(approval_id):
        raise LoadTestPolicyError("A protected load-test approval reference is required.")
    return host


def _expand(value: str) -> str:
    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        resolved = os.getenv(name)
        if not resolved:
            raise LoadTestPolicyError(f"Required protected value {name} is missing.")
        return resolved

    return ENV_PATTERN.sub(replace, value)


def _parse_scenarios(profile: dict[str, Any]) -> list[Scenario]:
    mutations_enabled = bool(profile.get("mutations_enabled", False))
    scenarios: list[Scenario] = []
    for raw in profile.get("scenarios", []):
        if not isinstance(raw, dict) or not raw.get("enabled", True):
            continue
        method = str(raw.get("method", "GET")).upper()
        if method not in {"GET", "HEAD", "POST"}:
            raise LoadTestPolicyError(f"Scenario method {method!r} is not supported.")
        if method == "POST":
            if not mutations_enabled:
                raise LoadTestPolicyError("A write scenario requires mutations_enabled.")
            if os.getenv("DCARBN_LOAD_TEST_MUTATION_CONFIRMATION") != MUTATION_CONFIRMATION:
                raise LoadTestPolicyError("Disposable-data mutation confirmation is missing.")
        weight = int(raw.get("weight", 1))
        if weight < 1 or weight > 100:
            raise LoadTestPolicyError("Scenario weights must be between 1 and 100.")
        expected = raw.get("expected_statuses", [200])
        if not isinstance(expected, list) or not expected:
            raise LoadTestPolicyError("Each scenario requires expected_statuses.")
        scenarios.append(
            Scenario(
                name=str(raw["name"]),
                method=method,
                path=_expand(str(raw["path"])),
                weight=weight,
                tenant_alias=str(raw.get("tenant_alias", "public")),
                token_env=(str(raw["token_env"]) if raw.get("token_env") else None),
                expected_statuses=frozenset(int(item) for item in expected),
                json_body_env=(
                    str(raw["json_body_env"]) if raw.get("json_body_env") else None
                ),
            )
        )
    if not scenarios:
        raise LoadTestPolicyError("The load profile contains no enabled scenarios.")
    return scenarios


def _weighted_scenarios(scenarios: list[Scenario]) -> tuple[list[Scenario], list[int]]:
    return scenarios, [scenario.weight for scenario in scenarios]


async def _request_once(
    client: httpx.AsyncClient,
    scenario: Scenario,
) -> RequestSample:
    headers: dict[str, str] = {}
    if scenario.token_env:
        token = os.getenv(scenario.token_env)
        if not token:
            raise LoadTestPolicyError(
                f"Protected token {scenario.token_env} is required for {scenario.name}."
            )
        headers["Authorization"] = f"Bearer {token}"
    json_body: object | None = None
    if scenario.json_body_env:
        raw_body = os.getenv(scenario.json_body_env)
        if not raw_body:
            raise LoadTestPolicyError(
                f"Protected JSON body {scenario.json_body_env} is missing."
            )
        json_body = json.loads(raw_body)
    started = time.perf_counter()
    try:
        response = await client.request(
            scenario.method,
            scenario.path,
            headers=headers,
            json=json_body,
        )
        latency_ms = (time.perf_counter() - started) * 1_000
        return RequestSample(
            scenario=scenario.name,
            tenant_alias=scenario.tenant_alias,
            latency_ms=latency_ms,
            status_code=response.status_code,
            succeeded=response.status_code in scenario.expected_statuses,
        )
    except httpx.TimeoutException:
        return RequestSample(
            scenario=scenario.name,
            tenant_alias=scenario.tenant_alias,
            latency_ms=(time.perf_counter() - started) * 1_000,
            status_code=None,
            succeeded=False,
            timed_out=True,
        )
    except httpx.RequestError:
        return RequestSample(
            scenario=scenario.name,
            tenant_alias=scenario.tenant_alias,
            latency_ms=(time.perf_counter() - started) * 1_000,
            status_code=None,
            succeeded=False,
        )


async def _virtual_user(
    *,
    number: int,
    client: httpx.AsyncClient,
    scenarios: list[Scenario],
    weights: list[int],
    stop_at: float,
    samples: list[RequestSample],
) -> None:
    random_source = random.Random(number)
    while time.monotonic() < stop_at:
        scenario = random_source.choices(scenarios, weights=weights, k=1)[0]
        samples.append(await _request_once(client, scenario))


async def execute(args: argparse.Namespace) -> dict[str, Any]:
    profile = _load_profile(args.profile)
    host = _validate_target(args.base_url, profile)
    scenarios = _parse_scenarios(profile)
    users = int(profile.get("users", 10))
    duration_seconds = int(profile.get("duration_seconds", 60))
    request_timeout_seconds = float(profile.get("request_timeout_seconds", 10))
    if not 1 <= users <= 500:
        raise LoadTestPolicyError("Virtual users must be between 1 and 500.")
    if not 10 <= duration_seconds <= 3_600:
        raise LoadTestPolicyError("Duration must be between 10 and 3600 seconds.")
    thresholds = LoadThresholds.from_mapping(profile.get("thresholds", {}))
    samples: list[RequestSample] = []
    selected, weights = _weighted_scenarios(scenarios)
    started_at = datetime.now(UTC)
    started = time.monotonic()
    stop_at = started + duration_seconds
    limits = httpx.Limits(max_connections=users, max_keepalive_connections=users)
    timeout = httpx.Timeout(request_timeout_seconds)
    async with httpx.AsyncClient(
        base_url=args.base_url.rstrip("/"),
        timeout=timeout,
        limits=limits,
        follow_redirects=False,
        headers={"User-Agent": "dcarbn-approved-load-test/1"},
    ) as client:
        await asyncio.gather(
            *(
                _virtual_user(
                    number=number,
                    client=client,
                    scenarios=selected,
                    weights=weights,
                    stop_at=stop_at,
                    samples=samples,
                )
                for number in range(users)
            )
        )
    elapsed = time.monotonic() - started
    summary = summarize_samples(samples, duration_seconds=elapsed, thresholds=thresholds)
    return {
        "schema_version": 1,
        "evidence_type": "platform_capacity_envelope",
        "approval_reference": os.environ["DCARBN_LOAD_TEST_APPROVAL_ID"],
        "release_sha": os.getenv("GITHUB_SHA") or os.getenv("RELEASE_SHA") or "unrecorded",
        "environment": profile["environment"],
        "target_alias": profile.get("target_alias", host),
        "started_at": started_at.isoformat(),
        "duration_seconds": round(elapsed, 3),
        "profile": {
            "users": users,
            "configured_duration_seconds": duration_seconds,
            "request_timeout_seconds": request_timeout_seconds,
            "enabled_scenarios": [scenario.name for scenario in scenarios],
            "tenant_aliases": sorted({scenario.tenant_alias for scenario in scenarios}),
        },
        "measurements": summary,
        "passed": summary["passed"],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run an approved, non-production D-carbN platform load profile."
    )
    parser.add_argument("--base-url", default=os.getenv("DCARBN_LOAD_TEST_BASE_URL", ""))
    parser.add_argument(
        "--profile",
        type=Path,
        default=Path("scripts/platform-load-profile.example.json"),
    )
    parser.add_argument(
        "--output", type=Path, default=Path("artifacts/platform-capacity.json")
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        result = asyncio.run(execute(args))
    except (LoadTestPolicyError, OSError, json.JSONDecodeError, ValueError) as exc:
        raise SystemExit(f"Platform load test refused: {exc}") from exc
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    if not result["passed"]:
        raise SystemExit("Platform capacity thresholds were not met.")


if __name__ == "__main__":
    main()

