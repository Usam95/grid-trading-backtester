from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from gridlab.api.canonical_translation import characterize_legacy_backtest
from gridlab.canonical.adaptation import AdaptationState, EvidenceQuality, PriorDecisionEvidence
from gridlab.canonical.epoch_transition import (
    EpochTransitionFacts,
    FakeTransitionRuntime,
    LateFillPosting,
    ManagedOrderState,
    OldEpochOrder,
    TransitionGate,
    TransitionGateOutcome,
    TransitionCrashBoundary,
    TransitionPhase,
    TransitionProgressStep,
    TransitionStepStatus,
    evaluate_epoch_transition,
)
from gridlab.canonical.events import DomainTime
from gridlab.canonical.initial_epoch import BootstrapEvidence, PlanAdmissionContext
from gridlab.canonical.operator_controls import InventoryBasis
from gridlab.canonical.safety import (
    CapitalCommitmentFacts,
    ClockEvidence,
    EvidenceClass,
    EvidenceCondition,
    FreshnessEvidence,
    LifecycleFacts,
    LossFacts,
    RangeCondition,
    SafetyRecoveryFacts,
    SymbolCondition,
    VenueConditionEvidence,
    evaluate_safety_posture,
)
from gridlab.canonical.values import ExactDecimal
from gridlab.persistence.transition_journal import SQLiteTransitionJournal


UTC = timezone.utc
BOUNDARY = datetime(2025, 1, 2, 8, 0, tzinfo=UTC)


def exact(value: str, kind: str = "quote_quantity") -> ExactDecimal:
    return ExactDecimal.parse(value, kind=kind)


def active_fixture():
    return characterize_legacy_backtest(
        symbol="BTCEUR",
        decision_time=DomainTime(datetime(2025, 1, 2, 0, 0, tzinfo=UTC)),
        quality=EvidenceQuality.ADMITTED,
    )


def safety() -> object:
    decision_time = DomainTime(BOUNDARY)
    freshness = tuple(
        FreshnessEvidence(
            schema_version="freshness-evidence/v1",
            evidence_class=evidence_class,
            condition=EvidenceCondition.HEALTHY,
            observed_at=DomainTime(BOUNDARY - timedelta(seconds=1)),
            evidence_id=f"sha256:{evidence_class.value[0].lower() * 64}",
        )
        for evidence_class in EvidenceClass
    )
    return evaluate_safety_posture(
        decision_time=decision_time,
        capital=CapitalCommitmentFacts(
            schema_version="capital-commitment-facts/v1",
            allocation_fingerprint="sha256:" + "1" * 64,
            epoch_id="sha256:" + "2" * 64,
            capital_envelope=exact("250"),
            committed_principal=exact("40"),
            fee_reserve=exact("5"),
            projected_obligation_fees=exact("1"),
            projected_terminal_fees=exact("1"),
            exposure_increasing_buy_principals=(exact("20"),),
            effective_managed_orders=4,
            foreign_open_orders=0,
            authenticated_order_limit=100,
            current_inventory=exact("0.60000000", "base_quantity"),
            pending_buy_inventory=exact("0.00000000", "base_quantity"),
            transition_bootstrap_inventory=exact("0.00000000", "base_quantity"),
            proposed_maximum_inventory=exact("0.80000000", "base_quantity"),
            maximum_planned_inventory=exact("0.80000000", "base_quantity"),
        ),
        loss=LossFacts(
            schema_version="loss-facts/v1",
            initial_equity=exact("250"),
            risk_day_baseline=exact("250"),
            run_high_water_mark=exact("250"),
            conservative_liquidation_equity=exact("249"),
            prior_daily_loss_latched=False,
            prior_run_drawdown_latched=False,
            guardrail_recovery_approved=False,
            global_stop_latched=False,
        ),
        freshness=freshness,
        clock=ClockEvidence(
            schema_version="clock-evidence/v1",
            condition=EvidenceCondition.HEALTHY,
            request_sent_at=DomainTime(BOUNDARY - timedelta(milliseconds=100)),
            response_received_at=decision_time,
            venue_time=DomainTime(BOUNDARY - timedelta(milliseconds=50)),
            scheduling_delay=exact("0.025000", "duration_seconds"),
            authenticated_timestamp_rejected=False,
            evidence_id="sha256:" + "c" * 64,
        ),
        lifecycle=LifecycleFacts(
            schema_version="lifecycle-facts/v1",
            grid_lifecycle="ACTIVE",
            adaptation_state=active_fixture().epoch.decision.state,
            epoch_transition_state="IDLE",
            runtime_lifecycle="OPERATING",
            reconciliation_state="RECONCILED",
        ),
        recovery=SafetyRecoveryFacts(
            schema_version="safety-recovery-facts/v1",
            prior_frozen_latched=False,
            frozen_recovery_approved=False,
        ),
        range_condition=RangeCondition.IN_RANGE,
        recovery_obligations=(),
        venue=VenueConditionEvidence(
            schema_version="venue-condition-evidence/v1",
            condition=SymbolCondition.TRADING,
            observed_at=decision_time,
            evidence_id="sha256:" + "d" * 64,
            source="canonical-fixture",
            wind_down_deadline=None,
        ),
        prior_global_stop_latched=False,
    )


