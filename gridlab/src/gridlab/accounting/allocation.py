from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from fractions import Fraction
from typing import Iterable, Mapping, TypedDict

from gridlab.canonical._identity import content_identity
from gridlab.canonical.events import DomainTime
from gridlab.canonical.values import ExactDecimal


class Account(str, Enum):
    EXTERNAL = "EXTERNAL"
    AVAILABLE = "AVAILABLE"
    INVENTORY = "INVENTORY"
    RESERVED = "RESERVED"
    RETAINED = "RETAINED"
    FEE_EXPENSE = "FEE_EXPENSE"
    BOOTSTRAP_REQUIREMENT = "BOOTSTRAP_REQUIREMENT"
    MEMO_OFFSET = "MEMO_OFFSET"


class PostingCause(str, Enum):
    ALLOCATION_FUNDING = "ALLOCATION_FUNDING"
    FILL_PRINCIPAL = "FILL_PRINCIPAL"
    FILL_RECEIPT = "FILL_RECEIPT"
    FEE = "FEE"
    RESERVATION = "RESERVATION"
    RESERVATION_RELEASE = "RESERVATION_RELEASE"
    RESERVATION_STATUS = "RESERVATION_STATUS"
    BOOTSTRAP_REQUIREMENT = "BOOTSTRAP_REQUIREMENT"
    RETAIN_INVENTORY = "RETAIN_INVENTORY"
    MANAGED_ORDER_STATE = "MANAGED_ORDER_STATE"


class ReservationState(str, Enum):
    ACTIVE = "ACTIVE"
    CANCELLATION_PENDING = "CANCELLATION_PENDING"
    OUTCOME_UNKNOWN = "OUTCOME_UNKNOWN"
    RECONCILED_TERMINAL = "RECONCILED_TERMINAL"


class ManagedOrderState(str, Enum):
    ACTIVE = "ACTIVE"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    CANCELLATION_PENDING = "CANCELLATION_PENDING"
    OUTCOME_UNKNOWN = "OUTCOME_UNKNOWN"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    RECONCILED_TERMINAL = "RECONCILED_TERMINAL"


_EFFECTIVE_ORDER_STATES = (
    ManagedOrderState.ACTIVE,
    ManagedOrderState.PARTIALLY_FILLED,
    ManagedOrderState.CANCELLATION_PENDING,
    ManagedOrderState.OUTCOME_UNKNOWN,
)
_TERMINAL_ORDER_STATES = (
    ManagedOrderState.FILLED,
    ManagedOrderState.CANCELLED,
    ManagedOrderState.RECONCILED_TERMINAL,
)


class _PostingCommon(TypedDict):
    run_id: str
    allocation_id: str
    grid_plan_epoch_id: str
    source_event_id: str
    event_time: DomainTime
    processing_position: int
    order_id: str
    fill_id: str


_OWNED_ACCOUNTS = (
    Account.AVAILABLE,
    Account.INVENTORY,
    Account.RESERVED,
    Account.RETAINED,
)
_LOT_ACCOUNTS = (Account.INVENTORY, Account.RETAINED)
_INVARIANT_CHECKS = (
    "native_asset_conservation",
    "posting_balance",
    "allocation_ownership",
    "reservation_coverage",
    "bootstrap_backing",
    "managed_order_occupancy",
    "order_fill_monotonicity",
    "paired_cycle_provenance",
    "retained_residual_ownership",
)


@dataclass(frozen=True, slots=True)
class AssetPosting:
    schema_version: str
    run_id: str
    allocation_id: str
    grid_plan_epoch_id: str
    native_asset: str
    account: Account
    amount: ExactDecimal
    cause: PostingCause
    source_event_id: str
    event_time: DomainTime
    processing_position: int
    transition_id: str | None = None
    order_id: str | None = None
    fill_id: str | None = None
    cycle_id: str | None = None
    obligation_id: str | None = None
    reservation_state: ReservationState | None = None
    lot_id: str | None = None
    origin_epoch_id: str | None = None
    paired_lot_id: str | None = None

    def __post_init__(self) -> None:
        if self.schema_version != "asset-posting/v1":
            raise ValueError("unsupported asset posting schema")
        if not all(
            (
                self.run_id,
                self.allocation_id,
                self.grid_plan_epoch_id,
                self.native_asset,
                self.source_event_id,
            )
        ):
            raise ValueError("posting canonical identities are required")
        if self.native_asset != self.native_asset.upper() or not self.native_asset.isalnum():
            raise ValueError("native asset must be an uppercase alphanumeric symbol")
        if self.amount.kind != "native_asset_quantity":
            raise ValueError("posting amount must use native_asset_quantity")
        if self.processing_position <= 0:
            raise ValueError("posting processing position must be positive")
        if self.cause in {
            PostingCause.FILL_PRINCIPAL,
            PostingCause.FILL_RECEIPT,
            PostingCause.FEE,
        } and (not self.order_id or not self.fill_id):
            raise ValueError("fill postings require order and fill identity")
        if self.account is Account.RESERVED and (
            not self.obligation_id or self.reservation_state is None or not self.order_id
        ):
            raise ValueError("reserved postings require reservation metadata")
        if self.cause is PostingCause.RESERVATION_STATUS and self.amount.decimal != 0:
            raise ValueError("reservation status postings must have zero amount")
        if self.account in _LOT_ACCOUNTS and (not self.lot_id or not self.origin_epoch_id):
            raise ValueError("inventory postings require lot and origin epoch provenance")
        if self.origin_epoch_id is not None and self.lot_id is None:
            raise ValueError("lot origin cannot exist without lot identity")
        if self.paired_lot_id is not None and (
            self.cycle_id is None or self.paired_lot_id != self.lot_id
        ):
            raise ValueError("paired-lot identity must match the consumed cycle lot")
        if self.cause is PostingCause.RETAIN_INVENTORY and not self.transition_id:
            raise ValueError("retained inventory classification requires transition identity")


@dataclass(frozen=True, slots=True)
class ManagedOrderEvidence:
    order_id: str
    grid_plan_epoch_id: str
    rung_id: str
    side: str
    state: ManagedOrderState
    base_asset: str
    quote_asset: str
    requested_base_quantity: ExactDecimal
    fixed_quote_principal: ExactDecimal
    paired_rung_id: str
    paired_price: ExactDecimal
    venue_quantity_step: ExactDecimal
    venue_minimum_quantity: ExactDecimal
    lot_id: str
    paired_obligation_id: str | None = None

    def __post_init__(self) -> None:
        if not all(
            (
                self.order_id,
                self.grid_plan_epoch_id,
                self.rung_id,
                self.base_asset,
                self.quote_asset,
                self.paired_rung_id,
                self.lot_id,
            )
        ):
            raise ValueError("managed order canonical identities are required")
        if self.side not in {"BUY", "SELL"}:
            raise ValueError("managed order side must be BUY or SELL")
        if self.base_asset == self.quote_asset:
            raise ValueError("managed order assets must differ")
        quantities = (
            self.requested_base_quantity,
            self.fixed_quote_principal,
            self.paired_price,
            self.venue_quantity_step,
            self.venue_minimum_quantity,
        )
        if any(item.kind != "native_asset_quantity" or item.decimal < 0 for item in quantities):
            raise ValueError("managed order quantities must be non-negative native assets")
        if self.venue_quantity_step.decimal <= 0:
            raise ValueError("managed order venue quantity step must be positive")


@dataclass(frozen=True, slots=True)
class FillEvidence:
    fill_id: str
    order_id: str
    grid_plan_epoch_id: str
    side: str
    base_asset: str
    quote_asset: str
    base_quantity: ExactDecimal
    quote_quantity: ExactDecimal
    fee_asset: str
    fee_quantity: ExactDecimal
    lot_id: str
    origin_epoch_id: str
    order_state: ManagedOrderState
    paired_obligation_id: str | None = None

    def __post_init__(self) -> None:
        if not all(
            (
                self.fill_id,
                self.order_id,
                self.grid_plan_epoch_id,
                self.base_asset,
                self.quote_asset,
                self.fee_asset,
                self.lot_id,
                self.origin_epoch_id,
            )
        ):
            raise ValueError("fill evidence canonical identities are required")
        if self.side not in {"BUY", "SELL"}:
            raise ValueError("fill evidence side must be BUY or SELL")
        if self.order_state not in {
            ManagedOrderState.PARTIALLY_FILLED,
            ManagedOrderState.FILLED,
        }:
            raise ValueError("fill evidence requires a filled order state")

    @property
    def net_base_quantity(self) -> Decimal:
        if self.side == "BUY" and self.fee_asset == self.base_asset:
            return self.base_quantity.decimal - self.fee_quantity.decimal
        return self.base_quantity.decimal

    def economic_identity(self) -> tuple[object, ...]:
        return (
            self.fill_id,
            self.order_id,
            self.grid_plan_epoch_id,
            self.side,
            self.base_asset,
            self.quote_asset,
            self.base_quantity,
            self.quote_quantity,
            self.fee_asset,
            self.fee_quantity,
            self.lot_id,
            self.origin_epoch_id,
            self.order_state,
            self.paired_obligation_id,
        )


