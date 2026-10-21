import { test, expect } from "@playwright/test";

test("UI-SMOKE-001 /recepcion renders", async ({ page }) => {
  const res = await page.goto("/recepcion");
  expect(res?.status()).toBe(200);
  await expect(page.locator("body")).not.toBeEmpty();
  await expect(page.getByRole("heading").first()).toBeVisible();
});

test("UI-SMOKE-002 /paciente shows consent dialog first", async ({ page }) => {
  await page.goto("/paciente");
  await expect(page.getByRole("dialog")).toBeVisible();
});
