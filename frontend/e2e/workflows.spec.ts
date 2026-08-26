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

test("inventory register separates Scope 2 methods and identifies the headline", async ({ page }) => {
  await page.goto("/inventories");
  await expect(page.getByRole("columnheader", { name: "Scope 2 location-based" })).toBeVisible();
  await expect(page.getByRole("columnheader", { name: "Scope 2 market-based" })).toBeVisible();
  await expect(page.getByRole("columnheader", { name: "Headline total (location-based)" })).toBeVisible();
  await page.getByLabel("Headline Scope 2 basis").selectOption("market_based");
  await expect(page.getByRole("columnheader", { name: "Headline total (market-based)" })).toBeVisible();
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

test("customer sees DcarbN and Government calculation comparison", async ({ page }) => {
  await page.goto("/data-reviews");
  await page.getByText("DATa-CALC-2026-0199").click();

  const comparison = page.getByLabel(
    "DcarbN and UK Government comparison"
  );
  await expect(comparison).toBeVisible();
  await expect(comparison.getByText("410.5 kgCO₂e")).toBeVisible();
  await expect(comparison.getByText("384.33 kgCO₂e")).toBeVisible();
  await expect(comparison.getByText("26.17 kgCO₂e")).toBeVisible();
  await expect(
    comparison.getByText("DcarbN operational", { exact: true })
  ).toBeVisible();
  await expect(
    comparison.getByText(/does not imply UK Government endorsement/)
  ).toBeVisible();
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
  await expect(page.getByText("Assurance-ready reporting pack", { exact: true })).toBeVisible();
  await expect(page.getByText(/Independent external assurance is still required/)).toBeVisible();
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


test("refrigerant mass balance submits governed inputs and calculated emitted mass", async ({ page }) => {
  await page.goto("/activities/new");
  await page.getByLabel("Governed calculation method").selectOption(
    "scope1.refrigerant.hfc134a.mass_balance.kg.uk_2026.v1"
  );
  await page.getByLabel("Description").fill("HFC-134a annual stock reconciliation");
  await page.getByLabel("Opening stock (kg)").fill("100");
  await page.getByLabel("Purchases/additions (kg)").fill("25");
  await page.getByLabel("Closing stock (kg)").fill("110");
  await page.getByLabel("Recovered/returned (kg)").fill("5");
  await page.getByLabel("Evidence reference").fill("refrigerant-register-2026");
  await page.getByLabel("Source record ID").fill("refrigerant-2026");

  const requestPromise = page.waitForRequest((request) =>
    request.url().includes("/activities") && request.method() === "POST"
  );
  await page.getByRole("button", { name: "Save and validate" }).click();
  const payload = (await requestPromise).postDataJSON() as {
    activity_value: string;
    factor_level_3: string;
    metadata_json: Record<string, string>;
  };

  expect(payload.activity_value).toBe("10");
  expect(payload.factor_level_3).toBe("HFC-134a");
  expect(payload.metadata_json).toMatchObject({
    calculation_method_id:
      "scope1.refrigerant.hfc134a.mass_balance.kg.uk_2026.v1",
    opening_stock_kg: "100",
    purchases_kg: "25",
    closing_stock_kg: "110",
    recovered_kg: "5"
  });
});


test("market-based Scope 2 submits complete contractual evidence", async ({ page }) => {
  await page.goto("/activities/new");
  await page.getByLabel("Scope").selectOption("scope_2");
  await page.getByLabel("Scope 2 method").selectOption("market_based");
  await page.getByLabel("Description").fill("Supplier-backed purchased electricity");
  await page.getByLabel("Activity value").fill("1000");
  await page.getByLabel("Unit").selectOption("kWh");
  await page.getByLabel("Supplier or issuer").fill("Example Energy Ltd");
  await page.getByLabel("Instrument reference").fill("SUPPLY-2026-001");
  await page.getByLabel("Factor source").fill("Supplier disclosure 2026");
  await page.getByLabel("Contractual factor (kg CO₂e/kWh)").fill("0.045");
  await page.getByLabel("Valid from").fill("2026-01-01");
  await page.getByLabel("Valid to").fill("2026-12-31");
  await page.getByLabel("Instrument meets the Scope 2 quality criteria").check();
  await page.getByLabel("Evidence reference").fill("supplier-contract-2026.pdf");
  await page.getByLabel("Source record ID").fill("electricity-2026");

  const requestPromise = page.waitForRequest((request) =>
    request.url().includes("/activities") && request.method() === "POST"
  );
  await page.getByRole("button", { name: "Save and validate" }).click();
  const payload = (await requestPromise).postDataJSON() as {
    scope_2_method: string;
    metadata_json: Record<string, unknown>;
  };

  expect(payload.scope_2_method).toBe("market_based");
  expect(payload.metadata_json).toMatchObject({
    instrument_type: "supplier_specific",
    supplier_or_issuer: "Example Energy Ltd",
    instrument_reference: "SUPPLY-2026-001",
    factor_source: "Supplier disclosure 2026",
    factor_value: "0.045",
    factor_unit: "kg CO2e/kWh",
    valid_from: "2026-01-01",
    valid_to: "2026-12-31",
    geography_code: "GB",
    quality_criteria_attested: true
  });
});


test("audit report exposes customer PDF and CSV exports", async ({ page }) => {
  await page.goto("/audit-reports");
  await page.getByRole("button", { name: "Open" }).click();

  await expect(page.getByRole("button", { name: "Download PDF" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Download CSV" })).toBeVisible();
  await expect(page.getByText("Report contents")).toBeVisible();
});


test("Scope 3 categories 3, 5 and 7 submit governed selectors", async ({ page }) => {
  const cases = [
    {
      method: "scope3.category3.diesel_wtt.litres.uk_2026.v1",
      category: 3, type: "stationary_combustion", unit: "litres",
      level1: "WTT- fuels", level3: "Diesel (average biofuel blend)",
      boundary: "well_to_tank"
    },
    {
      method: "scope3.category5.commercial_waste.landfill.tonnes.uk_2026.v1",
      category: 5, type: "waste_generated", unit: "tonnes",
      level1: "Waste disposal", level3: "Commercial and industrial waste",
      boundary: "indirect_value_chain"
    },
    {
      method: "scope3.category7.average_car.unknown_fuel.km.uk_2026.v1",
      category: 7, type: "employee_commuting", unit: "km",
      level1: "Business travel- land", level3: "Average car",
      boundary: "indirect_value_chain"
    }
  ];

  for (const item of cases) {
    await page.goto("/activities/new");
    await page.getByLabel("Governed calculation method").selectOption(item.method);
    await page.getByLabel("Description").fill(`Governed category ${item.category} activity`);
    await page.getByLabel("Activity value").fill("1000");
    await page.getByLabel("Evidence reference").fill(`category-${item.category}-evidence`);
    await page.getByLabel("Source record ID").fill(`category-${item.category}-2026`);
    const requestPromise = page.waitForRequest((request) =>
      request.url().includes("/activities") && request.method() === "POST"
    );
    await page.getByRole("button", { name: "Save and validate" }).click();
    const payload = (await requestPromise).postDataJSON() as Record<string, unknown>;
    expect(payload).toMatchObject({
      activity_type: item.type,
      scope: "scope_3",
      scope_3_category: item.category,
      activity_unit: item.unit,
      factor_level_1: item.level1,
      factor_level_3: item.level3,
      lifecycle_boundary: item.boundary,
      metadata_json: { calculation_method_id: item.method }
    });
  }
});


test("Category 9 downstream freight preserves mode and accounting classification", async ({ page }) => {
  const cases = [
    {
      method: "scope3.category9.average_diesel_van.tonne_km.uk_2026.v1",
      level2: "Vans", level3: "Average (up to 3.5 tonnes)", column: "Diesel"
    },
    {
      method: "scope3.category9.average_non_refrigerated_hgv.average_laden.tonne_km.uk_2026.v1",
      level2: "HGV (non-refrigerated, all diesel)",
      level3: "Average non-refrigerated HGVs", column: "Average laden"
    },
    {
      method: "scope3.category9.rail_freight.tonne_km.uk_2026.v1",
      level2: "Rail", level3: "Freight train", column: null
    }
  ];

  for (const item of cases) {
    await page.goto("/activities/new");
    await page.getByLabel("Governed calculation method").selectOption(item.method);
    await page.getByLabel("Description").fill("Customer-contracted downstream distribution");
    await page.getByLabel("Activity value").fill("1000");
    await page.getByLabel("Evidence reference").fill("carrier-movement-ledger-2026");
    await page.getByLabel("Source record ID").fill(`downstream-${item.level2}-2026`);

    const requestPromise = page.waitForRequest((request) =>
      request.url().includes("/activities") && request.method() === "POST"
    );
    await page.getByRole("button", { name: "Save and validate" }).click();
    const payload = (await requestPromise).postDataJSON() as Record<string, unknown>;

    expect(payload).toMatchObject({
      activity_type: "freight_transport",
      scope: "scope_3",
      scope_3_category: 9,
      activity_unit: "tonne.km",
      factor_level_1: "Freighting goods",
      factor_level_2: item.level2,
      factor_level_3: item.level3,
      factor_column_text: item.column,
      lifecycle_boundary: "indirect_value_chain",
      metadata_json: { calculation_method_id: item.method }
    });
  }
});


test("remaining Scope 3 categories submit supplier-specific lineage", async ({ page }) => {
  for (const category of [1, 2, 8, 10, 11, 12, 13, 14, 15]) {
    await page.goto("/activities/new");
    const method = `scope3.category${category}.supplier_specific.reported_kgco2e.ghgp.v1`;
    await page.getByLabel("Governed calculation method").selectOption(method);
    await page.getByLabel("Description", { exact: true }).fill(`Supplier result for category ${category}`);
    await page.getByLabel("Activity value").fill("1250");
    await page.getByLabel("Supplier or investee").fill("Example supplier");
    await page.getByLabel("Methodology", { exact: true }).fill("GHG Protocol supplier-specific method");
    await page.getByLabel("Methodology version").fill("2026.1");
    await page.getByLabel("Supplier reporting period").fill("2026");
    await page.getByLabel("Lifecycle boundary description").fill("Cradle-to-gate attributable emissions");
    await page.getByLabel("Assurance status").selectOption("third_party_verified");
    await page.getByLabel("Evidence reference").fill(`supplier-evidence-${category}.pdf`);
    await page.getByLabel("Source record ID").fill(`supplier-result-${category}-2026`);

    const requestPromise = page.waitForRequest((request) =>
      request.url().includes("/activities") && request.method() === "POST"
    );
    await page.getByRole("button", { name: "Save and validate" }).click();
    const payload = (await requestPromise).postDataJSON() as Record<string, unknown>;
    expect(payload).toMatchObject({
      activity_type: "value_chain_result",
      scope: "scope_3",
      scope_3_category: category,
      activity_value: "1250",
      activity_unit: "kgCO2e",
      factor_level_1: "Supplier-specific lifecycle result",
      factor_level_2: `Category ${category}`,
      lifecycle_boundary: "indirect_value_chain",
      evidence_reference: `supplier-evidence-${category}.pdf`,
      metadata_json: {
        calculation_method_id: method,
        supplier_name: "Example supplier",
        supplier_methodology: "GHG Protocol supplier-specific method",
        supplier_methodology_version: "2026.1",
        supplier_reporting_period: "2026",
        boundary_description: "Cradle-to-gate attributable emissions",
        assurance_status: "third_party_verified"
      }
    });
  }
});



test("Scope 1 DcarbN comparator method preserves delivery-van selectors", async ({ page }) => {
  await page.goto("/activities/new");
  await page.getByLabel("Governed calculation method").selectOption(
    "scope1.mobile_combustion.delivery_van.class1.diesel.km.uk_2026.v1"
  );
  await page.getByLabel("Description").fill("DcarbN fleet delivery van comparator");
  await page.getByLabel("Activity value").fill("1000");
  await page.getByLabel("Evidence reference").fill("dcarbn-fleet-ledger-2026");
  await page.getByLabel("Source record ID").fill("dcarbn-scope1-van-2026");

  const requestPromise = page.waitForRequest((request) =>
    request.url().includes("/activities") && request.method() === "POST"
  );
  await page.getByRole("button", { name: "Save and validate" }).click();
  const payload = (await requestPromise).postDataJSON() as Record<string, unknown>;

  expect(payload).toMatchObject({
    activity_type: "mobile_combustion",
    scope: "scope_1",
    scope_3_category: null,
    activity_unit: "km",
    factor_level_1: "Delivery vehicles",
    factor_level_2: "Vans",
    factor_level_3: "Class I (up to 1.305 tonnes)",
    factor_column_text: "Diesel",
    metadata_json: {
      calculation_method_id:
        "scope1.mobile_combustion.delivery_van.class1.diesel.km.uk_2026.v1"
    }
  });
});


test("customer uploads governed activity data without column mapping", async ({ page }) => {
  await page.goto("/data-imports");
  await expect(
    page.getByRole("heading", { name: "Upload Scope 1, 2 and 3 activity data" })
  ).toBeVisible();

  await page.getByLabel("Choose CSV file").setInputFiles({
    name: "activity-upload.csv",
    mimeType: "text/csv",
    buffer: Buffer.from(
      "calculation_method_id,activity_date,description,activity_value,activity_unit,evidence_reference,source_record_id,geography_code\n" +
        "scope2.location_electricity.kwh.uk_2026.v1,2026-03-31,Purchased electricity,50000,kWh,electricity-bill.pdf,electricity-2026-001,GB"
    )
  });

  await expect(page.getByText("1 ready", { exact: true })).toBeVisible();
  await expect(page.getByText("0 need attention", { exact: true })).toBeVisible();
  const requestPromise = page.waitForRequest((request) =>
    request.url().includes("/activities") && request.method() === "POST"
  );
  await page.getByRole("button", { name: "Import 1 validated rows" }).click();
  const payload = (await requestPromise).postDataJSON() as Record<string, unknown>;
  expect(payload).toMatchObject({
    activity_type: "purchased_electricity",
    scope: "scope_2",
    scope_2_method: "location_based",
    activity_value: "50000",
    activity_unit: "kWh",
    source_record_id: "electricity-2026-001",
    metadata_json: {
      calculation_method_id: "scope2.location_electricity.kwh.uk_2026.v1"
    }
  });

  const calculationPromise = page.waitForRequest((request) =>
    request.url().includes("/calculation-runs") && request.method() === "POST"
  );
  await page.getByRole("button", { name: "Calculate inventory" }).click();
  await calculationPromise;
  await expect(page.getByText("Calculation version 2 completed")).toBeVisible();
  await expect(page.getByLabel("Calculation summary")).toContainText("Scope 1");
  await expect(page.getByLabel("Calculation summary")).toContainText("Scope 2 location");
  await expect(page.getByLabel("Calculation summary")).toContainText("Scope 2 market");
  await expect(page.getByLabel("Calculation summary")).toContainText("Scope 3");
  await expect(page.getByText(/Headline total \(location-based\):/)).toContainText("12,846.28 tCO₂e");
  await expect(page.getByRole("link", { name: "Complete Scope 3 screening" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Continue to approval" })).toBeVisible();
});

test("an existing inventory can be calculated without re-uploading activity", async ({ page }) => {
  await page.goto("/inventories");
  await page.getByRole("button", { name: "Calculate" }).click();
  await expect(page.getByRole("dialog", { name: "Calculate inventory" })).toBeVisible();

  const calculationPromise = page.waitForRequest((request) =>
    request.url().includes("/calculation-runs") && request.method() === "POST"
  );
  await page.getByRole("button", { name: "Calculate inventory" }).click();
  await calculationPromise;

  await expect(page.getByText("Calculation version 2 completed")).toBeVisible();
  await expect(page.getByText(/Headline total \(location-based\):/)).toContainText("12,846.28 tCO₂e");

  await page.getByLabel("Calculation headline Scope 2 basis").selectOption("market_based");
  await expect(page.getByText(/Headline total \(market-based\):/)).toContainText("12,660.26 tCO₂e");
});


test("customer maps validates and reconciles an accounting import", async ({ page }) => {
  await page.goto("/data-imports");
  await page.getByRole("button", { name: "Supplier-calculated Scope 3" }).click();
  await expect(
    page.getByRole("heading", { name: "Supplier-calculated Scope 3 import" })
  ).toBeVisible();

  await page.getByRole("button", { name: "Load example" }).click();
  await expect(page.getByText("1 row detected. Confirm the column mapping.")).toBeVisible();
  await page.getByRole("button", { name: "Build validation preview" }).click();

  await expect(
    page.getByRole("table", { name: "Scope 3 import validation preview" })
  ).toBeVisible();
  await expect(page.getByText("1 valid", { exact: true })).toBeVisible();
  await expect(page.getByText("0 need attention", { exact: true })).toBeVisible();

  const requestPromise = page.waitForRequest((request) =>
    request.url().endsWith("/integrations/data/accounting/scope-3/batch") &&
    request.method() === "POST"
  );
  await page.getByRole("button", { name: "Import 1 validated rows" }).click();
  const request = await requestPromise;
  const payload = request.postDataJSON() as {
    schema_version: string;
    records: Array<Record<string, unknown>>;
  };

  expect(payload.schema_version).toBe("1.0");
  expect(payload.records).toHaveLength(1);
  expect(payload.records[0]).toMatchObject({
    source_system: "xero",
    external_transaction_id: "txn-1-001",
    scope_3_category: 1,
    reported_kg_co2e: "1000",
    allocation_percentage: "75",
    evidence_reference: "supplier-assurance-2026.pdf"
  });

  await expect(
    page.getByRole("heading", { name: "Import reconciliation" })
  ).toBeVisible();
  await expect(page.getByText("The accepted records entered the governed emissions review queue.")).toBeVisible();
  await expect(page.getByText("9f1d1c2fdbb70f6ea4f620f48ed9cfbff648901a205a4c524935730fcfaf4382")).toBeVisible();
});


test("connected systems register safe profiles and start authorised syncs", async ({ page }) => {
  await page.goto("/connected-systems");

  await expect(page.getByRole("heading", { name: "Connected systems" })).toBeVisible();
  await expect(page.getByText("Xero · UK entity").first()).toBeVisible();
  await expect(page.getByText("1", { exact: true }).first()).toBeVisible();
  await expect(page.getByRole("heading", { name: "Synchronisation history" })).toBeVisible();
  await expect(page.getByText("148 received")).toBeVisible();
  await expect(page.getByText("143 imported")).toBeVisible();
  await expect(page.getByText("5 rejected")).toBeVisible();
  await expect(page.getByText("3768f943c6b5…")).toBeVisible();

  const syncRequest = page.waitForRequest((request) =>
    request.url().endsWith(
      "/integrations/data/accounting/connections/77777777-7777-7777-7777-777777777777/syncs"
    ) && request.method() === "POST"
  );
  await page.getByRole("button", { name: "Sync now" }).click();
  await syncRequest;
  await expect(page.getByText(/Synchronisation job .* is queued/)).toBeVisible();

  await page.getByRole("button", { name: "Set up" }).first().click();
  await expect(page.getByRole("heading", { name: "Register QuickBooks" })).toBeVisible();
  await page.getByLabel("Reporting organisation").selectOption("11111111-1111-1111-1111-111111111111");
  await page.getByLabel("Connection name").fill("QuickBooks · UK entity");
  await page.getByLabel("Customer reference").fill("customer-1042");
  await page.getByLabel("External company ID").fill("northstar-qb");

  const createRequest = page.waitForRequest((request) =>
    request.url().endsWith("/integrations/data/accounting/connections") &&
    request.method() === "POST"
  );
  await page.getByRole("button", { name: "Register connection" }).click();
  const created = await createRequest;
  const payload = created.postDataJSON() as Record<string, unknown>;

  expect(payload).toMatchObject({
    organisation_id: "11111111-1111-1111-1111-111111111111",
    provider: "quickbooks",
    external_company_id: "northstar-qb",
    mapping_profile_version: "2026.1"
  });
  expect(payload).not.toHaveProperty("password");
  expect(payload).not.toHaveProperty("access_token");
  expect(payload).not.toHaveProperty("secret_reference");
  await expect(page.getByText(/QuickBooks has been registered safely/)).toBeVisible();

  await expect(page.getByRole("link", { name: "Open CSV import" })).toHaveAttribute(
    "href",
    "/data-imports"
  );
});
