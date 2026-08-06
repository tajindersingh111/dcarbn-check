from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Callable, Coroutine, TypeVar
from uuid import UUID

from fastapi import HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentPrincipal
from app.integrations.data.hashing import canonical_json_sha256
from app.models.activity import ActivityRecord
from app.models.data_integration import (
    DataClassificationStatus,
    DataFuelRecord,
    DataImportBatch,
    DataImportError,
    DataImportStatus,
    DataJourney,
    DataOperationalEmission,
    DataOrganisationMapping,
    DataPayloadRecord,
    DataRecordType,
    DataShipment,
    DataVehicle,
)
from app.models.organisation import Organisation
from app.schemas.data_integration import (
    DataBatchRequest,
    DataClassificationConfirmRequest,
    DataFuelPayload,
    DataJourneyPayload,
    DataOperationalEmissionPayload,
    DataOrganisationMappingCreate,
    DataPayloadPayload,
    DataShipmentPayload,
    DataVehiclePayload,
)
from app.services.audit import record_audit_event


PayloadT = TypeVar("PayloadT", bound=BaseModel)
UpsertHandler = Callable[
    [AsyncSession, CurrentPrincipal, PayloadT],
    Coroutine[Any, Any, None],
]


async def create_mapping(
    db: AsyncSession,
    principal: CurrentPrincipal,
    payload: DataOrganisationMappingCreate,
) -> DataOrganisationMapping:
    organisation = await db.scalar(
        select(Organisation).where(
            Organisation.id == payload.organisation_id,
            Organisation.tenant_id == principal.tenant_id,
        )
    )
    if organisation is None:
        raise HTTPException(status_code=404, detail="Organisation not found.")

    existing = await db.scalar(
        select(DataOrganisationMapping).where(
            DataOrganisationMapping.tenant_id == principal.tenant_id,
            DataOrganisationMapping.external_customer_id
            == payload.external_customer_id,
        )
    )
    if existing is not None:
        existing.organisation_id = payload.organisation_id
        existing.external_customer_name = payload.external_customer_name
        existing.mapping_notes = payload.mapping_notes
        existing.is_active = True
        mapping = existing
    else:
        mapping = DataOrganisationMapping(
            tenant_id=principal.tenant_id,
            **payload.model_dump(),
        )
        db.add(mapping)
        await db.flush()

    await record_audit_event(
        db,
        principal,
        action="data.organisation_mapping.upserted",
        entity_type="data_organisation_mapping",
        entity_id=mapping.id,
        event_data={
            "external_customer_id": mapping.external_customer_id,
            "organisation_id": str(mapping.organisation_id),
        },
    )
    await db.commit()
    await db.refresh(mapping)
    return mapping


async def _organisation_id(
    db: AsyncSession,
    tenant_id: UUID,
    external_customer_id: str,
) -> UUID:
    mapping = await db.scalar(
        select(DataOrganisationMapping).where(
            DataOrganisationMapping.tenant_id == tenant_id,
            DataOrganisationMapping.external_customer_id
            == external_customer_id,
            DataOrganisationMapping.is_active.is_(True),
        )
    )
    if mapping is None:
        raise ValueError(
            f"No active organisation mapping exists for "
            f"external_customer_id={external_customer_id!r}."
        )
    return mapping.organisation_id


async def _linked_id(
    db: AsyncSession,
    model: type[Any],
    tenant_id: UUID,
    external_field: Any,
    external_value: str | None,
) -> UUID | None:
    if not external_value:
        return None
    item = await db.scalar(
        select(model).where(
            model.tenant_id == tenant_id,
            external_field == external_value,
        )
    )
    if item is None:
        raise ValueError(f"Referenced DATa record was not found: {external_value}.")
    return item.id


