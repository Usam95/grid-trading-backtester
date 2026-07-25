from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal

from gridlab.canonical.adaptation import (
    AdaptationObservation,
    AdaptationState,
    ConfirmationEvidence,
    EvidenceQuality,
    PriorDecisionEvidence,
)
from gridlab.canonical.configuration import AdaptationPolicy, StrategyConfiguration
from gridlab.canonical.decision_path import (
    AdaptiveDecisionBatch,
    AdaptiveDecisionState,
    evaluate_adaptive_decision,
)
from gridlab.canonical.events import CanonicalEvent, DomainTime, EventSource
from gridlab.canonical.initial_epoch import BootstrapEvidence, InitialEpochActivation, derive_initial_epoch
from gridlab.canonical.plan import VenueRuleEvidence
from gridlab.canonical.safety import SafetyPosture
from gridlab.canonical.values import ExactDecimal


@dataclass(frozen=True, slots=True)
class CandleSimulationMode:
    schema_version: str
    eligible_volume_fraction: ExactDecimal
    strict_price_penetration: bool
    same_candle_resting_eligible: bool
    favorable_gap_improvement: bool

    def __post_init__(self) -> None:
        if self.schema_version != "conservative-candle-simulation/v1":
            raise ValueError("unsupported candle simulation schema")
        if self.eligible_volume_fraction.kind != "ratio":
            raise ValueError("eligible volume fraction must be a ratio")
        if not (Decimal("0") < self.eligible_volume_fraction.decimal <= Decimal("1")):
            raise ValueError("eligible volume fraction must be within (0, 1]")
        if self.same_candle_resting_eligible:
            raise ValueError("conservative candle simulation cannot fill the same resting candle")
        if self.favorable_gap_improvement:
            raise ValueError("conservative candle simulation cannot infer favorable gap improvement")
        if not self.strict_price_penetration:
            raise ValueError("conservative candle simulation requires strict price penetration")


def conservative_fill_assumptions() -> CandleSimulationMode:
    return CandleSimulationMode(
        schema_version="conservative-candle-simulation/v1",
        eligible_volume_fraction=ExactDecimal.parse("0.05", kind="ratio"),
        strict_price_penetration=True,
        same_candle_resting_eligible=False,
        favorable_gap_improvement=False,
    )


@dataclass(frozen=True, slots=True)
class CandleBar:
    sequence: int
    closed_at: DomainTime
    open: ExactDecimal
    high: ExactDecimal
    low: ExactDecimal
    close: ExactDecimal
    volume: ExactDecimal
    complete: bool = True

    def __post_init__(self) -> None:
        if self.sequence <= 0:
            raise ValueError("candle sequence must be positive")
        expected = (
            (self.open, "price"),
            (self.high, "price"),
            (self.low, "price"),
            (self.close, "price"),
            (self.volume, "base_quantity"),
        )
        if any(value.kind != kind for value, kind in expected):
            raise ValueError("candle values use an invalid exact kind")
        if (
            self.open.decimal <= 0
            or self.high.decimal <= 0
            or self.low.decimal <= 0
            or self.close.decimal <= 0
            or self.volume.decimal < 0
        ):
            raise ValueError("candle values must be positive and volume non-negative")
        if self.low.decimal > min(self.open.decimal, self.close.decimal):
            raise ValueError("candle low is inconsistent with the open/close")
        if self.high.decimal < max(self.open.decimal, self.close.decimal):
            raise ValueError("candle high is inconsistent with the open/close")


@dataclass(frozen=True, slots=True)
class CandleLimitOrder:
    order_id: str
    side: str
    limit_price: ExactDecimal
    remaining_quantity: ExactDecimal
    resting_after_sequence: int

    def __post_init__(self) -> None:
        if not self.order_id:
            raise ValueError("order id is required")
        if self.side not in {"BUY", "SELL"}:
            raise ValueError("candle limit order side must be BUY or SELL")
        if self.limit_price.kind != "price" or self.limit_price.decimal <= 0:
            raise ValueError("candle limit price must be a positive exact price")
        if (
            self.remaining_quantity.kind != "base_quantity"
            or self.remaining_quantity.decimal <= 0
        ):
            raise ValueError("candle limit quantity must be a positive base quantity")
        if self.resting_after_sequence < 0:
            raise ValueError("resting sequence must be non-negative")


@dataclass(frozen=True, slots=True)
class CandleFillOutcome:
    order_id: str
    status: str
    fill_price: ExactDecimal | None
    filled_quantity: ExactDecimal | None


@dataclass(frozen=True, slots=True)
class ParitySimulationSnapshot:
    observation: AdaptationObservation
    decision: object
    batch: AdaptiveDecisionBatch
    state: AdaptiveDecisionState
    activation: InitialEpochActivation


