from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from gridlab.canonical.adaptation import (
    AdaptationDecision,
    AdaptationObservation,
    AdaptationState,
    ConfirmationEvidence,
    DecisionIntent,
    EvidenceQuality,
    PriorDecisionEvidence,
    decide_adaptation,
)
from gridlab.canonical._identity import identity_payload
from gridlab.canonical.configuration import (
    AdaptationPolicy,
    Spacing,
    StrategyConfiguration,
)
from gridlab.canonical.events import CanonicalEvent, DomainTime, EventSource
from gridlab.api.canonical_translation import characterize_legacy_backtest
from gridlab.canonical.plan import (
    AllocationAssumptions,
    DerivedGridPlan,
    GridObligation,
    GridPlanEpoch,
    QuantizedRung,
    VenueRuleEvidence,
)
from gridlab.canonical.values import ExactDecimal


UTC = timezone.utc
BOUNDARY = datetime(2025, 1, 2, tzinfo=UTC)


def exact(source: str, kind: str = "ratio") -> ExactDecimal:
    return ExactDecimal.parse(source, kind=kind)


def policy() -> AdaptationPolicy:
    return AdaptationPolicy(
        schema_version="adaptation-policy/v1",
        observation_window=timedelta(hours=24),
        maximum_observation_age=timedelta(minutes=15),
        trend_threshold=exact("0.0100"),
        high_volatility_threshold=exact("0.0250"),
        confirmation_count=2,
        hysteresis=exact("0.0010"),
        minimum_epoch_residence=timedelta(hours=6),
        transition_cooldown=timedelta(hours=2),
        transition_expiry=timedelta(minutes=10),
        maximum_transitions_per_day=3,
        normal_width=exact("0.0400"),
        high_volatility_width=exact("0.0800"),
        maximum_width=exact("0.1000"),
        maximum_upward_shift=exact("0.0300"),
    )


def strategy() -> StrategyConfiguration:
    return StrategyConfiguration(
        schema_version="strategy-configuration/v1",
        symbol="BTCEUR",
        base_asset="BTC",
        quote_asset="EUR",
        adaptation_policy=policy(),
        rung_count=5,
        spacing=Spacing.GEOMETRIC,
        fixed_quote_principal=exact("20.00", "quote_quantity"),
        maker_fee=exact("0.0010", "fee_rate"),
        taker_fee=exact("0.0010", "fee_rate"),
        maximum_quote_capital=exact("250.00", "quote_quantity"),
        fee_reserve=exact("5.00", "quote_quantity"),
        stop_price=exact("80.00", "price"),
        lower_bound_limit=exact("85.00", "price"),
        upper_bound_limit=exact("120.00", "price"),
        execution_policy_id="limit-maker-ordinary/v1",
        risk_profile_id="mvp1-first-live-ceilings/v1",
    )


def observation(
    *,
    trend: str = "0.0000",
    volatility: str = "0.0100",
    quality: EvidenceQuality = EvidenceQuality.ADMITTED,
    complete: bool = True,
    event_time: datetime | None = None,
    sequence_start: int = 1,
    sequence_end: int = 24,
    confirmation_count: int = 2,
    prior_decision: PriorDecisionEvidence | None = None,
) -> AdaptationObservation:
    observation_time = event_time or BOUNDARY
    trend_decimal = Decimal(trend)
    if trend_decimal <= Decimal("-0.0100"):
        candidate = AdaptationState.TREND_DOWN
    elif trend_decimal >= Decimal("0.0100"):
        candidate = AdaptationState.TREND_UP
    elif Decimal(volatility) >= Decimal("0.0250"):
        candidate = AdaptationState.RANGE_HIGH_VOLATILITY
    else:
        candidate = AdaptationState.RANGE_NORMAL
    confirmations = tuple(
        ConfirmationEvidence(
            schema_version="adaptation-confirmation/v1",
            state=candidate,
            observation_id=f"sha256:{position:064x}",
            decision_time=DomainTime(observation_time - timedelta(minutes=3 - position)),
        )
        for position in range(1, confirmation_count + 1)
    )
    return AdaptationObservation(
        schema_version="adaptation-observation/v1",
        source=EventSource("binance-archive", "BTCEUR-1m"),
        event_time=DomainTime(observation_time),
        window_start=DomainTime(BOUNDARY - timedelta(hours=24)),
        window_end=DomainTime(observation_time),
        complete=complete,
        quality=quality,
        sequence_start=sequence_start,
        sequence_end=sequence_end,
        expected_count=24,
        observed_count=24,
        confirmations=confirmations,
        prior_decision=prior_decision,
        trend=exact(trend),
        volatility=exact(volatility),
        reference_price=exact("100.00", "price"),
    )


