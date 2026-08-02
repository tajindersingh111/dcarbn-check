from uuid import UUID

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from app.auth.dependencies import CurrentPrincipal, get_current_principal
from app.main import app
from tests.conftest import TEST_TENANT_ID

TEST_USER_ID = UUID("22222222-2222-2222-2222-222222222222")


def authenticated_principal() -> CurrentPrincipal:
    return CurrentPrincipal(
        subject=str(TEST_USER_ID),
        tenant_id=TEST_TENANT_ID,
        roles=frozenset({"tenant_admin"}),
    )


@pytest.mark.asyncio
async def test_create_and_list_organisation(client: AsyncClient) -> None:
    application: FastAPI = app
    application.dependency_overrides[get_current_principal] = authenticated_principal

    create_response = await client.post(
        "/api/v1/organisations",
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

    list_response = await client.get("/api/v1/organisations")

    assert list_response.status_code == 200
    result = list_response.json()
    assert result["total"] == 1
    assert result["items"][0]["id"] == created["id"]
