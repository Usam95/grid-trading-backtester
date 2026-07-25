from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from gridlab.api.canonical_translation import characterize_legacy_backtest
from gridlab.canonical.adaptation import (
    AdaptationObservation,
    AdaptationState,
    ConfirmationEvidence,
    EvidenceQuality,
)
from gridlab.canonical.configuration import AdaptationPolicy, Spacing, StrategyConfiguration
from gridlab.canonical.events import DomainTime, EventSource
from gridlab.canonical.initial_epoch import (
    AdjacentCycleEconomics,
    ActivationGate,
    ActivationGateOutcome,
    ActivationLifecycle,
    BootstrapEvidence,
    PlanAdmissionContext,
    PlanAdmissionAssessment,
    PostOnlyRetryPolicy,
    PrincipalFeasibilityPoint,
    PrincipalFeasibilityReport,
    RuleFeeContract,
    derive_initial_epoch,
)
from gridlab.canonical.plan import (
    BootstrapObligation,
    GridObligation,
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


def strategy(spacing: Spacing = Spacing.GEOMETRIC) -> StrategyConfiguration:
    return StrategyConfiguration(
        schema_version="strategy-configuration/v1",
        symbol="BTCEUR",
        base_asset="BTC",
        quote_asset="EUR",
        adaptation_policy=policy(),
        rung_count=5,
        spacing=spacing,
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
    reference_price: str = "100.00",
    trend: str = "0.0000",
    volatility: str = "0.0100",
    complete: bool = True,
    quality: EvidenceQuality = EvidenceQuality.ADMITTED,
    event_time: datetime = BOUNDARY,
    observed_count: int = 24,
    sequence_end: int = 24,
) -> AdaptationObservation:
    if exact(trend).decimal <= exact("-0.0100").decimal:
        state = AdaptationState.TREND_DOWN
    elif exact(trend).decimal >= exact("0.0100").decimal:
        state = AdaptationState.TREND_UP
    elif exact(volatility).decimal >= exact("0.0250").decimal:
        state = AdaptationState.RANGE_HIGH_VOLATILITY
    else:
        state = AdaptationState.RANGE_NORMAL
    return AdaptationObservation(
        schema_version="adaptation-observation/v1",
        source=EventSource("quality-approved-fixture", "BTCEUR-1h"),
        event_time=DomainTime(event_time),
        window_start=DomainTime(event_time - timedelta(hours=24)),
        window_end=DomainTime(event_time),
        complete=complete,
        quality=quality,
        sequence_start=1,
        sequence_end=sequence_end,
        expected_count=24,
        observed_count=observed_count,
        confirmations=tuple(
            ConfirmationEvidence(
                schema_version="adaptation-confirmation/v1",
                state=state,
                observation_id=f"sha256:{index:064x}",
                decision_time=DomainTime(event_time - timedelta(minutes=3 - index)),
            )
            for index in (1, 2)
        ),
        prior_decision=None,
        trend=exact(trend),
        volatility=exact(volatility),
        reference_price=exact(reference_price, "price"),
    )


def venue_rules() -> VenueRuleEvidence:
    return VenueRuleEvidence(
        schema_version="venue-rules/v1",
        source=EventSource("bounded-fixture", "BTCEUR:rules"),
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


def derive(
    *,
    configuration: StrategyConfiguration | None = None,
    evidence: AdaptationObservation | None = None,
    bootstrap: BootstrapEvidence | None = None,
    activation_price: str = "100.00",
):
    return derive_initial_epoch(
        configuration=configuration or strategy(),
        observation=evidence or observation(),
        decision_time=DomainTime(BOUNDARY),
        activation_price=exact(activation_price, "price"),
        derivation_causation_id="sha256:" + "a" * 64,
        venue_rules=venue_rules(),
        bootstrap_evidence=bootstrap or BootstrapEvidence.incomplete(),
    )


@pytest.mark.parametrize(
    "evidence",
    [
        observation(complete=False, quality=EvidenceQuality.INCOMPLETE),
        observation(event_time=BOUNDARY + timedelta(seconds=1)),
        observation(event_time=BOUNDARY - timedelta(minutes=16)),
        observation(observed_count=23),
        observation(sequence_end=23),
        observation(quality=EvidenceQuality.CONTRADICTORY),
    ],
)
def test_rejected_evidence_never_leaves_activation_pending_or_armed(
    evidence: AdaptationObservation,
) -> None:
    result = derive(evidence=evidence)

    assert result.lifecycle is ActivationLifecycle.REJECTED
    assert result.epoch is None
    assert result.activation_pending is False
    assert result.automatically_armed is False
    assert result.ladder_placement_allowed is False


def test_bounds_width_and_epoch_identity_are_exact_and_deterministic() -> None:
    first = derive()
    second = derive()

    assert first.derived_width == exact("0.0400")
    assert first.epoch is not None
    assert first.epoch.plan.lower.decimal == exact("96.000000", "price").decimal
    assert first.epoch.plan.upper.decimal == exact("104.000000", "price").decimal
    assert first.epoch.epoch_id == second.epoch.epoch_id
    assert first.replay_fingerprint == second.replay_fingerprint


@pytest.mark.parametrize("spacing", [Spacing.GEOMETRIC, Spacing.ARITHMETIC])
def test_rung_geometry_includes_bounds_and_never_inserts_activation_price(
    spacing: Spacing,
) -> None:
    result = derive(configuration=strategy(spacing))
    assert result.epoch is not None
    plan = result.epoch.plan

    assert len(plan.unquantized_rungs) == strategy(spacing).rung_count
    assert plan.unquantized_rungs[0] == plan.lower
    assert plan.unquantized_rungs[-1] == plan.upper
    if spacing is Spacing.GEOMETRIC:
        assert all(rung.decimal != plan.reference_price.decimal for rung in plan.unquantized_rungs)
    assert plan.derivation_semantics.endswith(spacing.value.lower() + "/v1")


def test_exact_activation_rung_is_inactive_and_boundaries_reject_before_bootstrap() -> None:
    arithmetic = strategy(Spacing.ARITHMETIC)
    exact_rung = derive(configuration=arithmetic)
    assert exact_rung.epoch is not None
    assert [rung.role for rung in exact_rung.epoch.plan.rungs] == [
        "BUY",
        "BUY",
        "INACTIVE",
        "SELL",
        "SELL",
    ]

    lower = derive(configuration=arithmetic, activation_price="96.00")
    upper = derive(configuration=arithmetic, activation_price="104.00")
    assert lower.lifecycle is ActivationLifecycle.REJECTED
    assert upper.lifecycle is ActivationLifecycle.REJECTED
    assert lower.bootstrap_obligation is None
    assert upper.bootstrap_obligation is None


def test_bootstrap_covers_initial_sells_rounding_fees_and_maximum_inventory() -> None:
    result = derive()
    assert result.epoch is not None
    obligation = result.bootstrap_obligation
    assert obligation is not None

    sell_quantities = [
        item.base_quantity.decimal for item in result.epoch.plan.obligations if item.role == "SELL"
    ]
    buy_quantities = [
        item.base_quantity.decimal for item in result.epoch.plan.obligations if item.role == "BUY"
    ]
    assert obligation.net_base_required.decimal == sum(sell_quantities)
    assert obligation.gross_base_required.decimal >= obligation.net_base_required.decimal
    assert obligation.fee_base_coverage.decimal == (
        obligation.gross_base_required.decimal - obligation.net_base_required.decimal
    )
    assert result.maximum_planned_inventory is not None
    assert result.maximum_planned_inventory.decimal == (
        obligation.net_base_required.decimal + sum(buy_quantities)
    )


def test_post_rounding_notional_below_venue_minimum_rejects_activation() -> None:
    result = derive(
        configuration=replace(
            strategy(),
            fixed_quote_principal=exact("5.00", "quote_quantity"),
        )
    )

    assert result.lifecycle is ActivationLifecycle.REJECTED
    assert result.epoch is None
    assert result.gates[-1].reason == "quantized_obligation_below_minimum_notional"


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        (
            {"observed_at": DomainTime(BOUNDARY + timedelta(seconds=1))},
            "venue_rules_observed_in_the_future",
        ),
        ({"observed_at": DomainTime(BOUNDARY - timedelta(minutes=16))}, "venue_rules_are_stale"),
        ({"symbol_status": "SUSPENDED"}, "venue_rules_symbol_suspended"),
        ({"spot_trading_allowed": False}, "venue_rules_spot_trading_unsupported"),
        ({"limit_maker_supported": False}, "venue_rules_post_only_unsupported"),
        ({"contradictory": True}, "venue_rules_are_contradictory"),
    ],
)
def test_invalid_venue_rule_contract_rejects_activation(changes: dict, reason: str) -> None:
    result = derive_initial_epoch(
        configuration=strategy(),
        observation=observation(),
        decision_time=DomainTime(BOUNDARY),
        activation_price=exact("100", "price"),
        derivation_causation_id="sha256:" + "a" * 64,
        venue_rules=replace(venue_rules(), **changes),
        bootstrap_evidence=BootstrapEvidence.incomplete(),
    )

    assert result.lifecycle is ActivationLifecycle.REJECTED
    assert result.gates[-1].reason == reason


