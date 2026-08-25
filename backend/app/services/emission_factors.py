from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentPrincipal
from app.factors.uk_2026_importer import (
    FactorWorkbookValidationError,
    parse_uk_flat_workbook,
    read_binary_stream,
)
from app.models.emission_factor import (
    EmissionFactor,
    EmissionFactorSet,
    FactorImportError,
    FactorImportJob,
    FactorImportStatus,
    FactorSetStatus,
    GreenhouseGasComponent,
)
from app.schemas.emission_factor import FactorSetImportMetadata
from app.services.audit import record_audit_event


UK_PUBLISHER = "Department for Energy Security and Net Zero"
UK_DATASET_NAME = "UK Government GHG Conversion Factors for Company Reporting"
UK_GEOGRAPHY_CODE = "GB"
OPEN_GOVERNMENT_LICENCE = "Open Government Licence v3.0"
OPEN_GOVERNMENT_LICENCE_REFERENCE = (
    "https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/"
)


async def import_uk_factor_workbook(
    db: AsyncSession,
    principal: CurrentPrincipal,
    upload: UploadFile,
    metadata: FactorSetImportMetadata,
    *,
    expected_reporting_year: int,
) -> FactorImportJob:
    if not upload.filename or not upload.filename.lower().endswith(".xlsx"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="An .xlsx workbook is required.",
        )
    if metadata.reporting_year != expected_reporting_year:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"The UK {expected_reporting_year} importer only accepts "
                f"reporting_year={expected_reporting_year}."
            ),
        )
    if metadata.effective_to < metadata.effective_from:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="effective_to must be on or after effective_from.",
        )

    try:
        content = read_binary_stream(upload.file)
        parsed = parse_uk_flat_workbook(content, expected_reporting_year)
    except FactorWorkbookValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    existing_query = select(EmissionFactorSet).where(
        EmissionFactorSet.publisher == UK_PUBLISHER,
        EmissionFactorSet.dataset_name == UK_DATASET_NAME,
        EmissionFactorSet.dataset_version == metadata.dataset_version,
        EmissionFactorSet.source_sha256 == parsed.source_sha256,
    )
    existing = await db.scalar(existing_query)
    if existing is not None:
        job = FactorImportJob(
            factor_set_id=existing.id,
            status=FactorImportStatus.DUPLICATE,
            source_filename=upload.filename,
            source_sha256=parsed.source_sha256,
            dataset_version=metadata.dataset_version,
            reporting_year=metadata.reporting_year,
            total_rows=parsed.total_data_rows,
            imported_rows=len(parsed.factors),
            rejected_rows=len(parsed.errors),
            skipped_rows=parsed.skipped_unavailable_rows,
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            requested_by=principal.subject,
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)
        return job

    job = FactorImportJob(
        status=FactorImportStatus.PROCESSING,
        source_filename=upload.filename,
        source_sha256=parsed.source_sha256,
        dataset_version=metadata.dataset_version,
        reporting_year=metadata.reporting_year,
        total_rows=parsed.total_data_rows,
        imported_rows=0,
        rejected_rows=len(parsed.errors),
        started_at=datetime.now(UTC),
        requested_by=principal.subject,
    )
    db.add(job)
    await db.flush()

    for error in parsed.errors:
        db.add(
            FactorImportError(
                import_job_id=job.id,
                worksheet_name="Factors by Category",
                row_number=error.row_number,
                error_code=error.error_code,
                error_message=error.message,
                raw_row_data=error.raw_source_data,
                created_at=datetime.now(UTC),
            )
        )

    if parsed.errors:
        job.status = FactorImportStatus.FAILED
        job.completed_at = datetime.now(UTC)
        job.failure_message = "The workbook contained invalid rows. No factor set was committed."
        await db.commit()
        await db.refresh(job)
        return job

    factor_set = EmissionFactorSet(
        publisher=UK_PUBLISHER,
        dataset_name=UK_DATASET_NAME,
        dataset_version=metadata.dataset_version,
        reporting_year=metadata.reporting_year,
        publication_date=metadata.publication_date,
        effective_from=metadata.effective_from,
        effective_to=metadata.effective_to,
        geography_code=UK_GEOGRAPHY_CODE,
        source_filename=upload.filename,
        source_sha256=parsed.source_sha256,
        source_reference=metadata.source_reference,
        methodology_reference=metadata.methodology_reference,
        licence_name=OPEN_GOVERNMENT_LICENCE,
        licence_reference=OPEN_GOVERNMENT_LICENCE_REFERENCE,
        status=FactorSetStatus.DRAFT,
        is_authoritative=True,
        imported_at=datetime.now(UTC),
        imported_by=principal.subject,
        notes=metadata.notes,
    )
    db.add(factor_set)
    await db.flush()

    db.add_all(
        [
            EmissionFactor(
                factor_set_id=factor_set.id,
                source_factor_id=row.source_factor_id,
                scope=row.scope,
                level_1=row.level_1,
                level_2=row.level_2,
                level_3=row.level_3,
                level_4=row.level_4,
                column_text=row.column_text,
                activity_unit=row.activity_unit,
                factor_unit_text=row.factor_unit_text,
                greenhouse_gas_component=row.greenhouse_gas_component,
                greenhouse_gas_label=row.greenhouse_gas_label,
                factor_value=row.factor_value,
                factor_numerator_unit=row.factor_numerator_unit,
                factor_denominator_unit=row.factor_denominator_unit,
                geography_code=UK_GEOGRAPHY_CODE,
                reporting_year=metadata.reporting_year,
                lifecycle_boundary=row.lifecycle_boundary,
                source_row_number=row.source_row_number,
                raw_source_data=row.raw_source_data,
                is_active=True,
            )
            for row in parsed.factors
        ]
    )

    job.factor_set_id = factor_set.id
    job.status = FactorImportStatus.COMPLETED
    job.imported_rows = len(parsed.factors)
    job.completed_at = datetime.now(UTC)

    await record_audit_event(
        db,
        principal,
        action="emission_factor_set.imported",
        entity_type="emission_factor_set",
        entity_id=factor_set.id,
        event_data={
            "dataset_version": metadata.dataset_version,
            "reporting_year": metadata.reporting_year,
            "source_sha256": parsed.source_sha256,
            "factor_count": len(parsed.factors),
        },
    )

    await db.commit()
    await db.refresh(job)
    return job