def inventory_basis() -> InventoryBasis:
    return InventoryBasis(
        basis_id="sha256:" + "3" * 64,
        source="canonical-reconciliation",
        base_asset="BTC",
        quantity=exact("0.60000000", "base_quantity"),
        authoritative=True,
        reconciled_at=DomainTime(BOUNDARY),
    )


def facts(**changes: object) -> EpochTransitionFacts:
    active = active_fixture()
    decision_time = DomainTime(BOUNDARY)
    observation = replace(
        active.observation,
        event_time=decision_time,
        window_start=DomainTime(BOUNDARY - timedelta(hours=24)),
        window_end=decision_time,
        volatility=ExactDecimal.parse("0.0300", kind="ratio"),
        prior_decision=PriorDecisionEvidence(
            state=active.epoch.decision.state,
            decision_id=active.epoch.decision.decision_id,
            decision_time=DomainTime(BOUNDARY - timedelta(hours=7)),
        ),
        confirmations=tuple(
            replace(
                confirmation,
                state=AdaptationState.RANGE_HIGH_VOLATILITY,
                decision_time=DomainTime(BOUNDARY - timedelta(minutes=3 - index)),
            )
            for index, confirmation in enumerate(active.observation.confirmations, start=1)
        ),
    )
    payload = {
        "schema_version": "epoch-transition-facts/v1",
        "decision_time": decision_time,
        "active_epoch": active.epoch,
        "active_epoch_started_at": DomainTime(BOUNDARY - timedelta(hours=8)),
        "last_transition_completed_at": DomainTime(BOUNDARY - timedelta(hours=12)),
        "transitions_in_current_day": 0,
        "observation": observation,
        "derivation_causation_id": active.event.event_id,
        "venue_rules": replace(
            active.epoch.venue_rules,
            observed_at=decision_time,
            foreign_open_orders=0,
        ),
        "bootstrap_evidence": BootstrapEvidence.incomplete(),
        "admission_context": PlanAdmissionContext(
            schema_version="plan-admission-context/v1",
            still_effective_quote_commitment=exact("40"),
            still_effective_inventory_commitment=exact("0.00000000", "base_quantity"),
            still_effective_order_count=2,
        ),
        "safety": safety(),
        "inventory_basis": inventory_basis(),
        "old_orders": (
            OldEpochOrder(
                order_id="sha256:" + "4" * 64,
                epoch_id=active.epoch.epoch_id,
                side="BUY",
                state=ManagedOrderState.CANCELLED,
                exposure_increasing=True,
                inventory_reducing=False,
                terminal_proven=True,
                outcome_unknown=False,
            ),
            OldEpochOrder(
                order_id="sha256:" + "5" * 64,
                epoch_id=active.epoch.epoch_id,
                side="SELL",
                state=ManagedOrderState.FILLED,
                exposure_increasing=False,
                inventory_reducing=True,
                terminal_proven=True,
                outcome_unknown=False,
            ),
        ),
        "late_fill_postings": (
            LateFillPosting(
                fill_id="sha256:" + "6" * 64,
                order_id="sha256:" + "5" * 64,
                original_epoch_id=active.epoch.epoch_id,
                posting_epoch_id=active.epoch.epoch_id,
            ),
        ),
        "request_submitted": True,
        "cancellation_submitted": True,
        "reconciliation_complete": True,
        "activation_committed": False,
        "replacement_order_ids": ("sha256:" + "7" * 64, "sha256:" + "8" * 64),
        "operator_preempted": False,
        "restart_boundaries": (
            TransitionCrashBoundary.CANCELLING,
            TransitionCrashBoundary.RECONCILING,
        ),
        "transition_requested_at": DomainTime(BOUNDARY - timedelta(minutes=5)),
    }
    payload.update(changes)
    return EpochTransitionFacts(**payload)