def test_incomplete_bootstrap_remains_blocked_without_scaling() -> None:
    result = derive(bootstrap=BootstrapEvidence.incomplete())
    assert result.lifecycle is ActivationLifecycle.BOOTSTRAPPING
    assert result.ladder_placement_allowed is False
    assert result.automatically_armed is False
    assert result.epoch is not None

    partial = replace(
        BootstrapEvidence.incomplete(),
        complete=True,
        net_base_confirmed=exact("0.10000", "base_quantity"),
        evidence_id="sha256:" + "c" * 64,
    )
    still_incomplete = derive(bootstrap=partial)
    assert still_incomplete.lifecycle is ActivationLifecycle.BOOTSTRAPPING
    assert still_incomplete.ladder_placement_allowed is False
    assert still_incomplete.epoch is not None
    assert still_incomplete.epoch.plan.rungs == result.epoch.plan.rungs


def test_complete_bootstrap_activates_the_immutable_epoch() -> None:
    pending = derive()
    assert pending.bootstrap_obligation is not None
    complete = derive(
        bootstrap=BootstrapEvidence(
            schema_version="bootstrap-evidence/v1",
            complete=True,
            net_base_confirmed=pending.bootstrap_obligation.net_base_required,
            evidence_id="sha256:" + "b" * 64,
        )
    )

    assert complete.lifecycle is ActivationLifecycle.ACTIVE
    assert complete.ladder_placement_allowed is True
    assert complete.activation_pending is False
    assert complete.automatically_armed is False
    assert complete.epoch is not None
    assert complete.epoch.epoch_id == pending.epoch.epoch_id


