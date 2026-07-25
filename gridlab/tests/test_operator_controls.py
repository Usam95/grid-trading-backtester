from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from gridlab.canonical.adaptation import AdaptationState
from gridlab.canonical.events import DomainTime
from gridlab.canonical.operator_controls import (
    GateOutcome,
    GoldenReplayCase,
    InventoryBasis,
    ManagedObligation,
    OperatorControlFacts,
    PreviewGate,
    PreviewAvailability,
    StopDisposition,
    TerminalDisposalWave,
    TerminalState,
    TerminalTrigger,
    TerminalWaveOutcome,
    evaluate_operator_controls,
)
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
        exposure_increasing_buy_principals=(exact("20"),),
        effective_managed_orders=10,
        foreign_open_orders=2,
        authenticated_order_limit=100,
        current_inventory=exact("1.0", "base_quantity"),
        pending_buy_inventory=exact("0.0", "base_quantity"),
        transition_bootstrap_inventory=exact("0.0", "base_quantity"),
        proposed_maximum_inventory=exact("1.0", "base_quantity"),
        maximum_planned_inventory=exact("1.5", "base_quantity"),
    )


def loss(*, equity: str = "249", global_stop_latched: bool = False) -> LossFacts:
    return LossFacts(
        schema_version="loss-facts/v1",
        initial_equity=exact("250"),
        risk_day_baseline=exact("250"),
        run_high_water_mark=exact("250"),
        conservative_liquidation_equity=exact(equity),
        prior_daily_loss_latched=False,
        prior_run_drawdown_latched=False,
        guardrail_recovery_approved=False,
        global_stop_latched=global_stop_latched,
    )


def all_freshness() -> tuple[FreshnessEvidence, ...]:
    return tuple(
        FreshnessEvidence(
            schema_version="freshness-evidence/v1",
            evidence_class=evidence_class,
            condition=EvidenceCondition.HEALTHY,
            observed_at=DomainTime(NOW.value - timedelta(seconds=1)),
            evidence_id="sha256:" + evidence_class.value[0].lower() * 64,
        )
        for evidence_class in EvidenceClass
    )


def clock() -> ClockEvidence:
    return ClockEvidence(
        schema_version="clock-evidence/v1",
        condition=EvidenceCondition.HEALTHY,
        request_sent_at=DomainTime(NOW.value - timedelta(milliseconds=200)),
        response_received_at=NOW,
        venue_time=DomainTime(NOW.value - timedelta(milliseconds=50)),
        scheduling_delay=exact("0.025000", "duration_seconds"),
        authenticated_timestamp_rejected=False,
        evidence_id="sha256:" + "c" * 64,
    )


def lifecycle(state: AdaptationState = AdaptationState.RANGE_NORMAL) -> LifecycleFacts:
    return LifecycleFacts(
        schema_version="lifecycle-facts/v1",
        grid_lifecycle="ACTIVE",
        adaptation_state=state,
        epoch_transition_state="ADAPTING",
        runtime_lifecycle="OPERATING",
        reconciliation_state="RECONCILED",
    )


def recovery() -> SafetyRecoveryFacts:
    return SafetyRecoveryFacts(
        schema_version="safety-recovery-facts/v1",
        prior_frozen_latched=False,
        frozen_recovery_approved=False,
    )


def safety(*, state: AdaptationState = AdaptationState.RANGE_NORMAL, equity: str = "249"):
    return evaluate_safety_posture(
        decision_time=NOW,
        capital=capital(),
        loss=loss(equity=equity),
        freshness=all_freshness(),
        clock=clock(),
        lifecycle=lifecycle(state),
        recovery=recovery(),
        range_condition=RangeCondition.IN_RANGE,
        recovery_obligations=(),
        venue=VenueConditionEvidence.trading(),
        prior_global_stop_latched=False,
    )


def inventory(*, authoritative: bool, quantity: str = "0.80000000") -> InventoryBasis:
    return InventoryBasis(
        basis_id="sha256:" + "9" * 64,
        source="canonical-reconciliation",
        base_asset="BTC",
        quantity=exact(quantity, "base_quantity"),
        authoritative=authoritative,
        reconciled_at=NOW if authoritative else None,
    )


