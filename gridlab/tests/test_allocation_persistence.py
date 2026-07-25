from __future__ import annotations

from datetime import datetime, timezone
import sqlite3

import pytest

from gridlab.accounting.allocation import (
    AllocationProjection,
    allocation_funding_batch,
    apply_posting_batch,
    spot_fill_batch,
)
from gridlab.canonical.events import DomainTime
from gridlab.canonical.values import ExactDecimal
from gridlab.persistence.allocation_journal import (
    AccountingCrashBoundary,
    SQLiteAllocationJournal,
)


UTC = timezone.utc
EVENT_TIME = DomainTime(datetime(2025, 1, 2, tzinfo=UTC))
RUN_ID = "run:ticket-07"
ALLOCATION_ID = "allocation:ticket-07"
EPOCH_ID = "epoch:one"


def exact(value: str) -> ExactDecimal:
    return ExactDecimal.parse(value, kind="native_asset_quantity")


def funding():
    return allocation_funding_batch(
        run_id=RUN_ID,
        allocation_id=ALLOCATION_ID,
        grid_plan_epoch_id=EPOCH_ID,
        source_event_id="event:funding",
        event_time=EVENT_TIME,
        processing_position=1,
        assets={"EUR": exact("1000.00"), "BNB": exact("1.00000000")},
    )


def fill():
    return spot_fill_batch(
        run_id=RUN_ID,
        allocation_id=ALLOCATION_ID,
        grid_plan_epoch_id=EPOCH_ID,
        source_event_id="event:fill",
        event_time=EVENT_TIME,
        processing_position=2,
        side="BUY",
        base_asset="BTC",
        quote_asset="EUR",
        base_quantity=exact("1.00000000"),
        quote_quantity=exact("100.00"),
        fee_asset="BNB",
        fee_quantity=exact("0.01000000"),
        order_id="order:buy",
        fill_id="fill:buy",
        lot_id="lot:buy",
        origin_epoch_id=EPOCH_ID,
    )


def test_atomic_journal_batch_rolls_back_on_injected_crash(tmp_path) -> None:
    journal = SQLiteAllocationJournal(tmp_path / "allocation.db", RUN_ID, ALLOCATION_ID)
    journal.append(funding())
    before = journal.projection()

    with pytest.raises(RuntimeError, match="injected crash"):
        journal.append(fill(), crash_after=AccountingCrashBoundary.BATCH_WRITE)

    assert journal.projection() == before
    assert journal.replay() == (funding(),)


def test_exact_replay_projection_rebuild_and_fingerprint_are_deterministic(tmp_path) -> None:
    first = SQLiteAllocationJournal(tmp_path / "first.db", RUN_ID, ALLOCATION_ID)
    second = SQLiteAllocationJournal(tmp_path / "second.db", RUN_ID, ALLOCATION_ID)

    for journal in (first, second):
        journal.append(funding())
        journal.append(fill())

    expected = apply_posting_batch(
        apply_posting_batch(
            AllocationProjection.initial(RUN_ID, ALLOCATION_ID),
            funding(),
        ),
        fill(),
    )
    assert first.replay() == (funding(), fill())
    assert first.projection() == expected
    assert first.rebuild_projection() == expected
    assert first.projection().fingerprint == second.projection().fingerprint
    assert first.journal_fingerprint == second.journal_fingerprint


def test_journal_rejects_noncontiguous_positions_without_partial_write(tmp_path) -> None:
    journal = SQLiteAllocationJournal(tmp_path / "allocation.db", RUN_ID, ALLOCATION_ID)
    misplaced = fill()

    with pytest.raises(ValueError, match="processing position"):
        journal.append(misplaced)

    assert journal.projection() == AllocationProjection.initial(RUN_ID, ALLOCATION_ID)
    assert journal.replay() == ()


def test_journal_rejects_identity_and_projection_corruption(tmp_path) -> None:
    path = tmp_path / "allocation.db"
    journal = SQLiteAllocationJournal(path, RUN_ID, ALLOCATION_ID)
    journal.append(funding())
    assert SQLiteAllocationJournal(path, RUN_ID, ALLOCATION_ID).projection() == journal.projection()

    with pytest.raises(ValueError, match="identity"):
        SQLiteAllocationJournal(path, "run:other", ALLOCATION_ID)

    with sqlite3.connect(path) as connection:
        connection.execute("UPDATE allocation_projection SET fingerprint = 'sha256:corrupt'")
    with pytest.raises(RuntimeError, match="snapshot fingerprint"):
        journal.projection()


def test_journal_detects_missing_projection_and_replay_divergence(tmp_path) -> None:
    missing_path = tmp_path / "missing.db"
    missing = SQLiteAllocationJournal(missing_path, RUN_ID, ALLOCATION_ID)
    with sqlite3.connect(missing_path) as connection:
        connection.execute("DELETE FROM allocation_projection")
    with pytest.raises(RuntimeError, match="not initialized"):
        missing.projection()

    replay_path = tmp_path / "replay.db"
    replay = SQLiteAllocationJournal(replay_path, RUN_ID, ALLOCATION_ID)
    replay.append(funding())
    with sqlite3.connect(replay_path) as connection:
        connection.execute("UPDATE posting_batches SET projection_fingerprint = 'sha256:corrupt'")
    with pytest.raises(RuntimeError, match="replay fingerprint"):
        replay.rebuild_projection()
