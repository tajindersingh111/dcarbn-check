from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentPrincipal, get_current_principal, require_roles
from app.db.session import get_db
from app.integrations.data.accounting_scope3 import (
    accounting_scope3_template,
    normalise_scope3_accounting_result,
)
from app.models.data_integration import DataRecordType
from app.schemas.data_integration import (
    DataAccountingConnectionCreate,
    DataAccountingConnectionResponse,
    DataAccountingScope3Payload,
    DataAccountingScope3TemplateResponse,
    DataAccountingSyncCreate,
    DataAccountingSyncResponse,
    DataBatchRequest,
    DataClassificationConfirmRequest,
    DataFuelPayload,
    DataImportBatchResponse,
    DataImportErrorResponse,
    DataJourneyPayload,
    DataOperationalEmissionPayload,
    DataOperationalEmissionResponse,
    DataOrganisationMappingCreate,
    DataOrganisationMappingResponse,
    DataPayloadPayload,
    DataReconciliationResponse,
    DataShipmentPayload,
    DataVehiclePayload,
)
from app.services.accounting_connections import (
    create_accounting_sync,
    list_accounting_connections,
    upsert_accounting_connection,
)
from app.services.data_integration import (
    confirm_operational_emission,
    create_mapping,
    get_batch,
    list_batch_errors,
    process_batch,
    reconciliation_counts,
    upsert_fuel,
    upsert_journey,
    upsert_operational_emission,
    upsert_payload,
    upsert_shipment,
    upsert_vehicle,
)

router = APIRouter(prefix="/integrations/data")
integration_writer = Depends(
    require_roles("platform_admin", "tenant_admin", "integration_client")
)
reviewer = Depends(
    require_roles("tenant_admin", "sustainability_manager", "data_reviewer")
)


