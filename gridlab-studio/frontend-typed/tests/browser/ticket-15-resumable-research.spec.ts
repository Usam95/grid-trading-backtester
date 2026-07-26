import { expect, test } from "@playwright/test";

test("creates and observes a durable adaptive research job with causal overlays", async ({ page }) => {
  await page.goto("/studio/");
  await expect(page.getByRole("heading", { name: "Run adaptive research outside the browser" })).toBeVisible();
  await page.getByRole("button", { name: "Start adaptive research job" }).click();
  await expect(page.getByText(/COMPLETED · SEALED|RESUMABLE · FAILED/)).toBeVisible({ timeout: 30_000 });
  await expect(page.getByText("Net return", { exact: true })).toBeVisible();
  await expect(page.getByText(/allocation-owned net-long base exposure/)).toBeVisible();
  await expect(page.locator(".research-job").getByText(/250 USDT Azure MVP is a validation\/learning vehicle/)).toBeVisible();
  await expect(page.getByText("correctness · Deterministic canonical result and invariant checks completed.")).toBeVisible();
  await page.getByRole("button", { name: /Cumulative buy fill/ }).click();
  await expect(page.getByText(/Selected evidence · fill/)).toBeVisible();
});
