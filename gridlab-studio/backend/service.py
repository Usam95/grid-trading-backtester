"""Service layer — the only place that talks to the gridlab engine.

It drives the engine directly (rather than only the thin facade) so it can emit
a richer, perfectly-aligned payload for the UI: down-sampled equity / price /
benchmark curves on a shared index, a drawdown series, the grid rung ladder for
the price overlay, trade markers mapped onto the down-sampled axis, and a set of
plain-English insights + an overall verdict. Everything returned is JSON-safe.
"""

from __future__ import annotations

import bisect
import math
from dataclasses import replace
from datetime import timedelta
from pathlib import Path
from typing import Any, Optional

import numpy as np
import pandas as pd

from gridlab.api.canonical_translation import characterize_legacy_backtest
from gridlab.api.facade import (
    BacktestSpec,
    _build_config,
    _build_strategy,
    _build_data,
    _enrich_indicators,
    _config_summary,
)
from gridlab.canonical._identity import content_identity
from gridlab.canonical.adaptation import (
    AdaptationState,
    EvidenceQuality,
    decide_adaptation,
)
from gridlab.canonical.configuration import Spacing
from gridlab.canonical.events import CanonicalEvent, DomainTime
from gridlab.canonical.initial_epoch import BootstrapEvidence, derive_initial_epoch
from gridlab.canonical.operator_controls import (
    GoldenReplayCase,
    InventoryBasis,
    ManagedObligation,
    OperatorControlFacts,
    StopDisposition,
    TerminalDisposalWave,
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
from gridlab.config.models import GridConfig
from gridlab.data.binance_archive import (
    AcquisitionLimits as AcquisitionLimits,
    ArchiveClient as ArchiveClient,
    ArchivePreview as ArchivePreview,
    ArchiveRequest as ArchiveRequest,
    ArchiveSource as ArchiveSource,
    DataAdmissionError as DataAdmissionError,
    OfficialBinanceArchiveClient as OfficialBinanceArchiveClient,
    acquire_binance_archive as acquire_binance_archive,
    preview_binance_archive as preview_binance_archive,
)
from gridlab.data.binance_catalog import (
    ArchiveCoverage as ArchiveCoverage,
    BinanceCatalogClient as BinanceCatalogClient,
    CatalogAdmissionError as CatalogAdmissionError,
    CatalogSource as CatalogSource,
    EurCatalogSymbol as EurCatalogSymbol,
    EurResearchCatalog as EurResearchCatalog,
    LiquidityEvidence as LiquidityEvidence,
    OfficialBinanceCatalogClient as OfficialBinanceCatalogClient,
    catalog_identity as catalog_identity,
    discover_eur_catalog as discover_eur_catalog,
)
from gridlab.engine.engine import BacktestEngine, EngineResult
from gridlab.indicators.indicators import atr as atr_ind, ema as ema_ind
from gridlab.research.grid_search import ParamSpace, grid_search
from gridlab.research.walk_forward import walk_forward
from gridlab.research.monte_carlo import monte_carlo
from gridlab.research.manifested import (
    run_manifested_backtest as _fingerprint_manifested_backtest,
)
from gridlab.research.robustness import robustness_report
from gridlab.results.benchmarks import buy_and_hold, dca_benchmark
from gridlab.results.metrics import compute_metrics
from gridlab.results.report import render_html_report

MAX_POINTS = 600
MAX_TRADES = 2000


def characterize_safety_posture() -> dict[str, Any]:
    """Present one deterministic Ticket 09 safety overlay without command dispatch."""
    decision_time = DomainTime(pd.Timestamp("2025-01-02T12:00:00Z").to_pydatetime())
    allocation_fingerprint = content_identity(
        "allocation-projection/v2",
        {"run_id": "run:ticket-09", "allocation_id": "allocation:ticket-09"},
    )
    epoch_id = content_identity(
        "grid-plan-epoch/v1",
        {"configuration_id": "fixture", "observation_id": "fixture"},
    )
    capital = CapitalCommitmentFacts(
        schema_version="capital-commitment-facts/v1",
        allocation_fingerprint=allocation_fingerprint,
        epoch_id=epoch_id,
        capital_envelope=ExactDecimal.parse("250.00", kind="quote_quantity"),
        committed_principal=ExactDecimal.parse("220.00", kind="quote_quantity"),
        fee_reserve=ExactDecimal.parse("8.00", kind="quote_quantity"),
        projected_obligation_fees=ExactDecimal.parse("2.00", kind="quote_quantity"),
        projected_terminal_fees=ExactDecimal.parse("1.00", kind="quote_quantity"),
        exposure_increasing_buy_principals=(
            ExactDecimal.parse("20.00", kind="quote_quantity"),
        ),
        effective_managed_orders=10,
        foreign_open_orders=2,
        authenticated_order_limit=100,
        current_inventory=ExactDecimal.parse("0.80", kind="base_quantity"),
        pending_buy_inventory=ExactDecimal.parse("0.20", kind="base_quantity"),
        transition_bootstrap_inventory=ExactDecimal.parse("0.00", kind="base_quantity"),
        proposed_maximum_inventory=ExactDecimal.parse("1.00", kind="base_quantity"),
        maximum_planned_inventory=ExactDecimal.parse("1.00", kind="base_quantity"),
    )
    loss = LossFacts(
        schema_version="loss-facts/v1",
        initial_equity=ExactDecimal.parse("250.00", kind="quote_quantity"),
        risk_day_baseline=ExactDecimal.parse("250.00", kind="quote_quantity"),
        run_high_water_mark=ExactDecimal.parse("250.00", kind="quote_quantity"),
        conservative_liquidation_equity=ExactDecimal.parse(
            "248.00", kind="quote_quantity"
        ),
        prior_daily_loss_latched=False,
        prior_run_drawdown_latched=False,
        guardrail_recovery_approved=False,
        global_stop_latched=False,
    )
    freshness = tuple(
        FreshnessEvidence(
            schema_version="freshness-evidence/v1",
            evidence_class=evidence_class,
            condition=EvidenceCondition.HEALTHY,
            observed_at=DomainTime(decision_time.value - timedelta(seconds=1)),
            evidence_id=content_identity(
                "freshness-evidence/v1",
                {"class": evidence_class, "decision_time": decision_time},
            ),
        )
        for evidence_class in EvidenceClass
    )
    clock = ClockEvidence(
        schema_version="clock-evidence/v1",
        condition=EvidenceCondition.HEALTHY,
        request_sent_at=DomainTime(decision_time.value - timedelta(milliseconds=200)),
        response_received_at=decision_time,
        venue_time=DomainTime(decision_time.value - timedelta(milliseconds=50)),
        scheduling_delay=ExactDecimal.parse("0.025000", kind="duration_seconds"),
        authenticated_timestamp_rejected=False,
        evidence_id=content_identity(
            "clock-evidence/v1", {"decision_time": decision_time}
        ),
    )
    lifecycle = LifecycleFacts(
        schema_version="lifecycle-facts/v1",
        grid_lifecycle="RANGE_EXHAUSTED",
        adaptation_state=AdaptationState.TREND_DOWN,
        epoch_transition_state="IDLE",
        runtime_lifecycle="OPERATING",
        reconciliation_state="RECONCILED",
    )
    recovery = SafetyRecoveryFacts(
        schema_version="safety-recovery-facts/v1",
        prior_frozen_latched=False,
        frozen_recovery_approved=False,
    )
    venue = VenueConditionEvidence(
        schema_version="venue-condition-evidence/v1",
        condition=SymbolCondition.DELISTING,
        observed_at=decision_time,
        evidence_id=content_identity(
            "venue-condition-evidence/v1",
            {"condition": SymbolCondition.DELISTING, "observed_at": decision_time},
        ),
        source="bounded-ticket-09-fixture",
        wind_down_deadline=DomainTime(decision_time.value + timedelta(days=7)),
    )
    evaluation = evaluate_safety_posture(
        decision_time=decision_time,
        capital=capital,
        loss=loss,
        freshness=freshness,
        clock=clock,
        lifecycle=lifecycle,
        recovery=recovery,
        range_condition=RangeCondition.BELOW_RANGE,
        recovery_obligations=(),
        venue=venue,
        prior_global_stop_latched=False,
    )
    return {
        "schema_version": "safety-posture-presentation/v1",
        "decision_time": decision_time.identity_payload(),
        "fingerprint": evaluation.fingerprint,
        "capital": {
            "allocation_fingerprint": capital.allocation_fingerprint,
            "epoch_id": capital.epoch_id,
            "capital_envelope": capital.capital_envelope.to_payload(),
            "committed_principal": capital.committed_principal.to_payload(),
            "fee_reserve": capital.fee_reserve.to_payload(),
            "maximum_planned_inventory": capital.maximum_planned_inventory.to_payload(),
        },
        "lifecycle": {
            "grid_lifecycle": lifecycle.grid_lifecycle,
            "adaptation_state": lifecycle.adaptation_state.value,
            "epoch_transition_state": lifecycle.epoch_transition_state,
            "runtime_lifecycle": lifecycle.runtime_lifecycle,
            "reconciliation_state": lifecycle.reconciliation_state,
        },
        "safety": {
            "posture": evaluation.posture.value,
            "reason_codes": list(evaluation.reason_codes),
            "loss_warning": evaluation.loss_warning,
            "daily_loss_latched": evaluation.daily_loss_latched,
            "run_drawdown_latched": evaluation.run_drawdown_latched,
            "global_stop_latched": evaluation.global_stop_latched,
            "allowed_command_classes": [
                item.value for item in evaluation.allowed_command_classes
            ],
            "placement_allowed": evaluation.placement_allowed,
            "replacement_allowed": evaluation.replacement_allowed,
            "downward_bound_shift_allowed": evaluation.downward_bound_shift_allowed,
            "fixed_quote_sizing_increase_allowed": (
                evaluation.fixed_quote_sizing_increase_allowed
            ),
            "clock_offset": evaluation.clock_offset.to_payload(),
            "scheduling_delay": evaluation.scheduling_delay.to_payload(),
            "round_trip_latency": evaluation.round_trip_latency.to_payload(),
        },
        "freshness": [
            {
                "evidence_class": item.evidence_class.value,
                "condition": item.condition.value,
                "observed_at": item.observed_at.identity_payload()
                if item.observed_at is not None
                else None,
                "evidence_id": item.evidence_id,
            }
            for item in evaluation.freshness
        ],
        "venue": {
            "condition": venue.condition.value,
            "evidence_id": venue.evidence_id,
            "source": venue.source,
            "wind_down_deadline": venue.wind_down_deadline.identity_payload()
            if venue.wind_down_deadline is not None
            else None,
        },
    }


def characterize_operator_controls() -> dict[str, Any]:
    """Present deterministic Ticket 10 operator previews and terminal disposal facts."""
    decision_time = DomainTime(pd.Timestamp("2025-01-02T12:05:00Z").to_pydatetime())
    safety = evaluate_safety_posture(
        decision_time=decision_time,
        capital=CapitalCommitmentFacts(
            schema_version="capital-commitment-facts/v1",
            allocation_fingerprint=content_identity(
                "allocation-projection/v2",
                {"run_id": "run:ticket-10", "allocation_id": "allocation:ticket-10"},
            ),
            epoch_id=content_identity(
                "grid-plan-epoch/v1",
                {"configuration_id": "ticket-10", "observation_id": "active"},
            ),
            capital_envelope=ExactDecimal.parse("250.00", kind="quote_quantity"),
            committed_principal=ExactDecimal.parse("210.00", kind="quote_quantity"),
            fee_reserve=ExactDecimal.parse("8.00", kind="quote_quantity"),
            projected_obligation_fees=ExactDecimal.parse("2.00", kind="quote_quantity"),
            projected_terminal_fees=ExactDecimal.parse("1.00", kind="quote_quantity"),
            exposure_increasing_buy_principals=(
                ExactDecimal.parse("20.00", kind="quote_quantity"),
            ),
            effective_managed_orders=6,
            foreign_open_orders=1,
            authenticated_order_limit=100,
            current_inventory=ExactDecimal.parse("0.80000000", kind="base_quantity"),
            pending_buy_inventory=ExactDecimal.parse(
                "0.00000000", kind="base_quantity"
            ),
            transition_bootstrap_inventory=ExactDecimal.parse(
                "0.00000000", kind="base_quantity"
            ),
            proposed_maximum_inventory=ExactDecimal.parse(
                "0.80000000", kind="base_quantity"
            ),
            maximum_planned_inventory=ExactDecimal.parse(
                "1.00000000", kind="base_quantity"
            ),
        ),
        loss=LossFacts(
            schema_version="loss-facts/v1",
            initial_equity=ExactDecimal.parse("250.00", kind="quote_quantity"),
            risk_day_baseline=ExactDecimal.parse("250.00", kind="quote_quantity"),
            run_high_water_mark=ExactDecimal.parse("250.00", kind="quote_quantity"),
            conservative_liquidation_equity=ExactDecimal.parse(
                "249.00", kind="quote_quantity"
            ),
            prior_daily_loss_latched=False,
            prior_run_drawdown_latched=False,
            guardrail_recovery_approved=False,
            global_stop_latched=False,
        ),
        freshness=tuple(
            FreshnessEvidence(
                schema_version="freshness-evidence/v1",
                evidence_class=evidence_class,
                condition=EvidenceCondition.HEALTHY,
                observed_at=DomainTime(decision_time.value - timedelta(seconds=2)),
                evidence_id=content_identity(
                    "freshness-evidence/v1",
                    {"class": evidence_class, "decision_time": decision_time},
                ),
            )
            for evidence_class in EvidenceClass
        ),
        clock=ClockEvidence(
            schema_version="clock-evidence/v1",
            condition=EvidenceCondition.HEALTHY,
            request_sent_at=DomainTime(
                decision_time.value - timedelta(milliseconds=200)
            ),
            response_received_at=decision_time,
            venue_time=DomainTime(decision_time.value - timedelta(milliseconds=50)),
            scheduling_delay=ExactDecimal.parse("0.025000", kind="duration_seconds"),
            authenticated_timestamp_rejected=False,
            evidence_id=content_identity(
                "clock-evidence/v1", {"decision_time": decision_time}
            ),
        ),
        lifecycle=LifecycleFacts(
            schema_version="lifecycle-facts/v1",
            grid_lifecycle="ACTIVE",
            adaptation_state=AdaptationState.RANGE_NORMAL,
            epoch_transition_state="ACTIVATION_PENDING",
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
        venue=VenueConditionEvidence.trading(),
        prior_global_stop_latched=False,
    )
    active_epoch_id = content_identity(
        "grid-plan-epoch/v1",
        {"configuration_id": "ticket-10", "observation_id": "active"},
    )
    proposed_epoch_id = content_identity(
        "grid-plan-epoch/v1",
        {"configuration_id": "ticket-10", "observation_id": "proposed"},
    )
    evaluation = evaluate_operator_controls(
        OperatorControlFacts(
            decision_time=decision_time,
            environment="paper",
            active_epoch_id=active_epoch_id,
            proposed_epoch_id=proposed_epoch_id,
            transition_state="ACTIVATION_PENDING",
            activation_pending=True,
            paused=True,
            safety=safety,
            managed_obligations=(
                ManagedObligation(
                    obligation_id=content_identity(
                        "managed-obligation/v1",
                        {"epoch_id": active_epoch_id, "rung": 1, "side": "BUY"},
                    ),
                    side="BUY",
                    exposure_increasing=True,
                    inventory_reducing=False,
                    fully_backed=False,
                ),
                ManagedObligation(
                    obligation_id=content_identity(
                        "managed-obligation/v1",
                        {"epoch_id": active_epoch_id, "rung": 2, "side": "BUY"},
                    ),
                    side="BUY",
                    exposure_increasing=True,
                    inventory_reducing=False,
                    fully_backed=False,
                ),
                ManagedObligation(
                    obligation_id=content_identity(
                        "managed-obligation/v1",
                        {"epoch_id": active_epoch_id, "rung": 3, "side": "SELL"},
                    ),
                    side="SELL",
                    exposure_increasing=False,
                    inventory_reducing=True,
                    fully_backed=True,
                ),
            ),
            inventory_basis=InventoryBasis(
                basis_id=content_identity(
                    "authoritative-inventory-basis/v1",
                    {"epoch_id": active_epoch_id, "decision_time": decision_time},
                ),
                source="reconciliation-ledger",
                base_asset="BTC",
                quantity=ExactDecimal.parse("0.80000000", kind="base_quantity"),
                authoritative=True,
                reconciled_at=decision_time,
            ),
            resume_evidence_current=False,
            resume_reconciliation_ok=False,
            resume_invariants_ok=True,
            resume_plan_valid=True,
            resume_authority_ok=False,
            operator_stop_disposition=StopDisposition.DISPOSE,
            late_fill_ids=(
                content_identity(
                    "late-fill/v1",
                    {"epoch_id": active_epoch_id, "fill": "late-1"},
                ),
            ),
            emergency_stop_requested=False,
            prior_operator_emergency_latched=False,
            disposal_waves=(
                TerminalDisposalWave(
                    wave=1,
                    quantity_limit=ExactDecimal.parse(
                        "0.50000000", kind="base_quantity"
                    ),
                    notional_limit=ExactDecimal.parse("50.00", kind="quote_quantity"),
                    max_depth_age=ExactDecimal.parse(
                        "3.000000", kind="duration_seconds"
                    ),
                    price_band_bps=ExactDecimal.parse("35", kind="basis_points"),
                    attempt_limit=2,
                    elapsed_time_limit=ExactDecimal.parse(
                        "15.000000", kind="duration_seconds"
                    ),
                    outcome=TerminalWaveOutcome.PARTIAL,
                    reconciled_before_next_wave=True,
                    authoritative_inventory_after_wave=ExactDecimal.parse(
                        "0.30000000", kind="base_quantity"
                    ),
                ),
                TerminalDisposalWave(
                    wave=2,
                    quantity_limit=ExactDecimal.parse(
                        "0.30000000", kind="base_quantity"
                    ),
                    notional_limit=ExactDecimal.parse("30.00", kind="quote_quantity"),
                    max_depth_age=ExactDecimal.parse(
                        "3.000000", kind="duration_seconds"
                    ),
                    price_band_bps=ExactDecimal.parse("45", kind="basis_points"),
                    attempt_limit=3,
                    elapsed_time_limit=ExactDecimal.parse(
                        "20.000000", kind="duration_seconds"
                    ),
                    outcome=TerminalWaveOutcome.COMPLETED,
                    reconciled_before_next_wave=True,
                    authoritative_inventory_after_wave=ExactDecimal.parse(
                        "0.00000000", kind="base_quantity"
                    ),
                ),
            ),
            golden_replay_cases=tuple(
                GoldenReplayCase(
                    case_name=case_name,
                    outcome=outcome,
                    replay_fingerprint=content_identity(
                        "terminal-disposal-replay/v1",
                        {"case_name": case_name},
                    ),
                )
                for case_name, outcome in (
                    ("GAP_THROUGH", "IOC walks accepted price band and reconciles"),
                    ("PARTIAL_DISPOSAL", "partial fill reconciles before next wave"),
                    ("REJECTION", "venue rejection remains bounded and terminal"),
                    (
                        "UNKNOWN_OUTCOME",
                        "unknown child outcome freezes until reconciliation",
                    ),
                    ("ATTEMPT_EXHAUSTION", "attempt limit retains bounded residual"),
                    ("RESIDUAL_HOLDINGS", "dust remains retained with provenance"),
                )
            ),
        )
    )
    inventory_basis = evaluation.pause.inventory_basis_id
    return {
        "schema_version": "operator-controls-presentation/v1",
        "decision_time": decision_time.identity_payload(),
        "fingerprint": evaluation.fingerprint,
        "projection": {
            "active_epoch_id": active_epoch_id,
            "proposed_epoch_id": proposed_epoch_id,
            "transition_state": "ACTIVATION_PENDING",
            "posture": evaluation.pause.posture,
        },
        "inventory_basis": {
            "basis_id": inventory_basis,
            "source": "reconciliation-ledger",
            "base_asset": "BTC",
            "quantity": {"kind": "base_quantity", "value": "0.80000000"},
            "authoritative": True,
            "reconciled_at": decision_time.identity_payload(),
        },
        "pause": _operator_preview_payload(evaluation.pause),
        "resume": _operator_preview_payload(evaluation.resume),
        "operator_stop": _operator_preview_payload(evaluation.operator_stop),
        "emergency_stop": _operator_preview_payload(evaluation.emergency_stop),
        "terminal": {
            "trigger": evaluation.terminal.trigger.value,
            "state": evaluation.terminal.state.value,
            "global_stop_latched": evaluation.terminal.global_stop_latched,
            "operator_emergency_latched": evaluation.terminal.operator_emergency_latched,
            "automatic_liquidation": evaluation.terminal.automatic_liquidation,
            "preempts_pending_activation": evaluation.terminal.preempts_pending_activation,
            "admission_order_preserved": evaluation.terminal.admission_order_preserved,
            "active_epoch_id": evaluation.terminal.active_epoch_id,
            "proposed_epoch_id": evaluation.terminal.proposed_epoch_id,
            "transition_state": evaluation.terminal.transition_state,
            "posture": evaluation.terminal.posture,
            "inventory_basis_id": evaluation.terminal.inventory_basis_id,
            "waves": [
                {
                    "wave": wave.wave,
                    "order_type": "IOC",
                    "quantity_limit": wave.quantity_limit.to_payload(),
                    "notional_limit": wave.notional_limit.to_payload(),
                    "max_depth_age": wave.max_depth_age.to_payload(),
                    "price_band_bps": wave.price_band_bps.to_payload(),
                    "attempt_limit": wave.attempt_limit,
                    "elapsed_time_limit": wave.elapsed_time_limit.to_payload(),
                    "outcome": wave.outcome.value,
                    "reconciled_before_next_wave": wave.reconciled_before_next_wave,
                    "authoritative_inventory_after_wave": (
                        wave.authoritative_inventory_after_wave.to_payload()
                    ),
                }
                for wave in evaluation.terminal.waves
            ],
            "golden_replay_cases": [
                {
                    "case_name": case.case_name,
                    "outcome": case.outcome,
                    "replay_fingerprint": case.replay_fingerprint,
                }
                for case in evaluation.terminal.golden_replay_cases
            ],
        },
    }


def _operator_preview_payload(preview: Any) -> dict[str, Any]:
    return {
        "action": preview.action,
        "availability": preview.availability.value,
        "confirmation_required": preview.confirmation_required,
        "environment_bound": preview.environment_bound,
        "idempotent": preview.idempotent,
        "preempts_pending_activation": preview.preempts_pending_activation,
        "blocks_new_epoch_placement": preview.blocks_new_epoch_placement,
        "admission_order_preserved": preview.admission_order_preserved,
        "active_epoch_id": preview.active_epoch_id,
        "proposed_epoch_id": preview.proposed_epoch_id,
        "transition_state": preview.transition_state,
        "posture": preview.posture,
        "inventory_basis_id": preview.inventory_basis_id,
        "cancel_obligation_ids": list(preview.cancel_obligation_ids),
        "retained_obligation_ids": list(preview.retained_obligation_ids),
        "late_fill_ids": list(preview.late_fill_ids),
        "gates": [
            {"name": gate.name, "outcome": gate.outcome.value, "reason": gate.reason}
            for gate in preview.gates
        ],
        "reason_codes": list(preview.reason_codes),
        "available_dispositions": [
            disposition.value for disposition in preview.available_dispositions
        ],
        "selected_disposition": (
            preview.selected_disposition.value
            if preview.selected_disposition is not None
            else None
        ),
    }


def characterize_canonical_adaptive(request: dict[str, Any]) -> dict[str, Any]:
    """Derive one bounded adaptive initial epoch beside the legacy diagnostic."""
    result = characterize_legacy_backtest(
        symbol=request["symbol"],
        decision_time=DomainTime(request["decision_time"]),
        trend=request["trend"],
        volatility=request["volatility"],
        reference_price=request["reference_price"],
        complete=request["complete"],
        quality=EvidenceQuality(request["evidence_quality"]),
    )
    configuration = replace(
        result.configuration,
        spacing=Spacing(request["spacing"]),
    )
    event_time = DomainTime(request.get("event_time") or request["decision_time"])
    confirmations = tuple(
        replace(
            confirmation,
            decision_time=DomainTime(
                event_time.value
                - configuration.adaptation_policy.maximum_observation_age
                + configuration.adaptation_policy.maximum_observation_age
                * index
                / (len(result.observation.confirmations) + 1)
            ),
        )
        for index, confirmation in enumerate(
            result.observation.confirmations,
            start=1,
        )
    )
    observation = replace(
        result.observation,
        event_time=event_time,
        window_start=DomainTime(
            event_time.value - configuration.adaptation_policy.observation_window
        ),
        window_end=event_time,
        observed_count=request["observed_count"],
        sequence_end=request["sequence_end"],
        confirmations=confirmations,
    )
    decision_time = DomainTime(request["decision_time"])
    decision = decide_adaptation(
        configuration.adaptation_policy,
        observation,
        decision_time,
    )
    bootstrap_evidence = BootstrapEvidence(
        schema_version="bootstrap-evidence/v1",
        complete=request["bootstrap_complete"],
        net_base_confirmed=ExactDecimal.parse(
            request["bootstrap_confirmed_base"],
            kind="base_quantity",
        ),
        evidence_id=request.get("bootstrap_evidence_id"),
    )
    venue_rules = replace(
        result.epoch.venue_rules,
        observed_at=decision_time,
        environment=request["venue_environment"],
        tick_size=ExactDecimal.parse(request["tick_size"], kind="price_increment"),
        step_size=ExactDecimal.parse(request["step_size"], kind="quantity_increment"),
        minimum_price=ExactDecimal.parse(request["minimum_price"], kind="price"),
        maximum_price=(
            ExactDecimal.parse(request["maximum_price"], kind="price")
            if request.get("maximum_price") is not None
            else None
        ),
        minimum_quantity=ExactDecimal.parse(
            request["minimum_quantity"], kind="base_quantity"
        ),
        maximum_quantity=(
            ExactDecimal.parse(request["maximum_quantity"], kind="base_quantity")
            if request.get("maximum_quantity") is not None
            else None
        ),
        minimum_notional=ExactDecimal.parse(
            request["minimum_notional"], kind="quote_quantity"
        ),
        maximum_notional=(
            ExactDecimal.parse(request["maximum_notional"], kind="quote_quantity")
            if request.get("maximum_notional") is not None
            else None
        ),
        max_open_orders=request.get("max_open_orders"),
        foreign_open_orders=request["foreign_open_orders"],
        symbol_status=request["symbol_status"],
        spot_trading_allowed=request["spot_trading_allowed"],
        limit_maker_supported=request["limit_maker_supported"],
        contradictory=request["contradictory_rules"],
    )
    event = CanonicalEvent.create(
        schema=observation.schema_version,
        source=observation.source,
        source_event_key=observation.observation_id,
        source_sequence=observation.sequence_end,
        event_time=observation.event_time,
        received_time=decision_time,
        correlation_id=f"initial-epoch-characterization:{configuration.symbol}",
        causation_id=None,
        payload={"observation_id": observation.observation_id},
    )
    activation = derive_initial_epoch(
        configuration=configuration,
        observation=observation,
        decision_time=decision_time,
        activation_price=ExactDecimal.parse(
            request["activation_price"],
            kind="price",
        ),
        derivation_causation_id=event.event_id,
        venue_rules=venue_rules,
        bootstrap_evidence=bootstrap_evidence,
    )
    epoch = activation.epoch
    plan = epoch.plan if epoch is not None else None
    return {
        "configuration": {
            "schema_version": configuration.schema_version,
            "configuration_id": configuration.configuration_id,
            "policy_id": configuration.adaptation_policy.policy_id,
            "symbol": configuration.symbol,
            "base_asset": configuration.base_asset,
            "quote_asset": configuration.quote_asset,
            "rung_count": configuration.rung_count,
            "spacing": configuration.spacing.value,
            "execution_policy_id": configuration.execution_policy_id,
            "risk_profile_id": configuration.risk_profile_id,
            "operator_inputs": {
                "fixed_quote_principal": configuration.fixed_quote_principal.to_payload(),
                "maker_fee": configuration.maker_fee.to_payload(),
                "taker_fee": configuration.taker_fee.to_payload(),
                "maximum_quote_capital": configuration.maximum_quote_capital.to_payload(),
                "fee_reserve": configuration.fee_reserve.to_payload(),
                "stop_price": configuration.stop_price.to_payload(),
                "lower_bound_limit": configuration.lower_bound_limit.to_payload(),
                "upper_bound_limit": configuration.upper_bound_limit.to_payload(),
            },
        },
        "observation": {
            "schema_version": observation.schema_version,
            "observation_id": observation.observation_id,
            "event_id": event.event_id,
            "source_system": observation.source.system,
            "source_stream": observation.source.stream,
            "event_time": observation.event_time.value,
            "decision_time": decision.decision_time.value,
            "complete": observation.complete,
            "quality": observation.quality.value,
            "confirmation_ids": [
                confirmation.confirmation_id
                for confirmation in observation.confirmations
            ],
            "prior_decision_id": (
                observation.prior_decision.decision_id
                if observation.prior_decision
                else None
            ),
            "trend": observation.trend.to_payload(),
            "volatility": observation.volatility.to_payload(),
            "reference_price": observation.reference_price.to_payload(),
        },
        "decision": {
            "decision_id": decision.decision_id,
            "adaptation_state": decision.state.value,
            "intent": decision.intent.value,
            "reason": decision.reason,
            "permits_exposure_increasing_buy": (
                decision.permits_exposure_increasing_buy
            ),
            "requested_bound_shift": (
                decision.requested_bound_shift.to_payload()
                if decision.requested_bound_shift
                else None
            ),
        },
        "activation": {
            "schema_version": activation.schema_version,
            "lifecycle": activation.lifecycle.value,
            "replay_fingerprint": activation.replay_fingerprint,
            "ladder_placement_allowed": activation.ladder_placement_allowed,
            "activation_pending": activation.activation_pending,
            "automatically_armed": activation.automatically_armed,
            "derived_width": (
                activation.derived_width.to_payload()
                if activation.derived_width is not None
                else None
            ),
            "gates": [
                {
                    "name": gate.name,
                    "outcome": gate.outcome.value,
                    "reason": gate.reason,
                }
                for gate in activation.gates
            ],
            "bootstrap_evidence": {
                "complete": activation.bootstrap_evidence.complete,
                "net_base_confirmed": (
                    activation.bootstrap_evidence.net_base_confirmed.to_payload()
                ),
                "evidence_id": activation.bootstrap_evidence.evidence_id,
            },
            "admission_context": {
                "still_effective_quote_commitment": (
                    activation.admission_context.still_effective_quote_commitment.to_payload()
                ),
                "still_effective_inventory_commitment": (
                    activation.admission_context.still_effective_inventory_commitment.to_payload()
                ),
                "still_effective_order_count": (
                    activation.admission_context.still_effective_order_count
                ),
            },
            "admission_assessment": (
                {
                    "capital_envelope": (
                        activation.admission_assessment.capital_envelope.to_payload()
                    ),
                    "still_effective_quote_commitment": (
                        activation.admission_assessment.still_effective_quote_commitment.to_payload()
                    ),
                    "proposed_quote_commitment": (
                        activation.admission_assessment.proposed_quote_commitment.to_payload()
                    ),
                    "bootstrap_quote_commitment": (
                        activation.admission_assessment.bootstrap_quote_commitment.to_payload()
                    ),
                    "total_quote_commitment": (
                        activation.admission_assessment.total_quote_commitment.to_payload()
                    ),
                    "fee_reserve": activation.admission_assessment.fee_reserve.to_payload(),
                    "still_effective_inventory_commitment": (
                        activation.admission_assessment.still_effective_inventory_commitment.to_payload()
                    ),
                    "additional_bootstrap_inventory": (
                        activation.admission_assessment.additional_bootstrap_inventory.to_payload()
                    ),
                    "maximum_planned_inventory": (
                        activation.admission_assessment.maximum_planned_inventory.to_payload()
                    ),
                    "total_worst_case_inventory": (
                        activation.admission_assessment.total_worst_case_inventory.to_payload()
                    ),
                    "still_effective_order_count": (
                        activation.admission_assessment.still_effective_order_count
                    ),
                    "proposed_order_count": activation.admission_assessment.proposed_order_count,
                    "total_order_count": activation.admission_assessment.total_order_count,
                    "venue_order_capacity": (
                        activation.admission_assessment.venue_order_capacity
                    ),
                    "foreign_open_orders": activation.admission_assessment.foreign_open_orders,
                }
                if activation.admission_assessment is not None
                else None
            ),
            "adjacent_cycle_economics": [
                {
                    "buy_rung_index": cycle.buy_rung_index,
                    "sell_rung_index": cycle.sell_rung_index,
                    "buy_price": cycle.buy_price.to_payload(),
                    "sell_price": cycle.sell_price.to_payload(),
                    "cycle_quantity": cycle.cycle_quantity.to_payload(),
                    "net_margin": cycle.net_margin.to_payload(),
                    "positive": cycle.positive,
                    "reason": cycle.reason,
                }
                for cycle in activation.adjacent_cycle_economics
            ],
            "principal_feasibility": {
                "schema_version": activation.principal_feasibility.schema_version,
                "points": [
                    {
                        "principal": point.principal.to_payload(),
                        "feasible": point.feasible,
                        "reasons": list(point.reasons),
                    }
                    for point in activation.principal_feasibility.points
                ],
            },
            "post_only_retry_policy": {
                "schema_version": activation.post_only_retry_policy.schema_version,
                "order_type": activation.post_only_retry_policy.order_type,
                "max_attempts": activation.post_only_retry_policy.max_attempts,
                "retry_delays": [
                    delay.to_payload()
                    for delay in activation.post_only_retry_policy.retry_delays
                ],
                "max_price_displacement_ratio": (
                    activation.post_only_retry_policy.max_price_displacement_ratio.to_payload()
                ),
                "max_adjacent_gap_fraction": (
                    activation.post_only_retry_policy.max_adjacent_gap_fraction.to_payload()
                ),
                "exhaustion_posture": activation.post_only_retry_policy.exhaustion_posture,
            },
            "rule_fee_contract": {
                "schema_version": activation.rule_fee_contract.schema_version,
                "contract_id": activation.rule_fee_contract.contract_id,
                "venue_rule_evidence_id": activation.rule_fee_contract.venue_rule_evidence_id,
                "maker_fee": activation.rule_fee_contract.maker_fee.to_payload(),
                "taker_fee": activation.rule_fee_contract.taker_fee.to_payload(),
            },
        },
        "derived_plan": (
            {
                "schema_version": plan.schema_version,
                "epoch_id": epoch.epoch_id,
                "predecessor_epoch_id": epoch.predecessor_epoch_id,
                "derivation_causation_id": epoch.derivation_causation_id,
                "derivation_semantics": plan.derivation_semantics,
                "venue_rule_evidence_id": epoch.venue_rules.evidence_id,
                "lower": plan.lower.to_payload(),
                "upper": plan.upper.to_payload(),
                "reference_price": plan.reference_price.to_payload(),
                "activation_price": (
                    plan.activation_price.to_payload()
                    if plan.activation_price is not None
                    else plan.reference_price.to_payload()
                ),
                "unquantized_rungs": [
                    value.to_payload() for value in plan.unquantized_rungs
                ],
                "quantized_rungs": [
                    {
                        "index": rung.index,
                        "price": rung.price.to_payload(),
                        "role": rung.role,
                    }
                    for rung in plan.rungs
                ],
                "obligations": [
                    {
                        "rung_index": obligation.rung_index,
                        "role": obligation.role,
                        "fixed_quote_principal": (
                            obligation.fixed_quote_principal.to_payload()
                        ),
                        "base_quantity": (
                            obligation.base_quantity.to_payload()
                            if obligation.base_quantity is not None
                            else None
                        ),
                    }
                    for obligation in plan.obligations
                ],
                "allocation_assumptions": {
                    "quote_allocation": (
                        plan.allocation_assumptions.quote_allocation.to_payload()
                    ),
                    "base_allocation": (
                        plan.allocation_assumptions.base_allocation.to_payload()
                    ),
                    "fee_reserve": plan.allocation_assumptions.fee_reserve.to_payload(),
                },
                "maximum_planned_inventory": (
                    activation.maximum_planned_inventory.to_payload()
                    if activation.maximum_planned_inventory is not None
                    else None
                ),
                "bootstrap_obligation": (
                    {
                        "net_base_required": (
                            activation.bootstrap_obligation.net_base_required.to_payload()
                        ),
                        "gross_base_required": (
                            activation.bootstrap_obligation.gross_base_required.to_payload()
                        ),
                        "fee_base_coverage": (
                            activation.bootstrap_obligation.fee_base_coverage.to_payload()
                        ),
                    }
                    if activation.bootstrap_obligation is not None
                    else None
                ),
            }
            if plan is not None and epoch is not None
            else None
        ),
        "legacy_comparison": {
            "bounded_bars": result.legacy_result["bars"],
            "legacy_adaptive": result.legacy_spec["grid"]["adaptive"],
            "legacy_spacing": result.legacy_spec["grid"]["spacing"],
            "effective_atr_multiplier": result.legacy_effective_atr_multiplier,
            "cancelled_orders": result.legacy_cancelled_orders,
            "semantic_differences": list(result.differences),
        },
    }


def fingerprint_manifested_backtest(spec: dict, manifest_path: Path) -> dict:
    """Fingerprint verified production history behind the Studio boundary."""
    return _fingerprint_manifested_backtest(spec, manifest_path)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _f(x: Any) -> Optional[float]:
    """Coerce to a JSON-safe float (NaN/inf -> None)."""
    if x is None:
        return None
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def _json_safe(obj: Any) -> Any:
    """Recursively replace NaN/inf floats with None so the payload is strict-JSON."""
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(v) for v in obj]
    if isinstance(obj, float):
        return obj if math.isfinite(obj) else None
    return obj


def _ds_indices(n: int, max_points: int = MAX_POINTS) -> np.ndarray:
    if n <= max_points:
        return np.arange(n)
    return np.unique(np.linspace(0, n - 1, max_points).astype(int))


def _pick(arr, idx) -> list[Optional[float]]:
    a = np.asarray(arr, dtype=float)
    return [(_f(v) if math.isfinite(v) else None) for v in a[idx]]


def _drawdown_series(equity: np.ndarray) -> list[float]:
    if equity.size == 0:
        return []
    peak = np.maximum.accumulate(equity)
    dd = np.where(peak > 0, (equity - peak) / peak, 0.0)
    return [float(v) for v in dd]


# ---------------------------------------------------------------------------
# Grid geometry (preview + price-chart overlay)
# ---------------------------------------------------------------------------


def compute_grid_levels(spec_dict: dict) -> dict:
    """Resolve the rung ladder for a spec — works for static and adaptive grids."""
    grid = dict(spec_dict.get("grid") or {})
    levels_n = int(grid.get("levels", 10) or 10)
    spacing = grid.get("spacing", "arithmetic")
    direction = grid.get("direction", "neutral")
    adaptive = bool(grid.get("adaptive", False))
    lower = grid.get("lower")
    upper = grid.get("upper")
    lookback = int(grid.get("lookback", 100) or 100)
    atr_period = int(grid.get("atr_period", 14) or 14)
    atr_mult = float(grid.get("atr_mult", 2.0) or 2.0)

    source = "static"
    need_derive = adaptive or lower is None or upper is None

    if need_derive:
        spec = BacktestSpec.from_dict(spec_dict)
        candles = list(_build_data(spec).candles())
        closes = np.array([c.close for c in candles], dtype=float)
        highs = np.array([c.high for c in candles], dtype=float)
        lows = np.array([c.low for c in candles], dtype=float)
        if closes.size == 0:
            return {"error": "no data to derive grid bounds"}
        win = closes[-lookback:] if closes.size > lookback else closes
        if adaptive and spacing == "atr":
            center = float(ema_ind(pd.Series(closes), max(2, lookback)).iloc[-1])
            atr_val = float(
                atr_ind(
                    pd.Series(highs), pd.Series(lows), pd.Series(closes), atr_period
                ).iloc[-1]
            )
            lower = center - atr_mult * atr_val
            upper = center + atr_mult * atr_val
            source = "adaptive_atr"
        elif adaptive:
            lower = float(np.min(win))
            upper = float(np.max(win))
            source = "adaptive_rolling"
        else:
            lower = float(np.min(win))
            upper = float(np.max(win))
            source = "derived"

    if lower is None or upper is None:
        return {"error": "grid bounds could not be resolved"}
    lower = float(lower)
    upper = float(upper)
    if lower >= upper or lower <= 0:
        return {"error": "invalid grid bounds (lower must be > 0 and < upper)"}

    if spacing == "geometric":
        rungs = np.geomspace(lower, upper, levels_n)
    else:  # arithmetic / atr (atr approximated linearly for preview)
        rungs = np.linspace(lower, upper, levels_n)

    return {
        "lower": lower,
        "upper": upper,
        "center": (lower + upper) / 2.0,
        "spacing": spacing,
        "direction": direction,
        "adaptive": adaptive,
        "source": source,
        "levels": [float(x) for x in rungs],
        "spacing_pct": float((upper - lower) / lower / max(1, levels_n - 1)),
    }


# ---------------------------------------------------------------------------
# Backtest
# ---------------------------------------------------------------------------


def _serialize_trades(trades, full_ts: list, ds_idx: np.ndarray) -> list[dict]:
    """Map each closed trade onto the down-sampled axis for chart markers."""
    out: list[dict] = []
    ds_list = ds_idx.tolist()
    n_full = len(full_ts)
    for t in trades[:MAX_TRADES]:
        # bar index of the exit, via timestamp bisect on the full axis
        exit_bar = bisect.bisect_left(full_ts, t.closed_at) if full_ts else 0
        exit_bar = min(max(exit_bar, 0), n_full - 1) if n_full else 0
        entry_bar = bisect.bisect_left(full_ts, t.opened_at) if full_ts else 0
        entry_bar = min(max(entry_bar, 0), n_full - 1) if n_full else 0
        out.append(
            {
                "side": t.side.value,
                "qty": _f(t.qty),
                "entry_price": _f(t.entry_price),
                "exit_price": _f(t.exit_price),
                "pnl": _f(t.pnl),
                "return_pct": _f(t.return_pct),
                "bars_held": int(t.bars_held),
                "opened_at": t.opened_at.isoformat(),
                "closed_at": t.closed_at.isoformat(),
                "exit_reason": t.exit_reason,
                "entry_x": bisect.bisect_left(ds_list, entry_bar),
                "exit_x": bisect.bisect_left(ds_list, exit_bar),
            }
        )
    return out


def run_backtest(
    spec_dict: dict, *, with_report: bool = False, include_trades: bool = True
) -> dict:
    spec = BacktestSpec.from_dict(spec_dict)
    data = _build_data(spec)
    return _run_backtest_with_data(
        spec_dict, spec, data, with_report=with_report, include_trades=include_trades
    )


def run_manifested_backtest(
    spec_dict: dict, manifest_path: Path, *, include_trades: bool = True
) -> dict:
    """Render the rich Studio result from verified offline Parquet candles."""
    import json

    from gridlab.data.binance_archive import load_manifested_candles
    from gridlab.data.source import InMemoryDataSource

    spec = BacktestSpec.from_dict(spec_dict)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if spec.symbol != manifest["symbol"]:
        raise ValueError(
            f"backtest symbol {spec.symbol} does not match dataset {manifest['symbol']}"
        )
    data = InMemoryDataSource(
        symbol=spec.symbol, _candles=load_manifested_candles(manifest_path)
    )
    return _run_backtest_with_data(
        spec_dict, spec, data, with_report=False, include_trades=include_trades
    )


def _run_backtest_with_data(
    spec_dict: dict,
    spec: BacktestSpec,
    data,
    *,
    with_report: bool,
    include_trades: bool,
) -> dict:
    config = _build_config(spec)
    gc = GridConfig(**spec.grid)
    if gc.adaptive or (spec.filter or {}).get("kind") in ("trend", "regime", "rsi"):
        data = _enrich_indicators(data, gc)

    strategy = _build_strategy(spec)
    engine = BacktestEngine(config)
    result: EngineResult = engine.run(data, strategy)

    metrics = compute_metrics(result, n_trials=spec.n_trials)
    bh = buy_and_hold(result.close, config.initial_cash, config.fees.taker)
    dca = dca_benchmark(result.close, config.initial_cash, fee=config.fees.taker)

    n = len(result.equity)
    idx = _ds_indices(n)
    equity = np.asarray(result.equity, dtype=float)
    dd_full = np.asarray(_drawdown_series(equity), dtype=float)
    full_ts = result.timestamps

    payload = {
        "symbol": result.symbol,
        "bars": result.bars,
        "start": full_ts[0].isoformat() if full_ts else None,
        "end": full_ts[-1].isoformat() if full_ts else None,
        "initial_cash": _f(result.initial_cash),
        "final_equity": _f(result.final_equity),
        "fees_paid": _f(result.fees_paid),
        "realized_pnl": _f(result.realized_pnl),
        "liquidated": bool(result.liquidated),
        "rejections": dict(result.rejections),
        "metrics": {k: _f(v) for k, v in metrics.items()},
        "benchmarks": {
            "buy_and_hold": {
                "total_return": _f(bh["total_return"]),
                "final_equity": _f(bh["final_equity"]),
                "max_drawdown": _f(bh["max_drawdown"]),
            },
            "dca": {
                "total_return": _f(dca["total_return"]),
                "final_equity": _f(dca["final_equity"]),
                "max_drawdown": _f(dca["max_drawdown"]),
            },
        },
        "series": {
            "x": [int(i) for i in idx],
            "timestamps": [full_ts[i].isoformat() for i in idx] if full_ts else [],
            "equity": _pick(result.equity, idx),
            "price": _pick(result.close, idx),
            "buy_and_hold": _pick(bh["equity_curve"], idx)
            if bh["equity_curve"]
            else [],
            "dca": _pick(dca["equity_curve"], idx) if dca["equity_curve"] else [],
            "drawdown": _pick(dd_full, idx) if dd_full.size else [],
        },
        "trades": _serialize_trades(result.closed_trades, full_ts, idx)
        if include_trades
        else [],
        "n_closed_trades": len(result.closed_trades),
        "config_summary": _config_summary(spec, config),
    }

    # Grid overlay for the price chart (mapped onto the down-sampled axis).
    try:
        payload["grid"] = compute_grid_levels(spec_dict)
    except Exception as exc:  # noqa: BLE001 - overlay is best-effort
        payload["grid"] = {"error": str(exc)}

    payload["insights"] = _build_insights(payload, spec_dict)
    payload["verdict"] = _build_verdict(payload)
    payload["data_source"] = _data_source_summary(spec_dict, result)

    if with_report:
        payload["html_report"] = render_html_report(
            result,
            metrics,
            benchmarks={"buy_and_hold": bh, "dca": dca},
            config_summary=_config_summary(spec, config),
        )
    return payload


# ---------------------------------------------------------------------------
# Insights + verdict (the "informative" layer)
# ---------------------------------------------------------------------------


def _build_insights(payload: dict, spec_dict: dict) -> list[dict]:
    m = payload["metrics"]
    out: list[dict] = []

    ret = m.get("total_return")
    bh = payload["benchmarks"]["buy_and_hold"]["total_return"]
    if ret is not None and bh is not None:
        diff = ret - bh
        if diff > 0.005:
            out.append(
                {
                    "tone": "good",
                    "text": (
                        f"Beats buy & hold by {diff * 100:.1f} pts "
                        f"({ret * 100:.1f}% vs {bh * 100:.1f}%) — the grid is adding value here."
                    ),
                }
            )
        elif diff < -0.005:
            out.append(
                {
                    "tone": "bad",
                    "text": (
                        f"Underperforms buy & hold by {abs(diff) * 100:.1f} pts "
                        f"({ret * 100:.1f}% vs {bh * 100:.1f}%). Simply holding would have done better."
                    ),
                }
            )
        else:
            out.append(
                {
                    "tone": "info",
                    "text": (
                        f"Roughly matches buy & hold ({ret * 100:.1f}% vs {bh * 100:.1f}%)."
                    ),
                }
            )

    dd = m.get("max_drawdown")
    if dd is not None:
        if dd > -0.05:
            out.append(
                {
                    "tone": "good",
                    "text": f"Shallow max drawdown of {dd * 100:.1f}% — a smooth ride.",
                }
            )
        elif dd > -0.20:
            out.append(
                {
                    "tone": "warn",
                    "text": f"Moderate max drawdown of {dd * 100:.1f}% — survivable but watch sizing.",
                }
            )
        else:
            out.append(
                {
                    "tone": "bad",
                    "text": f"Deep max drawdown of {dd * 100:.1f}% — likely an inventory build-up in a trend.",
                }
            )

    fee = m.get("fee_drag")
    if fee is not None and fee > 0.02:
        out.append(
            {
                "tone": "warn",
                "text": (
                    f"Fee drag is {fee * 100:.1f}% of capital. Grids trade a lot — widen spacing or "
                    f"use maker-only fills to keep more of the edge."
                ),
            }
        )

    fpr = m.get("fee_to_profit_ratio")
    if fpr is not None:
        if fpr >= 1.0:
            out.append(
                {
                    "tone": "bad",
                    "text": (
                        f"Fees ate the edge: you paid {fpr:.2f}× as much in fees as you kept in net profit. "
                        f"This config churns for the exchange, not for you — widen spacing or trade less."
                    ),
                }
            )
        elif fpr >= 0.5:
            out.append(
                {
                    "tone": "warn",
                    "text": (
                        f"Fee-to-profit ratio is {fpr:.2f} — fees consume a large share of the gross edge. "
                        f"Thin margin; sensitive to slippage."
                    ),
                }
            )
        elif fpr > 0:
            out.append(
                {
                    "tone": "good",
                    "text": (
                        f"Fee-to-profit ratio is a healthy {fpr:.2f} — most of the gross edge survives costs."
                    ),
                }
            )

    util = m.get("avg_capital_utilization")
    if util is not None:
        if util < 0.15:
            out.append(
                {
                    "tone": "info",
                    "text": (
                        f"Average capital utilisation is only {util * 100:.0f}% — most of your cash sat idle. "
                        f"Returns are small relative to capital tied up; consider tighter bounds or fewer rungs."
                    ),
                }
            )
        elif util > 0.85:
            out.append(
                {
                    "tone": "warn",
                    "text": (
                        f"Capital utilisation runs hot at {util * 100:.0f}% — little dry powder left for deeper dips."
                    ),
                }
            )

    tpd = m.get("trades_per_day")
    if tpd is not None and tpd > 0:
        out.append(
            {
                "tone": "info",
                "text": (
                    f"Roughly {tpd:.1f} round-trips per day. On a live venue every one pays the spread + fee, "
                    f"so realised results will trail the backtest if your cost assumptions are optimistic."
                ),
            }
        )

    if (spec_dict.get("data") or {}).get("kind", "synthetic") not in (
        "binance",
        "csv",
        "dataframe",
    ):
        out.append(
            {
                "tone": "warn",
                "text": (
                    "This run used SYNTHETIC data. Treat the numbers as a stress test, not a forecast — "
                    "switch the data source to real Binance klines before trusting profitability."
                ),
            }
        )

    pf = m.get("profit_factor")
    wr = m.get("win_rate")
    if pf is not None and wr is not None:
        if pf >= 1.5:
            out.append(
                {
                    "tone": "good",
                    "text": f"Profit factor {pf:.2f} with a {wr * 100:.0f}% win rate — a healthy edge.",
                }
            )
        elif pf >= 1.0:
            out.append(
                {
                    "tone": "info",
                    "text": f"Profit factor {pf:.2f} (win rate {wr * 100:.0f}%) — marginally profitable; fragile to costs.",
                }
            )
        else:
            out.append(
                {
                    "tone": "bad",
                    "text": f"Profit factor {pf:.2f} < 1 — losing strategy as configured.",
                }
            )

    dsr = m.get("deflated_sharpe")
    n_trials = spec_dict.get("n_trials", 1)
    if dsr is not None and n_trials and n_trials > 1:
        if dsr < 0.6:
            out.append(
                {
                    "tone": "bad",
                    "text": (
                        f"Deflated Sharpe is only {dsr * 100:.0f}% after {n_trials} trials — high over-fitting risk. "
                        f"Validate with walk-forward before trusting it."
                    ),
                }
            )
        else:
            out.append(
                {
                    "tone": "good",
                    "text": f"Deflated Sharpe holds at {dsr * 100:.0f}% after {n_trials} trials — robust to selection bias.",
                }
            )

    if payload["liquidated"]:
        out.append(
            {
                "tone": "bad",
                "text": "Position was LIQUIDATED during the run — leverage/risk caps are too loose.",
            }
        )

    rej = payload["rejections"]
    if rej:
        total = sum(rej.values())
        out.append(
            {
                "tone": "warn",
                "text": (
                    f"{total} orders were rejected ({', '.join(f'{k}:{v}' for k, v in rej.items())}). "
                    f"Constraints or capital limited the grid."
                ),
            }
        )

    regime = (spec_dict.get("data") or {}).get("regime")
    if regime == "trend":
        out.append(
            {
                "tone": "info",
                "text": "Tested on a trending regime — the hardest case for grids. Survival here is a strong signal.",
            }
        )
    elif regime == "range":
        out.append(
            {
                "tone": "info",
                "text": "Tested on a ranging regime — grid's natural habitat. Confirm it also survives a trend before going live.",
            }
        )
    return out


def _build_verdict(payload: dict) -> dict:
    m = payload["metrics"]
    score = 0
    ret = m.get("total_return") or 0.0
    bh = payload["benchmarks"]["buy_and_hold"]["total_return"] or 0.0
    dd = m.get("max_drawdown") or 0.0
    pf = m.get("profit_factor") or 0.0
    sharpe = m.get("sharpe") or 0.0

    if ret > bh:
        score += 2
    if ret > 0:
        score += 1
    if dd > -0.10:
        score += 1
    if pf >= 1.5:
        score += 2
    elif pf >= 1.0:
        score += 1
    if sharpe >= 1.0:
        score += 1
    if payload["liquidated"]:
        score -= 4

    if score >= 6:
        label, tone = "Strong", "good"
    elif score >= 4:
        label, tone = "Promising", "good"
    elif score >= 2:
        label, tone = "Marginal", "warn"
    else:
        label, tone = "Weak", "bad"
    return {"label": label, "tone": tone, "score": score, "max_score": 7}


def _data_source_summary(spec_dict: dict, result) -> dict:
    """Describe where the price data + cost model came from (real vs synthetic)."""
    d = spec_dict.get("data") or {}
    kind = d.get("kind", "synthetic")
    venue = spec_dict.get("venue")
    real = kind in ("binance", "csv")
    if kind == "binance":
        label = f"Binance {d.get('symbol', spec_dict.get('symbol', ''))} · {d.get('interval', '1h')}"
        desc = "Live Binance klines (real market history)."
    elif kind == "csv":
        label = "CSV file"
        desc = "Imported CSV price history."
    elif kind == "dataframe":
        label = "Custom data"
        desc = "Records supplied directly."
        real = True
    elif kind == "manifested_parquet":
        label = "Manifested Binance production history"
        desc = "Checksum-verified production candles loaded from typed Parquet."
        real = True
    else:
        label = f"Synthetic · {d.get('regime', 'range')}"
        desc = (
            "Generated price path — good for stress-testing, not for live expectations."
        )
    return {
        "kind": kind,
        "is_real": bool(real),
        "label": label,
        "description": desc,
        "venue": venue,
        "exchange_rules_on": bool(
            (spec_dict.get("exchange_rules") or {}).get("enabled") or venue
        ),
    }


# ---------------------------------------------------------------------------
# Research
# ---------------------------------------------------------------------------


def run_grid_search(
    base: dict,
    space: dict,
    *,
    objective: str = "deflated_sharpe",
    maximize: bool = True,
    top_k: Optional[int] = None,
) -> dict:
    ps = ParamSpace({k: list(v) for k, v in space.items()})
    results = grid_search(base, ps, objective=objective, maximize=maximize, top_k=top_k)
    rows = []
    for r in results:
        rows.append(
            {
                "params": r["params"],
                "score": _f(r["score"]),
                "total_return": _f(r["metrics"].get("total_return")),
                "max_drawdown": _f(r["metrics"].get("max_drawdown")),
                "sharpe": _f(r["metrics"].get("sharpe")),
                "deflated_sharpe": _f(r["metrics"].get("deflated_sharpe")),
                "win_rate": _f(r["metrics"].get("win_rate")),
                "profit_factor": _f(r["metrics"].get("profit_factor")),
                "n_trades": r["metrics"].get("n_trades"),
            }
        )
    keys = list(space.keys())
    heatmap = _build_heatmap(rows, keys) if len(keys) == 2 else None
    return {
        "objective": objective,
        "n_results": len(rows),
        "axes": keys,
        "results": rows,
        "heatmap": heatmap,
    }


def _build_heatmap(rows: list[dict], keys: list[str]) -> dict:
    kx, ky = keys[0], keys[1]
    xs, ys = [], []
    for r in rows:
        if r["params"].get(kx) not in xs:
            xs.append(r["params"].get(kx))
        if r["params"].get(ky) not in ys:
            ys.append(r["params"].get(ky))
    xs = sorted(xs, key=lambda v: (isinstance(v, str), v))
    ys = sorted(ys, key=lambda v: (isinstance(v, str), v))
    lookup = {(r["params"].get(kx), r["params"].get(ky)): r["score"] for r in rows}
    z = [[lookup.get((x, y)) for x in xs] for y in ys]
    return {"x_label": kx, "y_label": ky, "x": xs, "y": ys, "z": z}


def run_walk_forward(
    base: dict, space: dict, *, n_splits: int = 4, objective: str = "deflated_sharpe"
) -> dict:
    ps = ParamSpace({k: list(v) for k, v in space.items()})
    res = walk_forward(base, ps, n_splits=n_splits, objective=objective)
    for f in res.get("folds", []):
        for k in ("is_score", "oos_score", "oos_total_return", "oos_max_drawdown"):
            f[k] = _f(f.get(k))
    s = res.get("summary", {})
    for k in ("mean_oos_score", "mean_oos_return"):
        if k in s:
            s[k] = _f(s[k])
    return res


def _mc_histogram(samples: np.ndarray, bins: int = 40) -> dict:
    if samples.size == 0:
        return {"counts": [], "edges": []}
    counts, edges = np.histogram(samples, bins=bins)
    return {
        "counts": [int(c) for c in counts],
        "edges": [float(e) for e in edges],
        "centers": [
            float((edges[i] + edges[i + 1]) / 2) for i in range(len(edges) - 1)
        ],
    }


def run_monte_carlo(
    base: dict, *, method: str = "trades", n_sims: int = 2000, seed: int = 0
) -> dict:
    result = run_backtest(base, include_trades=True)
    initial = float(base.get("initial_cash", 10_000.0))
    equity = np.array(
        [p for p in result["series"]["equity"] if p is not None], dtype=float
    )
    pnls = np.array(
        [t["pnl"] for t in result["trades"] if t.get("pnl") is not None], dtype=float
    )

    mc = monte_carlo(
        {"equity_curve": equity.tolist(), "trades": result["trades"]},
        initial,
        method=method,
        n_sims=n_sims,
        seed=seed,
    )

    # Reproduce the bootstrap locally (same seed) to expose the full distribution
    # of final returns for the histogram chart.
    rng = np.random.default_rng(seed)
    final_returns = np.array([], dtype=float)
    if method == "returns" and equity.size >= 3:
        rets = np.diff(equity) / np.where(equity[:-1] == 0, np.nan, equity[:-1])
        rets = np.nan_to_num(rets, nan=0.0)
        start = float(equity[0])
        fr = np.empty(n_sims)
        for i in range(n_sims):
            fr[i] = (start * np.prod(1.0 + rng.permutation(rets))) / start - 1.0
        final_returns = fr
    elif method == "trades" and pnls.size > 0 and initial > 0:
        m = pnls.size
        fr = np.empty(n_sims)
        for i in range(n_sims):
            fr[i] = np.sum(rng.choice(pnls, size=m, replace=True)) / initial
        final_returns = fr

    out = {k: (_f(v) if isinstance(v, (int, float)) else v) for k, v in mc.items()}
    out["histogram"] = _mc_histogram(final_returns)
    out["base_total_return"] = result["metrics"].get("total_return")
    out["base_max_drawdown"] = result["metrics"].get("max_drawdown")
    out["n_trades_used"] = int(pnls.size)
    return out


def run_robustness(
    base: dict, space: Optional[dict] = None, *, n_splits: int = 3, mc_sims: int = 800
) -> dict:
    """Deployment trust scorecard: walk-forward OOS + deflated Sharpe + Monte-Carlo.

    Returns a 0-100 trust score with a transparent component breakdown. ``space``
    is the parameter grid to walk-forward optimise over; empty/None scores the
    single fixed configuration (walk-forward component is skipped).
    """
    space = {k: list(v) for k, v in (space or {}).items() if v}
    rep = robustness_report(base, space or None, n_splits=n_splits, mc_sims=mc_sims)
    return _json_safe(rep)