def test_initial_epoch_value_objects_reject_invalid_states() -> None:
    with pytest.raises(ValueError, match="name and reason"):
        ActivationGate("", ActivationGateOutcome.FAILED, "")
    with pytest.raises(ValueError, match="bootstrap evidence schema"):
        replace(BootstrapEvidence.incomplete(), schema_version="bootstrap-evidence/v2")
    with pytest.raises(ValueError, match="non-negative base quantity"):
        replace(
            BootstrapEvidence.incomplete(),
            net_base_confirmed=exact("-0.1", "base_quantity"),
        )
    with pytest.raises(ValueError, match="non-negative base quantity"):
        replace(
            BootstrapEvidence.incomplete(),
            net_base_confirmed=exact("0", "quote_quantity"),
        )
    with pytest.raises(ValueError, match="requires an identity"):
        replace(BootstrapEvidence.incomplete(), complete=True)

    rejected = derive(evidence=observation(complete=False))
    pending = derive()
    assert pending.epoch is not None
    assert pending.bootstrap_obligation is not None
    invalid_states = [
        ({"schema_version": "initial-epoch-activation/v2"}, "activation schema"),
        ({"gates": ()}, "gates are required"),
        ({"activation_pending": True}, "pending or automatically armed"),
        ({"automatically_armed": True}, "pending or automatically armed"),
        ({"epoch": pending.epoch}, "rejected activation"),
        (
            {
                "lifecycle": ActivationLifecycle.BOOTSTRAPPING,
                "epoch": None,
                "bootstrap_obligation": None,
            },
            "obligation-backed epoch",
        ),
        (
            {
                "lifecycle": ActivationLifecycle.ACTIVE,
                "epoch": pending.epoch,
                "bootstrap_obligation": pending.bootstrap_obligation,
            },
            "must permit ladder placement",
        ),
        (
            {
                "lifecycle": ActivationLifecycle.BOOTSTRAPPING,
                "ladder_placement_allowed": True,
            },
            "bootstrapping cannot permit",
        ),
    ]
    for changes, message in invalid_states:
        with pytest.raises(ValueError, match=message):
            replace(rejected if "rejected" in message else pending, **changes)


