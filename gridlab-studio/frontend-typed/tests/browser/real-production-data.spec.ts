import { expect, test } from "@playwright/test";

test("operator completes a bounded official EUR production-data workflow", async ({ page }) => {
  test.skip(
    process.env.GRIDLAB_REAL_BINANCE_BROWSER !== "1",
    "set GRIDLAB_REAL_BINANCE_BROWSER=1 for the bounded official EUR workflow",
  );
  test.setTimeout(360_000);

  await page.goto("/studio/");
  await expect(page.getByText(/eligible EUR symbols/)).toBeVisible({
    timeout: 180_000,
  });
  const catalogIdentity = await page.locator(".catalog-identity code").textContent();
  expect(catalogIdentity).toMatch(/^[0-9a-f]{64}$/);
  const symbolSelect = page.getByLabel("EUR production symbol");
  const selectedSymbol = await symbolSelect.locator("option").evaluateAll((options) =>
    options
      .map((option) => (option as HTMLOptionElement).value)
      .find((symbol) => symbol !== "BTCEUR"),
  );
  if (!selectedSymbol) throw new Error("live catalog has no non-BTC EUR symbol");
  expect(selectedSymbol).toMatch(/EUR$/);
  await symbolSelect.selectOption(selectedSymbol);
  await expect(page.locator(".symbol-evidence")).toContainText("median daily volume");
  await expect(page.locator(".symbol-evidence")).toContainText("current spread");
  await expect(page.locator(".symbol-evidence")).toContainText("Archive intervals:");
  const lastDate = await page.getByLabel("UTC end day").inputValue();
  expect(lastDate).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  await page.getByLabel("UTC start day").fill(lastDate);
  await page.getByRole("button", { name: "Preview official download" }).click();

  await expect(page.getByText(`${selectedSymbol}-1m-${lastDate}.zip`)).toBeVisible();
  await page.getByRole("button", { name: "Download, verify & normalize" }).click();
  await expect(page.getByText("QUALITY APPROVED")).toBeVisible({
    timeout: 60_000,
  });
  await expect(page.getByText(/1,440 ordered candles/)).toBeVisible();
  await expect(page.getByText("Manifest identity", { exact: true })).toBeVisible();
  await expect(page.locator(".manifest-card code")).toHaveCount(3);

  await page.getByRole("button", { name: "Run production-history backtest" }).click();
  await expect(page.getByText("PRODUCTION HISTORY", { exact: true })).toBeVisible({
    timeout: 60_000,
  });
  await expect(page.getByText("TESTNET HISTORY NOT USED")).toBeVisible();
  await expect(
    page.locator(".metrics article").filter({ hasText: "Final equity" }),
  ).toContainText("EUR");
  await expect(page.getByText("Deterministic backtest fingerprint")).toBeVisible();
  await expect(page.getByText("Catalog identity", { exact: true })).toHaveCount(2);
});
