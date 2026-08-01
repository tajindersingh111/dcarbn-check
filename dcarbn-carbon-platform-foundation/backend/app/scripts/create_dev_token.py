from __future__ import annotations

import argparse
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt

from app.core.config import get_settings


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a local development JWT.")
    parser.add_argument("--subject", required=True)
    parser.add_argument("--tenant-id", type=UUID, required=True)
    parser.add_argument("--roles", nargs="+", default=["tenant_admin"])
    parser.add_argument("--hours", type=int, default=8)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = get_settings()
    now = datetime.now(UTC)

    token = jwt.encode(
        {
            "sub": args.subject,
            "tenant_id": str(args.tenant_id),
            "roles": args.roles,
            "aud": settings.access_token_audience,
            "iat": now,
            "exp": now + timedelta(hours=args.hours),
        },
        settings.secret_key,
        algorithm=settings.jwt_algorithm,
    )
    print(token)


if __name__ == "__main__":
    main()
