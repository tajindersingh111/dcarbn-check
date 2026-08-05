import { expect, test } from "@playwright/test";

import { installApiFixtures } from "./fixtures";

test.beforeEach(async ({ page }) => {
  await installApiFixtures(page);
});

test("dashboard loads live workflow data", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
  await expect(page.getByText("12,846.28 tCO₂e")).toBeVisible();
  await expect(page.getByText("Northstar Corporate Inventory 2026")).toBeVisible();
});

test("organisation creation posts to the API", async ({ page }) => {
  await page.goto("/organisations");
  await page.getByRole("button", { name: "Add organisation" }).click();
  await page.getByLabel("Name", { exact: true }).fill("Northstar Logistics Ltd");
  await page.getByLabel("Country code").fill("GB");
  const requestPromise = page.waitForRequest((request) =>
    request.url().endsWith("/api/v1/organisations") && request.method() === "POST"
  );
  await page.getByRole("button", { name: "Create organisation" }).click();
  await requestPromise;
});

test("inventory workflow creates a reporting inventory", async ({ page }) => {
  await page.goto("/inventories");
  await page.getByRole("button", { name: "Create inventory" }).click();
  await page.getByLabel("Inventory name").fill("Northstar Corporate Inventory 2026");
  await page.getByLabel("Reporting period").selectOption("33333333-3333-3333-3333-333333333333");
  const requestPromise = page.waitForRequest((request) =>
    request.url().endsWith("/api/v1/inventories") && request.method() === "POST"
  );
  await page.getByRole("button", { name: "Create inventory" }).last().click();
  await requestPromise;
});

test("activity entry submits the backend contract", async ({ page }) => {
  await page.goto("/activities/new");
  await page.getByLabel("Description").fill("Diesel consumed by owned HGV fleet");
  await page.getByLabel("Activity value").fill("1250.50");
  await page.getByLabel("Evidence reference").fill("invoice-2026-08");
  await page.getByLabel("Source record ID").fill("fuel-statement-2026-08");
  const requestPromise = page.waitForRequest((request) =>
    request.url().includes("/activities") && request.method() === "POST"
  );
  await page.getByRole("button", { name: "Save and validate" }).click();
  await requestPromise;
  await expect(page.getByText("Activity saved and validated.")).toBeVisible();
});

test("DATa review decision calls the review API", async ({ page }) => {
  await page.goto("/data-reviews");
  await expect(page.getByRole("heading", { name: "DATa-CALC-2026-0184" })).toBeVisible();
  const requestPromise = page.waitForRequest((request) =>
    request.url().includes("/decision") && request.method() === "POST"
  );
  await page.getByRole("button", { name: "Approve" }).click();
  await requestPromise;
});

test("inventory approval calls the decision API", async ({ page }) => {
  await page.goto("/approvals");
  await expect(page.getByText("Northstar Corporate Inventory 2026").first()).toBeVisible();
  const requestPromise = page.waitForRequest((request) =>
    request.url().includes("/decision") && request.method() === "POST"
  );
  await page.getByRole("button", { name: "Approve inventory" }).click();
  await requestPromise;
});

test("audit report register opens the immutable payload", async ({ page }) => {
  await page.goto("/audit-reports");
  await page.getByRole("button", { name: "Open" }).click();
  await expect(page.getByText(/total_t_co2e/)).toBeVisible();
  await expect(page.getByText(/12846.28/)).toBeVisible();
});


test("Scope 3 screening saves all category decisions and shows validation boundary", async ({ page }) => {
  await page.goto("/scope-3-screening");
  await expect(page.getByRole("heading", { name: "Scope 3 category screening" })).toBeVisible();
  await expect(page.getByText("Draft — calculation not fully validated")).toBeVisible();
  await page.getByLabel("Reporting inventory").selectOption("22222222-2222-2222-2222-222222222222");

  for (let category = 1; category <= 15; category += 1) {
    await page.getByLabel(`Category ${category} rationale`).fill(
      "Included after documented relevance and materiality screening."
    );
  }

  const requestPromise = page.waitForRequest((request) =>
    request.url().includes("/scope-3-category-dispositions") && request.method() === "PUT"
  );
  await page.getByRole("button", { name: "Save all 15 decisions" }).click();
  const request = await requestPromise;
  const payload = request.postDataJSON() as { items: Array<{ category: number }> };
  expect(payload.items).toHaveLength(15);
  expect(payload.items.map((item) => item.category)).toEqual(Array.from({ length: 15 }, (_, index) => index + 1));
  await expect(page.getByText("Independent approval is still required.")).toBeVisible();
});


