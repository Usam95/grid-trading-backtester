from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from gridlab.canonical._identity import content_identity
from gridlab.canonical.events import DomainTime
from gridlab.canonical.safety import SafetyEvaluation
from gridlab.canonical.values import ExactDecimal


class PreviewAvailability(str, Enum):
    IMMEDIATE = "IMMEDIATE"
    PREVIEW_REQUIRED = "PREVIEW_REQUIRED"
    BLOCKED = "BLOCKED"
    LATCHED = "LATCHED"


class GateOutcome(str, Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"


class StopDisposition(str, Enum):
    RETAIN_HOLDING = "RETAIN_HOLDING"
    DISPOSE = "DISPOSE"


class TerminalTrigger(str, Enum):
    NONE = "NONE"
    OPERATOR_EMERGENCY = "OPERATOR_EMERGENCY"
    TERMINAL_LOSS = "TERMINAL_LOSS"


class TerminalState(str, Enum):
    NONE = "NONE"
    AWAITING_AUTHORITATIVE_INVENTORY = "AWAITING_AUTHORITATIVE_INVENTORY"
    DISPOSING = "DISPOSING"
    DISPOSED = "DISPOSED"
    RETAINED = "RETAINED"


class TerminalWaveOutcome(str, Enum):
    PARTIAL = "PARTIAL"
    REJECTED = "REJECTED"
    UNKNOWN = "UNKNOWN"
    EXHAUSTED = "EXHAUSTED"
    RESIDUAL_RETAINED = "RESIDUAL_RETAINED"
    COMPLETED = "COMPLETED"


REQUIRED_GOLDEN_CASE_NAMES = (
    "GAP_THROUGH",
    "PARTIAL_DISPOSAL",
    "REJECTION",
    "UNKNOWN_OUTCOME",
    "ATTEMPT_EXHAUSTION",
    "RESIDUAL_HOLDINGS",
)


@dataclass(frozen=True, slots=True)
class ManagedObligation:
    obligation_id: str
    side: str
    exposure_increasing: bool
    inventory_reducing: bool
    fully_backed: bool

    def __post_init__(self) -> None:
        if not self.obligation_id.startswith("sha256:"):
            raise ValueError("managed obligation identity is required")
        if self.side not in {"BUY", "SELL"}:
            raise ValueError("managed obligation side must be BUY or SELL")


@dataclass(frozen=True, slots=True)
class InventoryBasis:
    basis_id: str
    source: str
    base_asset: str
    quantity: ExactDecimal
    authoritative: bool
    reconciled_at: DomainTime | None

    def __post_init__(self) -> None:
        if not self.basis_id.startswith("sha256:") or not self.source or not self.base_asset:
            raise ValueError("authoritative inventory basis identity and source are required")
        if self.quantity.kind != "base_quantity" or self.quantity.decimal < 0:
            raise ValueError("authoritative inventory basis requires a non-negative base quantity")
        if self.authoritative and self.reconciled_at is None:
            raise ValueError("authoritative inventory basis requires reconciliation time")
        if not self.authoritative and self.reconciled_at is not None:
            raise ValueError("non-authoritative inventory basis cannot claim reconciliation")


@dataclass(frozen=True, slots=True)
class PreviewGate:
    name: str
    outcome: GateOutcome
    reason: str

    def __post_init__(self) -> None:
        if not self.name or not self.reason:
            raise ValueError("preview gates require canonical names and reasons")


@dataclass(frozen=True, slots=True)
class TerminalDisposalWave:
    wave: int
    quantity_limit: ExactDecimal
    notional_limit: ExactDecimal
    max_depth_age: ExactDecimal
    price_band_bps: ExactDecimal
    attempt_limit: int
    elapsed_time_limit: ExactDecimal
    outcome: TerminalWaveOutcome
    reconciled_before_next_wave: bool
    authoritative_inventory_after_wave: ExactDecimal

    def __post_init__(self) -> None:
        if self.wave <= 0 or self.attempt_limit <= 0:
            raise ValueError("terminal IOC waves require positive wave and attempt bounds")
        if self.quantity_limit.kind != "base_quantity" or self.quantity_limit.decimal <= 0:
            raise ValueError("terminal IOC waves require a positive quantity bound")
        if self.notional_limit.kind != "quote_quantity" or self.notional_limit.decimal <= 0:
            raise ValueError("terminal IOC waves require a positive notional bound")
        if self.max_depth_age.kind != "duration_seconds" or not (
            self.max_depth_age.decimal > 0 and self.max_depth_age.decimal <= 5
        ):
            raise ValueError(
                "terminal IOC waves require a fresh-depth bound of five seconds or less"
            )
        if self.price_band_bps.kind != "basis_points" or self.price_band_bps.decimal <= 0:
            raise ValueError("terminal IOC waves require a positive price-band bound")
        if (
            self.elapsed_time_limit.kind != "duration_seconds"
            or self.elapsed_time_limit.decimal <= 0
        ):
            raise ValueError("terminal IOC waves require a positive elapsed-time bound")
        if (
            self.authoritative_inventory_after_wave.kind != "base_quantity"
            or self.authoritative_inventory_after_wave.decimal < 0
        ):
            raise ValueError(
                "terminal IOC waves require non-negative authoritative inventory results"
            )


@dataclass(frozen=True, slots=True)
class GoldenReplayCase:
    case_name: str
    outcome: str
    replay_fingerprint: str

    def __post_init__(self) -> None:
        if self.case_name not in REQUIRED_GOLDEN_CASE_NAMES:
            raise ValueError(
                "terminal disposal golden replay case is not part of the accepted bundle"
            )
        if not self.outcome or not self.replay_fingerprint.startswith("sha256:"):
            raise ValueError("terminal disposal golden replay cases require deterministic identity")


@dataclass(frozen=True, slots=True)
class OperatorControlFacts:
    decision_time: DomainTime
    environment: str
    active_epoch_id: str
    proposed_epoch_id: str | None
    transition_state: str
    activation_pending: bool
    paused: bool
    safety: SafetyEvaluation
    managed_obligations: tuple[ManagedObligation, ...]
    inventory_basis: InventoryBasis
    resume_evidence_current: bool
    resume_reconciliation_ok: bool
    resume_invariants_ok: bool
    resume_plan_valid: bool
    resume_authority_ok: bool
    operator_stop_disposition: StopDisposition | None
    late_fill_ids: tuple[str, ...]
    emergency_stop_requested: bool
    prior_operator_emergency_latched: bool
    disposal_waves: tuple[TerminalDisposalWave, ...]
    golden_replay_cases: tuple[GoldenReplayCase, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "managed_obligations", tuple(self.managed_obligations))
        object.__setattr__(self, "late_fill_ids", tuple(sorted(self.late_fill_ids)))
        object.__setattr__(self, "disposal_waves", tuple(self.disposal_waves))
        object.__setattr__(self, "golden_replay_cases", tuple(self.golden_replay_cases))
        if not self.environment or not self.transition_state:
            raise ValueError("operator control facts require environment and transition state")
        if not self.active_epoch_id.startswith("sha256:"):
            raise ValueError("operator controls require an active epoch identity")
        if self.proposed_epoch_id is not None and not self.proposed_epoch_id.startswith("sha256:"):
            raise ValueError("operator controls require deterministic proposed epoch identity")
        if set(case.case_name for case in self.golden_replay_cases) != set(
            REQUIRED_GOLDEN_CASE_NAMES
        ):
            raise ValueError("terminal disposal golden replay coverage is incomplete")
        if self.disposal_waves:
            ordered = tuple(sorted(self.disposal_waves, key=lambda item: item.wave))
            if ordered != self.disposal_waves:
                raise ValueError("terminal IOC waves must be provided in deterministic order")
            for current, following in zip(ordered, ordered[1:]):
                if not current.reconciled_before_next_wave:
                    raise ValueError("terminal IOC waves must reconcile between waves")
                if following.wave != current.wave + 1:
                    raise ValueError("terminal IOC waves must use contiguous attempt order")


@dataclass(frozen=True, slots=True)
class OperatorCommandPreview:
    action: str
    availability: PreviewAvailability
    confirmation_required: bool
    environment_bound: bool
    idempotent: bool
    preempts_pending_activation: bool
    blocks_new_epoch_placement: bool
    admission_order_preserved: bool
    active_epoch_id: str
    proposed_epoch_id: str | None
    transition_state: str
    posture: str
    inventory_basis_id: str
    cancel_obligation_ids: tuple[str, ...]
    retained_obligation_ids: tuple[str, ...]
    late_fill_ids: tuple[str, ...]
    gates: tuple[PreviewGate, ...]
    reason_codes: tuple[str, ...]
    available_dispositions: tuple[StopDisposition, ...]
    selected_disposition: StopDisposition | None

    def __post_init__(self) -> None:
        object.__setattr__(self, "cancel_obligation_ids", tuple(self.cancel_obligation_ids))
        object.__setattr__(self, "retained_obligation_ids", tuple(self.retained_obligation_ids))
        object.__setattr__(self, "late_fill_ids", tuple(self.late_fill_ids))
        object.__setattr__(self, "gates", tuple(self.gates))
        object.__setattr__(self, "reason_codes", tuple(self.reason_codes))
        object.__setattr__(self, "available_dispositions", tuple(self.available_dispositions))


@dataclass(frozen=True, slots=True)
class TerminalDisposalEvaluation:
    trigger: TerminalTrigger
    state: TerminalState
    global_stop_latched: bool
    operator_emergency_latched: bool
    automatic_liquidation: bool
    preempts_pending_activation: bool
    admission_order_preserved: bool
    active_epoch_id: str
    proposed_epoch_id: str | None
    transition_state: str
    posture: str
    inventory_basis_id: str
    waves: tuple[TerminalDisposalWave, ...]
    golden_replay_cases: tuple[GoldenReplayCase, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "waves", tuple(self.waves))
        object.__setattr__(self, "golden_replay_cases", tuple(self.golden_replay_cases))


@dataclass(frozen=True, slots=True)
class OperatorControlEvaluation:
    schema_version: str
    decision_time: DomainTime
    input_fingerprint: str
    pause: OperatorCommandPreview
    resume: OperatorCommandPreview
    operator_stop: OperatorCommandPreview
    emergency_stop: OperatorCommandPreview
    terminal: TerminalDisposalEvaluation

    def __post_init__(self) -> None:
        if self.schema_version != "operator-control-evaluation/v1":
            raise ValueError("unsupported operator control evaluation schema")
        if not self.input_fingerprint.startswith("sha256:"):
            raise ValueError("operator control input fingerprint is required")

    @property
    def fingerprint(self) -> str:
        return content_identity("operator-control-evaluation/v1", self)


def evaluate_operator_controls(facts: OperatorControlFacts) -> OperatorControlEvaluation:
    cancel_ids = tuple(
        sorted(
            obligation.obligation_id
            for obligation in facts.managed_obligations
            if not (
                obligation.side == "SELL"
                and obligation.inventory_reducing
                and obligation.fully_backed
            )
        )
    )
    retained_ids = tuple(
        sorted(
            obligation.obligation_id
            for obligation in facts.managed_obligations
            if obligation.side == "SELL"
            and obligation.inventory_reducing
            and obligation.fully_backed
        )
    )
    preempts_pending = facts.activation_pending
    common = {
        "environment_bound": True,
        "idempotent": True,
        "preempts_pending_activation": preempts_pending,
        "blocks_new_epoch_placement": preempts_pending,
        "admission_order_preserved": True,
        "active_epoch_id": facts.active_epoch_id,
        "proposed_epoch_id": facts.proposed_epoch_id,
        "transition_state": facts.transition_state,
        "posture": facts.safety.posture.value,
        "inventory_basis_id": facts.inventory_basis.basis_id,
    }
    pause = OperatorCommandPreview(
        action="PAUSE",
        availability=PreviewAvailability.LATCHED if facts.paused else PreviewAvailability.IMMEDIATE,
        confirmation_required=False,
        cancel_obligation_ids=cancel_ids,
        retained_obligation_ids=retained_ids,
        late_fill_ids=(),
        gates=(),
        reason_codes=("pause_blocks_exposure_increasing_buys",),
        available_dispositions=(),
        selected_disposition=None,
        **common,
    )
    resume_gates = (
        PreviewGate(
            "current_evidence",
            GateOutcome.PASSED if facts.resume_evidence_current else GateOutcome.FAILED,
            "current authoritative evidence is required",
        ),
        PreviewGate(
            "reconciliation",
            GateOutcome.PASSED if facts.resume_reconciliation_ok else GateOutcome.FAILED,
            "resume requires reconciled authoritative inventory",
        ),
        PreviewGate(
            "invariants",
            GateOutcome.PASSED if facts.resume_invariants_ok else GateOutcome.FAILED,
            "resume requires invariant convergence",
        ),
        PreviewGate(
            "plan_validity",
            GateOutcome.PASSED if facts.resume_plan_valid else GateOutcome.FAILED,
            "resume requires a currently valid plan",
        ),
        PreviewGate(
            "command_authority",
            GateOutcome.PASSED if facts.resume_authority_ok else GateOutcome.FAILED,
            "resume requires an authenticated command path",
        ),
        PreviewGate(
            "posture",
            GateOutcome.PASSED
            if not facts.safety.global_stop_latched and not facts.prior_operator_emergency_latched
            else GateOutcome.FAILED,
            "resume is refused while any global stop remains latched",
        ),
    )
    resume_ready = all(gate.outcome is GateOutcome.PASSED for gate in resume_gates)
    resume = OperatorCommandPreview(
        action="RESUME",
        availability=PreviewAvailability.PREVIEW_REQUIRED
        if resume_ready
        else PreviewAvailability.BLOCKED,
        confirmation_required=True,
        cancel_obligation_ids=(),
        retained_obligation_ids=retained_ids,
        late_fill_ids=(),
        gates=resume_gates,
        reason_codes=tuple(
            gate.name for gate in resume_gates if gate.outcome is GateOutcome.FAILED
        ),
        available_dispositions=(),
        selected_disposition=None,
        **common,
    )
    operator_stop = OperatorCommandPreview(
        action="OPERATOR_STOP",
        availability=(
            PreviewAvailability.PREVIEW_REQUIRED
            if facts.operator_stop_disposition is not None
            else PreviewAvailability.BLOCKED
        ),
        confirmation_required=True,
        cancel_obligation_ids=tuple(
            sorted(obligation.obligation_id for obligation in facts.managed_obligations)
        ),
        retained_obligation_ids=(),
        late_fill_ids=facts.late_fill_ids,
        gates=(
            PreviewGate(
                "explicit_disposition",
                (
                    GateOutcome.PASSED
                    if facts.operator_stop_disposition is not None
                    else GateOutcome.FAILED
                ),
                "operator stop requires an explicit retained-holding or disposal disposition",
            ),
        ),
        reason_codes=(
            ("operator_stop_requires_explicit_disposition",)
            if facts.operator_stop_disposition is None
            else ("operator_stop_reconciles_late_fills",)
        ),
        available_dispositions=(
            StopDisposition.RETAIN_HOLDING,
            StopDisposition.DISPOSE,
        ),
        selected_disposition=facts.operator_stop_disposition,
        **common,
    )
    operator_emergency_latched = (
        facts.prior_operator_emergency_latched or facts.emergency_stop_requested
    )
    trigger = TerminalTrigger.NONE
    if operator_emergency_latched:
        trigger = TerminalTrigger.OPERATOR_EMERGENCY
    elif facts.safety.global_stop_latched:
        trigger = TerminalTrigger.TERMINAL_LOSS
    global_stop_latched = operator_emergency_latched or facts.safety.global_stop_latched
    if trigger is TerminalTrigger.NONE:
        if (
            facts.operator_stop_disposition is StopDisposition.DISPOSE
            and facts.inventory_basis.authoritative
        ):
            terminal_state = TerminalState.DISPOSED if facts.disposal_waves else TerminalState.NONE
        elif facts.operator_stop_disposition is StopDisposition.RETAIN_HOLDING:
            terminal_state = TerminalState.RETAINED
        else:
            terminal_state = TerminalState.NONE
    elif not facts.inventory_basis.authoritative:
        terminal_state = TerminalState.AWAITING_AUTHORITATIVE_INVENTORY
    elif facts.disposal_waves:
        last = facts.disposal_waves[-1]
        terminal_state = (
            TerminalState.DISPOSED
            if last.authoritative_inventory_after_wave.decimal == 0
            else TerminalState.DISPOSING
        )
    else:
        terminal_state = TerminalState.DISPOSING
    emergency_stop = OperatorCommandPreview(
        action="EMERGENCY_STOP",
        availability=(
            PreviewAvailability.LATCHED
            if operator_emergency_latched
            else PreviewAvailability.IMMEDIATE
        ),
        confirmation_required=False,
        cancel_obligation_ids=tuple(
            sorted(obligation.obligation_id for obligation in facts.managed_obligations)
        ),
        retained_obligation_ids=(),
        late_fill_ids=(),
        gates=(),
        reason_codes=(
            ("operator_emergency_stop_latched",)
            if operator_emergency_latched
            else ("operator_emergency_stop_immediately_available",)
        ),
        available_dispositions=(),
        selected_disposition=None,
        **common,
    )
    terminal = TerminalDisposalEvaluation(
        trigger=trigger,
        state=terminal_state,
        global_stop_latched=global_stop_latched,
        operator_emergency_latched=operator_emergency_latched,
        automatic_liquidation=trigger is TerminalTrigger.TERMINAL_LOSS,
        preempts_pending_activation=preempts_pending and global_stop_latched,
        admission_order_preserved=True,
        active_epoch_id=facts.active_epoch_id,
        proposed_epoch_id=facts.proposed_epoch_id,
        transition_state=facts.transition_state,
        posture=facts.safety.posture.value,
        inventory_basis_id=facts.inventory_basis.basis_id,
        waves=facts.disposal_waves,
        golden_replay_cases=facts.golden_replay_cases,
    )
    input_fingerprint = content_identity("operator-controls-input/v1", facts)
    return OperatorControlEvaluation(
        schema_version="operator-control-evaluation/v1",
        decision_time=facts.decision_time,
        input_fingerprint=input_fingerprint,
        pause=pause,
        resume=resume,
        operator_stop=operator_stop,
        emergency_stop=emergency_stop,
        terminal=terminal,
    )
