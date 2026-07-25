from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from gridlab.canonical.adaptation import AdaptationState
from gridlab.canonical.events import DomainTime
from gridlab.canonical.safety import (
    AllowedCommandClass,
    CapitalCommitmentFacts,
    ClockEvidence,
    EvidenceClass,
    EvidenceCondition,
    FreshnessEvidence,
    LifecycleFacts,
    LossFacts,
    RangeCondition,
    RecoveryObligation,
    SafetyEvaluation,
    SafetyHazard,
    SafetyPosture,
    SafetyRecoveryFacts,
    SymbolCondition,
    VenueConditionEvidence,
    evaluate_safety_posture,
)
from gridlab.canonical.values import ExactDecimal


UTC = timezone.utc
NOW = DomainTime(datetime(2025, 1, 2, 12, 0, tzinfo=UTC))


def exact(value: str, kind: str = "quote_quantity") -> ExactDecimal:
    return ExactDecimal.parse(value, kind=kind)


def capital() -> CapitalCommitmentFacts:
    return CapitalCommitmentFacts(
        schema_version="capital-commitment-facts/v1",
        allocation_fingerprint="sha256:" + "1" * 64,
        epoch_id="sha256:" + "2" * 64,
        capital_envelope=exact("250"),
        committed_principal=exact("200"),
        fee_reserve=exact("10"),
        projected_obligation_fees=exact("2"),
        projected_terminal_fees=exact("1"),
        exposure_increasing_buy_principals=(exact("20"), exact("19.50")),
        effective_managed_orders=10,
        foreign_open_orders=2,
        authenticated_order_limit=100,
        current_inventory=exact("1.0", "base_quantity"),
        pending_buy_inventory=exact("0.4", "base_quantity"),
        transition_bootstrap_inventory=exact("0.1", "base_quantity"),
        proposed_maximum_inventory=exact("1.5", "base_quantity"),
        maximum_planned_inventory=exact("1.5", "base_quantity"),
    )


def loss() -> LossFacts:
    return LossFacts(
        schema_version="loss-facts/v1",
        initial_equity=exact("250"),
        risk_day_baseline=exact("250"),
        run_high_water_mark=exact("250"),
        conservative_liquidation_equity=exact("249"),
        prior_daily_loss_latched=False,
        prior_run_drawdown_latched=False,
        guardrail_recovery_approved=False,
        global_stop_latched=False,
    )


def freshness(
    evidence_class: EvidenceClass,
    *,
    age: timedelta = timedelta(seconds=1),
    condition: EvidenceCondition = EvidenceCondition.HEALTHY,
) -> FreshnessEvidence:
    return FreshnessEvidence(
        schema_version="freshness-evidence/v1",
        evidence_class=evidence_class,
        condition=condition,
        observed_at=DomainTime(NOW.value - age)
        if condition is not EvidenceCondition.MISSING
        else None,
        evidence_id="sha256:" + evidence_class.value[0].lower() * 64,
    )


def all_freshness() -> tuple[FreshnessEvidence, ...]:
    return tuple(freshness(item) for item in EvidenceClass)


def clock(
    *,
    venue_delta_ms: int = 0,
    round_trip_ms: int = 200,
    condition: EvidenceCondition = EvidenceCondition.HEALTHY,
    timestamp_rejected: bool = False,
    scheduling_delay: str = "0.025000",
) -> ClockEvidence:
    sent = NOW.value - timedelta(milliseconds=round_trip_ms)
    midpoint = sent + timedelta(milliseconds=round_trip_ms / 2)
    return ClockEvidence(
        schema_version="clock-evidence/v1",
        condition=condition,
        request_sent_at=DomainTime(sent),
        response_received_at=NOW,
        venue_time=DomainTime(midpoint + timedelta(milliseconds=venue_delta_ms)),
        scheduling_delay=exact(scheduling_delay, "duration_seconds"),
        authenticated_timestamp_rejected=timestamp_rejected,
        evidence_id="sha256:" + "c" * 64,
    )