def test_transition_progresses_through_guarded_bootstrap_without_old_new_overlap() -> None:
    evaluation = evaluate_epoch_transition(facts())

    assert evaluation.current_phase is TransitionPhase.BOOTSTRAPPING
    assert evaluation.refusal_reason is None
    assert evaluation.active_epoch_id == facts().active_epoch.epoch_id
    assert evaluation.proposed_epoch is not None
    assert evaluation.proposed_epoch.predecessor_epoch_id == evaluation.active_epoch_id
    assert evaluation.proposed_epoch_id == evaluation.proposed_epoch.epoch_id
    assert evaluation.permissions.placement_allowed is False
    assert evaluation.permissions.replacement_allowed is False
    assert evaluation.permissions.cancellation_allowed is True
    assert evaluation.permissions.reconciliation_allowed is True
    assert evaluation.permissions.inventory_reduction_allowed is True
    assert evaluation.replacement_activation is not None
    assert evaluation.replacement_activation.lifecycle.value == "BOOTSTRAPPING"
    assert (
        evaluation.replacement_activation.admission_context.still_effective_quote_commitment
        == exact("40")
    )
    assert all(
        posting.original_epoch_id == evaluation.active_epoch_id
        and posting.posting_epoch_id == evaluation.active_epoch_id
        for posting in evaluation.late_fill_postings
    )
    assert {
        step.phase: step.status for step in evaluation.progress
    }[TransitionPhase.OLD_EXPOSURE_BLOCKED] is TransitionStepStatus.COMPLETED
    assert {
        step.phase: step.status for step in evaluation.progress
    }[TransitionPhase.BOOTSTRAPPING] is TransitionStepStatus.CURRENT
    assert evaluation.crash_safe is False


@pytest.mark.parametrize(
    ("changes", "gate_name", "reason"),
    [
        (
            {"active_epoch_started_at": DomainTime(BOUNDARY - timedelta(hours=1))},
            "minimum_residence",
            "minimum_residence_unsatisfied",
        ),
        (
            {"last_transition_completed_at": DomainTime(BOUNDARY - timedelta(minutes=30))},
            "cooldown",
            "transition_cooldown_unsatisfied",
        ),
        (
            {"transitions_in_current_day": 3},
            "maximum_frequency",
            "transition_frequency_exceeded",
        ),
        (
            {"transition_requested_at": DomainTime(BOUNDARY - timedelta(minutes=11))},
            "expiry",
            "transition_expired",
        ),
    ],
)
def test_transition_records_exact_refusals_when_timing_gates_fail(
    changes: dict[str, object],
    gate_name: str,
    reason: str,
) -> None:
    evaluation = evaluate_epoch_transition(facts(**changes))

    assert evaluation.current_phase is TransitionPhase.ACTIVE
    assert evaluation.refusal_reason == reason
    assert next(gate for gate in evaluation.gates if gate.name == gate_name).reason == reason
    assert evaluation.proposed_epoch is None


