"""Pydantic request/response schemas for the studio API.

Every nested config block mirrors a gridlab config object but keeps all fields
optional. We dump with ``exclude_none=True`` before handing the dict to gridlab,
so the engine remains the single source of default values and validation — the
API never silently disagrees with the engine about what a default is.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal, Optional

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    StrictStr,
    model_validator,
)


class _Block(BaseModel):
    model_config = ConfigDict(extra="ignore")


class GridSpec(_Block):
    levels: Optional[int] = Field(default=None, ge=2, le=500)
    lower: Optional[float] = None
    upper: Optional[float] = None
    spacing: Optional[Literal["arithmetic", "geometric", "atr"]] = None
    direction: Optional[Literal["neutral", "long", "short"]] = None
    adaptive: Optional[bool] = None
    lookback: Optional[int] = Field(default=None, ge=2)
    atr_period: Optional[int] = Field(default=None, ge=2)
    atr_mult: Optional[float] = Field(default=None, gt=0)
    recenter_drift_frac: Optional[float] = Field(default=None, ge=0)
    take_profit_frac: Optional[float] = Field(default=None, ge=0)
    stop_loss_frac: Optional[float] = Field(default=None, ge=0)


class SizingSpec(_Block):
    mode: Optional[
        Literal["fixed_quote", "fixed_base", "percent_equity", "martingale"]
    ] = None
    value: Optional[float] = Field(default=None, gt=0)
    martingale_factor: Optional[float] = Field(default=None, ge=1)
    max_martingale_steps: Optional[int] = Field(default=None, ge=0)


class FeesSpec(_Block):
    maker: Optional[float] = Field(default=None, ge=0, le=0.05)
    taker: Optional[float] = Field(default=None, ge=0, le=0.05)


class SlippageSpec(_Block):
    spread_frac: Optional[float] = Field(default=None, ge=0, le=0.1)
    impact_frac: Optional[float] = Field(default=None, ge=0, le=0.1)


class FillSpec(_Block):
    mode: Optional[Literal["optimistic", "conservative"]] = None
    fill_on_touch: Optional[bool] = None
    fill_gaps_at_open: Optional[bool] = None
    participation: Optional[float] = Field(default=None, gt=0)


class MarginSpec(_Block):
    leverage: Optional[float] = Field(default=None, ge=1)
    maintenance_margin_frac: Optional[float] = Field(default=None, ge=0, lt=1)
    liquidation_fee_frac: Optional[float] = Field(default=None, ge=0)
    allow_short: Optional[bool] = None


class BootstrapSpec(_Block):
    base_fraction: Optional[float] = Field(default=None, ge=0, le=1)
    side: Optional[Literal["LONG", "SHORT"]] = None


class ConstraintsSpec(_Block):
    max_base_inventory: Optional[float] = Field(default=None, ge=0)
    max_gross_exposure_frac: Optional[float] = Field(default=None, ge=0)
    max_open_orders: Optional[int] = Field(default=None, ge=1)
    min_order_qty: Optional[float] = Field(default=None, ge=0)
    min_notional: Optional[float] = Field(default=None, ge=0)


class DataSpec(_Block):
    kind: Optional[
        Literal["synthetic", "dataframe", "binance", "csv", "manifested_parquet"]
    ] = None
    dataset_id: Optional[str] = None
    # synthetic
    n: Optional[int] = Field(default=None, ge=50, le=200_000)
    start_price: Optional[float] = Field(default=None, gt=0)
    seed: Optional[int] = None
    sigma: Optional[float] = Field(default=None, gt=0, le=1)
    regime: Optional[Literal["range", "trend", "random"]] = None
    interval_minutes: Optional[int] = Field(default=None, ge=1)
    records: Optional[list[dict[str, Any]]] = None
    # real data (binance / csv)
    symbol: Optional[str] = None
    interval: Optional[str] = None
    start: Optional[str] = None
    end: Optional[str] = None
    max_candles: Optional[int] = Field(default=None, ge=50, le=200_000)
    path: Optional[str] = None


class ExchangeRulesSpec(_Block):
    enabled: Optional[bool] = None
    tick_size: Optional[float] = Field(default=None, ge=0)
    step_size: Optional[float] = Field(default=None, ge=0)
    min_qty: Optional[float] = Field(default=None, ge=0)
    min_notional: Optional[float] = Field(default=None, ge=0)


class FilterSpec(_Block):
    kind: Optional[Literal["none", "trend", "regime", "rsi"]] = None
    adx_threshold: Optional[float] = Field(default=None, ge=0, le=100)
    oversold: Optional[float] = Field(default=None, ge=0, le=100)
    overbought: Optional[float] = Field(default=None, ge=0, le=100)


class BacktestRequest(_Block):
    """A full declarative backtest spec accepted by the API."""

    symbol: str = "BTCUSDT"
    market_type: Literal["spot", "futures"] = "spot"
    venue: Optional[str] = None  # "binance" | "ibkr" cost+filter preset
    initial_cash: float = Field(default=10_000.0, gt=0)
    grid: GridSpec = Field(default_factory=GridSpec)
    sizing: SizingSpec = Field(default_factory=SizingSpec)
    fees: FeesSpec = Field(default_factory=FeesSpec)
    slippage: SlippageSpec = Field(default_factory=SlippageSpec)
    fill: FillSpec = Field(default_factory=FillSpec)
    margin: MarginSpec = Field(default_factory=MarginSpec)
    bootstrap: BootstrapSpec = Field(default_factory=BootstrapSpec)
    constraints: ConstraintsSpec = Field(default_factory=ConstraintsSpec)
    exchange_rules: ExchangeRulesSpec = Field(default_factory=ExchangeRulesSpec)
    data: DataSpec = Field(default_factory=DataSpec)
    filter: FilterSpec = Field(default_factory=FilterSpec)
    n_trials: int = Field(default=1, ge=1)
    periods_per_year: Optional[float] = None

    def to_spec(self) -> dict:
        """Collapse to the plain dict gridlab's facade expects (no None leaves)."""
        raw = self.model_dump(exclude_none=True)
        # Drop empty nested blocks so gridlab falls back to its own defaults.
        return {k: v for k, v in raw.items() if not (isinstance(v, dict) and not v)}