def lifecycle() -> LifecycleFacts:
    return LifecycleFacts(
        schema_version="lifecycle-facts/v1",
        grid_lifecycle="ACTIVE",
        adaptation_state=AdaptationState.RANGE_NORMAL,
        epoch_transition_state="IDLE",
        runtime_lifecycle="OPERATING",
        reconciliation_state="RECONCILED",
    )


def recovery() -> SafetyRecoveryFacts:
    return SafetyRecoveryFacts(
        schema_version="safety-recovery-facts/v1",
        prior_frozen_latched=False,
        frozen_recovery_approved=False,
    )


def evaluate(**changes: object) -> SafetyEvaluation:
    arguments = {
        "decision_time": NOW,
        "capital": capital(),
        "loss": loss(),
        "freshness": all_freshness(),
        "clock": clock(),
        "lifecycle": lifecycle(),
        "recovery": recovery(),
        "range_condition": RangeCondition.IN_RANGE,
        "recovery_obligations": (),
        "venue": VenueConditionEvidence.trading(),
        "prior_global_stop_latched": False,
    }
    arguments.update(changes)
    return evaluate_safety_posture(**arguments)


@pytest.mark.parametrize(
    ("facts", "reason", "posture"),
    [
        (
            replace(capital(), capital_envelope=exact("250.01")),
            "capital_envelope_exceeds_mvp_ceiling",
            SafetyPosture.FROZEN,
        ),
        (
            replace(capital(), committed_principal=exact("246"), fee_reserve=exact("5")),
            "worst_case_commitment_exceeds_envelope",
            SafetyPosture.FROZEN,
        ),
        (
            replace(capital(), fee_reserve=exact("5.99")),
            "fee_reserve_is_insufficient",
            SafetyPosture.REDUCE_ONLY,
        ),
        (
            replace(capital(), exposure_increasing_buy_principals=(exact("20.01"),)),
            "buy_principal_exceeds_ceiling",
            SafetyPosture.FROZEN,
        ),
        (
            replace(capital(), effective_managed_orders=21),
            "effective_order_capacity_exceeded",
            SafetyPosture.REDUCE_ONLY,
        ),
        (
            replace(capital(), authenticated_order_limit=20, foreign_open_orders=1),
            "venue_order_headroom_is_insufficient",
            SafetyPosture.REDUCE_ONLY,
        ),
        (
            replace(capital(), proposed_maximum_inventory=exact("1.50001", "base_quantity")),
            "maximum_planned_inventory_exceeded",
            SafetyPosture.REDUCE_ONLY,
        ),
    ],
)
def test_capital_and_worst_case_commitment_limits(
    facts: CapitalCommitmentFacts, reason: str, posture: SafetyPosture
) -> None:
    result = evaluate(capital=facts)

    assert result.posture is posture
    assert reason in result.reason_codes
    assert AllowedCommandClass.EXPOSURE_INCREASING not in result.allowed_command_classes


@pytest.mark.parametrize(
    ("equity", "posture", "warning", "latched"),
    [
        ("246", SafetyPosture.NORMAL, True, False),
        ("245", SafetyPosture.REDUCE_ONLY, True, False),
        ("230", SafetyPosture.REDUCE_ONLY, True, False),
        ("220", SafetyPosture.TERMINAL_LIQUIDATION, True, True),
    ],
)
def test_warning_reduce_only_and_terminal_latch_thresholds(
    equity: str, posture: SafetyPosture, warning: bool, latched: bool
) -> None:
    result = evaluate(loss=replace(loss(), conservative_liquidation_equity=exact(equity)))

    assert result.posture is posture
    assert result.loss_warning is warning
    assert result.global_stop_latched is latched


