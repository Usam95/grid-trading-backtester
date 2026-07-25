from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_CEILING
from enum import Enum

from gridlab.canonical._identity import content_identity
from gridlab.canonical.adaptation import AdaptationState
from gridlab.canonical.events import DomainTime
from gridlab.canonical.values import ExactDecimal


class SafetyPosture(str, Enum):
    NORMAL = "NORMAL"
    REDUCE_ONLY = "REDUCE_ONLY"
    TERMINAL_LIQUIDATION = "TERMINAL_LIQUIDATION"
    FROZEN = "FROZEN"
    CLOSED = "CLOSED"


class AllowedCommandClass(str, Enum):
    EXPOSURE_INCREASING = "EXPOSURE_INCREASING"
    INVENTORY_REDUCING = "INVENTORY_REDUCING"
    PLACEMENT = "PLACEMENT"
    REPLACEMENT = "REPLACEMENT"
    CANCELLATION = "CANCELLATION"
    RECONCILIATION = "RECONCILIATION"
    EVIDENCE_GATHERING = "EVIDENCE_GATHERING"


class EvidenceClass(str, Enum):
    VALUATION = "VALUATION"
    STRATEGY_INPUT = "STRATEGY_INPUT"
    PRIVATE_STREAM = "PRIVATE_STREAM"
    CONTROL_PATH = "CONTROL_PATH"
    CLOCK = "CLOCK"


class EvidenceCondition(str, Enum):
    HEALTHY = "HEALTHY"
    MISSING = "MISSING"
    STALE = "STALE"
    GAPPED = "GAPPED"
    DISCONNECTED = "DISCONNECTED"
    UNAVAILABLE = "UNAVAILABLE"
    REJECTED = "REJECTED"


class RangeCondition(str, Enum):
    IN_RANGE = "IN_RANGE"
    BELOW_RANGE = "BELOW_RANGE"
    ABOVE_RANGE = "ABOVE_RANGE"


class SymbolCondition(str, Enum):
    TRADING = "TRADING"
    SUSPENDED = "SUSPENDED"
    MAINTENANCE = "MAINTENANCE"
    DELISTING = "DELISTING"


@dataclass(frozen=True, slots=True)
class CapitalCommitmentFacts:
    schema_version: str
    allocation_fingerprint: str
    epoch_id: str
    capital_envelope: ExactDecimal
    committed_principal: ExactDecimal
    fee_reserve: ExactDecimal
    projected_obligation_fees: ExactDecimal
    projected_terminal_fees: ExactDecimal
    exposure_increasing_buy_principals: tuple[ExactDecimal, ...]
    effective_managed_orders: int
    foreign_open_orders: int
    authenticated_order_limit: int
    current_inventory: ExactDecimal
    pending_buy_inventory: ExactDecimal
    transition_bootstrap_inventory: ExactDecimal
    proposed_maximum_inventory: ExactDecimal
    maximum_planned_inventory: ExactDecimal

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "exposure_increasing_buy_principals",
            tuple(self.exposure_increasing_buy_principals),
        )
        if self.schema_version != "capital-commitment-facts/v1":
            raise ValueError("unsupported capital commitment facts schema")
        if not self.allocation_fingerprint.startswith("sha256:"):
            raise ValueError("allocation fingerprint is required")
        if not self.epoch_id.startswith("sha256:"):
            raise ValueError("grid plan epoch identity is required")
        quote_values = (
            self.capital_envelope,
            self.committed_principal,
            self.fee_reserve,
            self.projected_obligation_fees,
            self.projected_terminal_fees,
            *self.exposure_increasing_buy_principals,
        )
        if any(value.kind != "quote_quantity" or value.decimal < 0 for value in quote_values):
            raise ValueError("capital commitments require non-negative quote quantities")
        inventory_values = (
            self.current_inventory,
            self.pending_buy_inventory,
            self.transition_bootstrap_inventory,
            self.proposed_maximum_inventory,
            self.maximum_planned_inventory,
        )
        if any(value.kind != "base_quantity" or value.decimal < 0 for value in inventory_values):
            raise ValueError("inventory commitments require non-negative base quantities")
        if (
            min(
                self.effective_managed_orders,
                self.foreign_open_orders,
                self.authenticated_order_limit,
            )
            < 0
        ):
            raise ValueError("order counts must be non-negative")