async def import_uk_2026_factor_workbook(
    db: AsyncSession,
    principal: CurrentPrincipal,
    upload: UploadFile,
    metadata: FactorSetImportMetadata,
) -> FactorImportJob:
    return await import_uk_factor_workbook(
        db,
        principal,
        upload,
        metadata,
        expected_reporting_year=2026,
    )


async def import_uk_2024_factor_workbook(
    db: AsyncSession,
    principal: CurrentPrincipal,
    upload: UploadFile,
    metadata: FactorSetImportMetadata,
) -> FactorImportJob:
    return await import_uk_factor_workbook(
        db,
        principal,
        upload,
        metadata,
        expected_reporting_year=2024,
    )


async def import_uk_2023_factor_workbook(
    db: AsyncSession,
    principal: CurrentPrincipal,
    upload: UploadFile,
    metadata: FactorSetImportMetadata,
) -> FactorImportJob:
    return await import_uk_factor_workbook(
        db,
        principal,
        upload,
        metadata,
        expected_reporting_year=2023,
    )


async def import_uk_2025_factor_workbook(
    db: AsyncSession,
    principal: CurrentPrincipal,
    upload: UploadFile,
    metadata: FactorSetImportMetadata,
) -> FactorImportJob:
    return await import_uk_factor_workbook(
        db,
        principal,
        upload,
        metadata,
        expected_reporting_year=2025,
    )


async def list_factor_sets(
    db: AsyncSession,
    *,
    status_filter: FactorSetStatus | None = None,
    reporting_year: int | None = None,
) -> list[EmissionFactorSet]:
    query = select(EmissionFactorSet)
    if status_filter is not None:
        query = query.where(EmissionFactorSet.status == status_filter)
    if reporting_year is not None:
        query = query.where(EmissionFactorSet.reporting_year == reporting_year)
    query = query.order_by(
        EmissionFactorSet.reporting_year.desc(),
        EmissionFactorSet.dataset_version.desc(),
    )
    return list((await db.scalars(query)).all())


async def get_factor_set(
    db: AsyncSession,
    factor_set_id: UUID,
) -> EmissionFactorSet | None:
    return await db.get(EmissionFactorSet, factor_set_id)


async def get_import_job(
    db: AsyncSession,
    import_job_id: UUID,
) -> FactorImportJob | None:
    return await db.get(FactorImportJob, import_job_id)


async def list_import_errors(
    db: AsyncSession,
    import_job_id: UUID,
) -> list[FactorImportError]:
    query = (
        select(FactorImportError)
        .where(FactorImportError.import_job_id == import_job_id)
        .order_by(FactorImportError.row_number)
    )
    return list((await db.scalars(query)).all())


