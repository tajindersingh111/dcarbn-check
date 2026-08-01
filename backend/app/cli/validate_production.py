from __future__ import annotations

from app.core.config import get_settings


def main() -> None:
    settings = get_settings()
    if settings.app_env != "production":
        raise SystemExit("APP_ENV must be production.")
    print("Production configuration validation passed.")


if __name__ == "__main__":
    main()