async def process_batch(
    db: AsyncSession,
    principal: CurrentPrincipal,
    *,
    record_type: DataRecordType,
    request: DataBatchRequest[PayloadT],
    handler: UpsertHandler[PayloadT],
    external_id_getter: Callable[[PayloadT], str],
) -> DataImportBatch:
    payload_dict = request.model_dump(mode="json")
    payload_hash = canonical_json_sha256(payload_dict)

    existing = await db.scalar(
        select(DataImportBatch).where(
            DataImportBatch.tenant_id == principal.tenant_id,
            DataImportBatch.idempotency_key == request.idempotency_key,
        )
    )
    if existing is not None:
        if existing.source_payload_sha256 != payload_hash:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "The idempotency key has already been used with a "
                    "different payload."
                ),
            )
        existing.status = DataImportStatus.DUPLICATE
        await db.commit()
        await db.refresh(existing)
        return existing

    batch = DataImportBatch(
        tenant_id=principal.tenant_id,
        schema_version=request.schema_version,
        record_type=record_type,
        idempotency_key=request.idempotency_key,
        source_payload_sha256=payload_hash,
        status=DataImportStatus.PROCESSING,
        records_received=len(request.records),
        started_at=datetime.now(UTC),
        requested_by=principal.subject,
    )
    db.add(batch)
    await db.flush()

    for index, record in enumerate(request.records):
        try:
            await handler(db, principal, record)
            batch.records_imported += 1
        except ValueError as exc:
            batch.records_rejected += 1
            db.add(
                DataImportError(
                    batch_id=batch.id,
                    record_index=index,
                    external_record_id=external_id_getter(record),
                    error_code="record_rejected",
                    error_message=str(exc),
                    raw_record=record.model_dump(mode="json"),
                    created_at=datetime.now(UTC),
                )
            )

    batch.completed_at = datetime.now(UTC)
    if batch.records_rejected == 0:
        batch.status = DataImportStatus.COMPLETED
    elif batch.records_imported == 0:
        batch.status = DataImportStatus.FAILED
        batch.failure_message = "All records were rejected."
    else:
        batch.status = DataImportStatus.PARTIAL

    await record_audit_event(
        db,
        principal,
        action="data.batch_import.completed",
        entity_type="data_import_batch",
        entity_id=batch.id,
        event_data={
            "record_type": record_type.value,
            "records_received": batch.records_received,
            "records_imported": batch.records_imported,
            "records_rejected": batch.records_rejected,
            "status": batch.status.value,
        },
    )
    await db.commit()
    await db.refresh(batch)
    return batch


async def upsert_vehicle(
    db: AsyncSession,
    principal: CurrentPrincipal,
    payload: DataVehiclePayload,
) -> None:
    organisation_id = await _organisation_id(
        db,
        principal.tenant_id,
        payload.external_customer_id,
    )
    source_hash = canonical_json_sha256(payload.model_dump(mode="json"))
    item = await db.scalar(
        select(DataVehicle).where(
            DataVehicle.tenant_id == principal.tenant_id,
            DataVehicle.external_vehicle_id == payload.external_vehicle_id,
        )
    )
    values = {
        "organisation_id": organisation_id,
        "registration_number": payload.registration_number,
        "vehicle_type": payload.vehicle_type,
        "fuel_type": payload.fuel_type,
        "gross_vehicle_weight_kg": payload.gross_vehicle_weight_kg,
        "model_year": payload.model_year,
        "metadata_json": payload.metadata,
        "source_record_hash": source_hash,
        "source_updated_at": payload.source_updated_at,
    }
    if item is None:
        db.add(
            DataVehicle(
                tenant_id=principal.tenant_id,
                external_vehicle_id=payload.external_vehicle_id,
                **values,
            )
        )
    elif item.source_record_hash != source_hash:
        for field, value in values.items():
            setattr(item, field, value)


