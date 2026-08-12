from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.exc import TimeoutError as SQLAlchemyTimeoutError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import get_settings
from app.db.pool_metrics import (
    acquisition_started,
    observe_acquisition,
    record_acquisition_timeout,
)
from app.db.pooling import (
    create_database_engine,
    create_operator_engine,
    create_session_factory,
)
from app.db.tenant_context import clear_tenant_context

settings = get_settings()

engine = create_database_engine(settings)
operator_engine = create_operator_engine(settings)

AsyncSessionFactory = create_session_factory(engine, settings)
OperatorSessionFactory = async_sessionmaker(
    bind=operator_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionFactory() as session:
        started = acquisition_started()
        try:
            await session.connection()
        except SQLAlchemyTimeoutError:
            record_acquisition_timeout(settings.database_process_role)
            await session.rollback()
            raise
        observe_acquisition(settings.database_process_role, started)
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            clear_tenant_context(session)
