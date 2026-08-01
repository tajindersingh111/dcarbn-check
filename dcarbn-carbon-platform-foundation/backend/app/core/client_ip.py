from __future__ import annotations

import ipaddress

from fastapi import Request

from app.core.config import get_settings


def get_client_ip(request: Request) -> str | None:
    direct_ip = request.client.host if request.client else None
    if direct_ip is None:
        return None

    settings = get_settings()
    if not _is_trusted_proxy(direct_ip, settings.trusted_proxy_ips):
        return direct_ip

    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        candidate = forwarded.split(",", 1)[0].strip()
        if _valid_ip(candidate):
            return candidate

    real_ip = request.headers.get("x-real-ip")
    if real_ip and _valid_ip(real_ip):
        return real_ip

    return direct_ip


def _is_trusted_proxy(address: str, trusted_values: list[str]) -> bool:
    try:
        ip = ipaddress.ip_address(address)
    except ValueError:
        return False

    for value in trusted_values:
        try:
            if "/" in value:
                if ip in ipaddress.ip_network(value, strict=False):
                    return True
            elif ip == ipaddress.ip_address(value):
                return True
        except ValueError:
            continue
    return False


def _valid_ip(value: str) -> bool:
    try:
        ipaddress.ip_address(value)
        return True
    except ValueError:
        return False