@dataclass(frozen=True, slots=True)
class PostingBatch:
    schema_version: str
    run_id: str
    allocation_id: str
    source_event_id: str
    event_time: DomainTime
    processing_position: int
    postings: tuple[AssetPosting, ...]
    managed_order_evidence: ManagedOrderEvidence | None = None
    fill_evidence: FillEvidence | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "postings", tuple(self.postings))
        if self.schema_version != "posting-batch/v1":
            raise ValueError("unsupported posting batch schema")
        if not self.run_id or not self.allocation_id or not self.source_event_id:
            raise ValueError("posting batch identities are required")
        if self.processing_position <= 0 or not self.postings:
            raise ValueError("posting batch position and postings are required")
        if any(
            (
                item.run_id != self.run_id
                or item.allocation_id != self.allocation_id
                or item.source_event_id != self.source_event_id
                or item.event_time != self.event_time
                or item.processing_position != self.processing_position
            )
            for item in self.postings
        ):
            raise ValueError("posting metadata conflicts with its atomic batch")
        if (
            self.managed_order_evidence is not None
            and self.managed_order_evidence.grid_plan_epoch_id
            != self.postings[0].grid_plan_epoch_id
        ):
            raise ValueError("managed order evidence epoch conflicts with its atomic batch")
        if self.fill_evidence is not None and (
            self.fill_evidence.grid_plan_epoch_id != self.postings[0].grid_plan_epoch_id
            or self.fill_evidence.fill_id != self.postings[0].fill_id
            or self.fill_evidence.order_id != self.postings[0].order_id
        ):
            raise ValueError("fill evidence identity conflicts with its atomic batch")

    @property
    def batch_id(self) -> str:
        if self.managed_order_evidence is None and self.fill_evidence is None:
            return content_identity("posting-batch/v1", self.legacy_identity_payload())
        return content_identity("posting-batch/v2", self)

    def legacy_identity_payload(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "run_id": self.run_id,
            "allocation_id": self.allocation_id,
            "source_event_id": self.source_event_id,
            "event_time": self.event_time,
            "processing_position": self.processing_position,
            "postings": self.postings,
        }


@dataclass(frozen=True, slots=True)
class InvariantResult:
    schema_version: str
    checks: tuple[str, ...]
    passed: bool

    def __post_init__(self) -> None:
        if self.schema_version != "allocation-invariants/v1":
            raise ValueError("unsupported allocation invariant schema")
        object.__setattr__(self, "checks", tuple(self.checks))


@dataclass(frozen=True, slots=True)
class AccountBalance:
    native_asset: str
    account: Account
    quantity: Decimal


@dataclass(frozen=True, slots=True)
class ReservationRecord:
    obligation_id: str
    order_id: str
    grid_plan_epoch_id: str
    native_asset: str
    quantity: Decimal
    state: ReservationState
    transition_id: str | None


@dataclass(frozen=True, slots=True)
class InventoryLot:
    lot_id: str
    native_asset: str
    origin_epoch_id: str
    inventory_quantity: Decimal
    retained_quantity: Decimal


@dataclass(frozen=True, slots=True)
class ManagedOrderRecord:
    order_id: str
    grid_plan_epoch_id: str
    rung_id: str
    side: str
    state: ManagedOrderState
    base_asset: str
    quote_asset: str
    requested_base_quantity: Decimal
    fixed_quote_principal: Decimal
    paired_rung_id: str
    paired_price: Decimal
    venue_quantity_step: Decimal
    venue_minimum_quantity: Decimal
    lot_id: str
    paired_obligation_id: str | None
    cumulative_base_quantity: Decimal
    cumulative_net_base_quantity: Decimal


@dataclass(frozen=True, slots=True)
class FillRecord:
    fill_id: str
    order_id: str
    grid_plan_epoch_id: str
    side: str
    base_asset: str
    quote_asset: str
    base_quantity: Decimal
    quote_quantity: Decimal
    fee_asset: str
    fee_quantity: Decimal
    net_base_quantity: Decimal
    lot_id: str
    origin_epoch_id: str
    order_state: ManagedOrderState
    paired_obligation_id: str | None


@dataclass(frozen=True, slots=True)
class PairObligation:
    obligation_id: str
    origin_order_id: str
    origin_epoch_id: str
    origin_rung_id: str
    paired_rung_id: str
    paired_order_id: str
    lot_id: str
    base_asset: str
    quote_asset: str
    fixed_quote_principal: Decimal
    cumulative_net_base_quantity: Decimal
    paired_base_quantity: Decimal
    residual_base_quantity: Decimal
    cumulative_sold_base_quantity: Decimal
    acquisition_quote_quantity: Decimal
    proceeds_quote_quantity: Decimal
    attributable_fees: tuple[tuple[str, Decimal], ...]


@dataclass(frozen=True, slots=True)
class CompletedCycle:
    cycle_id: str
    pair_obligation_id: str
    origin_epoch_id: str
    lot_id: str
    acquisition_quote_quantity: Decimal
    proceeds_quote_quantity: Decimal
    attributable_fees: tuple[tuple[str, Decimal], ...]
    realized_quote_result: Decimal
    replacement_order_id: str
    fixed_quote_principal: Decimal


@dataclass(frozen=True, slots=True)
class ResidualInventory:
    residual_id: str
    pair_obligation_id: str
    lot_id: str
    origin_epoch_id: str
    native_asset: str
    quantity: Decimal
    classification: str


@dataclass(frozen=True, slots=True)
class AllocationProjection:
    schema_version: str
    run_id: str
    allocation_id: str
    processing_position: int
    balances: tuple[AccountBalance, ...]
    reservations: tuple[ReservationRecord, ...]
    lots: tuple[InventoryLot, ...]
    replay_fingerprint: str
    last_batch: PostingBatch | None
    last_invariants: InvariantResult
    managed_orders: tuple[ManagedOrderRecord, ...] = ()
    fills: tuple[FillRecord, ...] = ()
    pair_obligations: tuple[PairObligation, ...] = ()
    completed_cycles: tuple[CompletedCycle, ...] = ()
    residuals: tuple[ResidualInventory, ...] = ()

    def __post_init__(self) -> None:
        if self.schema_version != "allocation-projection/v1":
            raise ValueError("unsupported allocation projection schema")
        for field_name in (
            "balances",
            "reservations",
            "lots",
            "managed_orders",
            "fills",
            "pair_obligations",
            "completed_cycles",
            "residuals",
        ):
            object.__setattr__(self, field_name, tuple(getattr(self, field_name)))
        if not self.replay_fingerprint:
            raise ValueError("allocation replay fingerprint is required")

    @classmethod
    def initial(cls, run_id: str, allocation_id: str) -> AllocationProjection:
        if not run_id or not allocation_id:
            raise ValueError("run and allocation identity are required")
        return cls(
            schema_version="allocation-projection/v1",
            run_id=run_id,
            allocation_id=allocation_id,
            processing_position=0,
            balances=(),
            reservations=(),
            lots=(),
            replay_fingerprint=content_identity(
                "allocation-replay/v1",
                {"run_id": run_id, "allocation_id": allocation_id, "batches": ()},
            ),
            last_batch=None,
            last_invariants=InvariantResult(
                schema_version="allocation-invariants/v1",
                checks=_INVARIANT_CHECKS,
                passed=True,
            ),
            managed_orders=(),
            fills=(),
            pair_obligations=(),
            completed_cycles=(),
            residuals=(),
        )

    @property
    def fingerprint(self) -> str:
        if not any(
            (
                self.managed_orders,
                self.fills,
                self.pair_obligations,
                self.completed_cycles,
                self.residuals,
            )
        ):
            return content_identity(
                "allocation-projection/v1",
                {
                    "schema_version": self.schema_version,
                    "run_id": self.run_id,
                    "allocation_id": self.allocation_id,
                    "processing_position": self.processing_position,
                    "balances": self.balances,
                    "reservations": self.reservations,
                    "lots": self.lots,
                    "replay_fingerprint": self.replay_fingerprint,
                    "last_batch": (
                        self.last_batch.legacy_identity_payload()
                        if self.last_batch is not None
                        else None
                    ),
                    "last_invariants": self.last_invariants,
                },
            )
        return content_identity("allocation-projection/v2", self)

    def balance(self, native_asset: str, account: Account | None = None) -> Decimal:
        accounts = _OWNED_ACCOUNTS if account is None else (account,)
        return sum(
            (
                item.quantity
                for item in self.balances
                if item.native_asset == native_asset and item.account in accounts
            ),
            Decimal("0"),
        )

    def fee_paid(self, native_asset: str) -> Decimal:
        return self.balance(native_asset, Account.FEE_EXPENSE)

    def reservation(self, obligation_id: str) -> ReservationRecord:
        matches = [item for item in self.reservations if item.obligation_id == obligation_id]
        if len(matches) != 1:
            raise KeyError(obligation_id)
        return matches[0]

    def lot(self, lot_id: str) -> InventoryLot:
        matches = [item for item in self.lots if item.lot_id == lot_id]
        if len(matches) != 1:
            raise KeyError(lot_id)
        return matches[0]

    def managed_order(self, order_id: str) -> ManagedOrderRecord:
        matches = [item for item in self.managed_orders if item.order_id == order_id]
        if len(matches) != 1:
            raise KeyError(order_id)
        return matches[0]