def test_exact_values_round_trip_without_binary_float() -> None:
    value = ExactDecimal.parse("001.2300", kind="price")
    assert value.source == "001.2300"
    assert value.canonical == "1.2300"
    assert value.to_payload() == {"kind": "price", "value": "001.2300"}
    assert ExactDecimal.from_payload(value.to_payload()) == value
    with pytest.raises(TypeError, match="string"):
        ExactDecimal.parse(1.23, kind="price")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="canonical decimal"):
        ExactDecimal.parse("1e-3", kind="price")
    with pytest.raises(ValueError, match="kind"):
        ExactDecimal.parse("1.0", kind="")
    with pytest.raises(ValueError, match="only kind and value"):
        ExactDecimal.from_payload({"value": "1.0"})
    assert identity_payload(Decimal("1.20")) == "1.20"
    assert identity_payload(BOUNDARY) == "2025-01-02T00:00:00Z"
    assert identity_payload([Decimal("1.0")]) == ["1.0"]
    with pytest.raises(ValueError, match="must agree"):
        ExactDecimal(source="1.00", kind="price", decimal=Decimal("2.00"))


def test_configuration_is_immutable_versioned_and_content_identified() -> None:
    configuration = strategy()
    assert configuration.configuration_id.startswith("sha256:")
    assert configuration == strategy()
    with pytest.raises(FrozenInstanceError):
        configuration.symbol = "ETHEUR"  # type: ignore[misc]
    changed = replace(configuration, fixed_quote_principal=exact("20.01", "quote_quantity"))
    assert changed.configuration_id != configuration.configuration_id
    with pytest.raises(ValueError, match="quote_quantity"):
        replace(configuration, fixed_quote_principal=exact("20.00", "price"))
    with pytest.raises(ValueError, match="unsupported strategy"):
        replace(configuration, schema_version="strategy-configuration/v2")
    with pytest.raises(ValueError, match="unsupported adaptation"):
        replace(configuration.adaptation_policy, schema_version="adaptation-policy/v2")


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"schema_version": ""}, "schema version"),
        ({"observation_window": timedelta(0)}, "durations"),
        ({"confirmation_count": 0}, "counts"),
        ({"hysteresis": exact("-0.1")}, "non-negative"),
        ({"hysteresis": exact("0.1", "price")}, "exact kind ratio"),
        ({"hysteresis": exact("0.0100")}, "below the trend threshold"),
        ({"trend_threshold": exact("0.0")}, "thresholds"),
        ({"normal_width": exact("0.09")}, "normal width"),
        ({"high_volatility_width": exact("0.11")}, "maximum width"),
    ],
)
def test_adaptation_policy_rejects_invalid_operator_inputs(
    changes: dict[str, object], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        replace(policy(), **changes)


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"schema_version": ""}, "schema version"),
        ({"symbol": ""}, "identities"),
        ({"symbol": "ETHEUR"}, "base and quote"),
        ({"rung_count": 1}, "rung count"),
        ({"fixed_quote_principal": exact("0.00", "quote_quantity")}, "positive"),
        ({"maker_fee": exact("-0.1", "fee_rate")}, "non-negative"),
        ({"fee_reserve": exact("250.00", "quote_quantity")}, "fee reserve"),
        ({"execution_policy_id": ""}, "identities"),
        ({"lower_bound_limit": exact("121.00", "price")}, "lower bound"),
        ({"stop_price": exact("86.00", "price")}, "stop price"),
    ],
)
def test_strategy_configuration_rejects_invalid_inputs(
    changes: dict[str, object], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        replace(strategy(), **changes)


def test_decision_is_past_only_deterministic_and_fail_closed() -> None:
    cases = [
        (observation(), AdaptationState.RANGE_NORMAL),
        (
            observation(volatility="0.0300"),
            AdaptationState.RANGE_HIGH_VOLATILITY,
        ),
        (observation(trend="0.0200"), AdaptationState.TREND_UP),
        (observation(trend="-0.0200"), AdaptationState.TREND_DOWN),
    ]
    for evidence, expected in cases:
        decision = decide_adaptation(policy(), evidence, DomainTime(BOUNDARY))
        assert decision.state is expected
        assert decision == decide_adaptation(policy(), evidence, DomainTime(BOUNDARY))

    unsafe = [
        observation(complete=False),
        observation(quality=EvidenceQuality.GAPPED),
        observation(quality=EvidenceQuality.CONTRADICTORY),
        observation(event_time=BOUNDARY + timedelta(seconds=1)),
        observation(event_time=BOUNDARY - timedelta(minutes=16)),
        observation(sequence_end=23),
    ]
    for evidence in unsafe:
        decision = decide_adaptation(policy(), evidence, DomainTime(BOUNDARY))
        assert decision.state is AdaptationState.UNCERTAIN
        assert decision.intent is DecisionIntent.FROZEN

    ambiguous_window = replace(
        observation(),
        window_start=DomainTime(BOUNDARY - timedelta(hours=23)),
    )
    assert (
        decide_adaptation(policy(), ambiguous_window, DomainTime(BOUNDARY)).state
        is AdaptationState.UNCERTAIN
    )
    unconfirmed = observation(confirmation_count=1)
    decision = decide_adaptation(policy(), unconfirmed, DomainTime(BOUNDARY))
    assert decision.state is AdaptationState.UNCERTAIN
    assert decision.reason == "unconfirmed_classification"
    hysteresis_hold = replace(
        observation(trend="0.0095"),
        confirmations=tuple(
            replace(item, state=AdaptationState.TREND_UP) for item in observation().confirmations
        ),
        prior_decision=PriorDecisionEvidence(
            state=AdaptationState.TREND_UP,
            decision_id="sha256:" + "7" * 64,
            decision_time=DomainTime(BOUNDARY - timedelta(minutes=3)),
        ),
    )
    assert (
        decide_adaptation(policy(), hysteresis_hold, DomainTime(BOUNDARY)).state
        is AdaptationState.TREND_UP
    )


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"schema_version": ""}, "schema version"),
        ({"window_start": DomainTime(BOUNDARY)}, "positive duration"),
        (
            {"event_time": DomainTime(BOUNDARY - timedelta(seconds=1))},
            "closed window end",
        ),
        ({"sequence_start": -1}, "sequence range"),
        ({"expected_count": 0}, "counts"),
        (
            {
                "confirmations": (
                    ConfirmationEvidence(
                        schema_version="adaptation-confirmation/v1",
                        state=AdaptationState.RANGE_NORMAL,
                        observation_id="sha256:" + "1" * 64,
                        decision_time=DomainTime(BOUNDARY + timedelta(seconds=1)),
                    ),
                )
            },
            "past-only",
        ),
        ({"volatility": exact("-0.1")}, "non-negative"),
        ({"trend": exact("0.1", "price")}, "ratio values"),
        ({"reference_price": exact("100", "ratio")}, "price values"),
    ],
)
def test_observation_rejects_invalid_or_ambiguous_evidence(
    changes: dict[str, object], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        replace(observation(), **changes)


def test_confirmed_downtrend_never_requests_buy_or_downward_shift() -> None:
    decision = decide_adaptation(policy(), observation(trend="-0.0200"), DomainTime(BOUNDARY))
    assert decision.state is AdaptationState.TREND_DOWN
    assert decision.intent is DecisionIntent.REDUCE_ONLY
    assert decision.permits_exposure_increasing_buy is False
    assert decision.requested_bound_shift is None


def test_canonical_event_has_stable_causal_and_time_identities() -> None:
    event = CanonicalEvent.create(
        schema="adaptation-observation/v1",
        source=EventSource("binance-archive", "BTCEUR-1m"),
        source_event_key="2025-01-02T00:00:00Z",
        source_sequence=24,
        event_time=DomainTime(BOUNDARY),
        received_time=DomainTime(BOUNDARY + timedelta(seconds=1)),
        correlation_id="correlation:research-run",
        causation_id="event:previous",
        payload={"close": exact("100.00", "price")},
    )
    assert event == CanonicalEvent.create(
        schema="adaptation-observation/v1",
        source=event.source,
        source_event_key=event.source_event_key,
        source_sequence=24,
        event_time=event.event_time,
        received_time=event.received_time,
        correlation_id=event.correlation_id,
        causation_id=event.causation_id,
        payload={"close": exact("100.00", "price")},
    )
    assert event.event_id.startswith("sha256:")
    assert event.ordering_key == (
        BOUNDARY,
        "binance-archive",
        "BTCEUR-1m",
        24,
        event.event_id,
    )
    mutable_payload = {"nested": ["original"]}
    immutable_event = CanonicalEvent.create(
        schema="payload/v1",
        source=event.source,
        source_event_key="mutable-source",
        source_sequence=25,
        event_time=event.event_time,
        received_time=event.received_time,
        correlation_id="correlation:payload",
        causation_id=event.event_id,
        payload=mutable_payload,
    )
    original_identity = immutable_event.event_id
    mutable_payload["nested"].append("changed")
    assert immutable_event.payload == {"nested": ["original"]}
    assert immutable_event.event_id == original_identity
    with pytest.raises(ValueError, match="timezone-aware"):
        DomainTime(datetime(2025, 1, 1))
    with pytest.raises(ValueError, match="source"):
        EventSource("", "stream")
    with pytest.raises(ValueError, match="schema"):
        CanonicalEvent.create(
            schema="",
            source=event.source,
            source_event_key="key",
            source_sequence=1,
            event_time=event.event_time,
            received_time=event.received_time,
            correlation_id="correlation",
            causation_id=None,
            payload={},
        )
    with pytest.raises(ValueError, match="non-negative"):
        CanonicalEvent.create(
            schema="event/v1",
            source=event.source,
            source_event_key="key",
            source_sequence=-1,
            event_time=event.event_time,
            received_time=event.received_time,
            correlation_id="correlation",
            causation_id=None,
            payload={},
        )
    with pytest.raises(TypeError, match="keys must be strings"):
        CanonicalEvent.create(
            schema="event/v1",
            source=event.source,
            source_event_key="key",
            source_sequence=1,
            event_time=event.event_time,
            received_time=event.received_time,
            correlation_id="correlation",
            causation_id=None,
            payload={1: "ambiguous"},  # type: ignore[dict-item]
        )
    with pytest.raises(TypeError, match="floats"):
        CanonicalEvent.create(
            schema="event/v1",
            source=event.source,
            source_event_key="key",
            source_sequence=1,
            event_time=event.event_time,
            received_time=event.received_time,
            correlation_id="correlation",
            causation_id=None,
            payload={"price": 1.25},
        )
    with pytest.raises(TypeError, match="keys must be strings"):
        CanonicalEvent.create(
            schema="event/v1",
            source=event.source,
            source_event_key="key",
            source_sequence=1,
            event_time=event.event_time,
            received_time=event.received_time,
            correlation_id="correlation",
            causation_id=None,
            payload={"nested": {1: "ambiguous"}},  # type: ignore[dict-item]
        )
    with pytest.raises(ValueError, match="schema identity"):
        CanonicalEvent.create(
            schema="event/v0",
            source=event.source,
            source_event_key="key",
            source_sequence=1,
            event_time=event.event_time,
            received_time=event.received_time,
            correlation_id="correlation",
            causation_id=None,
            payload={},
        )
    with pytest.raises(ValueError, match="unique"):
        CanonicalEvent(
            schema="event/v1",
            source=event.source,
            source_event_key="key",
            source_sequence=1,
            event_time=event.event_time,
            received_time=event.received_time,
            correlation_id="correlation",
            causation_id=None,
            payload_items=(("same", "first"), ("same", "second")),
        )
    with pytest.raises(TypeError, match="keys must be strings"):
        CanonicalEvent(
            schema="event/v1",
            source=event.source,
            source_event_key="key",
            source_sequence=1,
            event_time=event.event_time,
            received_time=event.received_time,
            correlation_id="correlation",
            causation_id=None,
            payload_items=((1, "ambiguous"),),  # type: ignore[arg-type]
        )
    with pytest.raises(TypeError, match="unsupported object"):
        CanonicalEvent.create(
            schema="event/v1",
            source=event.source,
            source_event_key="key",
            source_sequence=1,
            event_time=event.event_time,
            received_time=event.received_time,
            correlation_id="correlation",
            causation_id=None,
            payload={"unsupported": object()},
        )
    nested = CanonicalEvent.create(
        schema="event/v1",
        source=event.source,
        source_event_key="nested",
        source_sequence=2,
        event_time=event.event_time,
        received_time=event.received_time,
        correlation_id="correlation",
        causation_id=event.event_id,
        payload={"nested": {"items": ["value"]}},
    )
    assert nested.payload == {"nested": {"items": ["value"]}}


def test_epoch_identity_covers_material_inputs_not_presentation() -> None:
    decision = decide_adaptation(policy(), observation(), DomainTime(BOUNDARY))
    plan = DerivedGridPlan(
        schema_version="grid-plan/v1",
        lower=exact("90.00", "price"),
        upper=exact("109.3955625000", "price"),
        reference_price=exact("100.00", "price"),
        unquantized_rungs=(
            exact("90.0000000000", "price"),
            exact("94.5000000000", "price"),
            exact("99.2250000000", "price"),
            exact("104.1862500000", "price"),
            exact("109.3955625000", "price"),
        ),
        rungs=(
            QuantizedRung(0, exact("90.00", "price"), "BUY"),
            QuantizedRung(1, exact("94.50", "price"), "BUY"),
            QuantizedRung(2, exact("99.22", "price"), "BUY"),
            QuantizedRung(3, exact("104.18", "price"), "SELL"),
            QuantizedRung(4, exact("109.39", "price"), "SELL"),
        ),
        fixed_quote_principal=exact("20.00", "quote_quantity"),
        obligations=(
            GridObligation(0, "BUY", exact("20.00", "quote_quantity")),
            GridObligation(1, "BUY", exact("20.00", "quote_quantity")),
            GridObligation(2, "BUY", exact("20.00", "quote_quantity")),
            GridObligation(3, "SELL", exact("20.00", "quote_quantity")),
            GridObligation(4, "SELL", exact("20.00", "quote_quantity")),
        ),
        allocation_assumptions=AllocationAssumptions(
            quote_allocation=exact("245.00", "quote_quantity"),
            base_allocation=exact("0.00000", "base_quantity"),
            fee_reserve=exact("5.00", "quote_quantity"),
        ),
        derivation_semantics="bounded-symmetric-geometric/v1",
    )
    rules = VenueRuleEvidence(
        schema_version="venue-rules/v1",
        source=EventSource("binance", "exchangeInfo:BTCEUR"),
        observed_at=DomainTime(BOUNDARY),
        environment="production",
        tick_size=exact("0.01", "price_increment"),
        step_size=exact("0.00001", "quantity_increment"),
        minimum_price=exact("0.01", "price"),
        maximum_price=None,
        minimum_quantity=exact("0.00010", "base_quantity"),
        maximum_quantity=None,
        minimum_notional=exact("5.00", "quote_quantity"),
        maximum_notional=None,
    )
    epoch = GridPlanEpoch.derive(
        configuration=strategy(),
        observation=observation(),
        decision=decision,
        predecessor_epoch_id="sha256:" + "0" * 64,
        derivation_causation_id="sha256:" + "1" * 64,
        venue_rules=rules,
        plan=plan,
        presentation={"label": "Operator preview"},
    )
    relabelled = replace(epoch, presentation={"label": "Übersicht"})
    assert relabelled.epoch_id == epoch.epoch_id
    changed = GridPlanEpoch.derive(
        configuration=strategy(),
        observation=observation(),
        decision=decision,
        predecessor_epoch_id="sha256:" + "0" * 64,
        derivation_causation_id="sha256:" + "1" * 64,
        venue_rules=replace(rules, tick_size=exact("0.005", "price_increment")),
        plan=plan,
    )
    assert changed.epoch_id != epoch.epoch_id
    changed_allocation = GridPlanEpoch.derive(
        configuration=strategy(),
        observation=observation(),
        decision=decision,
        predecessor_epoch_id="sha256:" + "0" * 64,
        derivation_causation_id="sha256:" + "1" * 64,
        venue_rules=rules,
        plan=replace(
            plan,
            allocation_assumptions=replace(
                plan.allocation_assumptions,
                quote_allocation=exact("244.00", "quote_quantity"),
            ),
        ),
    )
    assert changed_allocation.epoch_id != epoch.epoch_id
    changed_causation = replace(
        epoch,
        derivation_causation_id="sha256:" + "2" * 64,
    )
    assert changed_causation.epoch_id != epoch.epoch_id
    with pytest.raises(TypeError):
        epoch.presentation["label"] = "mutated"  # type: ignore[index]

    mismatched_policy = replace(
        decision,
        policy_id="sha256:" + "9" * 64,
    )
    with pytest.raises(ValueError, match="policy"):
        GridPlanEpoch.derive(
            configuration=strategy(),
            observation=observation(),
            decision=mismatched_policy,
            predecessor_epoch_id=None,
            derivation_causation_id="sha256:" + "1" * 64,
            venue_rules=rules,
            plan=plan,
        )
    mismatched_observation = replace(
        decision,
        observation_id="sha256:" + "8" * 64,
    )
    with pytest.raises(ValueError, match="evidence"):
        GridPlanEpoch.derive(
            configuration=strategy(),
            observation=observation(),
            decision=mismatched_observation,
            predecessor_epoch_id=None,
            derivation_causation_id="sha256:" + "1" * 64,
            venue_rules=rules,
            plan=plan,
        )


def test_adaptation_decision_rejects_semantic_conflicts_and_unknown_schema() -> None:
    base = decide_adaptation(policy(), observation(), DomainTime(BOUNDARY))
    with pytest.raises(ValueError, match="state, intent"):
        replace(base, intent=DecisionIntent.FROZEN)
    with pytest.raises(ValueError, match="only TREND_UP"):
        replace(base, requested_bound_shift=exact("0.01"))
    with pytest.raises(ValueError, match="unsupported adaptation decision"):
        replace(base, schema_version="adaptation-decision/v2")
    with pytest.raises(ValueError, match="requires a non-negative ratio shift"):
        AdaptationDecision(
            schema_version="adaptation-decision/v1",
            policy_id=base.policy_id,
            observation_id=base.observation_id,
            decision_time=base.decision_time,
            state=AdaptationState.TREND_UP,
            intent=DecisionIntent.SHIFT_UP,
            reason="invalid_shift",
            permits_exposure_increasing_buy=True,
            requested_bound_shift=exact("-0.01"),
        )


def test_adaptation_evidence_rejects_invalid_identity_and_time_material() -> None:
    base = observation()
    confirmation = base.confirmations[0]
    with pytest.raises(ValueError, match="unsupported adaptation confirmation"):
        replace(confirmation, schema_version="adaptation-confirmation/v2")
    with pytest.raises(ValueError, match="observation identity"):
        replace(confirmation, observation_id="")
    with pytest.raises(ValueError, match="prior decision identity"):
        PriorDecisionEvidence(
            state=AdaptationState.RANGE_NORMAL,
            decision_id="",
            decision_time=DomainTime(BOUNDARY - timedelta(minutes=1)),
        )
    with pytest.raises(ValueError, match="time ordered"):
        replace(base, confirmations=tuple(reversed(base.confirmations)))
    with pytest.raises(ValueError, match="unique"):
        replace(base, confirmations=(confirmation, confirmation))
    with pytest.raises(ValueError, match="confirmations must be past-only"):
        replace(
            base,
            confirmations=(
                replace(
                    confirmation,
                    decision_time=DomainTime(BOUNDARY + timedelta(minutes=1)),
                ),
            ),
        )
    with pytest.raises(ValueError, match="prior decision evidence must be past-only"):
        replace(
            base,
            prior_decision=PriorDecisionEvidence(
                state=AdaptationState.RANGE_NORMAL,
                decision_id="sha256:" + "7" * 64,
                decision_time=DomainTime(BOUNDARY + timedelta(minutes=1)),
            ),
        )
    decision = decide_adaptation(policy(), base, DomainTime(BOUNDARY))
    with pytest.raises(ValueError, match="identities and reason"):
        replace(decision, reason="")


def test_downtrend_hysteresis_uses_prior_decision_evidence() -> None:
    prior = PriorDecisionEvidence(
        state=AdaptationState.TREND_DOWN,
        decision_id="sha256:" + "7" * 64,
        decision_time=DomainTime(BOUNDARY - timedelta(minutes=5)),
    )
    base = observation(trend="-0.0095", prior_decision=prior)
    confirmed = replace(
        base,
        confirmations=tuple(
            replace(item, state=AdaptationState.TREND_DOWN) for item in base.confirmations
        ),
    )
    decision = decide_adaptation(policy(), confirmed, DomainTime(BOUNDARY))
    assert decision.state is AdaptationState.TREND_DOWN
    assert decision.permits_exposure_increasing_buy is False


def test_plan_collections_are_normalized_and_roles_respect_reference_price() -> None:
    mutable_rungs = [
        QuantizedRung(0, exact("90.00", "price"), "BUY"),
        QuantizedRung(1, exact("110.00", "price"), "SELL"),
    ]
    mutable_prices = [exact("90.00", "price"), exact("110.00", "price")]
    mutable_obligations = [
        GridObligation(0, "BUY", exact("20.00", "quote_quantity")),
        GridObligation(1, "SELL", exact("20.00", "quote_quantity")),
    ]
    immutable = DerivedGridPlan(
        schema_version="grid-plan/v1",
        lower=exact("90.00", "price"),
        upper=exact("110.00", "price"),
        reference_price=exact("100.00", "price"),
        unquantized_rungs=mutable_prices,  # type: ignore[arg-type]
        rungs=mutable_rungs,  # type: ignore[arg-type]
        fixed_quote_principal=exact("20.00", "quote_quantity"),
        obligations=mutable_obligations,  # type: ignore[arg-type]
        allocation_assumptions=AllocationAssumptions(
            quote_allocation=exact("245.00", "quote_quantity"),
            base_allocation=exact("0.00000", "base_quantity"),
            fee_reserve=exact("5.00", "quote_quantity"),
        ),
        derivation_semantics="test/v1",
    )
    mutable_rungs.clear()
    mutable_prices.clear()
    mutable_obligations.clear()
    assert len(immutable.rungs) == len(immutable.unquantized_rungs) == 2
    assert len(immutable.obligations) == 2
    with pytest.raises(ValueError, match="reference price"):
        replace(
            immutable,
            rungs=(
                QuantizedRung(0, exact("90.00", "price"), "BUY"),
                QuantizedRung(1, exact("110.00", "price"), "BUY"),
            ),
            obligations=(
                GridObligation(0, "BUY", exact("20.00", "quote_quantity")),
                GridObligation(1, "BUY", exact("20.00", "quote_quantity")),
            ),
        )


def test_epoch_rejects_inconsistent_material_and_supports_arithmetic_spacing() -> None:
    result = characterize_legacy_backtest(
        symbol="BTCEUR",
        decision_time=DomainTime(BOUNDARY),
    )
    epoch = result.epoch
    plan = epoch.plan
    with pytest.raises(ValueError, match="unsupported grid-plan-epoch"):
        replace(epoch, schema_version="grid-plan-epoch/v2")
    with pytest.raises(ValueError, match="derivation causation"):
        replace(epoch, derivation_causation_id="")
    with pytest.raises(ValueError, match="rung count"):
        replace(epoch, configuration=replace(epoch.configuration, rung_count=4))
    with pytest.raises(ValueError, match="principal does not match"):
        replace(
            epoch,
            configuration=replace(
                epoch.configuration,
                fixed_quote_principal=exact("21.00", "quote_quantity"),
            ),
        )
    changed_observation = replace(
        epoch.observation,
        reference_price=exact("101.00", "price"),
    )
    with pytest.raises(ValueError, match="reference price"):
        replace(
            epoch,
            observation=changed_observation,
            decision=decide_adaptation(
                epoch.configuration.adaptation_policy,
                changed_observation,
                DomainTime(BOUNDARY),
            ),
        )
    with pytest.raises(ValueError, match="bounds exceed"):
        replace(
            epoch,
            configuration=replace(
                epoch.configuration,
                lower_bound_limit=exact("91.00", "price"),
            ),
        )
    with pytest.raises(ValueError, match="capital envelope"):
        replace(
            epoch,
            plan=replace(
                plan,
                allocation_assumptions=replace(
                    plan.allocation_assumptions,
                    quote_allocation=exact("246.00", "quote_quantity"),
                ),
            ),
        )
    with pytest.raises(ValueError, match="obligations do not match"):
        replace(
            epoch,
            plan=replace(
                plan,
                obligations=tuple(
                    replace(
                        obligation,
                        fixed_quote_principal=exact("21.00", "quote_quantity"),
                    )
                    for obligation in plan.obligations
                ),
            ),
        )
    with pytest.raises(ValueError, match="minimum notional"):
        replace(
            epoch,
            venue_rules=replace(
                epoch.venue_rules,
                minimum_notional=exact("21.00", "quote_quantity"),
            ),
        )
    with pytest.raises(ValueError, match="venue-quantized"):
        replace(
            epoch,
            venue_rules=replace(
                epoch.venue_rules,
                tick_size=exact("0.07", "price_increment"),
            ),
        )
    altered_unquantized = list(plan.unquantized_rungs)
    altered_unquantized[1] = exact("95.00", "price")
    with pytest.raises(ValueError, match="geometric spacing"):
        replace(epoch, plan=replace(plan, unquantized_rungs=altered_unquantized))

    arithmetic_prices = ("90.00", "95.00", "100.00", "105.00", "110.00")
    arithmetic_roles = ("BUY", "BUY", "INACTIVE", "SELL", "SELL")
    arithmetic_plan = replace(
        plan,
        upper=exact("110.00", "price"),
        unquantized_rungs=tuple(exact(value, "price") for value in arithmetic_prices),
        rungs=tuple(
            QuantizedRung(index, exact(value, "price"), arithmetic_roles[index])
            for index, value in enumerate(arithmetic_prices)
        ),
        obligations=tuple(
            GridObligation(index, role, exact("20.00", "quote_quantity"))
            for index, role in enumerate(arithmetic_roles)
            if role != "INACTIVE"
        ),
        derivation_semantics="bounded-symmetric-arithmetic/v1",
    )
    arithmetic_epoch = replace(
        epoch,
        configuration=replace(epoch.configuration, spacing=Spacing.ARITHMETIC),
        plan=arithmetic_plan,
    )
    assert arithmetic_epoch.epoch_id != epoch.epoch_id
    with pytest.raises(ValueError, match="arithmetic spacing"):
        replace(
            arithmetic_epoch,
            plan=replace(
                arithmetic_plan,
                unquantized_rungs=plan.unquantized_rungs,
            ),
        )

    down_observation = observation(trend="-0.0200")
    down_decision = decide_adaptation(
        epoch.configuration.adaptation_policy,
        down_observation,
        DomainTime(BOUNDARY),
    )
    with pytest.raises(ValueError, match="TREND_DOWN"):
        replace(epoch, observation=down_observation, decision=down_decision)
    uncertain_observation = observation(complete=False)
    uncertain_decision = decide_adaptation(
        epoch.configuration.adaptation_policy,
        uncertain_observation,
        DomainTime(BOUNDARY),
    )
    with pytest.raises(ValueError, match="UNCERTAIN"):
        replace(
            epoch,
            observation=uncertain_observation,
            decision=uncertain_decision,
        )


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"schema_version": ""}, "schema"),
        ({"lower": exact("111.00", "price")}, "lower bound"),
        ({"lower": exact("90.00", "ratio")}, "price values"),
        ({"fixed_quote_principal": exact("20.00", "price")}, "quote_quantity"),
        ({"reference_price": exact("120.00", "price")}, "strictly inside"),
        ({"rungs": (QuantizedRung(0, exact("90.00", "price"), "BUY"),)}, "two rungs"),
        ({"unquantized_rungs": (exact("90.00", "price"),)}, "counts must match"),
        (
            {
                "unquantized_rungs": (
                    exact("90.00", "ratio"),
                    exact("110.00", "price"),
                )
            },
            "unquantized rungs",
        ),
        (
            {
                "unquantized_rungs": (
                    exact("91.00", "price"),
                    exact("110.00", "price"),
                )
            },
            "both exact bounds",
        ),
        ({"obligations": ()}, "cover every active rung"),
        (
            {
                "rungs": (
                    QuantizedRung(1, exact("90.00", "price"), "BUY"),
                    QuantizedRung(2, exact("110.00", "price"), "SELL"),
                )
            },
            "contiguous",
        ),
        (
            {
                "rungs": (
                    QuantizedRung(0, exact("110.00", "price"), "SELL"),
                    QuantizedRung(1, exact("90.00", "price"), "BUY"),
                )
            },
            "unique and ordered",
        ),
    ],
)
def test_derived_plan_rejects_invalid_mechanical_values(
    changes: dict[str, object], message: str
) -> None:
    base = DerivedGridPlan(
        schema_version="grid-plan/v1",
        lower=exact("90.00", "price"),
        upper=exact("110.00", "price"),
        reference_price=exact("100.00", "price"),
        unquantized_rungs=(
            exact("90.0000", "price"),
            exact("110.0000", "price"),
        ),
        rungs=(
            QuantizedRung(0, exact("90.00", "price"), "BUY"),
            QuantizedRung(1, exact("110.00", "price"), "SELL"),
        ),
        fixed_quote_principal=exact("20.00", "quote_quantity"),
        obligations=(
            GridObligation(0, "BUY", exact("20.00", "quote_quantity")),
            GridObligation(1, "SELL", exact("20.00", "quote_quantity")),
        ),
        allocation_assumptions=AllocationAssumptions(
            quote_allocation=exact("245.00", "quote_quantity"),
            base_allocation=exact("0.00000", "base_quantity"),
            fee_reserve=exact("5.00", "quote_quantity"),
        ),
        derivation_semantics="test/v1",
    )
    with pytest.raises(ValueError, match=message):
        replace(base, **changes)