def obligations() -> tuple[ManagedObligation, ...]:
    return (
        ManagedObligation(
            obligation_id="sha256:" + "a" * 64,
            side="BUY",
            exposure_increasing=True,
            inventory_reducing=False,
            fully_backed=False,
        ),
        ManagedObligation(
            obligation_id="sha256:" + "b" * 64,
            side="BUY",
            exposure_increasing=True,
            inventory_reducing=False,
            fully_backed=False,
        ),
        ManagedObligation(
            obligation_id="sha256:" + "c" * 64,
            side="SELL",
            exposure_increasing=False,
            inventory_reducing=True,
            fully_backed=True,
        ),
        ManagedObligation(
            obligation_id="sha256:" + "d" * 64,
            side="SELL",
            exposure_increasing=False,
            inventory_reducing=True,
            fully_backed=False,
        ),
    )


def waves() -> tuple[TerminalDisposalWave, ...]:
    return (
        TerminalDisposalWave(
            wave=1,
            quantity_limit=exact("0.50000000", "base_quantity"),
            notional_limit=exact("50.00"),
            max_depth_age=exact("3.000000", "duration_seconds"),
            price_band_bps=exact("35", "basis_points"),
            attempt_limit=2,
            elapsed_time_limit=exact("15.000000", "duration_seconds"),
            outcome=TerminalWaveOutcome.PARTIAL,
            reconciled_before_next_wave=True,
            authoritative_inventory_after_wave=exact("0.30000000", "base_quantity"),
        ),
        TerminalDisposalWave(
            wave=2,
            quantity_limit=exact("0.30000000", "base_quantity"),
            notional_limit=exact("30.00"),
            max_depth_age=exact("3.000000", "duration_seconds"),
            price_band_bps=exact("45", "basis_points"),
            attempt_limit=3,
            elapsed_time_limit=exact("20.000000", "duration_seconds"),
            outcome=TerminalWaveOutcome.COMPLETED,
            reconciled_before_next_wave=True,
            authoritative_inventory_after_wave=exact("0.00000000", "base_quantity"),
        ),
    )


def golden_cases() -> tuple[GoldenReplayCase, ...]:
    return tuple(
        GoldenReplayCase(
            case_name=case_name,
            outcome=outcome,
            replay_fingerprint="sha256:" + seed * 64,
        )
        for case_name, outcome, seed in (
            ("GAP_THROUGH", "IOC walks accepted price band and reconciles", "1"),
            ("PARTIAL_DISPOSAL", "partial fill reconciles before next wave", "2"),
            ("REJECTION", "venue rejection remains bounded and terminal", "3"),
            ("UNKNOWN_OUTCOME", "unknown child outcome freezes until reconciliation", "4"),
            ("ATTEMPT_EXHAUSTION", "attempt limit retains bounded residual", "5"),
            ("RESIDUAL_HOLDINGS", "dust remains retained with provenance", "6"),
        )
    )


def facts(**changes: object) -> OperatorControlFacts:
    payload = {
        "decision_time": NOW,
        "environment": "paper",
        "active_epoch_id": "sha256:" + "e" * 64,
        "proposed_epoch_id": "sha256:" + "f" * 64,
        "transition_state": "ACTIVATION_PENDING",
        "activation_pending": True,
        "paused": True,
        "safety": safety(),
        "managed_obligations": obligations(),
        "inventory_basis": inventory(authoritative=True),
        "resume_evidence_current": False,
        "resume_reconciliation_ok": False,
        "resume_invariants_ok": True,
        "resume_plan_valid": True,
        "resume_authority_ok": False,
        "operator_stop_disposition": StopDisposition.DISPOSE,
        "late_fill_ids": ("sha256:" + "7" * 64,),
        "emergency_stop_requested": False,
        "prior_operator_emergency_latched": False,
        "disposal_waves": waves(),
        "golden_replay_cases": golden_cases(),
    }
    payload.update(changes)
    return OperatorControlFacts(**payload)


