import { expect, test } from "@playwright/test";

test("user signs in and enters the tenant workspace", async ({ page }) => {
  await page.route("**/api/v1/auth/login", async (route) => {
    await route.fulfill({ json: {
      access_token: "access-token",
      refresh_token: "refresh-token",
      token_type: "bearer",
      access_token_expires_at: "2026-08-01T20:00:00Z",
      refresh_token_expires_at: "2026-08-31T20:00:00Z"
    }});
  });
  await page.route("**/api/v1/auth/me", async (route) => {
    await route.fulfill({ json: {
      id: "user-1",
      email: "alex@example.com",
      full_name: "Alex Morgan",
      tenant_id: "tenant-1",
      tenant_name: "Northstar Logistics",
      tenant_slug: "northstar-logistics",
      roles: ["tenant_admin"],
      is_platform_admin: false
    }});
  });
  await page.route("**/api/v1/dashboard", async (route) => {
    await route.fulfill({ json: {
      total_kg_co2e: "0",
      total_t_co2e: "0",
      inventory_count: 0,
      locked_inventory_count: 0,
      open_data_review_count: 0,
      open_approval_count: 0,
      organisation_count: 0
    }});
  });
  await page.route("**/api/v1/inventories**", async (route) => {
    await route.fulfill({ json: { items: [], total: 0, limit: 5, offset: 0 }});
  });

  await page.goto("/login");
  await page.getByLabel("Tenant workspace").fill("northstar-logistics");
  await page.getByLabel("Email address").fill("alex@example.com");
  await page.getByLabel("Password").fill("Correct-Horse-Battery-Staple-2026");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL("/");
  await expect(page.getByText("Alex Morgan")).toBeVisible();
});

test("invited user creates an account", async ({ page }) => {
  await page.route("**/api/v1/auth/invitations/accept", async (route) => {
    await route.fulfill({ status: 204, body: "" });
  });
  await page.goto("/accept-invitation?token=" + "a".repeat(48));
  await page.getByLabel("Password").fill("Correct-Horse-Battery-Staple-2026");
  await page.getByLabel("Confirm password").fill("Correct-Horse-Battery-Staple-2026");
  await page.getByRole("button", { name: "Activate account" }).click();
  await expect(page.getByText("Your account is active.")).toBeVisible();
});
