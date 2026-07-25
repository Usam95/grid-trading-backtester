from __future__ import annotations

from dataclasses import fields
from decimal import Decimal
from enum import Enum
import json
from pathlib import Path
import sqlite3
from typing import Any, Mapping

from gridlab.accounting.allocation import (
    Account,
    AccountBalance,
    AllocationProjection,
    AssetPosting,
    CompletedCycle,
    FillEvidence,
    FillRecord,
    InvariantResult,
    InventoryLot,
    ManagedOrderEvidence,
    ManagedOrderRecord,
    ManagedOrderState,
    PairObligation,
    PostingBatch,
    PostingCause,
    ResidualInventory,
    ReservationRecord,
    ReservationState,
    apply_posting_batch,
)
from gridlab.canonical._identity import content_identity
from gridlab.canonical.events import DomainTime
from gridlab.canonical.values import ExactDecimal


class AccountingCrashBoundary(str, Enum):
    BATCH_WRITE = "batch_write"


def _encode_posting(posting: AssetPosting) -> dict[str, Any]:
    return {
        field.name: (
            posting.amount.to_payload()
            if field.name == "amount"
            else posting.event_time.identity_payload()
            if field.name == "event_time"
            else value.value
            if isinstance((value := getattr(posting, field.name)), Enum)
            else value
        )
        for field in fields(posting)
    }


def _decode_posting(payload: Mapping[str, Any]) -> AssetPosting:
    return AssetPosting(
        schema_version=str(payload["schema_version"]),
        run_id=str(payload["run_id"]),
        allocation_id=str(payload["allocation_id"]),
        grid_plan_epoch_id=str(payload["grid_plan_epoch_id"]),
        native_asset=str(payload["native_asset"]),
        account=Account(str(payload["account"])),
        amount=ExactDecimal.from_payload(dict(payload["amount"])),
        cause=PostingCause(str(payload["cause"])),
        source_event_id=str(payload["source_event_id"]),
        event_time=_decode_time(str(payload["event_time"])),
        processing_position=int(payload["processing_position"]),
        transition_id=payload["transition_id"],
        order_id=payload["order_id"],
        fill_id=payload["fill_id"],
        cycle_id=payload["cycle_id"],
        obligation_id=payload["obligation_id"],
        reservation_state=(
            ReservationState(str(payload["reservation_state"]))
            if payload["reservation_state"] is not None
            else None
        ),
        lot_id=payload["lot_id"],
        origin_epoch_id=payload["origin_epoch_id"],
        paired_lot_id=payload["paired_lot_id"],
    )


def _encode_batch(batch: PostingBatch) -> dict[str, Any]:
    return {
        "schema_version": batch.schema_version,
        "run_id": batch.run_id,
        "allocation_id": batch.allocation_id,
        "source_event_id": batch.source_event_id,
        "event_time": batch.event_time.identity_payload(),
        "processing_position": batch.processing_position,
        "postings": [_encode_posting(item) for item in batch.postings],
        "managed_order_evidence": (
            {
                field.name: (
                    value.to_payload()
                    if isinstance(
                        (value := getattr(batch.managed_order_evidence, field.name)), ExactDecimal
                    )
                    else value.value
                    if isinstance(value, Enum)
                    else value
                )
                for field in fields(batch.managed_order_evidence)
            }
            if batch.managed_order_evidence is not None
            else None
        ),
        "fill_evidence": (
            {
                field.name: (
                    value.to_payload()
                    if isinstance((value := getattr(batch.fill_evidence, field.name)), ExactDecimal)
                    else value.value
                    if isinstance(value, Enum)
                    else value
                )
                for field in fields(batch.fill_evidence)
            }
            if batch.fill_evidence is not None
            else None
        ),
    }


def _decode_time(value: str) -> DomainTime:
    from datetime import datetime

    return DomainTime(datetime.fromisoformat(value.replace("Z", "+00:00")))