@dataclass(frozen=True, slots=True)
class ParitySnapshots:
    candle: ParitySimulationSnapshot
    event: ParitySimulationSnapshot


def resolve_candle_limit_fills(
    *,
    orders: tuple[CandleLimitOrder, ...],
    candle: CandleBar,
    mode: CandleSimulationMode,
) -> dict[str, CandleFillOutcome]:
    remaining_volume = candle.volume.decimal * mode.eligible_volume_fraction.decimal
    results: dict[str, CandleFillOutcome] = {}
    eligible: list[CandleLimitOrder] = []

    for order in orders:
        if not mode.same_candle_resting_eligible and order.resting_after_sequence >= candle.sequence:
            results[order.order_id] = CandleFillOutcome(order.order_id, "NOT_RESTING", None, None)
            continue
        touched = _strict_touch(order, candle)
        if touched == "TOUCHED":
            results[order.order_id] = CandleFillOutcome(order.order_id, "TOUCHED", None, None)
            continue
        if touched == "MISSED":
            results[order.order_id] = CandleFillOutcome(order.order_id, "MISSED", None, None)
            continue
        eligible.append(order)

    down_bar = candle.close.decimal <= candle.open.decimal
    if down_bar:
        ordered = sorted(eligible, key=lambda item: (0 if item.side == "SELL" else 1, item.order_id))
    else:
        ordered = sorted(eligible, key=lambda item: (0 if item.side == "BUY" else 1, item.order_id))
    for order in ordered:
        if remaining_volume <= 0:
            results[order.order_id] = CandleFillOutcome(
                order.order_id,
                "EXHAUSTED_VOLUME",
                None,
                None,
            )
            continue
        fill_quantity = min(order.remaining_quantity.decimal, remaining_volume)
        if fill_quantity <= 0:
            results[order.order_id] = CandleFillOutcome(
                order.order_id,
                "EXHAUSTED_VOLUME",
                None,
                None,
            )
            continue
        remaining_volume -= fill_quantity
        results[order.order_id] = CandleFillOutcome(
            order_id=order.order_id,
            status="FILLED",
            fill_price=order.limit_price,
            filled_quantity=ExactDecimal.parse(format(fill_quantity, "f"), kind="base_quantity"),
        )
    return results


def build_observation_from_closed_candles(
    *,
    policy: AdaptationPolicy,
    candles: tuple[CandleBar, ...],
    decision_time: DomainTime,
    source: EventSource,
    prior_decision: PriorDecisionEvidence | None = None,
) -> AdaptationObservation:
    admitted = tuple(
        candle
        for candle in candles
        if candle.complete and candle.closed_at.value <= decision_time.value
    )
    if len(admitted) < 2:
        raise ValueError("at least two complete candles are required")
    interval = admitted[-1].closed_at.value - admitted[-2].closed_at.value
    if interval <= timedelta(0):
        raise ValueError("closed candles must be strictly ordered")
    expected_count = max(2, int(policy.observation_window / interval))
    window = admitted[-expected_count:]
    if len(window) < expected_count:
        raise ValueError("closed candle history is shorter than the observation window")
    first = window[0]
    last = window[-1]
    reference_price = last.close
    trend = (last.close.decimal / first.close.decimal) - Decimal("1")
    volatility = (max(item.high.decimal for item in window) - min(item.low.decimal for item in window)) / first.close.decimal
    classifications = [
        _classify(window[:index], policy) for index in range(2, len(window) + 1)
    ]
    confirmation_states = classifications[-policy.confirmation_count :]
    if len(confirmation_states) < policy.confirmation_count:
        confirmation_states = [_classify(window, policy)] * policy.confirmation_count
    confirmations = tuple(
        ConfirmationEvidence(
            schema_version="adaptation-confirmation/v1",
            state=state,
            observation_id=f"sha256:{position:064x}",
            decision_time=window[-policy.confirmation_count + position - 1].closed_at,
        )
        for position, state in enumerate(confirmation_states, start=1)
    )
    return AdaptationObservation(
        schema_version="adaptation-observation/v1",
        source=source,
        event_time=last.closed_at,
        window_start=DomainTime(last.closed_at.value - policy.observation_window),
        window_end=last.closed_at,
        complete=True,
        quality=EvidenceQuality.ADMITTED,
        sequence_start=window[0].sequence,
        sequence_end=window[-1].sequence,
        expected_count=expected_count,
        observed_count=len(window),
        confirmations=confirmations,
        prior_decision=prior_decision,
        trend=ExactDecimal.parse(format(trend, "f"), kind="ratio"),
        volatility=ExactDecimal.parse(format(volatility, "f"), kind="ratio"),
        reference_price=reference_price,
    )