def test_plan_admission_and_post_only_value_objects_reject_invalid_states() -> None:
    context = PlanAdmissionContext.initial()
    assessment = PlanAdmissionAssessment(
        schema_version="plan-admission-assessment/v1",
        capital_envelope=exact("250", "quote_quantity"),
        still_effective_quote_commitment=exact("0", "quote_quantity"),
        proposed_quote_commitment=exact("98", "quote_quantity"),
        bootstrap_quote_commitment=exact("38", "quote_quantity"),
        total_quote_commitment=exact("98", "quote_quantity"),
        fee_reserve=exact("5", "quote_quantity"),
        still_effective_inventory_commitment=exact("0", "base_quantity"),
        additional_bootstrap_inventory=exact("0.3", "base_quantity"),
        maximum_planned_inventory=exact("1.0", "base_quantity"),
        total_worst_case_inventory=exact("1.0", "base_quantity"),
        still_effective_order_count=0,
        proposed_order_count=5,
        total_order_count=5,
        venue_order_capacity=10,
        foreign_open_orders=0,
    )
    cycle = AdjacentCycleEconomics(
        schema_version="adjacent-cycle-economics/v1",
        buy_rung_index=0,
        sell_rung_index=1,
        buy_price=exact("99", "price"),
        sell_price=exact("101", "price"),
        cycle_quantity=exact("0.1", "base_quantity"),
        net_margin=exact("0.1", "quote_quantity"),
        positive=True,
        reason="ok",
    )
    report = PrincipalFeasibilityReport(
        schema_version="principal-feasibility-report/v1",
        points=(PrincipalFeasibilityPoint(exact("10", "quote_quantity"), True, ()),),
    )
    policy = PostOnlyRetryPolicy.accepted()
    contract = RuleFeeContract(
        schema_version="rule-fee-contract/v1",
        venue_rule_evidence_id=venue_rules().evidence_id,
        maker_fee=exact("0.0010", "fee_rate"),
        taker_fee=exact("0.0010", "fee_rate"),
    )

    invalid_objects = [
        (
            lambda: PlanAdmissionContext(
                "plan-admission-context/v2",
                exact("0", "quote_quantity"),
                exact("0", "base_quantity"),
                0,
            ),
            "context schema",
        ),
        (
            lambda: PlanAdmissionContext(
                "plan-admission-context/v1", exact("0", "price"), exact("0", "base_quantity"), 0
            ),
            "quote commitment",
        ),
        (
            lambda: PlanAdmissionContext(
                "plan-admission-context/v1",
                exact("0", "quote_quantity"),
                exact("0", "quote_quantity"),
                0,
            ),
            "inventory commitment",
        ),
        (
            lambda: PlanAdmissionContext(
                "plan-admission-context/v1",
                exact("0", "quote_quantity"),
                exact("0", "base_quantity"),
                -1,
            ),
            "order count",
        ),
        (
            lambda: replace(assessment, schema_version="plan-admission-assessment/v2"),
            "assessment schema",
        ),
        (lambda: replace(assessment, capital_envelope=exact("1", "price")), "quote quantities"),
        (
            lambda: replace(assessment, maximum_planned_inventory=exact("1", "quote_quantity")),
            "base quantities",
        ),
        (lambda: replace(assessment, foreign_open_orders=-1), "order counts"),
        (lambda: replace(assessment, venue_order_capacity=0), "order capacity"),
        (lambda: replace(cycle, schema_version="adjacent-cycle-economics/v2"), "economics schema"),
        (lambda: replace(cycle, buy_rung_index=1, sell_rung_index=1), "rung indices"),
        (lambda: replace(cycle, buy_price=exact("0", "price")), "prices"),
        (lambda: replace(cycle, cycle_quantity=exact("0", "base_quantity")), "quantity"),
        (lambda: replace(cycle, net_margin=exact("1", "ratio")), "net margin"),
        (lambda: replace(cycle, reason=""), "reason is required"),
        (
            lambda: PrincipalFeasibilityPoint(exact("0", "quote_quantity"), True, ()),
            "positive quote quantity",
        ),
        (
            lambda: PrincipalFeasibilityPoint(exact("10", "quote_quantity"), True, ("blocked",)),
            "cannot carry rejection reasons",
        ),
        (
            lambda: PrincipalFeasibilityPoint(exact("10", "quote_quantity"), False, ()),
            "must explain their rejection",
        ),
        (
            lambda: PrincipalFeasibilityReport("principal-feasibility-report/v2", report.points),
            "feasibility report schema",
        ),
        (
            lambda: PrincipalFeasibilityReport("principal-feasibility-report/v1", ()),
            "points are required",
        ),
        (
            lambda: replace(policy, schema_version="post-only-retry-policy/v2"),
            "retry policy schema",
        ),
        (lambda: replace(policy, order_type="LIMIT"), "LIMIT_MAKER"),
        (lambda: replace(policy, max_attempts=2), "accepted bounds"),
        (
            lambda: replace(policy, retry_delays=(exact("1", "duration_seconds"),)),
            "250 ms then one second",
        ),
        (
            lambda: replace(
                policy, retry_delays=(exact("0.25", "ratio"), exact("1", "duration_seconds"))
            ),
            "exact durations",
        ),
        (
            lambda: replace(policy, max_price_displacement_ratio=exact("0.0030", "ratio")),
            "displacement limits",
        ),
        (lambda: replace(contract, schema_version="rule-fee-contract/v2"), "contract schema"),
        (lambda: replace(contract, venue_rule_evidence_id="not-an-id"), "evidence identity"),
        (lambda: replace(contract, maker_fee=exact("0.1", "ratio")), "fee rates"),
    ]
    for build, message in invalid_objects:
        with pytest.raises(ValueError, match=message):
            build()


