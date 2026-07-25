import { expect, test } from "@playwright/test";

const catalogId = "9".repeat(64);

async function routeEurCatalog(page: import("@playwright/test").Page) {
  await page.route("**/api/studio/catalogs/binance/eur?refresh=*", (route) => route.fulfill({
    contentType: "application/json",
    body: JSON.stringify({
      catalog_id: catalogId,
      retrieved_at: "2026-07-23T12:00:00Z",
      quote_asset: "EUR",
      filters: ["production_and_testnet", "TRADING", "spot_allowed", "LIMIT_MAKER", "quote_asset=EUR"],
      sources: [
        { environment: "production", url: "https://data-api.binance.vision/api/v3/exchangeInfo", server_time: "2026-07-23T12:00:00Z" },
        { environment: "testnet", url: "https://testnet.binance.vision/api/v3/exchangeInfo", server_time: "2026-07-23T12:00:00Z" },
      ],
      symbols: ["BTCEUR", "ETHEUR"].map((symbol, index) => ({
        symbol,
        base_asset: symbol.slice(0, -3),
        quote_asset: "EUR",
        status: "TRADING",
        exchange_filters: {
          PRICE_FILTER: { filterType: "PRICE_FILTER", tickSize: "0.01" },
          LOT_SIZE: { filterType: "LOT_SIZE", stepSize: "0.0001" },
          NOTIONAL: { filterType: "NOTIONAL", minNotional: "5" },
        },
        coverage: {
          first_date: "2021-01-01",
          last_date: "2026-07-21",
          intervals: ["1d", "1h", "1m", "5m"],
          known_gap_dates: [],
          evidence_urls: [`https://data.binance.vision/${symbol}`],
        },
        liquidity: {
          observed_days: 30,
          observed_start_date: "2026-06-22",
          observed_end_date: "2026-07-21",
          observed_at: "2026-07-23T12:00:00Z",
          kline_source_url: `https://data-api.binance.vision/api/v3/klines?symbol=${symbol}`,
          kline_payload_sha256: "01".repeat(32),
          ticker_source_url: `https://data-api.binance.vision/api/v3/ticker/24hr?symbol=${symbol}`,
          ticker_payload_sha256: "02".repeat(32),
          median_daily_quote_volume: String(25_000_000 - index * 1_000_000),
          median_daily_trade_count: String(18_000 - index * 1000),
          annualized_realized_volatility: "0.4",
          current_spread_bps: index ? "1.75" : "2.25",
          current_trade_count: 20_000,
        },
        liquidity_rank: index + 1,
      })),
    }),
  }));
}

