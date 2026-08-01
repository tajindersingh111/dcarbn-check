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
  await page.getByLabel("Name").fill("Northstar Logistics Ltd");
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
  await expect(page.getByText("DATa-CALC-2026-0184")).toBeVisible();
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