class BacktestOptions(_Block):
    with_report: bool = False
    include_trades: bool = True


class RunBacktestBody(_Block):
    spec: BacktestRequest = Field(default_factory=BacktestRequest)
    options: BacktestOptions = Field(default_factory=BacktestOptions)


class StudioMetrics(_Block):
    model_config = ConfigDict(extra="allow")

    total_return: float
    max_drawdown: float
    n_trades: float
    win_rate: Optional[float]


class StudioVerdict(_Block):
    label: str
    tone: Literal["good", "warn", "bad"]
    score: int
    max_score: int


class StudioBacktestResult(_Block):
    model_config = ConfigDict(extra="allow")

    symbol: str
    bars: int
    initial_cash: float
    final_equity: float
    fees_paid: float
    metrics: StudioMetrics
    verdict: StudioVerdict
    trades: list[dict[str, Any]]
    simulation: "StudioSimulationPresentation"


class StudioSimulationPresentation(_Block):
    mode: Literal["candle"]
    canonical_core: bool
    venue_execution_proof: bool
    limitations: list[str]


class StudioPrimaryResult(_Block):
    net_return: float
    final_equity: float
    max_drawdown: float
    completed_trades: int
    fees_paid: float
    verdict: str


class ProductionDatasetProvenance(_Block):
    dataset_id: str
    manifest_identity: str
    source_provider: str
    history_environment: Literal["production"]
    testnet_history_used: Literal[False]
    symbol: str
    interval: Literal["1m"]
    requested_start: datetime
    requested_end: datetime
    retrieved_at: datetime
    source_urls: list[str]
    normalized_sha256: str
    candle_sequence_sha256: str
    backtest_fingerprint: str
    candle_count: int
    coverage: dict[str, datetime]
    partition_identities: list[str]
    catalog_identity: Optional[str] = None
    quote_asset: Optional[str] = None


class StudioBacktestRun(_Block):
    id: str
    status: Literal["completed"]
    created_at: datetime
    specification: dict[str, Any]
    primary_result: StudioPrimaryResult
    result: StudioBacktestResult
    provenance: Optional[ProductionDatasetProvenance] = None


class StudioConfiguration(_Block):
    default_spec: BacktestRequest
    spacing: list[Literal["geometric", "arithmetic"]]
    data_regimes: list[Literal["range", "trend", "random"]]


