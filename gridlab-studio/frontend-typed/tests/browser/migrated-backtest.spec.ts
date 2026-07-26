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

async function routeProductionPanel(page: import("@playwright/test").Page) {
  await page.route("**/api/studio/archives/binance/eur?refresh=*", (route) => route.fulfill({
    contentType: "application/json",
    body: JSON.stringify({
      archive_id: "7".repeat(64),
      status: "ready",
      retrieved_at: "2026-07-25T12:00:00Z",
      quote_asset: "EUR",
      interval: "1m",
      symbols: ["BTCEUR", "ETHEUR", "SOLEUR", "XRPEUR", "ADAEUR", "PEPEEUR", "BNBEUR", "DOGEEUR", "XLMEUR", "LTCEUR"],
      sources: [{ kind: "production_exchange_info", url: "https://data-api.binance.vision/api/v3/exchangeInfo", observed_at: "2026-07-25T12:00:00Z", identity: "1".repeat(64) }],
      preview: { preview_id: "6".repeat(64), source_objects: 14, estimated_download_bytes: 123456789, estimated_storage_bytes: 234567890, pending_partitions: 0, verified_partitions: 10, symbols: [] },
      datasets: ["BTCEUR", "ETHEUR", "SOLEUR", "XRPEUR", "ADAEUR", "PEPEEUR", "BNBEUR", "DOGEEUR", "XLMEUR", "LTCEUR"].map((symbol, index) => ({
        symbol,
        dataset_id: `${index + 1}`.repeat(64),
        quote_asset: "EUR",
        display_order: index + 1,
        coverage: {
          first_date: "2022-01-01",
          last_date: "2026-07-21",
          intervals: ["1d", "1h", "1m", "5m"],
          known_gap_dates: [],
          evidence_urls: [`https://data.binance.vision/coverage/${symbol}`],
        },
        verified_ranges: [{
          start: "2022-01-01T00:00:00Z",
          end: "2026-07-22T00:00:00Z",
          start_open_price: "100.000000000000000000",
          end_close_price: "101.500000000000000000",
        }],
        total_rows: 2_000_000,
        stored_bytes: 654321 + index,
        partitions: [{
          schema_version: "gridlab.production-archive-partition.v1",
          archive_id: "7".repeat(64),
          dataset_id: `${index + 1}`.repeat(64),
          symbol,
          quote_asset: "EUR",
          interval: "1m",
          month: "2026-07",
          coverage_start: "2026-07-01T00:00:00Z",
          coverage_end: "2026-07-22T00:00:00Z",
          source_kind: "daily_archives_current_month",
          row_count: 30240,
          ordering: ["open_time", "source_sha256", "source_row"],
          normalization_identity: "gridlab.binance-eur-production-monthly-partition.v1",
          normalized_sha256: "d".repeat(64),
          source_urls: [`https://data.binance.vision/${symbol}-1m-2026-07-21.zip`],
          source_checksums: ["3".repeat(64)],
          timestamp_units: ["microseconds"],
          source_evidence: [],
          quality: { rows: 30240, gaps: 0, duplicates: 0, out_of_order: 0, invalid_records: 0 },
          schema: [],
          verification_status: "verified",
          active: true,
          gap_findings: [],
          correction_findings: [],
          sequence_sha256: "e".repeat(64),
          partition_id: `${index + 2}`.repeat(64),
          path: `C:\\repo\\${symbol}\\data.parquet`,
          manifest_path: `C:\\repo\\${symbol}\\manifest.json`,
          byte_size: 654321 + index,
          manifest_identity: "5".repeat(64),
        }],
        pending_partition_months: [],
      })),
      blocking_reasons: [],
    }),
  }));
}

