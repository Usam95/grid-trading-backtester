from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from gridlab.canonical._identity import content_identity
from gridlab.canonical.adaptation import (
    AdaptationDecision,
    AdaptationObservation,
    AdaptationState,
    decide_adaptation,
)
from gridlab.canonical.events import DomainTime
from gridlab.canonical.initial_epoch import (
    ActivationGateOutcome,
    ActivationLifecycle,
    BootstrapEvidence,
    InitialEpochActivation,
    PlanAdmissionContext,
    derive_initial_epoch,
)
from gridlab.canonical.operator_controls import InventoryBasis
from gridlab.canonical.plan import GridPlanEpoch, VenueRuleEvidence
from gridlab.canonical.safety import (
    AllowedCommandClass,
    SafetyEvaluation,
    SafetyPosture,
)


class TransitionPhase(str, Enum):
    ACTIVE = "ACTIVE"
    CHANGE_CONFIRMED = "CHANGE_CONFIRMED"
    TRANSITION_REQUESTED = "TRANSITION_REQUESTED"
    OLD_EXPOSURE_BLOCKED = "OLD_EXPOSURE_BLOCKED"
    CANCELLING = "CANCELLING"
    RECONCILING = "RECONCILING"
    DERIVING = "DERIVING"
    VALIDATING = "VALIDATING"
    BOOTSTRAPPING = "BOOTSTRAPPING"
    ACTIVATING = "ACTIVATING"


class TransitionStepStatus(str, Enum):
    PENDING = "PENDING"
    CURRENT = "CURRENT"
    COMPLETED = "COMPLETED"
    SKIPPED = "SKIPPED"
    FAILED = "FAILED"