class CanonicalAdaptiveRequest(_Block):
    symbol: str = Field(
        default="BTCEUR", min_length=4, max_length=20, pattern=r"^[A-Z0-9]+EUR$"
    )
    decision_time: AwareDatetime
    trend: StrictStr = Field(default="0.0000", pattern=r"^-?[0-9]+(?:\.[0-9]+)?$")
    volatility: StrictStr = Field(default="0.0100", pattern=r"^[0-9]+(?:\.[0-9]+)?$")
    reference_price: StrictStr = Field(
        default="100.00", pattern=r"^[0-9]+(?:\.[0-9]+)?$"
    )
    activation_price: StrictStr = Field(
        default="100.00", pattern=r"^[0-9]+(?:\.[0-9]+)?$"
    )
    event_time: Optional[AwareDatetime] = None
    observed_count: int = Field(default=24, ge=0, le=100_000)
    sequence_end: int = Field(default=24, ge=0, le=100_000)
    spacing: Literal["GEOMETRIC", "ARITHMETIC"] = "GEOMETRIC"
    venue_environment: Literal["production", "testnet"] = "production"
    tick_size: StrictStr = Field(default="0.01", pattern=r"^[0-9]+(?:\.[0-9]+)?$")
    step_size: StrictStr = Field(default="0.00001", pattern=r"^[0-9]+(?:\.[0-9]+)?$")
    minimum_price: StrictStr = Field(default="0.01", pattern=r"^[0-9]+(?:\.[0-9]+)?$")
    maximum_price: Optional[StrictStr] = Field(
        default=None, pattern=r"^[0-9]+(?:\.[0-9]+)?$"
    )
    minimum_quantity: StrictStr = Field(
        default="0.00010", pattern=r"^[0-9]+(?:\.[0-9]+)?$"
    )
    maximum_quantity: Optional[StrictStr] = Field(
        default=None, pattern=r"^[0-9]+(?:\.[0-9]+)?$"
    )
    minimum_notional: StrictStr = Field(
        default="5.00", pattern=r"^[0-9]+(?:\.[0-9]+)?$"
    )
    maximum_notional: Optional[StrictStr] = Field(
        default=None, pattern=r"^[0-9]+(?:\.[0-9]+)?$"
    )
    max_open_orders: Optional[int] = Field(default=None, ge=1, le=10_000)
    foreign_open_orders: int = Field(default=0, ge=0, le=10_000)
    symbol_status: Literal[
        "TRADING", "SUSPENDED", "MAINTENANCE", "DELISTING", "UNKNOWN"
    ] = "TRADING"
    spot_trading_allowed: bool = True
    limit_maker_supported: bool = True
    contradictory_rules: bool = False
    bootstrap_complete: bool = False
    bootstrap_confirmed_base: StrictStr = Field(
        default="0", pattern=r"^[0-9]+(?:\.[0-9]+)?$"
    )
    bootstrap_evidence_id: Optional[str] = None
    complete: bool = True
    evidence_quality: Literal[
        "ADMITTED",
        "INCOMPLETE",
        "STALE",
        "GAPPED",
        "CONTRADICTORY",
        "AMBIGUOUS",
    ] = "ADMITTED"


class ExactValuePresentation(_Block):
    kind: str
    value: str


class CanonicalConfigurationPresentation(_Block):
    schema_version: str
    configuration_id: str
    policy_id: str
    symbol: str
    base_asset: str
    quote_asset: str
    rung_count: int
    spacing: Literal["ARITHMETIC", "GEOMETRIC"]
    execution_policy_id: str
    risk_profile_id: str
    operator_inputs: dict[str, ExactValuePresentation]


class CanonicalObservationPresentation(_Block):
    schema_version: str
    observation_id: str
    event_id: str
    source_system: str
    source_stream: str
    event_time: datetime
    decision_time: datetime
    complete: bool
    quality: str
    confirmation_ids: list[str]
    prior_decision_id: Optional[str]
    trend: ExactValuePresentation
    volatility: ExactValuePresentation
    reference_price: ExactValuePresentation


class CanonicalDecisionPresentation(_Block):
    decision_id: str
    adaptation_state: Literal[
        "RANGE_NORMAL",
        "RANGE_HIGH_VOLATILITY",
        "TREND_UP",
        "TREND_DOWN",
        "UNCERTAIN",
    ]
    intent: Literal["SYMMETRIC", "WIDEN", "SHIFT_UP", "REDUCE_ONLY", "FROZEN"]
    reason: str
    permits_exposure_increasing_buy: bool
    requested_bound_shift: Optional[ExactValuePresentation]


class CanonicalRungPresentation(_Block):
    index: int
    price: ExactValuePresentation
    role: Literal["BUY", "SELL", "INACTIVE"]


class CanonicalObligationPresentation(_Block):
    rung_index: int
    role: Literal["BUY", "SELL"]
    fixed_quote_principal: ExactValuePresentation
    base_quantity: Optional[ExactValuePresentation]


class CanonicalAllocationPresentation(_Block):
    quote_allocation: ExactValuePresentation
    base_allocation: ExactValuePresentation
    fee_reserve: ExactValuePresentation


class CanonicalDerivedPlanPresentation(_Block):
    schema_version: str
    epoch_id: str
    predecessor_epoch_id: Optional[str]
    derivation_causation_id: str
    derivation_semantics: str
    venue_rule_evidence_id: str
    lower: ExactValuePresentation
    upper: ExactValuePresentation
    reference_price: ExactValuePresentation
    activation_price: ExactValuePresentation
    unquantized_rungs: list[ExactValuePresentation]
    quantized_rungs: list[CanonicalRungPresentation]
    obligations: list[CanonicalObligationPresentation]
    allocation_assumptions: CanonicalAllocationPresentation
    maximum_planned_inventory: Optional[ExactValuePresentation]
    bootstrap_obligation: Optional["CanonicalBootstrapObligationPresentation"]


class CanonicalBootstrapObligationPresentation(_Block):
    net_base_required: ExactValuePresentation
    gross_base_required: ExactValuePresentation
    fee_base_coverage: ExactValuePresentation


class CanonicalActivationGatePresentation(_Block):
    name: str
    outcome: Literal["PASSED", "FAILED", "BLOCKED"]
    reason: str


class CanonicalBootstrapEvidencePresentation(_Block):
    complete: bool
    net_base_confirmed: ExactValuePresentation
    evidence_id: Optional[str]


