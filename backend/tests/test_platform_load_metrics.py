from __future__ import annotations

import pytest

from app.performance.load_metrics import (
    LoadThresholds,
    RequestSample,
    percentile,
    summarize_samples,
)


def sample(
    latency_ms: float,
    *,
    tenant: str = "tenant-a",
    succeeded: bool = True,
    timed_out: bool = False,
) -> RequestSample:
    return RequestSample(
        scenario="dashboard",
        tenant_alias=tenant,
        latency_ms=latency_ms,
        status_code=200 if succeeded else None,
        succeeded=succeeded,
        timed_out=timed_out,
    )


def test_percentile_uses_nearest_rank() -> None:
    values = list(range(1, 101))

    assert percentile(values, 0.50) == 50
    assert percentile(values, 0.95) == 95
    assert percentile(values, 0.99) == 99


def test_capacity_summary_passes_with_fair_tenants() -> None:
    samples = [sample(100 + index, tenant="tenant-a") for index in range(50)]
    samples += [sample(110 + index, tenant="tenant-b") for index in range(50)]

    result = summarize_samples(
        samples,
        duration_seconds=10,
        thresholds=LoadThresholds(
            minimum_requests=100,
            maximum_p95_ms=250,
            maximum_p99_ms=300,
        ),
    )

    assert result["passed"] is True
    assert result["requests_per_second"] == 10
    assert set(result["tenant_aliases"]) == {"tenant-a", "tenant-b"}


def test_capacity_summary_fails_closed_on_errors_timeouts_and_unfairness() -> None:
    samples = [sample(100, tenant="tenant-a") for _ in range(98)]
    samples += [sample(1_000, tenant="tenant-b", succeeded=False) for _ in range(2)]
    samples[-1] = sample(1_000, tenant="tenant-b", succeeded=False, timed_out=True)

    result = summarize_samples(
        samples,
        duration_seconds=10,
        thresholds=LoadThresholds(
            maximum_error_rate=0.01,
            maximum_timeout_rate=0.005,
            maximum_p95_ms=500,
            maximum_p99_ms=500,
            maximum_tenant_p95_ratio=1.5,
        ),
    )

    assert result["passed"] is False
    assert result["assertions"]["error_rate_met"] is False
    assert result["assertions"]["timeout_rate_met"] is False
    assert result["assertions"]["tenant_fairness_met"] is False


def test_unknown_threshold_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown load threshold"):
        LoadThresholds.from_mapping({"maximum_average_ms": 100})

