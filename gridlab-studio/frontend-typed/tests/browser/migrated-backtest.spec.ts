import { expect, test } from "@playwright/test";

test("operator completes and reloads the migrated typed backtest while legacy stays available", async ({
  page,
}) => {
  const consoleErrors: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });

  await page.goto("/studio/");
  await expect(page.getByText("NO ONLINE TRADING AUTHORITY")).toBeVisible();
  await expect(page.getByRole("navigation", { name: "Studio" })).toContainText(
    "Command Center",
  );

  await page.getByLabel("Symbol").fill("ETHUSDT");
  await page.getByLabel("Synthetic bars").fill("300");
  await page.getByRole("combobox", { name: "Spacing" }).selectOption("geometric");
  await page.getByRole("button", { name: "Run backtest" }).click();

  await expect(
    page.getByRole("heading", { name: "ETHUSDT primary result" }),
  ).toBeVisible();
  await expect(page.getByText("Authoritative local record")).toBeVisible();
  const runId = await page.locator(".record code").innerText();
  await expect(page).toHaveURL(new RegExp(`/experiments/${runId}$`));

  await page.reload();
  await expect(
    page.getByRole("heading", { name: "ETHUSDT primary result" }),
  ).toBeVisible();
  await expect(page.locator(".record code")).toHaveText(runId);

  await page.getByRole("button", { name: "Operations workspace" }).click();
  await expect(page.getByText("No commands are cached or queued by this browser.")).toBeVisible();
  await expect(page.getByRole("button", { name: /pause|stop|activate/i })).toHaveCount(0);

  await page.goto("/");
  await expect(page.getByText("gridlab studio", { exact: true })).toBeVisible();
  expect(consoleErrors).toEqual([]);
});

test("operator sees manifested production-history provenance in the real browser", async ({ page }) => {
  const datasetId = "c".repeat(64);
  const fingerprint = "f".repeat(64);
  await page.route("**/api/studio/datasets/binance/preview", (route) => route.fulfill({
    contentType: "application/json",
    body: JSON.stringify({
      preview_id: "a".repeat(64), venue: "binance", market: "spot-production-archive",
      symbol: "BTCUSDT", interval: "1m", start: "2025-01-01T00:00:00Z",
      end: "2025-01-02T00:00:00Z", estimated_bytes: 123456,
      sources: [{ date: "2025-01-01", url: "https://data.binance.vision/BTCUSDT-1m-2025-01-01.zip", checksum_url: "https://data.binance.vision/BTCUSDT-1m-2025-01-01.zip.CHECKSUM", expected_sha256: "b".repeat(64), estimated_bytes: 123456 }],
    }),
  }));
  await page.route("**/api/studio/datasets/binance/import", (route) => route.fulfill({
    contentType: "application/json",
    body: JSON.stringify({ dataset_id: datasetId, history_environment: "production", source_provider: "official Binance public archive", quality: { rows: 1440, gaps: 0, duplicates: 0, out_of_order: 0, invalid_records: 0 }, normalization: { sha256: "d".repeat(64), candle_sequence_sha256: "e".repeat(64) } }),
  }));
  await page.route("**/api/studio/backtests/manifested", (route) => route.fulfill({
    status: 201, contentType: "application/json",
    body: JSON.stringify({
      id: "production-run", status: "completed", created_at: "2026-07-21T12:00:00Z", specification: { symbol: "BTCUSDT" },
      primary_result: { net_return: 0.01, final_equity: 10100, max_drawdown: -0.01, completed_trades: 2, fees_paid: 1, verdict: "Promising" },
      result: { symbol: "BTCUSDT", bars: 1440, initial_cash: 10000, final_equity: 10100, fees_paid: 1, metrics: { total_return: 0.01, max_drawdown: -0.01, n_trades: 2, win_rate: 1 }, verdict: { label: "Promising", tone: "good", score: 5, max_score: 7 }, trades: [] },
      provenance: { dataset_id: datasetId, manifest_identity: datasetId, source_provider: "official Binance public archive", history_environment: "production", testnet_history_used: false, symbol: "BTCUSDT", interval: "1m", requested_start: "2025-01-01T00:00:00Z", requested_end: "2025-01-02T00:00:00Z", retrieved_at: "2026-07-21T12:00:00Z", source_urls: [], normalized_sha256: "d".repeat(64), candle_sequence_sha256: "e".repeat(64), backtest_fingerprint: fingerprint },
    }),
  }));

  await page.goto("/studio/");
  await page.getByRole("button", { name: "Preview official download" }).click();
  await expect(page.getByText("123,456 bytes")).toBeVisible();
  await page.getByRole("button", { name: "Download, verify & normalize" }).click();
  await expect(page.getByText("QUALITY APPROVED")).toBeVisible();
  await expect(page.getByText(datasetId)).toBeVisible();
  await page.getByRole("button", { name: "Run production-history backtest" }).click();
  await expect(page.getByText("PRODUCTION HISTORY", { exact: true })).toBeVisible();
  await expect(page.getByText("TESTNET HISTORY NOT USED")).toBeVisible();
  await expect(page.getByText(fingerprint)).toBeVisible();
});
