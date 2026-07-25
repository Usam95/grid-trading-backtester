from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import sqlite3
from typing import Any

from gridlab.canonical.epoch_transition import (
    EpochTransitionFacts,
    TransitionCrashBoundary,
    evaluate_epoch_transition,
)


@dataclass(frozen=True, slots=True)
class TransitionJournalEntry:
    processing_position: int
    fingerprint: str
    payload: dict[str, Any]


class SQLiteTransitionJournal:
    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._connect().close()
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS epoch_transition_journal (
                    processing_position INTEGER PRIMARY KEY,
                    fingerprint TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._path)

    def process(
        self,
        facts: EpochTransitionFacts,
        *,
        crash_boundary: TransitionCrashBoundary | None = None,
    ) -> TransitionJournalEntry:
        evaluation = evaluate_epoch_transition(facts)
        payload = evaluation.to_payload()
        if crash_boundary is not None:
            raise RuntimeError(f"crash injected at {crash_boundary.value}")
        with self._connect() as connection:
            position = connection.execute(
                "SELECT COALESCE(MAX(processing_position), 0) + 1 FROM epoch_transition_journal"
            ).fetchone()[0]
            connection.execute(
                """
                INSERT INTO epoch_transition_journal (processing_position, fingerprint, payload_json)
                VALUES (?, ?, ?)
                """,
                (position, evaluation.fingerprint, json.dumps(payload, sort_keys=True)),
            )
        return TransitionJournalEntry(
            processing_position=position,
            fingerprint=evaluation.fingerprint,
            payload=payload,
        )

    def replay(self) -> tuple[TransitionJournalEntry, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT processing_position, fingerprint, payload_json
                FROM epoch_transition_journal
                ORDER BY processing_position
                """
            ).fetchall()
        return tuple(
            TransitionJournalEntry(
                processing_position=int(position),
                fingerprint=str(fingerprint),
                payload=json.loads(payload_json),
            )
            for position, fingerprint, payload_json in rows
        )

    def rebuild_projection(self) -> dict[str, Any] | None:
        entries = self.replay()
        return None if not entries else entries[-1].payload
