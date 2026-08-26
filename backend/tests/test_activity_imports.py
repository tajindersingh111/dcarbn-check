from __future__ import annotations

from datetime import date
from io import BytesIO
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException, UploadFile
from httpx import AsyncClient
from openpyxl import Workbook

from app.auth.dependencies import CurrentPrincipal, get_current_principal
from app.main import app
from app.services.activity_imports import parse_activity_workbook
from tests.conftest import TEST_TENANT_ID

HEADERS = [
    "calculation_method_id",
    "activity_date",
    "description",
    "activity_value",
    "activity_unit",
    "evidence_reference",
    "source_record_id",
    "geography_code",
]


def _principal() -> CurrentPrincipal:
    return CurrentPrincipal(
        subject="excel-reviewer@example.com",
        tenant_id=TEST_TENANT_ID,
        roles=frozenset({"sustainability_manager"}),
    )


def _workbook_bytes(
    rows: list[list[object]],
    *,
    second_sheet_rows: list[list[object]] | None = None,
) -> bytes:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Activity data"
    for row in rows:
        worksheet.append(row)
    if second_sheet_rows is not None:
        second = workbook.create_sheet("Second activity table")
        for row in second_sheet_rows:
            second.append(row)
    stream = BytesIO()
    workbook.save(stream)
    workbook.close()
    return stream.getvalue()


def _upload(content: bytes, filename: str = "activity-upload.xlsx") -> UploadFile:
    return UploadFile(filename=filename, file=BytesIO(content))


@pytest.mark.asyncio
async def test_excel_activity_parser_returns_plain_headers_and_rows() -> None:
    content = _workbook_bytes(
        [
            HEADERS,
            [
                "scope2.location_electricity.kwh.uk_2026.v1",
                date(2026, 3, 31),
                "Purchased electricity",
                50_000,
                "kWh",
                "electricity-bill.pdf",
                "electricity-excel-001",
                "GB",
            ],
        ]
    )

    headers, rows = await parse_activity_workbook(_upload(content))

    assert headers == HEADERS
    assert rows == [
        [
            "scope2.location_electricity.kwh.uk_2026.v1",
            "2026-03-31",
            "Purchased electricity",
            "50000",
            "kWh",
            "electricity-bill.pdf",
            "electricity-excel-001",
            "GB",
        ]
    ]


@pytest.mark.asyncio
async def test_excel_activity_parser_rejects_formulas() -> None:
    content = _workbook_bytes(
        [
            HEADERS,
            [
                "scope2.location_electricity.kwh.uk_2026.v1",
                "2026-03-31",
                "Purchased electricity",
                "=25000*2",
                "kWh",
                "electricity-bill.pdf",
                "electricity-excel-formula",
                "GB",
            ],
        ]
    )

    with pytest.raises(HTTPException, match="contains a formula"):
        await parse_activity_workbook(_upload(content))


@pytest.mark.asyncio
async def test_excel_activity_parser_rejects_multiple_populated_sheets() -> None:
    content = _workbook_bytes(
        [HEADERS, ["method-one", "2026-03-31", "First"]],
        second_sheet_rows=[HEADERS, ["method-two", "2026-03-31", "Second"]],
    )

    with pytest.raises(HTTPException, match="one populated worksheet"):
        await parse_activity_workbook(_upload(content))


@pytest.mark.asyncio
async def test_excel_activity_parser_rejects_legacy_excel_files() -> None:
    with pytest.raises(HTTPException, match="Excel .xlsx"):
        await parse_activity_workbook(_upload(b"legacy", filename="activity-upload.xls"))


@pytest.mark.asyncio
async def test_excel_activity_parser_rejects_invalid_xlsx_archives() -> None:
    with pytest.raises(HTTPException, match="not a valid .xlsx"):
        await parse_activity_workbook(_upload(b"not-an-xlsx-workbook"))


@pytest.mark.asyncio
async def test_excel_activity_parse_api_accepts_governed_workbook(
    client: AsyncClient,
) -> None:
    app.dependency_overrides[get_current_principal] = _principal
    content = _workbook_bytes(
        [
            HEADERS,
            [
                "scope1.stationary_diesel.litres.uk_2026.v1",
                "2026-03-31",
                "Generator diesel",
                1250,
                "litres",
                "fuel-invoice.pdf",
                "fuel-excel-001",
                "GB",
            ],
        ]
    )

    with patch("app.middleware.rate_limit.get_redis") as get_redis:
        get_redis.return_value.eval = AsyncMock(return_value=[1, 60])
        response = await client.post(
            "/api/v1/activity-imports/parse-workbook",
            files={
                "workbook": (
                    "activity-upload.xlsx",
                    content,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
        )

    assert response.status_code == 200, response.text
    assert response.json()["headers"] == HEADERS
    assert response.json()["rows"][0][6] == "fuel-excel-001"