async def upsert_shipment(
    db: AsyncSession,
    principal: CurrentPrincipal,
    payload: DataShipmentPayload,
) -> None:
    organisation_id = await _organisation_id(
        db,
        principal.tenant_id,
        payload.external_customer_id,
    )
    source_hash = canonical_json_sha256(payload.model_dump(mode="json"))
    item = await db.scalar(
        select(DataShipment).where(
            DataShipment.tenant_id == principal.tenant_id,
            DataShipment.external_shipment_id == payload.external_shipment_id,
        )
    )
    values = {
        "organisation_id": organisation_id,
        "external_consignment_id": payload.external_consignment_id,
        "shipment_date": payload.shipment_date,
        "origin_country_code": payload.origin_country_code,
        "origin_postcode": payload.origin_postcode,
        "destination_country_code": payload.destination_country_code,
        "destination_postcode": payload.destination_postcode,
        "metadata_json": payload.metadata,
        "source_record_hash": source_hash,
        "source_updated_at": payload.source_updated_at,
    }
    if item is None:
        db.add(
            DataShipment(
                tenant_id=principal.tenant_id,
                external_shipment_id=payload.external_shipment_id,
                **values,
            )
        )
    elif item.source_record_hash != source_hash:
        for field, value in values.items():
            setattr(item, field, value)


async def upsert_journey(
    db: AsyncSession,
    principal: CurrentPrincipal,
    payload: DataJourneyPayload,
) -> None:
    organisation_id = await _organisation_id(
        db,
        principal.tenant_id,
        payload.external_customer_id,
    )
    vehicle_id = await _linked_id(
        db,
        DataVehicle,
        principal.tenant_id,
        DataVehicle.external_vehicle_id,
        payload.external_vehicle_id,
    )
    shipment_id = await _linked_id(
        db,
        DataShipment,
        principal.tenant_id,
        DataShipment.external_shipment_id,
        payload.external_shipment_id,
    )
    source_hash = canonical_json_sha256(payload.model_dump(mode="json"))
    item = await db.scalar(
        select(DataJourney).where(
            DataJourney.tenant_id == principal.tenant_id,
            DataJourney.external_journey_id == payload.external_journey_id,
        )
    )
    values = {
        "organisation_id": organisation_id,
        "vehicle_id": vehicle_id,
        "shipment_id": shipment_id,
        "journey_started_at": payload.journey_started_at,
        "journey_completed_at": payload.journey_completed_at,
        "distance_value": payload.distance_value,
        "distance_unit": payload.distance_unit,
        "distance_source": payload.distance_source,
        "route_reference": payload.route_reference,
        "metadata_json": payload.metadata,
        "source_record_hash": source_hash,
        "source_updated_at": payload.source_updated_at,
    }
    if item is None:
        db.add(
            DataJourney(
                tenant_id=principal.tenant_id,
                external_journey_id=payload.external_journey_id,
                **values,
            )
        )
    elif item.source_record_hash != source_hash:
        for field, value in values.items():
            setattr(item, field, value)


async def upsert_fuel(
    db: AsyncSession,
    principal: CurrentPrincipal,
    payload: DataFuelPayload,
) -> None:
    organisation_id = await _organisation_id(
        db,
        principal.tenant_id,
        payload.external_customer_id,
    )
    journey_id = await _linked_id(
        db,
        DataJourney,
        principal.tenant_id,
        DataJourney.external_journey_id,
        payload.external_journey_id,
    )
    vehicle_id = await _linked_id(
        db,
        DataVehicle,
        principal.tenant_id,
        DataVehicle.external_vehicle_id,
        payload.external_vehicle_id,
    )
    source_hash = canonical_json_sha256(payload.model_dump(mode="json"))
    item = await db.scalar(
        select(DataFuelRecord).where(
            DataFuelRecord.tenant_id == principal.tenant_id,
            DataFuelRecord.external_fuel_record_id
            == payload.external_fuel_record_id,
        )
    )
    values = {
        "organisation_id": organisation_id,
        "journey_id": journey_id,
        "vehicle_id": vehicle_id,
        "fuel_type": payload.fuel_type,
        "quantity_value": payload.quantity_value,
        "quantity_unit": payload.quantity_unit,
        "quantity_source": payload.quantity_source,
        "transaction_at": payload.transaction_at,
        "metadata_json": payload.metadata,
        "source_record_hash": source_hash,
    }
    if item is None:
        db.add(
            DataFuelRecord(
                tenant_id=principal.tenant_id,
                external_fuel_record_id=payload.external_fuel_record_id,
                **values,
            )
        )
    elif item.source_record_hash != source_hash:
        for field, value in values.items():
            setattr(item, field, value)