class TransitionGateOutcome(str, Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class ManagedOrderState(str, Enum):
    OPEN = "OPEN"
    CANCEL_PENDING = "CANCEL_PENDING"
    CANCELLED = "CANCELLED"
    FILLED = "FILLED"
    UNKNOWN = "UNKNOWN"


class TransitionCrashBoundary(str, Enum):
    CHANGE_CONFIRMED = "CHANGE_CONFIRMED"
    TRANSITION_REQUESTED = "TRANSITION_REQUESTED"
    OLD_EXPOSURE_BLOCKED = "OLD_EXPOSURE_BLOCKED"
    CANCELLING = "CANCELLING"
    RECONCILING = "RECONCILING"
    DERIVING = "DERIVING"
    VALIDATING = "VALIDATING"
    BOOTSTRAPPING = "BOOTSTRAPPING"
    ACTIVATING = "ACTIVATING"
    ACTIVE = "ACTIVE"


@dataclass(frozen=True, slots=True)
class TransitionGate:
    name: str
    outcome: TransitionGateOutcome
    reason: str

    def __post_init__(self) -> None:
        if not self.name or not self.reason:
            raise ValueError("transition gates require canonical names and reasons")


@dataclass(frozen=True, slots=True)
class TransitionProgressStep:
    phase: TransitionPhase
    status: TransitionStepStatus
    reason: str

    def __post_init__(self) -> None:
        if not self.reason:
            raise ValueError("transition progress steps require a reason")


@dataclass(frozen=True, slots=True)
class TransitionPermissions:
    placement_allowed: bool
    replacement_allowed: bool
    cancellation_allowed: bool
    reconciliation_allowed: bool
    inventory_reduction_allowed: bool


@dataclass(frozen=True, slots=True)
class OldEpochOrder:
    order_id: str
    epoch_id: str
    side: str
    state: ManagedOrderState
    exposure_increasing: bool
    inventory_reducing: bool
    terminal_proven: bool
    outcome_unknown: bool

    def __post_init__(self) -> None:
        if not self.order_id.startswith("sha256:") or not self.epoch_id.startswith("sha256:"):
            raise ValueError("old-epoch orders require deterministic identities")
        if self.side not in {"BUY", "SELL"}:
            raise ValueError("old-epoch order side must be BUY or SELL")
        if self.terminal_proven and self.outcome_unknown:
            raise ValueError("old-epoch orders cannot be terminal and outcome-unknown")
        if self.state is ManagedOrderState.UNKNOWN and not self.outcome_unknown:
            raise ValueError("unknown order state must remain outcome-unknown")


@dataclass(frozen=True, slots=True)
class LateFillPosting:
    fill_id: str
    order_id: str
    original_epoch_id: str
    posting_epoch_id: str

    def __post_init__(self) -> None:
        identities = (
            self.fill_id,
            self.order_id,
            self.original_epoch_id,
            self.posting_epoch_id,
        )
        if any(not value.startswith("sha256:") for value in identities):
            raise ValueError("late-fill postings require deterministic identities")


@dataclass(frozen=True, slots=True)
class EpochTransitionFacts:
    schema_version: str
    decision_time: DomainTime
    active_epoch: GridPlanEpoch
    active_epoch_started_at: DomainTime
    last_transition_completed_at: DomainTime | None
    transitions_in_current_day: int
    observation: AdaptationObservation
    derivation_causation_id: str
    venue_rules: VenueRuleEvidence
    bootstrap_evidence: BootstrapEvidence
    admission_context: PlanAdmissionContext
    safety: SafetyEvaluation
    inventory_basis: InventoryBasis
    old_orders: tuple[OldEpochOrder, ...]
    late_fill_postings: tuple[LateFillPosting, ...]
    request_submitted: bool
    cancellation_submitted: bool
    reconciliation_complete: bool
    activation_committed: bool
    replacement_order_ids: tuple[str, ...] = ()
    operator_preempted: bool = False
    restart_boundaries: tuple[TransitionCrashBoundary, ...] = ()
    transition_requested_at: DomainTime | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "old_orders", tuple(self.old_orders))
        object.__setattr__(self, "late_fill_postings", tuple(self.late_fill_postings))
        object.__setattr__(self, "replacement_order_ids", tuple(sorted(self.replacement_order_ids)))
        object.__setattr__(self, "restart_boundaries", tuple(self.restart_boundaries))
        if self.schema_version != "epoch-transition-facts/v1":
            raise ValueError("unsupported epoch transition facts schema")
        if self.active_epoch_started_at.value > self.decision_time.value:
            raise ValueError("active epoch residence cannot start in the future")
        if self.transitions_in_current_day < 0:
            raise ValueError("transition frequency must be non-negative")
        if not self.derivation_causation_id:
            raise ValueError("epoch transition requires a derivation causation identity")
        if self.transition_requested_at is None and (
            self.request_submitted
            or self.cancellation_submitted
            or self.reconciliation_complete
            or self.activation_committed
        ):
            raise ValueError("submitted transitions require a transition request time")
        if not self.request_submitted and (
            self.cancellation_submitted or self.reconciliation_complete or self.activation_committed
        ):
            raise ValueError("transition phases cannot advance before a request")
        if not self.cancellation_submitted and self.reconciliation_complete:
            raise ValueError("reconciliation cannot complete before cancellation is submitted")
        if any(order.epoch_id != self.active_epoch.epoch_id for order in self.old_orders):
            raise ValueError("transition facts may only describe effective active-epoch orders")
        if any(
            posting.original_epoch_id != self.active_epoch.epoch_id
            for posting in self.late_fill_postings
        ):
            raise ValueError("late fills must preserve their originating epoch")
        if any(
            posting.posting_epoch_id != posting.original_epoch_id
            for posting in self.late_fill_postings
        ):
            raise ValueError("late fills must post to their originating epoch")


