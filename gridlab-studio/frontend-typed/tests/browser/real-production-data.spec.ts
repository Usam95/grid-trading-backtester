import { expect, test } from "@playwright/test";

test("operator replays one local synchronized EUR archive slice", async ({ page }) => {
  test.skip(
    process.env.GRIDLAB_REAL_BINANCE_BROWSER !== "1",
    "set GRIDLAB_REAL_BINANCE_BROWSER=1 after synchronizing the local EUR archive",
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
  await expect(page.locator(".symbol-evidence")).toContainText("Stable dataset identity");
  await expect(page.locator(".symbol-evidence")).toContainText("verified 1m candles");
  const lastDate = await page.getByLabel("UTC end day").inputValue();
  expect(lastDate).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  await page.getByLabel("UTC start day").fill(lastDate);

  await page.getByRole("button", { name: "Run production-history backtest" }).click();
  await expect(page.getByText("PRODUCTION HISTORY", { exact: true })).toBeVisible({
    timeout: 60_000,
  });
  await expect(page.getByText("TESTNET HISTORY NOT USED")).toBeVisible();
  await expect(
    page.locator(".metrics article").filter({ hasText: "Final equity" }),
  ).toContainText("EUR");
  await expect(page.getByText("Dataset identity", { exact: true })).toBeVisible();
  await expect(page.getByText("Partition identities", { exact: true })).toBeVisible();
  await expect(page.getByText("Deterministic backtest fingerprint")).toBeVisible();
  await expect(page.getByText("Catalog identity", { exact: true })).toHaveCount(2);
});