async def approve_factor_set(
    db: AsyncSession,
    principal: CurrentPrincipal,
    factor_set: EmissionFactorSet,
    reason: str,
) -> EmissionFactorSet:
    if factor_set.status != FactorSetStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only draft factor sets can be approved.",
        )

    if factor_set.imported_by == principal.subject:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A factor set must be approved by someone other than its importer.",
        )

    factor_count = int(
        (
            await db.scalar(
                select(func.count())
                .select_from(EmissionFactor)
                .where(EmissionFactor.factor_set_id == factor_set.id)
            )
        )
        or 0
    )
    if factor_count == 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An empty factor set cannot be approved.",
        )

    factor_set.status = FactorSetStatus.APPROVED
    factor_set.approved_at = datetime.now(UTC)
    factor_set.approved_by = principal.subject

    await record_audit_event(
        db,
        principal,
        action="emission_factor_set.approved",
        entity_type="emission_factor_set",
        entity_id=factor_set.id,
        event_data={"reason": reason, "factor_count": factor_count},
    )
    await db.commit()
    await db.refresh(factor_set)
    return factor_set


async def supersede_factor_set(
    db: AsyncSession,
    principal: CurrentPrincipal,
    factor_set: EmissionFactorSet,
    replacement: EmissionFactorSet,
    reason: str,
) -> EmissionFactorSet:
    if factor_set.id == replacement.id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A factor set cannot supersede itself.",
        )
    if factor_set.status != FactorSetStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only approved factor sets can be superseded.",
        )
    if replacement.status != FactorSetStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The replacement factor set must be approved.",
        )

    factor_set.status = FactorSetStatus.SUPERSEDED
    factor_set.superseded_at = datetime.now(UTC)
    factor_set.superseded_by_set_id = replacement.id

    await record_audit_event(
        db,
        principal,
        action="emission_factor_set.superseded",
        entity_type="emission_factor_set",
        entity_id=factor_set.id,
        event_data={
            "replacement_factor_set_id": str(replacement.id),
            "reason": reason,
        },
    )
    await db.commit()
    await db.refresh(factor_set)
    return factor_set


async def search_factors(
    db: AsyncSession,
    *,
    query_text: str | None,
    factor_set_id: UUID | None,
    reporting_year: int | None,
    scope: str | None,
    level_1: str | None,
    activity_unit: str | None,
    component: GreenhouseGasComponent | None,
    approved_only: bool,
    limit: int,
    offset: int,
) -> tuple[list[EmissionFactor], int]:
    query = select(EmissionFactor).join(EmissionFactorSet)
    count_query = select(func.count()).select_from(EmissionFactor).join(EmissionFactorSet)

    conditions = []
    if factor_set_id is not None:
        conditions.append(EmissionFactor.factor_set_id == factor_set_id)
    if reporting_year is not None:
        conditions.append(EmissionFactor.reporting_year == reporting_year)
    if scope is not None:
        conditions.append(EmissionFactor.scope == scope)
    if level_1 is not None:
        conditions.append(EmissionFactor.level_1 == level_1)
    if activity_unit is not None:
        conditions.append(EmissionFactor.activity_unit == activity_unit)
    if component is not None:
        conditions.append(EmissionFactor.greenhouse_gas_component == component)
    if approved_only:
        conditions.append(EmissionFactorSet.status == FactorSetStatus.APPROVED)
    if query_text:
        pattern = f"%{query_text.strip()}%"
        conditions.append(
            or_(
                EmissionFactor.source_factor_id.ilike(pattern),
                EmissionFactor.level_1.ilike(pattern),
                EmissionFactor.level_2.ilike(pattern),
                EmissionFactor.level_3.ilike(pattern),
                EmissionFactor.level_4.ilike(pattern),
                EmissionFactor.column_text.ilike(pattern),
            )
        )

    if conditions:
        query = query.where(*conditions)
        count_query = count_query.where(*conditions)

    query = (
        query.order_by(
            EmissionFactor.level_1,
            EmissionFactor.level_2,
            EmissionFactor.level_3,
            EmissionFactor.activity_unit,
            EmissionFactor.source_factor_id,
        )
        .limit(limit)
        .offset(offset)
    )

    items = list((await db.scalars(query)).all())
    total = int((await db.scalar(count_query)) or 0)
    return items, total