@router.post(
    "/organisation-mappings",
    response_model=DataOrganisationMappingResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[integration_writer],
)
async def upsert_mapping(
    payload: DataOrganisationMappingCreate,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> DataOrganisationMappingResponse:
    mapping = await create_mapping(db, principal, payload)
    return DataOrganisationMappingResponse.model_validate(mapping)


@router.post(
    "/accounting/connections",
    response_model=DataAccountingConnectionResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[integration_writer],
)
async def upsert_connection(
    payload: DataAccountingConnectionCreate,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> DataAccountingConnectionResponse:
    connection = await upsert_accounting_connection(
        db,
        principal,
        payload,
    )
    return DataAccountingConnectionResponse.model_validate(connection)


@router.get(
    "/accounting/connections",
    response_model=list[DataAccountingConnectionResponse],
)
async def get_connections(
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> list[DataAccountingConnectionResponse]:
    connections = await list_accounting_connections(db, principal.tenant_id)
    return [
        DataAccountingConnectionResponse.model_validate(item)
        for item in connections
    ]


@router.post(
    "/accounting/connections/{connection_id}/syncs",
    response_model=DataAccountingSyncResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[integration_writer],
)
async def queue_connection_sync(
    connection_id: UUID,
    payload: DataAccountingSyncCreate,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> DataAccountingSyncResponse:
    job = await create_accounting_sync(
        db,
        principal,
        connection_id,
        payload,
    )
    return DataAccountingSyncResponse.model_validate(job)


@router.get(
    "/accounting/scope-3/template",
    response_model=DataAccountingScope3TemplateResponse,
)
async def get_accounting_scope3_template() -> DataAccountingScope3TemplateResponse:
    return accounting_scope3_template()


@router.post(
    "/accounting/scope-3/batch",
    response_model=DataImportBatchResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[integration_writer],
)
async def import_accounting_scope3_results(
    payload: DataBatchRequest[DataAccountingScope3Payload],
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> DataImportBatchResponse:
    normalised = DataBatchRequest[DataOperationalEmissionPayload](
        schema_version=payload.schema_version,
        idempotency_key=payload.idempotency_key,
        records=[
            normalise_scope3_accounting_result(item)
            for item in payload.records
        ],
    )
    batch = await process_batch(
        db,
        principal,
        record_type=DataRecordType.OPERATIONAL_EMISSION,
        request=normalised,
        handler=upsert_operational_emission,
        external_id_getter=lambda item: item.external_calculation_id,
    )
    return DataImportBatchResponse.model_validate(batch)


@router.post(
    "/vehicles/batch",
    response_model=DataImportBatchResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[integration_writer],
)
async def import_vehicles(
    payload: DataBatchRequest[DataVehiclePayload],
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> DataImportBatchResponse:
    batch = await process_batch(
        db,
        principal,
        record_type=DataRecordType.VEHICLE,
        request=payload,
        handler=upsert_vehicle,
        external_id_getter=lambda item: item.external_vehicle_id,
    )
    return DataImportBatchResponse.model_validate(batch)


@router.post(
    "/shipments/batch",
    response_model=DataImportBatchResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[integration_writer],
)
async def import_shipments(
    payload: DataBatchRequest[DataShipmentPayload],
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> DataImportBatchResponse:
    batch = await process_batch(
        db,
        principal,
        record_type=DataRecordType.SHIPMENT,
        request=payload,
        handler=upsert_shipment,
        external_id_getter=lambda item: item.external_shipment_id,
    )
    return DataImportBatchResponse.model_validate(batch)


@router.post(
    "/journeys/batch",
    response_model=DataImportBatchResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[integration_writer],
)
async def import_journeys(
    payload: DataBatchRequest[DataJourneyPayload],
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> DataImportBatchResponse:
    batch = await process_batch(
        db,
        principal,
        record_type=DataRecordType.JOURNEY,
        request=payload,
        handler=upsert_journey,
        external_id_getter=lambda item: item.external_journey_id,
    )
    return DataImportBatchResponse.model_validate(batch)


@router.post(
    "/fuel/batch",
    response_model=DataImportBatchResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[integration_writer],
)
async def import_fuel(
    payload: DataBatchRequest[DataFuelPayload],
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> DataImportBatchResponse:
    batch = await process_batch(
        db,
        principal,
        record_type=DataRecordType.FUEL,
        request=payload,
        handler=upsert_fuel,
        external_id_getter=lambda item: item.external_fuel_record_id,
    )
    return DataImportBatchResponse.model_validate(batch)


@router.post(
    "/payloads/batch",
    response_model=DataImportBatchResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[integration_writer],
)
async def import_payloads(
    payload: DataBatchRequest[DataPayloadPayload],
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> DataImportBatchResponse:
    batch = await process_batch(
        db,
        principal,
        record_type=DataRecordType.PAYLOAD,
        request=payload,
        handler=upsert_payload,
        external_id_getter=lambda item: item.external_payload_record_id,
    )
    return DataImportBatchResponse.model_validate(batch)


@router.post(
    "/operational-emissions/batch",
    response_model=DataImportBatchResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[integration_writer],
)
async def import_operational_emissions(
    payload: DataBatchRequest[DataOperationalEmissionPayload],
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> DataImportBatchResponse:
    batch = await process_batch(
        db,
        principal,
        record_type=DataRecordType.OPERATIONAL_EMISSION,
        request=payload,
        handler=upsert_operational_emission,
        external_id_getter=lambda item: item.external_calculation_id,
    )
    return DataImportBatchResponse.model_validate(batch)


@router.get(
    "/imports/{batch_id}",
    response_model=DataImportBatchResponse,
)
async def get_import(
    batch_id: UUID,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> DataImportBatchResponse:
    batch = await get_batch(db, principal.tenant_id, batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="Import batch not found.")
    return DataImportBatchResponse.model_validate(batch)


@router.get(
    "/imports/{batch_id}/errors",
    response_model=list[DataImportErrorResponse],
)
async def get_import_errors(
    batch_id: UUID,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> list[DataImportErrorResponse]:
    errors = await list_batch_errors(db, principal.tenant_id, batch_id)
    return [DataImportErrorResponse.model_validate(item) for item in errors]


@router.post(
    "/operational-emissions/{emission_id}/classification",
    response_model=DataOperationalEmissionResponse,
    dependencies=[reviewer],
)
async def classify_operational_emission(
    emission_id: UUID,
    payload: DataClassificationConfirmRequest,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> DataOperationalEmissionResponse:
    item = await confirm_operational_emission(
        db,
        principal,
        emission_id,
        payload,
    )
    return DataOperationalEmissionResponse.model_validate(item)


@router.get(
    "/reconciliation",
    response_model=DataReconciliationResponse,
)
async def reconcile(
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> DataReconciliationResponse:
    counts = await reconciliation_counts(db, principal.tenant_id)
    return DataReconciliationResponse(
        tenant_id=principal.tenant_id,
        **counts,
    )