class CanonicalAdmissionContextPresentation(_Block):
    still_effective_quote_commitment: ExactValuePresentation
    still_effective_inventory_commitment: ExactValuePresentation
    still_effective_order_count: int


class CanonicalAdmissionAssessmentPresentation(_Block):
    capital_envelope: ExactValuePresentation
    still_effective_quote_commitment: ExactValuePresentation
    proposed_quote_commitment: ExactValuePresentation
    bootstrap_quote_commitment: ExactValuePresentation
    total_quote_commitment: ExactValuePresentation
    fee_reserve: ExactValuePresentation
    still_effective_inventory_commitment: ExactValuePresentation
    additional_bootstrap_inventory: ExactValuePresentation
    maximum_planned_inventory: ExactValuePresentation
    total_worst_case_inventory: ExactValuePresentation
    still_effective_order_count: int
    proposed_order_count: int
    total_order_count: int
    venue_order_capacity: Optional[int]
    foreign_open_orders: int


class CanonicalAdjacentCyclePresentation(_Block):
    buy_rung_index: int
    sell_rung_index: int
    buy_price: ExactValuePresentation
    sell_price: ExactValuePresentation
    cycle_quantity: ExactValuePresentation
    net_margin: ExactValuePresentation
    positive: bool
    reason: str


class CanonicalPrincipalFeasibilityPointPresentation(_Block):
    principal: ExactValuePresentation
    feasible: bool
    reasons: list[str]


class CanonicalPrincipalFeasibilityPresentation(_Block):
    schema_version: str
    points: list[CanonicalPrincipalFeasibilityPointPresentation]


class CanonicalPostOnlyRetryPolicyPresentation(_Block):
    schema_version: str
    order_type: Literal["LIMIT_MAKER"]
    max_attempts: int
    retry_delays: list[ExactValuePresentation]
    max_price_displacement_ratio: ExactValuePresentation
    max_adjacent_gap_fraction: ExactValuePresentation
    exhaustion_posture: Literal["REDUCE_ONLY"]


class CanonicalRuleFeeContractPresentation(_Block):
    schema_version: str
    contract_id: str
    venue_rule_evidence_id: str
    maker_fee: ExactValuePresentation
    taker_fee: ExactValuePresentation


class CanonicalInitialActivationPresentation(_Block):
    schema_version: str
    lifecycle: Literal["REJECTED", "BOOTSTRAPPING", "ACTIVE"]
    replay_fingerprint: str
    ladder_placement_allowed: bool
    activation_pending: bool
    automatically_armed: bool
    derived_width: Optional[ExactValuePresentation]
    gates: list[CanonicalActivationGatePresentation]
    bootstrap_evidence: CanonicalBootstrapEvidencePresentation
    admission_context: CanonicalAdmissionContextPresentation
    admission_assessment: Optional[CanonicalAdmissionAssessmentPresentation]
    adjacent_cycle_economics: list[CanonicalAdjacentCyclePresentation]
    principal_feasibility: CanonicalPrincipalFeasibilityPresentation
    post_only_retry_policy: CanonicalPostOnlyRetryPolicyPresentation
    rule_fee_contract: CanonicalRuleFeeContractPresentation


class LegacyComparisonPresentation(_Block):
    bounded_bars: int
    legacy_adaptive: bool
    legacy_spacing: str
    effective_atr_multiplier: str
    cancelled_orders: int
    semantic_differences: list[str]


class CanonicalAdaptivePresentation(_Block):
    configuration: CanonicalConfigurationPresentation
    observation: CanonicalObservationPresentation
    decision: CanonicalDecisionPresentation
    activation: CanonicalInitialActivationPresentation
    derived_plan: Optional[CanonicalDerivedPlanPresentation]
    legacy_comparison: LegacyComparisonPresentation


class SafetyCapitalPresentation(_Block):
    allocation_fingerprint: str
    epoch_id: str
    capital_envelope: ExactValuePresentation
    committed_principal: ExactValuePresentation
    fee_reserve: ExactValuePresentation
    maximum_planned_inventory: ExactValuePresentation


class SafetyLifecyclePresentation(_Block):
    grid_lifecycle: str
    adaptation_state: Literal[
        "RANGE_NORMAL",
        "RANGE_HIGH_VOLATILITY",
        "TREND_UP",
        "TREND_DOWN",
        "UNCERTAIN",
    ]
    epoch_transition_state: str
    runtime_lifecycle: str
    reconciliation_state: str


class SafetyFactPresentation(_Block):
    posture: Literal[
        "NORMAL", "REDUCE_ONLY", "TERMINAL_LIQUIDATION", "FROZEN", "CLOSED"
    ]
    reason_codes: list[str]
    loss_warning: bool
    daily_loss_latched: bool
    run_drawdown_latched: bool
    global_stop_latched: bool
    allowed_command_classes: list[
        Literal[
            "EXPOSURE_INCREASING",
            "INVENTORY_REDUCING",
            "PLACEMENT",
            "REPLACEMENT",
            "CANCELLATION",
            "RECONCILIATION",
            "EVIDENCE_GATHERING",
        ]
    ]
    placement_allowed: bool
    replacement_allowed: bool
    downward_bound_shift_allowed: bool
    fixed_quote_sizing_increase_allowed: bool
    clock_offset: ExactValuePresentation
    scheduling_delay: ExactValuePresentation
    round_trip_latency: ExactValuePresentation


