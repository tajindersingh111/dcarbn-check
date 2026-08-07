export type StatusTone = "success" | "info" | "warning" | "neutral" | "danger";

export interface ListResponse<T> {
  items: T[];
  total: number;
  limit?: number;
  offset?: number;
}

export interface Organisation {
  id: string;
  tenant_id: string;
  name: string;
  legal_name: string | null;
  registration_number: string | null;
  country_code: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ReportingPeriod {
  id: string;
  tenant_id: string;
  organisation_id: string;
  name: string;
  start_date: string;
  end_date: string;
  is_base_year: boolean;
  created_at: string;
  updated_at: string;
}

export interface Inventory {
  id: string;
  tenant_id: string;
  reporting_period_id: string;
  organisation_id: string;
  organisation_name: string;
  reporting_period_name: string;
  reporting_period_start: string;
  reporting_period_end: string;
  name: string;
  status: string;
  version: number;
  locked_at: string | null;
  approved_at: string | null;
  latest_calculation_run_id: string | null;
  total_kg_co2e: string | null;
  scope_1_kg_co2e: string | null;
  scope_2_kg_co2e: string | null;
  scope_3_kg_co2e: string | null;
  created_at: string;
  updated_at: string;
}

export interface DashboardSummary {
  total_kg_co2e: string;
  total_t_co2e: string;
  inventory_count: number;
  locked_inventory_count: number;
  open_data_review_count: number;
  open_approval_count: number;
  organisation_count: number;
}

export interface DataReviewRecord {
  id: string;
  tenant_id: string;
  operational_emission_id: string;
  inventory_id: string | null;
  status: string;
  reviewer_id: string | null;
  review_started_at: string | null;
  reviewed_at: string | null;
  converted_at: string | null;
  reviewer_comment: string | null;
  rejection_reason: string | null;
  conversion_failure: string | null;
  calculation_run_id: string | null;
  calculation_result_id: string | null;
  activity_id: string | null;
  review_snapshot: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface DataReviewQueueItem {
  review: DataReviewRecord;
  external_calculation_id: string;
  external_customer_id: string | null;
  organisation_id: string;
  suggested_scope: string | null;
  suggested_scope_3_category: number | null;
  confirmed_scope: string | null;
  confirmed_scope_3_category: number | null;
  methodology_version: string;
  total_kg_co2e: string;
  data_quality_level: string | null;
  data_quality_score: number | null;
  calculated_at: string;
}

export interface ApprovalQueueItem {
  id: string;
  inventory_id: string;
  inventory_name: string;
  calculation_run_id: string;
  version: number;
  status: string;
  requested_by: string;
  requested_at: string;
  reviewer_id: string | null;
  evidence_complete: boolean;
  boundary_complete: boolean;
  factor_lineage_complete: boolean;
  calculation_complete: boolean;
}

export interface AuditReportListItem {
  id: string;
  inventory_id: string;
  inventory_name: string;
  version: number;
  status: string;
  generated_by: string;
  generated_at: string;
  finalized_at: string | null;
  report_sha256: string;
  total_kg_co2e: string;
  total_t_co2e: string;
}

export interface AuditReport {
  id: string;
  tenant_id: string;
  inventory_id: string;
  calculation_run_id: string;
  approval_id: string;
  version: number;
  status: string;
  generated_by: string;
  generated_at: string;
  finalized_by: string | null;
  finalized_at: string | null;
  report_sha256: string;
  report_payload: Record<string, unknown>;
  superseded_by_report_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface ActivityFormValues {
  organisationId: string;
  inventoryId: string;
  calculationMethodId: string;
  activityType: string;
  scope: string;
  scope2Method: string;
  scope3Category: string;
  activityDate: string;
  description: string;
  activityValue: string;
  openingStockKg: string;
  purchasesKg: string;
  closingStockKg: string;
  recoveredKg: string;
  scope2InstrumentType: string;
  scope2SupplierOrIssuer: string;
  scope2InstrumentReference: string;
  scope2FactorSource: string;
  scope2FactorValue: string;
  scope2ValidFrom: string;
  scope2ValidTo: string;
  scope2QualityCriteriaAttested: boolean;
  supplierName: string;
  supplierMethodology: string;
  supplierMethodologyVersion: string;
  supplierReportingPeriod: string;
  supplierBoundaryDescription: string;
  supplierAssuranceStatus: string;
  activityUnit: string;
  geographyCode: string;
  factorLevel1: string;
  factorLevel2: string;
  factorLevel3: string;
  factorLevel4: string;
  factorColumnText: string;
  lifecycleBoundary: string;
  evidenceReference: string;
  sourceRecordId: string;
}

export interface DataComparisonResultView {
  result_id: string;
  allocated_kg_co2e: string;
  methodology_version: string;
  calculation_method: string;
  factor_id: string | null;
  factor_value: string | null;
  warnings: string[];
  lineage: Record<string, unknown>;
}

export interface DataCalculationComparisonDetail {
  id: string;
  tenant_id: string;
  operational_emission_id: string;
  comparison_group_key: string;
  dcarbn_result_id: string | null;
  government_result_id: string | null;
  status: "pending" | "ready" | "unavailable";
  reporting_basis: "dcarbn_operational" | "uk_government";
  basis_reason: string | null;
  comparison_unavailable_reason: string | null;
  absolute_delta_kg_co2e: string | null;
  percentage_delta: string | null;
  confirmed_scope: string | null;
  confirmed_scope_3_category: number | null;
  data_quality_level: string | null;
  data_quality_score: number | null;
  uncertainty_percentage: string | null;
  dcarbn_result: DataComparisonResultView | null;
  government_result: DataComparisonResultView | null;
}
