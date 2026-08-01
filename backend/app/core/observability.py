from __future__ import annotations

import logging
import time
from collections.abc import Callable

from fastapi import FastAPI, Request, Response
from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from prometheus_client import Counter, Gauge, Histogram, make_asgi_app
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.config import get_settings

logger = logging.getLogger(__name__)

HTTP_REQUESTS = Counter(
    "dcarbn_http_requests_total",
    "HTTP requests processed by the API.",
    ["method", "route", "status"],
)
HTTP_DURATION = Histogram(
    "dcarbn_http_request_duration_seconds",
    "HTTP request duration.",
    ["method", "route"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
)
HTTP_IN_PROGRESS = Gauge(
    "dcarbn_http_requests_in_progress",
    "HTTP requests currently in progress.",
    ["method", "route"],
)
SECURITY_EVENTS = Counter(
    "dcarbn_security_events_total",
    "Security events recorded by type, severity, and result.",
    ["event_type", "severity", "success"],
)
DEPENDENCY_HEALTH = Gauge(
    "dcarbn_dependency_health",
    "Dependency health status where 1 is healthy.",
    ["dependency"],
)
BACKUP_AGE_SECONDS = Gauge(
    "dcarbn_backup_age_seconds",
    "Age of the latest successful database backup.",
)
BACKUP_SUCCESS = Gauge(
    "dcarbn_backup_last_success",
    "Whether the latest backup attempt succeeded.",
)

WAL_ARCHIVE_AGE_SECONDS = Gauge(
    "dcarbn_wal_archive_age_seconds",
    "Age of the latest archived WAL segment.",
)
WAL_ARCHIVE_HEALTH = Gauge(
    "dcarbn_wal_archive_health",
    "WAL archive health where 1 is healthy.",
)
PITR_BASE_BACKUP_AGE_SECONDS = Gauge(
    "dcarbn_pitr_base_backup_age_seconds",
    "Age of the latest verified PITR base backup.",
)
PITR_READINESS = Gauge(
    "dcarbn_pitr_readiness",
    "PITR readiness where 1 is ready.",
)
FAILOVER_REGION_STATE = Gauge(
    "dcarbn_failover_region_state",
    "Region database role: 1 primary, 0 standby, -1 unknown.",
    ["region"],
)


def configure_observability(app: FastAPI, engine: AsyncEngine) -> None:
    settings = get_settings()
    app.mount("/metrics", make_asgi_app())

    if not settings.otel_enabled:
        return

    resource = Resource.create(
        {
            "service.name": settings.otel_service_name,
            "service.version": "0.1.0",
            "deployment.environment": settings.app_env,
        }
    )

    trace_provider = TracerProvider(resource=resource)
    trace_provider.add_span_processor(
        BatchSpanProcessor(
            OTLPSpanExporter(
                endpoint=settings.otel_exporter_otlp_endpoint,
                insecure=settings.otel_exporter_otlp_insecure,
            )
        )
    )
    trace.set_tracer_provider(trace_provider)

    metric_reader = PeriodicExportingMetricReader(
        OTLPMetricExporter(
            endpoint=settings.otel_exporter_otlp_endpoint,
            insecure=settings.otel_exporter_otlp_insecure,
        ),
        export_interval_millis=settings.otel_metric_export_interval_ms,
    )
    metrics.set_meter_provider(
        MeterProvider(resource=resource, metric_readers=[metric_reader])
    )

    FastAPIInstrumentor.instrument_app(
        app,
        excluded_urls="/api/v1/health/live,/metrics",
    )
    SQLAlchemyInstrumentor().instrument(engine=engine.sync_engine)
    RedisInstrumentor().instrument()


async def metrics_middleware(
    request: Request,
    call_next: Callable[[Request], object],
) -> Response:
    route = _route_name(request)
    method = request.method
    started = time.perf_counter()
    HTTP_IN_PROGRESS.labels(method=method, route=route).inc()
    status_code = 500

    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        elapsed = time.perf_counter() - started
        HTTP_IN_PROGRESS.labels(method=method, route=route).dec()
        HTTP_REQUESTS.labels(
            method=method,
            route=route,
            status=str(status_code),
        ).inc()
        HTTP_DURATION.labels(method=method, route=route).observe(elapsed)


def _route_name(request: Request) -> str:
    route = request.scope.get("route")
    path = getattr(route, "path", None)
    return str(path or request.url.path)
