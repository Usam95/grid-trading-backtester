import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { App } from "./App";
import type {
  BinanceEurResearchCatalog,
  CanonicalAdaptivePresentation,
  FrozenProductionPanel,
  OperatorControlsPresentation,
  ResearchPort,
  SafetyPosturePresentation,
  StudioBacktestRun,
  StudioConfiguration,
} from "./research/port";

const eurSymbols = [
  "ADAEUR", "APTEUR", "ATOMEUR", "AVAXEUR", "BCHEUR", "BNBEUR", "BTCEUR",
  "DOGEEUR", "DOTEUR", "EGLDEUR", "ETHEUR", "ICPEUR", "LINKEUR", "LTCEUR",
  "NEAREUR", "PEPEEUR", "POLEUR", "RENDEREUR", "SEUR", "SHIBEUR", "SOLEUR",
  "SUIEUR", "TRXEUR", "VETEUR", "WINEUR", "WLDEUR", "WLFIEUR", "XLMEUR",
  "XRPEUR",
];

const catalog: BinanceEurResearchCatalog = {
  catalog_id: "9".repeat(64),
  retrieved_at: "2026-07-23T12:00:00Z",
  quote_asset: "EUR",
  filters: [
    "production_and_testnet",
    "TRADING",
    "spot_allowed",
    "LIMIT_MAKER",
    "quote_asset=EUR",
  ],
  sources: [
    {
      environment: "production",
      url: "https://data-api.binance.vision/api/v3/exchangeInfo",
      server_time: "2026-07-23T12:00:00Z",
    },
    {
      environment: "testnet",
      url: "https://testnet.binance.vision/api/v3/exchangeInfo",
      server_time: "2026-07-23T12:00:00Z",
    },
  ],
  symbols: eurSymbols.map((symbol, index) => ({
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
      first_date: symbol === "ETHEUR" ? "2020-01-01" : "2022-01-01",
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
      median_daily_quote_volume: String(30_000_000 - index * 100_000),
      median_daily_trade_count: String(20_000 - index * 100),
      annualized_realized_volatility: "0.42",
      current_spread_bps: symbol === "ETHEUR" ? "1.75" : "2.5",
      current_trade_count: 25_000 - index * 100,
    },
    liquidity_rank: index + 1,
  })),
};