def _sorted_balances(
    balances: Mapping[tuple[str, Account], Decimal],
) -> tuple[AccountBalance, ...]:
    return tuple(
        AccountBalance(asset, account, quantity)
        for (asset, account), quantity in sorted(
            balances.items(), key=lambda item: (item[0][0], item[0][1].value)
        )
        if quantity != 0
    )


def _reservation_transition_allowed(previous: ReservationState, current: ReservationState) -> bool:
    if previous is current:
        return True
    allowed = {
        ReservationState.ACTIVE: {
            ReservationState.CANCELLATION_PENDING,
            ReservationState.OUTCOME_UNKNOWN,
            ReservationState.RECONCILED_TERMINAL,
        },
        ReservationState.CANCELLATION_PENDING: {
            ReservationState.OUTCOME_UNKNOWN,
            ReservationState.RECONCILED_TERMINAL,
        },
        ReservationState.OUTCOME_UNKNOWN: {ReservationState.RECONCILED_TERMINAL},
        ReservationState.RECONCILED_TERMINAL: set(),
    }
    return current in allowed[previous]


def _apply_reservations(
    prior: AllocationProjection,
    postings: tuple[AssetPosting, ...],
) -> tuple[ReservationRecord, ...]:
    records = {item.obligation_id: item for item in prior.reservations}
    pending_states = {
        ReservationState.CANCELLATION_PENDING,
        ReservationState.OUTCOME_UNKNOWN,
    }
    for item in postings:
        if item.account is not Account.RESERVED:
            continue
        if item.obligation_id is None or item.reservation_state is None or item.order_id is None:
            raise ValueError("reserved posting lacks reservation metadata")
        existing = records.get(item.obligation_id)
        if existing is not None:
            if (
                existing.grid_plan_epoch_id != item.grid_plan_epoch_id
                or existing.native_asset != item.native_asset
                or existing.order_id != item.order_id
            ):
                raise ValueError("committed obligation identity cannot be reassigned")
            if not _reservation_transition_allowed(existing.state, item.reservation_state):
                raise ValueError("reservation state transition is invalid")
            if (
                item.amount.decimal < 0
                and existing.state in pending_states
                and item.reservation_state is not ReservationState.RECONCILED_TERMINAL
            ):
                raise ValueError("pending old-epoch obligation remains committed")
            quantity = existing.quantity + item.amount.decimal
        else:
            if item.amount.decimal < 0:
                raise ValueError("reservation cannot release an unknown obligation")
            quantity = item.amount.decimal
        if quantity < 0:
            raise ValueError("reservation quantity cannot be negative")
        if quantity == 0 and item.reservation_state is not ReservationState.RECONCILED_TERMINAL:
            raise ValueError("non-terminal reservation must remain committed")
        records[item.obligation_id] = ReservationRecord(
            obligation_id=item.obligation_id,
            order_id=item.order_id,
            grid_plan_epoch_id=item.grid_plan_epoch_id,
            native_asset=item.native_asset,
            quantity=quantity,
            state=item.reservation_state,
            transition_id=item.transition_id,
        )
    return tuple(
        sorted(records.values(), key=lambda item: (item.grid_plan_epoch_id, item.obligation_id))
    )


def _apply_lots(
    prior: AllocationProjection,
    postings: tuple[AssetPosting, ...],
) -> tuple[InventoryLot, ...]:
    lots = {item.lot_id: item for item in prior.lots}
    for item in postings:
        if item.account not in _LOT_ACCOUNTS:
            continue
        if item.lot_id is None or item.origin_epoch_id is None:
            raise ValueError("lot posting lacks provenance")
        existing = lots.get(item.lot_id)
        if existing is None:
            inventory = Decimal("0")
            retained = Decimal("0")
            native_asset = item.native_asset
            origin_epoch_id = item.origin_epoch_id
        else:
            inventory = existing.inventory_quantity
            retained = existing.retained_quantity
            native_asset = existing.native_asset
            origin_epoch_id = existing.origin_epoch_id
            if native_asset != item.native_asset or origin_epoch_id != item.origin_epoch_id:
                raise ValueError("inventory lot provenance cannot be rewritten")
        if item.account is Account.INVENTORY:
            inventory += item.amount.decimal
        else:
            retained += item.amount.decimal
        if inventory < 0 or retained < 0:
            raise ValueError("inventory lot quantity cannot be negative")
        lots[item.lot_id] = InventoryLot(
            lot_id=item.lot_id,
            native_asset=native_asset,
            origin_epoch_id=origin_epoch_id,
            inventory_quantity=inventory,
            retained_quantity=retained,
        )
    return tuple(sorted(lots.values(), key=lambda item: item.lot_id))


def _order_transition_allowed(previous: ManagedOrderState, current: ManagedOrderState) -> bool:
    if previous is current:
        return True
    allowed = {
        ManagedOrderState.ACTIVE: {
            ManagedOrderState.PARTIALLY_FILLED,
            ManagedOrderState.CANCELLATION_PENDING,
            ManagedOrderState.OUTCOME_UNKNOWN,
            ManagedOrderState.FILLED,
            ManagedOrderState.CANCELLED,
            ManagedOrderState.RECONCILED_TERMINAL,
        },
        ManagedOrderState.PARTIALLY_FILLED: {
            ManagedOrderState.CANCELLATION_PENDING,
            ManagedOrderState.OUTCOME_UNKNOWN,
            ManagedOrderState.FILLED,
            ManagedOrderState.CANCELLED,
            ManagedOrderState.RECONCILED_TERMINAL,
        },
        ManagedOrderState.CANCELLATION_PENDING: {
            ManagedOrderState.PARTIALLY_FILLED,
            ManagedOrderState.OUTCOME_UNKNOWN,
            ManagedOrderState.FILLED,
            ManagedOrderState.CANCELLED,
            ManagedOrderState.RECONCILED_TERMINAL,
        },
        ManagedOrderState.OUTCOME_UNKNOWN: {
            ManagedOrderState.PARTIALLY_FILLED,
            ManagedOrderState.FILLED,
            ManagedOrderState.CANCELLED,
            ManagedOrderState.RECONCILED_TERMINAL,
        },
        ManagedOrderState.FILLED: set(),
        ManagedOrderState.CANCELLED: set(),
        ManagedOrderState.RECONCILED_TERMINAL: set(),
    }
    return current in allowed[previous]


def _record_from_evidence(evidence: ManagedOrderEvidence) -> ManagedOrderRecord:
    return ManagedOrderRecord(
        order_id=evidence.order_id,
        grid_plan_epoch_id=evidence.grid_plan_epoch_id,
        rung_id=evidence.rung_id,
        side=evidence.side,
        state=evidence.state,
        base_asset=evidence.base_asset,
        quote_asset=evidence.quote_asset,
        requested_base_quantity=evidence.requested_base_quantity.decimal,
        fixed_quote_principal=evidence.fixed_quote_principal.decimal,
        paired_rung_id=evidence.paired_rung_id,
        paired_price=evidence.paired_price.decimal,
        venue_quantity_step=evidence.venue_quantity_step.decimal,
        venue_minimum_quantity=evidence.venue_minimum_quantity.decimal,
        lot_id=evidence.lot_id,
        paired_obligation_id=evidence.paired_obligation_id,
        cumulative_base_quantity=Decimal("0"),
        cumulative_net_base_quantity=Decimal("0"),
    )


def _same_order_contract(record: ManagedOrderRecord, evidence: ManagedOrderEvidence) -> bool:
    return (
        record.grid_plan_epoch_id == evidence.grid_plan_epoch_id
        and record.rung_id == evidence.rung_id
        and record.side == evidence.side
        and record.base_asset == evidence.base_asset
        and record.quote_asset == evidence.quote_asset
        and record.requested_base_quantity == evidence.requested_base_quantity.decimal
        and record.fixed_quote_principal == evidence.fixed_quote_principal.decimal
        and record.paired_rung_id == evidence.paired_rung_id
        and record.paired_price == evidence.paired_price.decimal
        and record.venue_quantity_step == evidence.venue_quantity_step.decimal
        and record.venue_minimum_quantity == evidence.venue_minimum_quantity.decimal
        and record.lot_id == evidence.lot_id
        and record.paired_obligation_id == evidence.paired_obligation_id
    )


def _assert_rung_occupancy(
    orders: Mapping[str, ManagedOrderRecord],
    candidate: ManagedOrderRecord,
) -> None:
    if candidate.state not in _EFFECTIVE_ORDER_STATES:
        return
    for item in orders.values():
        if (
            item.order_id != candidate.order_id
            and item.grid_plan_epoch_id == candidate.grid_plan_epoch_id
            and item.rung_id == candidate.rung_id
            and item.state in _EFFECTIVE_ORDER_STATES
        ):
            raise ValueError("epoch rung already has an effective managed order")