def _decode_batch(payload: Mapping[str, Any]) -> PostingBatch:
    order_payload = payload.get("managed_order_evidence")
    fill_payload = payload.get("fill_evidence")
    return PostingBatch(
        schema_version=str(payload["schema_version"]),
        run_id=str(payload["run_id"]),
        allocation_id=str(payload["allocation_id"]),
        source_event_id=str(payload["source_event_id"]),
        event_time=_decode_time(str(payload["event_time"])),
        processing_position=int(payload["processing_position"]),
        postings=tuple(_decode_posting(item) for item in payload["postings"]),
        managed_order_evidence=(
            ManagedOrderEvidence(
                order_id=str(order_payload["order_id"]),
                grid_plan_epoch_id=str(order_payload["grid_plan_epoch_id"]),
                rung_id=str(order_payload["rung_id"]),
                side=str(order_payload["side"]),
                state=ManagedOrderState(str(order_payload["state"])),
                base_asset=str(order_payload["base_asset"]),
                quote_asset=str(order_payload["quote_asset"]),
                requested_base_quantity=ExactDecimal.from_payload(
                    dict(order_payload["requested_base_quantity"])
                ),
                fixed_quote_principal=ExactDecimal.from_payload(
                    dict(order_payload["fixed_quote_principal"])
                ),
                paired_rung_id=str(order_payload["paired_rung_id"]),
                paired_price=ExactDecimal.from_payload(dict(order_payload["paired_price"])),
                venue_quantity_step=ExactDecimal.from_payload(
                    dict(order_payload["venue_quantity_step"])
                ),
                venue_minimum_quantity=ExactDecimal.from_payload(
                    dict(order_payload["venue_minimum_quantity"])
                ),
                lot_id=str(order_payload["lot_id"]),
                paired_obligation_id=order_payload["paired_obligation_id"],
            )
            if order_payload is not None
            else None
        ),
        fill_evidence=(
            FillEvidence(
                fill_id=str(fill_payload["fill_id"]),
                order_id=str(fill_payload["order_id"]),
                grid_plan_epoch_id=str(fill_payload["grid_plan_epoch_id"]),
                side=str(fill_payload["side"]),
                base_asset=str(fill_payload["base_asset"]),
                quote_asset=str(fill_payload["quote_asset"]),
                base_quantity=ExactDecimal.from_payload(dict(fill_payload["base_quantity"])),
                quote_quantity=ExactDecimal.from_payload(dict(fill_payload["quote_quantity"])),
                fee_asset=str(fill_payload["fee_asset"]),
                fee_quantity=ExactDecimal.from_payload(dict(fill_payload["fee_quantity"])),
                lot_id=str(fill_payload["lot_id"]),
                origin_epoch_id=str(fill_payload["origin_epoch_id"]),
                order_state=ManagedOrderState(str(fill_payload["order_state"])),
                paired_obligation_id=fill_payload["paired_obligation_id"],
            )
            if fill_payload is not None
            else None
        ),
    )


def _encode_projection_record(value: Any) -> Any:
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, tuple) and all(
        isinstance(item, tuple) and len(item) == 2 for item in value
    ):
        return [[asset, format(quantity, "f")] for asset, quantity in value]
    return value


def _encode_projection(projection: AllocationProjection) -> dict[str, Any]:
    return {
        "schema_version": projection.schema_version,
        "run_id": projection.run_id,
        "allocation_id": projection.allocation_id,
        "processing_position": projection.processing_position,
        "balances": [
            {
                "native_asset": item.native_asset,
                "account": item.account.value,
                "quantity": format(item.quantity, "f"),
            }
            for item in projection.balances
        ],
        "reservations": [
            {
                "obligation_id": item.obligation_id,
                "order_id": item.order_id,
                "grid_plan_epoch_id": item.grid_plan_epoch_id,
                "native_asset": item.native_asset,
                "quantity": format(item.quantity, "f"),
                "state": item.state.value,
                "transition_id": item.transition_id,
            }
            for item in projection.reservations
        ],
        "lots": [
            {
                "lot_id": item.lot_id,
                "native_asset": item.native_asset,
                "origin_epoch_id": item.origin_epoch_id,
                "inventory_quantity": format(item.inventory_quantity, "f"),
                "retained_quantity": format(item.retained_quantity, "f"),
            }
            for item in projection.lots
        ],
        "managed_orders": [
            {
                field.name: _encode_projection_record(getattr(item, field.name))
                for field in fields(item)
            }
            for item in projection.managed_orders
        ],
        "fills": [
            {
                field.name: _encode_projection_record(getattr(item, field.name))
                for field in fields(item)
            }
            for item in projection.fills
        ],
        "pair_obligations": [
            {
                field.name: _encode_projection_record(getattr(item, field.name))
                for field in fields(item)
            }
            for item in projection.pair_obligations
        ],
        "completed_cycles": [
            {
                field.name: _encode_projection_record(getattr(item, field.name))
                for field in fields(item)
            }
            for item in projection.completed_cycles
        ],
        "residuals": [
            {
                field.name: _encode_projection_record(getattr(item, field.name))
                for field in fields(item)
            }
            for item in projection.residuals
        ],
        "replay_fingerprint": projection.replay_fingerprint,
        "last_batch": (
            _encode_batch(projection.last_batch) if projection.last_batch is not None else None
        ),
        "last_invariants": {
            "schema_version": projection.last_invariants.schema_version,
            "checks": list(projection.last_invariants.checks),
            "passed": projection.last_invariants.passed,
        },
    }