@pytest.mark.parametrize(
    ("changes", "reason", "phase", "posture"),
    [
        (
            {
                "observation": replace(
                    facts().observation,
                    trend=ExactDecimal.parse("-0.0200", kind="ratio"),
                    volatility=ExactDecimal.parse("0.0100", kind="ratio"),
                    confirmations=tuple(
                        replace(
                            confirmation,
                            state=AdaptationState.TREND_DOWN,
                        )
                        for confirmation in facts().observation.confirmations
                    ),
                )
            },
            "downtrend_recovery_only",
            TransitionPhase.ACTIVE,
            "REDUCE_ONLY",
        ),
        (
            {
                "observation": replace(
                    facts().observation,
                    complete=False,
                    quality=EvidenceQuality.INCOMPLETE,
                )
            },
            "uncertain_transition_frozen",
            TransitionPhase.ACTIVE,
            "FROZEN",
        ),
    ],
)
def test_downtrend_and_uncertain_states_refuse_replacement_epochs(
    changes: dict[str, object],
    reason: str,
    phase: TransitionPhase,
    posture: str,
) -> None:
    evaluation = evaluate_epoch_transition(facts(**changes))

    assert evaluation.refusal_reason == reason
    assert evaluation.current_phase is phase
    assert evaluation.posture.value == posture
    assert evaluation.proposed_epoch is None


def test_unknown_cancel_outcomes_hold_transition_in_reconciling_fail_closed() -> None:
    evaluation = evaluate_epoch_transition(
        facts(
            old_orders=(
                OldEpochOrder(
                    order_id="sha256:" + "4" * 64,
                    epoch_id=facts().active_epoch.epoch_id,
                    side="BUY",
                    state=ManagedOrderState.UNKNOWN,
                    exposure_increasing=True,
                    inventory_reducing=False,
                    terminal_proven=False,
                    outcome_unknown=True,
                ),
            ),
            replacement_order_ids=(),
        )
    )

    assert evaluation.current_phase is TransitionPhase.RECONCILING
    assert evaluation.proposed_epoch is None
    assert evaluation.crash_safe is False
    assert evaluation.permissions.placement_allowed is False
    assert evaluation.permissions.replacement_allowed is False


def test_managed_identity_reuse_is_refused_before_replacement_activation() -> None:
    evaluation = evaluate_epoch_transition(
        facts(replacement_order_ids=("sha256:" + "4" * 64,))
    )

    assert evaluation.current_phase is TransitionPhase.ACTIVE
    assert evaluation.refusal_reason == "managed_identity_reuse_forbidden"
    assert evaluation.proposed_epoch is not None