test("operator completes and reloads the migrated typed backtest while legacy stays available", async ({
  page,
}) => {
  await routeEurCatalog(page);
  const consoleErrors: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });

  await page.goto("/studio/");
  await expect(page.getByText("NO ONLINE TRADING AUTHORITY")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Adaptive policy characterization" })).toBeVisible();
  await expect(page.locator(".scope", { hasText: "BOOTSTRAPPING" })).toBeVisible();
  await expect(page.getByText("required_backing_inventory_not_confirmed", { exact: false })).toBeVisible();
  await expect(page.getByLabel("Initial rung ladder").getByText("BUY")).toHaveCount(3);
  await expect(page.getByLabel("Initial rung ladder").getByText("SELL")).toHaveCount(2);
  await expect(page.getByText("Ladder placement blocked", { exact: false })).toBeVisible();
  const configurationIdentity = await page.getByText("Configuration identity")
    .locator("xpath=following-sibling::code[1]").innerText();
  const observationIdentity = await page.getByText("Observation identity")
    .locator("xpath=following-sibling::code[1]").innerText();
  const eventIdentity = await page.getByText("Canonical event identity")
    .locator("xpath=following-sibling::code[1]").innerText();
  const epochIdentity = await page.getByText("Grid plan epoch identity")
    .locator("xpath=following-sibling::code[1]").innerText();
  const derivationCausation = await page.getByText("Plan derivation causation")
    .locator("xpath=following-sibling::code[1]").innerText();
  await expect(page.getByRole("navigation", { name: "Studio" })).toContainText(
    "Command Center",
  );

  await page.getByLabel("Symbol", { exact: true }).fill("ETHUSDT");
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
  await expect(page.getByText("Configuration identity")
    .locator("xpath=following-sibling::code[1]")).toHaveText(configurationIdentity);
  await expect(page.getByText("Observation identity")
    .locator("xpath=following-sibling::code[1]")).toHaveText(observationIdentity);
  await expect(page.getByText("Canonical event identity")
    .locator("xpath=following-sibling::code[1]")).toHaveText(eventIdentity);
  await expect(page.getByText("Grid plan epoch identity")
    .locator("xpath=following-sibling::code[1]")).toHaveText(epochIdentity);
  await expect(page.getByText("Plan derivation causation")
    .locator("xpath=following-sibling::code[1]")).toHaveText(derivationCausation);
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
  await routeEurCatalog(page);
  await page.route("**/api/studio/datasets/binance/preview", (route) => route.fulfill({
    contentType: "application/json",
    body: JSON.stringify({
      preview_id: "a".repeat(64), venue: "binance", market: "spot-production-archive",
      symbol: "ETHEUR", interval: "1m", start: "2025-01-01T00:00:00Z",
      end: "2025-01-02T00:00:00Z", estimated_bytes: 123456,
      limits: { max_days: 7, max_objects: 7, max_bytes: 268435456 },
      catalog_identity: catalogId,
      symbol_metadata: { base_asset: "ETH", quote_asset: "EUR", liquidity_rank: 2 },
      sources: [{ date: "2025-01-01", url: "https://data.binance.vision/ETHEUR-1m-2025-01-01.zip", checksum_url: "https://data.binance.vision/ETHEUR-1m-2025-01-01.zip.CHECKSUM", expected_sha256: "b".repeat(64), estimated_bytes: 123456 }],
    }),
  }));
  await page.route("**/api/studio/datasets/binance/import", (route) => route.fulfill({
    contentType: "application/json",
    body: JSON.stringify({ dataset_id: datasetId, manifest_sha256: "8".repeat(64), history_environment: "production", source_provider: "official Binance public archive", quality: { rows: 1440, gaps: 0, duplicates: 0, out_of_order: 0, invalid_records: 0 }, normalization: { sha256: "d".repeat(64), candle_sequence_sha256: "e".repeat(64) } }),
  }));
  await page.route("**/api/studio/backtests/manifested", (route) => route.fulfill({
    status: 201, contentType: "application/json",
    body: JSON.stringify({
      id: "production-run", status: "completed", created_at: "2026-07-21T12:00:00Z", specification: { symbol: "ETHEUR" },
      primary_result: { net_return: 0.01, final_equity: 10100, max_drawdown: -0.01, completed_trades: 2, fees_paid: 1, verdict: "Promising" },
      result: { symbol: "ETHEUR", bars: 1440, initial_cash: 10000, final_equity: 10100, fees_paid: 1, metrics: { total_return: 0.01, max_drawdown: -0.01, n_trades: 2, win_rate: 1 }, verdict: { label: "Promising", tone: "good", score: 5, max_score: 7 }, trades: [] },
      provenance: { dataset_id: datasetId, manifest_identity: datasetId, source_provider: "official Binance public archive", history_environment: "production", testnet_history_used: false, symbol: "ETHEUR", interval: "1m", requested_start: "2025-01-01T00:00:00Z", requested_end: "2025-01-02T00:00:00Z", retrieved_at: "2026-07-21T12:00:00Z", source_urls: [], normalized_sha256: "d".repeat(64), candle_sequence_sha256: "e".repeat(64), backtest_fingerprint: fingerprint, catalog_identity: catalogId, quote_asset: "EUR" },
    }),
  }));

  await page.goto("/studio/");
  await expect(page.getByText("2 eligible EUR symbols")).toBeVisible();
  await page.getByLabel("EUR production symbol").selectOption("ETHEUR");
  await expect(page.getByText("€24,000,000 median daily volume")).toBeVisible();
  await expect(page.getByText("1.75 bps current spread")).toBeVisible();
  await page.getByRole("button", { name: "Preview official download" }).click();
  await expect(page.getByText("123,456 bytes")).toBeVisible();
  await page.getByRole("button", { name: "Download, verify & normalize" }).click();
  await expect(page.getByText("QUALITY APPROVED")).toBeVisible();
  await expect(page.getByText(datasetId)).toBeVisible();
  await page.getByRole("button", { name: "Run production-history backtest" }).click();
  await expect(page.getByText("PRODUCTION HISTORY", { exact: true })).toBeVisible();
  await expect(page.getByText("TESTNET HISTORY NOT USED")).toBeVisible();
  await expect(page.getByText("10,100.00 EUR")).toBeVisible();
  await expect(page.getByText(fingerprint)).toBeVisible();
});