class SafetyFreshnessPresentation(_Block):
    evidence_class: Literal[
        "VALUATION", "STRATEGY_INPUT", "PRIVATE_STREAM", "CONTROL_PATH", "CLOCK"
    ]
    condition: Literal[
        "HEALTHY",
        "MISSING",
        "STALE",
        "GAPPED",
        "DISCONNECTED",
        "UNAVAILABLE",
        "REJECTED",
    ]
    observed_at: Optional[datetime]
    evidence_id: str


class SafetyVenuePresentation(_Block):
    condition: Literal["TRADING", "SUSPENDED", "MAINTENANCE", "DELISTING"]
    evidence_id: str
    source: str
    wind_down_deadline: Optional[datetime]


class SafetyPosturePresentation(_Block):
    schema_version: Literal["safety-posture-presentation/v1"]
    decision_time: datetime
    fingerprint: str
    capital: SafetyCapitalPresentation
    lifecycle: SafetyLifecyclePresentation
    safety: SafetyFactPresentation
    freshness: list[SafetyFreshnessPresentation]
    venue: SafetyVenuePresentation


class OperatorProjectionPresentation(_Block):
    active_epoch_id: str
    proposed_epoch_id: Optional[str]
    transition_state: str
    posture: Literal[
        "NORMAL", "REDUCE_ONLY", "TERMINAL_LIQUIDATION", "FROZEN", "CLOSED"
    ]


class AuthoritativeInventoryBasisPresentation(_Block):
    basis_id: str
    source: str
    base_asset: str
    quantity: ExactValuePresentation
    authoritative: bool
    reconciled_at: Optional[datetime]


class OperatorPreviewGatePresentation(_Block):
    name: str
    outcome: Literal["PASSED", "FAILED"]
    reason: str


class OperatorCommandPreviewPresentation(_Block):
    action: Literal["PAUSE", "RESUME", "OPERATOR_STOP", "EMERGENCY_STOP"]
    availability: Literal["IMMEDIATE", "PREVIEW_REQUIRED", "BLOCKED", "LATCHED"]
    confirmation_required: bool
    environment_bound: bool
    idempotent: bool
    preempts_pending_activation: bool
    blocks_new_epoch_placement: bool
    admission_order_preserved: bool
    active_epoch_id: str
    proposed_epoch_id: Optional[str]
    transition_state: str
    posture: Literal[
        "NORMAL", "REDUCE_ONLY", "TERMINAL_LIQUIDATION", "FROZEN", "CLOSED"
    ]
    inventory_basis_id: str
    cancel_obligation_ids: list[str]
    retained_obligation_ids: list[str]
    late_fill_ids: list[str]
    gates: list[OperatorPreviewGatePresentation]
    reason_codes: list[str]
    available_dispositions: list[Literal["RETAIN_HOLDING", "DISPOSE"]]
    selected_disposition: Optional[Literal["RETAIN_HOLDING", "DISPOSE"]]


class TerminalDisposalWavePresentation(_Block):
    wave: int
    order_type: Literal["IOC"]
    quantity_limit: ExactValuePresentation
    notional_limit: ExactValuePresentation
    max_depth_age: ExactValuePresentation
    price_band_bps: ExactValuePresentation
    attempt_limit: int
    elapsed_time_limit: ExactValuePresentation
    outcome: Literal[
        "PARTIAL", "REJECTED", "UNKNOWN", "EXHAUSTED", "RESIDUAL_RETAINED", "COMPLETED"
    ]
    reconciled_before_next_wave: bool
    authoritative_inventory_after_wave: ExactValuePresentation


class TerminalGoldenReplayPresentation(_Block):
    case_name: Literal[
        "GAP_THROUGH",
        "PARTIAL_DISPOSAL",
        "REJECTION",
        "UNKNOWN_OUTCOME",
        "ATTEMPT_EXHAUSTION",
        "RESIDUAL_HOLDINGS",
    ]
    outcome: str
    replay_fingerprint: str


class TerminalDisposalPresentation(_Block):
    trigger: Literal["NONE", "OPERATOR_EMERGENCY", "TERMINAL_LOSS"]
    state: Literal[
        "NONE",
        "AWAITING_AUTHORITATIVE_INVENTORY",
        "DISPOSING",
        "DISPOSED",
        "RETAINED",
    ]
    global_stop_latched: bool
    operator_emergency_latched: bool
    automatic_liquidation: bool
    preempts_pending_activation: bool
    admission_order_preserved: bool
    active_epoch_id: str
    proposed_epoch_id: Optional[str]
    transition_state: str
    posture: Literal[
        "NORMAL", "REDUCE_ONLY", "TERMINAL_LIQUIDATION", "FROZEN", "CLOSED"
    ]
    inventory_basis_id: str
    waves: list[TerminalDisposalWavePresentation]
    golden_replay_cases: list[TerminalGoldenReplayPresentation]