@dataclass(frozen=True, slots=True)
class EpochTransitionEvaluation:
    schema_version: str
    decision_time: DomainTime
    active_epoch_id: str
    proposed_epoch_id: str | None
    current_phase: TransitionPhase
    posture: SafetyPosture
    decision: AdaptationDecision
    gates: tuple[TransitionGate, ...]
    progress: tuple[TransitionProgressStep, ...]
    permissions: TransitionPermissions
    inventory_basis: InventoryBasis
    old_orders: tuple[OldEpochOrder, ...]
    late_fill_postings: tuple[LateFillPosting, ...]
    refusal_reason: str | None
    crash_safe: bool
    replacement_activation: InitialEpochActivation | None
    proposed_epoch: GridPlanEpoch | None
    restart_boundaries: tuple[TransitionCrashBoundary, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "gates", tuple(self.gates))
        object.__setattr__(self, "progress", tuple(self.progress))
        object.__setattr__(self, "old_orders", tuple(self.old_orders))
        object.__setattr__(self, "late_fill_postings", tuple(self.late_fill_postings))
        object.__setattr__(self, "restart_boundaries", tuple(self.restart_boundaries))
        if self.schema_version != "epoch-transition-evaluation/v1":
            raise ValueError("unsupported epoch transition evaluation schema")
        if self.proposed_epoch is None and self.proposed_epoch_id is not None:
            raise ValueError("proposed epoch identity requires a proposed epoch")
        if (
            self.proposed_epoch is not None
            and self.proposed_epoch.epoch_id != self.proposed_epoch_id
        ):
            raise ValueError("proposed epoch identity must match the proposed epoch")

    @property
    def fingerprint(self) -> str:
        return content_identity("epoch-transition-evaluation/v1", self)

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "decision_time": self.decision_time.identity_payload(),
            "fingerprint": self.fingerprint,
            "active_epoch_id": self.active_epoch_id,
            "proposed_epoch_id": self.proposed_epoch_id,
            "phase": self.current_phase.value,
            "posture": self.posture.value,
            "evidence": {
                "observation_id": self.decision.observation_id,
                "decision_id": self.decision.decision_id,
                "adaptation_state": self.decision.state.value,
                "intent": self.decision.intent.value,
                "reason": self.decision.reason,
            },
            "refusal_reason": self.refusal_reason,
            "crash_safe": self.crash_safe,
            "restart_boundaries": [boundary.value for boundary in self.restart_boundaries],
            "gates": [
                {"name": gate.name, "outcome": gate.outcome.value, "reason": gate.reason}
                for gate in self.gates
            ],
            "progress": [
                {"phase": step.phase.value, "status": step.status.value, "reason": step.reason}
                for step in self.progress
            ],
            "permissions": {
                "placement_allowed": self.permissions.placement_allowed,
                "replacement_allowed": self.permissions.replacement_allowed,
                "cancellation_allowed": self.permissions.cancellation_allowed,
                "reconciliation_allowed": self.permissions.reconciliation_allowed,
                "inventory_reduction_allowed": self.permissions.inventory_reduction_allowed,
            },
            "inventory_basis": {
                "basis_id": self.inventory_basis.basis_id,
                "source": self.inventory_basis.source,
                "base_asset": self.inventory_basis.base_asset,
                "quantity": self.inventory_basis.quantity.to_payload(),
                "authoritative": self.inventory_basis.authoritative,
                "reconciled_at": (
                    self.inventory_basis.reconciled_at.identity_payload()
                    if self.inventory_basis.reconciled_at is not None
                    else None
                ),
            },
            "old_orders": [
                {
                    "order_id": order.order_id,
                    "epoch_id": order.epoch_id,
                    "side": order.side,
                    "state": order.state.value,
                    "exposure_increasing": order.exposure_increasing,
                    "inventory_reducing": order.inventory_reducing,
                    "terminal_proven": order.terminal_proven,
                    "outcome_unknown": order.outcome_unknown,
                }
                for order in self.old_orders
            ],
            "late_fill_postings": [
                {
                    "fill_id": posting.fill_id,
                    "order_id": posting.order_id,
                    "original_epoch_id": posting.original_epoch_id,
                    "posting_epoch_id": posting.posting_epoch_id,
                }
                for posting in self.late_fill_postings
            ],
            "replacement_activation": (
                {
                    "lifecycle": self.replacement_activation.lifecycle.value,
                    "replay_fingerprint": self.replacement_activation.replay_fingerprint,
                    "ladder_placement_allowed": (
                        self.replacement_activation.ladder_placement_allowed
                    ),
                    "bootstrap_required": (
                        self.replacement_activation.lifecycle is ActivationLifecycle.BOOTSTRAPPING
                    ),
                    "admission_context": {
                        "still_effective_quote_commitment": (
                            self.replacement_activation.admission_context.still_effective_quote_commitment.to_payload()
                        ),
                        "still_effective_inventory_commitment": (
                            self.replacement_activation.admission_context.still_effective_inventory_commitment.to_payload()
                        ),
                        "still_effective_order_count": (
                            self.replacement_activation.admission_context.still_effective_order_count
                        ),
                    },
                    "admission_assessment": (
                        {
                            "capital_envelope": (
                                self.replacement_activation.admission_assessment.capital_envelope.to_payload()
                            ),
                            "total_quote_commitment": (
                                self.replacement_activation.admission_assessment.total_quote_commitment.to_payload()
                            ),
                            "bootstrap_quote_commitment": (
                                self.replacement_activation.admission_assessment.bootstrap_quote_commitment.to_payload()
                            ),
                            "fee_reserve": (
                                self.replacement_activation.admission_assessment.fee_reserve.to_payload()
                            ),
                            "maximum_planned_inventory": (
                                self.replacement_activation.admission_assessment.maximum_planned_inventory.to_payload()
                            ),
                            "total_worst_case_inventory": (
                                self.replacement_activation.admission_assessment.total_worst_case_inventory.to_payload()
                            ),
                            "total_order_count": (
                                self.replacement_activation.admission_assessment.total_order_count
                            ),
                            "venue_order_capacity": (
                                self.replacement_activation.admission_assessment.venue_order_capacity
                            ),
                        }
                        if self.replacement_activation.admission_assessment is not None
                        else None
                    ),
                    "gates": [
                        {
                            "name": gate.name,
                            "outcome": gate.outcome.value,
                            "reason": gate.reason,
                        }
                        for gate in self.replacement_activation.gates
                    ],
                }
                if self.replacement_activation is not None
                else None
            ),
        }


