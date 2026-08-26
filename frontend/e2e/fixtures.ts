import type { Page } from "@playwright/test";

const organisation = {
  id: "11111111-1111-1111-1111-111111111111",
  tenant_id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
  name: "Northstar Logistics Ltd",
  legal_name: "Northstar Logistics Limited",
  registration_number: "01234567",
  country_code: "GB",
  is_active: true,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z"
};

const inventory = {
  id: "22222222-2222-2222-2222-222222222222",
  tenant_id: organisation.tenant_id,
  reporting_period_id: "33333333-3333-3333-3333-333333333333",
  organisation_id: organisation.id,
  organisation_name: organisation.name,
  reporting_period_name: "Calendar year 2026",
  reporting_period_start: "2026-01-01",
  reporting_period_end: "2026-12-31",
  name: "Northstar Corporate Inventory 2026",
  status: "review_required",
  version: 1,
  locked_at: null,
  approved_at: null,
  latest_calculation_run_id: "44444444-4444-4444-4444-444444444444",
  scope_2_headline_basis: "location_based",
  total_kg_co2e: "12846280",
  scope_1_kg_co2e: "3540440",
  scope_2_kg_co2e: "1286020",
  scope_2_location_based_kg_co2e: "1286020",
  scope_2_market_based_kg_co2e: "1100000",
  scope_3_kg_co2e: "8019820",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z"
};

