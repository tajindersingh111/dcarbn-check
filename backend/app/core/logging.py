import logging
import sys

import structlog
from opentelemetry import trace

from app.core.config import get_settings


def add_trace_context(_, __, event_dict: dict[str, object]) -> dict[str, object]:
    span = trace.get_current_span()
    context = span.get_span_context()
    if context.is_valid:
        event_dict['trace_id'] = format(context.trace_id, '032x')
        event_dict['span_id'] = format(context.span_id, '016x')
    return event_dict


def configure_logging() -> None:
    settings = get_settings()

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=settings.log_level.upper(),
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            add_trace_context,
            structlog.processors.EventRenamer('message'),
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(settings.log_level.upper())
        ),
        cache_logger_on_first_use=True,
    )
