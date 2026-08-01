from datetime import UTC, datetime, timedelta

import jwt
import pytest
from httpx import AsyncClient

from app.core.config import get_settings
from tests.conftest import TEST_TENANT_ID


def auth_headers() -> dict[str, str]:
    settings = get_settings()
    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "sub": "test-user",
            "tenant_id": str(TEST_TENANT_ID),
            "roles": ["tenant_admin"],
            "aud": settings.access_token_audience,
            "iat": now,
            "exp": now + timedelta(minutes=30),
        },
        settings.secret_key,
        algorithm=settings.jwt_algorithm,
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_create_and_list_organisation(client: AsyncClient) -> None:
    create_response = await client.post(
        "/api/v1/organisations",
        headers=auth_headers(),
        json={
            "name": "Example Logistics Ltd",
            "legal_name": "Example Logistics Limited",
            "registration_number": "12345678",
            "country_code": "gb",
        },
    )

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["country_code"] == "GB"
    assert created["name"] == "Example Logistics Ltd"

    list_response = await client.get(
        "/api/v1/organisations",
        headers=auth_headers(),
    )

    assert list_response.status_code == 200
    result = list_response.json()
    assert result["total"] == 1
    assert result["items"][0]["id"] == created["id"]