class OperatorControlsPresentation(_Block):
    schema_version: Literal["operator-controls-presentation/v1"]
    decision_time: datetime
    fingerprint: str
    projection: OperatorProjectionPresentation
    inventory_basis: AuthoritativeInventoryBasisPresentation
    pause: OperatorCommandPreviewPresentation
    resume: OperatorCommandPreviewPresentation
    operator_stop: OperatorCommandPreviewPresentation
    emergency_stop: OperatorCommandPreviewPresentation
    terminal: TerminalDisposalPresentation


class EpochTransitionEvidencePresentation(_Block):
    observation_id: str
    decision_id: str
    adaptation_state: Literal[
        "RANGE_NORMAL",
        "RANGE_HIGH_VOLATILITY",
        "TREND_UP",
        "TREND_DOWN",
        "UNCERTAIN",
    ]
    intent: Literal["SYMMETRIC", "WIDEN", "SHIFT_UP", "REDUCE_ONLY", "FROZEN"]
    reason: str


class EpochTransitionGatePresentation(_Block):
    name: str
    outcome: Literal["PASSED", "FAILED", "NOT_APPLICABLE"]
    reason: str


class EpochTransitionProgressPresentation(_Block):
    phase: Literal[
        "CHANGE_CONFIRMED",
        "TRANSITION_REQUESTED",
        "OLD_EXPOSURE_BLOCKED",
        "CANCELLING",
        "RECONCILING",
        "DERIVING",
        "VALIDATING",
        "BOOTSTRAPPING",
        "ACTIVATING",
        "ACTIVE",
    ]
    status: Literal["PENDING", "CURRENT", "COMPLETED", "SKIPPED", "FAILED"]
    reason: str


class EpochTransitionPermissionsPresentation(_Block):
    placement_allowed: bool
    replacement_allowed: bool
    cancellation_allowed: bool
    reconciliation_allowed: bool
    inventory_reduction_allowed: bool


class EpochTransitionOrderPresentation(_Block):
    order_id: str
    epoch_id: str
    side: Literal["BUY", "SELL"]
    state: Literal["OPEN", "CANCEL_PENDING", "CANCELLED", "FILLED", "UNKNOWN"]
    exposure_increasing: bool
    inventory_reducing: bool
    terminal_proven: bool
    outcome_unknown: bool


class EpochTransitionLateFillPresentation(_Block):
    fill_id: str
    order_id: str
    original_epoch_id: str
    posting_epoch_id: str


class EpochTransitionAdmissionAssessmentPresentation(_Block):
    capital_envelope: ExactValuePresentation
    total_quote_commitment: ExactValuePresentation
    bootstrap_quote_commitment: ExactValuePresentation
    fee_reserve: ExactValuePresentation
    maximum_planned_inventory: ExactValuePresentation
    total_worst_case_inventory: ExactValuePresentation
    total_order_count: int
    venue_order_capacity: Optional[int]


class EpochTransitionActivationPresentation(_Block):
    lifecycle: Literal["REJECTED", "BOOTSTRAPPING", "ACTIVE"]
    replay_fingerprint: str
    ladder_placement_allowed: bool
    bootstrap_required: bool
    admission_context: CanonicalAdmissionContextPresentation
    admission_assessment: Optional[EpochTransitionAdmissionAssessmentPresentation]
    gates: list[CanonicalActivationGatePresentation]


class EpochTransitionPresentation(_Block):
    schema_version: Literal["epoch-transition-evaluation/v1"]
    decision_time: datetime
    fingerprint: str
    active_epoch_id: str
    proposed_epoch_id: Optional[str]
    phase: Literal[
        "ACTIVE",
        "CHANGE_CONFIRMED",
        "TRANSITION_REQUESTED",
        "OLD_EXPOSURE_BLOCKED",
        "CANCELLING",
        "RECONCILING",
        "DERIVING",
        "VALIDATING",
        "BOOTSTRAPPING",
        "ACTIVATING",
    ]
    posture: Literal[
        "NORMAL", "REDUCE_ONLY", "TERMINAL_LIQUIDATION", "FROZEN", "CLOSED"
    ]
    evidence: EpochTransitionEvidencePresentation
    refusal_reason: Optional[str]
    crash_safe: bool
    restart_boundaries: list[
        Literal[
            "CHANGE_CONFIRMED",
            "TRANSITION_REQUESTED",
            "OLD_EXPOSURE_BLOCKED",
            "CANCELLING",
            "RECONCILING",
            "DERIVING",
            "VALIDATING",
            "BOOTSTRAPPING",
            "ACTIVATING",
            "ACTIVE",
        ]
    ]
    gates: list[EpochTransitionGatePresentation]
    progress: list[EpochTransitionProgressPresentation]
    permissions: EpochTransitionPermissionsPresentation
    inventory_basis: AuthoritativeInventoryBasisPresentation
    old_orders: list[EpochTransitionOrderPresentation]
    late_fill_postings: list[EpochTransitionLateFillPresentation]
    replacement_activation: Optional[EpochTransitionActivationPresentation]


