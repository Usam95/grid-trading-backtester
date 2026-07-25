from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import json
from pathlib import Path
import sqlite3
from typing import Any, Mapping

from gridlab.canonical.adaptation import (
    AdaptationDecision,
    AdaptationObservation,
    AdaptationState,
    ConfirmationEvidence,
    DecisionIntent,
    EvidenceQuality,
    PriorDecisionEvidence,
)
from gridlab.canonical.configuration import AdaptationPolicy
from gridlab.canonical.decision_path import (
    AdaptiveDecisionBatch,
    AdaptiveDecisionState,
    DecisionAction,
    DecisionGate,
    DecisionInvariant,
    GateOutcome,
    SafetyPosture,
    evaluate_adaptive_decision,
)
from gridlab.canonical.events import CanonicalEvent, DomainTime, EventSource
from gridlab.canonical.values import ExactDecimal


class EvidenceDisposition(str, Enum):
    ADMITTED = "ADMITTED"
    DUPLICATE = "DUPLICATE"
    LATE = "LATE"
    CONFLICT = "CONFLICT"


class CrashBoundary(str, Enum):
    ADMITTED_INPUT = "admitted_input"
    DECISION_BATCH = "decision_batch"
    PROJECTION_EFFECT = "projection_effect"
    INVARIANT_RESULT = "invariant_result"
    EXPLANATION = "explanation"
    PROJECTION_WRITE = "projection_write"


@dataclass(frozen=True, slots=True)
class ReplayEntry:
    schema_version: str
    processing_position: int
    event: CanonicalEvent
    observation: AdaptationObservation
    policy: AdaptationPolicy
    batch: AdaptiveDecisionBatch
    state: AdaptiveDecisionState
    committed_at: DomainTime
    fingerprint: str

    def __post_init__(self) -> None:
        if self.schema_version != "adaptive-decision-transaction/v1":
            raise ValueError("unsupported replay entry schema")
        if self.processing_position != self.state.processing_position:
            raise ValueError("replay entry position conflicts with projected state")
        if self.fingerprint != self.state.fingerprint:
            raise ValueError("replay entry fingerprint conflicts with projected state")


@dataclass(frozen=True, slots=True)
class ProcessResult:
    disposition: EvidenceDisposition
    processing_position: int | None
    replay_entry: ReplayEntry | None

    @property
    def batch(self) -> AdaptiveDecisionBatch:
        if self.replay_entry is None:
            raise ValueError("non-admitted evidence has no decision batch")
        return self.replay_entry.batch

    @property
    def state(self) -> AdaptiveDecisionState:
        if self.replay_entry is None:
            raise ValueError("non-admitted evidence has no projected state")
        return self.replay_entry.state

    @property
    def fingerprint(self) -> str:
        if self.replay_entry is None:
            raise ValueError("non-admitted evidence has no state fingerprint")
        return self.replay_entry.fingerprint


@dataclass(frozen=True, slots=True)
class EvidenceReceipt:
    schema_version: str
    event: CanonicalEvent
    observation: AdaptationObservation
    disposition: EvidenceDisposition
    related_position: int | None
    committed_at: DomainTime

    def __post_init__(self) -> None:
        if self.schema_version != "canonical-evidence-receipt/v1":
            raise ValueError("unsupported evidence receipt schema")


def _time(value: DomainTime) -> str:
    return value.identity_payload()


def _parse_time(value: str) -> DomainTime:
    return DomainTime(datetime.fromisoformat(value.replace("Z", "+00:00")))


def _exact(value: ExactDecimal) -> dict[str, str]:
    return value.to_payload()


def _parse_exact(value: Mapping[str, Any]) -> ExactDecimal:
    return ExactDecimal.from_payload(dict(value))


