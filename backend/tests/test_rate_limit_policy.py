from app.middleware.rate_limit import _policy_for


def test_login_uses_dedicated_rate_limit(monkeypatch) -> None:
    monkeypatch.setenv("RATE_LIMIT_LOGIN_REQUESTS", "7")
    monkeypatch.setenv("RATE_LIMIT_LOGIN_WINDOW_SECONDS", "120")
    from app.core.config import get_settings

    get_settings.cache_clear()
    policy = _policy_for("/api/v1/auth/login")
    get_settings.cache_clear()

    assert policy.name == "login"
    assert policy.limit == 7
    assert policy.window_seconds == 120


def test_password_reset_uses_recovery_policy() -> None:
    policy = _policy_for("/api/v1/auth/password-reset/request")

    assert policy.name == "password_reset"