async def upsert_payload(
    db: AsyncSession,
    principal: CurrentPrincipal,
    payload: DataPayloadPayload,
) -> None:
    organisation_id = await _organisation_id(
        db,
        principal.tenant_id,
        payload.external_customer_id,
    )
    journey_id = await _linked_id(
        db,
        DataJourney,
        principal.tenant_id,
        DataJourney.external_journey_id,
        payload.external_journey_id,
    )
    shipment_id = await _linked_id(
        db,
        DataShipment,
        principal.tenant_id,
        DataShipment.external_shipment_id,
        payload.external_shipment_id,
    )
    source_hash = canonical_json_sha256(payload.model_dump(mode="json"))
    item = await db.scalar(
        select(DataPayloadRecord).where(
            DataPayloadRecord.tenant_id == principal.tenant_id,
            DataPayloadRecord.external_payload_record_id
            == payload.external_payload_record_id,
        )
    )
    values = {
        "organisation_id": organisation_id,
        "journey_id": journey_id,
        "shipment_id": shipment_id,
        "quantity_value": payload.quantity_value,
        "quantity_unit": payload.quantity_unit,
        "quantity_source": payload.quantity_source,
        "metadata_json": payload.metadata,
        "source_record_hash": source_hash,
    }
    if item is None:
        db.add(
            DataPayloadRecord(
                tenant_id=principal.tenant_id,
                external_payload_record_id=payload.external_payload_record_id,
                **values,
            )
        )
    elif item.source_record_hash != source_hash:
        for field, value in values.items():
            setattr(item, field, value)


async def upsert_operational_emission(
    db: AsyncSession,
    principal: CurrentPrincipal,
    payload: DataOperationalEmissionPayload,
) -> None:
    organisation_id = await _organisation_id(
        db,
        principal.tenant_id,
        payload.external_customer_id,
    )
    journey_id = await _linked_id(
        db,
        DataJourney,
        principal.tenant_id,
        DataJourney.external_journey_id,
        payload.external_journey_id,
    )
    shipment_id = await _linked_id(
        db,
        DataShipment,
        principal.tenant_id,
        DataShipment.external_shipment_id,
        payload.external_shipment_id,
    )
    vehicle_id = await _linked_id(
        db,
        DataVehicle,
        principal.tenant_id,
        DataVehicle.external_vehicle_id,
        payload.external_vehicle_id,
    )
    item = await db.scalar(
        select(DataOperationalEmission).where(
            DataOperationalEmission.tenant_id == principal.tenant_id,
            DataOperationalEmission.external_calculation_id
            == payload.external_calculation_id,
        )
    )
    values = {
        "organisation_id": organisation_id,
        "journey_id": journey_id,
        "shipment_id": shipment_id,
        "vehicle_id": vehicle_id,
        "suggested_scope": payload.suggested_scope,
        "suggested_scope_3_category": payload.suggested_scope_3_category,
        "classification_reason": payload.classification_reason,
        "methodology_version": payload.methodology_version,
        "external_activity_key": payload.external_activity_key,
        "method_identifier": payload.method_identifier,
        "calculation_software_version": payload.calculation_software_version,
        "reporting_period_start": payload.reporting_period_start,
        "reporting_period_end": payload.reporting_period_end,
        "uncertainty_percentage": payload.uncertainty_percentage,
        "comparison_inputs_json": payload.comparison_inputs,
        "total_kg_co2e": payload.total_kg_co2e,
        "co2_kg": payload.co2_kg,
        "ch4_kg_co2e": payload.ch4_kg_co2e,
        "n2o_kg_co2e": payload.n2o_kg_co2e,
        "data_quality_level": payload.data_quality_level,
        "data_quality_score": payload.data_quality_score,
        "calculated_at": payload.calculated_at,
        "source_record_version": payload.source_record_version,
        "source_record_hash": payload.source_hash,
        "lineage_json": payload.lineage,
        "metadata_json": payload.metadata,
    }
    if item is None:
        db.add(
            DataOperationalEmission(
                tenant_id=principal.tenant_id,
                external_calculation_id=payload.external_calculation_id,
                classification_status=DataClassificationStatus.SUGGESTED,
                **values,
            )
        )
    elif item.source_record_hash == payload.source_hash:
        return
    else:
        for field, value in values.items():
            setattr(item, field, value)
        item.classification_status = DataClassificationStatus.REVIEW_REQUIRED


