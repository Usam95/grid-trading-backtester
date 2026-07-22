import { expect, test } from "@playwright/test";

test("operator completes the fixed official production-data workflow", async ({ page }) => {
  test.skip(
    process.env.GRIDLAB_REAL_BINANCE_BROWSER !== "1",
    "set GRIDLAB_REAL_BINANCE_BROWSER=1 for the fixed official one-day workflow",
  );
  test.setTimeout(180_000);

  await page.goto("/studio/");
  await page.getByLabel("Symbol").fill("BTCUSDT");
  await page.getByLabel("UTC archive day").fill("2025-01-01");
  await page.getByLabel("Lower bound").fill("92500");
  await page.getByLabel("Upper bound").fill("93500");
  await page.getByRole("button", { name: "Preview official download" }).click();

  await expect(page.getByText("BTCUSDT-1m-2025-01-01.zip")).toBeVisible();
  await page.getByRole("button", { name: "Download, verify & normalize" }).click();
  await expect(page.getByText("QUALITY APPROVED")).toBeVisible({
    timeout: 60_000,
  });
  await expect(page.getByText(/1,440 ordered candles/)).toBeVisible();

  await page.getByRole("button", { name: "Run production-history backtest" }).click();
  await expect(page.getByText("PRODUCTION HISTORY", { exact: true })).toBeVisible({
    timeout: 60_000,
  });
  await expect(page.getByText("TESTNET HISTORY NOT USED")).toBeVisible();
  await expect(page.getByText("Deterministic backtest fingerprint")).toBeVisible();
});
