from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import (
    CurrentPrincipal,
    get_current_principal,
    require_roles,
)
from app.db.session import get_db
from app.schemas.inventory_governance import (
    ApprovalDecision,
    ApprovalRequestCreate,
    AuditReportResponse,
    InventoryApprovalResponse,
    InventoryLockRequest,
    InventoryLockResponse,
    InventoryRestatementResponse,
    ReportGenerateRequest,
    RestatementDecision,
    RestatementRequestCreate,
)
from app.services.inventory_governance import (
    complete_restatement,
    create_approval_request,
    decide_approval,
    decide_restatement,
    generate_audit_report,
    get_approval,
    get_audit_report,
    get_restatement,
    lock_inventory,
    request_restatement,
    start_approval_review,
)

router = APIRouter()
submitter = Depends(
    require_roles("tenant_admin", "sustainability_manager")
)
approver = Depends(
    require_roles("tenant_admin", "inventory_approver")
)


@router.post(
    "/inventories/{inventory_id}/approval-requests",
    response_model=InventoryApprovalResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[submitter],
)
async def request_approval(
    inventory_id: UUID,
    payload: ApprovalRequestCreate,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> InventoryApprovalResponse:
    approval = await create_approval_request(
        db,
        principal,
        inventory_id,
        payload.calculation_run_id,
    )
    return InventoryApprovalResponse.model_validate(approval)


@router.post(
    "/inventory-approvals/{approval_id}/start-review",
    response_model=InventoryApprovalResponse,
    dependencies=[approver],
)
async def start_review(
    approval_id: UUID,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> InventoryApprovalResponse:
    approval = await start_approval_review(db, principal, approval_id)
    return InventoryApprovalResponse.model_validate(approval)


@router.post(
    "/inventory-approvals/{approval_id}/decision",
    response_model=InventoryApprovalResponse,
    dependencies=[approver],
)
async def decide(
    approval_id: UUID,
    payload: ApprovalDecision,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> InventoryApprovalResponse:
    approval = await decide_approval(
        db,
        principal,
        approval_id,
        payload,
    )
    return InventoryApprovalResponse.model_validate(approval)


@router.get(
    "/inventory-approvals/{approval_id}",
    response_model=InventoryApprovalResponse,
)
async def get_approval_request(
    approval_id: UUID,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> InventoryApprovalResponse:
    approval = await get_approval(db, principal.tenant_id, approval_id)
    if approval is None:
        raise HTTPException(status_code=404, detail="Approval request not found.")
    return InventoryApprovalResponse.model_validate(approval)


@router.post(
    "/inventories/{inventory_id}/lock",
    response_model=InventoryLockResponse,
    dependencies=[approver],
)
async def lock(
    inventory_id: UUID,
    payload: InventoryLockRequest,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> InventoryLockResponse:
    lock_record = await lock_inventory(
        db,
        principal,
        inventory_id,
        payload.lock_reason,
    )
    return InventoryLockResponse.model_validate(lock_record)


@router.post(
    "/inventories/{inventory_id}/restatements",
    response_model=InventoryRestatementResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[submitter],
)
async def create_restatement(
    inventory_id: UUID,
    payload: RestatementRequestCreate,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> InventoryRestatementResponse:
    restatement = await request_restatement(
        db,
        principal,
        inventory_id,
        payload,
    )
    return InventoryRestatementResponse.model_validate(restatement)


@router.post(
    "/inventory-restatements/{restatement_id}/decision",
    response_model=InventoryRestatementResponse,
    dependencies=[approver],
)
async def decide_restatement_request(
    restatement_id: UUID,
    payload: RestatementDecision,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> InventoryRestatementResponse:
    restatement = await decide_restatement(
        db,
        principal,
        restatement_id,
        payload,
    )
    return InventoryRestatementResponse.model_validate(restatement)


@router.post(
    "/inventory-restatements/{restatement_id}/complete",
    response_model=InventoryRestatementResponse,
    dependencies=[approver],
)
async def complete_restatement_request(
    restatement_id: UUID,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> InventoryRestatementResponse:
    restatement = await complete_restatement(
        db,
        principal,
        restatement_id,
    )
    return InventoryRestatementResponse.model_validate(restatement)


@router.get(
    "/inventory-restatements/{restatement_id}",
    response_model=InventoryRestatementResponse,
)
async def get_restatement_request(
    restatement_id: UUID,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> InventoryRestatementResponse:
    restatement = await get_restatement(
        db,
        principal.tenant_id,
        restatement_id,
    )
    if restatement is None:
        raise HTTPException(status_code=404, detail="Restatement not found.")
    return InventoryRestatementResponse.model_validate(restatement)


@router.post(
    "/inventories/{inventory_id}/audit-reports",
    response_model=AuditReportResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[approver],
)
async def generate_report(
    inventory_id: UUID,
    payload: ReportGenerateRequest,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> AuditReportResponse:
    report = await generate_audit_report(
        db,
        principal,
        inventory_id,
        finalize=payload.finalize,
        scope_2_headline_basis=payload.scope_2_headline_basis,
    )
    return AuditReportResponse.model_validate(report)


@router.get(
    "/audit-reports/{report_id}",
    response_model=AuditReportResponse,
)
async def get_report(
    report_id: UUID,
    principal: CurrentPrincipal = Depends(get_current_principal),
    db: AsyncSession = Depends(get_db),
) -> AuditReportResponse:
    report = await get_audit_report(
        db,
        principal.tenant_id,
        report_id,
    )
    if report is None:
        raise HTTPException(status_code=404, detail="Audit report not found.")
    return AuditReportResponse.model_validate(report)