def test_initial_epoch_rejects_invalid_activation_and_policy_or_venue_limits() -> None:
    with pytest.raises(ValueError, match="activation price"):
        derive_initial_epoch(
            configuration=strategy(),
            observation=observation(),
            decision_time=DomainTime(BOUNDARY),
            activation_price=exact("0", "price"),
            derivation_causation_id="sha256:" + "a" * 64,
            venue_rules=venue_rules(),
            bootstrap_evidence=BootstrapEvidence.incomplete(),
        )
    with pytest.raises(ValueError, match="activation price"):
        derive_initial_epoch(
            configuration=strategy(),
            observation=observation(),
            decision_time=DomainTime(BOUNDARY),
            activation_price=exact("100", "ratio"),
            derivation_causation_id="sha256:" + "a" * 64,
            venue_rules=venue_rules(),
            bootstrap_evidence=BootstrapEvidence.incomplete(),
        )
    with pytest.raises(ValueError, match="collapse"):
        derive(
            configuration=replace(
                strategy(),
                lower_bound_limit=exact("105", "price"),
                upper_bound_limit=exact("106", "price"),
            )
        )

    uptrend = derive(evidence=observation(trend="0.0200"), activation_price="102.00")
    assert uptrend.epoch is not None
    assert uptrend.epoch.plan.lower.decimal > exact("96", "price").decimal
    downtrend = derive(evidence=observation(trend="-0.0200"))
    assert downtrend.epoch is not None
    assert all(rung.role != "BUY" for rung in downtrend.epoch.plan.rungs)

    minimum_quantity = derive(
        configuration=replace(
            strategy(),
            fixed_quote_principal=exact("5.01", "quote_quantity"),
        ),
        activation_price="100.00",
    )
    assert minimum_quantity.lifecycle is ActivationLifecycle.BOOTSTRAPPING
    restrictive_rules = replace(
        venue_rules(),
        minimum_quantity=exact("1", "base_quantity"),
    )
    below_quantity = derive_initial_epoch(
        configuration=strategy(),
        observation=observation(),
        decision_time=DomainTime(BOUNDARY),
        activation_price=exact("100", "price"),
        derivation_causation_id="sha256:" + "a" * 64,
        venue_rules=restrictive_rules,
        bootstrap_evidence=BootstrapEvidence.incomplete(),
    )
    assert below_quantity.gates[-1].reason == "quantized_obligation_below_minimum_quantity"

    collapsed = derive_initial_epoch(
        configuration=strategy(),
        observation=observation(),
        decision_time=DomainTime(BOUNDARY),
        activation_price=exact("100", "price"),
        derivation_causation_id="sha256:" + "a" * 64,
        venue_rules=replace(venue_rules(), tick_size=exact("10", "price_increment")),
        bootstrap_evidence=BootstrapEvidence.incomplete(),
    )
    assert collapsed.gates[-1].reason == "venue_quantization_collapsed_rungs"

    with pytest.raises(ValueError, match="below one"):
        derive(configuration=replace(strategy(), taker_fee=exact("1", "fee_rate")))
    capital = derive(
        configuration=replace(
            strategy(),
            fixed_quote_principal=exact("100", "quote_quantity"),
        )
    )
    assert capital.gates[-1].reason == "planned_obligations_exceed_capital_envelope"