@dataclass(frozen=True, slots=True)
class LossFacts:
    schema_version: str
    initial_equity: ExactDecimal
    risk_day_baseline: ExactDecimal
    run_high_water_mark: ExactDecimal
    conservative_liquidation_equity: ExactDecimal
    prior_daily_loss_latched: bool
    prior_run_drawdown_latched: bool
    guardrail_recovery_approved: bool
    global_stop_latched: bool

    def __post_init__(self) -> None:
        if self.schema_version != "loss-facts/v1":
            raise ValueError("unsupported loss facts schema")
        values = (
            self.initial_equity,
            self.risk_day_baseline,
            self.run_high_water_mark,
            self.conservative_liquidation_equity,
        )
        if any(value.kind != "quote_quantity" or value.decimal < 0 for value in values):
            raise ValueError("loss facts require non-negative quote quantities")
        if self.initial_equity.decimal <= 0:
            raise ValueError("initial equity must be positive")
        if self.risk_day_baseline.decimal <= 0 or self.run_high_water_mark.decimal <= 0:
            raise ValueError("loss guardrail baselines must be positive")


@dataclass(frozen=True, slots=True)
class FreshnessEvidence:
    schema_version: str
    evidence_class: EvidenceClass
    condition: EvidenceCondition
    observed_at: DomainTime | None
    evidence_id: str

    def __post_init__(self) -> None:
        if self.schema_version != "freshness-evidence/v1":
            raise ValueError("unsupported freshness evidence schema")
        if not self.evidence_id.startswith("sha256:"):
            raise ValueError("freshness evidence identity is required")
        if self.condition is EvidenceCondition.MISSING:
            if self.observed_at is not None:
                raise ValueError("missing evidence cannot have an observation time")
        elif self.observed_at is None:
            raise ValueError("observed evidence requires an explicit time")


@dataclass(frozen=True, slots=True)
class ClockEvidence:
    schema_version: str
    condition: EvidenceCondition
    request_sent_at: DomainTime
    response_received_at: DomainTime
    venue_time: DomainTime
    scheduling_delay: ExactDecimal
    authenticated_timestamp_rejected: bool
    evidence_id: str

    def __post_init__(self) -> None:
        if self.schema_version != "clock-evidence/v1":
            raise ValueError("unsupported clock evidence schema")
        if self.response_received_at.value < self.request_sent_at.value:
            raise ValueError("clock response cannot precede its request")
        if self.scheduling_delay.kind != "duration_seconds" or self.scheduling_delay.decimal < 0:
            raise ValueError("scheduling delay must be a non-negative exact duration")
        if not self.evidence_id.startswith("sha256:"):
            raise ValueError("clock evidence identity is required")


@dataclass(frozen=True, slots=True)
class LifecycleFacts:
    schema_version: str
    grid_lifecycle: str
    adaptation_state: AdaptationState
    epoch_transition_state: str
    runtime_lifecycle: str
    reconciliation_state: str

    def __post_init__(self) -> None:
        if self.schema_version != "lifecycle-facts/v1":
            raise ValueError("unsupported lifecycle facts schema")
        if not all(
            (
                self.grid_lifecycle,
                self.epoch_transition_state,
                self.runtime_lifecycle,
                self.reconciliation_state,
            )
        ):
            raise ValueError("separate lifecycle facts are required")


