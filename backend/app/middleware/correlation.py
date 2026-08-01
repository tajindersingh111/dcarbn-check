from __future__ import annotations

from uuid import uuid4

import structlog
from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class CorrelationIdMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        correlation_id = headers.get(b"x-correlation-id", b"").decode() or str(uuid4())
        structlog.contextvars.bind_contextvars(correlation_id=correlation_id)

        async def send_with_header(message: Message) -> None:
            if message["type"] == "http.response.start":
                mutable_headers = MutableHeaders(scope=message)
                mutable_headers.append("X-Correlation-ID", correlation_id)
            await send(message)

        try:
            await self.app(scope, receive, send_with_header)
        finally:
            structlog.contextvars.clear_contextvars()
