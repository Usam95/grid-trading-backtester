from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Iterable, Mapping

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


class ReservationState(str, Enum):
    ACTIVE = "ACTIVE"
    CANCELLATION_PENDING = "CANCELLATION_PENDING"
    OUTCOME_UNKNOWN = "OUTCOME_UNKNOWN"
    RECONCILED_TERMINAL = "RECONCILED_TERMINAL"


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
class PostingBatch:
    schema_version: str
    run_id: str
    allocation_id: str
    source_event_id: str
    event_time: DomainTime
    processing_position: int
    postings: tuple[AssetPosting, ...]

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

    @property
    def batch_id(self) -> str:
        return content_identity("posting-batch/v1", self)


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

    def __post_init__(self) -> None:
        if self.schema_version != "allocation-projection/v1":
            raise ValueError("unsupported allocation projection schema")
        for field_name in ("balances", "reservations", "lots"):
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
        )

    @property
    def fingerprint(self) -> str:
        return content_identity("allocation-projection/v1", self)

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


def apply_posting_batch(
    projection: AllocationProjection, batch: PostingBatch
) -> AllocationProjection:
    if batch.run_id != projection.run_id or batch.allocation_id != projection.allocation_id:
        raise ValueError("posting batch run or allocation does not own this subledger")
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
    common = {
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