def _decode_projection(payload: Mapping[str, Any]) -> AllocationProjection:
    invariant = payload["last_invariants"]
    last_batch = payload["last_batch"]
    return AllocationProjection(
        schema_version=str(payload["schema_version"]),
        run_id=str(payload["run_id"]),
        allocation_id=str(payload["allocation_id"]),
        processing_position=int(payload["processing_position"]),
        balances=tuple(
            AccountBalance(
                native_asset=str(item["native_asset"]),
                account=Account(str(item["account"])),
                quantity=Decimal(str(item["quantity"])),
            )
            for item in payload["balances"]
        ),
        reservations=tuple(
            ReservationRecord(
                obligation_id=str(item["obligation_id"]),
                order_id=str(item["order_id"]),
                grid_plan_epoch_id=str(item["grid_plan_epoch_id"]),
                native_asset=str(item["native_asset"]),
                quantity=Decimal(str(item["quantity"])),
                state=ReservationState(str(item["state"])),
                transition_id=item["transition_id"],
            )
            for item in payload["reservations"]
        ),
        lots=tuple(
            InventoryLot(
                lot_id=str(item["lot_id"]),
                native_asset=str(item["native_asset"]),
                origin_epoch_id=str(item["origin_epoch_id"]),
                inventory_quantity=Decimal(str(item["inventory_quantity"])),
                retained_quantity=Decimal(str(item["retained_quantity"])),
            )
            for item in payload["lots"]
        ),
        replay_fingerprint=str(payload["replay_fingerprint"]),
        last_batch=_decode_batch(last_batch) if last_batch is not None else None,
        last_invariants=InvariantResult(
            schema_version=str(invariant["schema_version"]),
            checks=tuple(str(item) for item in invariant["checks"]),
            passed=bool(invariant["passed"]),
        ),
        managed_orders=tuple(
            ManagedOrderRecord(
                order_id=str(item["order_id"]),
                grid_plan_epoch_id=str(item["grid_plan_epoch_id"]),
                rung_id=str(item["rung_id"]),
                side=str(item["side"]),
                state=ManagedOrderState(str(item["state"])),
                base_asset=str(item["base_asset"]),
                quote_asset=str(item["quote_asset"]),
                requested_base_quantity=Decimal(str(item["requested_base_quantity"])),
                fixed_quote_principal=Decimal(str(item["fixed_quote_principal"])),
                paired_rung_id=str(item["paired_rung_id"]),
                paired_price=Decimal(str(item["paired_price"])),
                venue_quantity_step=Decimal(str(item["venue_quantity_step"])),
                venue_minimum_quantity=Decimal(str(item["venue_minimum_quantity"])),
                lot_id=str(item["lot_id"]),
                paired_obligation_id=item["paired_obligation_id"],
                cumulative_base_quantity=Decimal(str(item["cumulative_base_quantity"])),
                cumulative_net_base_quantity=Decimal(str(item["cumulative_net_base_quantity"])),
            )
            for item in payload.get("managed_orders", ())
        ),
        fills=tuple(
            FillRecord(
                fill_id=str(item["fill_id"]),
                order_id=str(item["order_id"]),
                grid_plan_epoch_id=str(item["grid_plan_epoch_id"]),
                side=str(item["side"]),
                base_asset=str(item["base_asset"]),
                quote_asset=str(item["quote_asset"]),
                base_quantity=Decimal(str(item["base_quantity"])),
                quote_quantity=Decimal(str(item["quote_quantity"])),
                fee_asset=str(item["fee_asset"]),
                fee_quantity=Decimal(str(item["fee_quantity"])),
                net_base_quantity=Decimal(str(item["net_base_quantity"])),
                lot_id=str(item["lot_id"]),
                origin_epoch_id=str(item["origin_epoch_id"]),
                order_state=ManagedOrderState(str(item["order_state"])),
                paired_obligation_id=item["paired_obligation_id"],
            )
            for item in payload.get("fills", ())
        ),
        pair_obligations=tuple(
            PairObligation(
                obligation_id=str(item["obligation_id"]),
                origin_order_id=str(item["origin_order_id"]),
                origin_epoch_id=str(item["origin_epoch_id"]),
                origin_rung_id=str(item["origin_rung_id"]),
                paired_rung_id=str(item["paired_rung_id"]),
                paired_order_id=str(item["paired_order_id"]),
                lot_id=str(item["lot_id"]),
                base_asset=str(item["base_asset"]),
                quote_asset=str(item["quote_asset"]),
                fixed_quote_principal=Decimal(str(item["fixed_quote_principal"])),
                cumulative_net_base_quantity=Decimal(str(item["cumulative_net_base_quantity"])),
                paired_base_quantity=Decimal(str(item["paired_base_quantity"])),
                residual_base_quantity=Decimal(str(item["residual_base_quantity"])),
                cumulative_sold_base_quantity=Decimal(str(item["cumulative_sold_base_quantity"])),
                acquisition_quote_quantity=Decimal(str(item["acquisition_quote_quantity"])),
                proceeds_quote_quantity=Decimal(str(item["proceeds_quote_quantity"])),
                attributable_fees=tuple(
                    (str(asset), Decimal(str(quantity)))
                    for asset, quantity in item["attributable_fees"]
                ),
            )
            for item in payload.get("pair_obligations", ())
        ),
        completed_cycles=tuple(
            CompletedCycle(
                cycle_id=str(item["cycle_id"]),
                pair_obligation_id=str(item["pair_obligation_id"]),
                origin_epoch_id=str(item["origin_epoch_id"]),
                lot_id=str(item["lot_id"]),
                acquisition_quote_quantity=Decimal(str(item["acquisition_quote_quantity"])),
                proceeds_quote_quantity=Decimal(str(item["proceeds_quote_quantity"])),
                attributable_fees=tuple(
                    (str(asset), Decimal(str(quantity)))
                    for asset, quantity in item["attributable_fees"]
                ),
                realized_quote_result=Decimal(str(item["realized_quote_result"])),
                replacement_order_id=str(item["replacement_order_id"]),
                fixed_quote_principal=Decimal(str(item["fixed_quote_principal"])),
            )
            for item in payload.get("completed_cycles", ())
        ),
        residuals=tuple(
            ResidualInventory(
                residual_id=str(item["residual_id"]),
                pair_obligation_id=str(item["pair_obligation_id"]),
                lot_id=str(item["lot_id"]),
                origin_epoch_id=str(item["origin_epoch_id"]),
                native_asset=str(item["native_asset"]),
                quantity=Decimal(str(item["quantity"])),
                classification=str(item["classification"]),
            )
            for item in payload.get("residuals", ())
        ),
    )