class BinanceDatasetRequest(_Block):
    catalog_id: Optional[str] = Field(
        default=None, min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$"
    )
    symbol: str = Field(min_length=5, max_length=20, pattern=r"^[A-Za-z0-9]+$")
    interval: Literal["1m"] = "1m"
    start: datetime
    end: datetime


class ArchiveSourcePreview(_Block):
    date: str
    url: str
    checksum_url: str
    expected_sha256: str
    estimated_bytes: int


class AcquisitionLimitsPreview(_Block):
    max_days: int
    max_objects: int
    max_bytes: int


class BinanceDatasetPreview(_Block):
    preview_id: str
    venue: Literal["binance"]
    market: Literal["spot-production-archive"]
    symbol: str
    interval: Literal["1m"]
    start: datetime
    end: datetime
    estimated_bytes: int
    sources: list[ArchiveSourcePreview]
    limits: AcquisitionLimitsPreview
    catalog_identity: Optional[str] = None
    symbol_metadata: Optional[dict[str, Any]] = None


class CatalogSourceEvidence(_Block):
    environment: Literal["production", "testnet"]
    url: str
    server_time: datetime


class ArchiveCoverageEvidence(_Block):
    first_date: date
    last_date: date
    intervals: list[str]
    known_gap_dates: list[date]
    evidence_urls: list[str]


class LiquiditySelectionEvidence(_Block):
    observed_days: int
    observed_start_date: date
    observed_end_date: date
    observed_at: datetime
    kline_source_url: str
    kline_payload_sha256: str
    ticker_source_url: str
    ticker_payload_sha256: str
    median_daily_quote_volume: Decimal
    median_daily_trade_count: Decimal
    annualized_realized_volatility: Decimal
    current_spread_bps: Decimal
    current_trade_count: int


class EurCatalogSymbolEvidence(_Block):
    symbol: str
    base_asset: str
    quote_asset: Literal["EUR"]
    status: Literal["TRADING"]
    exchange_filters: dict[str, dict[str, Any]]
    coverage: ArchiveCoverageEvidence
    liquidity: LiquiditySelectionEvidence
    liquidity_rank: int


class BinanceEurResearchCatalog(_Block):
    catalog_id: str
    retrieved_at: datetime
    quote_asset: Literal["EUR"]
    filters: list[str]
    sources: list[CatalogSourceEvidence]
    symbols: list[EurCatalogSymbolEvidence]


class ProductionPanelSourceEvidence(_Block):
    kind: str
    url: str
    observed_at: datetime
    identity: str


class ArchiveSyncPlanEvidence(_Block):
    month: str
    source_kind: Literal["monthly_archive", "daily_archives_current_month"]
    reason: str
    coverage_start: datetime
    coverage_end: datetime
    expected_rows: int
    estimated_download_bytes: int
    estimated_storage_bytes: int
    missing_source_objects: int
    source_labels: list[str]


class ArchiveSyncPreviewSymbolEvidence(_Block):
    symbol: str
    dataset_id: str
    first_available_date: date
    last_available_date: date
    pending_partitions: int
    missing_source_objects: int
    estimated_download_bytes: int
    estimated_storage_bytes: int
    plans: list[ArchiveSyncPlanEvidence]


class ArchiveSyncPreviewEvidence(_Block):
    preview_id: str
    source_objects: int
    estimated_download_bytes: int
    estimated_storage_bytes: int
    pending_partitions: int
    verified_partitions: int
    symbols: list[ArchiveSyncPreviewSymbolEvidence]


class ProductionArchivePartitionEvidence(_Block):
    schema_version: str
    archive_id: str
    dataset_id: str
    symbol: str
    quote_asset: Literal["EUR"]
    interval: Literal["1m"]
    month: str
    coverage_start: datetime
    coverage_end: datetime
    source_kind: Literal["monthly_archive", "daily_archives_current_month"]
    row_count: int
    ordering: list[str]
    normalization_identity: str
    normalized_sha256: str
    source_urls: list[str]
    source_checksums: list[str]
    timestamp_units: list[str]
    source_evidence: list[dict[str, Any]]
    quality: DatasetQuality
    parquet_schema: list[ParquetField] = Field(
        alias="schema", serialization_alias="schema"
    )
    verification_status: Literal["verified"]
    active: bool
    gap_findings: list[str]
    correction_findings: list[str]
    sequence_sha256: str
    partition_id: str
    path: str
    manifest_path: str
    byte_size: int
    manifest_identity: str


class VerifiedRangeEvidence(_Block):
    start: datetime
    end: datetime


class SynchronizedProductionDatasetEvidence(_Block):
    symbol: str
    dataset_id: str
    quote_asset: Literal["EUR"]
    display_order: int
    coverage: ArchiveCoverageEvidence
    verified_ranges: list[VerifiedRangeEvidence]
    total_rows: int
    stored_bytes: int
    partitions: list[ProductionArchivePartitionEvidence]
    pending_partition_months: list[str]