def test_global_stop_is_irreversible_and_precedence_is_monotonic() -> None:
    stopped = evaluate(
        loss=replace(loss(), conservative_liquidation_equity=exact("219")),
        prior_global_stop_latched=True,
        freshness=tuple(
            replace(item, condition=EvidenceCondition.MISSING, observed_at=None)
            if item.evidence_class is EvidenceClass.VALUATION
            else item
            for item in all_freshness()
        ),
    )
    recovered_market = evaluate(
        loss=loss(),
        prior_global_stop_latched=stopped.global_stop_latched,
    )

    assert stopped.posture is SafetyPosture.FROZEN
    assert stopped.global_stop_latched is True
    assert recovered_market.posture is SafetyPosture.TERMINAL_LIQUIDATION
    assert stopped.hazards == tuple(
        sorted(stopped.hazards, key=lambda item: (-item.severity, item.code))
    )


@pytest.mark.parametrize(
    ("evidence_class", "condition", "age", "posture"),
    [
        (EvidenceClass.VALUATION, EvidenceCondition.MISSING, 0, SafetyPosture.FROZEN),
        (EvidenceClass.VALUATION, EvidenceCondition.HEALTHY, 6, SafetyPosture.FROZEN),
        (EvidenceClass.STRATEGY_INPUT, EvidenceCondition.MISSING, 0, SafetyPosture.REDUCE_ONLY),
        (EvidenceClass.STRATEGY_INPUT, EvidenceCondition.HEALTHY, 16, SafetyPosture.REDUCE_ONLY),
        (EvidenceClass.PRIVATE_STREAM, EvidenceCondition.GAPPED, 1, SafetyPosture.FROZEN),
        (EvidenceClass.CONTROL_PATH, EvidenceCondition.UNAVAILABLE, 10, SafetyPosture.FROZEN),
        (EvidenceClass.CONTROL_PATH, EvidenceCondition.HEALTHY, 10, SafetyPosture.FROZEN),
        (EvidenceClass.CLOCK, EvidenceCondition.MISSING, 0, SafetyPosture.FROZEN),
    ],
)
def test_missing_or_stale_evidence_selects_class_posture(
    evidence_class: EvidenceClass,
    condition: EvidenceCondition,
    age: int,
    posture: SafetyPosture,
) -> None:
    evidence = tuple(
        freshness(item)
        if item is not evidence_class
        else freshness(item, age=timedelta(seconds=age), condition=condition)
        for item in EvidenceClass
    )

    assert evaluate(freshness=evidence).posture is posture


def test_clock_uses_midpoint_offset_and_not_scheduling_delay() -> None:
    delayed = evaluate(clock=clock(round_trip_ms=4000, venue_delta_ms=100))
    offset = evaluate(clock=clock(round_trip_ms=200, venue_delta_ms=501))
    rejected = evaluate(clock=clock(timestamp_rejected=True))

    assert delayed.posture is SafetyPosture.NORMAL
    assert delayed.clock_offset.source == "0.100000"
    assert delayed.scheduling_delay.source == "0.025000"
    assert delayed.round_trip_latency.source == "4.000000"
    assert offset.posture is SafetyPosture.FROZEN
    assert rejected.posture is SafetyPosture.FROZEN
    assert "authenticated_timestamp_rejection" in rejected.reason_codes


def test_range_exhaustion_preserves_only_fully_backed_inventory_reduction() -> None:
    recovery = (
        RecoveryObligation(
            obligation_id="sha256:" + "a" * 64,
            side="SELL",
            price=exact("104", "price"),
            fully_backed=True,
            inventory_reducing=True,
            inside_outer_rungs=True,
        ),
        RecoveryObligation(
            obligation_id="sha256:" + "b" * 64,
            side="BUY",
            price=exact("80", "price"),
            fully_backed=True,
            inventory_reducing=False,
            inside_outer_rungs=False,
        ),
    )

    result = evaluate(
        range_condition=RangeCondition.BELOW_RANGE,
        recovery_obligations=recovery,
    )

    assert result.posture is SafetyPosture.REDUCE_ONLY
    assert result.permitted_recovery_obligation_ids == (recovery[0].obligation_id,)
    assert AllowedCommandClass.INVENTORY_REDUCING in result.allowed_command_classes
    assert AllowedCommandClass.EXPOSURE_INCREASING not in result.allowed_command_classes