@dataclass(frozen=True, slots=True)
class SafetyRecoveryFacts:
    schema_version: str
    prior_frozen_latched: bool
    frozen_recovery_approved: bool

    def __post_init__(self) -> None:
        if self.schema_version != "safety-recovery-facts/v1":
            raise ValueError("unsupported safety recovery facts schema")


@dataclass(frozen=True, slots=True)
class RecoveryObligation:
    obligation_id: str
    side: str
    price: ExactDecimal
    fully_backed: bool
    inventory_reducing: bool
    inside_outer_rungs: bool

    def __post_init__(self) -> None:
        if not self.obligation_id.startswith("sha256:"):
            raise ValueError("recovery obligation identity is required")
        if self.side not in {"BUY", "SELL"}:
            raise ValueError("recovery obligation side must be BUY or SELL")
        if self.price.kind != "price" or self.price.decimal <= 0:
            raise ValueError("recovery obligation price must be positive")


@dataclass(frozen=True, slots=True)
class VenueConditionEvidence:
    schema_version: str
    condition: SymbolCondition
    observed_at: DomainTime
    evidence_id: str
    source: str
    wind_down_deadline: DomainTime | None

    def __post_init__(self) -> None:
        if self.schema_version != "venue-condition-evidence/v1":
            raise ValueError("unsupported venue condition evidence schema")
        if not self.evidence_id.startswith("sha256:") or not self.source:
            raise ValueError("venue condition evidence identity and source are required")
        if self.condition is SymbolCondition.DELISTING:
            if (
                self.wind_down_deadline is None
                or self.wind_down_deadline.value <= self.observed_at.value
            ):
                raise ValueError("delisting evidence requires a future wind-down deadline")
        elif self.wind_down_deadline is not None:
            raise ValueError("only delisting evidence may carry a wind-down deadline")

    @classmethod
    def trading(cls) -> VenueConditionEvidence:
        observed_at = DomainTime(datetime(1970, 1, 1, tzinfo=timezone.utc))
        return cls(
            schema_version="venue-condition-evidence/v1",
            condition=SymbolCondition.TRADING,
            observed_at=observed_at,
            evidence_id=content_identity(
                "venue-condition-evidence/v1",
                {"condition": SymbolCondition.TRADING, "observed_at": observed_at},
            ),
            source="canonical-fixture",
            wind_down_deadline=None,
        )


@dataclass(frozen=True, slots=True)
class SafetyHazard:
    code: str
    posture: SafetyPosture
    severity: int
    evidence_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "evidence_ids", tuple(sorted(self.evidence_ids)))
        if not self.code or self.severity != _severity(self.posture):
            raise ValueError("safety hazard posture severity is invalid")


@dataclass(frozen=True, slots=True)
class SafetyEvaluation:
    schema_version: str
    decision_time: DomainTime
    input_fingerprint: str
    posture: SafetyPosture
    hazards: tuple[SafetyHazard, ...]
    reason_codes: tuple[str, ...]
    loss_warning: bool
    daily_loss_latched: bool
    run_drawdown_latched: bool
    global_stop_latched: bool
    allowed_command_classes: tuple[AllowedCommandClass, ...]
    placement_allowed: bool
    replacement_allowed: bool
    downward_bound_shift_allowed: bool
    fixed_quote_sizing_increase_allowed: bool
    permitted_recovery_obligation_ids: tuple[str, ...]
    clock_offset: ExactDecimal
    scheduling_delay: ExactDecimal
    round_trip_latency: ExactDecimal
    lifecycle: LifecycleFacts
    freshness: tuple[FreshnessEvidence, ...]
    venue_evidence_id: str
    wind_down_deadline: DomainTime | None

    def __post_init__(self) -> None:
        object.__setattr__(self, "hazards", tuple(self.hazards))
        object.__setattr__(self, "reason_codes", tuple(self.reason_codes))
        object.__setattr__(self, "allowed_command_classes", tuple(self.allowed_command_classes))
        object.__setattr__(
            self,
            "permitted_recovery_obligation_ids",
            tuple(self.permitted_recovery_obligation_ids),
        )
        object.__setattr__(self, "freshness", tuple(self.freshness))
        if self.schema_version != "safety-evaluation/v1":
            raise ValueError("unsupported safety evaluation schema")
        if not self.input_fingerprint.startswith("sha256:"):
            raise ValueError("safety input fingerprint is required")
        if self.posture is SafetyPosture.TERMINAL_LIQUIDATION and not self.global_stop_latched:
            raise ValueError("terminal liquidation posture must be latched")

    @property
    def fingerprint(self) -> str:
        return content_identity("safety-evaluation/v1", self)