@dataclass(frozen=True, slots=True)
class FakeTransitionRuntime:
    facts: EpochTransitionFacts

    def evaluate(self) -> EpochTransitionEvaluation:
        return evaluate_epoch_transition(self.facts)


def _timing_gate(
    name: str, passed: bool, success_reason: str, failure_reason: str
) -> TransitionGate:
    return TransitionGate(
        name=name,
        outcome=TransitionGateOutcome.PASSED if passed else TransitionGateOutcome.FAILED,
        reason=success_reason if passed else failure_reason,
    )


def _has_material_change(active_epoch: GridPlanEpoch, decision: AdaptationDecision) -> bool:
    return (
        decision.state is not active_epoch.decision.state
        or decision.intent is not active_epoch.decision.intent
        or decision.requested_bound_shift != active_epoch.decision.requested_bound_shift
    )


def _resolved_orders(orders: tuple[OldEpochOrder, ...]) -> bool:
    return all(order.terminal_proven or order.outcome_unknown for order in orders)


def _terminal_orders(orders: tuple[OldEpochOrder, ...]) -> bool:
    return all(order.terminal_proven for order in orders)


def _crash_safe(
    *,
    permissions: TransitionPermissions,
    facts: EpochTransitionFacts,
    replacement_ready: bool,
) -> bool:
    if permissions.placement_allowed or permissions.replacement_allowed:
        return False
    if any(order.outcome_unknown for order in facts.old_orders):
        return False
    if facts.operator_preempted:
        return True
    if not replacement_ready:
        return False
    return facts.inventory_basis.authoritative