def _apply_managed_order_evidence(
    prior: AllocationProjection,
    evidence: ManagedOrderEvidence | None,
) -> dict[str, ManagedOrderRecord]:
    orders = {item.order_id: item for item in prior.managed_orders}
    if evidence is None:
        return orders
    existing = orders.get(evidence.order_id)
    if existing is None:
        candidate = _record_from_evidence(evidence)
    else:
        if not _same_order_contract(existing, evidence):
            raise ValueError("managed order immutable contract cannot be rewritten")
        if not _order_transition_allowed(existing.state, evidence.state):
            raise ValueError("managed order state transition is invalid")
        candidate = _replace_order(existing, state=evidence.state)
    _assert_rung_occupancy(orders, candidate)
    orders[candidate.order_id] = candidate
    return orders


def _replace_order(
    order: ManagedOrderRecord,
    *,
    state: ManagedOrderState | None = None,
    requested_base_quantity: Decimal | None = None,
    cumulative_base_quantity: Decimal | None = None,
    cumulative_net_base_quantity: Decimal | None = None,
) -> ManagedOrderRecord:
    return ManagedOrderRecord(
        order_id=order.order_id,
        grid_plan_epoch_id=order.grid_plan_epoch_id,
        rung_id=order.rung_id,
        side=order.side,
        state=order.state if state is None else state,
        base_asset=order.base_asset,
        quote_asset=order.quote_asset,
        requested_base_quantity=(
            order.requested_base_quantity
            if requested_base_quantity is None
            else requested_base_quantity
        ),
        fixed_quote_principal=order.fixed_quote_principal,
        paired_rung_id=order.paired_rung_id,
        paired_price=order.paired_price,
        venue_quantity_step=order.venue_quantity_step,
        venue_minimum_quantity=order.venue_minimum_quantity,
        lot_id=order.lot_id,
        paired_obligation_id=order.paired_obligation_id,
        cumulative_base_quantity=(
            order.cumulative_base_quantity
            if cumulative_base_quantity is None
            else cumulative_base_quantity
        ),
        cumulative_net_base_quantity=(
            order.cumulative_net_base_quantity
            if cumulative_net_base_quantity is None
            else cumulative_net_base_quantity
        ),
    )


def _fee_map(
    fees: Iterable[tuple[str, Decimal]],
) -> dict[str, Decimal]:
    result: dict[str, Decimal] = {}
    for asset, quantity in fees:
        result[asset] = result.get(asset, Decimal("0")) + quantity
    return result


def _sorted_fees(fees: Mapping[str, Decimal]) -> tuple[tuple[str, Decimal], ...]:
    return tuple((asset, quantity) for asset, quantity in sorted(fees.items()) if quantity != 0)


def _quantize_down(quantity: Decimal, step: Decimal) -> Decimal:
    units = Fraction(quantity) // Fraction(step)
    step_tuple = step.as_tuple()
    coefficient = int("".join(str(digit) for digit in step_tuple.digits))
    return _decimal_units(units * coefficient, step_tuple.exponent)


def _decimal_units(units: int, exponent: int | str) -> Decimal:
    if not isinstance(exponent, int):
        raise ValueError("exact decimal operation requires finite operands")
    sign = 1 if units < 0 else 0
    digits = tuple(int(character) for character in str(abs(units))) or (0,)
    return Decimal((sign, digits, exponent))


def _apply_fill_evidence(
    prior: AllocationProjection,
    evidence: FillEvidence | None,
    orders: dict[str, ManagedOrderRecord],
) -> tuple[
    tuple[FillRecord, ...],
    dict[str, PairObligation],
    dict[str, CompletedCycle],
    dict[str, ResidualInventory],
]:
    fills = list(prior.fills)
    obligations = {item.obligation_id: item for item in prior.pair_obligations}
    cycles = {item.cycle_id: item for item in prior.completed_cycles}
    residuals = {item.residual_id: item for item in prior.residuals}
    if evidence is None:
        return tuple(fills), obligations, cycles, residuals
    order = orders.get(evidence.order_id)
    if order is None:
        raise ValueError("fill references an unknown managed order")
    if (
        order.grid_plan_epoch_id != evidence.grid_plan_epoch_id
        or order.side != evidence.side
        or order.base_asset != evidence.base_asset
        or order.quote_asset != evidence.quote_asset
        or order.lot_id != evidence.lot_id
        or evidence.origin_epoch_id != order.grid_plan_epoch_id
    ):
        raise ValueError("fill cannot rewrite managed order or epoch provenance")
    if order.state not in _TERMINAL_ORDER_STATES and not _order_transition_allowed(
        order.state, evidence.order_state
    ):
        raise ValueError("fill order state transition is invalid")

    fills.append(
        FillRecord(
            fill_id=evidence.fill_id,
            order_id=evidence.order_id,
            grid_plan_epoch_id=evidence.grid_plan_epoch_id,
            side=evidence.side,
            base_asset=evidence.base_asset,
            quote_asset=evidence.quote_asset,
            base_quantity=evidence.base_quantity.decimal,
            quote_quantity=evidence.quote_quantity.decimal,
            fee_asset=evidence.fee_asset,
            fee_quantity=evidence.fee_quantity.decimal,
            net_base_quantity=evidence.net_base_quantity,
            lot_id=evidence.lot_id,
            origin_epoch_id=evidence.origin_epoch_id,
            order_state=evidence.order_state,
            paired_obligation_id=evidence.paired_obligation_id,
        )
    )
    order = _replace_order(
        order,
        state=(order.state if order.state in _TERMINAL_ORDER_STATES else evidence.order_state),
        cumulative_base_quantity=order.cumulative_base_quantity + evidence.base_quantity.decimal,
        cumulative_net_base_quantity=order.cumulative_net_base_quantity
        + evidence.net_base_quantity,
    )
    if order.cumulative_base_quantity > order.requested_base_quantity:
        raise ValueError("cumulative fill exceeds managed order quantity")
    orders[order.order_id] = order

    if evidence.side == "BUY":
        obligation_id = content_identity(
            "cumulative-pair-obligation/v1",
            {
                "run_id": prior.run_id,
                "allocation_id": prior.allocation_id,
                "origin_epoch_id": order.grid_plan_epoch_id,
                "origin_rung_id": order.rung_id,
                "origin_order_id": order.order_id,
            },
        )
        existing = obligations.get(obligation_id)
        paired_order_id = (
            content_identity("cumulative-paired-order/v1", obligation_id)
            if existing is None
            else existing.paired_order_id
        )
        fees = _fee_map(existing.attributable_fees if existing is not None else ())
        fees[evidence.fee_asset] = fees.get(evidence.fee_asset, Decimal("0")) + (
            evidence.fee_quantity.decimal
        )
        net_quantity = (
            evidence.net_base_quantity
            if existing is None
            else existing.cumulative_net_base_quantity + evidence.net_base_quantity
        )
        paired_quantity = _quantize_down(net_quantity, order.venue_quantity_step)
        if paired_quantity < order.venue_minimum_quantity:
            paired_quantity = Decimal("0")
        residual_quantity = net_quantity - paired_quantity
        obligation = PairObligation(
            obligation_id=obligation_id,
            origin_order_id=order.order_id,
            origin_epoch_id=order.grid_plan_epoch_id,
            origin_rung_id=order.rung_id,
            paired_rung_id=order.paired_rung_id,
            paired_order_id=paired_order_id,
            lot_id=order.lot_id,
            base_asset=order.base_asset,
            quote_asset=order.quote_asset,
            fixed_quote_principal=order.fixed_quote_principal,
            cumulative_net_base_quantity=net_quantity,
            paired_base_quantity=paired_quantity,
            residual_base_quantity=residual_quantity,
            cumulative_sold_base_quantity=(
                Decimal("0") if existing is None else existing.cumulative_sold_base_quantity
            ),
            acquisition_quote_quantity=(
                evidence.quote_quantity.decimal
                if existing is None
                else existing.acquisition_quote_quantity + evidence.quote_quantity.decimal
            ),
            proceeds_quote_quantity=(
                Decimal("0") if existing is None else existing.proceeds_quote_quantity
            ),
            attributable_fees=_sorted_fees(fees),
        )
        obligations[obligation_id] = obligation
        if residual_quantity > 0:
            residual_id = content_identity("paired-residual/v1", obligation_id)
            residuals[residual_id] = ResidualInventory(
                residual_id=residual_id,
                pair_obligation_id=obligation_id,
                lot_id=order.lot_id,
                origin_epoch_id=order.grid_plan_epoch_id,
                native_asset=order.base_asset,
                quantity=residual_quantity,
                classification=(
                    "PENDING_PAIR"
                    if order.state in _EFFECTIVE_ORDER_STATES
                    else "RETAINED_RESIDUAL"
                ),
            )
        else:
            residuals.pop(content_identity("paired-residual/v1", obligation_id), None)
        if paired_quantity > 0:
            paired_order = orders.get(paired_order_id)
            remaining_quantity = paired_quantity - obligation.cumulative_sold_base_quantity
            if paired_order is None or paired_order.state in _TERMINAL_ORDER_STATES:
                paired_order_id = content_identity(
                    "cumulative-paired-order/v2",
                    {
                        "obligation_id": obligation_id,
                        "remaining_quantity": format(remaining_quantity, "f"),
                    },
                )
                obligation = PairObligation(
                    obligation_id=obligation.obligation_id,
                    origin_order_id=obligation.origin_order_id,
                    origin_epoch_id=obligation.origin_epoch_id,
                    origin_rung_id=obligation.origin_rung_id,
                    paired_rung_id=obligation.paired_rung_id,
                    paired_order_id=paired_order_id,
                    lot_id=obligation.lot_id,
                    base_asset=obligation.base_asset,
                    quote_asset=obligation.quote_asset,
                    fixed_quote_principal=obligation.fixed_quote_principal,
                    cumulative_net_base_quantity=obligation.cumulative_net_base_quantity,
                    paired_base_quantity=obligation.paired_base_quantity,
                    residual_base_quantity=obligation.residual_base_quantity,
                    cumulative_sold_base_quantity=obligation.cumulative_sold_base_quantity,
                    acquisition_quote_quantity=obligation.acquisition_quote_quantity,
                    proceeds_quote_quantity=obligation.proceeds_quote_quantity,
                    attributable_fees=obligation.attributable_fees,
                )
                obligations[obligation_id] = obligation
                paired_order = ManagedOrderRecord(
                    order_id=paired_order_id,
                    grid_plan_epoch_id=order.grid_plan_epoch_id,
                    rung_id=order.paired_rung_id,
                    side="SELL",
                    state=ManagedOrderState.ACTIVE,
                    base_asset=order.base_asset,
                    quote_asset=order.quote_asset,
                    requested_base_quantity=remaining_quantity,
                    fixed_quote_principal=order.fixed_quote_principal,
                    paired_rung_id=order.rung_id,
                    paired_price=order.paired_price,
                    venue_quantity_step=order.venue_quantity_step,
                    venue_minimum_quantity=order.venue_minimum_quantity,
                    lot_id=order.lot_id,
                    paired_obligation_id=obligation_id,
                    cumulative_base_quantity=Decimal("0"),
                    cumulative_net_base_quantity=Decimal("0"),
                )
            else:
                paired_order = _replace_order(
                    paired_order, requested_base_quantity=remaining_quantity
                )
            _assert_rung_occupancy(orders, paired_order)
            orders[paired_order_id] = paired_order
    else:
        if evidence.paired_obligation_id is None:
            raise ValueError("paired sell fill requires its cumulative obligation identity")
        sell_obligation = obligations.get(evidence.paired_obligation_id)
        if sell_obligation is None or sell_obligation.paired_order_id != evidence.order_id:
            raise ValueError("paired sell fill references an unknown cumulative obligation")
        obligation = sell_obligation
        fees = _fee_map(obligation.attributable_fees)
        fees[evidence.fee_asset] = fees.get(evidence.fee_asset, Decimal("0")) + (
            evidence.fee_quantity.decimal
        )
        sold_quantity = obligation.cumulative_sold_base_quantity + evidence.base_quantity.decimal
        if sold_quantity > obligation.paired_base_quantity:
            raise ValueError("paired sell exceeds its cumulative obligation")
        obligation = PairObligation(
            obligation_id=obligation.obligation_id,
            origin_order_id=obligation.origin_order_id,
            origin_epoch_id=obligation.origin_epoch_id,
            origin_rung_id=obligation.origin_rung_id,
            paired_rung_id=obligation.paired_rung_id,
            paired_order_id=obligation.paired_order_id,
            lot_id=obligation.lot_id,
            base_asset=obligation.base_asset,
            quote_asset=obligation.quote_asset,
            fixed_quote_principal=obligation.fixed_quote_principal,
            cumulative_net_base_quantity=obligation.cumulative_net_base_quantity,
            paired_base_quantity=obligation.paired_base_quantity,
            residual_base_quantity=obligation.residual_base_quantity,
            cumulative_sold_base_quantity=sold_quantity,
            acquisition_quote_quantity=obligation.acquisition_quote_quantity,
            proceeds_quote_quantity=obligation.proceeds_quote_quantity
            + evidence.quote_quantity.decimal,
            attributable_fees=_sorted_fees(fees),
        )
        obligations[obligation.obligation_id] = obligation
    return tuple(fills), obligations, cycles, residuals