async def get_batch(
    db: AsyncSession,
    tenant_id: UUID,
    batch_id: UUID,
) -> DataImportBatch | None:
    return await db.scalar(
        select(DataImportBatch).where(
            DataImportBatch.id == batch_id,
            DataImportBatch.tenant_id == tenant_id,
        )
    )


async def list_batch_errors(
    db: AsyncSession,
    tenant_id: UUID,
    batch_id: UUID,
) -> list[DataImportError]:
    batch = await get_batch(db, tenant_id, batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="Import batch not found.")
    return list(
        (
            await db.scalars(
                select(DataImportError)
                .where(DataImportError.batch_id == batch_id)
                .order_by(DataImportError.record_index)
            )
        ).all()
    )


async def confirm_operational_emission(
    db: AsyncSession,
    principal: CurrentPrincipal,
    emission_id: UUID,
    payload: DataClassificationConfirmRequest,
) -> DataOperationalEmission:
    emission = await db.scalar(
        select(DataOperationalEmission).where(
            DataOperationalEmission.id == emission_id,
            DataOperationalEmission.tenant_id == principal.tenant_id,
        )
    )
    if emission is None:
        raise HTTPException(
            status_code=404,
            detail="DATa operational-emission record not found.",
        )

    if payload.activity_id is not None:
        activity = await db.scalar(
            select(ActivityRecord).where(
                ActivityRecord.id == payload.activity_id,
                ActivityRecord.tenant_id == principal.tenant_id,
            )
        )
        if activity is None:
            raise HTTPException(status_code=404, detail="Activity not found.")

    emission.activity_id = payload.activity_id
    emission.confirmed_scope = payload.confirmed_scope
    emission.confirmed_scope_3_category = payload.confirmed_scope_3_category
    emission.classification_status = payload.classification_status

    await record_audit_event(
        db,
        principal,
        action="data.operational_emission.classified",
        entity_type="data_operational_emission",
        entity_id=emission.id,
        event_data={
            "activity_id": str(payload.activity_id) if payload.activity_id else None,
            "confirmed_scope": payload.confirmed_scope,
            "confirmed_scope_3_category": payload.confirmed_scope_3_category,
            "classification_status": payload.classification_status.value,
        },
    )
    await db.commit()
    await db.refresh(emission)
    return emission


async def reconciliation_counts(
    db: AsyncSession,
    tenant_id: UUID,
) -> dict[str, int]:
    async def count(model: type[Any], *conditions: Any) -> int:
        query = select(func.count()).select_from(model).where(
            model.tenant_id == tenant_id,
            *conditions,
        )
        return int((await db.scalar(query)) or 0)

    return {
        "mappings": await count(DataOrganisationMapping),
        "vehicles": await count(DataVehicle),
        "shipments": await count(DataShipment),
        "journeys": await count(DataJourney),
        "fuel_records": await count(DataFuelRecord),
        "payload_records": await count(DataPayloadRecord),
        "operational_emissions": await count(DataOperationalEmission),
        "unclassified_operational_emissions": await count(
            DataOperationalEmission,
            DataOperationalEmission.classification_status
            != DataClassificationStatus.CONFIRMED,
        ),
        "linked_activities": await count(
            DataOperationalEmission,
            DataOperationalEmission.activity_id.is_not(None),
        ),
    }