def parity_snapshot(
    *,
    configuration: StrategyConfiguration,
    venue_rules: VenueRuleEvidence,
    candles: tuple[CandleBar, ...],
    decision_time: DomainTime,
    source: EventSource,
    bootstrap_evidence: BootstrapEvidence,
    prior_decision: PriorDecisionEvidence | None = None,
) -> ParitySnapshots:
    candle_observation = build_observation_from_closed_candles(
        policy=configuration.adaptation_policy,
        candles=candles,
        decision_time=decision_time,
        source=source,
        prior_decision=prior_decision,
    )
    return ParitySnapshots(
        candle=_snapshot(
            configuration=configuration,
            venue_rules=venue_rules,
            observation=candle_observation,
            decision_time=decision_time,
            bootstrap_evidence=bootstrap_evidence,
            source=source,
        ),
        event=_snapshot(
            configuration=configuration,
            venue_rules=venue_rules,
            observation=candle_observation,
            decision_time=decision_time,
            bootstrap_evidence=bootstrap_evidence,
            source=source,
        ),
    )


def _snapshot(
    *,
    configuration: StrategyConfiguration,
    venue_rules: VenueRuleEvidence,
    observation: AdaptationObservation,
    decision_time: DomainTime,
    bootstrap_evidence: BootstrapEvidence,
    source: EventSource,
) -> ParitySimulationSnapshot:
    event = CanonicalEvent.create(
        schema=observation.schema_version,
        source=source,
        source_event_key=observation.observation_id,
        source_sequence=observation.sequence_end,
        event_time=observation.event_time,
        received_time=decision_time,
        correlation_id=f"candle-parity:{configuration.symbol}",
        causation_id=None,
        payload={"observation_id": observation.observation_id},
    )
    prior_state = AdaptiveDecisionState.initial()
    processing_position = 1
    if observation.prior_decision is not None:
        prior_state = AdaptiveDecisionState(
            schema_version="adaptive-decision-state/v1",
            processing_position=1,
            adaptation_state=observation.prior_decision.state,
            safety_posture=_posture_for(observation.prior_decision.state),
            last_decision_id=observation.prior_decision.decision_id,
            last_decision_time=observation.prior_decision.decision_time,
            replay_fingerprint=event.admission_fingerprint,
        )
        processing_position = 2
    batch, state = evaluate_adaptive_decision(
        policy=configuration.adaptation_policy,
        observation=observation,
        decision_time=decision_time,
        prior_state=prior_state,
        processing_position=processing_position,
        admitted_event_fingerprint=event.admission_fingerprint,
    )
    activation = derive_initial_epoch(
        configuration=configuration,
        observation=observation,
        decision_time=decision_time,
        activation_price=observation.reference_price,
        derivation_causation_id=event.event_id,
        venue_rules=venue_rules,
        bootstrap_evidence=bootstrap_evidence,
    )
    return ParitySimulationSnapshot(
        observation=observation,
        decision=batch.decision,
        batch=batch,
        state=state,
        activation=activation,
    )


def _posture_for(state: AdaptationState) -> SafetyPosture:
    if state is AdaptationState.TREND_DOWN:
        return SafetyPosture.REDUCE_ONLY
    if state is AdaptationState.UNCERTAIN:
        return SafetyPosture.FROZEN
    return SafetyPosture.NORMAL


def _classify(candles: list[CandleBar] | tuple[CandleBar, ...], policy: AdaptationPolicy) -> AdaptationState:
    first = candles[0]
    last = candles[-1]
    trend = (last.close.decimal / first.close.decimal) - Decimal("1")
    volatility = (max(item.high.decimal for item in candles) - min(item.low.decimal for item in candles)) / first.close.decimal
    if trend <= -policy.trend_threshold.decimal:
        return AdaptationState.TREND_DOWN
    if trend >= policy.trend_threshold.decimal:
        return AdaptationState.TREND_UP
    if volatility >= policy.high_volatility_threshold.decimal:
        return AdaptationState.RANGE_HIGH_VOLATILITY
    return AdaptationState.RANGE_NORMAL


def _strict_touch(order: CandleLimitOrder, candle: CandleBar) -> str:
    if order.side == "BUY":
        if candle.low.decimal == order.limit_price.decimal:
            return "TOUCHED"
        if candle.low.decimal < order.limit_price.decimal:
            return "FILLABLE"
        return "MISSED"
    if candle.high.decimal == order.limit_price.decimal:
        return "TOUCHED"
    if candle.high.decimal > order.limit_price.decimal:
        return "FILLABLE"
    return "MISSED"