class SQLiteAllocationJournal:
    def __init__(self, path: str | Path, run_id: str, allocation_id: str) -> None:
        self._path = Path(path)
        self._run_id = run_id
        self._allocation_id = allocation_id
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._path)
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    @staticmethod
    def _json(payload: Mapping[str, Any]) -> str:
        return json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)

    def _initialize(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        initial = AllocationProjection.initial(self._run_id, self._allocation_id)
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS allocation_metadata (
                    singleton INTEGER PRIMARY KEY CHECK(singleton = 1),
                    schema_version TEXT NOT NULL,
                    run_id TEXT NOT NULL,
                    allocation_id TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS posting_batches (
                    processing_position INTEGER PRIMARY KEY,
                    schema_version TEXT NOT NULL,
                    source_event_id TEXT NOT NULL UNIQUE,
                    batch_id TEXT NOT NULL UNIQUE,
                    batch_json TEXT NOT NULL,
                    projection_fingerprint TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS allocation_projection (
                    singleton INTEGER PRIMARY KEY CHECK(singleton = 1),
                    schema_version TEXT NOT NULL,
                    processing_position INTEGER NOT NULL,
                    state_json TEXT NOT NULL,
                    fingerprint TEXT NOT NULL
                );
                """
            )
            metadata = connection.execute(
                "SELECT run_id, allocation_id FROM allocation_metadata WHERE singleton = 1"
            ).fetchone()
            if metadata is None:
                connection.execute(
                    "INSERT INTO allocation_metadata VALUES (1, ?, ?, ?)",
                    ("allocation-journal-metadata/v1", self._run_id, self._allocation_id),
                )
            elif metadata != (self._run_id, self._allocation_id):
                raise ValueError("allocation journal identity does not match")
            connection.execute(
                """
                INSERT OR IGNORE INTO allocation_projection
                    (singleton, schema_version, processing_position, state_json, fingerprint)
                VALUES (1, ?, ?, ?, ?)
                """,
                (
                    initial.schema_version,
                    0,
                    self._json(_encode_projection(initial)),
                    initial.fingerprint,
                ),
            )

    def _replay(self, connection: sqlite3.Connection) -> tuple[PostingBatch, ...]:
        rows = connection.execute(
            "SELECT batch_json FROM posting_batches ORDER BY processing_position"
        ).fetchall()
        return tuple(_decode_batch(json.loads(row[0])) for row in rows)

    def _projection(self, connection: sqlite3.Connection) -> AllocationProjection:
        row = connection.execute(
            "SELECT state_json, fingerprint FROM allocation_projection WHERE singleton = 1"
        ).fetchone()
        if row is None:
            raise RuntimeError("allocation projection is not initialized")
        state = _decode_projection(json.loads(row[0]))
        if state.fingerprint != row[1]:
            raise RuntimeError("allocation projection snapshot fingerprint diverged")
        return state

    def append(
        self,
        batch: PostingBatch,
        *,
        crash_after: AccountingCrashBoundary | None = None,
    ) -> AllocationProjection:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            prior = self._projection(connection)
            existing = connection.execute(
                """
                SELECT batch_id FROM posting_batches
                WHERE source_event_id = ? OR batch_id = ?
                """,
                (batch.source_event_id, batch.batch_id),
            ).fetchone()
            if existing is not None:
                if existing[0] != batch.batch_id:
                    raise ValueError("duplicate source event has conflicting batch identity")
                connection.rollback()
                return prior
            projected = apply_posting_batch(prior, batch)
            if projected == prior:
                connection.rollback()
                return prior
            connection.execute(
                "INSERT INTO posting_batches VALUES (?, ?, ?, ?, ?, ?)",
                (
                    batch.processing_position,
                    batch.schema_version,
                    batch.source_event_id,
                    batch.batch_id,
                    self._json(_encode_batch(batch)),
                    projected.fingerprint,
                ),
            )
            if crash_after is AccountingCrashBoundary.BATCH_WRITE:
                raise RuntimeError("injected crash after batch_write")
            connection.execute(
                """
                UPDATE allocation_projection
                SET schema_version = ?, processing_position = ?, state_json = ?,
                    fingerprint = ?
                WHERE singleton = 1
                """,
                (
                    projected.schema_version,
                    projected.processing_position,
                    self._json(_encode_projection(projected)),
                    projected.fingerprint,
                ),
            )
            connection.commit()
            return projected
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def replay(self) -> tuple[PostingBatch, ...]:
        with self._connect() as connection:
            return self._replay(connection)

    def projection(self) -> AllocationProjection:
        with self._connect() as connection:
            return self._projection(connection)

    def rebuild_projection(self) -> AllocationProjection:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            rows = connection.execute(
                """
                SELECT processing_position, projection_fingerprint
                FROM posting_batches ORDER BY processing_position
                """
            ).fetchall()
            state = AllocationProjection.initial(self._run_id, self._allocation_id)
            for batch, row in zip(self._replay(connection), rows, strict=True):
                state = apply_posting_batch(state, batch)
                if row != (state.processing_position, state.fingerprint):
                    raise RuntimeError("posting replay fingerprint diverged")
            projected = state
            connection.execute(
                """
                UPDATE allocation_projection
                SET schema_version = ?, processing_position = ?, state_json = ?,
                    fingerprint = ?
                WHERE singleton = 1
                """,
                (
                    projected.schema_version,
                    projected.processing_position,
                    self._json(_encode_projection(projected)),
                    projected.fingerprint,
                ),
            )
            connection.commit()
            return projected
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @property
    def journal_fingerprint(self) -> str:
        return content_identity(
            "allocation-journal/v1", tuple(item.batch_id for item in self.replay())
        )
