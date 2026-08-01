import { expect, test } from "@playwright/test";

test("MFA challenge completes cookie login", async ({ page }) => {
  await page.route("**/api/v1/auth/login", async (route) => {
    await route.fulfill({ json: {
      authenticated: false,
      requires_mfa: true,
      mfa_challenge_token: "challenge-token-12345678901234567890"
    }});
  });
  await page.route("**/api/v1/auth/mfa/verify", async (route) => {
    await route.fulfill({ json: { authenticated: true, requires_mfa: false }});
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
  await page.getByLabel("MFA or recovery code").fill("123456");
  await page.getByRole("button", { name: "Verify and sign in" }).click();
  await expect(page).toHaveURL("/");
});

test("password reset request is non-enumerating", async ({ page }) => {
  await page.route("**/api/v1/auth/password-reset/request", async (route) => {
    await route.fulfill({ status: 202, json: {
      message: "If the account exists, password reset instructions have been sent."
    }});
  });
  await page.goto("/forgot-password");
  await page.getByLabel("Tenant workspace").fill("northstar-logistics");
  await page.getByLabel("Email address").fill("unknown@example.com");
  await page.getByRole("button", { name: "Send reset instructions" }).click();
  await expect(page.getByText(/If the account exists/)).toBeVisible();
});
