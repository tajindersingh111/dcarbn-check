from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from redis.exceptions import RedisError
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.redis import get_redis
from app.db.session import get_db
from app.schemas.health import HealthResponse
from app.schemas.operations import (
    OperationalHealthResponse,
    RecoveryReadinessResponse,
)
from app.services.operational_health import (
    operational_health,
    recovery_readiness,
)

router = APIRouter()


@router.get("/health/live", response_model=HealthResponse)
async def liveness() -> HealthResponse:
    return HealthResponse(status="ok", timestamp=datetime.now(UTC))


@router.get("/health/ready", response_model=HealthResponse)
async def readiness(db: AsyncSession = Depends(get_db)) -> HealthResponse:
    await db.execute(text("SELECT 1"))

    try:
        await get_redis().ping()
    except RedisError as exc:
        if get_settings().redis_required:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Redis dependency is unavailable.",
            ) from exc

    return HealthResponse(status="ok", timestamp=datetime.now(UTC))


@router.get(
    "/health/operational",
    response_model=OperationalHealthResponse,
)
async def operational_status(
    db: AsyncSession = Depends(get_db),
) -> OperationalHealthResponse:
    return await operational_health(db)



@router.get(
    "/health/recovery-readiness",
    response_model=RecoveryReadinessResponse,
)
async def recovery_status() -> RecoveryReadinessResponse:
    return recovery_readiness()
