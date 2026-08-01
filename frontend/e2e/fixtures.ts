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
  total_kg_co2e: "12846280",
  scope_1_kg_co2e: "3540440",
  scope_2_kg_co2e: "1286020",
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
        roles: ["tenant_admin"],
        is_platform_admin: false
      }});
    }
    if (path === "/dashboard") {
      return route.fulfill({ json: {
        total_kg_co2e: "12846280",
        total_t_co2e: "12846.28",
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
    if (path.startsWith("/inventories") && method === "GET" && !path.includes("calculation-runs")) {
      return route.fulfill({ json: { items: [inventory], total: 1, limit: 200, offset: 0 }});
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
    if (path.endsWith("/activities") && method === "POST") {
      return route.fulfill({ status: 201, json: { id: "activity-1" } });
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
      }], total: 1, limit: 200, offset: 0 }});
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
        report_payload: { totals: { total_t_co2e: "12846.28" } },
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
