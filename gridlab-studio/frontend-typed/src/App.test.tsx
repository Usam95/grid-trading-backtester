import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { App } from "./App";
import type {
  BinanceEurResearchCatalog,
  CanonicalAdaptivePresentation,
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

const productionRun: StudioBacktestRun = {
  ...completedRun,
  id: "run-production-001",
  result: { ...completedRun.result, symbol: "ETHEUR", bars: 1440 },
  provenance: {
    dataset_id: manifest.dataset_id,
    manifest_identity: manifest.manifest_sha256,
    source_provider: manifest.source_provider,
    history_environment: "production",
    testnet_history_used: false,
    symbol: "ETHEUR",
    interval: "1m",
    requested_start: "2025-01-01T00:00:00Z",
    requested_end: "2025-01-02T00:00:00Z",
    retrieved_at: "2026-07-21T12:00:00Z",
    source_urls: [preview.sources[0].url],
    normalized_sha256: manifest.normalization.sha256,
    candle_sequence_sha256: manifest.normalization.candle_sequence_sha256,
    backtest_fingerprint: "f".repeat(64),
    catalog_identity: catalog.catalog_id,
    quote_asset: "EUR",
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
    characterizeCanonicalAdaptive: vi.fn().mockResolvedValue(canonicalAdaptive),
    getSafetyPosture: vi.fn().mockResolvedValue(safetyPosture),
    getOperatorControls: vi.fn().mockResolvedValue(operatorControls),
    executeBacktest: vi.fn().mockResolvedValue(completedRun),
    getBacktest: vi.fn().mockResolvedValue(completedRun),
    previewProductionDataset: vi.fn().mockResolvedValue(preview),
    importProductionDataset: vi.fn().mockResolvedValue(manifest),
    executeManifestedBacktest: vi.fn().mockResolvedValue(productionRun),
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

    expect(await screen.findByText("Market & Data")).toBeTruthy();
    expect(screen.getByText("Grid & Capital")).toBeTruthy();
    expect(screen.getByText("Costs & Execution")).toBeTruthy();
    expect(screen.getByText("Risk & Evaluation")).toBeTruthy();

    fireEvent.change(screen.getByLabelText("Symbol"), {
      target: { value: "ETHUSDT" },
    });

    fireEvent.click(screen.getByRole("button", { name: "Run backtest" }));

    await waitFor(() => expect(research.executeBacktest).toHaveBeenCalledOnce());
    expect(screen.getByText("+3.12%")).toBeTruthy();
    expect(screen.getByText("10,312.00 USDT")).toBeTruthy();
    expect(screen.getByText("run-typed-001")).toBeTruthy();
  });

  it("presents the obligation-backed adaptive initial epoch and activation gates", async () => {
    render(<App research={researchPort()} />);

    expect(await screen.findByText("Adaptive policy characterization")).toBeTruthy();
    expect(screen.getByText("RANGE_NORMAL")).toBeTruthy();
    expect(screen.getAllByText("BOOTSTRAPPING")).toHaveLength(2);
    expect(screen.getByText(identity("1"))).toBeTruthy();
    expect(screen.getByText(identity("3"))).toBeTruthy();
    expect(screen.getByText(identity("6"))).toBeTruthy();
    expect(screen.getByText(identity("a"))).toBeTruthy();
    expect(screen.getByText("required_backing_inventory_not_confirmed", { exact: false })).toBeTruthy();
    expect(screen.getAllByText("BUY")).toHaveLength(3);
    expect(screen.getAllByText("SELL")).toHaveLength(2);
    expect(screen.getByText("0.38886 BTC gross", { exact: false })).toBeTruthy();
    expect(screen.getByText(
      "canonical seam emits no immediate cancel-all/rebuild transition",
    )).toBeTruthy();
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

  it("previews, admits, and runs manifested production history with explicit provenance", async () => {
    const research = researchPort();
    render(<App research={research} />);

    expect(await screen.findByText("Production history")).toBeTruthy();
    expect(await screen.findByText("29 eligible EUR symbols")).toBeTruthy();
    fireEvent.change(screen.getByLabelText("EUR production symbol"), {
      target: { value: "ETHEUR" },
    });
    expect(screen.getByText("€29,000,000 median daily volume")).toBeTruthy();
    expect(screen.getByText("1.75 bps current spread")).toBeTruthy();
    expect(screen.getByText("Available historical data")).toBeTruthy();
    expect(screen.getByText("2020-01-01 → 2026-07-21")).toBeTruthy();
    fireEvent.change(screen.getByLabelText("UTC start day"), {
      target: { value: "2025-01-01" },
    });
    fireEvent.change(screen.getByLabelText("UTC end day"), {
      target: { value: "2025-01-02" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Preview official download" }));
    expect(await screen.findByText("123,456 bytes")).toBeTruthy();
    expect(screen.getByText("b".repeat(64))).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "Download, verify & normalize" }));
    expect(await screen.findByText("QUALITY APPROVED")).toBeTruthy();
    expect(screen.getByText(manifest.dataset_id)).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "Run production-history backtest" }));
    expect(await screen.findByText("PRODUCTION HISTORY")).toBeTruthy();
    expect(screen.getByText("TESTNET HISTORY NOT USED")).toBeTruthy();
    expect(screen.getByText("f".repeat(64))).toBeTruthy();
    expect(research.executeManifestedBacktest).toHaveBeenCalledOnce();
    expect(screen.getByText("10,312.00 EUR")).toBeTruthy();
    expect(research.previewProductionDataset).toHaveBeenCalledWith({
      catalog_id: catalog.catalog_id,
      symbol: "ETHEUR",
      interval: "1m",
      start: "2025-01-01T00:00:00.000Z",
      end: "2025-01-03T00:00:00.000Z",
    });
  });
});