def test_rung_and_venue_rules_reject_invalid_values() -> None:
    with pytest.raises(ValueError, match="index and price"):
        QuantizedRung(-1, exact("90.00", "price"), "BUY")
    with pytest.raises(ValueError, match="role"):
        QuantizedRung(0, exact("90.00", "price"), "HOLD")
    with pytest.raises(ValueError, match="price value"):
        QuantizedRung(0, exact("90.00", "ratio"), "BUY")
    rules = VenueRuleEvidence(
        schema_version="venue-rules/v1",
        source=EventSource("binance", "exchangeInfo:BTCEUR"),
        observed_at=DomainTime(BOUNDARY),
        environment="production",
        tick_size=exact("0.01", "price_increment"),
        step_size=exact("0.00001", "quantity_increment"),
        minimum_price=exact("0.01", "price"),
        maximum_price=None,
        minimum_quantity=exact("0.00010", "base_quantity"),
        maximum_quantity=None,
        minimum_notional=exact("5.00", "quote_quantity"),
        maximum_notional=None,
    )
    with pytest.raises(ValueError, match="schema"):
        replace(rules, schema_version="")
    with pytest.raises(ValueError, match="non-negative"):
        replace(rules, minimum_notional=exact("-1.00", "quote_quantity"))
    with pytest.raises(ValueError, match="exact kind"):
        replace(rules, tick_size=exact("0.01", "fee_rate"))
    with pytest.raises(ValueError, match="must be positive"):
        replace(rules, tick_size=exact("0.00", "price_increment"))
    with pytest.raises(ValueError, match="production or testnet"):
        replace(rules, environment="paper")
    with pytest.raises(ValueError, match="positive exact values"):
        replace(rules, maximum_price=exact("0.00", "price"))
    with pytest.raises(ValueError, match="minimum price"):
        replace(rules, maximum_price=exact("0.001", "price"))
    with pytest.raises(ValueError, match="minimum quantity"):
        replace(rules, maximum_quantity=exact("0.00001", "base_quantity"))
    with pytest.raises(ValueError, match="minimum notional"):
        replace(rules, maximum_notional=exact("1.00", "quote_quantity"))
    with pytest.raises(ValueError, match="open orders must be positive"):
        replace(rules, max_open_orders=0)
    with pytest.raises(ValueError, match="open orders must be non-negative"):
        replace(rules, foreign_open_orders=-1)