def _proportional_part(
    quantity: Decimal,
    numerator: Decimal,
    denominator: Decimal,
) -> Decimal:
    if quantity == 0 or numerator == 0:
        return Decimal("0")
    if denominator <= 0 or numerator > denominator:
        raise ValueError("proportional allocation bounds are invalid")
    exponent = quantity.as_tuple().exponent
    if not isinstance(exponent, int):
        raise ValueError("proportional allocation requires a finite decimal")
    exact_units = (
        Fraction(quantity)
        * Fraction(numerator)
        / Fraction(denominator)
        / Fraction(Decimal((0, (1,), exponent)))
    )
    return _decimal_units(exact_units.numerator // exact_units.denominator, exponent)


def _complete_ready_cycles(
    orders: dict[str, ManagedOrderRecord],
    fills: tuple[FillRecord, ...],
    obligations: Mapping[str, PairObligation],
    cycles: dict[str, CompletedCycle],
    residuals: dict[str, ResidualInventory],
) -> None:
    for obligation in obligations.values():
        origin_order = orders[obligation.origin_order_id]
        paired_order = orders.get(obligation.paired_order_id)
        residual_id = content_identity("paired-residual/v1", obligation.obligation_id)
        residual = residuals.get(residual_id)
        if residual is not None and origin_order.state in _TERMINAL_ORDER_STATES:
            residuals[residual_id] = ResidualInventory(
                residual_id=residual.residual_id,
                pair_obligation_id=residual.pair_obligation_id,
                lot_id=residual.lot_id,
                origin_epoch_id=residual.origin_epoch_id,
                native_asset=residual.native_asset,
                quantity=residual.quantity,
                classification="RETAINED_RESIDUAL",
            )
        if (
            obligation.paired_base_quantity <= 0
            or paired_order is None
            or origin_order.state not in _TERMINAL_ORDER_STATES
            or paired_order.state not in _TERMINAL_ORDER_STATES
            or obligation.cumulative_sold_base_quantity != obligation.paired_base_quantity
        ):
            continue
        cycle_id = content_identity("completed-grid-cycle/v1", obligation.obligation_id)
        if cycle_id in cycles:
            continue
        acquisition = sum(
            (
                _proportional_part(
                    item.quote_quantity,
                    obligation.paired_base_quantity,
                    obligation.cumulative_net_base_quantity,
                )
                for item in fills
                if item.order_id == obligation.origin_order_id
            ),
            Decimal("0"),
        )
        attributable_map: dict[str, Decimal] = {}
        for item in fills:
            if item.order_id == obligation.origin_order_id:
                fee = _proportional_part(
                    item.fee_quantity,
                    obligation.paired_base_quantity,
                    obligation.cumulative_net_base_quantity,
                )
            elif item.paired_obligation_id == obligation.obligation_id:
                fee = item.fee_quantity
            else:
                continue
            attributable_map[item.fee_asset] = (
                attributable_map.get(item.fee_asset, Decimal("0")) + fee
            )
        attributable = _sorted_fees(attributable_map)
        quote_fees = sum(
            (quantity for asset, quantity in attributable if asset == obligation.quote_asset),
            Decimal("0"),
        )
        replacement_order_id = content_identity(
            "fixed-principal-replacement/v1", obligation.obligation_id
        )
        cycles[cycle_id] = CompletedCycle(
            cycle_id=cycle_id,
            pair_obligation_id=obligation.obligation_id,
            origin_epoch_id=obligation.origin_epoch_id,
            lot_id=obligation.lot_id,
            acquisition_quote_quantity=acquisition,
            proceeds_quote_quantity=obligation.proceeds_quote_quantity,
            attributable_fees=attributable,
            realized_quote_result=obligation.proceeds_quote_quantity - acquisition - quote_fees,
            replacement_order_id=replacement_order_id,
            fixed_quote_principal=obligation.fixed_quote_principal,
        )
        replacement = ManagedOrderRecord(
            order_id=replacement_order_id,
            grid_plan_epoch_id=origin_order.grid_plan_epoch_id,
            rung_id=origin_order.rung_id,
            side="BUY",
            state=ManagedOrderState.ACTIVE,
            base_asset=origin_order.base_asset,
            quote_asset=origin_order.quote_asset,
            requested_base_quantity=origin_order.requested_base_quantity,
            fixed_quote_principal=origin_order.fixed_quote_principal,
            paired_rung_id=origin_order.paired_rung_id,
            paired_price=origin_order.paired_price,
            venue_quantity_step=origin_order.venue_quantity_step,
            venue_minimum_quantity=origin_order.venue_minimum_quantity,
            lot_id=content_identity("replacement-lot/v1", obligation.obligation_id),
            paired_obligation_id=None,
            cumulative_base_quantity=Decimal("0"),
            cumulative_net_base_quantity=Decimal("0"),
        )
        _assert_rung_occupancy(orders, replacement)
        orders[replacement_order_id] = replacement


def _validate_batch_balance(postings: Iterable[AssetPosting]) -> None:
    totals: dict[str, Decimal] = {}
    for item in postings:
        totals[item.native_asset] = (
            totals.get(item.native_asset, Decimal("0")) + item.amount.decimal
        )
    if any(total != 0 for total in totals.values()):
        raise ValueError("posting balance invariant failed")


def _validate_projection(
    *,
    balances: Mapping[tuple[str, Account], Decimal],
    reservations: tuple[ReservationRecord, ...],
    lots: tuple[InventoryLot, ...],
) -> None:
    assets = {asset for asset, _ in balances}
    for asset in assets:
        total = sum(
            (quantity for (candidate, _), quantity in balances.items() if candidate == asset),
            Decimal("0"),
        )
        if total != 0:
            raise ValueError("native asset conservation invariant failed")
    if any(
        quantity < 0 for (_, account), quantity in balances.items() if account in _OWNED_ACCOUNTS
    ):
        raise ValueError("allocation ownership invariant failed")

    reservation_totals: dict[str, Decimal] = {}
    for item in reservations:
        reservation_totals[item.native_asset] = (
            reservation_totals.get(item.native_asset, Decimal("0")) + item.quantity
        )
    for asset in assets | set(reservation_totals):
        reserved_balance = balances.get((asset, Account.RESERVED), Decimal("0"))
        if reserved_balance != reservation_totals.get(asset, Decimal("0")):
            raise ValueError("reservation coverage invariant failed")

    for account in _LOT_ACCOUNTS:
        lot_totals: dict[str, Decimal] = {}
        for lot in lots:
            quantity = (
                lot.inventory_quantity if account is Account.INVENTORY else lot.retained_quantity
            )
            lot_totals[lot.native_asset] = lot_totals.get(lot.native_asset, Decimal("0")) + quantity
        for asset in assets | set(lot_totals):
            if balances.get((asset, account), Decimal("0")) != lot_totals.get(asset, Decimal("0")):
                raise ValueError("allocation ownership lot provenance invariant failed")

    for asset in assets:
        required = balances.get((asset, Account.BOOTSTRAP_REQUIREMENT), Decimal("0"))
        backing = balances.get((asset, Account.INVENTORY), Decimal("0")) + balances.get(
            (asset, Account.RESERVED), Decimal("0")
        )
        if required < 0 or backing < required:
            raise ValueError("bootstrap backing invariant failed")


def _validate_cycle_projection(
    *,
    orders: Mapping[str, ManagedOrderRecord],
    fills: tuple[FillRecord, ...],
    obligations: Mapping[str, PairObligation],
    cycles: Mapping[str, CompletedCycle],
    residuals: Mapping[str, ResidualInventory],
    lots: tuple[InventoryLot, ...],
) -> None:
    effective_slots = [
        (item.grid_plan_epoch_id, item.rung_id)
        for item in orders.values()
        if item.state in _EFFECTIVE_ORDER_STATES
    ]
    if len(effective_slots) != len(set(effective_slots)):
        raise ValueError("managed order occupancy invariant failed")
    if len({item.fill_id for item in fills}) != len(fills):
        raise ValueError("fill identity invariant failed")
    for order in orders.values():
        order_fills = [item for item in fills if item.order_id == order.order_id]
        cumulative = sum((item.base_quantity for item in order_fills), Decimal("0"))
        cumulative_net = sum((item.net_base_quantity for item in order_fills), Decimal("0"))
        if (
            cumulative != order.cumulative_base_quantity
            or cumulative_net != order.cumulative_net_base_quantity
            or cumulative < 0
            or cumulative > order.requested_base_quantity
        ):
            raise ValueError("order fill monotonicity invariant failed")
        if any(
            item.grid_plan_epoch_id != order.grid_plan_epoch_id
            or item.origin_epoch_id != order.grid_plan_epoch_id
            or item.lot_id != order.lot_id
            for item in order_fills
        ):
            raise ValueError("order fill epoch provenance invariant failed")
    lot_map = {item.lot_id: item for item in lots}
    for obligation in obligations.values():
        origin = orders.get(obligation.origin_order_id)
        paired = orders.get(obligation.paired_order_id)
        paired_fills = [
            item for item in fills if item.paired_obligation_id == obligation.obligation_id
        ]
        if (
            origin is None
            or origin.grid_plan_epoch_id != obligation.origin_epoch_id
            or origin.lot_id != obligation.lot_id
            or obligation.cumulative_net_base_quantity
            != obligation.paired_base_quantity + obligation.residual_base_quantity
            or obligation.cumulative_sold_base_quantity > obligation.paired_base_quantity
            or (obligation.paired_base_quantity > 0 and paired is None)
            or (
                paired is not None
                and (
                    paired.paired_obligation_id != obligation.obligation_id
                    or paired.grid_plan_epoch_id != obligation.origin_epoch_id
                )
            )
            or sum((item.base_quantity for item in paired_fills), Decimal("0"))
            != obligation.cumulative_sold_base_quantity
        ):
            raise ValueError("paired cycle provenance invariant failed")
    for cycle in cycles.values():
        cycle_obligation = obligations.get(cycle.pair_obligation_id)
        if (
            cycle_obligation is None
            or cycle.origin_epoch_id != cycle_obligation.origin_epoch_id
            or cycle.lot_id != cycle_obligation.lot_id
            or cycle.fixed_quote_principal != cycle_obligation.fixed_quote_principal
        ):
            raise ValueError("completed cycle provenance invariant failed")
    for residual in residuals.values():
        residual_obligation = obligations.get(residual.pair_obligation_id)
        lot = lot_map.get(residual.lot_id)
        if (
            residual_obligation is None
            or lot is None
            or residual.origin_epoch_id != residual_obligation.origin_epoch_id
            or residual.native_asset != residual_obligation.base_asset
            or residual.quantity != residual_obligation.residual_base_quantity
            or residual.quantity <= 0
            or lot.inventory_quantity + lot.retained_quantity < residual.quantity
        ):
            raise ValueError("retained residual ownership invariant failed")


def apply_posting_batch(
    projection: AllocationProjection, batch: PostingBatch
) -> AllocationProjection:
    if batch.run_id != projection.run_id or batch.allocation_id != projection.allocation_id:
        raise ValueError("posting batch run or allocation does not own this subledger")
    if batch.fill_evidence is not None:
        duplicate = next(
            (item for item in projection.fills if item.fill_id == batch.fill_evidence.fill_id),
            None,
        )
        if duplicate is not None:
            evidence = batch.fill_evidence
            if (
                duplicate.order_id,
                duplicate.grid_plan_epoch_id,
                duplicate.side,
                duplicate.base_asset,
                duplicate.quote_asset,
                duplicate.base_quantity,
                duplicate.quote_quantity,
                duplicate.fee_asset,
                duplicate.fee_quantity,
                duplicate.lot_id,
                duplicate.origin_epoch_id,
                duplicate.order_state,
                duplicate.paired_obligation_id,
            ) != (
                evidence.order_id,
                evidence.grid_plan_epoch_id,
                evidence.side,
                evidence.base_asset,
                evidence.quote_asset,
                evidence.base_quantity.decimal,
                evidence.quote_quantity.decimal,
                evidence.fee_asset,
                evidence.fee_quantity.decimal,
                evidence.lot_id,
                evidence.origin_epoch_id,
                evidence.order_state,
                evidence.paired_obligation_id,
            ):
                raise ValueError("duplicate fill identity has conflicting economics")
            return projection
    if batch.processing_position != projection.processing_position + 1:
        raise ValueError("posting batch processing position is not contiguous")
    if (
        any(item.cause is PostingCause.ALLOCATION_FUNDING for item in batch.postings)
        and projection.processing_position != 0
    ):
        raise ValueError("allocation funding is allowed only in the initial atomic batch")

    _validate_batch_balance(batch.postings)
    balances = {(item.native_asset, item.account): item.quantity for item in projection.balances}
    for item in batch.postings:
        key = (item.native_asset, item.account)
        balances[key] = balances.get(key, Decimal("0")) + item.amount.decimal
    reservations = _apply_reservations(projection, batch.postings)
    lots = _apply_lots(projection, batch.postings)
    _validate_projection(balances=balances, reservations=reservations, lots=lots)
    orders = _apply_managed_order_evidence(projection, batch.managed_order_evidence)
    fills, obligations, cycles, residuals = _apply_fill_evidence(
        projection, batch.fill_evidence, orders
    )
    _complete_ready_cycles(orders, fills, obligations, cycles, residuals)
    _validate_cycle_projection(
        orders=orders,
        fills=fills,
        obligations=obligations,
        cycles=cycles,
        residuals=residuals,
        lots=lots,
    )
    return AllocationProjection(
        schema_version="allocation-projection/v1",
        run_id=projection.run_id,
        allocation_id=projection.allocation_id,
        processing_position=batch.processing_position,
        balances=_sorted_balances(balances),
        reservations=reservations,
        lots=lots,
        replay_fingerprint=content_identity(
            "allocation-replay/v1",
            {
                "prior_fingerprint": projection.replay_fingerprint,
                "batch_id": batch.batch_id,
            },
        ),
        last_batch=batch,
        last_invariants=InvariantResult(
            schema_version="allocation-invariants/v1",
            checks=_INVARIANT_CHECKS,
            passed=True,
        ),
        managed_orders=tuple(
            sorted(
                orders.values(),
                key=lambda item: (
                    item.grid_plan_epoch_id,
                    item.rung_id,
                    item.order_id,
                ),
            )
        ),
        fills=tuple(sorted(fills, key=lambda item: item.fill_id)),
        pair_obligations=tuple(sorted(obligations.values(), key=lambda item: item.obligation_id)),
        completed_cycles=tuple(sorted(cycles.values(), key=lambda item: item.cycle_id)),
        residuals=tuple(sorted(residuals.values(), key=lambda item: item.residual_id)),
    )


def _posting(
    *,
    run_id: str,
    allocation_id: str,
    grid_plan_epoch_id: str,
    native_asset: str,
    account: Account,
    amount: ExactDecimal,
    cause: PostingCause,
    source_event_id: str,
    event_time: DomainTime,
    processing_position: int,
    transition_id: str | None = None,
    order_id: str | None = None,
    fill_id: str | None = None,
    cycle_id: str | None = None,
    lot_id: str | None = None,
    origin_epoch_id: str | None = None,
    paired_lot_id: str | None = None,
) -> AssetPosting:
    return AssetPosting(
        schema_version="asset-posting/v1",
        run_id=run_id,
        allocation_id=allocation_id,
        grid_plan_epoch_id=grid_plan_epoch_id,
        native_asset=native_asset,
        account=account,
        amount=amount,
        cause=cause,
        source_event_id=source_event_id,
        event_time=event_time,
        processing_position=processing_position,
        transition_id=transition_id,
        order_id=order_id,
        fill_id=fill_id,
        cycle_id=cycle_id,
        lot_id=lot_id,
        origin_epoch_id=origin_epoch_id,
        paired_lot_id=paired_lot_id,
    )


def allocation_funding_batch(
    *,
    run_id: str,
    allocation_id: str,
    grid_plan_epoch_id: str,
    source_event_id: str,
    event_time: DomainTime,
    processing_position: int,
    assets: Mapping[str, ExactDecimal],
    inventory_assets: set[str] | frozenset[str] = frozenset(),
) -> PostingBatch:
    postings: list[AssetPosting] = []
    for asset, amount in sorted(assets.items()):
        owned_account = Account.INVENTORY if asset in inventory_assets else Account.AVAILABLE
        lot_id = "lot:bootstrap" if owned_account is Account.INVENTORY else None
        origin_epoch_id = grid_plan_epoch_id if lot_id is not None else None
        postings.extend(
            (
                _posting(
                    run_id=run_id,
                    allocation_id=allocation_id,
                    grid_plan_epoch_id=grid_plan_epoch_id,
                    native_asset=asset,
                    account=Account.EXTERNAL,
                    amount=ExactDecimal.parse(
                        format(-amount.decimal, "f"), kind="native_asset_quantity"
                    ),
                    cause=PostingCause.ALLOCATION_FUNDING,
                    source_event_id=source_event_id,
                    event_time=event_time,
                    processing_position=processing_position,
                ),
                _posting(
                    run_id=run_id,
                    allocation_id=allocation_id,
                    grid_plan_epoch_id=grid_plan_epoch_id,
                    native_asset=asset,
                    account=owned_account,
                    amount=amount,
                    cause=PostingCause.ALLOCATION_FUNDING,
                    source_event_id=source_event_id,
                    event_time=event_time,
                    processing_position=processing_position,
                    lot_id=lot_id,
                    origin_epoch_id=origin_epoch_id,
                ),
            )
        )
    return PostingBatch(
        schema_version="posting-batch/v1",
        run_id=run_id,
        allocation_id=allocation_id,
        source_event_id=source_event_id,
        event_time=event_time,
        processing_position=processing_position,
        postings=tuple(postings),
    )


def _negated(value: ExactDecimal) -> ExactDecimal:
    return ExactDecimal.parse(format(-value.decimal, "f"), kind="native_asset_quantity")


def managed_order_state_batch(
    *,
    run_id: str,
    allocation_id: str,
    grid_plan_epoch_id: str,
    source_event_id: str,
    event_time: DomainTime,
    processing_position: int,
    order_id: str,
    rung_id: str,
    side: str,
    state: ManagedOrderState,
    base_asset: str,
    quote_asset: str,
    requested_base_quantity: ExactDecimal,
    fixed_quote_principal: ExactDecimal,
    paired_rung_id: str,
    paired_price: ExactDecimal,
    venue_quantity_step: ExactDecimal,
    venue_minimum_quantity: ExactDecimal,
    lot_id: str,
    paired_obligation_id: str | None = None,
) -> PostingBatch:
    evidence = ManagedOrderEvidence(
        order_id=order_id,
        grid_plan_epoch_id=grid_plan_epoch_id,
        rung_id=rung_id,
        side=side,
        state=state,
        base_asset=base_asset,
        quote_asset=quote_asset,
        requested_base_quantity=requested_base_quantity,
        fixed_quote_principal=fixed_quote_principal,
        paired_rung_id=paired_rung_id,
        paired_price=paired_price,
        venue_quantity_step=venue_quantity_step,
        venue_minimum_quantity=venue_minimum_quantity,
        lot_id=lot_id,
        paired_obligation_id=paired_obligation_id,
    )
    zero = ExactDecimal.parse("0", kind="native_asset_quantity")
    return PostingBatch(
        schema_version="posting-batch/v1",
        run_id=run_id,
        allocation_id=allocation_id,
        source_event_id=source_event_id,
        event_time=event_time,
        processing_position=processing_position,
        postings=(
            _posting(
                run_id=run_id,
                allocation_id=allocation_id,
                grid_plan_epoch_id=grid_plan_epoch_id,
                native_asset=base_asset,
                account=Account.MEMO_OFFSET,
                amount=zero,
                cause=PostingCause.MANAGED_ORDER_STATE,
                source_event_id=source_event_id,
                event_time=event_time,
                processing_position=processing_position,
                order_id=order_id,
            ),
        ),
        managed_order_evidence=evidence,
    )


def spot_fill_batch(
    *,
    run_id: str,
    allocation_id: str,
    grid_plan_epoch_id: str,
    source_event_id: str,
    event_time: DomainTime,
    processing_position: int,
    side: str,
    base_asset: str,
    quote_asset: str,
    base_quantity: ExactDecimal,
    quote_quantity: ExactDecimal,
    fee_asset: str,
    fee_quantity: ExactDecimal,
    order_id: str,
    fill_id: str,
    lot_id: str,
    origin_epoch_id: str,
    cycle_id: str | None = None,
    paired_lot_id: str | None = None,
) -> PostingBatch:
    if side not in {"BUY", "SELL"}:
        raise ValueError("spot fill side must be BUY or SELL")
    if any(
        value.kind != "native_asset_quantity" or value.decimal < 0
        for value in (base_quantity, quote_quantity, fee_quantity)
    ):
        raise ValueError("spot fill quantities must be non-negative native assets")
    common: _PostingCommon = {
        "run_id": run_id,
        "allocation_id": allocation_id,
        "grid_plan_epoch_id": grid_plan_epoch_id,
        "source_event_id": source_event_id,
        "event_time": event_time,
        "processing_position": processing_position,
        "order_id": order_id,
        "fill_id": fill_id,
    }
    postings: list[AssetPosting]
    if side == "BUY":
        postings = [
            _posting(
                **common,
                native_asset=quote_asset,
                account=Account.AVAILABLE,
                amount=_negated(quote_quantity),
                cause=PostingCause.FILL_PRINCIPAL,
            ),
            _posting(
                **common,
                native_asset=quote_asset,
                account=Account.EXTERNAL,
                amount=quote_quantity,
                cause=PostingCause.FILL_PRINCIPAL,
            ),
            _posting(
                **common,
                native_asset=base_asset,
                account=Account.EXTERNAL,
                amount=_negated(base_quantity),
                cause=PostingCause.FILL_RECEIPT,
            ),
            _posting(
                **common,
                native_asset=base_asset,
                account=Account.INVENTORY,
                amount=base_quantity,
                cause=PostingCause.FILL_RECEIPT,
                lot_id=lot_id,
                origin_epoch_id=origin_epoch_id,
            ),
        ]
        fee_account = Account.INVENTORY if fee_asset == base_asset else Account.AVAILABLE
        fee_lot_id = lot_id if fee_account is Account.INVENTORY else None
        fee_origin = origin_epoch_id if fee_lot_id is not None else None
    else:
        postings = [
            _posting(
                **common,
                native_asset=base_asset,
                account=Account.INVENTORY,
                amount=_negated(base_quantity),
                cause=PostingCause.FILL_PRINCIPAL,
                cycle_id=cycle_id,
                lot_id=lot_id,
                origin_epoch_id=origin_epoch_id,
                paired_lot_id=paired_lot_id,
            ),
            _posting(
                **common,
                native_asset=base_asset,
                account=Account.EXTERNAL,
                amount=base_quantity,
                cause=PostingCause.FILL_PRINCIPAL,
            ),
            _posting(
                **common,
                native_asset=quote_asset,
                account=Account.EXTERNAL,
                amount=_negated(quote_quantity),
                cause=PostingCause.FILL_RECEIPT,
            ),
            _posting(
                **common,
                native_asset=quote_asset,
                account=Account.AVAILABLE,
                amount=quote_quantity,
                cause=PostingCause.FILL_RECEIPT,
            ),
        ]
        fee_account = Account.INVENTORY if fee_asset == base_asset else Account.AVAILABLE
        fee_lot_id = lot_id if fee_account is Account.INVENTORY else None
        fee_origin = origin_epoch_id if fee_lot_id is not None else None
    postings.extend(
        (
            _posting(
                **common,
                native_asset=fee_asset,
                account=fee_account,
                amount=_negated(fee_quantity),
                cause=PostingCause.FEE,
                cycle_id=cycle_id,
                lot_id=fee_lot_id,
                origin_epoch_id=fee_origin,
                paired_lot_id=(paired_lot_id if fee_account is Account.INVENTORY else None),
            ),
            _posting(
                **common,
                native_asset=fee_asset,
                account=Account.FEE_EXPENSE,
                amount=fee_quantity,
                cause=PostingCause.FEE,
                cycle_id=cycle_id,
            ),
        )
    )
    return PostingBatch(
        schema_version="posting-batch/v1",
        run_id=run_id,
        allocation_id=allocation_id,
        source_event_id=source_event_id,
        event_time=event_time,
        processing_position=processing_position,
        postings=tuple(postings),
    )


def cumulative_grid_fill_batch(
    *,
    run_id: str,
    allocation_id: str,
    grid_plan_epoch_id: str,
    source_event_id: str,
    event_time: DomainTime,
    processing_position: int,
    side: str,
    base_asset: str,
    quote_asset: str,
    base_quantity: ExactDecimal,
    quote_quantity: ExactDecimal,
    fee_asset: str,
    fee_quantity: ExactDecimal,
    order_id: str,
    fill_id: str,
    lot_id: str,
    origin_epoch_id: str,
    order_state: ManagedOrderState,
    paired_obligation_id: str | None = None,
) -> PostingBatch:
    cycle_id = (
        content_identity("completed-grid-cycle/v1", paired_obligation_id)
        if side == "SELL" and paired_obligation_id is not None
        else None
    )
    posting_batch = spot_fill_batch(
        run_id=run_id,
        allocation_id=allocation_id,
        grid_plan_epoch_id=grid_plan_epoch_id,
        source_event_id=source_event_id,
        event_time=event_time,
        processing_position=processing_position,
        side=side,
        base_asset=base_asset,
        quote_asset=quote_asset,
        base_quantity=base_quantity,
        quote_quantity=quote_quantity,
        fee_asset=fee_asset,
        fee_quantity=fee_quantity,
        order_id=order_id,
        fill_id=fill_id,
        lot_id=lot_id,
        origin_epoch_id=origin_epoch_id,
        cycle_id=cycle_id,
        paired_lot_id=lot_id if cycle_id is not None else None,
    )
    return PostingBatch(
        schema_version=posting_batch.schema_version,
        run_id=posting_batch.run_id,
        allocation_id=posting_batch.allocation_id,
        source_event_id=posting_batch.source_event_id,
        event_time=posting_batch.event_time,
        processing_position=posting_batch.processing_position,
        postings=posting_batch.postings,
        fill_evidence=FillEvidence(
            fill_id=fill_id,
            order_id=order_id,
            grid_plan_epoch_id=grid_plan_epoch_id,
            side=side,
            base_asset=base_asset,
            quote_asset=quote_asset,
            base_quantity=base_quantity,
            quote_quantity=quote_quantity,
            fee_asset=fee_asset,
            fee_quantity=fee_quantity,
            lot_id=lot_id,
            origin_epoch_id=origin_epoch_id,
            order_state=order_state,
            paired_obligation_id=paired_obligation_id,
        ),
    )


@dataclass(frozen=True, slots=True)
class ValuationObservation:
    schema_version: str
    native_asset: str
    quote_asset: str
    current_rate: ExactDecimal
    conservative_liquidation_rate: ExactDecimal

    def __post_init__(self) -> None:
        if self.schema_version != "valuation-observation/v1":
            raise ValueError("unsupported valuation observation schema")
        if self.native_asset == self.quote_asset:
            raise ValueError("quote asset does not require a valuation observation")
        if any(
            value.kind != "valuation_rate" or value.decimal < 0
            for value in (self.current_rate, self.conservative_liquidation_rate)
        ):
            raise ValueError("valuation rates must be non-negative exact rates")
        if self.conservative_liquidation_rate.decimal > self.current_rate.decimal:
            raise ValueError("conservative liquidation rate cannot exceed current rate")

    @classmethod
    def create(
        cls,
        native_asset: str,
        quote_asset: str,
        current_rate: str,
        conservative_liquidation_rate: str,
    ) -> ValuationObservation:
        return cls(
            schema_version="valuation-observation/v1",
            native_asset=native_asset,
            quote_asset=quote_asset,
            current_rate=ExactDecimal.parse(current_rate, kind="valuation_rate"),
            conservative_liquidation_rate=ExactDecimal.parse(
                conservative_liquidation_rate, kind="valuation_rate"
            ),
        )


@dataclass(frozen=True, slots=True)
class EquityProjection:
    schema_version: str
    projection: str
    quote_asset: str
    amount: Decimal | None
    unavailable_assets: tuple[str, ...]
    observation_fingerprints: tuple[str, ...]

    @property
    def fingerprint(self) -> str:
        return content_identity(self.schema_version, self)


@dataclass(frozen=True, slots=True)
class FeeQuoteValuation:
    native_asset: str
    native_amount: Decimal
    quote_asset: str
    amount: Decimal | None


def _valuation_map(
    quote_asset: str, observations: Iterable[ValuationObservation]
) -> dict[str, ValuationObservation]:
    values: dict[str, ValuationObservation] = {}
    for item in observations:
        if item.quote_asset != quote_asset:
            raise ValueError("valuation observation uses the wrong quote asset")
        if item.native_asset in values:
            raise ValueError("valuation observations must be unique per native asset")
        values[item.native_asset] = item
    return values


def _equity(
    projection: AllocationProjection,
    *,
    quote_asset: str,
    observations: Iterable[ValuationObservation],
    conservative: bool,
) -> EquityProjection:
    values = _valuation_map(quote_asset, observations)
    total = projection.balance(quote_asset)
    unavailable: list[str] = []
    used: list[str] = []
    owned_assets = sorted(
        {
            item.native_asset
            for item in projection.balances
            if item.account in _OWNED_ACCOUNTS and item.quantity != 0
        }
    )
    for asset in owned_assets:
        if asset == quote_asset:
            continue
        quantity = projection.balance(asset)
        observation = values.get(asset)
        if observation is None:
            unavailable.append(asset)
            continue
        rate = (
            observation.conservative_liquidation_rate if conservative else observation.current_rate
        )
        total += quantity * rate.decimal
        used.append(content_identity("valuation-observation/v1", observation))
    schema = "conservative-liquidation-equity/v1" if conservative else "current-grid-equity/v1"
    return EquityProjection(
        schema_version=schema,
        projection=("CONSERVATIVE_LIQUIDATION" if conservative else "CURRENT_GRID"),
        quote_asset=quote_asset,
        amount=None if unavailable else total,
        unavailable_assets=tuple(unavailable),
        observation_fingerprints=tuple(sorted(used)),
    )


def current_grid_equity(
    projection: AllocationProjection,
    *,
    quote_asset: str,
    observations: Iterable[ValuationObservation],
) -> EquityProjection:
    return _equity(
        projection,
        quote_asset=quote_asset,
        observations=observations,
        conservative=False,
    )


def conservative_liquidation_equity(
    projection: AllocationProjection,
    *,
    quote_asset: str,
    observations: Iterable[ValuationObservation],
) -> EquityProjection:
    return _equity(
        projection,
        quote_asset=quote_asset,
        observations=observations,
        conservative=True,
    )


def fee_quote_valuation(
    projection: AllocationProjection,
    *,
    quote_asset: str,
    observations: Iterable[ValuationObservation],
) -> dict[str, FeeQuoteValuation]:
    values = _valuation_map(quote_asset, observations)
    result: dict[str, FeeQuoteValuation] = {}
    fee_assets = sorted(
        {
            item.native_asset
            for item in projection.balances
            if item.account is Account.FEE_EXPENSE and item.quantity != 0
        }
    )
    for asset in fee_assets:
        native_amount = projection.fee_paid(asset)
        if asset == quote_asset:
            amount: Decimal | None = native_amount
        else:
            observation = values.get(asset)
            amount = (
                None if observation is None else native_amount * observation.current_rate.decimal
            )
        result[asset] = FeeQuoteValuation(
            native_asset=asset,
            native_amount=native_amount,
            quote_asset=quote_asset,
            amount=amount,
        )
    return result