def test_plan_admission_enforces_maximum_filters_capacity_and_inventory_commitments() -> None:
    minimum_price = derive_initial_epoch(
        configuration=strategy(),
        observation=observation(),
        decision_time=DomainTime(BOUNDARY),
        activation_price=exact("100", "price"),
        derivation_causation_id="sha256:" + "a" * 64,
        venue_rules=replace(venue_rules(), minimum_price=exact("100.01", "price")),
        bootstrap_evidence=BootstrapEvidence.incomplete(),
    )
    assert minimum_price.gates[-1].reason == "quantized_price_below_minimum_price"

    maximum_price = derive_initial_epoch(
        configuration=strategy(),
        observation=observation(),
        decision_time=DomainTime(BOUNDARY),
        activation_price=exact("100", "price"),
        derivation_causation_id="sha256:" + "a" * 64,
        venue_rules=replace(venue_rules(), maximum_price=exact("99.00", "price")),
        bootstrap_evidence=BootstrapEvidence.incomplete(),
    )
    assert maximum_price.gates[-1].reason == "quantized_price_above_maximum_price"

    zero_quantity = derive_initial_epoch(
        configuration=strategy(),
        observation=observation(),
        decision_time=DomainTime(BOUNDARY),
        activation_price=exact("100", "price"),
        derivation_causation_id="sha256:" + "a" * 64,
        venue_rules=replace(venue_rules(), step_size=exact("1", "quantity_increment")),
        bootstrap_evidence=BootstrapEvidence.incomplete(),
    )
    assert zero_quantity.gates[-1].reason == "quantized_obligation_zero_quantity"

    maximum_quantity = derive_initial_epoch(
        configuration=strategy(),
        observation=observation(),
        decision_time=DomainTime(BOUNDARY),
        activation_price=exact("100", "price"),
        derivation_causation_id="sha256:" + "a" * 64,
        venue_rules=replace(venue_rules(), maximum_quantity=exact("0.10", "base_quantity")),
        bootstrap_evidence=BootstrapEvidence.incomplete(),
    )
    assert maximum_quantity.gates[-1].reason == "quantized_obligation_above_maximum_quantity"

    maximum_notional = derive_initial_epoch(
        configuration=strategy(),
        observation=observation(),
        decision_time=DomainTime(BOUNDARY),
        activation_price=exact("100", "price"),
        derivation_causation_id="sha256:" + "a" * 64,
        venue_rules=replace(venue_rules(), maximum_notional=exact("10", "quote_quantity")),
        bootstrap_evidence=BootstrapEvidence.incomplete(),
    )
    assert maximum_notional.gates[-1].reason == "quantized_obligation_above_maximum_notional"

    capacity = derive_initial_epoch(
        configuration=strategy(),
        observation=observation(),
        decision_time=DomainTime(BOUNDARY),
        activation_price=exact("100", "price"),
        derivation_causation_id="sha256:" + "a" * 64,
        venue_rules=replace(venue_rules(), max_open_orders=3, foreign_open_orders=1),
        bootstrap_evidence=BootstrapEvidence.incomplete(),
    )
    assert capacity.gates[-1].reason == "planned_orders_exceed_venue_capacity"

    inventory = derive_initial_epoch(
        configuration=strategy(),
        observation=observation(),
        decision_time=DomainTime(BOUNDARY),
        activation_price=exact("100", "price"),
        derivation_causation_id="sha256:" + "a" * 64,
        venue_rules=venue_rules(),
        bootstrap_evidence=BootstrapEvidence.incomplete(),
        admission_context=PlanAdmissionContext(
            schema_version="plan-admission-context/v1",
            still_effective_quote_commitment=exact("0", "quote_quantity"),
            still_effective_inventory_commitment=exact("1.00000", "base_quantity"),
            still_effective_order_count=0,
        ),
    )
    assert inventory.gates[-1].reason == "planned_inventory_exceeds_maximum_inventory"