def test_pause_resume_and_operator_stop_previews_follow_ticket_contract() -> None:
    result = evaluate_operator_controls(facts())

    assert result.pause.availability is PreviewAvailability.LATCHED
    assert result.pause.cancel_obligation_ids == (
        "sha256:" + "a" * 64,
        "sha256:" + "b" * 64,
        "sha256:" + "d" * 64,
    )
    assert result.pause.retained_obligation_ids == ("sha256:" + "c" * 64,)
    assert result.pause.preempts_pending_activation is True
    assert result.pause.blocks_new_epoch_placement is True
    assert result.pause.admission_order_preserved is True

    assert result.resume.availability is PreviewAvailability.BLOCKED
    assert {gate.name for gate in result.resume.gates if gate.outcome is GateOutcome.FAILED} == {
        "current_evidence",
        "reconciliation",
        "command_authority",
    }

    assert result.operator_stop.availability is PreviewAvailability.PREVIEW_REQUIRED
    assert result.operator_stop.late_fill_ids == ("sha256:" + "7" * 64,)
    assert result.operator_stop.available_dispositions == (
        StopDisposition.RETAIN_HOLDING,
        StopDisposition.DISPOSE,
    )
    assert result.operator_stop.selected_disposition is StopDisposition.DISPOSE


def test_emergency_and_terminal_loss_paths_latch_irreversibly() -> None:
    emergency = evaluate_operator_controls(
        facts(
            paused=False,
            safety=safety(state=AdaptationState.UNCERTAIN),
            inventory_basis=inventory(authoritative=False),
            emergency_stop_requested=True,
            disposal_waves=(),
        )
    )
    terminal_loss = evaluate_operator_controls(
        facts(
            paused=False,
            safety=safety(equity="219"),
            inventory_basis=inventory(authoritative=True),
        )
    )

    assert emergency.emergency_stop.availability is PreviewAvailability.LATCHED
    assert emergency.terminal.trigger is TerminalTrigger.OPERATOR_EMERGENCY
    assert emergency.terminal.global_stop_latched is True
    assert emergency.terminal.operator_emergency_latched is True
    assert emergency.terminal.state is TerminalState.AWAITING_AUTHORITATIVE_INVENTORY
    assert emergency.terminal.preempts_pending_activation is True

    assert terminal_loss.terminal.trigger is TerminalTrigger.TERMINAL_LOSS
    assert terminal_loss.terminal.global_stop_latched is True
    assert terminal_loss.terminal.automatic_liquidation is True
    assert terminal_loss.terminal.state is TerminalState.DISPOSED
    assert terminal_loss.terminal.operator_emergency_latched is False


def test_terminal_ioc_waves_and_golden_replay_bundle_are_deterministic() -> None:
    first = evaluate_operator_controls(facts())
    second = evaluate_operator_controls(facts())

    assert first == second
    assert first.fingerprint == second.fingerprint
    assert [wave.outcome for wave in first.terminal.waves] == [
        TerminalWaveOutcome.PARTIAL,
        TerminalWaveOutcome.COMPLETED,
    ]
    assert {case.case_name for case in first.terminal.golden_replay_cases} == {
        "GAP_THROUGH",
        "PARTIAL_DISPOSAL",
        "REJECTION",
        "UNKNOWN_OUTCOME",
        "ATTEMPT_EXHAUSTION",
        "RESIDUAL_HOLDINGS",
    }


def test_operator_control_contracts_reject_incomplete_replay_coverage_and_missing_reconciliation() -> (
    None
):
    with pytest.raises(ValueError, match="coverage is incomplete"):
        facts(golden_replay_cases=golden_cases()[:-1])

    broken_wave = replace(waves()[0], reconciled_before_next_wave=False)
    with pytest.raises(ValueError, match="reconcile between waves"):
        facts(disposal_waves=(broken_wave, waves()[1]))


