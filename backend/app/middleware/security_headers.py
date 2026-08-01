from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import get_settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        settings = get_settings()

        response.headers["Content-Security-Policy"] = (
            settings.content_security_policy
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), payment=(), usb=()"
        )
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Cross-Origin-Resource-Policy"] = "same-site"
        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"

        if request.url.path.startswith(settings.api_v1_prefix):
            response.headers["Cache-Control"] = "no-store"
            response.headers["Pragma"] = "no-cache"

        if settings.hsts_enabled:
            value = f"max-age={settings.hsts_max_age_seconds}"
            if settings.hsts_include_subdomains:
                value += "; includeSubDomains"
            if settings.hsts_preload:
                value += "; preload"
            response.headers["Strict-Transport-Security"] = value

        return response