def _severity(posture: SafetyPosture) -> int:
    return {
        SafetyPosture.NORMAL: 0,
        SafetyPosture.REDUCE_ONLY: 1,
        SafetyPosture.TERMINAL_LIQUIDATION: 2,
        SafetyPosture.FROZEN: 3,
        SafetyPosture.CLOSED: 4,
    }[posture]


def _hazard(
    hazards: list[SafetyHazard],
    code: str,
    posture: SafetyPosture,
    *evidence_ids: str,
) -> None:
    hazards.append(SafetyHazard(code, posture, _severity(posture), tuple(evidence_ids)))


def _loss_threshold(initial: Decimal, ratio: str, amount: str) -> Decimal:
    return min(initial * Decimal(ratio), Decimal(amount))


def _seconds(value: timedelta) -> ExactDecimal:
    total_microseconds = (value.days * 86_400 + value.seconds) * 1_000_000 + value.microseconds
    exact_seconds = Decimal(total_microseconds) / Decimal("1000000")
    return ExactDecimal.parse(
        format(exact_seconds, ".6f"),
        kind="duration_seconds",
    )


def evaluate_safety_posture(
    *,
    decision_time: DomainTime,
    capital: CapitalCommitmentFacts,
    loss: LossFacts,
    freshness: tuple[FreshnessEvidence, ...],
    clock: ClockEvidence,
    lifecycle: LifecycleFacts,
    recovery: SafetyRecoveryFacts,
    range_condition: RangeCondition,
    recovery_obligations: tuple[RecoveryObligation, ...],
    venue: VenueConditionEvidence,
    prior_global_stop_latched: bool,
) -> SafetyEvaluation:
    evidence = tuple(sorted(freshness, key=lambda item: item.evidence_class.value))
    if {item.evidence_class for item in evidence} != set(EvidenceClass):
        raise ValueError("exactly one freshness fact per evidence class is required")
    if len(evidence) != len(EvidenceClass):
        raise ValueError("freshness evidence classes must be unique")
    hazards: list[SafetyHazard] = []

    if capital.capital_envelope.decimal > Decimal("250"):
        _hazard(
            hazards,
            "capital_envelope_exceeds_mvp_ceiling",
            SafetyPosture.FROZEN,
            capital.allocation_fingerprint,
        )
    required_fee_reserve = max(
        Decimal("5"),
        Decimal("2")
        * (capital.projected_obligation_fees.decimal + capital.projected_terminal_fees.decimal),
    )
    if capital.fee_reserve.decimal < required_fee_reserve:
        _hazard(
            hazards,
            "fee_reserve_is_insufficient",
            SafetyPosture.REDUCE_ONLY,
            capital.allocation_fingerprint,
        )
    if (
        capital.committed_principal.decimal + capital.fee_reserve.decimal
        > capital.capital_envelope.decimal
    ):
        _hazard(
            hazards,
            "worst_case_commitment_exceeds_envelope",
            SafetyPosture.FROZEN,
            capital.allocation_fingerprint,
        )
    if any(
        principal.decimal > Decimal("20")
        for principal in capital.exposure_increasing_buy_principals
    ):
        _hazard(
            hazards,
            "buy_principal_exceeds_ceiling",
            SafetyPosture.FROZEN,
            capital.epoch_id,
        )
    if capital.effective_managed_orders > 20:
        _hazard(
            hazards,
            "effective_order_capacity_exceeded",
            SafetyPosture.REDUCE_ONLY,
            capital.epoch_id,
        )
    required_headroom = max(
        10,
        int(
            (Decimal(capital.authenticated_order_limit) * Decimal("0.20")).to_integral_value(
                rounding=ROUND_CEILING
            )
        ),
    )
    available_headroom = (
        capital.authenticated_order_limit
        - capital.foreign_open_orders
        - capital.effective_managed_orders
    )
    if available_headroom < required_headroom:
        _hazard(
            hazards,
            "venue_order_headroom_is_insufficient",
            SafetyPosture.REDUCE_ONLY,
            capital.epoch_id,
        )
    worst_inventory = max(
        capital.current_inventory.decimal
        + capital.pending_buy_inventory.decimal
        + capital.transition_bootstrap_inventory.decimal,
        capital.proposed_maximum_inventory.decimal,
    )
    if worst_inventory > capital.maximum_planned_inventory.decimal:
        _hazard(
            hazards,
            "maximum_planned_inventory_exceeded",
            SafetyPosture.REDUCE_ONLY,
            capital.allocation_fingerprint,
            capital.epoch_id,
        )

    initial = loss.initial_equity.decimal
    current = loss.conservative_liquidation_equity.decimal
    daily_decline = max(loss.risk_day_baseline.decimal - current, Decimal("0"))
    drawdown = max(loss.run_high_water_mark.decimal - current, Decimal("0"))
    terminal_decline = max(initial - current, Decimal("0"))
    daily_threshold = _loss_threshold(loss.risk_day_baseline.decimal, "0.02", "5")
    drawdown_threshold = _loss_threshold(loss.run_high_water_mark.decimal, "0.08", "20")
    terminal_threshold = _loss_threshold(initial, "0.12", "30")
    loss_warning = any(
        decline >= threshold * Decimal("0.80")
        for decline, threshold in (
            (daily_decline, daily_threshold),
            (drawdown, drawdown_threshold),
            (terminal_decline, terminal_threshold),
        )
    )
    daily_breached = daily_decline >= daily_threshold
    drawdown_breached = drawdown >= drawdown_threshold
    guardrail_recovery_complete = (
        loss.guardrail_recovery_approved and lifecycle.reconciliation_state == "RECONCILED"
    )
    daily_loss_latched = daily_breached or (
        loss.prior_daily_loss_latched and not guardrail_recovery_complete
    )
    run_drawdown_latched = drawdown_breached or (
        loss.prior_run_drawdown_latched and not guardrail_recovery_complete
    )
    if daily_loss_latched:
        _hazard(hazards, "daily_loss_threshold_reached", SafetyPosture.REDUCE_ONLY)
    if run_drawdown_latched:
        _hazard(hazards, "run_drawdown_threshold_reached", SafetyPosture.REDUCE_ONLY)
    global_stop_latched = (
        prior_global_stop_latched
        or loss.global_stop_latched
        or terminal_decline >= terminal_threshold
    )
    if global_stop_latched:
        _hazard(
            hazards,
            "terminal_equity_global_stop_latched",
            SafetyPosture.TERMINAL_LIQUIDATION,
        )

    for item in evidence:
        age = None if item.observed_at is None else decision_time.value - item.observed_at.value
        unhealthy = item.condition is not EvidenceCondition.HEALTHY or (
            age is not None and age < timedelta(0)
        )
        if item.evidence_class is EvidenceClass.VALUATION and (
            unhealthy or age is None or age > timedelta(seconds=5)
        ):
            _hazard(
                hazards,
                "valuation_evidence_missing_or_stale",
                SafetyPosture.FROZEN,
                item.evidence_id,
            )
        elif item.evidence_class is EvidenceClass.STRATEGY_INPUT and (
            unhealthy or age is None or age > timedelta(seconds=15)
        ):
            _hazard(
                hazards,
                "strategy_input_missing_or_stale",
                SafetyPosture.REDUCE_ONLY,
                item.evidence_id,
            )
        elif item.evidence_class is EvidenceClass.PRIVATE_STREAM and unhealthy:
            _hazard(
                hazards,
                "private_stream_continuity_unhealthy",
                SafetyPosture.FROZEN,
                item.evidence_id,
            )
        elif item.evidence_class is EvidenceClass.CONTROL_PATH and (
            item.condition is EvidenceCondition.MISSING
            or age is None
            or age >= timedelta(seconds=10)
            or unhealthy
        ):
            _hazard(
                hazards,
                "authenticated_control_path_unavailable",
                SafetyPosture.FROZEN,
                item.evidence_id,
            )
        elif item.evidence_class is EvidenceClass.CLOCK and unhealthy:
            _hazard(
                hazards,
                "clock_evidence_missing_or_stale",
                SafetyPosture.FROZEN,
                item.evidence_id,
            )

    scheduling_delay_delta = clock.response_received_at.value - clock.request_sent_at.value
    midpoint = clock.request_sent_at.value + scheduling_delay_delta / 2
    clock_offset_delta = clock.venue_time.value - midpoint
    if (
        clock.condition is not EvidenceCondition.HEALTHY
        or clock.response_received_at.value > decision_time.value
    ):
        _hazard(
            hazards,
            "clock_observation_unhealthy",
            SafetyPosture.FROZEN,
            clock.evidence_id,
        )
    if abs(clock_offset_delta) > timedelta(milliseconds=500):
        _hazard(
            hazards,
            "clock_offset_exceeds_500ms",
            SafetyPosture.FROZEN,
            clock.evidence_id,
        )
    if clock.authenticated_timestamp_rejected:
        _hazard(
            hazards,
            "authenticated_timestamp_rejection",
            SafetyPosture.FROZEN,
            clock.evidence_id,
        )

    if lifecycle.adaptation_state is AdaptationState.TREND_DOWN:
        _hazard(
            hazards,
            "confirmed_downtrend",
            SafetyPosture.REDUCE_ONLY,
        )
    elif lifecycle.adaptation_state is AdaptationState.UNCERTAIN:
        _hazard(
            hazards,
            "uncertain_adaptation_evidence",
            SafetyPosture.FROZEN,
        )
    if range_condition is not RangeCondition.IN_RANGE:
        _hazard(
            hazards,
            "range_exhausted",
            SafetyPosture.REDUCE_ONLY,
        )

    if venue.condition in {SymbolCondition.SUSPENDED, SymbolCondition.MAINTENANCE}:
        _hazard(
            hazards,
            f"symbol_{venue.condition.value.lower()}",
            SafetyPosture.FROZEN,
            venue.evidence_id,
        )
    elif venue.condition is SymbolCondition.DELISTING:
        _hazard(
            hazards,
            "symbol_delisting_wind_down",
            SafetyPosture.REDUCE_ONLY,
            venue.evidence_id,
        )

    if lifecycle.grid_lifecycle == "CLOSED":
        _hazard(hazards, "grid_lifecycle_closed", SafetyPosture.CLOSED)

    current_frozen = any(item.posture is SafetyPosture.FROZEN for item in hazards)
    if (
        recovery.prior_frozen_latched
        and not current_frozen
        and not (
            recovery.frozen_recovery_approved and lifecycle.reconciliation_state == "RECONCILED"
        )
    ):
        _hazard(
            hazards,
            "material_frozen_incident_requires_recovery",
            SafetyPosture.FROZEN,
        )

    hazards.sort(key=lambda item: (-item.severity, item.code, item.evidence_ids))
    posture = hazards[0].posture if hazards else SafetyPosture.NORMAL
    allowed: set[AllowedCommandClass]
    if posture is SafetyPosture.NORMAL:
        allowed = {
            AllowedCommandClass.EXPOSURE_INCREASING,
            AllowedCommandClass.INVENTORY_REDUCING,
            AllowedCommandClass.PLACEMENT,
            AllowedCommandClass.REPLACEMENT,
            AllowedCommandClass.CANCELLATION,
            AllowedCommandClass.RECONCILIATION,
            AllowedCommandClass.EVIDENCE_GATHERING,
        }
    elif posture is SafetyPosture.REDUCE_ONLY:
        allowed = {
            AllowedCommandClass.INVENTORY_REDUCING,
            AllowedCommandClass.REPLACEMENT,
            AllowedCommandClass.CANCELLATION,
            AllowedCommandClass.RECONCILIATION,
            AllowedCommandClass.EVIDENCE_GATHERING,
        }
    elif posture is SafetyPosture.FROZEN:
        allowed = {
            AllowedCommandClass.CANCELLATION,
            AllowedCommandClass.RECONCILIATION,
            AllowedCommandClass.EVIDENCE_GATHERING,
        }
    elif posture is SafetyPosture.TERMINAL_LIQUIDATION:
        allowed = {
            AllowedCommandClass.INVENTORY_REDUCING,
            AllowedCommandClass.CANCELLATION,
            AllowedCommandClass.RECONCILIATION,
            AllowedCommandClass.EVIDENCE_GATHERING,
        }
    else:
        allowed = {AllowedCommandClass.EVIDENCE_GATHERING}
    if lifecycle.adaptation_state is AdaptationState.UNCERTAIN:
        allowed.discard(AllowedCommandClass.PLACEMENT)
        allowed.discard(AllowedCommandClass.REPLACEMENT)
    if lifecycle.adaptation_state is AdaptationState.TREND_DOWN:
        allowed.discard(AllowedCommandClass.EXPOSURE_INCREASING)
        allowed.discard(AllowedCommandClass.PLACEMENT)

    permitted_recovery = tuple(
        sorted(
            item.obligation_id
            for item in recovery_obligations
            if item.fully_backed and item.inventory_reducing and item.inside_outer_rungs
        )
    )
    input_fingerprint = content_identity(
        "safety-input/v1",
        {
            "decision_time": decision_time,
            "capital": capital,
            "loss": loss,
            "freshness": evidence,
            "clock": clock,
            "lifecycle": lifecycle,
            "recovery": recovery,
            "range_condition": range_condition,
            "recovery_obligations": recovery_obligations,
            "venue": venue,
            "prior_global_stop_latched": prior_global_stop_latched,
        },
    )
    return SafetyEvaluation(
        schema_version="safety-evaluation/v1",
        decision_time=decision_time,
        input_fingerprint=input_fingerprint,
        posture=posture,
        hazards=tuple(hazards),
        reason_codes=tuple(item.code for item in hazards),
        loss_warning=loss_warning,
        daily_loss_latched=daily_loss_latched,
        run_drawdown_latched=run_drawdown_latched,
        global_stop_latched=global_stop_latched,
        allowed_command_classes=tuple(sorted(allowed, key=lambda item: item.value)),
        placement_allowed=AllowedCommandClass.PLACEMENT in allowed,
        replacement_allowed=AllowedCommandClass.REPLACEMENT in allowed,
        downward_bound_shift_allowed=False,
        fixed_quote_sizing_increase_allowed=False,
        permitted_recovery_obligation_ids=permitted_recovery,
        clock_offset=_seconds(clock_offset_delta),
        scheduling_delay=clock.scheduling_delay,
        round_trip_latency=_seconds(scheduling_delay_delta),
        lifecycle=lifecycle,
        freshness=evidence,
        venue_evidence_id=venue.evidence_id,
        wind_down_deadline=venue.wind_down_deadline,
    )
