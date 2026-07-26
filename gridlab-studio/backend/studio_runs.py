"""Durable repository for typed Studio backtest resources."""

from __future__ import annotations

import json
import os
import sqlite3
from collections.abc import Iterator
from pathlib import Path
from types import TracebackType

from backend.schemas import ResearchJob, StudioBacktestRun


DEFAULT_DATABASE = Path(__file__).resolve().parent.parent / ".studio" / "studio.sqlite3"


class SqliteStudioRunStore:
    """Small durable store owned by the local research service, not the browser."""

    def __init__(self, database: Path) -> None:
        self.database = database
        database.parent.mkdir(parents=True, exist_ok=True)
        # FastAPI may enter and exit a sync generator dependency on different
        # worker threads; this connection is still request-scoped.
        self._connection = sqlite3.connect(database, check_same_thread=False)
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS studio_backtest_runs (
                run_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                payload_json TEXT NOT NULL
            )
            """
        )
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS studio_research_jobs (
                job_id TEXT PRIMARY KEY,
                updated_at TEXT NOT NULL,
                payload_json TEXT NOT NULL
            )
            """
        )
        self._connection.commit()

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

    def save_job(self, job: ResearchJob) -> None:
        self._connection.execute(
            "INSERT OR REPLACE INTO studio_research_jobs VALUES (?, ?, ?)",
            (job.id, job.updated_at.isoformat(), job.model_dump_json()),
        )
        self._connection.commit()

    def get_job(self, job_id: str) -> ResearchJob | None:
        row = self._connection.execute(
            "SELECT payload_json FROM studio_research_jobs WHERE job_id = ?", (job_id,)
        ).fetchone()
        return None if row is None else ResearchJob.model_validate(json.loads(row[0]))

    def list_jobs(self) -> list[ResearchJob]:
        rows = self._connection.execute("SELECT payload_json FROM studio_research_jobs ORDER BY updated_at DESC").fetchall()
        return [ResearchJob.model_validate(json.loads(row[0])) for row in rows]

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
