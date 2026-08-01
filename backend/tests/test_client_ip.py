from types import SimpleNamespace

from app.core.client_ip import get_client_ip


class Headers(dict[str, str]):
    def get(self, key: str, default: str | None = None) -> str | None:
        return super().get(key, default)


def request(
    direct_ip: str,
    forwarded_for: str | None = None,
) -> SimpleNamespace:
    headers = Headers()
    if forwarded_for:
        headers["x-forwarded-for"] = forwarded_for
    return SimpleNamespace(
        client=SimpleNamespace(host=direct_ip),
        headers=headers,
    )


def test_untrusted_client_cannot_spoof_forwarded_ip(monkeypatch) -> None:
    monkeypatch.setenv("TRUSTED_PROXY_IPS", "127.0.0.1")
    from app.core.config import get_settings

    get_settings.cache_clear()
    value = get_client_ip(request("198.51.100.10", "203.0.113.5"))
    get_settings.cache_clear()

    assert value == "198.51.100.10"


def test_trusted_proxy_uses_first_forwarded_ip(monkeypatch) -> None:
    monkeypatch.setenv("TRUSTED_PROXY_IPS", "127.0.0.1")
    from app.core.config import get_settings

    get_settings.cache_clear()
    value = get_client_ip(
        request("127.0.0.1", "203.0.113.5, 127.0.0.1")
    )
    get_settings.cache_clear()

    assert value == "203.0.113.5"
