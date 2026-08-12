from __future__ import annotations

import hashlib
import inspect
import logging
from dataclasses import dataclass

from redis.exceptions import RedisError
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.client_ip import get_client_ip
from app.core.config import get_settings
from app.core.redis import get_redis

logger = logging.getLogger(__name__)

FIXED_WINDOW_SCRIPT = """
local current = redis.call('INCR', KEYS[1])
if current == 1 then
  redis.call('EXPIRE', KEYS[1], ARGV[1])
end
local ttl = redis.call('TTL', KEYS[1])
return {current, ttl}
"""


@dataclass(frozen=True, slots=True)
class RatePolicy:
    name: str
    limit: int
    window_seconds: int


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        settings = get_settings()
        if request.url.path.endswith('/health/live'):
            return await call_next(request)
        if not settings.rate_limit_enabled:
            return await call_next(request)

        policy = _policy_for(request.url.path)
        client_ip = get_client_ip(request) or "unknown"
        key_material = f"{policy.name}:{client_ip}"
        key = "rate:" + hashlib.sha256(key_material.encode("utf-8")).hexdigest()

        try:
            pending_result = get_redis().eval(
                FIXED_WINDOW_SCRIPT,
                1,
                key,
                str(policy.window_seconds),
            )
            result = (
                await pending_result
                if inspect.isawaitable(pending_result)
                else pending_result
            )
            if not isinstance(result, (list, tuple)) or len(result) != 2:
                raise RedisError("Unexpected rate-limit script response.")
            count = _redis_int(result[0])
            ttl = max(_redis_int(result[1]), 0)
        except RedisError:
            logger.exception("rate_limit_redis_failure")
            if settings.rate_limit_fail_open:
                return await call_next(request)
            return JSONResponse(
                status_code=503,
                content={"detail": "Request protection service is unavailable."},
                headers={"Retry-After": "5"},
            )

        remaining = max(policy.limit - count, 0)
        headers = {
            "RateLimit-Limit": str(policy.limit),
            "RateLimit-Remaining": str(remaining),
            "RateLimit-Reset": str(ttl),
        }
        if count > policy.limit:
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests."},
                headers={**headers, "Retry-After": str(max(ttl, 1))},
            )

        response = await call_next(request)
        response.headers.update(headers)
        return response


def _redis_int(value: object) -> int:
    if isinstance(value, (str, bytes, bytearray, int, float)):
        return int(value)
    raise RedisError("Rate-limit script returned a non-numeric value.")


def _policy_for(path: str) -> RatePolicy:
    settings = get_settings()
    if path.endswith("/auth/login"):
        return RatePolicy(
            "login",
            settings.rate_limit_login_requests,
            settings.rate_limit_login_window_seconds,
        )
    if "/auth/mfa/" in path:
        return RatePolicy(
            "mfa",
            settings.rate_limit_mfa_requests,
            settings.rate_limit_mfa_window_seconds,
        )
    if "/auth/password-reset/" in path:
        return RatePolicy(
            "password_reset",
            settings.rate_limit_password_reset_requests,
            settings.rate_limit_password_reset_window_seconds,
        )
    if path.endswith("/auth/refresh"):
        return RatePolicy(
            "refresh",
            settings.rate_limit_refresh_requests,
            settings.rate_limit_refresh_window_seconds,
        )
    return RatePolicy(
        "general",
        settings.rate_limit_general_requests,
        settings.rate_limit_general_window_seconds,
    )