@pytest.mark.parametrize(
    ("factory", "message"),
    [
        (
            lambda: TransitionGate("", TransitionGateOutcome.PASSED, "reason"),
            "canonical names and reasons",
        ),
        (
            lambda: TransitionProgressStep(
                TransitionPhase.ACTIVE, TransitionStepStatus.CURRENT, ""
            ),
            "require a reason",
        ),
        (
            lambda: OldEpochOrder(
                order_id="invalid",
                epoch_id="sha256:" + "1" * 64,
                side="BUY",
                state=ManagedOrderState.OPEN,
                exposure_increasing=True,
                inventory_reducing=False,
                terminal_proven=False,
                outcome_unknown=False,
            ),
            "deterministic identities",
        ),
        (
            lambda: OldEpochOrder(
                order_id="sha256:" + "1" * 64,
                epoch_id="sha256:" + "2" * 64,
                side="HOLD",
                state=ManagedOrderState.OPEN,
                exposure_increasing=True,
                inventory_reducing=False,
                terminal_proven=False,
                outcome_unknown=False,
            ),
            "must be BUY or SELL",
        ),
        (
            lambda: OldEpochOrder(
                order_id="sha256:" + "1" * 64,
                epoch_id="sha256:" + "2" * 64,
                side="BUY",
                state=ManagedOrderState.CANCELLED,
                exposure_increasing=True,
                inventory_reducing=False,
                terminal_proven=True,
                outcome_unknown=True,
            ),
            "cannot be terminal and outcome-unknown",
        ),
        (
            lambda: OldEpochOrder(
                order_id="sha256:" + "1" * 64,
                epoch_id="sha256:" + "2" * 64,
                side="BUY",
                state=ManagedOrderState.UNKNOWN,
                exposure_increasing=True,
                inventory_reducing=False,
                terminal_proven=False,
                outcome_unknown=False,
            ),
            "must remain outcome-unknown",
        ),
        (
            lambda: LateFillPosting(
                fill_id="invalid",
                order_id="sha256:" + "1" * 64,
                original_epoch_id="sha256:" + "2" * 64,
                posting_epoch_id="sha256:" + "2" * 64,
            ),
            "deterministic identities",
        ),
    ],
)
def test_transition_value_objects_reject_invalid_inputs(factory, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        factory()


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"schema_version": "epoch-transition-facts/v2"}, "unsupported epoch transition"),
        (
            {"active_epoch_started_at": DomainTime(BOUNDARY + timedelta(minutes=1))},
            "cannot start in the future",
        ),
        ({"transitions_in_current_day": -1}, "must be non-negative"),
        ({"derivation_causation_id": ""}, "causation identity"),
        ({"transition_requested_at": None}, "require a transition request time"),
        (
            {
                "request_submitted": False,
                "transition_requested_at": DomainTime(BOUNDARY - timedelta(minutes=5)),
            },
            "cannot advance before a request",
        ),
        (
            {
                "request_submitted": True,
                "cancellation_submitted": False,
                "reconciliation_complete": True,
            },
            "before cancellation is submitted",
        ),
        (
            {
                "old_orders": (
                    OldEpochOrder(
                        order_id="sha256:" + "1" * 64,
                        epoch_id="sha256:" + "9" * 64,
                        side="BUY",
                        state=ManagedOrderState.CANCELLED,
                        exposure_increasing=True,
                        inventory_reducing=False,
                        terminal_proven=True,
                        outcome_unknown=False,
                    ),
                )
            },
            "effective active-epoch orders",
        ),
        (
            {
                "late_fill_postings": (
                    LateFillPosting(
                        fill_id="sha256:" + "6" * 64,
                        order_id="sha256:" + "5" * 64,
                        original_epoch_id="sha256:" + "9" * 64,
                        posting_epoch_id="sha256:" + "9" * 64,
                    ),
                )
            },
            "preserve their originating epoch",
        ),
        (
            {
                "late_fill_postings": (
                    LateFillPosting(
                        fill_id="sha256:" + "6" * 64,
                        order_id="sha256:" + "5" * 64,
                        original_epoch_id=facts().active_epoch.epoch_id,
                        posting_epoch_id="sha256:" + "9" * 64,
                    ),
                )
            },
            "must post to their originating epoch",
        ),
    ],
)
def test_transition_facts_reject_invalid_sequences(changes: dict[str, object], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        facts(**changes)


def test_transition_evaluation_rejects_invalid_projection_shapes() -> None:
    evaluation = evaluate_epoch_transition(facts())
    with pytest.raises(ValueError, match="unsupported epoch transition evaluation schema"):
        replace(evaluation, schema_version="epoch-transition-evaluation/v2")
    with pytest.raises(ValueError, match="requires a proposed epoch"):
        replace(evaluation, proposed_epoch_id="sha256:" + "a" * 64, proposed_epoch=None)
    with pytest.raises(ValueError, match="must match the proposed epoch"):
        replace(
            evaluation,
            proposed_epoch_id="sha256:" + "b" * 64,
            proposed_epoch=evaluation.proposed_epoch,
        )


def test_operator_preemption_rebuilds_fail_closed_and_marks_crash_safe() -> None:
    evaluation = evaluate_epoch_transition(facts(operator_preempted=True))

    assert evaluation.refusal_reason == "operator_preempted"
    assert evaluation.current_phase is TransitionPhase.ACTIVE
    assert evaluation.crash_safe is True


@pytest.mark.parametrize(
    ("changes", "phase"),
    [
        ({"request_submitted": False, "cancellation_submitted": False, "reconciliation_complete": False, "transition_requested_at": None}, TransitionPhase.CHANGE_CONFIRMED),
        ({"cancellation_submitted": False, "reconciliation_complete": False}, TransitionPhase.OLD_EXPOSURE_BLOCKED),
        (
            {
                "old_orders": (
                    OldEpochOrder(
                        order_id="sha256:" + "1" * 64,
                        epoch_id=facts().active_epoch.epoch_id,
                        side="BUY",
                        state=ManagedOrderState.OPEN,
                        exposure_increasing=True,
                        inventory_reducing=False,
                        terminal_proven=False,
                        outcome_unknown=False,
                    ),
                ),
                "reconciliation_complete": False,
            },
            TransitionPhase.CANCELLING,
        ),
    ],
)
def test_transition_reports_intermediate_guard_states(
    changes: dict[str, object],
    phase: TransitionPhase,
) -> None:
    evaluation = evaluate_epoch_transition(facts(**changes))

    assert evaluation.current_phase is phase


def test_rejected_replacement_validation_and_ready_activation_are_exposed() -> None:
    rejected = evaluate_epoch_transition(
        facts(
            admission_context=PlanAdmissionContext(
                schema_version="plan-admission-context/v1",
                still_effective_quote_commitment=exact("40"),
                still_effective_inventory_commitment=exact("0.05000000", "base_quantity"),
                still_effective_order_count=2,
            )
        )
    )
    activating = evaluate_epoch_transition(
        facts(
            bootstrap_evidence=BootstrapEvidence(
                schema_version="bootstrap-evidence/v1",
                complete=True,
                net_base_confirmed=exact("0.40040040", "base_quantity"),
                evidence_id="sha256:" + "f" * 64,
            ),
            activation_committed=False,
        )
    )

    assert rejected.refusal_reason == "planned_inventory_exceeds_maximum_inventory"
    assert rejected.replacement_activation is not None
    assert rejected.replacement_activation.lifecycle.value == "REJECTED"
    assert activating.current_phase is TransitionPhase.ACTIVATING
    assert activating.proposed_epoch is not None


def test_direct_persistence_and_fake_runtime_harnesses_match(tmp_path) -> None:
    fixture = facts(
        bootstrap_evidence=BootstrapEvidence(
            schema_version="bootstrap-evidence/v1",
            complete=True,
            net_base_confirmed=exact("0.40040040", "base_quantity"),
            evidence_id="sha256:" + "9" * 64,
        ),
        activation_committed=True,
        restart_boundaries=(TransitionCrashBoundary.ACTIVATING, TransitionCrashBoundary.ACTIVE),
    )
    direct = evaluate_epoch_transition(fixture)
    runtime = FakeTransitionRuntime(fixture).evaluate()

    journal = SQLiteTransitionJournal(tmp_path / "transition.db")
    entry = journal.process(fixture)
    rebuilt = journal.rebuild_projection()

    assert runtime.to_payload() == direct.to_payload()
    assert entry.payload == direct.to_payload()
    assert rebuilt == direct.to_payload()
    assert direct.current_phase is TransitionPhase.ACTIVE
    assert direct.crash_safe is True


@pytest.mark.parametrize("boundary", list(TransitionCrashBoundary))
def test_transition_crash_injection_rebuilds_fail_closed(tmp_path, boundary: TransitionCrashBoundary) -> None:
    journal = SQLiteTransitionJournal(tmp_path / "transition.db")

    with pytest.raises(RuntimeError, match=boundary.value):
        journal.process(
            facts(
                bootstrap_evidence=BootstrapEvidence(
                    schema_version="bootstrap-evidence/v1",
                    complete=True,
                    net_base_confirmed=exact("0.40040040", "base_quantity"),
                    evidence_id="sha256:" + "a" * 64,
                ),
                activation_committed=True,
                restart_boundaries=(boundary,),
            ),
            crash_boundary=boundary,
        )

    assert journal.replay() == ()
    assert journal.rebuild_projection() is None