def test_positive_adjacent_cycle_report_and_post_only_policy_are_admitted_deterministically() -> (
    None
):
    result = derive()

    assert result.epoch is not None
    assert result.admission_assessment is not None
    assert result.post_only_retry_policy.order_type == "LIMIT_MAKER"
    assert result.post_only_retry_policy.max_attempts == 3
    assert result.rule_fee_contract.contract_id.startswith("sha256:")
    assert all(item.positive for item in result.adjacent_cycle_economics)
    assert result.principal_feasibility.points[0].principal.decimal == Decimal("10")
    assert result.principal_feasibility.points[-1].principal.decimal == Decimal("20")
    assert len(result.principal_feasibility.points) == 11

    restrictive = derive_initial_epoch(
        configuration=strategy(),
        observation=observation(),
        decision_time=DomainTime(BOUNDARY),
        activation_price=exact("100", "price"),
        derivation_causation_id="sha256:" + "a" * 64,
        venue_rules=replace(venue_rules(), maximum_quantity=exact("0.10", "base_quantity")),
        bootstrap_evidence=BootstrapEvidence.incomplete(),
    )
    assert any(not point.feasible for point in restrictive.principal_feasibility.points)
    assert (
        "quantized_obligation_above_maximum_quantity"
        in restrictive.principal_feasibility.points[0].reasons
    )

    capital_restrictive = derive_initial_epoch(
        configuration=strategy(),
        observation=observation(),
        decision_time=DomainTime(BOUNDARY),
        activation_price=exact("100", "price"),
        derivation_causation_id="sha256:" + "a" * 64,
        venue_rules=replace(venue_rules(), minimum_notional=exact("0", "quote_quantity")),
        bootstrap_evidence=BootstrapEvidence.incomplete(),
        admission_context=PlanAdmissionContext(
            schema_version="plan-admission-context/v1",
            still_effective_quote_commitment=exact("245", "quote_quantity"),
            still_effective_inventory_commitment=exact("0", "base_quantity"),
            still_effective_order_count=0,
        ),
    )
    assert "planned_obligations_exceed_capital_envelope" in (
        capital_restrictive.principal_feasibility.points[-1].reasons
    )

    dust_cycle = derive_initial_epoch(
        configuration=replace(
            strategy(),
            fixed_quote_principal=exact("0.0104", "quote_quantity"),
        ),
        observation=observation(),
        decision_time=DomainTime(BOUNDARY),
        activation_price=exact("100", "price"),
        derivation_causation_id="sha256:" + "a" * 64,
        venue_rules=replace(venue_rules(), minimum_notional=exact("0", "quote_quantity")),
        bootstrap_evidence=BootstrapEvidence.incomplete(),
    )
    assert dust_cycle.gates[-1].reason == "adjacent_cycle_quantity_below_minimum_quantity"

    non_positive = derive(
        configuration=replace(
            strategy(),
            maker_fee=exact("0.0200", "fee_rate"),
        )
    )
    assert non_positive.gates[-1].reason == (
        "adjacent_cycle_not_positive_after_fees_rounding_allowance_and_margin"
    )


