import { expect, test } from "@playwright/test";

test("creates and observes a durable adaptive research job with causal overlays", async ({ page }) => {
  test.setTimeout(360_000);
  await page.goto("/studio/");
  await expect(page.getByRole("heading", { name: "Run adaptive research outside the browser" })).toBeVisible();
  await expect(page.getByText("Local datasets ready", { exact: true })).toBeVisible();
  await page.getByLabel("EUR production symbol").selectOption("DOGEEUR");
  await expect(page.getByLabel("Verified local range")).toBeEnabled();
  await page.getByRole("button", { name: "Start adaptive research job" }).click();
  await expect(page.getByText(/COMPLETED · SEALED|RESUMABLE · FAILED/)).toBeVisible({ timeout: 330_000 });
  await expect(page.getByText("Net return", { exact: true })).toBeVisible();
  await expect(page.getByText("Data source", { exact: true })).toBeVisible();
  await expect(page.getByText("verified local production archive", { exact: true })).toBeVisible();
  await expect(page.getByText(/\d[\d,]* candles/)).toBeVisible();
  await expect(page.getByText(/allocation-owned net-long base exposure/)).toBeVisible();
  await expect(page.locator(".research-job").getByText(/250 USDT Azure MVP is a validation\/learning vehicle/)).toBeVisible();
  await expect(page.getByText("correctness · Deterministic canonical result and invariant checks completed.")).toBeVisible();
  await page.getByRole("button", { name: /Cumulative execution fill/ }).click();
  await expect(page.getByText(/Selected evidence · fill/)).toBeVisible();
});