test("governed freight method locks and submits exact calculation selectors", async ({ page }) => {
  await page.goto("/activities/new");
  await page.getByLabel("Governed calculation method").selectOption(
    "scope3.category4.diesel_van.tonne_km.uk_2026.v1"
  );
  await expect(page.getByText("Governed method selected")).toBeVisible();
  await expect(page.getByLabel("Scope 3 category")).toHaveValue("4");
  await expect(page.getByLabel("Unit")).toHaveValue("tonne.km");
  await page.getByLabel("Description").fill("Upstream freight by Class I diesel van");
  await page.getByLabel("Activity value").fill("1000");
  await page.getByLabel("Evidence reference").fill("freight-ledger-2026-01");
  await page.getByLabel("Source record ID").fill("freight-2026-01");

  const requestPromise = page.waitForRequest((request) =>
    request.url().includes("/activities") && request.method() === "POST"
  );
  await page.getByRole("button", { name: "Save and validate" }).click();
  const request = await requestPromise;
  const payload = request.postDataJSON() as {
    activity_type: string;
    scope: string;
    scope_3_category: number;
    activity_unit: string;
    factor_level_1: string;
    factor_level_2: string;
    factor_level_3: string;
    factor_column_text: string;
    metadata_json: { calculation_method_id: string };
  };

  expect(payload).toMatchObject({
    activity_type: "freight_transport",
    scope: "scope_3",
    scope_3_category: 4,
    activity_unit: "tonne.km",
    factor_level_1: "Freighting goods",
    factor_level_2: "Vans",
    factor_level_3: "Class I (up to 1.305 tonnes)",
    factor_column_text: "Diesel",
    metadata_json: {
      calculation_method_id:
        "scope3.category4.diesel_van.tonne_km.uk_2026.v1"
    }
  });
});


test("methodology administrator creates a controlled draft version", async ({ page }) => {
  await page.goto("/admin/methodologies");
  await expect(page.getByRole("heading", { name: "Methodology registry" })).toBeVisible();
  await page.getByRole("button", { name: "New version" }).click();
  await page.getByLabel("Method key").fill("scope2.location_electricity");
  await page.getByLabel("Display name").fill("Scope 2 location electricity");
  await page.getByLabel("Effective from").fill("2026-01-01");
  await page.getByLabel("Effective to").fill("2026-12-31");
  await page.getByLabel("Golden factor value").fill("0.20000");
  await page.getByLabel("Expected output").fill("200.00000");
  await page.getByLabel("Official source URL").fill(
    "https://www.gov.uk/government/publications/greenhouse-gas-reporting-conversion-factors-2026"
  );
  await page.getByLabel("Reason for change").fill(
    "Initial controlled Scope 2 methodology for the 2026 reporting year."
  );

  const requestPromise = page.waitForRequest((request) =>
    request.url().endsWith("/api/v1/methodologies") &&
    request.method() === "POST"
  );
  await page.getByRole("button", { name: "Create draft version" }).click();
  const request = await requestPromise;
  const payload = request.postDataJSON() as {
    expression: string;
    inputs: Array<{ name: string; unit: string }>;
    golden_tests: Array<{ expected_output: string }>;
    source_reference: string;
  };

  expect(payload.expression).toBe(
    "activity_value * factor_value * allocation_percentage / 100"
  );
  expect(payload.inputs.map((item) => item.name)).toEqual([
    "activity_value",
    "factor_value",
    "allocation_percentage"
  ]);
  expect(payload.golden_tests[0].expected_output).toBe("200.00000");
  expect(payload.source_reference).toContain("gov.uk");
});