@pytest.mark.parametrize(
    ("trend", "volatility", "state"),
    [
        ("0.0200", "0.0100", AdaptationState.TREND_UP),
        ("0.0000", "0.0300", AdaptationState.RANGE_HIGH_VOLATILITY),
    ],
)
def test_bounded_legacy_diagnostic_builds_matching_confirmation_evidence(
    trend: str,
    volatility: str,
    state: AdaptationState,
) -> None:
    result = characterize_legacy_backtest(
        symbol="BTCEUR",
        decision_time=DomainTime(BOUNDARY),
        trend=trend,
        volatility=volatility,
    )

    assert all(item.state is state for item in result.observation.confirmations)


def test_obligation_backed_plan_value_objects_reject_inconsistent_material() -> None:
    result = derive()
    assert result.epoch is not None
    plan = result.epoch.plan
    obligation = plan.obligations[0]
    bootstrap = plan.bootstrap_obligation
    assert bootstrap is not None

    with pytest.raises(ValueError, match="base quantity must be positive"):
        replace(obligation, base_quantity=exact("0", "base_quantity"))
    with pytest.raises(ValueError, match="base quantity must be positive"):
        replace(obligation, base_quantity=exact("1", "quote_quantity"))

    invalid_bootstrap = [
        ({"schema_version": "bootstrap-obligation/v2"}, "schema"),
        (
            {"net_base_required": exact("-1", "base_quantity")},
            "non-negative base quantity",
        ),
        (
            {"net_base_required": exact("1", "quote_quantity")},
            "non-negative base quantity",
        ),
        (
            {
                "net_base_required": exact("2", "base_quantity"),
                "gross_base_required": exact("1", "base_quantity"),
                "fee_base_coverage": exact("-1", "base_quantity"),
            },
            "non-negative base quantity",
        ),
        (
            {
                "net_base_required": exact("2", "base_quantity"),
                "gross_base_required": exact("1", "base_quantity"),
                "fee_base_coverage": exact("0", "base_quantity"),
            },
            "cannot be below",
        ),
        (
            {"fee_base_coverage": exact("0", "base_quantity")},
            "reconcile exactly",
        ),
    ]
    for changes, message in invalid_bootstrap:
        with pytest.raises(ValueError, match=message):
            replace(bootstrap, **changes)

    missing_quantity = replace(plan.obligations[0], base_quantity=None)
    with pytest.raises(ValueError, match="exact base quantities"):
        replace(plan, obligations=(missing_quantity, *plan.obligations[1:]))
    with pytest.raises(ValueError, match="maximum planned inventory"):
        replace(
            plan,
            maximum_planned_inventory=exact("-1", "base_quantity"),
        )
    with pytest.raises(ValueError, match="maximum planned inventory"):
        replace(
            plan,
            maximum_planned_inventory=exact("1", "quote_quantity"),
        )
    with pytest.raises(ValueError, match="cover every initial sell"):
        replace(
            plan,
            bootstrap_obligation=replace(
                bootstrap,
                net_base_required=bootstrap.gross_base_required,
                fee_base_coverage=exact("0", "base_quantity"),
            ),
        )
    with pytest.raises(ValueError, match="activation price"):
        replace(plan, activation_price=exact("0", "price"))
    with pytest.raises(ValueError, match="activation price"):
        replace(plan, activation_price=exact("100", "ratio"))
