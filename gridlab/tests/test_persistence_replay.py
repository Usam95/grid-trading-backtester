from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json
import sqlite3

import pytest

from gridlab.api.canonical_translation import characterize_legacy_backtest
from gridlab.canonical.adaptation import (
    AdaptationObservation,
    AdaptationState,
    ConfirmationEvidence,
    DecisionIntent,
    EvidenceQuality,
    PriorDecisionEvidence,
)
from gridlab.canonical.configuration import AdaptationPolicy
from gridlab.canonical.decision_path import (
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
from gridlab.persistence.journal import (
    CrashBoundary,
    EvidenceDisposition,
    JournalCodec,
    ProcessResult,
    SQLiteDecisionJournal,
)


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


def observation(
    *,
    event_time: datetime = BOUNDARY,
    trend: str = "0.0000",
    volatility: str = "0.0100",
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
        source=EventSource("fixture", "BTCEUR-1m"),
        event_time=DomainTime(event_time),
        window_start=DomainTime(event_time - timedelta(hours=24)),
        window_end=DomainTime(event_time),
        complete=True,
        quality=EvidenceQuality.ADMITTED,
        sequence_start=1,
        sequence_end=24,
        expected_count=24,
        observed_count=24,
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
        reference_price=exact("100.00", "price"),
    )


def event(evidence: AdaptationObservation, *, source_key: str | None = None) -> CanonicalEvent:
    return CanonicalEvent.create(
        schema="adaptation-observation/v1",
        source=evidence.source,
        source_event_key=source_key or evidence.event_time.identity_payload(),
        source_sequence=evidence.sequence_end,
        event_time=evidence.event_time,
        received_time=DomainTime(evidence.event_time.value + timedelta(seconds=1)),
        correlation_id="correlation:ticket-05",
        causation_id=None,
        payload={"observation_id": evidence.observation_id},
    )


@pytest.mark.parametrize(
    ("evidence", "decision_time", "state", "intent", "action", "posture", "explanation"),
    [
        (
            observation(volatility="0.0300"),
            DomainTime(BOUNDARY),
            AdaptationState.RANGE_HIGH_VOLATILITY,
            DecisionIntent.WIDEN,
            DecisionAction.CLASSIFICATION_ACCEPTED,
            SafetyPosture.NORMAL,
            "classification_accepted",
        ),
        (
            observation(),
            DomainTime(BOUNDARY),
            AdaptationState.RANGE_NORMAL,
            DecisionIntent.SYMMETRIC,
            DecisionAction.NO_ACTION,
            SafetyPosture.NORMAL,
            "threshold_no_action",
        ),
        (
            observation(),
            DomainTime(BOUNDARY + timedelta(minutes=16)),
            AdaptationState.UNCERTAIN,
            DecisionIntent.FROZEN,
            DecisionAction.NO_ACTION,
            SafetyPosture.FROZEN,
            "stale_evidence",
        ),
        (
            observation(trend="-0.0200"),
            DomainTime(BOUNDARY),
            AdaptationState.TREND_DOWN,
            DecisionIntent.REDUCE_ONLY,
            DecisionAction.CLASSIFICATION_ACCEPTED,
            SafetyPosture.REDUCE_ONLY,
            "confirmed_downtrend",
        ),
    ],
)
def test_golden_decisions_persist_and_replay_exactly(
    tmp_path,
    evidence,
    decision_time,
    state,
    intent,
    action,
    posture,
    explanation,
) -> None:
    journal = SQLiteDecisionJournal(tmp_path / "journal.db", policy())

    result = journal.process(
        event(evidence),
        evidence,
        decision_time=decision_time,
        committed_at=DomainTime(decision_time.value + timedelta(seconds=1)),
    )

    assert result.disposition is EvidenceDisposition.ADMITTED
    assert result.processing_position == 1
    assert result.batch.decision.state is state
    assert result.batch.decision.intent is intent
    assert result.batch.action is action
    assert result.batch.posture_effect is posture
    assert result.batch.explanation == explanation
    assert result.batch.invariant.passed is True
    confirmation_gate = next(gate for gate in result.batch.gates if gate.name == "confirmation")
    if state is AdaptationState.UNCERTAIN:
        assert confirmation_gate.outcome.value == "NOT_APPLICABLE"
    if state is AdaptationState.TREND_DOWN:
        assert result.batch.decision.permits_exposure_increasing_buy is False
        assert result.batch.decision.requested_bound_shift is None
        assert result.batch.requested_epoch_cause is None

    original = journal.projection()
    rebuilt = journal.rebuild_projection()
    assert rebuilt == original
    assert rebuilt.fingerprint == result.fingerprint
    assert journal.replay()[0].batch == result.batch


def test_duplicates_and_late_inputs_retain_evidence_without_consequences(tmp_path) -> None:
    journal = SQLiteDecisionJournal(tmp_path / "journal.db", policy())
    first = observation(volatility="0.0300")
    admitted = journal.process(
        event(first),
        first,
        decision_time=DomainTime(BOUNDARY),
        committed_at=DomainTime(BOUNDARY + timedelta(seconds=1)),
    )
    duplicate_event = replace(
        event(first),
        source_event_key="re-enveloped-observation",
        correlation_id="correlation:duplicate-delivery",
        received_time=DomainTime(BOUNDARY + timedelta(seconds=2)),
    )
    duplicate = journal.process(
        duplicate_event,
        first,
        decision_time=DomainTime(BOUNDARY),
        committed_at=DomainTime(BOUNDARY + timedelta(seconds=2)),
    )
    late = observation(event_time=BOUNDARY - timedelta(minutes=1), trend="-0.0200")
    late_result = journal.process(
        event(late, source_key="late-observation"),
        late,
        decision_time=DomainTime(BOUNDARY),
        committed_at=DomainTime(BOUNDARY + timedelta(seconds=3)),
    )
    next_evidence = observation(event_time=BOUNDARY + timedelta(minutes=1))
    next_result = journal.process(
        event(next_evidence),
        next_evidence,
        decision_time=DomainTime(BOUNDARY + timedelta(minutes=1)),
        committed_at=DomainTime(BOUNDARY + timedelta(minutes=1, seconds=1)),
    )

    assert admitted.processing_position == 1
    assert duplicate.disposition is EvidenceDisposition.DUPLICATE
    assert duplicate.processing_position == 1
    assert late_result.disposition is EvidenceDisposition.LATE
    assert late_result.processing_position is None
    assert next_result.processing_position == 2
    assert journal.evidence_dispositions() == (
        EvidenceDisposition.ADMITTED,
        EvidenceDisposition.DUPLICATE,
        EvidenceDisposition.LATE,
        EvidenceDisposition.ADMITTED,
    )
    receipts = journal.evidence_receipts()
    assert receipts[1].event == duplicate_event
    assert receipts[1].observation == first
    assert receipts[2].event == event(late, source_key="late-observation")
    assert receipts[2].observation == late
    assert len(journal.replay()) == 2


@pytest.mark.parametrize("boundary", list(CrashBoundary))
def test_crash_at_each_transaction_boundary_leaves_no_admitted_progress(tmp_path, boundary) -> None:
    database = tmp_path / f"{boundary.value}.db"
    journal = SQLiteDecisionJournal(database, policy())
    evidence = observation(volatility="0.0300")

    with pytest.raises(RuntimeError, match="injected crash"):
        journal.process(
            event(evidence),
            evidence,
            decision_time=DomainTime(BOUNDARY),
            committed_at=DomainTime(BOUNDARY + timedelta(seconds=1)),
            crash_after=boundary,
        )

    assert journal.projection().processing_position == 0
    assert journal.replay() == ()
    assert journal.evidence_dispositions() == ()


def test_canonical_input_is_validated_before_durable_admission(tmp_path) -> None:
    journal = SQLiteDecisionJournal(tmp_path / "journal.db", policy())
    evidence = observation()
    mismatched = replace(event(evidence), source_event_key="different-key")
    mismatched_evidence = replace(
        evidence,
        source=EventSource("fixture", "different-stream"),
    )

    with pytest.raises(ValueError, match="event and observation"):
        journal.process(
            mismatched,
            mismatched_evidence,
            decision_time=DomainTime(BOUNDARY),
            committed_at=DomainTime(BOUNDARY + timedelta(seconds=1)),
        )

    assert journal.evidence_dispositions() == ()
    assert journal.projection().processing_position == 0


def test_persisted_records_have_schema_identity_and_v0_upcasts_to_v1(tmp_path) -> None:
    database = tmp_path / "journal.db"
    journal = SQLiteDecisionJournal(database, policy())
    evidence = observation()
    result = journal.process(
        event(evidence),
        evidence,
        decision_time=DomainTime(BOUNDARY),
        committed_at=DomainTime(BOUNDARY + timedelta(seconds=1)),
    )

    with sqlite3.connect(database) as connection:
        schemas = connection.execute(
            """
            SELECT admitted_schema, decision_schema, projection_schema,
                   invariant_schema, explanation_schema, transaction_schema
            FROM journal_entries
            """
        ).fetchone()
    assert schemas == (
        "canonical-admission/v1",
        "adaptive-decision-batch/v1",
        "adaptive-projection-effect/v1",
        "decision-invariant/v1",
        "decision-explanation/v1",
        "adaptive-decision-transaction/v1",
    )

    current = JournalCodec.encode_replay_entry(journal.replay()[0])
    legacy = dict(current)
    legacy["schema"] = "adaptive-decision-transaction/v0"
    legacy["state_fingerprint"] = legacy.pop("fingerprint")
    decoded = JournalCodec.decode_replay_entry(legacy)
    assert decoded == result.replay_entry
    assert JournalCodec.encode_replay_entry(decoded)["schema"] == (
        "adaptive-decision-transaction/v1"
    )


def test_journal_rejects_changed_immutable_policy_context(tmp_path) -> None:
    database = tmp_path / "journal.db"
    SQLiteDecisionJournal(database, policy())

    with pytest.raises(ValueError, match="policy identity"):
        SQLiteDecisionJournal(
            database,
            replace(policy(), trend_threshold=exact("0.0200")),
        )


def test_prior_decision_evidence_mismatch_fails_closed(tmp_path) -> None:
    journal = SQLiteDecisionJournal(tmp_path / "journal.db", policy())
    first = observation(volatility="0.0300")
    admitted = journal.process(
        event(first),
        first,
        decision_time=DomainTime(BOUNDARY),
        committed_at=DomainTime(BOUNDARY + timedelta(seconds=1)),
    )
    second_time = BOUNDARY + timedelta(minutes=1)
    second = replace(
        observation(event_time=second_time, trend="0.0200"),
        prior_decision=PriorDecisionEvidence(
            state=AdaptationState.RANGE_NORMAL,
            decision_id="sha256:" + "9" * 64,
            decision_time=DomainTime(BOUNDARY),
        ),
    )

    result = journal.process(
        event(second),
        second,
        decision_time=DomainTime(second_time),
        committed_at=DomainTime(second_time + timedelta(seconds=1)),
    )

    assert admitted.state.adaptation_state is AdaptationState.RANGE_HIGH_VOLATILITY
    assert result.batch.decision.state is AdaptationState.UNCERTAIN
    assert result.batch.explanation == "prior_state_evidence_mismatch"
    assert result.state.safety_posture is SafetyPosture.FROZEN


def test_conflicting_deduplication_identities_retain_evidence_without_progress(
    tmp_path,
) -> None:
    journal = SQLiteDecisionJournal(tmp_path / "journal.db", policy())
    first = observation(volatility="0.0300")
    journal.process(
        event(first, source_key="first"),
        first,
        decision_time=DomainTime(BOUNDARY),
        committed_at=DomainTime(BOUNDARY + timedelta(seconds=1)),
    )
    second_time = BOUNDARY + timedelta(minutes=1)
    second = observation(event_time=second_time)
    journal.process(
        event(second, source_key="second"),
        second,
        decision_time=DomainTime(second_time),
        committed_at=DomainTime(second_time + timedelta(seconds=1)),
    )
    conflict_event = replace(
        event(first, source_key="second"),
        received_time=DomainTime(second_time + timedelta(seconds=2)),
    )

    result = journal.process(
        conflict_event,
        first,
        decision_time=DomainTime(second_time),
        committed_at=DomainTime(second_time + timedelta(seconds=2)),
    )

    assert result.disposition is EvidenceDisposition.CONFLICT
    assert result.processing_position is None
    assert journal.projection().processing_position == 2
    assert journal.evidence_receipts()[-1].event == conflict_event


def test_replay_detects_admitted_event_envelope_corruption(tmp_path) -> None:
    database = tmp_path / "journal.db"
    journal = SQLiteDecisionJournal(database, policy())
    evidence = observation(volatility="0.0300")
    journal.process(
        event(evidence),
        evidence,
        decision_time=DomainTime(BOUNDARY),
        committed_at=DomainTime(BOUNDARY + timedelta(seconds=1)),
    )
    with sqlite3.connect(database) as connection:
        payload = json.loads(
            connection.execute("SELECT replay_json FROM journal_entries").fetchone()[0]
        )
        payload["event"]["received_time"] = "2025-01-02T00:00:09Z"
        connection.execute(
            "UPDATE journal_entries SET replay_json = ?",
            (json.dumps(payload, separators=(",", ":"), sort_keys=True),),
        )

    with pytest.raises(RuntimeError, match="replay diverged"):
        journal.rebuild_projection()


def test_source_key_collision_with_different_evidence_is_a_conflict(tmp_path) -> None:
    journal = SQLiteDecisionJournal(tmp_path / "journal.db", policy())
    first = observation()
    journal.process(
        event(first, source_key="shared-source-key"),
        first,
        decision_time=DomainTime(BOUNDARY),
        committed_at=DomainTime(BOUNDARY + timedelta(seconds=1)),
    )
    different_time = BOUNDARY + timedelta(minutes=1)
    different = observation(event_time=different_time, trend="-0.0200")

    result = journal.process(
        event(different, source_key="shared-source-key"),
        different,
        decision_time=DomainTime(different_time),
        committed_at=DomainTime(different_time + timedelta(seconds=1)),
    )

    assert result.disposition is EvidenceDisposition.CONFLICT
    assert journal.projection().processing_position == 1
    assert journal.evidence_receipts()[-1].observation == different


def test_ticket04_canonical_event_is_admitted_without_payload_reshaping(tmp_path) -> None:
    canonical = characterize_legacy_backtest(
        symbol="BTCEUR",
        decision_time=DomainTime(BOUNDARY),
    )
    journal = SQLiteDecisionJournal(
        tmp_path / "journal.db",
        canonical.configuration.adaptation_policy,
    )

    result = journal.process(
        canonical.event,
        canonical.observation,
        decision_time=DomainTime(BOUNDARY),
        committed_at=DomainTime(BOUNDARY + timedelta(seconds=1)),
    )

    assert result.disposition is EvidenceDisposition.ADMITTED
    assert result.batch.observation_id == canonical.observation.observation_id


def test_canonical_decision_path_rejects_invalid_material(tmp_path) -> None:
    journal = SQLiteDecisionJournal(tmp_path / "journal.db", policy())
    evidence = observation(volatility="0.0300")
    result = journal.process(
        event(evidence),
        evidence,
        decision_time=DomainTime(BOUNDARY),
        committed_at=DomainTime(BOUNDARY + timedelta(seconds=1)),
    )
    batch = result.batch
    state = result.state
    initial = AdaptiveDecisionState.initial()

    with pytest.raises(ValueError, match="gate schema"):
        DecisionGate("adaptive-decision-gate/v2", "classification", GateOutcome.PASSED, "ok")
    with pytest.raises(ValueError, match="name and reason"):
        DecisionGate("adaptive-decision-gate/v1", "", GateOutcome.PASSED, "ok")
    with pytest.raises(ValueError, match="invariant schema"):
        DecisionInvariant("decision-invariant/v2", True, ("check",))
    with pytest.raises(ValueError, match="checks are required"):
        DecisionInvariant("decision-invariant/v1", True, ())
    with pytest.raises(ValueError, match="state schema"):
        replace(state, schema_version="adaptive-decision-state/v2")
    with pytest.raises(ValueError, match="non-negative"):
        replace(state, processing_position=-1)
    with pytest.raises(ValueError, match="initial decision state"):
        replace(
            initial,
            last_decision_id=state.last_decision_id,
            last_decision_time=state.last_decision_time,
        )
    with pytest.raises(ValueError, match="requires decision evidence"):
        replace(state, last_decision_id=None, last_decision_time=None)
    with pytest.raises(ValueError, match="fingerprint is invalid"):
        replace(state, replay_fingerprint="invalid")
    with pytest.raises(ValueError, match="batch schema"):
        replace(batch, schema_version="adaptive-decision-batch/v2")
    with pytest.raises(ValueError, match="observation identity"):
        replace(batch, observation_id="sha256:" + "0" * 64)
    with pytest.raises(ValueError, match="gates and explanation"):
        replace(batch, gates=())
    failed = DecisionInvariant("decision-invariant/v1", False, ("failed",))
    with pytest.raises(ValueError, match="failed decision invariant"):
        replace(batch, invariant=failed)
    with pytest.raises(ValueError, match="no-action"):
        replace(
            batch,
            action=DecisionAction.NO_ACTION,
            requested_epoch_cause=evidence.observation_id,
        )
    assert batch.batch_id.startswith("sha256:")
    with pytest.raises(ValueError, match="immediately follow"):
        evaluate_adaptive_decision(
            policy=policy(),
            observation=evidence,
            decision_time=DomainTime(BOUNDARY),
            prior_state=initial,
            processing_position=2,
            admitted_event_fingerprint=event(evidence).admission_fingerprint,
        )
    with pytest.raises(ValueError, match="event fingerprint"):
        evaluate_adaptive_decision(
            policy=policy(),
            observation=evidence,
            decision_time=DomainTime(BOUNDARY),
            prior_state=initial,
            processing_position=1,
            admitted_event_fingerprint="invalid",
        )


def test_persistence_reader_rejects_invalid_or_incomplete_material(tmp_path) -> None:
    database = tmp_path / "journal.db"
    journal = SQLiteDecisionJournal(database, policy())
    evidence = observation()
    result = journal.process(
        event(evidence),
        evidence,
        decision_time=DomainTime(BOUNDARY),
        committed_at=DomainTime(BOUNDARY + timedelta(seconds=1)),
    )
    entry = result.replay_entry
    assert entry is not None
    receipt = journal.evidence_receipts()[0]

    with pytest.raises(ValueError, match="replay entry schema"):
        replace(entry, schema_version="adaptive-decision-transaction/v2")
    with pytest.raises(ValueError, match="position conflicts"):
        replace(entry, processing_position=2)
    with pytest.raises(ValueError, match="fingerprint conflicts"):
        replace(entry, fingerprint="sha256:" + "0" * 64)
    empty_result = ProcessResult(EvidenceDisposition.LATE, None, None)
    for attribute in ("batch", "state", "fingerprint"):
        with pytest.raises(ValueError, match="non-admitted"):
            getattr(empty_result, attribute)
    with pytest.raises(ValueError, match="receipt schema"):
        replace(receipt, schema_version="canonical-evidence-receipt/v2")
    with pytest.raises(ValueError, match="unsupported replay entry schema"):
        JournalCodec.decode_replay_entry({"schema": "adaptive-decision-transaction/v9"})
    prior_payload = JournalCodec._encode_prior(
        PriorDecisionEvidence(
            state=AdaptationState.RANGE_NORMAL,
            decision_id="sha256:" + "1" * 64,
            decision_time=DomainTime(BOUNDARY),
        )
    )
    assert JournalCodec._decode_prior(prior_payload) is not None

    SQLiteDecisionJournal(database, policy())
    with journal._connect() as connection:
        with pytest.raises(RuntimeError, match="entry 999 is incomplete"):
            journal._entry_at(connection, 999)
        connection.execute("DELETE FROM adaptive_projection")
    with pytest.raises(RuntimeError, match="projection is not initialized"):
        journal.projection()


def test_replay_rejects_noncontiguous_processing_positions(tmp_path) -> None:
    database = tmp_path / "journal.db"
    journal = SQLiteDecisionJournal(database, policy())
    evidence = observation()
    journal.process(
        event(evidence),
        evidence,
        decision_time=DomainTime(BOUNDARY),
        committed_at=DomainTime(BOUNDARY + timedelta(seconds=1)),
    )
    with sqlite3.connect(database) as connection:
        payload = json.loads(
            connection.execute("SELECT replay_json FROM journal_entries").fetchone()[0]
        )
        payload["processing_position"] = 2
        payload["state"]["processing_position"] = 2
        connection.execute(
            "UPDATE journal_entries SET replay_json = ?",
            (json.dumps(payload, separators=(",", ":"), sort_keys=True),),
        )

    with pytest.raises(RuntimeError, match="positions are not contiguous"):
        journal.rebuild_projection()