class FrozenProductionPanel(_Block):
    archive_id: str
    status: Literal["pending", "ready", "blocked"]
    retrieved_at: datetime
    quote_asset: Literal["EUR"]
    interval: Literal["1m"]
    symbols: list[str]
    sources: list[ProductionPanelSourceEvidence]
    preview: ArchiveSyncPreviewEvidence
    datasets: list[SynchronizedProductionDatasetEvidence]
    blocking_reasons: list[str]


class ImportDatasetBody(_Block):
    preview_id: str = Field(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")


class DatasetQuality(_Block):
    rows: int
    gaps: int
    duplicates: int
    out_of_order: int
    invalid_records: int


class ParquetField(_Block):
    name: str
    type: str
    nullable: bool


class DatasetNormalization(_Block):
    identity: str
    format: Literal["parquet"]
    path: str
    sha256: str
    rows: int
    parquet_schema: list[ParquetField] = Field(
        alias="schema", serialization_alias="schema"
    )
    candle_sequence_sha256: str
    ordering: list[str]
    parent_dataset_id: Optional[str]
    resampling_rule: Optional[str]


class DatasetManifest(_Block):
    dataset_id: str
    manifest_sha256: str
    schema_version: str
    identity: dict[str, Any]
    venue: Literal["binance"]
    market: Literal["spot"]
    history_environment: Literal["production"]
    source_provider: str
    catalog_identity: Optional[str] = None
    symbol_metadata: Optional[dict[str, Any]] = None
    symbol: str
    event_kind: Literal["kline"]
    interval: Literal["1m"]
    requested_range: dict[str, datetime]
    coverage: dict[str, datetime]
    retrieved_at: datetime
    sources: list[dict[str, Any]]
    timestamp: dict[str, Any]
    quality: DatasetQuality
    normalization: DatasetNormalization
    venue_rule_snapshot_id: Optional[str]
    fee_snapshot_id: Optional[str]


class ManifestedBacktestBody(_Block):
    dataset_id: str = Field(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")
    spec: BacktestRequest
    options: BacktestOptions = Field(default_factory=BacktestOptions)

    @model_validator(mode="after")
    def enforce_static_neutral_spot(self) -> ManifestedBacktestBody:
        grid = self.spec.grid
        margin = self.spec.margin
        if (
            self.spec.market_type != "spot"
            or grid.direction not in (None, "neutral")
            or grid.adaptive is True
            or grid.spacing == "atr"
            or (margin.leverage is not None and margin.leverage != 1)
            or margin.allow_short is True
            or self.spec.bootstrap.side == "SHORT"
        ):
            raise ValueError(
                "manifested production backtests accept only static neutral Spot "
                "without leverage or short exposure"
            )
        return self


class ProductionArchiveBacktestBody(_Block):
    dataset_id: str = Field(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")
    start: AwareDatetime
    end: AwareDatetime
    spec: BacktestRequest
    options: BacktestOptions = Field(default_factory=BacktestOptions)

    @model_validator(mode="after")
    def enforce_static_neutral_spot(self) -> ProductionArchiveBacktestBody:
        grid = self.spec.grid
        margin = self.spec.margin
        if (
            self.spec.market_type != "spot"
            or grid.direction not in (None, "neutral")
            or grid.adaptive is True
            or grid.spacing == "atr"
            or (margin.leverage is not None and margin.leverage != 1)
            or margin.allow_short is True
            or self.spec.bootstrap.side == "SHORT"
            or self.end <= self.start
        ):
            raise ValueError(
                "synchronized production-archive backtests accept only static neutral Spot "
                "without leverage or short exposure, over a non-empty UTC range"
            )
        return self


class GridPreviewBody(_Block):
    """Lightweight request to compute grid rung prices for the live preview."""

    spec: BacktestRequest = Field(default_factory=BacktestRequest)


class GridSearchBody(_Block):
    base: BacktestRequest = Field(default_factory=BacktestRequest)
    space: dict[str, list[Any]] = Field(default_factory=dict)
    objective: str = "deflated_sharpe"
    maximize: bool = True
    top_k: Optional[int] = Field(default=None, ge=1)


class WalkForwardBody(_Block):
    base: BacktestRequest = Field(default_factory=BacktestRequest)
    space: dict[str, list[Any]] = Field(default_factory=dict)
    n_splits: int = Field(default=4, ge=2, le=20)
    objective: str = "deflated_sharpe"


class MonteCarloBody(_Block):
    base: BacktestRequest = Field(default_factory=BacktestRequest)
    method: Literal["trades", "returns"] = "trades"
    n_sims: int = Field(default=2000, ge=100, le=20000)
    seed: int = 0


class RobustnessBody(_Block):
    base: BacktestRequest = Field(default_factory=BacktestRequest)
    space: dict[str, list[Any]] = Field(default_factory=dict)
    n_splits: int = Field(default=3, ge=2, le=12)
    mc_sims: int = Field(default=800, ge=100, le=10000)
