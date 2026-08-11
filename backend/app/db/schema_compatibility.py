from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.db.migration_control import assert_supported_schema_version


async def assert_runtime_schema_compatible(engine: AsyncEngine) -> None:
    """Fail application startup unless PostgreSQL is at a reviewed revision."""

    async with engine.connect() as connection:
        exists = await connection.scalar(
            text("SELECT to_regclass('public.alembic_version') IS NOT NULL")
        )
        version: str | None = None
        if exists:
            value = await connection.scalar(
                text("SELECT version_num FROM alembic_version LIMIT 1")
            )
            version = str(value) if value is not None else None
    assert_supported_schema_version(version)