const completedRun: StudioBacktestRun = {
  id: "run-typed-001",
  status: "completed",
  created_at: "2026-07-19T12:00:00Z",
  specification: { symbol: "ETHUSDT" },
  primary_result: {
    net_return: 0.0312,
    final_equity: 10312,
    max_drawdown: -0.018,
    completed_trades: 42,
    fees_paid: 14.2,
    verdict: "Strong",
  },
  result: {
    symbol: "ETHUSDT",
    bars: 300,
    initial_cash: 10000,
    final_equity: 10312,
    fees_paid: 14.2,
    metrics: {
      total_return: 0.0312,
      max_drawdown: -0.018,
      n_trades: 42,
      win_rate: 0.62,
    },
    verdict: { label: "Strong", tone: "good", score: 6, max_score: 7 },
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
};

const preview = {
  preview_id: "a".repeat(64),
  venue: "binance" as const,
  market: "spot-production-archive" as const,
  symbol: "ETHEUR",
  interval: "1m" as const,
  start: "2025-01-01T00:00:00Z",
  end: "2025-01-02T00:00:00Z",
  estimated_bytes: 123456,
  limits: { max_days: 7, max_objects: 7, max_bytes: 268435456 },
  catalog_identity: catalog.catalog_id,
  symbol_metadata: { base_asset: "ETH", quote_asset: "EUR", liquidity_rank: 11 },
  sources: [{
    date: "2025-01-01",
    url: "https://data.binance.vision/data/spot/daily/klines/BTCUSDT/1m/BTCUSDT-1m-2025-01-01.zip",
    checksum_url: "https://data.binance.vision/data/spot/daily/klines/BTCUSDT/1m/BTCUSDT-1m-2025-01-01.zip.CHECKSUM",
    expected_sha256: "b".repeat(64),
    estimated_bytes: 123456,
  }],
};

const manifest = {
  dataset_id: "c".repeat(64),
  manifest_sha256: "8".repeat(64),
  history_environment: "production" as const,
  source_provider: "official Binance public archive",
  quality: { rows: 1440, gaps: 0, duplicates: 0, out_of_order: 0, invalid_records: 0 },
  normalization: { sha256: "d".repeat(64), candle_sequence_sha256: "e".repeat(64) },
  catalog_identity: catalog.catalog_id,
  symbol_metadata: { base_asset: "ETH", quote_asset: "EUR", liquidity_rank: 11 },
};

const panel: FrozenProductionPanel = {
  archive_id: "7".repeat(64),
  status: "ready",
  retrieved_at: "2026-07-25T12:00:00Z",
  quote_asset: "EUR",
  interval: "1m",
  symbols: ["BTCEUR", "ETHEUR", "SOLEUR", "XRPEUR", "ADAEUR", "PEPEEUR", "BNBEUR", "DOGEEUR", "XLMEUR", "LTCEUR"],
  sources: [{
    kind: "production_exchange_info",
    url: "https://data-api.binance.vision/api/v3/exchangeInfo",
    observed_at: "2026-07-25T12:00:00Z",
    identity: "1".repeat(64),
  }],
  preview: {
    preview_id: "6".repeat(64),
    source_objects: 14,
    estimated_download_bytes: 123456789,
    estimated_storage_bytes: 234567890,
    pending_partitions: 0,
    verified_partitions: 22,
    symbols: ["BTCEUR", "ETHEUR", "SOLEUR", "XRPEUR", "ADAEUR", "PEPEEUR", "BNBEUR", "DOGEEUR", "XLMEUR", "LTCEUR"].map((symbol, index) => ({
      symbol,
      dataset_id: `${index + 1}`.repeat(64),
      first_available_date: "2021-01-01",
      last_available_date: "2026-07-21",
      pending_partitions: 0,
      missing_source_objects: 0,
      estimated_download_bytes: 0,
      estimated_storage_bytes: 0,
      plans: [],
    })),
  },
  datasets: ["BTCEUR", "ETHEUR", "SOLEUR", "XRPEUR", "ADAEUR", "PEPEEUR", "BNBEUR", "DOGEEUR", "XLMEUR", "LTCEUR"].map((symbol, index) => ({
    symbol,
    dataset_id: `${index + 1}`.repeat(64),
    quote_asset: "EUR" as const,
    display_order: index + 1,
    coverage: {
      first_date: index === 0 ? "2020-01-01" : "2022-01-01",
      last_date: "2026-07-21",
      intervals: ["1d", "1h", "1m", "5m"],
      known_gap_dates: [],
      evidence_urls: [`https://data.binance.vision/coverage/${symbol}`],
    },
    verified_ranges: index === 1 ? [{
      start: "2022-01-01T00:00:00Z",
      end: "2024-01-01T00:00:00Z",
      start_open_price: "110.000000000000000000",
      end_close_price: "115.500000000000000000",
    }, {
      start: "2025-01-01T00:00:00Z",
      end: "2026-07-22T00:00:00Z",
      start_open_price: "111.000000000000000000",
      end_close_price: "118.500000000000000000",
    }] : [{
      start: "2022-01-01T00:00:00Z",
      end: "2026-07-22T00:00:00Z",
      start_open_price: "100.000000000000000000",
      end_close_price: "101.500000000000000000",
    }],
    total_rows: 2_000_000 + index,
    stored_bytes: 654321 + index,
    partitions: [{
      schema_version: "gridlab.production-archive-partition.v1",
      archive_id: "7".repeat(64),
      dataset_id: `${index + 1}`.repeat(64),
      symbol,
      quote_asset: "EUR" as const,
      interval: "1m" as const,
      month: "2026-07",
      coverage_start: "2026-07-01T00:00:00Z",
      coverage_end: "2026-07-22T00:00:00Z",
      source_kind: "daily_archives_current_month" as const,
      row_count: 30240,
      ordering: ["open_time", "source_sha256", "source_row"],
      normalization_identity: "gridlab.binance-eur-production-monthly-partition.v1",
      normalized_sha256: "d".repeat(64),
      source_urls: [`https://data.binance.vision/data/spot/daily/klines/${symbol}/1m/${symbol}-1m-2026-07-21.zip`],
      source_checksums: ["3".repeat(64)],
      timestamp_units: ["microseconds"],
      source_evidence: [],
      quality: { rows: 30240, gaps: 0, duplicates: 0, out_of_order: 0, invalid_records: 0 },
      schema: [],
      verification_status: "verified" as const,
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
};

const productionRun: StudioBacktestRun = {
  ...completedRun,
  id: "run-production-001",
  specification: {
    symbol: "ETHEUR",
    market_type: "spot",
    initial_cash: 10000,
    grid: {
      levels: 12,
      lower: 102.12,
      upper: 119.88,
      spacing: "arithmetic",
      direction: "neutral",
      adaptive: false,
      stop_loss_frac: 0.12,
    },
    sizing: { mode: "fixed_quote", value: 80 },
    fees: { maker: 0.001, taker: 0.001 },
    data: { kind: "manifested_parquet", dataset_id: panel.datasets[1].dataset_id },
    n_trials: 1,
  },
  result: {
    ...completedRun.result,
    symbol: "ETHEUR",
    bars: 1440,
    series: {
      x: [0, 1, 2, 3, 4, 5],
      timestamps: [
        "2025-01-01T00:00:00Z",
        "2025-01-01T04:00:00Z",
        "2025-01-01T08:00:00Z",
        "2025-01-01T12:00:00Z",
        "2025-01-01T16:00:00Z",
        "2025-01-01T20:00:00Z",
      ],
      price: [111, 112.4, 109.8, 115.1, 117.2, 118.5],
      equity: [10000, 10010, 10005, 10120, 10210, 10312],
      drawdown: [0, -0.002, -0.004, -0.001, -0.0005, -0.0018],
    },
    grid: {
      lower: 102.12,
      upper: 119.88,
      center: 111,
      spacing: "arithmetic",
      direction: "neutral",
      adaptive: false,
      source: "static",
      levels: [102.12, 106.56, 111.0, 115.44, 119.88],
    },
    trades: [{
      side: "LONG",
      qty: 0.72,
      entry_price: 109.8,
      exit_price: 117.2,
      pnl: 5.32,
      return_pct: 0.067,
      bars_held: 2,
      opened_at: "2025-01-01T08:00:00Z",
      closed_at: "2025-01-01T16:00:00Z",
      exit_reason: "limit",
      entry_x: 2,
      exit_x: 4,
    }],
  },
  provenance: {
    dataset_id: panel.datasets[1].dataset_id,
    manifest_identity: "8".repeat(64),
    source_provider: "official Binance public archive",
    history_environment: "production",
    testnet_history_used: false,
    symbol: "ETHEUR",
    interval: "1m",
    requested_start: "2025-01-01T00:00:00Z",
    requested_end: "2025-01-02T00:00:00Z",
    retrieved_at: "2026-07-21T12:00:00Z",
    source_urls: ["https://data.binance.vision/data/spot/daily/klines/ETHEUR/1m/ETHEUR-1m-2025-01-01.zip"],
    normalized_sha256: "d".repeat(64),
    candle_sequence_sha256: "e".repeat(64),
    backtest_fingerprint: "f".repeat(64),
    catalog_identity: catalog.catalog_id,
    candle_count: 1440,
    coverage: {
      first_verified_open_time: "2025-01-01T00:00:00Z",
      last_verified_open_time: "2025-01-01T23:59:00Z",
    },
    partition_identities: [panel.datasets[1].partitions[0].partition_id],
    quote_asset: "EUR",
  },
};

const zeroTradeProductionRun: StudioBacktestRun = {
  ...productionRun,
  id: "run-production-zero-001",
  primary_result: {
    net_return: 0,
    final_equity: 10000,
    max_drawdown: 0,
    completed_trades: 0,
    fees_paid: 0,
    verdict: "Weak",
  },
  result: {
    ...productionRun.result,
    initial_cash: 10000,
    final_equity: 10000,
    fees_paid: 0,
    metrics: {
      ...productionRun.result.metrics,
      total_return: 0,
      max_drawdown: 0,
      n_trades: 0,
      win_rate: 0,
    },
    verdict: { label: "Weak", tone: "bad", score: 1, max_score: 7 },
    trades: [],
  },
};

const configuration: StudioConfiguration = {
  default_spec: {
    symbol: "BTCUSDT",
    market_type: "spot",
    initial_cash: 10000,
    grid: {
      levels: 12,
      lower: 92,
      upper: 108,
      spacing: "arithmetic",
      direction: "neutral",
      stop_loss_frac: 0.12,
    },
    sizing: { mode: "fixed_quote", value: 80 },
    fees: { maker: 0.001, taker: 0.001 },
    data: {
      kind: "synthetic",
      n: 300,
      start_price: 100,
      seed: 7,
      sigma: 0.012,
      regime: "range",
    },
    n_trials: 1,
  },
  spacing: ["geometric", "arithmetic"],
  data_regimes: ["range", "trend", "random"],
};

const identity = (character: string) => `sha256:${character.repeat(64)}`;
const canonicalAdaptive: CanonicalAdaptivePresentation = {
  configuration: {
    schema_version: "strategy-configuration/v1",
    configuration_id: identity("1"),
    policy_id: identity("2"),
    symbol: "BTCEUR",
    base_asset: "BTC",
    quote_asset: "EUR",
    rung_count: 5,
    spacing: "GEOMETRIC",
    execution_policy_id: "limit-maker-ordinary/v1",
    risk_profile_id: "mvp1-first-live-ceilings/v1",
    operator_inputs: {
      fixed_quote_principal: { kind: "quote_quantity", value: "20.00" },
      maker_fee: { kind: "fee_rate", value: "0.0010" },
      maximum_quote_capital: { kind: "quote_quantity", value: "250.00" },
      fee_reserve: { kind: "quote_quantity", value: "5.00" },
      stop_price: { kind: "price", value: "80.00" },
      lower_bound_limit: { kind: "price", value: "85.00" },
      upper_bound_limit: { kind: "price", value: "120.00" },
    },
  },
  observation: {
    schema_version: "adaptation-observation/v1",
    observation_id: identity("3"),
    event_id: identity("4"),
    source_system: "legacy-backtest-translation",
    source_stream: "BTCEUR:synthetic:7",
    event_time: "2025-01-02T00:00:00Z",
    decision_time: "2025-01-02T00:00:00Z",
    complete: true,
    quality: "ADMITTED",
    confirmation_ids: [identity("8"), identity("9")],
    prior_decision_id: null,
    trend: { kind: "ratio", value: "0.0000" },
    volatility: { kind: "ratio", value: "0.0100" },
    reference_price: { kind: "price", value: "100.00" },
  },
  decision: {
    decision_id: identity("5"),
    adaptation_state: "RANGE_NORMAL",
    intent: "SYMMETRIC",
    reason: "qualified_sideways_range",
    permits_exposure_increasing_buy: true,
    requested_bound_shift: null,
  },
  activation: {
    schema_version: "initial-epoch-activation/v1",
    lifecycle: "BOOTSTRAPPING",
    replay_fingerprint: identity("a"),
    ladder_placement_allowed: false,
    activation_pending: false,
    automatically_armed: false,
    derived_width: { kind: "ratio", value: "0.0400" },
    gates: [
      {
        name: "quality_approved_past_only_evidence",
        outcome: "PASSED",
        reason: "qualified_sideways_range",
      },
      {
        name: "activation_price_strictly_inside_bounds",
        outcome: "PASSED",
        reason: "activation_price_inside_derived_bounds",
      },
      {
        name: "capital_and_fee_coverage",
        outcome: "PASSED",
        reason: "planned_obligations_fit_capital_envelope",
      },
      {
        name: "bootstrap_inventory_complete",
        outcome: "BLOCKED",
        reason: "required_backing_inventory_not_confirmed",
      },
    ],
    bootstrap_evidence: {
      complete: false,
      net_base_confirmed: { kind: "base_quantity", value: "0" },
      evidence_id: null,
    },
    admission_context: {
      still_effective_quote_commitment: { kind: "quote_quantity", value: "0" },
      still_effective_inventory_commitment: { kind: "base_quantity", value: "0" },
      still_effective_order_count: 0,
    },
    admission_assessment: {
      capital_envelope: { kind: "quote_quantity", value: "250.00" },
      still_effective_quote_commitment: { kind: "quote_quantity", value: "0" },
      proposed_quote_commitment: { kind: "quote_quantity", value: "98.8870000" },
      bootstrap_quote_commitment: { kind: "quote_quantity", value: "38.8870000" },
      total_quote_commitment: { kind: "quote_quantity", value: "98.8870000" },
      fee_reserve: { kind: "quote_quantity", value: "5.00" },
      still_effective_inventory_commitment: { kind: "base_quantity", value: "0" },
      additional_bootstrap_inventory: { kind: "base_quantity", value: "0.38886" },
      maximum_planned_inventory: { kind: "base_quantity", value: "1.00116" },
      total_worst_case_inventory: { kind: "base_quantity", value: "1.00116" },
      still_effective_order_count: 0,
      proposed_order_count: 5,
      total_order_count: 5,
      venue_order_capacity: null,
      foreign_open_orders: 0,
    },
    adjacent_cycle_economics: [
      {
        buy_rung_index: 2,
        sell_rung_index: 3,
        buy_price: { kind: "price", value: "99.92" },
        sell_price: { kind: "price", value: "101.95" },
        cycle_quantity: { kind: "base_quantity", value: "0.19995" },
        net_margin: { kind: "quote_quantity", value: "0.1658111900" },
        positive: true,
        reason: "adjacent_cycle_positive_after_fees_rounding_allowance_and_margin",
      },
    ],
    principal_feasibility: {
      schema_version: "principal-feasibility-report/v1",
      points: [
        {
          principal: { kind: "quote_quantity", value: "10" },
          feasible: true,
          reasons: [],
        },
        {
          principal: { kind: "quote_quantity", value: "20" },
          feasible: true,
          reasons: [],
        },
      ],
    },
    post_only_retry_policy: {
      schema_version: "post-only-retry-policy/v1",
      order_type: "LIMIT_MAKER",
      max_attempts: 3,
      retry_delays: [
        { kind: "duration_seconds", value: "0.25" },
        { kind: "duration_seconds", value: "1" },
      ],
      max_price_displacement_ratio: { kind: "ratio", value: "0.0025" },
      max_adjacent_gap_fraction: { kind: "ratio", value: "0.25" },
      exhaustion_posture: "REDUCE_ONLY",
    },
    rule_fee_contract: {
      schema_version: "rule-fee-contract/v1",
      contract_id: identity("contract"),
      venue_rule_evidence_id: identity("7"),
      maker_fee: { kind: "fee_rate", value: "0.0010" },
      taker_fee: { kind: "fee_rate", value: "0.0010" },
    },
  },
  derived_plan: {
    schema_version: "grid-plan/v1",
    epoch_id: identity("6"),
    predecessor_epoch_id: null,
    derivation_causation_id: identity("4"),
    derivation_semantics: "bounded-symmetric-geometric/v1",
    venue_rule_evidence_id: identity("7"),
    lower: { kind: "price", value: "96.000000" },
    upper: { kind: "price", value: "104.000000" },
    reference_price: { kind: "price", value: "100.00" },
    activation_price: { kind: "price", value: "100.00" },
    unquantized_rungs: [
      { kind: "price", value: "96.000000" },
      { kind: "price", value: "97.941125496954281171240529379361208784543249014745" },
      { kind: "price", value: "99.921537826482739726869338565769719813532289400057" },
      { kind: "price", value: "101.94199907753713939235021015220813827736184800424" },
      { kind: "price", value: "104.000000" },
    ],
    quantized_rungs: [
      { index: 0, price: { kind: "price", value: "96.00" }, role: "BUY" },
      { index: 1, price: { kind: "price", value: "97.94" }, role: "BUY" },
      { index: 2, price: { kind: "price", value: "99.92" }, role: "BUY" },
      { index: 3, price: { kind: "price", value: "101.95" }, role: "SELL" },
      { index: 4, price: { kind: "price", value: "104.00" }, role: "SELL" },
    ],
    obligations: [
      { rung_index: 0, role: "BUY", fixed_quote_principal: { kind: "quote_quantity", value: "20.00" }, base_quantity: { kind: "base_quantity", value: "0.20833" } },
      { rung_index: 1, role: "BUY", fixed_quote_principal: { kind: "quote_quantity", value: "20.00" }, base_quantity: { kind: "base_quantity", value: "0.20420" } },
      { rung_index: 2, role: "BUY", fixed_quote_principal: { kind: "quote_quantity", value: "20.00" }, base_quantity: { kind: "base_quantity", value: "0.20016" } },
      { rung_index: 3, role: "SELL", fixed_quote_principal: { kind: "quote_quantity", value: "20.00" }, base_quantity: { kind: "base_quantity", value: "0.19617" } },
      { rung_index: 4, role: "SELL", fixed_quote_principal: { kind: "quote_quantity", value: "20.00" }, base_quantity: { kind: "base_quantity", value: "0.19230" } },
    ],
    allocation_assumptions: {
      quote_allocation: { kind: "quote_quantity", value: "98.8870000" },
      base_allocation: { kind: "base_quantity", value: "0.00000" },
      fee_reserve: { kind: "quote_quantity", value: "5.00" },
    },
    maximum_planned_inventory: { kind: "base_quantity", value: "1.00116" },
    bootstrap_obligation: {
      net_base_required: { kind: "base_quantity", value: "0.38847" },
      gross_base_required: { kind: "base_quantity", value: "0.38886" },
      fee_base_coverage: { kind: "base_quantity", value: "0.00039" },
    },
  },
  legacy_comparison: {
    bounded_bars: 120,
    legacy_adaptive: true,
    legacy_spacing: "geometric",
    effective_atr_multiplier: "2.0",
    cancelled_orders: 64,
    semantic_differences: [
      "canonical policy does not inherit the legacy nonzero atr_mult default",
      "canonical seam emits no immediate cancel-all/rebuild transition",
      "canonical classification fails closed on incomplete or ambiguous evidence",
      "canonical characterization applies the MVP 250.00 EUR capital envelope instead of the legacy 1000.0 initial cash",
      "canonical venue-rule evidence is an explicit translation assumption absent from the legacy backtest",
    ],
  },
};

const safetyPosture: SafetyPosturePresentation = {
  schema_version: "safety-posture-presentation/v1",
  decision_time: "2025-01-02T12:00:00Z",
  fingerprint: identity("f"),
  capital: {
    allocation_fingerprint: identity("a"),
    epoch_id: identity("e"),
    capital_envelope: { kind: "quote_quantity", value: "250.00" },
    committed_principal: { kind: "quote_quantity", value: "220.00" },
    fee_reserve: { kind: "quote_quantity", value: "8.00" },
    maximum_planned_inventory: { kind: "base_quantity", value: "1.00" },
  },
  lifecycle: {
    grid_lifecycle: "RANGE_EXHAUSTED",
    adaptation_state: "TREND_DOWN",
    epoch_transition_state: "IDLE",
    runtime_lifecycle: "OPERATING",
    reconciliation_state: "RECONCILED",
  },
  safety: {
    posture: "REDUCE_ONLY",
    reason_codes: ["confirmed_downtrend", "range_exhausted", "symbol_delisting_wind_down"],
    loss_warning: false,
    daily_loss_latched: false,
    run_drawdown_latched: false,
    global_stop_latched: false,
    allowed_command_classes: ["CANCELLATION", "EVIDENCE_GATHERING", "INVENTORY_REDUCING", "RECONCILIATION", "REPLACEMENT"],
    placement_allowed: false,
    replacement_allowed: true,
    downward_bound_shift_allowed: false,
    fixed_quote_sizing_increase_allowed: false,
    clock_offset: { kind: "duration_seconds", value: "0.050" },
    scheduling_delay: { kind: "duration_seconds", value: "0.025000" },
    round_trip_latency: { kind: "duration_seconds", value: "0.200000" },
  },
  freshness: [
    "CLOCK", "CONTROL_PATH", "PRIVATE_STREAM", "STRATEGY_INPUT", "VALUATION",
  ].map((evidence_class) => ({
    evidence_class: evidence_class as "CLOCK",
    condition: "HEALTHY" as const,
    observed_at: "2025-01-02T11:59:59Z",
    evidence_id: identity(evidence_class[0].toLowerCase()),
  })),
  venue: {
    condition: "DELISTING",
    evidence_id: identity("d"),
    source: "bounded-ticket-09-fixture",
    wind_down_deadline: "2025-01-09T12:00:00Z",
  },
};

const operatorControls: OperatorControlsPresentation = {
  schema_version: "operator-controls-presentation/v1",
  decision_time: "2025-01-02T12:05:00Z",
  fingerprint: identity("o"),
  projection: {
    active_epoch_id: identity("e"),
    proposed_epoch_id: identity("f"),
    transition_state: "ACTIVATION_PENDING",
    posture: "NORMAL",
  },
  inventory_basis: {
    basis_id: identity("9"),
    source: "reconciliation-ledger",
    base_asset: "BTC",
    quantity: { kind: "base_quantity", value: "0.80000000" },
    authoritative: true,
    reconciled_at: "2025-01-02T12:05:00Z",
  },
  pause: {
    action: "PAUSE",
    availability: "LATCHED",
    confirmation_required: false,
    environment_bound: true,
    idempotent: true,
    preempts_pending_activation: true,
    blocks_new_epoch_placement: true,
    admission_order_preserved: true,
    active_epoch_id: identity("e"),
    proposed_epoch_id: identity("f"),
    transition_state: "ACTIVATION_PENDING",
    posture: "NORMAL",
    inventory_basis_id: identity("9"),
    cancel_obligation_ids: [identity("a"), identity("b")],
    retained_obligation_ids: [identity("c")],
    late_fill_ids: [],
    gates: [],
    reason_codes: ["pause_blocks_exposure_increasing_buys"],
    available_dispositions: [],
    selected_disposition: null,
  },
  resume: {
    action: "RESUME",
    availability: "BLOCKED",
    confirmation_required: true,
    environment_bound: true,
    idempotent: true,
    preempts_pending_activation: true,
    blocks_new_epoch_placement: true,
    admission_order_preserved: true,
    active_epoch_id: identity("e"),
    proposed_epoch_id: identity("f"),
    transition_state: "ACTIVATION_PENDING",
    posture: "NORMAL",
    inventory_basis_id: identity("9"),
    cancel_obligation_ids: [],
    retained_obligation_ids: [identity("c")],
    late_fill_ids: [],
    gates: [
      { name: "current_evidence", outcome: "FAILED", reason: "current authoritative evidence is required" },
      { name: "reconciliation", outcome: "FAILED", reason: "resume requires reconciled authoritative inventory" },
      { name: "command_authority", outcome: "FAILED", reason: "resume requires an authenticated command path" },
    ],
    reason_codes: ["current_evidence", "reconciliation", "command_authority"],
    available_dispositions: [],
    selected_disposition: null,
  },
  operator_stop: {
    action: "OPERATOR_STOP",
    availability: "PREVIEW_REQUIRED",
    confirmation_required: true,
    environment_bound: true,
    idempotent: true,
    preempts_pending_activation: true,
    blocks_new_epoch_placement: true,
    admission_order_preserved: true,
    active_epoch_id: identity("e"),
    proposed_epoch_id: identity("f"),
    transition_state: "ACTIVATION_PENDING",
    posture: "NORMAL",
    inventory_basis_id: identity("9"),
    cancel_obligation_ids: [identity("a"), identity("b"), identity("c")],
    retained_obligation_ids: [],
    late_fill_ids: [identity("7")],
    gates: [
      { name: "explicit_disposition", outcome: "PASSED", reason: "operator stop requires an explicit retained-holding or disposal disposition" },
    ],
    reason_codes: ["operator_stop_reconciles_late_fills"],
    available_dispositions: ["RETAIN_HOLDING", "DISPOSE"],
    selected_disposition: "DISPOSE",
  },
  emergency_stop: {
    action: "EMERGENCY_STOP",
    availability: "IMMEDIATE",
    confirmation_required: false,
    environment_bound: true,
    idempotent: true,
    preempts_pending_activation: true,
    blocks_new_epoch_placement: true,
    admission_order_preserved: true,
    active_epoch_id: identity("e"),
    proposed_epoch_id: identity("f"),
    transition_state: "ACTIVATION_PENDING",
    posture: "NORMAL",
    inventory_basis_id: identity("9"),
    cancel_obligation_ids: [identity("a"), identity("b"), identity("c")],
    retained_obligation_ids: [],
    late_fill_ids: [],
    gates: [],
    reason_codes: ["operator_emergency_stop_immediately_available"],
    available_dispositions: [],
    selected_disposition: null,
  },
  terminal: {
    trigger: "NONE",
    state: "DISPOSED",
    global_stop_latched: false,
    operator_emergency_latched: false,
    automatic_liquidation: false,
    preempts_pending_activation: false,
    admission_order_preserved: true,
    active_epoch_id: identity("e"),
    proposed_epoch_id: identity("f"),
    transition_state: "ACTIVATION_PENDING",
    posture: "NORMAL",
    inventory_basis_id: identity("9"),
    waves: [
      {
        wave: 1,
        order_type: "IOC",
        quantity_limit: { kind: "base_quantity", value: "0.50000000" },
        notional_limit: { kind: "quote_quantity", value: "50.00" },
        max_depth_age: { kind: "duration_seconds", value: "3.000000" },
        price_band_bps: { kind: "basis_points", value: "35" },
        attempt_limit: 2,
        elapsed_time_limit: { kind: "duration_seconds", value: "15.000000" },
        outcome: "PARTIAL",
        reconciled_before_next_wave: true,
        authoritative_inventory_after_wave: { kind: "base_quantity", value: "0.30000000" },
      },
      {
        wave: 2,
        order_type: "IOC",
        quantity_limit: { kind: "base_quantity", value: "0.30000000" },
        notional_limit: { kind: "quote_quantity", value: "30.00" },
        max_depth_age: { kind: "duration_seconds", value: "3.000000" },
        price_band_bps: { kind: "basis_points", value: "45" },
        attempt_limit: 3,
        elapsed_time_limit: { kind: "duration_seconds", value: "20.000000" },
        outcome: "COMPLETED",
        reconciled_before_next_wave: true,
        authoritative_inventory_after_wave: { kind: "base_quantity", value: "0.00000000" },
      },
    ],
    golden_replay_cases: [
      "GAP_THROUGH",
      "PARTIAL_DISPOSAL",
      "REJECTION",
      "UNKNOWN_OUTCOME",
      "ATTEMPT_EXHAUSTION",
      "RESIDUAL_HOLDINGS",
    ].map((case_name, index) => ({
      case_name: case_name as "GAP_THROUGH",
      outcome: `fixture ${index + 1}`,
      replay_fingerprint: identity(String(index + 1)),
    })),
  },
};


function researchPort(): ResearchPort {
  return {
    getConfiguration: vi.fn().mockResolvedValue(configuration),
    getEurCatalog: vi.fn().mockResolvedValue(catalog),
    getProductionArchive: vi.fn().mockResolvedValue(panel),
    synchronizeProductionArchive: vi.fn().mockResolvedValue(panel),
    characterizeCanonicalAdaptive: vi.fn().mockResolvedValue(canonicalAdaptive),
    getSafetyPosture: vi.fn().mockResolvedValue(safetyPosture),
    getOperatorControls: vi.fn().mockResolvedValue(operatorControls),
    executeBacktest: vi.fn().mockResolvedValue(completedRun),
    getBacktest: vi.fn().mockResolvedValue(completedRun),
    previewProductionDataset: vi.fn().mockResolvedValue(preview),
    importProductionDataset: vi.fn().mockResolvedValue(manifest),
    executeManifestedBacktest: vi.fn().mockResolvedValue(productionRun),
    executeProductionArchiveBacktest: vi.fn().mockResolvedValue(productionRun),
  };
}


describe("typed Studio shell", () => {
  it("keeps the trust boundary and permanent navigation visible", () => {
    render(<App research={researchPort()} />);

    expect(screen.getByText("RESEARCH")).toBeTruthy();
    expect(screen.getByText("LOCAL")).toBeTruthy();
    expect(screen.getByText("NO ONLINE TRADING AUTHORITY")).toBeTruthy();
    expect(screen.getByRole("navigation", { name: "Studio" }).textContent).toContain("Experiments");
    expect(screen.getByRole("navigation", { name: "Studio" }).textContent).toContain("Command Center");
  });

  it("configures and executes the migrated backtest through the Research port", async () => {
    const research = researchPort();
    render(<App research={research} />);

    fireEvent.click(await screen.findByRole("button", { name: /experiment quickly with synthetic data/i }));
    expect(await screen.findByText("Try the strategy with fast synthetic data")).toBeTruthy();
    expect(screen.getByText("Market & scenario")).toBeTruthy();
    expect(screen.getByText("Grid setup")).toBeTruthy();
    expect(screen.getByText("Costs")).toBeTruthy();
    expect(screen.getByText("Safety limits")).toBeTruthy();

    fireEvent.change(screen.getByLabelText("Symbol"), {
      target: { value: "ETHUSDT" },
    });

    fireEvent.click(screen.getByRole("button", { name: "Run synthetic backtest" }));

    await waitFor(() => expect(research.executeBacktest).toHaveBeenCalledOnce());
    expect(screen.getByText("+3.12%")).toBeTruthy();
    expect(screen.getByText("10,312.00 USDT")).toBeTruthy();
    expect(screen.getByText("run-typed-001")).toBeTruthy();
    expect(screen.getByText("Show simulation caveats")).toBeTruthy();
  });

  it("presents the obligation-backed adaptive initial epoch and activation gates", async () => {
    render(<App research={researchPort()} />);

    expect(await screen.findByText("Why this starting grid was suggested")).toBeTruthy();
    expect(screen.getByText("RANGE_NORMAL")).toBeTruthy();
    expect(screen.getByText("Needs confirmation")).toBeTruthy();
    expect(screen.getAllByText("qualified_sideways_range").length).toBeGreaterThan(0);
    expect(screen.getAllByText("required_backing_inventory_not_confirmed", { exact: false }).length).toBeGreaterThan(0);
    expect(screen.getByText("0.38886 BTC gross backing inventory")).toBeTruthy();
    expect(screen.getByText("Show detailed decision evidence")).toBeTruthy();
  });

  it("presents separate safety facts without implying command authority", async () => {
    render(<App research={researchPort()} />);

    fireEvent.click(screen.getByRole("button", { name: "Operations workspace" }));

    expect(screen.getByText("OPERATIONS")).toBeTruthy();
    expect(screen.getAllByText("GATEWAY NOT CONFIGURED")).toHaveLength(2);
    expect(screen.getAllByText("COMMAND AUTHORITY UNAVAILABLE")).toHaveLength(2);
    expect(await screen.findByText("Safety and venue evidence")).toBeTruthy();
    expect(screen.getAllByText("REDUCE_ONLY")).toHaveLength(2);
    expect(screen.getByText("RANGE_EXHAUSTED")).toBeTruthy();
    expect(screen.getByText("TREND_DOWN")).toBeTruthy();
    expect(screen.getByText("IDLE")).toBeTruthy();
    expect(screen.getByText("OPERATING")).toBeTruthy();
    expect(screen.getByText("RECONCILED")).toBeTruthy();
    expect(screen.getByText("DELISTING", { exact: false })).toBeTruthy();
    expect(screen.getByText("2025-01-09T12:00:00.000Z")).toBeTruthy();
    expect(await screen.findByText("Operate controls and terminal disposal")).toBeTruthy();
    expect(screen.getByText("ACTIVATION_PENDING")).toBeTruthy();
    expect(screen.getByText(/0\.80000000[\s\S]*reconciliation-ledger/i)).toBeTruthy();
    expect(screen.getByText(/cancel 2 obligations · retain 1/i)).toBeTruthy();
    expect(screen.getByText(/PREVIEW_REQUIRED · DISPOSE · 1 late fills admitted/i)).toBeTruthy();
    expect(screen.queryByRole("button", { name: /pause|resume|stop|emergency/i })).toBeNull();
  });

  it("runs synchronized production-history snapshots with explicit provenance", async () => {
    const research = researchPort();
    render(<App research={research} />);

    expect(await screen.findByText("Run over local EUR market history")).toBeTruthy();
    expect(await screen.findByText("Local datasets ready")).toBeTruthy();
    fireEvent.change(screen.getByLabelText("EUR production symbol"), {
      target: { value: "ETHEUR" },
    });
    expect(screen.getByText("Stable local dataset · EUR quote asset · verified Spot production replay only.")).toBeTruthy();
    fireEvent.change(screen.getByLabelText("Verified local range"), {
      target: { value: "1" },
    });
    expect(screen.getByText("Replay-start price")).toBeTruthy();
    expect(screen.getAllByText("111.00 EUR").length).toBeGreaterThan(0);
    expect((screen.getByLabelText("Lower bound") as HTMLInputElement).value).toBe("102.12");
    expect((screen.getByLabelText("Upper bound") as HTMLInputElement).value).toBe("119.88");
    fireEvent.click(screen.getByRole("button", { name: "Run production-history backtest" }));
    expect(await screen.findByText("Show technical provenance")).toBeTruthy();
    expect(screen.getByText("Price path, grid, and executed trades")).toBeTruthy();
    expect(screen.getByLabelText("Replay price path with grid levels and executed trades")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Zoom in replay chart" })).toBeTruthy();
    expect(screen.getByText("Visible points: 6 / 6 · Drag to pan · Wheel to zoom")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Zoom in replay chart" }));
    expect(screen.getByText("Visible points: 4 / 6 · Drag to pan · Wheel to zoom")).toBeTruthy();
    expect(research.executeProductionArchiveBacktest).toHaveBeenCalledOnce();
    expect(screen.getByText("10,312.00 EUR")).toBeTruthy();
    expect(research.executeProductionArchiveBacktest).toHaveBeenCalledWith({
      dataset_id: panel.datasets[1].dataset_id,
      start: "2025-01-01T00:00:00Z",
      end: "2026-07-22T00:00:00Z",
      spec: expect.objectContaining({
        symbol: "ETHEUR",
        data: { kind: "manifested_parquet", dataset_id: panel.datasets[1].dataset_id },
      }),
      options: {
        include_trades: true,
        with_report: false,
      },
    });
  });

  it("explains zero-trade production runs using the submitted grid configuration", async () => {
    const research = {
      ...researchPort(),
      executeProductionArchiveBacktest: vi.fn().mockResolvedValue(zeroTradeProductionRun),
    };
    render(<App research={research} />);

    expect(await screen.findByText("Run over local EUR market history")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Run production-history backtest" }));

    expect(await screen.findByText("NO ORDER FILLS WERE RECORDED")).toBeTruthy();
    expect(screen.getByText(/this submitted grid never executed a fill/i)).toBeTruthy();
    expect(screen.getByText("Submitted bounds")).toBeTruthy();
    expect(screen.getByText("102.12 → 119.88 EUR")).toBeTruthy();
    expect(screen.getAllByText(/12 rung prices · arithmetic spacing/i).length).toBeGreaterThan(0);
  });

  it("exposes the synchronized ten-symbol EUR production archive in Studio", async () => {
    const research = researchPort();
    render(<App research={research} />);

    expect(await screen.findByText("Run over local EUR market history")).toBeTruthy();
    expect(screen.getByText("Eligible EUR symbols")).toBeTruthy();
    expect(screen.getByText("Estimated local storage")).toBeTruthy();
    expect(screen.getByText("Refresh local archive status")).toBeTruthy();
    expect(research.getProductionArchive).toHaveBeenCalledOnce();
  });

  it("keeps catalog symbols visible and exposes synchronization when the local archive is empty", async () => {
    const emptyPanel: FrozenProductionPanel = {
      ...panel,
      status: "pending",
      symbols: [],
      datasets: [],
      preview: { ...panel.preview, symbols: [], pending_partitions: 1, verified_partitions: 0 },
    };
    const research = {
      ...researchPort(),
      getProductionArchive: vi.fn().mockResolvedValue(emptyPanel),
    };
    render(<App research={research} />);

    expect(await screen.findByText("Run over local EUR market history")).toBeTruthy();
    expect(screen.getByRole("option", { name: /ADAEUR · local archive pending/i })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Synchronize local archive" })).toBeTruthy();
    expect(screen.getByText(/No verified local range is available until the archive is synchronized/i)).toBeTruthy();
  });
});