@pytest.mark.parametrize(
    ("state", "posture", "replacement", "sizing_increase"),
    [
        (AdaptationState.TREND_DOWN, SafetyPosture.REDUCE_ONLY, True, False),
        (AdaptationState.UNCERTAIN, SafetyPosture.FROZEN, False, False),
        (AdaptationState.RANGE_HIGH_VOLATILITY, SafetyPosture.NORMAL, True, False),
    ],
)
def test_adaptive_state_restrictions(
    state: AdaptationState,
    posture: SafetyPosture,
    replacement: bool,
    sizing_increase: bool,
) -> None:
    result = evaluate(lifecycle=replace(lifecycle(), adaptation_state=state))

    assert result.posture is posture
    assert result.placement_allowed is (posture is SafetyPosture.NORMAL)
    assert result.replacement_allowed is replacement
    assert result.fixed_quote_sizing_increase_allowed is sizing_increase
    if state is AdaptationState.TREND_DOWN:
        assert result.downward_bound_shift_allowed is False
        assert AllowedCommandClass.EXPOSURE_INCREASING not in result.allowed_command_classes


@pytest.mark.parametrize(
    ("condition", "posture"),
    [
        (SymbolCondition.SUSPENDED, SafetyPosture.FROZEN),
        (SymbolCondition.MAINTENANCE, SafetyPosture.FROZEN),
        (SymbolCondition.DELISTING, SafetyPosture.REDUCE_ONLY),
    ],
)
def test_symbol_suspension_maintenance_and_delisting(
    condition: SymbolCondition, posture: SafetyPosture
) -> None:
    venue = VenueConditionEvidence(
        schema_version="venue-condition-evidence/v1",
        condition=condition,
        observed_at=NOW,
        evidence_id="sha256:" + "d" * 64,
        source="fixture",
        wind_down_deadline=(
            DomainTime(NOW.value + timedelta(days=7))
            if condition is SymbolCondition.DELISTING
            else None
        ),
    )

    result = evaluate(venue=venue)

    assert result.posture is posture
    assert result.venue_evidence_id == venue.evidence_id
    assert (result.wind_down_deadline is not None) is (condition is SymbolCondition.DELISTING)


def test_replay_identity_and_typed_facts_are_deterministic_and_separate() -> None:
    first = evaluate()
    second = evaluate()

    assert first == second
    assert first.fingerprint == second.fingerprint
    assert first.input_fingerprint == second.input_fingerprint
    assert evaluate(capital=replace(capital(), committed_principal=exact("201"))).fingerprint != (
        first.fingerprint
    )
    assert (
        evaluate(loss=replace(loss(), conservative_liquidation_equity=exact("248"))).fingerprint
        != first.fingerprint
    )
    assert first.lifecycle.grid_lifecycle == "ACTIVE"
    assert first.lifecycle.adaptation_state is AdaptationState.RANGE_NORMAL
    assert first.lifecycle.epoch_transition_state == "IDLE"
    assert first.lifecycle.runtime_lifecycle == "OPERATING"
    assert first.posture is SafetyPosture.NORMAL
    assert first.freshness
    assert first.lifecycle.reconciliation_state == "RECONCILED"


def test_daily_and_drawdown_percentages_use_their_own_baselines() -> None:
    result = evaluate(
        loss=replace(
            loss(),
            risk_day_baseline=exact("230"),
            run_high_water_mark=exact("240"),
            conservative_liquidation_equity=exact("225.3"),
        )
    )

    assert result.posture is SafetyPosture.REDUCE_ONLY
    assert "daily_loss_threshold_reached" in result.reason_codes