class JournalCodec:
    @staticmethod
    def encode_replay_entry(entry: ReplayEntry) -> dict[str, Any]:
        return {
            "schema": entry.schema_version,
            "processing_position": entry.processing_position,
            "event": JournalCodec._encode_event(entry.event),
            "observation": JournalCodec._encode_observation(entry.observation),
            "policy": JournalCodec._encode_policy(entry.policy),
            "batch": JournalCodec._encode_batch(entry.batch),
            "state": JournalCodec._encode_state(entry.state),
            "committed_at": _time(entry.committed_at),
            "fingerprint": entry.fingerprint,
        }

    @staticmethod
    def decode_replay_entry(payload: Mapping[str, Any]) -> ReplayEntry:
        material = dict(payload)
        schema = material.get("schema")
        if schema == "adaptive-decision-transaction/v0":
            material = JournalCodec._upcast_v0(material)
        elif schema != "adaptive-decision-transaction/v1":
            raise ValueError(f"unsupported replay entry schema {schema!r}")
        return ReplayEntry(
            schema_version="adaptive-decision-transaction/v1",
            processing_position=int(material["processing_position"]),
            event=JournalCodec._decode_event(material["event"]),
            observation=JournalCodec._decode_observation(material["observation"]),
            policy=JournalCodec._decode_policy(material["policy"]),
            batch=JournalCodec._decode_batch(material["batch"]),
            state=JournalCodec._decode_state(material["state"]),
            committed_at=_parse_time(material["committed_at"]),
            fingerprint=str(material["fingerprint"]),
        )

    @staticmethod
    def _upcast_v0(payload: dict[str, Any]) -> dict[str, Any]:
        upgraded = dict(payload)
        upgraded["schema"] = "adaptive-decision-transaction/v1"
        upgraded["fingerprint"] = upgraded.pop("state_fingerprint")
        return upgraded

    @staticmethod
    def _encode_event(event: CanonicalEvent) -> dict[str, Any]:
        return {
            "schema": event.schema,
            "source": {"system": event.source.system, "stream": event.source.stream},
            "source_event_key": event.source_event_key,
            "source_sequence": event.source_sequence,
            "event_time": _time(event.event_time),
            "received_time": _time(event.received_time),
            "correlation_id": event.correlation_id,
            "causation_id": event.causation_id,
            "payload": event.payload,
        }

    @staticmethod
    def _decode_event(payload: Mapping[str, Any]) -> CanonicalEvent:
        source = payload["source"]
        return CanonicalEvent.create(
            schema=str(payload["schema"]),
            source=EventSource(str(source["system"]), str(source["stream"])),
            source_event_key=str(payload["source_event_key"]),
            source_sequence=int(payload["source_sequence"]),
            event_time=_parse_time(str(payload["event_time"])),
            received_time=_parse_time(str(payload["received_time"])),
            correlation_id=str(payload["correlation_id"]),
            causation_id=payload["causation_id"],
            payload=payload["payload"],
        )

    @staticmethod
    def _encode_confirmation(value: ConfirmationEvidence) -> dict[str, Any]:
        return {
            "schema_version": value.schema_version,
            "state": value.state.value,
            "observation_id": value.observation_id,
            "decision_time": _time(value.decision_time),
        }

    @staticmethod
    def _decode_confirmation(payload: Mapping[str, Any]) -> ConfirmationEvidence:
        return ConfirmationEvidence(
            schema_version=str(payload["schema_version"]),
            state=AdaptationState(str(payload["state"])),
            observation_id=str(payload["observation_id"]),
            decision_time=_parse_time(str(payload["decision_time"])),
        )

    @staticmethod
    def _encode_prior(value: PriorDecisionEvidence | None) -> dict[str, Any] | None:
        if value is None:
            return None
        return {
            "state": value.state.value,
            "decision_id": value.decision_id,
            "decision_time": _time(value.decision_time),
        }

    @staticmethod
    def _decode_prior(payload: Mapping[str, Any] | None) -> PriorDecisionEvidence | None:
        if payload is None:
            return None
        return PriorDecisionEvidence(
            state=AdaptationState(str(payload["state"])),
            decision_id=str(payload["decision_id"]),
            decision_time=_parse_time(str(payload["decision_time"])),
        )

    @staticmethod
    def _encode_observation(value: AdaptationObservation) -> dict[str, Any]:
        return {
            "schema_version": value.schema_version,
            "source": {"system": value.source.system, "stream": value.source.stream},
            "event_time": _time(value.event_time),
            "window_start": _time(value.window_start),
            "window_end": _time(value.window_end),
            "complete": value.complete,
            "quality": value.quality.value,
            "sequence_start": value.sequence_start,
            "sequence_end": value.sequence_end,
            "expected_count": value.expected_count,
            "observed_count": value.observed_count,
            "confirmations": [
                JournalCodec._encode_confirmation(item) for item in value.confirmations
            ],
            "prior_decision": JournalCodec._encode_prior(value.prior_decision),
            "trend": _exact(value.trend),
            "volatility": _exact(value.volatility),
            "reference_price": _exact(value.reference_price),
        }

    @staticmethod
    def _decode_observation(payload: Mapping[str, Any]) -> AdaptationObservation:
        source = payload["source"]
        return AdaptationObservation(
            schema_version=str(payload["schema_version"]),
            source=EventSource(str(source["system"]), str(source["stream"])),
            event_time=_parse_time(str(payload["event_time"])),
            window_start=_parse_time(str(payload["window_start"])),
            window_end=_parse_time(str(payload["window_end"])),
            complete=bool(payload["complete"]),
            quality=EvidenceQuality(str(payload["quality"])),
            sequence_start=int(payload["sequence_start"]),
            sequence_end=int(payload["sequence_end"]),
            expected_count=int(payload["expected_count"]),
            observed_count=int(payload["observed_count"]),
            confirmations=tuple(
                JournalCodec._decode_confirmation(item) for item in payload["confirmations"]
            ),
            prior_decision=JournalCodec._decode_prior(payload["prior_decision"]),
            trend=_parse_exact(payload["trend"]),
            volatility=_parse_exact(payload["volatility"]),
            reference_price=_parse_exact(payload["reference_price"]),
        )

    @staticmethod
    def _encode_policy(value: AdaptationPolicy) -> dict[str, Any]:
        return {
            "schema_version": value.schema_version,
            "observation_window_us": int(value.observation_window.total_seconds() * 1_000_000),
            "maximum_observation_age_us": int(
                value.maximum_observation_age.total_seconds() * 1_000_000
            ),
            "trend_threshold": _exact(value.trend_threshold),
            "high_volatility_threshold": _exact(value.high_volatility_threshold),
            "confirmation_count": value.confirmation_count,
            "hysteresis": _exact(value.hysteresis),
            "minimum_epoch_residence_us": int(
                value.minimum_epoch_residence.total_seconds() * 1_000_000
            ),
            "transition_cooldown_us": int(value.transition_cooldown.total_seconds() * 1_000_000),
            "transition_expiry_us": int(value.transition_expiry.total_seconds() * 1_000_000),
            "maximum_transitions_per_day": value.maximum_transitions_per_day,
            "normal_width": _exact(value.normal_width),
            "high_volatility_width": _exact(value.high_volatility_width),
            "maximum_width": _exact(value.maximum_width),
            "maximum_upward_shift": _exact(value.maximum_upward_shift),
        }

    @staticmethod
    def _decode_policy(payload: Mapping[str, Any]) -> AdaptationPolicy:
        return AdaptationPolicy(
            schema_version=str(payload["schema_version"]),
            observation_window=timedelta(microseconds=int(payload["observation_window_us"])),
            maximum_observation_age=timedelta(
                microseconds=int(payload["maximum_observation_age_us"])
            ),
            trend_threshold=_parse_exact(payload["trend_threshold"]),
            high_volatility_threshold=_parse_exact(payload["high_volatility_threshold"]),
            confirmation_count=int(payload["confirmation_count"]),
            hysteresis=_parse_exact(payload["hysteresis"]),
            minimum_epoch_residence=timedelta(
                microseconds=int(payload["minimum_epoch_residence_us"])
            ),
            transition_cooldown=timedelta(microseconds=int(payload["transition_cooldown_us"])),
            transition_expiry=timedelta(microseconds=int(payload["transition_expiry_us"])),
            maximum_transitions_per_day=int(payload["maximum_transitions_per_day"]),
            normal_width=_parse_exact(payload["normal_width"]),
            high_volatility_width=_parse_exact(payload["high_volatility_width"]),
            maximum_width=_parse_exact(payload["maximum_width"]),
            maximum_upward_shift=_parse_exact(payload["maximum_upward_shift"]),
        )

    @staticmethod
    def _encode_decision(value: AdaptationDecision) -> dict[str, Any]:
        return {
            "schema_version": value.schema_version,
            "policy_id": value.policy_id,
            "observation_id": value.observation_id,
            "decision_time": _time(value.decision_time),
            "state": value.state.value,
            "intent": value.intent.value,
            "reason": value.reason,
            "permits_exposure_increasing_buy": value.permits_exposure_increasing_buy,
            "requested_bound_shift": (
                _exact(value.requested_bound_shift)
                if value.requested_bound_shift is not None
                else None
            ),
        }

    @staticmethod
    def _decode_decision(payload: Mapping[str, Any]) -> AdaptationDecision:
        shift = payload["requested_bound_shift"]
        return AdaptationDecision(
            schema_version=str(payload["schema_version"]),
            policy_id=str(payload["policy_id"]),
            observation_id=str(payload["observation_id"]),
            decision_time=_parse_time(str(payload["decision_time"])),
            state=AdaptationState(str(payload["state"])),
            intent=DecisionIntent(str(payload["intent"])),
            reason=str(payload["reason"]),
            permits_exposure_increasing_buy=bool(payload["permits_exposure_increasing_buy"]),
            requested_bound_shift=_parse_exact(shift) if shift is not None else None,
        )

    @staticmethod
    def _encode_batch(value: AdaptiveDecisionBatch) -> dict[str, Any]:
        return {
            "schema_version": value.schema_version,
            "observation_id": value.observation_id,
            "prior_adaptation_state": value.prior_adaptation_state.value,
            "decision": JournalCodec._encode_decision(value.decision),
            "action": value.action.value,
            "gates": [
                {
                    "schema_version": item.schema_version,
                    "name": item.name,
                    "outcome": item.outcome.value,
                    "reason": item.reason,
                }
                for item in value.gates
            ],
            "requested_epoch_cause": value.requested_epoch_cause,
            "posture_effect": value.posture_effect.value,
            "explanation": value.explanation,
            "invariant": {
                "schema_version": value.invariant.schema_version,
                "passed": value.invariant.passed,
                "checks": list(value.invariant.checks),
            },
        }

    @staticmethod
    def _decode_batch(payload: Mapping[str, Any]) -> AdaptiveDecisionBatch:
        invariant = payload["invariant"]
        return AdaptiveDecisionBatch(
            schema_version=str(payload["schema_version"]),
            observation_id=str(payload["observation_id"]),
            prior_adaptation_state=AdaptationState(str(payload["prior_adaptation_state"])),
            decision=JournalCodec._decode_decision(payload["decision"]),
            action=DecisionAction(str(payload["action"])),
            gates=tuple(
                DecisionGate(
                    schema_version=str(item["schema_version"]),
                    name=str(item["name"]),
                    outcome=GateOutcome(str(item["outcome"])),
                    reason=str(item["reason"]),
                )
                for item in payload["gates"]
            ),
            requested_epoch_cause=payload["requested_epoch_cause"],
            posture_effect=SafetyPosture(str(payload["posture_effect"])),
            explanation=str(payload["explanation"]),
            invariant=DecisionInvariant(
                schema_version=str(invariant["schema_version"]),
                passed=bool(invariant["passed"]),
                checks=tuple(str(item) for item in invariant["checks"]),
            ),
        )

    @staticmethod
    def _encode_state(value: AdaptiveDecisionState) -> dict[str, Any]:
        return {
            "schema_version": value.schema_version,
            "processing_position": value.processing_position,
            "adaptation_state": value.adaptation_state.value,
            "safety_posture": value.safety_posture.value,
            "last_decision_id": value.last_decision_id,
            "last_decision_time": (
                _time(value.last_decision_time) if value.last_decision_time is not None else None
            ),
            "replay_fingerprint": value.replay_fingerprint,
        }

    @staticmethod
    def _decode_state(payload: Mapping[str, Any]) -> AdaptiveDecisionState:
        last_decision_time = payload["last_decision_time"]
        return AdaptiveDecisionState(
            schema_version=str(payload["schema_version"]),
            processing_position=int(payload["processing_position"]),
            adaptation_state=AdaptationState(str(payload["adaptation_state"])),
            safety_posture=SafetyPosture(str(payload["safety_posture"])),
            last_decision_id=payload["last_decision_id"],
            last_decision_time=(
                _parse_time(str(last_decision_time)) if last_decision_time is not None else None
            ),
            replay_fingerprint=str(payload["replay_fingerprint"]),
        )