def evaluate_epoch_transition(facts: EpochTransitionFacts) -> EpochTransitionEvaluation:
    decision = decide_adaptation(
        facts.active_epoch.configuration.adaptation_policy,
        facts.observation,
        facts.decision_time,
    )
    policy = facts.active_epoch.configuration.adaptation_policy
    change_gate = TransitionGate(
        name="confirmation",
        outcome=(
            TransitionGateOutcome.PASSED
            if _has_material_change(facts.active_epoch, decision)
            and decision.state not in {AdaptationState.TREND_DOWN, AdaptationState.UNCERTAIN}
            else TransitionGateOutcome.FAILED
        ),
        reason=(
            "change_confirmed_from_admitted_evidence"
            if _has_material_change(facts.active_epoch, decision)
            and decision.state not in {AdaptationState.TREND_DOWN, AdaptationState.UNCERTAIN}
            else "uncertain_transition_frozen"
            if decision.state is AdaptationState.UNCERTAIN
            else "downtrend_recovery_only"
            if decision.state is AdaptationState.TREND_DOWN
            else "no_change_confirmed"
        ),
    )
    residence_ok = (
        facts.decision_time.value - facts.active_epoch_started_at.value
        >= policy.minimum_epoch_residence
    )
    cooldown_ok = facts.last_transition_completed_at is None or (
        facts.decision_time.value - facts.last_transition_completed_at.value
        >= policy.transition_cooldown
    )
    frequency_ok = facts.transitions_in_current_day < policy.maximum_transitions_per_day
    expiry_ok = facts.transition_requested_at is None or (
        facts.decision_time.value - facts.transition_requested_at.value <= policy.transition_expiry
    )
    gates = (
        change_gate,
        _timing_gate(
            "minimum_residence",
            residence_ok,
            "minimum_residence_satisfied",
            "minimum_residence_unsatisfied",
        ),
        _timing_gate(
            "cooldown",
            cooldown_ok,
            "transition_cooldown_satisfied",
            "transition_cooldown_unsatisfied",
        ),
        _timing_gate(
            "maximum_frequency",
            frequency_ok,
            "transition_frequency_satisfied",
            "transition_frequency_exceeded",
        ),
        TransitionGate(
            name="expiry",
            outcome=(
                TransitionGateOutcome.PASSED
                if facts.transition_requested_at is None or expiry_ok
                else TransitionGateOutcome.FAILED
            ),
            reason=(
                "transition_not_requested"
                if facts.transition_requested_at is None
                else "transition_expiry_satisfied"
                if expiry_ok
                else "transition_expired"
            ),
        ),
    )
    blocking_gate = next(
        (gate for gate in gates if gate.outcome is TransitionGateOutcome.FAILED), None
    )
    if facts.operator_preempted:
        refusal_reason = "operator_preempted"
    elif blocking_gate is not None:
        refusal_reason = blocking_gate.reason
    else:
        refusal_reason = None
    if decision.state is AdaptationState.UNCERTAIN:
        posture = SafetyPosture.FROZEN
    elif (
        decision.state is AdaptationState.TREND_DOWN
        and facts.safety.posture is SafetyPosture.NORMAL
    ):
        posture = SafetyPosture.REDUCE_ONLY
    else:
        posture = facts.safety.posture
    request_active = facts.request_submitted and refusal_reason is None
    permissions = TransitionPermissions(
        placement_allowed=(
            not request_active
            and not facts.operator_preempted
            and facts.safety.placement_allowed
            and change_gate.outcome is not TransitionGateOutcome.FAILED
        ),
        replacement_allowed=(
            not request_active
            and not facts.operator_preempted
            and facts.safety.replacement_allowed
            and change_gate.outcome is not TransitionGateOutcome.FAILED
        ),
        cancellation_allowed=AllowedCommandClass.CANCELLATION
        in facts.safety.allowed_command_classes,
        reconciliation_allowed=(
            AllowedCommandClass.RECONCILIATION in facts.safety.allowed_command_classes
        ),
        inventory_reduction_allowed=(
            AllowedCommandClass.INVENTORY_REDUCING in facts.safety.allowed_command_classes
        ),
    )
    replacement_activation: InitialEpochActivation | None = None
    proposed_epoch: GridPlanEpoch | None = None
    proposed_epoch_id: str | None = None
    identity_overlap = set(facts.replacement_order_ids).intersection(
        order.order_id for order in facts.old_orders
    )
    orders_resolved = _resolved_orders(facts.old_orders)
    orders_terminal = _terminal_orders(facts.old_orders)
    late_fills_reconciled = all(
        posting.posting_epoch_id == posting.original_epoch_id
        for posting in facts.late_fill_postings
    )
    replacement_ready = False
    if (
        request_active
        and facts.cancellation_submitted
        and orders_terminal
        and facts.reconciliation_complete
    ):
        replacement_activation = derive_initial_epoch(
            configuration=facts.active_epoch.configuration,
            observation=facts.observation,
            decision_time=facts.decision_time,
            activation_price=facts.observation.reference_price,
            derivation_causation_id=facts.derivation_causation_id,
            venue_rules=facts.venue_rules,
            bootstrap_evidence=facts.bootstrap_evidence,
            admission_context=facts.admission_context,
        )
        if replacement_activation.epoch is not None:
            proposed_epoch = GridPlanEpoch.derive(
                configuration=facts.active_epoch.configuration,
                observation=facts.observation,
                decision=decision,
                predecessor_epoch_id=facts.active_epoch.epoch_id,
                derivation_causation_id=facts.derivation_causation_id,
                venue_rules=facts.venue_rules,
                plan=replacement_activation.epoch.plan,
                presentation={
                    "transition": "replacement-epoch/v1",
                    "active_epoch_id": facts.active_epoch.epoch_id,
                },
            )
            proposed_epoch_id = proposed_epoch.epoch_id
        replacement_ready = (
            replacement_activation.lifecycle
            in {ActivationLifecycle.ACTIVE, ActivationLifecycle.BOOTSTRAPPING}
            and proposed_epoch is not None
            and not identity_overlap
        )
    validation_failed = (
        replacement_activation is not None
        and replacement_activation.lifecycle is ActivationLifecycle.REJECTED
    ) or bool(identity_overlap)
    if validation_failed and refusal_reason is None:
        if identity_overlap:
            refusal_reason = "managed_identity_reuse_forbidden"
        else:
            assert replacement_activation is not None
            refusal_reason = next(
                (
                    gate.reason
                    for gate in replacement_activation.gates
                    if gate.outcome is ActivationGateOutcome.FAILED
                ),
                "replacement_validation_failed",
            )
    phase = TransitionPhase.ACTIVE
    if refusal_reason is None and change_gate.outcome is TransitionGateOutcome.PASSED:
        phase = TransitionPhase.CHANGE_CONFIRMED
        if request_active:
            phase = TransitionPhase.TRANSITION_REQUESTED
            phase = TransitionPhase.OLD_EXPOSURE_BLOCKED
            if facts.cancellation_submitted:
                phase = TransitionPhase.CANCELLING
                if orders_resolved:
                    phase = TransitionPhase.RECONCILING
                    if facts.reconciliation_complete and late_fills_reconciled and orders_terminal:
                        phase = TransitionPhase.DERIVING
                        assert replacement_activation is not None
                        phase = TransitionPhase.VALIDATING
                        if replacement_activation.lifecycle is ActivationLifecycle.BOOTSTRAPPING:
                            phase = TransitionPhase.BOOTSTRAPPING
                        elif facts.activation_committed:
                            phase = TransitionPhase.ACTIVE
                        else:
                            phase = TransitionPhase.ACTIVATING
    elif facts.request_submitted and refusal_reason == "transition_expired":
        phase = TransitionPhase.ACTIVE
    progress: list[TransitionProgressStep] = []
    phase_order = (
        TransitionPhase.CHANGE_CONFIRMED,
        TransitionPhase.TRANSITION_REQUESTED,
        TransitionPhase.OLD_EXPOSURE_BLOCKED,
        TransitionPhase.CANCELLING,
        TransitionPhase.RECONCILING,
        TransitionPhase.DERIVING,
        TransitionPhase.VALIDATING,
        TransitionPhase.BOOTSTRAPPING,
        TransitionPhase.ACTIVATING,
        TransitionPhase.ACTIVE,
    )
    current_found = False
    for candidate in phase_order:
        if candidate is TransitionPhase.ACTIVE:
            status = (
                TransitionStepStatus.CURRENT
                if phase is TransitionPhase.ACTIVE and not current_found
                else TransitionStepStatus.PENDING
            )
            reason = (
                "replacement_epoch_active"
                if facts.activation_committed and refusal_reason is None and replacement_ready
                else refusal_reason or "active_epoch_retained"
            )
        elif refusal_reason is not None and candidate is phase_order[0]:
            status = TransitionStepStatus.FAILED
            reason = refusal_reason
        elif current_found:
            status = TransitionStepStatus.PENDING
            reason = "awaiting_prior_transition_step"
        elif candidate is phase:
            status = TransitionStepStatus.CURRENT
            current_found = True
            reason = {
                TransitionPhase.CHANGE_CONFIRMED: "confirmed_change_ready_for_request",
                TransitionPhase.TRANSITION_REQUESTED: "transition_request_recorded",
                TransitionPhase.OLD_EXPOSURE_BLOCKED: "old_epoch_exposure_blocked",
                TransitionPhase.CANCELLING: "effective_orders_cancelling",
                TransitionPhase.RECONCILING: "late_fill_reconciliation_in_progress",
                TransitionPhase.DERIVING: "replacement_derivation_started",
                TransitionPhase.VALIDATING: "replacement_validation_running",
                TransitionPhase.BOOTSTRAPPING: "bounded_bootstrap_required",
                TransitionPhase.ACTIVATING: "replacement_activation_ready",
                TransitionPhase.ACTIVE: "replacement_epoch_active",
            }[candidate]
        elif refusal_reason is None and phase_order.index(candidate) < phase_order.index(phase):
            status = TransitionStepStatus.COMPLETED
            reason = "transition_step_completed"
        else:
            status = TransitionStepStatus.PENDING
            reason = "awaiting_transition_step"
        progress.append(TransitionProgressStep(candidate, status, reason))
    crash_safe = _crash_safe(
        permissions=permissions,
        facts=facts,
        replacement_ready=replacement_ready and facts.activation_committed,
    )
    return EpochTransitionEvaluation(
        schema_version="epoch-transition-evaluation/v1",
        decision_time=facts.decision_time,
        active_epoch_id=facts.active_epoch.epoch_id,
        proposed_epoch_id=proposed_epoch_id,
        current_phase=phase,
        posture=posture,
        decision=decision,
        gates=gates,
        progress=tuple(progress),
        permissions=permissions,
        inventory_basis=facts.inventory_basis,
        old_orders=facts.old_orders,
        late_fill_postings=facts.late_fill_postings,
        refusal_reason=refusal_reason,
        crash_safe=crash_safe,
        replacement_activation=replacement_activation,
        proposed_epoch=proposed_epoch,
        restart_boundaries=facts.restart_boundaries,
    )
