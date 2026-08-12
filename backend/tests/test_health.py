from unittest.mock import patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_liveness(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health/live")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_database_pool_health_is_tenant_safe(client: AsyncClient) -> None:
    with patch("app.middleware.rate_limit.get_redis") as get_redis:
        response = await client.get("/api/v1/health/database-pool")

    assert response.status_code == 200
    get_redis.assert_not_called()
    payload = response.json()
    assert payload["status"] in {"ok", "saturated", "exhausted", "not_applicable"}
    assert payload["process_role"] == "api"
    assert "tenant" not in response.text.casefold()
