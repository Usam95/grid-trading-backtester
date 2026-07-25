from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

from gridlab.canonical._identity import content_identity
from gridlab.canonical.configuration import AdaptationPolicy
from gridlab.canonical.events import DomainTime, EventSource
from gridlab.canonical.values import ExactDecimal


class EvidenceQuality(str, Enum):
    ADMITTED = "ADMITTED"
    INCOMPLETE = "INCOMPLETE"
    STALE = "STALE"
    GAPPED = "GAPPED"
    CONTRADICTORY = "CONTRADICTORY"
    AMBIGUOUS = "AMBIGUOUS"


class AdaptationState(str, Enum):
    RANGE_NORMAL = "RANGE_NORMAL"
    RANGE_HIGH_VOLATILITY = "RANGE_HIGH_VOLATILITY"
    TREND_UP = "TREND_UP"
    TREND_DOWN = "TREND_DOWN"
    UNCERTAIN = "UNCERTAIN"


class DecisionIntent(str, Enum):
    SYMMETRIC = "SYMMETRIC"
    WIDEN = "WIDEN"
    SHIFT_UP = "SHIFT_UP"
    REDUCE_ONLY = "REDUCE_ONLY"
    FROZEN = "FROZEN"


@dataclass(frozen=True, slots=True)
class ConfirmationEvidence:
    schema_version: str
    state: AdaptationState
    observation_id: str
    decision_time: DomainTime

    def __post_init__(self) -> None:
        if self.schema_version != "adaptation-confirmation/v1":
            raise ValueError("unsupported adaptation confirmation schema version")
        if not self.observation_id:
            raise ValueError("confirmation observation identity is required")

    @property
    def confirmation_id(self) -> str:
        return content_identity("adaptation-confirmation/v1", self)


@dataclass(frozen=True, slots=True)
class PriorDecisionEvidence:
    state: AdaptationState
    decision_id: str
    decision_time: DomainTime

    def __post_init__(self) -> None:
        if not self.decision_id:
            raise ValueError("prior decision identity is required")


@dataclass(frozen=True, slots=True)
class AdaptationObservation:
    schema_version: str
    source: EventSource
    event_time: DomainTime
    window_start: DomainTime
    window_end: DomainTime
    complete: bool
    quality: EvidenceQuality
    sequence_start: int
    sequence_end: int
    expected_count: int
    observed_count: int
    confirmations: tuple[ConfirmationEvidence, ...]
    prior_decision: PriorDecisionEvidence | None
    trend: ExactDecimal
    volatility: ExactDecimal
    reference_price: ExactDecimal

    def __post_init__(self) -> None:
        if self.schema_version != "adaptation-observation/v1":
            raise ValueError("unsupported adaptation observation schema version")
        object.__setattr__(self, "confirmations", tuple(self.confirmations))
        if self.window_start.value >= self.window_end.value:
            raise ValueError("observation window must have positive duration")
        if self.event_time != self.window_end:
            raise ValueError("observation event time must equal its closed window end")
        if self.sequence_start < 0 or self.sequence_end < self.sequence_start:
            raise ValueError("observation sequence range is invalid")
        if self.expected_count < 1 or self.observed_count < 0:
            raise ValueError("observation counts are invalid")
        confirmation_times = tuple(
            confirmation.decision_time.value for confirmation in self.confirmations
        )
        if confirmation_times != tuple(sorted(confirmation_times)):
            raise ValueError("classification confirmations must be time ordered")
        if any(value > self.event_time.value for value in confirmation_times):
            raise ValueError("classification confirmations must be past-only")
        if len({item.confirmation_id for item in self.confirmations}) != len(self.confirmations):
            raise ValueError("classification confirmations must be unique")
        if (
            self.prior_decision is not None
            and self.prior_decision.decision_time.value > self.event_time.value
        ):
            raise ValueError("prior decision evidence must be past-only")
        if self.volatility.decimal < 0 or self.reference_price.decimal <= 0:
            raise ValueError("volatility must be non-negative and price positive")
        if self.trend.kind != "ratio" or self.volatility.kind != "ratio":
            raise ValueError("trend and volatility observations must use ratio values")
        if self.reference_price.kind != "price":
            raise ValueError("reference price observation must use price values")

    @property
    def observation_id(self) -> str:
        return content_identity("adaptation-observation/v1", self)