test("operator completes and reloads the migrated typed backtest while legacy stays available", async ({
  page,
}) => {
  await routeEurCatalog(page);
  await routeProductionPanel(page);
  const consoleErrors: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });

  await page.goto("/studio/");
  await expect(page.getByText("NO ONLINE TRADING AUTHORITY")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Choose how you want to test the strategy" })).toBeVisible();
  await page.getByText("See why the system suggests a certain starting grid").click();
  await expect(page.getByRole("heading", { name: "Why this starting grid was suggested" })).toBeVisible();
  await expect(page.locator(".scope", { hasText: "BOOTSTRAPPING" })).toBeVisible();
  await expect(page.getByText("Needs confirmation")).toBeVisible();
  await expect(page.getByText("Show detailed decision evidence")).toBeVisible();
  await page.getByText("Show detailed decision evidence").click();
  await expect(page.getByText("bootstrap_inventory_complete: required_backing_inventory_not_confirmed")).toBeVisible();
  await expect(page.getByLabel("Initial rung ladder").getByText("BUY")).toHaveCount(3);
  await expect(page.getByLabel("Initial rung ladder").getByText("SELL")).toHaveCount(2);
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

  await page.getByRole("button", { name: /experiment quickly with synthetic data/i }).click();
  await page.getByLabel("Symbol", { exact: true }).fill("ETHUSDT");
  await page.getByLabel("Synthetic bars").fill("300");
  await page.getByRole("combobox", { name: "Spacing" }).selectOption("geometric");
  await page.getByRole("button", { name: "Run synthetic backtest" }).click();

  await expect(
    page.getByRole("heading", { name: "ETHUSDT result" }),
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
    page.getByRole("heading", { name: "ETHUSDT result" }),
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
  await routeProductionPanel(page);
  await page.route("**/api/studio/backtests/production-archive", (route) => route.fulfill({
    status: 201, contentType: "application/json",
    body: JSON.stringify({
      id: "production-run", status: "completed", created_at: "2026-07-21T12:00:00Z", specification: { symbol: "ETHEUR" },
      primary_result: { net_return: 0.01, final_equity: 10100, max_drawdown: -0.01, completed_trades: 2, fees_paid: 1, verdict: "Promising" },
      result: { symbol: "ETHEUR", bars: 1440, initial_cash: 10000, final_equity: 10100, fees_paid: 1, metrics: { total_return: 0.01, max_drawdown: -0.01, n_trades: 2, win_rate: 1 }, verdict: { label: "Promising", tone: "good", score: 5, max_score: 7 }, trades: [], simulation: { mode: "candle", canonical_core: false, venue_execution_proof: false, limitations: ["Normal orders become eligible only from the candle after they begin resting."] } },
      provenance: { dataset_id: "2".repeat(64), manifest_identity: "8".repeat(64), source_provider: "official Binance public archive", history_environment: "production", testnet_history_used: false, symbol: "ETHEUR", interval: "1m", requested_start: "2025-01-01T00:00:00Z", requested_end: "2025-01-02T00:00:00Z", retrieved_at: "2026-07-21T12:00:00Z", source_urls: [], normalized_sha256: "d".repeat(64), candle_sequence_sha256: "e".repeat(64), backtest_fingerprint: fingerprint, candle_count: 1440, coverage: { first_verified_open_time: "2025-01-01T00:00:00Z", last_verified_open_time: "2025-01-01T23:59:00Z" }, partition_identities: ["3".repeat(64)], catalog_identity: catalogId, quote_asset: "EUR" },
    }),
  }));
  await page.route("**/api/studio/archives/binance/eur/synchronize", (route) => route.fulfill({
    contentType: "application/json",
    body: JSON.stringify({
      archive_id: "7".repeat(64),
      status: "ready",
      retrieved_at: "2026-07-25T12:00:00Z",
      quote_asset: "EUR",
      interval: "1m",
      symbols: ["BTCEUR", "ETHEUR", "SOLEUR", "XRPEUR", "ADAEUR", "PEPEEUR", "BNBEUR", "DOGEEUR", "XLMEUR", "LTCEUR"],
      sources: [{ kind: "production_exchange_info", url: "https://data-api.binance.vision/api/v3/exchangeInfo", observed_at: "2026-07-25T12:00:00Z", identity: "1".repeat(64) }],
      preview: { preview_id: "6".repeat(64), source_objects: 0, estimated_download_bytes: 0, estimated_storage_bytes: 0, pending_partitions: 0, verified_partitions: 10, symbols: [] },
      datasets: [],
      blocking_reasons: [],
    }),
  }));

  await page.goto("/studio/");
  await expect(page.getByRole("heading", { name: "Run over local EUR market history" })).toBeVisible();
  await expect(page.getByText("Eligible EUR symbols")).toBeVisible();
  await expect(page.getByText("Local datasets ready")).toBeVisible();
  await page.getByLabel("EUR production symbol").selectOption("ETHEUR");
  await expect(page.getByText("Stable local dataset · EUR quote asset · verified Spot production replay only.")).toBeVisible();
  await expect(page.getByLabel("Verified local range")).toBeVisible();
  await page.getByRole("button", { name: "Run production-history backtest" }).click();
  await expect(page.getByText("Show technical provenance")).toBeVisible();
  await expect(page.getByText("10,100.00 EUR")).toBeVisible();
  await page.getByText("Show technical provenance").click();
  await expect(page.getByText("TESTNET HISTORY NOT USED")).toBeVisible();
  await expect(page.getByText(fingerprint)).toBeVisible();
});