def test_loss_guardrails_do_not_resume_without_approved_recovery() -> None:
    latched = evaluate(
        loss=replace(
            loss(),
            prior_daily_loss_latched=True,
            prior_run_drawdown_latched=True,
        )
    )
    approved = evaluate(
        loss=replace(
            loss(),
            prior_daily_loss_latched=True,
            prior_run_drawdown_latched=True,
            guardrail_recovery_approved=True,
        )
    )

    assert latched.posture is SafetyPosture.REDUCE_ONLY
    assert latched.daily_loss_latched is True
    assert latched.run_drawdown_latched is True
    assert approved.posture is SafetyPosture.NORMAL
    assert approved.daily_loss_latched is False
    assert approved.run_drawdown_latched is False


def test_recovery_requires_reconciliation_and_explicit_approval() -> None:
    still_frozen = evaluate(
        lifecycle=replace(lifecycle(), reconciliation_state="UNRECONCILED"),
        recovery=replace(
            recovery(),
            prior_frozen_latched=True,
            frozen_recovery_approved=True,
        ),
    )
    approved = evaluate(
        recovery=replace(
            recovery(),
            prior_frozen_latched=True,
            frozen_recovery_approved=True,
        )
    )

    assert still_frozen.posture is SafetyPosture.FROZEN
    assert approved.posture is SafetyPosture.NORMAL


def test_loss_baselines_must_be_positive_canonical_facts() -> None:
    with pytest.raises(ValueError, match="baselines must be positive"):
        replace(loss(), risk_day_baseline=exact("0"))
    with pytest.raises(ValueError, match="baselines must be positive"):
        replace(loss(), run_high_water_mark=exact("0"))


def test_closed_grid_lifecycle_has_closed_posture_and_no_trading_authority() -> None:
    result = evaluate(lifecycle=replace(lifecycle(), grid_lifecycle="CLOSED"))

    assert result.posture is SafetyPosture.CLOSED
    assert result.allowed_command_classes == (AllowedCommandClass.EVIDENCE_GATHERING,)