export async function installApiFixtures(page: Page): Promise<void> {
  await page.addInitScript(() => {
    localStorage.setItem("dcarbn.access_token", "e2e-token");
  });

  await page.route("**/api/v1/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname.replace("/api/v1", "");
    const method = request.method();

    if (path === "/auth/me") {
      return route.fulfill({ json: {
        id: "e2e-user",
        email: "alex@example.com",
        full_name: "Alex Morgan",
        tenant_id: organisation.tenant_id,
        tenant_name: organisation.name,
        tenant_slug: "northstar-logistics",
        roles: ["tenant_admin", "methodology_manager"],
        is_platform_admin: false
      }});
    }
    if (path === "/methodologies" && method === "GET") {
      return route.fulfill({ json: { items: [], total: 0 } });
    }
    if (path === "/methodologies" && method === "POST") {
      const payload = request.postDataJSON() as Record<string, unknown>;
      return route.fulfill({ status: 201, json: {
        ...payload,
        id: "methodology-1",
        version: 1,
        status: "draft",
        input_schema: { inputs: payload.inputs },
        created_by: "e2e-user",
        submitted_at: null,
        reviewed_by: null,
        reviewed_at: null,
        approved_by: null,
        approved_at: null,
        activated_by: null,
        activated_at: null,
        retired_at: null,
        supersedes_version_id: null,
        created_at: "2026-08-05T00:00:00Z",
        updated_at: "2026-08-05T00:00:00Z"
      }});
    }
    if (path.startsWith("/methodologies/") && method === "POST") {
      return route.fulfill({ json: { status: "in_review" } });
    }
    if (path === "/dashboard") {
      const headlineBasis = url.searchParams.get("scope_2_headline_basis") ?? "location_based";
      return route.fulfill({ json: {
        scope_2_headline_basis: headlineBasis,
        scope_2_location_based_kg_co2e: "1286020",
        scope_2_market_based_kg_co2e: "1100000",
        total_kg_co2e: headlineBasis === "location_based" ? "12846280" : "12660260",
        total_t_co2e: headlineBasis === "location_based" ? "12846.28" : "12660.26",
        inventory_count: 1,
        locked_inventory_count: 0,
        open_data_review_count: 1,
        open_approval_count: 1,
        organisation_count: 1
      }});
    }
    if (path.startsWith("/organisations") && method === "GET") {
      return route.fulfill({ json: { items: [organisation], total: 1, limit: 200, offset: 0 }});
    }
    if (path === "/organisations" && method === "POST") {
      return route.fulfill({ status: 201, json: organisation });
    }
    if (path.startsWith("/inventories") && method === "GET" && !path.includes("calculation-runs") && !path.includes("scope-3-category-dispositions")) {
      const headlineBasis = url.searchParams.get("scope_2_headline_basis") ?? "location_based";
      const selectedInventory = {
        ...inventory,
        scope_2_headline_basis: headlineBasis,
        scope_2_kg_co2e: headlineBasis === "location_based" ? "1286020" : "1100000",
        total_kg_co2e: headlineBasis === "location_based" ? "12846280" : "12660260"
      };
      return route.fulfill({ json: { items: [selectedInventory], total: 1, limit: 200, offset: 0 }});
    }
    if (path === "/inventories" && method === "POST") {
      return route.fulfill({ status: 201, json: inventory });
    }
    if (path === "/reporting-periods" && method === "GET") {
      return route.fulfill({ json: { items: [{
        id: inventory.reporting_period_id,
        tenant_id: organisation.tenant_id,
        organisation_id: organisation.id,
        name: "Calendar year 2026",
        start_date: "2026-01-01",
        end_date: "2026-12-31",
        is_base_year: false,
        created_at: "2026-01-01T00:00:00Z",
        updated_at: "2026-01-01T00:00:00Z"
      }], total: 1 }});
    }
    if (path === "/reporting-periods" && method === "POST") {
      return route.fulfill({ status: 201, json: {} });
    }
    if (path.endsWith("/activities/batch") && method === "POST") {
      const payload = request.postDataJSON() as { items?: unknown[] };
      return route.fulfill({
        status: 201,
        json: { items: payload.items ?? [], total: payload.items?.length ?? 0 }
      });
    }
    if (path.endsWith("/activities") && method === "POST") {
      return route.fulfill({ status: 201, json: { id: "activity-1" } });
    }
    if (path === "/integrations/data/accounting/syncs" && method === "GET") {
      return route.fulfill({ json: { items: [{
        id: "99999999-9999-9999-9999-999999999999",
        tenant_id: organisation.tenant_id,
        connection_id: "77777777-7777-7777-7777-777777777777",
        sync_identity: "3768f943c6b5d642bd96dcdf346fb9673efc41073f80fd4129db3d5aacc9204a",
        cursor_before: "cursor-11",
        cursor_after: "cursor-12",
        requested_from: "2026-01-01T00:00:00Z",
        requested_to: "2026-06-30T23:59:59Z",
        status: "completed",
        records_received: 148,
        records_imported: 143,
        records_rejected: 5,
        requested_by: "e2e-user",
        started_at: "2026-08-07T07:58:00Z",
        completed_at: "2026-08-07T08:00:00Z",
        failure_code: null,
        failure_message: null,
        diagnostics_json: { mapping_profile_version: "2026.1" },
        created_at: "2026-08-07T07:58:00Z",
        updated_at: "2026-08-07T08:00:00Z"
      }], next_cursor: null }});
    }
    if (path === "/integrations/data/accounting/connections" && method === "GET") {
      return route.fulfill({ json: [{
        id: "77777777-7777-7777-7777-777777777777",
        tenant_id: organisation.tenant_id,
        organisation_id: organisation.id,
        external_customer_id: "customer-1042",
        provider: "xero",
        external_company_id: "northstar-xero",
        display_name: "Xero · UK entity",
        status: "active",
        mapping_profile_version: "2026.1",
        mapping_json: {},
        last_cursor: "cursor-12",
        last_synced_at: "2026-08-07T08:00:00Z",
        failure_code: null,
        failure_message: null,
        created_at: "2026-08-01T00:00:00Z",
        updated_at: "2026-08-07T08:00:00Z"
      }]});
    }
    if (path === "/integrations/data/accounting/connections" && method === "POST") {
      const payload = request.postDataJSON() as Record<string, unknown>;
      return route.fulfill({ status: 201, json: {
        ...payload,
        id: "88888888-8888-8888-8888-888888888888",
        tenant_id: organisation.tenant_id,
        status: "draft",
        last_synced_at: null,
        failure_code: null,
        failure_message: null,
        created_at: "2026-08-07T09:00:00Z",
        updated_at: "2026-08-07T09:00:00Z"
      }});
    }
    if (
      path === "/integrations/data/accounting/connections/77777777-7777-7777-7777-777777777777/syncs" &&
      method === "POST"
    ) {
      return route.fulfill({ status: 202, json: {
        id: "99999999-9999-9999-9999-999999999999",
        status: "queued"
      }});
    }
    if (
      path === "/integrations/data/accounting/scope-3/template" &&
      method === "GET"
    ) {
      return route.fulfill({ json: {
        schema_version: "1.0",
        supported_source_systems: ["csv", "quickbooks", "xero", "sage", "api"],
        required_columns: [
          "external_customer_id",
          "external_transaction_id",
          "source_system",
          "transaction_date",
          "supplier_name",
          "description",
          "scope_3_category",
          "reported_kg_co2e",
          "allocation_percentage",
          "supplier_methodology",
          "supplier_methodology_version",
          "supplier_reporting_period_start",
          "supplier_reporting_period_end",
          "supplier_result_calculated_at",
          "boundary_description",
          "assurance_status",
          "evidence_reference"
        ],
        optional_columns: [
          "source_account_code",
          "source_account_name",
          "currency_code",
          "net_amount",
          "source_document_reference",
          "source_record_version"
        ],
        governed_methods: {
          "1": "scope3.category1.supplier_specific.reported_kgco2e.ghgp.v1",
          "2": "scope3.category2.supplier_specific.reported_kgco2e.ghgp.v1",
          "8": "scope3.category8.supplier_specific.reported_kgco2e.ghgp.v1",
          "10": "scope3.category10.supplier_specific.reported_kgco2e.ghgp.v1",
          "11": "scope3.category11.supplier_specific.reported_kgco2e.ghgp.v1",
          "12": "scope3.category12.supplier_specific.reported_kgco2e.ghgp.v1",
          "13": "scope3.category13.supplier_specific.reported_kgco2e.ghgp.v1",
          "14": "scope3.category14.supplier_specific.reported_kgco2e.ghgp.v1",
          "15": "scope3.category15.supplier_specific.reported_kgco2e.ghgp.v1"
        }
      } });
    }
    if (
      path === "/integrations/data/accounting/scope-3/batch" &&
      method === "POST"
    ) {
      const payload = request.postDataJSON() as { records: unknown[] };
      return route.fulfill({ status: 202, json: {
        id: "import-batch-1",
        tenant_id: organisation.tenant_id,
        schema_version: "1.0",
        record_type: "operational_emission",
        idempotency_key: "customer-import",
        source_payload_sha256:
          "9f1d1c2fdbb70f6ea4f620f48ed9cfbff648901a205a4c524935730fcfaf4382",
        status: "completed",
        records_received: payload.records.length,
        records_imported: payload.records.length,
        records_rejected: 0,
        started_at: "2026-08-07T07:00:00Z",
        completed_at: "2026-08-07T07:00:01Z",
        requested_by: "e2e-user",
        failure_message: null
      } });
    }
    if (path === "/integrations/data/reviews") {
      return route.fulfill({ json: { items: [{
        review: {
          id: "review-1",
          tenant_id: organisation.tenant_id,
          operational_emission_id: "emission-1",
          inventory_id: inventory.id,
          status: "in_review",
          reviewer_id: "reviewer",
          review_started_at: "2026-08-01T00:00:00Z",
          reviewed_at: null,
          converted_at: null,
          reviewer_comment: null,
          rejection_reason: null,
          conversion_failure: null,
          calculation_run_id: null,
          calculation_result_id: null,
          activity_id: null,
          review_snapshot: {},
          created_at: "2026-08-01T00:00:00Z",
          updated_at: "2026-08-01T00:00:00Z"
        },
        external_calculation_id: "DATa-CALC-2026-0184",
        external_customer_id: "northstar",
        organisation_id: organisation.id,
        suggested_scope: "scope_3",
        suggested_scope_3_category: 4,
        confirmed_scope: "scope_3",
        confirmed_scope_3_category: 4,
        methodology_version: "DATa-2026.1",
        total_kg_co2e: "326.745",
        data_quality_level: "primary",
        data_quality_score: 92,
        calculated_at: "2026-08-01T00:00:00Z"
      }, {
        review: {
          id: "review-2",
          tenant_id: organisation.tenant_id,
          operational_emission_id: "emission-2",
          inventory_id: inventory.id,
          status: "converted",
          reviewer_id: "reviewer",
          review_started_at: "2026-08-01T00:00:00Z",
          reviewed_at: "2026-08-01T01:00:00Z",
          converted_at: "2026-08-01T02:00:00Z",
          reviewer_comment: "Approved for comparison",
          rejection_reason: null,
          conversion_failure: null,
          calculation_run_id: "dcarbn-run-2",
          calculation_result_id: "dcarbn-result-2",
          activity_id: "activity-2",
          review_snapshot: {},
          created_at: "2026-08-01T00:00:00Z",
          updated_at: "2026-08-01T02:00:00Z"
        },
        external_calculation_id: "DATa-CALC-2026-0199",
        external_customer_id: "northstar",
        organisation_id: organisation.id,
        suggested_scope: "scope_3",
        suggested_scope_3_category: 9,
        confirmed_scope: "scope_3",
        confirmed_scope_3_category: 9,
        methodology_version: "DATa-2026.1",
        total_kg_co2e: "410.5",
        data_quality_level: "primary",
        data_quality_score: 94,
        calculated_at: "2026-08-02T00:00:00Z"
      }], total: 2, limit: 200, offset: 0 }});
    }
    if (
      path ===
        "/integrations/data/comparisons/operational-emissions/emission-2" &&
      method === "GET"
    ) {
      return route.fulfill({ json: {
        id: "comparison-2",
        tenant_id: organisation.tenant_id,
        operational_emission_id: "emission-2",
        comparison_group_key: "dcarbn:route-199:2026-01-01:2026-12-31",
        dcarbn_result_id: "dcarbn-result-2",
        government_result_id: "government-result-2",
        status: "ready",
        reporting_basis: "dcarbn_operational",
        basis_reason: "DcarbN selected as the operational headline basis.",
        comparison_unavailable_reason: null,
        absolute_delta_kg_co2e: "26.17",
        percentage_delta: "6.81",
        confirmed_scope: "scope_3",
        confirmed_scope_3_category: 9,
        data_quality_level: "primary",
        data_quality_score: 94,
        uncertainty_percentage: "4.5",
        dcarbn_result: {
          result_id: "dcarbn-result-2",
          allocated_kg_co2e: "410.5",
          methodology_version: "DATa-2026.1",
          calculation_method: "external_operational_result",
          factor_id: null,
          factor_value: null,
          warnings: [],
          lineage: { route_reference: "route-199" }
        },
        government_result: {
          result_id: "government-result-2",
          allocated_kg_co2e: "384.33",
          methodology_version: "UK-Government-comparator-v1",
          calculation_method: "activity_factor",
          factor_id: "factor-2026-van",
          factor_value: "0.38433",
          warnings: ["comparison_only_not_included_in_inventory_totals"],
          lineage: {
            governed_method_id:
              "scope3.category9.average_diesel_van.tonne_km.uk_2026.v1"
          }
        }
      }});
    }
    if (path.startsWith("/integrations/data/reviews/") && method === "POST") {
      return route.fulfill({ json: { status: "approved" } });
    }
    if (path === "/inventory-approvals") {
      return route.fulfill({ json: { items: [{
        id: "approval-1",
        inventory_id: inventory.id,
        inventory_name: inventory.name,
        calculation_run_id: inventory.latest_calculation_run_id,
        version: 1,
        status: "in_review",
        requested_by: "Sam Green",
        requested_at: "2026-08-01T09:42:00Z",
        reviewer_id: "Alex Morgan",
        evidence_complete: true,
        boundary_complete: true,
        factor_lineage_complete: true,
        calculation_complete: true
      }], total: 1, limit: 200, offset: 0 }});
    }
    if (path.endsWith("/scope-3-category-dispositions") && method === "GET") {
      return route.fulfill({ json: { items: [], total: 0, complete: false, approved: false } });
    }
    if (path.endsWith("/scope-3-category-dispositions") && method === "PUT") {
      const payload = request.postDataJSON() as { items: Array<Record<string, unknown>> };
      return route.fulfill({ json: {
        items: payload.items.map((item, index) => ({
          ...item,
          id: `disposition-${index + 1}`,
          tenant_id: organisation.tenant_id,
          inventory_id: inventory.id,
          prepared_by: "e2e-user",
          prepared_at: "2026-08-05T00:00:00Z",
          approved_by: null,
          approved_at: null,
          created_at: "2026-08-05T00:00:00Z",
          updated_at: "2026-08-05T00:00:00Z"
        })),
        total: 15,
        complete: true,
        approved: false
      }});
    }
    if (path.endsWith("/scope-3-category-dispositions/approve") && method === "POST") {
      return route.fulfill({ json: { items: [], total: 15, complete: true, approved: true } });
    }
    if (path.endsWith(`/inventories/${inventory.id}/calculation-runs`) && method === "POST") {
      return route.fulfill({ status: 201, json: {
        id: inventory.latest_calculation_run_id,
        inventory_id: inventory.id,
        version: 2,
        status: "completed",
        activity_count: 1,
        result_count: 1,
        failed_count: 0,
        failure_message: null
      }});
    }
    if (path === `/calculation-runs/${inventory.latest_calculation_run_id}/summary` && method === "GET") {
      const headlineBasis = url.searchParams.get("scope_2_headline_basis") ?? "location_based";
      return route.fulfill({ json: {
        calculation_run_id: inventory.latest_calculation_run_id,
        inventory_id: inventory.id,
        scope_2_headline_basis: headlineBasis,
        scope_1_kg_co2e: "3540440",
        scope_2_location_based_kg_co2e: "1286020",
        scope_2_market_based_kg_co2e: "1100000",
        scope_3_kg_co2e: "8019820",
        total_kg_co2e: headlineBasis === "location_based" ? "12846280" : "12660260",
        total_t_co2e: headlineBasis === "location_based" ? "12846.28" : "12660.26",
        items: []
      }});
    }
    if (path.includes("/calculation-runs") && method === "GET") {
      return route.fulfill({ json: { items: [{
        id: inventory.latest_calculation_run_id,
        inventory_id: inventory.id,
        version: 1,
        status: "completed",
        completed_at: "2026-08-01T00:00:00Z",
        activity_count: 1,
        result_count: 1
      }], total: 1 }});
    }
    if ((path.startsWith("/inventory-approvals/") || path.endsWith("/approval-requests") || path.endsWith("/lock")) && method === "POST") {
      return route.fulfill({ json: { status: "approved" } });
    }
    if (path === "/audit-reports") {
      return route.fulfill({ json: { items: [{
        id: "report-1",
        inventory_id: inventory.id,
        inventory_name: inventory.name,
        version: 1,
        status: "final",
        generated_by: "Alex Morgan",
        generated_at: "2026-08-01T10:00:00Z",
        finalized_at: "2026-08-01T10:00:00Z",
        report_sha256: "785f16d75c3bcc2b50d6d38db743a131f6cf979194f8152163a9b90312498d0f",
        total_kg_co2e: "12846280",
        total_t_co2e: "12846.28"
      }], total: 1, limit: 200, offset: 0 }});
    }
    if (path === "/audit-reports/report-1") {
      return route.fulfill({ json: {
        id: "report-1",
        tenant_id: organisation.tenant_id,
        inventory_id: inventory.id,
        calculation_run_id: inventory.latest_calculation_run_id,
        approval_id: "approval-1",
        version: 1,
        status: "final",
        generated_by: "Alex Morgan",
        generated_at: "2026-08-01T10:00:00Z",
        finalized_by: "Alex Morgan",
        finalized_at: "2026-08-01T10:00:00Z",
        report_sha256: "hash",
        report_payload: {
          totals: { total_t_co2e: "12846.28" },
          assurance_readiness: {
            status: "assurance_ready",
            claim_wording: "Assurance-ready reporting pack",
            ready: true,
            checks: [{ code: "approved_boundary", passed: true, summary: "The inventory boundary is approved." }],
            blockers: [],
            external_assurance_required: true
          }
        },
        superseded_by_report_id: null,
        created_at: "2026-08-01T10:00:00Z",
        updated_at: "2026-08-01T10:00:00Z"
      }});
    }
    if (path.endsWith("/audit-reports") && method === "POST") {
      return route.fulfill({ status: 201, json: { id: "report-1" } });
    }
    return route.fulfill({ status: 200, json: {} });
  });
}
