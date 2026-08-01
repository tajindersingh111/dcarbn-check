import { expect, test } from "@playwright/test";

test("live backend accepts the configured bearer token", async ({ request }) => {
  test.skip(!process.env.E2E_ACCESS_TOKEN, "E2E_ACCESS_TOKEN is not configured.");

  const apiBase =
    process.env.E2E_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1";
  const response = await request.get(`${apiBase}/dashboard`, {
    headers: {
      Authorization: `Bearer ${process.env.E2E_ACCESS_TOKEN}`
    }
  });

  expect(response.ok()).toBeTruthy();
  const body = await response.json();
  expect(body).toHaveProperty("inventory_count");
  expect(body).toHaveProperty("total_t_co2e");
});
