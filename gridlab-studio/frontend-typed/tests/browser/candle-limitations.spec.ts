import { expect, test } from "@playwright/test";

test("operator sees candle-fill limitations called out in research results", async ({ page }) => {
  await page.route("**/api/studio/catalogs/binance/eur?refresh=*", (route) => route.fulfill({
    contentType: "application/json",
    body: JSON.stringify({
      catalog_id: "9".repeat(64),
      retrieved_at: "2026-07-23T12:00:00Z",
      quote_asset: "EUR",
      filters: [],
      sources: [],
      symbols: [],
    }),
  }));
  await page.route("**/api/studio/archives/binance/eur?refresh=*", (route) => route.fulfill({
    contentType: "application/json",
    body: JSON.stringify({
      archive_id: "7".repeat(64),
      status: "ready",
      retrieved_at: "2026-07-25T12:00:00Z",
      quote_asset: "EUR",
      interval: "1m",
      symbols: ["BTCEUR", "ETHEUR"],
      sources: [],
      preview: {
        preview_id: "6".repeat(64),
        source_objects: 0,
        estimated_download_bytes: 0,
        estimated_storage_bytes: 0,
        pending_partitions: 0,
        verified_partitions: 2,
        symbols: [],
      },
      datasets: [],
      blocking_reasons: [],
    }),
  }));
  await page.route("**/api/studio/backtests", (route) => route.fulfill({
    status: 201,
    contentType: "application/json",
    body: JSON.stringify({
      id: "run-1",
      status: "completed",
      created_at: "2026-07-25T12:00:00Z",
      specification: { symbol: "ETHUSDT" },
      primary_result: {
        net_return: 0.01,
        final_equity: 10100,
        max_drawdown: -0.01,
        completed_trades: 2,
        fees_paid: 1,
        verdict: "Promising",
      },
      result: {
        symbol: "ETHUSDT",
        bars: 300,
        initial_cash: 10000,
        final_equity: 10100,
        fees_paid: 1,
        metrics: { total_return: 0.01, max_drawdown: -0.01, n_trades: 2, win_rate: 1 },
        verdict: { label: "Promising", tone: "good", score: 5, max_score: 7 },
        trades: [],
        simulation: {
          mode: "candle",
          canonical_core: false,
          venue_execution_proof: false,
          limitations: [
            "Normal orders become eligible only from the candle after they begin resting.",
          ],
        },
      },
    }),
  }));

  await page.goto("/studio/");
  await page.getByLabel("Symbol", { exact: true }).fill("ETHUSDT");
  await page.getByLabel("Synthetic bars").fill("300");
  await page.getByRole("button", { name: "Run backtest" }).click();

  await expect(page.getByText("CANDLE SIMULATION ONLY")).toBeVisible();
  await expect(page.getByText("NOT VENUE EXECUTION PROOF")).toBeVisible();
});
