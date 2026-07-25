from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from gridlab.canonical._identity import content_identity
from gridlab.canonical.adaptation import (
    AdaptationDecision,
    AdaptationObservation,
    AdaptationState,
    DecisionIntent,
    decide_adaptation,
)
from gridlab.canonical.configuration import AdaptationPolicy
from gridlab.canonical.events import DomainTime


class SafetyPosture(str, Enum):
    NORMAL = "NORMAL"
    REDUCE_ONLY = "REDUCE_ONLY"
    FROZEN = "FROZEN"


class DecisionAction(str, Enum):
    CLASSIFICATION_ACCEPTED = "CLASSIFICATION_ACCEPTED"
    NO_ACTION = "NO_ACTION"


class GateOutcome(str, Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


@dataclass(frozen=True, slots=True)
class DecisionGate:
    schema_version: str
    name: str
    outcome: GateOutcome
    reason: str

    def __post_init__(self) -> None:
        if self.schema_version != "adaptive-decision-gate/v1":
            raise ValueError("unsupported adaptive decision gate schema")
        if not self.name or not self.reason:
            raise ValueError("decision gate name and reason are required")


@dataclass(frozen=True, slots=True)
class DecisionInvariant:
    schema_version: str
    passed: bool
    checks: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.schema_version != "decision-invariant/v1":
            raise ValueError("unsupported decision invariant schema")
        object.__setattr__(self, "checks", tuple(self.checks))
        if not self.checks:
            raise ValueError("decision invariant checks are required")


@dataclass(frozen=True, slots=True)
class AdaptiveDecisionState:
    schema_version: str
    processing_position: int
    adaptation_state: AdaptationState
    safety_posture: SafetyPosture
    last_decision_id: str | None
    last_decision_time: DomainTime | None
    replay_fingerprint: str

    def __post_init__(self) -> None:
        if self.schema_version != "adaptive-decision-state/v1":
            raise ValueError("unsupported adaptive decision state schema")
        if self.processing_position < 0:
            raise ValueError("processing position must be non-negative")
        if self.processing_position == 0 and (
            self.last_decision_id is not None or self.last_decision_time is not None
        ):
            raise ValueError("initial decision state cannot have decision evidence")
        if self.processing_position > 0 and (
            not self.last_decision_id or self.last_decision_time is None
        ):
            raise ValueError("processed decision state requires decision evidence")
        if not self.replay_fingerprint.startswith("sha256:"):
            raise ValueError("decision state replay fingerprint is invalid")

    @classmethod
    def initial(cls) -> AdaptiveDecisionState:
        fingerprint = content_identity(
            "adaptive-decision-history/v1",
            {
                "processing_position": 0,
                "adaptation_state": AdaptationState.RANGE_NORMAL,
                "safety_posture": SafetyPosture.NORMAL,
            },
        )
        return cls(
            schema_version="adaptive-decision-state/v1",
            processing_position=0,
            adaptation_state=AdaptationState.RANGE_NORMAL,
            safety_posture=SafetyPosture.NORMAL,
            last_decision_id=None,
            last_decision_time=None,
            replay_fingerprint=fingerprint,
        )

    @property
    def fingerprint(self) -> str:
        return self.replay_fingerprint


@dataclass(frozen=True, slots=True)
class AdaptiveDecisionBatch:
    schema_version: str
    observation_id: str
    prior_adaptation_state: AdaptationState
    decision: AdaptationDecision
    action: DecisionAction
    gates: tuple[DecisionGate, ...]
    requested_epoch_cause: str | None
    posture_effect: SafetyPosture
    explanation: str
    invariant: DecisionInvariant

    def __post_init__(self) -> None:
        if self.schema_version != "adaptive-decision-batch/v1":
            raise ValueError("unsupported adaptive decision batch schema")
        object.__setattr__(self, "gates", tuple(self.gates))
        if self.observation_id != self.decision.observation_id:
            raise ValueError("decision batch observation identity conflicts with decision")
        if not self.gates or not self.explanation:
            raise ValueError("decision gates and explanation are required")
        if not self.invariant.passed:
            raise ValueError("failed decision invariant cannot become canonical state")
        if self.requested_epoch_cause is not None and self.action is DecisionAction.NO_ACTION:
            raise ValueError("no-action decision cannot request an epoch")

    @property
    def batch_id(self) -> str:
        return content_identity("adaptive-decision-batch/v1", self)


def _posture_for(state: AdaptationState) -> SafetyPosture:
    if state is AdaptationState.TREND_DOWN:
        return SafetyPosture.REDUCE_ONLY
    if state is AdaptationState.UNCERTAIN:
        return SafetyPosture.FROZEN
    return SafetyPosture.NORMAL


def evaluate_adaptive_decision(
    *,
    policy: AdaptationPolicy,
    observation: AdaptationObservation,
    decision_time: DomainTime,
    prior_state: AdaptiveDecisionState,
    processing_position: int,
    admitted_event_fingerprint: str,
) -> tuple[AdaptiveDecisionBatch, AdaptiveDecisionState]:
    if processing_position != prior_state.processing_position + 1:
        raise ValueError("processing position must immediately follow prior state")
    if not admitted_event_fingerprint.startswith("sha256:"):
        raise ValueError("admitted event fingerprint is invalid")
    prior_evidence = observation.prior_decision
    prior_matches = (prior_state.processing_position == 0 and prior_evidence is None) or (
        prior_state.processing_position > 0
        and prior_evidence is not None
        and prior_evidence.state is prior_state.adaptation_state
        and prior_evidence.decision_id == prior_state.last_decision_id
        and prior_evidence.decision_time == prior_state.last_decision_time
    )
    if prior_matches:
        decision = decide_adaptation(policy, observation, decision_time)
    else:
        decision = AdaptationDecision(
            schema_version="adaptation-decision/v1",
            policy_id=policy.policy_id,
            observation_id=observation.observation_id,
            decision_time=decision_time,
            state=AdaptationState.UNCERTAIN,
            intent=DecisionIntent.FROZEN,
            reason="prior_state_evidence_mismatch",
            permits_exposure_increasing_buy=False,
            requested_bound_shift=None,
        )
    uncertain = decision.state is AdaptationState.UNCERTAIN
    same_state = decision.state is prior_state.adaptation_state
    action = (
        DecisionAction.NO_ACTION
        if uncertain or same_state
        else DecisionAction.CLASSIFICATION_ACCEPTED
    )
    if uncertain:
        explanation = decision.reason
    elif same_state:
        explanation = "threshold_no_action"
    elif decision.state is AdaptationState.TREND_DOWN:
        explanation = decision.reason
    else:
        explanation = "classification_accepted"

    gates = (
        DecisionGate(
            "adaptive-decision-gate/v1",
            "classification_evidence",
            GateOutcome.FAILED if uncertain else GateOutcome.PASSED,
            decision.reason,
        ),
        DecisionGate(
            "adaptive-decision-gate/v1",
            "confirmation",
            (
                GateOutcome.FAILED
                if decision.reason == "unconfirmed_classification"
                else GateOutcome.NOT_APPLICABLE
                if uncertain
                else GateOutcome.PASSED
            ),
            (
                decision.reason
                if decision.reason == "unconfirmed_classification"
                else "classification_short_circuited"
                if uncertain
                else "required_confirmations_recorded"
            ),
        ),
        DecisionGate(
            "adaptive-decision-gate/v1",
            "hysteresis",
            (
                GateOutcome.PASSED
                if prior_evidence is not None and prior_matches
                else GateOutcome.FAILED
                if prior_evidence is not None or prior_state.processing_position > 0
                else GateOutcome.NOT_APPLICABLE
            ),
            (
                "prior_decision_evaluated"
                if prior_evidence is not None and prior_matches
                else "prior_state_evidence_mismatch"
                if prior_evidence is not None or prior_state.processing_position > 0
                else "no_prior_decision_evidence"
            ),
        ),
        DecisionGate(
            "adaptive-decision-gate/v1",
            "minimum_residence",
            GateOutcome.NOT_APPLICABLE,
            "epoch_transition_not_started",
        ),
        DecisionGate(
            "adaptive-decision-gate/v1",
            "cooldown",
            GateOutcome.NOT_APPLICABLE,
            "epoch_transition_not_started",
        ),
    )
    requested_epoch_cause = (
        observation.observation_id
        if action is DecisionAction.CLASSIFICATION_ACCEPTED
        and decision.intent in {DecisionIntent.WIDEN, DecisionIntent.SHIFT_UP}
        else None
    )
    checks = [
        "decision_observation_identity_matches",
        "decision_posture_is_fail_closed",
    ]
    invariant_passed = True
    if decision.state is AdaptationState.TREND_DOWN:
        checks.append("downtrend_has_no_buy_or_bound_shift")
        invariant_passed = (
            not decision.permits_exposure_increasing_buy
            and decision.requested_bound_shift is None
            and requested_epoch_cause is None
        )
    if decision.state is AdaptationState.UNCERTAIN:
        checks.append("uncertain_is_frozen")
        invariant_passed = invariant_passed and _posture_for(decision.state) is SafetyPosture.FROZEN
    invariant = DecisionInvariant(
        schema_version="decision-invariant/v1",
        passed=invariant_passed,
        checks=tuple(checks),
    )
    batch = AdaptiveDecisionBatch(
        schema_version="adaptive-decision-batch/v1",
        observation_id=observation.observation_id,
        prior_adaptation_state=prior_state.adaptation_state,
        decision=decision,
        action=action,
        gates=gates,
        requested_epoch_cause=requested_epoch_cause,
        posture_effect=_posture_for(decision.state),
        explanation=explanation,
        invariant=invariant,
    )
    replay_fingerprint = content_identity(
        "adaptive-decision-history/v1",
        {
            "prior_fingerprint": prior_state.fingerprint,
            "processing_position": processing_position,
            "admitted_event_fingerprint": admitted_event_fingerprint,
            "batch": batch,
        },
    )
    state = AdaptiveDecisionState(
        schema_version="adaptive-decision-state/v1",
        processing_position=processing_position,
        adaptation_state=decision.state,
        safety_posture=batch.posture_effect,
        last_decision_id=decision.decision_id,
        last_decision_time=decision.decision_time,
        replay_fingerprint=replay_fingerprint,
    )
    return batch, state