def test_operator_control_contracts_reject_invalid_canonical_material() -> None:
    with pytest.raises(ValueError, match="managed obligation identity"):
        ManagedObligation(
            obligation_id="invalid",
            side="BUY",
            exposure_increasing=True,
            inventory_reducing=False,
            fully_backed=False,
        )
    with pytest.raises(ValueError, match="side must be BUY or SELL"):
        ManagedObligation(
            obligation_id="sha256:" + "a" * 64,
            side="HOLD",
            exposure_increasing=False,
            inventory_reducing=False,
            fully_backed=False,
        )

    with pytest.raises(ValueError, match="identity and source"):
        InventoryBasis(
            basis_id="invalid",
            source="",
            base_asset="BTC",
            quantity=exact("1.0", "base_quantity"),
            authoritative=False,
            reconciled_at=None,
        )
    with pytest.raises(ValueError, match="non-negative base quantity"):
        InventoryBasis(
            basis_id="sha256:" + "9" * 64,
            source="fixture",
            base_asset="BTC",
            quantity=exact("-1.0", "base_quantity"),
            authoritative=False,
            reconciled_at=None,
        )
    with pytest.raises(ValueError, match="requires reconciliation time"):
        InventoryBasis(
            basis_id="sha256:" + "9" * 64,
            source="fixture",
            base_asset="BTC",
            quantity=exact("1.0", "base_quantity"),
            authoritative=True,
            reconciled_at=None,
        )
    with pytest.raises(ValueError, match="cannot claim reconciliation"):
        InventoryBasis(
            basis_id="sha256:" + "9" * 64,
            source="fixture",
            base_asset="BTC",
            quantity=exact("1.0", "base_quantity"),
            authoritative=False,
            reconciled_at=NOW,
        )

    with pytest.raises(ValueError, match="preview gates require canonical names"):
        PreviewGate("", GateOutcome.PASSED, "")

    with pytest.raises(ValueError, match="positive wave and attempt bounds"):
        replace(waves()[0], wave=0)
    with pytest.raises(ValueError, match="positive quantity bound"):
        replace(waves()[0], quantity_limit=exact("0.0", "base_quantity"))
    with pytest.raises(ValueError, match="positive notional bound"):
        replace(waves()[0], notional_limit=exact("0.0"))
    with pytest.raises(ValueError, match="fresh-depth bound"):
        replace(waves()[0], max_depth_age=exact("6.000000", "duration_seconds"))
    with pytest.raises(ValueError, match="positive price-band bound"):
        replace(waves()[0], price_band_bps=exact("0", "basis_points"))
    with pytest.raises(ValueError, match="positive elapsed-time bound"):
        replace(waves()[0], elapsed_time_limit=exact("0.000000", "duration_seconds"))
    with pytest.raises(ValueError, match="non-negative authoritative inventory results"):
        replace(
            waves()[0],
            authoritative_inventory_after_wave=exact("-0.1", "base_quantity"),
        )

    with pytest.raises(ValueError, match="accepted bundle"):
        GoldenReplayCase("NOT_A_CASE", "invalid", "sha256:" + "1" * 64)
    with pytest.raises(ValueError, match="deterministic identity"):
        GoldenReplayCase("GAP_THROUGH", "", "invalid")

    with pytest.raises(ValueError, match="environment and transition state"):
        facts(environment="", transition_state="")
    with pytest.raises(ValueError, match="active epoch identity"):
        facts(active_epoch_id="invalid")
    with pytest.raises(ValueError, match="proposed epoch identity"):
        facts(proposed_epoch_id="invalid")
    with pytest.raises(ValueError, match="provided in deterministic order"):
        facts(disposal_waves=(waves()[1], waves()[0]))
    with pytest.raises(ValueError, match="contiguous attempt order"):
        facts(disposal_waves=(waves()[0], replace(waves()[1], wave=3)))


def test_terminal_state_branches_cover_retained_none_and_disposing_paths() -> None:
    retained = evaluate_operator_controls(
        facts(operator_stop_disposition=StopDisposition.RETAIN_HOLDING, disposal_waves=())
    )
    none_state = evaluate_operator_controls(
        facts(operator_stop_disposition=None, disposal_waves=())
    )
    disposing = evaluate_operator_controls(
        facts(
            paused=False,
            safety=safety(equity="219"),
            disposal_waves=(),
            inventory_basis=inventory(authoritative=True, quantity="0.10000000"),
        )
    )

    assert retained.terminal.state is TerminalState.RETAINED
    assert none_state.operator_stop.availability is PreviewAvailability.BLOCKED
    assert none_state.terminal.state is TerminalState.NONE
    assert disposing.terminal.state is TerminalState.DISPOSING


def test_operator_control_evaluation_contract_rejects_invalid_schema_and_fingerprint() -> None:
    result = evaluate_operator_controls(facts())

    with pytest.raises(ValueError, match="evaluation schema"):
        replace(result, schema_version="operator-control-evaluation/v2")
    with pytest.raises(ValueError, match="input fingerprint"):
        replace(result, input_fingerprint="invalid")
