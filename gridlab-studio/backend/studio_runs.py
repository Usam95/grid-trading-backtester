"""Durable repository for typed Studio backtest resources."""

from __future__ import annotations

import json
import os
import sqlite3
from collections.abc import Iterator
from pathlib import Path
from types import TracebackType

from backend.schemas import StudioBacktestRun


DEFAULT_DATABASE = Path(__file__).resolve().parent.parent / ".studio" / "studio.sqlite3"


class SqliteStudioRunStore:
    """Small durable store owned by the local research service, not the browser."""

    def __init__(self, database: Path) -> None:
        database.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(database)
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS studio_backtest_runs (
                run_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                payload_json TEXT NOT NULL
            )
            """
        )

    def save(self, run: StudioBacktestRun) -> None:
        self._connection.execute(
            "INSERT INTO studio_backtest_runs VALUES (?, ?, ?)",
            (run.id, run.created_at.isoformat(), run.model_dump_json()),
        )
        self._connection.commit()

    def get(self, run_id: str) -> StudioBacktestRun | None:
        row = self._connection.execute(
            "SELECT payload_json FROM studio_backtest_runs WHERE run_id = ?",
            (run_id,),
        ).fetchone()
        if row is None:
            return None
        return StudioBacktestRun.model_validate(json.loads(row[0]))

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> SqliteStudioRunStore:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()


def studio_run_store() -> Iterator[SqliteStudioRunStore]:
    """Provide one short-lived connection to the configured local research store."""
    configured = os.environ.get("GRIDLAB_STUDIO_DATABASE")
    path = Path(configured) if configured else DEFAULT_DATABASE
    with SqliteStudioRunStore(path) as store:
        yield store