class SQLiteDecisionJournal:
    def __init__(self, path: str | Path, policy: AdaptationPolicy) -> None:
        self._path = Path(path)
        self._policy = policy
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._path)
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS evidence_receipts (
                    receipt_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    receipt_schema TEXT NOT NULL,
                    event_id TEXT NOT NULL,
                    event_schema TEXT NOT NULL,
                    source_system TEXT NOT NULL,
                    source_stream TEXT NOT NULL,
                    source_event_key TEXT NOT NULL,
                    event_time TEXT NOT NULL,
                    disposition TEXT NOT NULL,
                    related_position INTEGER,
                    event_json TEXT NOT NULL,
                    observation_json TEXT NOT NULL,
                    committed_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS admitted_events (
                    processing_position INTEGER PRIMARY KEY,
                    admitted_schema TEXT NOT NULL,
                    event_id TEXT NOT NULL UNIQUE,
                    source_system TEXT NOT NULL,
                    source_stream TEXT NOT NULL,
                    source_event_key TEXT NOT NULL,
                    observation_id TEXT NOT NULL UNIQUE,
                    event_time TEXT NOT NULL,
                    event_json TEXT NOT NULL,
                    observation_json TEXT NOT NULL,
                    UNIQUE(source_system, source_stream, source_event_key)
                );
                CREATE TABLE IF NOT EXISTS decision_batches (
                    processing_position INTEGER PRIMARY KEY
                        REFERENCES admitted_events(processing_position),
                    decision_schema TEXT NOT NULL,
                    batch_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS projection_effects (
                    processing_position INTEGER PRIMARY KEY
                        REFERENCES admitted_events(processing_position),
                    projection_schema TEXT NOT NULL,
                    state_json TEXT NOT NULL,
                    fingerprint TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS invariant_results (
                    processing_position INTEGER PRIMARY KEY
                        REFERENCES admitted_events(processing_position),
                    invariant_schema TEXT NOT NULL,
                    invariant_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS explanations (
                    processing_position INTEGER PRIMARY KEY
                        REFERENCES admitted_events(processing_position),
                    explanation_schema TEXT NOT NULL,
                    explanation TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS journal_entries (
                    processing_position INTEGER PRIMARY KEY
                        REFERENCES admitted_events(processing_position),
                    admitted_schema TEXT NOT NULL,
                    decision_schema TEXT NOT NULL,
                    projection_schema TEXT NOT NULL,
                    invariant_schema TEXT NOT NULL,
                    explanation_schema TEXT NOT NULL,
                    transaction_schema TEXT NOT NULL,
                    replay_json TEXT NOT NULL,
                    fingerprint TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS adaptive_projection (
                    singleton INTEGER PRIMARY KEY CHECK(singleton = 1),
                    projection_schema TEXT NOT NULL,
                    state_json TEXT NOT NULL,
                    fingerprint TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS journal_metadata (
                    singleton INTEGER PRIMARY KEY CHECK(singleton = 1),
                    metadata_schema TEXT NOT NULL,
                    policy_id TEXT NOT NULL,
                    policy_json TEXT NOT NULL
                );
                """
            )
            policy_json = self._json(JournalCodec._encode_policy(self._policy))
            metadata = connection.execute(
                "SELECT policy_id, policy_json FROM journal_metadata WHERE singleton = 1"
            ).fetchone()
            if metadata is None:
                connection.execute(
                    "INSERT INTO journal_metadata VALUES (1, ?, ?, ?)",
                    (
                        "adaptive-journal-metadata/v1",
                        self._policy.policy_id,
                        policy_json,
                    ),
                )
            elif metadata != (self._policy.policy_id, policy_json):
                raise ValueError("journal adaptation policy identity does not match")
            initial = AdaptiveDecisionState.initial()
            connection.execute(
                """
                INSERT OR IGNORE INTO adaptive_projection
                    (singleton, projection_schema, state_json, fingerprint)
                VALUES (1, ?, ?, ?)
                """,
                (
                    initial.schema_version,
                    self._json(JournalCodec._encode_state(initial)),
                    initial.fingerprint,
                ),
            )

    @staticmethod
    def _json(payload: Mapping[str, Any]) -> str:
        return json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)

    @staticmethod
    def _crash(boundary: CrashBoundary | None, current: CrashBoundary) -> None:
        if boundary is current:
            raise RuntimeError(f"injected crash after {current.value}")

    @staticmethod
    def _validate_input(event: CanonicalEvent, observation: AdaptationObservation) -> None:
        payload = event.payload
        mirrored_values = {
            "trend": observation.trend.to_payload(),
            "volatility": observation.volatility.to_payload(),
            "reference_price": observation.reference_price.to_payload(),
        }
        if (
            event.schema != observation.schema_version
            or event.source != observation.source
            or event.event_time != observation.event_time
            or event.source_sequence != observation.sequence_end
            or payload.get("observation_id") != observation.observation_id
            or any(
                key in payload and payload[key] != expected
                for key, expected in mirrored_values.items()
            )
        ):
            raise ValueError("canonical event and observation evidence do not agree")

    def process(
        self,
        event: CanonicalEvent,
        observation: AdaptationObservation,
        *,
        decision_time: DomainTime,
        committed_at: DomainTime,
        crash_after: CrashBoundary | None = None,
    ) -> ProcessResult:
        self._validate_input(event, observation)
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            event_match = connection.execute(
                "SELECT processing_position FROM admitted_events WHERE event_id = ?",
                (event.event_id,),
            ).fetchone()
            observation_match = connection.execute(
                """
                SELECT processing_position FROM admitted_events
                WHERE observation_id = ?
                """,
                (observation.observation_id,),
            ).fetchone()
            source_key_match = connection.execute(
                """
                SELECT processing_position FROM admitted_events
                WHERE source_system = ? AND source_stream = ? AND source_event_key = ?
                """,
                (
                    event.source.system,
                    event.source.stream,
                    event.source_event_key,
                ),
            ).fetchone()
            matched_positions = {
                int(match[0])
                for match in (event_match, observation_match, source_key_match)
                if match is not None
            }
            source_key_conflict = (
                source_key_match is not None and event_match is None and observation_match is None
            )
            if len(matched_positions) > 1 or source_key_conflict:
                self._insert_receipt(
                    connection,
                    event,
                    observation,
                    EvidenceDisposition.CONFLICT,
                    None,
                    committed_at,
                )
                connection.commit()
                return ProcessResult(EvidenceDisposition.CONFLICT, None, None)
            if matched_positions:
                position = matched_positions.pop()
                self._insert_receipt(
                    connection,
                    event,
                    observation,
                    EvidenceDisposition.DUPLICATE,
                    position,
                    committed_at,
                )
                connection.commit()
                return ProcessResult(
                    EvidenceDisposition.DUPLICATE,
                    position,
                    self._entry_at(connection, position),
                )

            latest = connection.execute(
                "SELECT event_json FROM admitted_events ORDER BY processing_position DESC LIMIT 1"
            ).fetchone()
            if latest is not None:
                latest_event = JournalCodec._decode_event(json.loads(latest[0]))
                if event.ordering_key <= latest_event.ordering_key:
                    self._insert_receipt(
                        connection,
                        event,
                        observation,
                        EvidenceDisposition.LATE,
                        None,
                        committed_at,
                    )
                    connection.commit()
                    return ProcessResult(EvidenceDisposition.LATE, None, None)

            prior_state = self._projection(connection)
            position = prior_state.processing_position + 1
            batch, state = evaluate_adaptive_decision(
                policy=self._policy,
                observation=observation,
                decision_time=decision_time,
                prior_state=prior_state,
                processing_position=position,
                admitted_event_fingerprint=event.admission_fingerprint,
            )
            entry = ReplayEntry(
                schema_version="adaptive-decision-transaction/v1",
                processing_position=position,
                event=event,
                observation=observation,
                policy=self._policy,
                batch=batch,
                state=state,
                committed_at=committed_at,
                fingerprint=state.fingerprint,
            )
            event_json = self._json(JournalCodec._encode_event(event))
            observation_json = self._json(JournalCodec._encode_observation(observation))
            batch_json = self._json(JournalCodec._encode_batch(batch))
            state_json = self._json(JournalCodec._encode_state(state))
            invariant_json = self._json(
                {
                    "schema_version": batch.invariant.schema_version,
                    "passed": batch.invariant.passed,
                    "checks": list(batch.invariant.checks),
                }
            )
            self._insert_receipt(
                connection,
                event,
                observation,
                EvidenceDisposition.ADMITTED,
                position,
                committed_at,
            )
            connection.execute(
                """
                INSERT INTO admitted_events VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    position,
                    "canonical-admission/v1",
                    event.event_id,
                    event.source.system,
                    event.source.stream,
                    event.source_event_key,
                    observation.observation_id,
                    _time(event.event_time),
                    event_json,
                    observation_json,
                ),
            )
            self._crash(crash_after, CrashBoundary.ADMITTED_INPUT)
            connection.execute(
                "INSERT INTO decision_batches VALUES (?, ?, ?)",
                (position, batch.schema_version, batch_json),
            )
            self._crash(crash_after, CrashBoundary.DECISION_BATCH)
            connection.execute(
                "INSERT INTO projection_effects VALUES (?, ?, ?, ?)",
                (position, "adaptive-projection-effect/v1", state_json, state.fingerprint),
            )
            self._crash(crash_after, CrashBoundary.PROJECTION_EFFECT)
            connection.execute(
                "INSERT INTO invariant_results VALUES (?, ?, ?)",
                (position, batch.invariant.schema_version, invariant_json),
            )
            self._crash(crash_after, CrashBoundary.INVARIANT_RESULT)
            connection.execute(
                "INSERT INTO explanations VALUES (?, ?, ?)",
                (position, "decision-explanation/v1", batch.explanation),
            )
            self._crash(crash_after, CrashBoundary.EXPLANATION)
            connection.execute(
                """
                INSERT INTO journal_entries VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    position,
                    "canonical-admission/v1",
                    batch.schema_version,
                    "adaptive-projection-effect/v1",
                    batch.invariant.schema_version,
                    "decision-explanation/v1",
                    entry.schema_version,
                    self._json(JournalCodec.encode_replay_entry(entry)),
                    entry.fingerprint,
                ),
            )
            connection.execute(
                """
                UPDATE adaptive_projection
                SET projection_schema = ?, state_json = ?, fingerprint = ?
                WHERE singleton = 1
                """,
                (state.schema_version, state_json, state.fingerprint),
            )
            self._crash(crash_after, CrashBoundary.PROJECTION_WRITE)
            connection.commit()
            return ProcessResult(EvidenceDisposition.ADMITTED, position, entry)
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _insert_receipt(
        self,
        connection: sqlite3.Connection,
        event: CanonicalEvent,
        observation: AdaptationObservation,
        disposition: EvidenceDisposition,
        related_position: int | None,
        committed_at: DomainTime,
    ) -> None:
        connection.execute(
            """
            INSERT INTO evidence_receipts
                (receipt_schema, event_id, event_schema, source_system, source_stream,
                 source_event_key, event_time, disposition, related_position,
                 event_json, observation_json, committed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "canonical-evidence-receipt/v1",
                event.event_id,
                event.schema,
                event.source.system,
                event.source.stream,
                event.source_event_key,
                _time(event.event_time),
                disposition.value,
                related_position,
                self._json(JournalCodec._encode_event(event)),
                self._json(JournalCodec._encode_observation(observation)),
                _time(committed_at),
            ),
        )

    def _projection(self, connection: sqlite3.Connection) -> AdaptiveDecisionState:
        row = connection.execute(
            "SELECT state_json FROM adaptive_projection WHERE singleton = 1"
        ).fetchone()
        if row is None:
            raise RuntimeError("adaptive projection is not initialized")
        return JournalCodec._decode_state(json.loads(row[0]))

    def projection(self) -> AdaptiveDecisionState:
        with self._connect() as connection:
            return self._projection(connection)

    def _entry_at(self, connection: sqlite3.Connection, position: int) -> ReplayEntry:
        row = connection.execute(
            "SELECT replay_json FROM journal_entries WHERE processing_position = ?",
            (position,),
        ).fetchone()
        if row is None:
            raise RuntimeError(f"journal entry {position} is incomplete")
        return JournalCodec.decode_replay_entry(json.loads(row[0]))

    def replay(self) -> tuple[ReplayEntry, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT replay_json FROM journal_entries ORDER BY processing_position"
            ).fetchall()
        return tuple(JournalCodec.decode_replay_entry(json.loads(row[0])) for row in rows)

    def rebuild_projection(self) -> AdaptiveDecisionState:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            rows = connection.execute(
                "SELECT replay_json FROM journal_entries ORDER BY processing_position"
            ).fetchall()
            state = AdaptiveDecisionState.initial()
            for row in rows:
                entry = JournalCodec.decode_replay_entry(json.loads(row[0]))
                self._validate_input(entry.event, entry.observation)
                if entry.processing_position != state.processing_position + 1:
                    raise RuntimeError("journal processing positions are not contiguous")
                batch, rebuilt = evaluate_adaptive_decision(
                    policy=entry.policy,
                    observation=entry.observation,
                    decision_time=entry.batch.decision.decision_time,
                    prior_state=state,
                    processing_position=entry.processing_position,
                    admitted_event_fingerprint=entry.event.admission_fingerprint,
                )
                if batch != entry.batch or rebuilt != entry.state:
                    raise RuntimeError(
                        "journal replay diverged from persisted canonical consequences"
                    )
                state = rebuilt
            connection.execute(
                """
                UPDATE adaptive_projection
                SET projection_schema = ?, state_json = ?, fingerprint = ?
                WHERE singleton = 1
                """,
                (
                    state.schema_version,
                    self._json(JournalCodec._encode_state(state)),
                    state.fingerprint,
                ),
            )
            connection.commit()
            return state
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def evidence_dispositions(self) -> tuple[EvidenceDisposition, ...]:
        return tuple(receipt.disposition for receipt in self.evidence_receipts())

    def evidence_receipts(self) -> tuple[EvidenceReceipt, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT receipt_schema, event_json, observation_json, disposition,
                       related_position, committed_at
                FROM evidence_receipts
                ORDER BY receipt_id
                """
            ).fetchall()
        return tuple(
            EvidenceReceipt(
                schema_version=row[0],
                event=JournalCodec._decode_event(json.loads(row[1])),
                observation=JournalCodec._decode_observation(json.loads(row[2])),
                disposition=EvidenceDisposition(row[3]),
                related_position=row[4],
                committed_at=_parse_time(row[5]),
            )
            for row in rows
        )