@dataclass(frozen=True, slots=True)
class AdaptationDecision:
    schema_version: str
    policy_id: str
    observation_id: str
    decision_time: DomainTime
    state: AdaptationState
    intent: DecisionIntent
    reason: str
    permits_exposure_increasing_buy: bool
    requested_bound_shift: ExactDecimal | None

    def __post_init__(self) -> None:
        if self.schema_version != "adaptation-decision/v1":
            raise ValueError("unsupported adaptation decision schema version")
        if not self.policy_id or not self.observation_id or not self.reason:
            raise ValueError("adaptation decision identities and reason are required")
        expected = {
            AdaptationState.RANGE_NORMAL: (DecisionIntent.SYMMETRIC, True, False),
            AdaptationState.RANGE_HIGH_VOLATILITY: (
                DecisionIntent.WIDEN,
                True,
                False,
            ),
            AdaptationState.TREND_UP: (DecisionIntent.SHIFT_UP, True, True),
            AdaptationState.TREND_DOWN: (
                DecisionIntent.REDUCE_ONLY,
                False,
                False,
            ),
            AdaptationState.UNCERTAIN: (DecisionIntent.FROZEN, False, False),
        }
        intent, permits_buy, requires_shift = expected[self.state]
        if self.intent is not intent or self.permits_exposure_increasing_buy is not permits_buy:
            raise ValueError("adaptation decision state, intent, and buy permission conflict")
        if requires_shift:
            if (
                self.requested_bound_shift is None
                or self.requested_bound_shift.kind != "ratio"
                or self.requested_bound_shift.decimal < 0
            ):
                raise ValueError("TREND_UP decision requires a non-negative ratio shift")
        elif self.requested_bound_shift is not None:
            raise ValueError("only TREND_UP may request a bound shift")

    @property
    def decision_id(self) -> str:
        return content_identity("adaptation-decision/v1", self)


def _uncertain(
    policy: AdaptationPolicy,
    observation: AdaptationObservation,
    decision_time: DomainTime,
    reason: str,
) -> AdaptationDecision:
    return AdaptationDecision(
        schema_version="adaptation-decision/v1",
        policy_id=policy.policy_id,
        observation_id=observation.observation_id,
        decision_time=decision_time,
        state=AdaptationState.UNCERTAIN,
        intent=DecisionIntent.FROZEN,
        reason=reason,
        permits_exposure_increasing_buy=False,
        requested_bound_shift=None,
    )


def decide_adaptation(
    policy: AdaptationPolicy,
    observation: AdaptationObservation,
    decision_time: DomainTime,
) -> AdaptationDecision:
    if not observation.complete or observation.quality is not EvidenceQuality.ADMITTED:
        return _uncertain(policy, observation, decision_time, "evidence_not_admitted")
    if observation.event_time.value > decision_time.value:
        return _uncertain(policy, observation, decision_time, "future_evidence")
    if decision_time.value - observation.event_time.value > policy.maximum_observation_age:
        return _uncertain(policy, observation, decision_time, "stale_evidence")
    if observation.window_end.value - observation.window_start.value != policy.observation_window:
        return _uncertain(policy, observation, decision_time, "ambiguous_window")
    expected_sequence_end = observation.sequence_start + observation.expected_count - 1
    if (
        observation.observed_count != observation.expected_count
        or observation.sequence_end != expected_sequence_end
    ):
        return _uncertain(policy, observation, decision_time, "gapped_evidence")

    trend = observation.trend.decimal
    trend_threshold = policy.trend_threshold.decimal
    prior_state = observation.prior_decision.state if observation.prior_decision else None
    if prior_state is AdaptationState.TREND_UP:
        up_threshold = max(trend_threshold - policy.hysteresis.decimal, Decimal("0"))
    else:
        up_threshold = trend_threshold
    if prior_state is AdaptationState.TREND_DOWN:
        down_threshold = max(trend_threshold - policy.hysteresis.decimal, Decimal("0"))
    else:
        down_threshold = trend_threshold
    if trend <= -down_threshold:
        state = AdaptationState.TREND_DOWN
        intent = DecisionIntent.REDUCE_ONLY
        permits_buy = False
        shift = None
        reason = "confirmed_downtrend"
    elif trend >= up_threshold:
        state = AdaptationState.TREND_UP
        intent = DecisionIntent.SHIFT_UP
        permits_buy = True
        shift = policy.maximum_upward_shift
        reason = "confirmed_uptrend"
    elif observation.volatility.decimal >= policy.high_volatility_threshold.decimal:
        state = AdaptationState.RANGE_HIGH_VOLATILITY
        intent = DecisionIntent.WIDEN
        permits_buy = True
        shift = None
        reason = "qualified_sideways_high_volatility"
    else:
        state = AdaptationState.RANGE_NORMAL
        intent = DecisionIntent.SYMMETRIC
        permits_buy = True
        shift = None
        reason = "qualified_sideways_range"
    confirmations = observation.confirmations[-policy.confirmation_count :]
    if len(confirmations) < policy.confirmation_count or any(
        confirmation.state is not state for confirmation in confirmations
    ):
        return _uncertain(policy, observation, decision_time, "unconfirmed_classification")
    return AdaptationDecision(
        schema_version="adaptation-decision/v1",
        policy_id=policy.policy_id,
        observation_id=observation.observation_id,
        decision_time=decision_time,
        state=state,
        intent=intent,
        reason=reason,
        permits_exposure_increasing_buy=permits_buy,
        requested_bound_shift=shift,
    )