def test_safety_contracts_reject_invalid_canonical_material() -> None:
    with pytest.raises(ValueError, match="capital commitment facts schema"):
        replace(capital(), schema_version="capital-commitment-facts/v2")
    with pytest.raises(ValueError, match="allocation fingerprint"):
        replace(capital(), allocation_fingerprint="invalid")
    with pytest.raises(ValueError, match="epoch identity"):
        replace(capital(), epoch_id="invalid")
    with pytest.raises(ValueError, match="quote quantities"):
        replace(capital(), fee_reserve=exact("1", "base_quantity"))
    with pytest.raises(ValueError, match="base quantities"):
        replace(capital(), current_inventory=exact("1", "quote_quantity"))
    with pytest.raises(ValueError, match="order counts"):
        replace(capital(), foreign_open_orders=-1)

    with pytest.raises(ValueError, match="loss facts schema"):
        replace(loss(), schema_version="loss-facts/v2")
    with pytest.raises(ValueError, match="non-negative quote"):
        replace(loss(), conservative_liquidation_equity=exact("-1"))
    with pytest.raises(ValueError, match="initial equity"):
        replace(loss(), initial_equity=exact("0"))

    healthy = freshness(EvidenceClass.VALUATION)
    with pytest.raises(ValueError, match="freshness evidence schema"):
        replace(healthy, schema_version="freshness-evidence/v2")
    with pytest.raises(ValueError, match="freshness evidence identity"):
        replace(healthy, evidence_id="invalid")
    with pytest.raises(ValueError, match="missing evidence"):
        replace(healthy, condition=EvidenceCondition.MISSING)
    with pytest.raises(ValueError, match="explicit time"):
        replace(healthy, observed_at=None)

    healthy_clock = clock()
    with pytest.raises(ValueError, match="clock evidence schema"):
        replace(healthy_clock, schema_version="clock-evidence/v2")
    with pytest.raises(ValueError, match="precede"):
        replace(
            healthy_clock,
            response_received_at=DomainTime(
                healthy_clock.request_sent_at.value - timedelta(microseconds=1)
            ),
        )
    with pytest.raises(ValueError, match="scheduling delay"):
        replace(healthy_clock, scheduling_delay=exact("-0.1", "duration_seconds"))
    with pytest.raises(ValueError, match="clock evidence identity"):
        replace(healthy_clock, evidence_id="invalid")

    with pytest.raises(ValueError, match="lifecycle facts schema"):
        replace(lifecycle(), schema_version="lifecycle-facts/v2")
    with pytest.raises(ValueError, match="separate lifecycle facts"):
        replace(lifecycle(), runtime_lifecycle="")
    with pytest.raises(ValueError, match="recovery facts schema"):
        replace(recovery(), schema_version="safety-recovery-facts/v2")

    obligation = RecoveryObligation(
        obligation_id="sha256:" + "a" * 64,
        side="SELL",
        price=exact("100", "price"),
        fully_backed=True,
        inventory_reducing=True,
        inside_outer_rungs=True,
    )
    with pytest.raises(ValueError, match="obligation identity"):
        replace(obligation, obligation_id="invalid")
    with pytest.raises(ValueError, match="side"):
        replace(obligation, side="HOLD")
    with pytest.raises(ValueError, match="price"):
        replace(obligation, price=exact("0", "price"))

    venue = VenueConditionEvidence.trading()
    with pytest.raises(ValueError, match="venue condition evidence schema"):
        replace(venue, schema_version="venue-condition-evidence/v2")
    with pytest.raises(ValueError, match="identity and source"):
        replace(venue, evidence_id="invalid")
    with pytest.raises(ValueError, match="identity and source"):
        replace(venue, source="")
    with pytest.raises(ValueError, match="future wind-down"):
        replace(venue, condition=SymbolCondition.DELISTING)
    with pytest.raises(ValueError, match="future wind-down"):
        replace(
            venue,
            condition=SymbolCondition.DELISTING,
            wind_down_deadline=venue.observed_at,
        )
    with pytest.raises(ValueError, match="only delisting"):
        replace(
            venue,
            wind_down_deadline=DomainTime(venue.observed_at.value + timedelta(days=1)),
        )

    with pytest.raises(ValueError, match="hazard posture severity"):
        SafetyHazard("", SafetyPosture.NORMAL, 0, ())
    normal = evaluate()
    with pytest.raises(ValueError, match="safety evaluation schema"):
        replace(normal, schema_version="safety-evaluation/v2")
    with pytest.raises(ValueError, match="input fingerprint"):
        replace(normal, input_fingerprint="invalid")
    with pytest.raises(ValueError, match="must be latched"):
        replace(
            normal,
            posture=SafetyPosture.TERMINAL_LIQUIDATION,
            global_stop_latched=False,
        )


def test_safety_evaluation_rejects_missing_and_duplicate_freshness_classes() -> None:
    with pytest.raises(ValueError, match="exactly one freshness"):
        evaluate(freshness=all_freshness()[:-1])
    with pytest.raises(ValueError, match="must be unique"):
        evaluate(freshness=all_freshness() + (freshness(EvidenceClass.CLOCK),))


def test_unhealthy_or_future_clock_observation_freezes() -> None:
    unhealthy = evaluate(clock=clock(condition=EvidenceCondition.STALE))
    future = evaluate(
        clock=replace(
            clock(),
            response_received_at=DomainTime(NOW.value + timedelta(milliseconds=1)),
            venue_time=DomainTime(NOW.value),
        )
    )

    assert unhealthy.posture is SafetyPosture.FROZEN
    assert future.posture is SafetyPosture.FROZEN