def test_obligation_and_allocation_values_are_semantically_typed() -> None:
    with pytest.raises(ValueError, match="rung and role"):
        GridObligation(-1, "BUY", exact("20.00", "quote_quantity"))
    with pytest.raises(ValueError, match="positive quote quantity"):
        GridObligation(0, "BUY", exact("20.00", "price"))
    with pytest.raises(ValueError, match="base_allocation"):
        AllocationAssumptions(
            quote_allocation=exact("245.00", "quote_quantity"),
            base_allocation=exact("0.00", "quote_quantity"),
            fee_reserve=exact("5.00", "quote_quantity"),
        )


def test_existing_backtest_translation_reports_explicit_semantic_differences() -> None:
    result = characterize_legacy_backtest(
        symbol="BTCEUR",
        decision_time=DomainTime(BOUNDARY),
    )
    assert result.legacy_result["bars"] == 120
    assert result.legacy_spec["grid"]["adaptive"] is True
    assert result.legacy_spec["grid"]["spacing"] == "geometric"
    assert result.configuration.configuration_id.startswith("sha256:")
    assert result.observation.observation_id.startswith("sha256:")
    assert result.epoch.epoch_id.startswith("sha256:")
    quantized = [rung.price.decimal for rung in result.epoch.plan.rungs]
    assert quantized != [
        Decimal("90.00"),
        Decimal("95.00"),
        Decimal("100.00"),
        Decimal("105.00"),
        Decimal("110.00"),
    ]
    assert result.differences == (
        "canonical policy does not inherit the legacy nonzero atr_mult default",
        "canonical seam emits no immediate cancel-all/rebuild transition",
        "canonical classification fails closed on incomplete or ambiguous evidence",
        "canonical characterization applies the MVP 250.00 EUR capital envelope instead of the legacy 1000.0 initial cash",
        "canonical venue-rule evidence is an explicit translation assumption absent from the legacy backtest",
    )
    assert result.legacy_effective_atr_multiplier == "2.0"
    assert result.legacy_cancelled_orders > 0
    downtrend = characterize_legacy_backtest(
        symbol="BTCEUR",
        decision_time=DomainTime(BOUNDARY),
        trend="-0.0200",
    )
    assert downtrend.epoch.decision.state is AdaptationState.TREND_DOWN
    assert all(rung.role != "BUY" for rung in downtrend.epoch.plan.rungs)
    with pytest.raises(ValueError, match="EUR-quoted"):
        characterize_legacy_backtest(
            symbol="BTCUSDT",
            decision_time=DomainTime(BOUNDARY),
        )
