from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass
from math import ceil
from typing import Any


@dataclass(frozen=True)
class RequestSample:
    scenario: str
    tenant_alias: str
    latency_ms: float
    status_code: int | None
    succeeded: bool
    timed_out: bool = False


@dataclass(frozen=True)
class LoadThresholds:
    minimum_requests: int = 100
    maximum_error_rate: float = 0.01
    maximum_timeout_rate: float = 0.005
    maximum_p95_ms: float = 1_000
    maximum_p99_ms: float = 2_000
    maximum_tenant_p95_ratio: float = 1.5

    @classmethod
    def from_mapping(cls, values: Mapping[str, object]) -> LoadThresholds:
        allowed = {field for field in cls.__dataclass_fields__}
        unknown = set(values) - allowed
        if unknown:
            raise ValueError(f"Unknown load threshold(s): {', '.join(sorted(unknown))}.")
        return cls(**values)  # type: ignore[arg-type]


def percentile(values: Iterable[float], fraction: float) -> float:
    if not 0 <= fraction <= 1:
        raise ValueError("Percentile fraction must be between zero and one.")
    ordered = sorted(values)
    if not ordered:
        return 0.0
    index = max(ceil(fraction * len(ordered)) - 1, 0)
    return ordered[index]


def summarize_samples(
    samples: list[RequestSample],
    *,
    duration_seconds: float,
    thresholds: LoadThresholds,
) -> dict[str, Any]:
    latencies = [sample.latency_ms for sample in samples]
    failures = sum(not sample.succeeded for sample in samples)
    timeouts = sum(sample.timed_out for sample in samples)
    request_count = len(samples)

    by_scenario: dict[str, list[RequestSample]] = defaultdict(list)
    by_tenant: dict[str, list[RequestSample]] = defaultdict(list)
    for sample in samples:
        by_scenario[sample.scenario].append(sample)
        if sample.tenant_alias:
            by_tenant[sample.tenant_alias].append(sample)

    scenario_metrics = {
        name: _group_summary(group) for name, group in sorted(by_scenario.items())
    }
    tenant_metrics = {
        name: _group_summary(group) for name, group in sorted(by_tenant.items())
    }
    tenant_p95s = [
        float(metrics["latency_p95_ms"])
        for metrics in tenant_metrics.values()
        if int(metrics["requests"]) > 0
    ]
    tenant_p95_ratio = (
        max(tenant_p95s) / max(min(tenant_p95s), 0.001)
        if len(tenant_p95s) >= 2
        else 1.0
    )

    error_rate = failures / request_count if request_count else 1.0
    timeout_rate = timeouts / request_count if request_count else 1.0
    p95_ms = percentile(latencies, 0.95)
    p99_ms = percentile(latencies, 0.99)
    assertions = {
        "minimum_requests_met": request_count >= thresholds.minimum_requests,
        "error_rate_met": error_rate <= thresholds.maximum_error_rate,
        "timeout_rate_met": timeout_rate <= thresholds.maximum_timeout_rate,
        "p95_latency_met": p95_ms <= thresholds.maximum_p95_ms,
        "p99_latency_met": p99_ms <= thresholds.maximum_p99_ms,
        "tenant_fairness_met": tenant_p95_ratio <= thresholds.maximum_tenant_p95_ratio,
    }

    return {
        "requests": request_count,
        "requests_per_second": round(request_count / max(duration_seconds, 0.001), 3),
        "errors": failures,
        "error_rate": round(error_rate, 6),
        "timeouts": timeouts,
        "timeout_rate": round(timeout_rate, 6),
        "latency_p50_ms": round(percentile(latencies, 0.50), 3),
        "latency_p95_ms": round(p95_ms, 3),
        "latency_p99_ms": round(p99_ms, 3),
        "tenant_p95_ratio": round(tenant_p95_ratio, 3),
        "thresholds": asdict(thresholds),
        "scenarios": scenario_metrics,
        "tenant_aliases": tenant_metrics,
        "assertions": assertions,
        "passed": all(assertions.values()),
    }


def _group_summary(samples: list[RequestSample]) -> dict[str, int | float]:
    latencies = [sample.latency_ms for sample in samples]
    failures = sum(not sample.succeeded for sample in samples)
    return {
        "requests": len(samples),
        "errors": failures,
        "latency_p50_ms": round(percentile(latencies, 0.50), 3),
        "latency_p95_ms": round(percentile(latencies, 0.95), 3),
        "latency_p99_ms": round(percentile(latencies, 0.99), 3),
    }

