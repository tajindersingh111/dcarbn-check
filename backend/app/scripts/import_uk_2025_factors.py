from __future__ import annotations

import argparse
import asyncio
from datetime import date
from pathlib import Path
from uuid import UUID

from fastapi import UploadFile

from app.auth.dependencies import CurrentPrincipal
from app.db.session import AsyncSessionFactory
from app.schemas.emission_factor import FactorSetImportMetadata
from app.services.emission_factors import import_uk_2025_factor_workbook


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import the official final UK Government 2025 flat-format factor workbook."
    )
    parser.add_argument("workbook", type=Path)
    parser.add_argument("--dataset-version", default="2025-v1.0")
    parser.add_argument("--reporting-year", type=int, default=2025)
    parser.add_argument("--publication-date", type=date.fromisoformat)
    parser.add_argument("--effective-from", type=date.fromisoformat, required=True)
    parser.add_argument("--effective-to", type=date.fromisoformat, required=True)
    parser.add_argument("--source-reference")
    parser.add_argument("--methodology-reference")
    parser.add_argument("--subject", default="cli-factor-import")
    parser.add_argument(
        "--tenant-id",
        type=UUID,
        default=UUID("00000000-0000-0000-0000-000000000000"),
    )
    return parser.parse_args()


async def run() -> None:
    args = parse_args()
    if not args.workbook.is_file():
        raise SystemExit(f"Workbook not found: {args.workbook}")

    metadata = FactorSetImportMetadata(
        dataset_version=args.dataset_version,
        reporting_year=args.reporting_year,
        publication_date=args.publication_date,
        effective_from=args.effective_from,
        effective_to=args.effective_to,
        source_reference=args.source_reference,
        methodology_reference=args.methodology_reference,
        notes=(
            "UK Government 2025 final factor set. HVO is available only when "
            "explicitly selected and evidenced."
        ),
    )
    principal = CurrentPrincipal(
        subject=args.subject,
        tenant_id=args.tenant_id,
        roles=frozenset({"platform_admin", "factor_manager"}),
    )

    async with AsyncSessionFactory() as db:
        with args.workbook.open("rb") as stream:
            upload = UploadFile(filename=args.workbook.name, file=stream)
            job = await import_uk_2025_factor_workbook(db, principal, upload, metadata)
            print(
                f"Import {job.status}: {job.imported_rows} imported, "
                f"{job.rejected_rows} rejected, job={job.id}"
            )


if __name__ == "__main__":
    asyncio.run(run())
