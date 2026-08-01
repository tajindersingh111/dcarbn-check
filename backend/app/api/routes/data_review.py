from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import (
    CurrentPrincipal,
    get_current_principal,
    require_roles,
)
from app.db.session import get_db
from app.models.data_integration import DataOrganisationMapping
from app.models.data_review import DataReviewStatus
from app.schemas.data_review import (
    DataConversionResponse,
    DataReviewDecisionRequest,
    DataReviewQueueItem,
    DataReviewQueueResponse,
    DataReviewResponse,
    DataReviewStartRequest,
)
from app.services.data_review import (
    convert_review,
    decide_review,
    ensure_pending_reviews_for_confirmed_emissions,
    get_or_create_review,
    get_review,
    list_reviews,
    start_review,
)

router = APIRouter(prefix="/integrations/data/reviews")
reviewer = Depends(
    require_roles(
        "tenant_admin",
        "sustainability_manager",
        "data_reviewer",
        "inventory_approver",
    )
)


@router.post(
    "/sync",
    response_model=dict[str, int],
    dependencies=[reviewer],
)
async def sync_queue(
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> dict[str, int]:
    created = await ensure_pending_reviews_for_confirmed_emissions(
        db,
        principal,
    )
    return {"created": created}


@router.get("", response_model=DataReviewQueueResponse)
async def queue(
    status_filter: DataReviewStatus | None = Query(
        default=None,
        alias="status",
    ),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> DataReviewQueueResponse:
    items, total = await list_reviews(
        db,
        principal.tenant_id,
        status_filter=status_filter,
        limit=limit,
        offset=offset,
    )

    queue_items: list[DataReviewQueueItem] = []
    for review, emission in items:
        external_customer_id = await db.scalar(
            __import__("sqlalchemy").select(
                DataOrganisationMapping.external_customer_id
            ).where(
                DataOrganisationMapping.tenant_id == principal.tenant_id,
                DataOrganisationMapping.organisation_id
                == emission.organisation_id,
                DataOrganisationMapping.is_active.is_(True),
            )
        )
        queue_items.append(
            DataReviewQueueItem(
                review=DataReviewResponse.model_validate(review),
                external_calculation_id=emission.external_calculation_id,
                external_customer_id=external_customer_id,
                organisation_id=emission.organisation_id,
                suggested_scope=emission.suggested_scope,
                suggested_scope_3_category=(
                    emission.suggested_scope_3_category
                ),
                confirmed_scope=emission.confirmed_scope,
                confirmed_scope_3_category=(
                    emission.confirmed_scope_3_category
                ),
                methodology_version=emission.methodology_version,
                total_kg_co2e=str(emission.total_kg_co2e),
                data_quality_level=emission.data_quality_level,
                data_quality_score=emission.data_quality_score,
                calculated_at=emission.calculated_at,
            )
        )

    return DataReviewQueueResponse(
        items=queue_items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{review_id}", response_model=DataReviewResponse)
async def get_one(
    review_id: UUID,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> DataReviewResponse:
    review = await get_review(db, principal.tenant_id, review_id)
    if review is None:
        raise HTTPException(status_code=404, detail="Review not found.")
    return DataReviewResponse.model_validate(review)


@router.post(
    "/operational-emissions/{emission_id}",
    response_model=DataReviewResponse,
    dependencies=[reviewer],
)
async def create_review(
    emission_id: UUID,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> DataReviewResponse:
    review = await get_or_create_review(db, principal, emission_id)
    return DataReviewResponse.model_validate(review)


@router.post(
    "/{review_id}/start",
    response_model=DataReviewResponse,
    dependencies=[reviewer],
)
async def begin_review(
    review_id: UUID,
    payload: DataReviewStartRequest,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> DataReviewResponse:
    review = await get_review(db, principal.tenant_id, review_id)
    if review is None:
        raise HTTPException(status_code=404, detail="Review not found.")
    updated = await start_review(
        db,
        principal,
        review.operational_emission_id,
        payload,
    )
    return DataReviewResponse.model_validate(updated)


@router.post(
    "/{review_id}/decision",
    response_model=DataReviewResponse,
    dependencies=[reviewer],
)
async def decide(
    review_id: UUID,
    payload: DataReviewDecisionRequest,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> DataReviewResponse:
    review = await decide_review(
        db,
        principal,
        review_id,
        payload,
    )
    return DataReviewResponse.model_validate(review)


@router.post(
    "/{review_id}/convert",
    response_model=DataConversionResponse,
    dependencies=[reviewer],
)
async def convert(
    review_id: UUID,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> DataConversionResponse:
    review = await convert_review(
        db,
        principal,
        review_id,
    )
    if (
        review.activity_id is None
        or review.calculation_run_id is None
        or review.calculation_result_id is None
    ):
        raise HTTPException(
            status_code=500,
            detail="Converted review is missing calculation references.",
        )

    return DataConversionResponse(
        review=DataReviewResponse.model_validate(review),
        activity_id=review.activity_id,
        calculation_run_id=review.calculation_run_id,
        calculation_result_id=review.calculation_result_id,
    )
