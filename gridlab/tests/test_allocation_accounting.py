from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
import json
from pathlib import Path

import pytest

from gridlab.accounting.allocation import (
    Account,
    AllocationProjection,
    AssetPosting,
    InvariantResult,
    PostingBatch,
    PostingCause,
    ReservationState,
    ValuationObservation,
    allocation_funding_batch,
    apply_posting_batch,
    conservative_liquidation_equity,
    current_grid_equity,
    fee_quote_valuation,
    spot_fill_batch,
)
from gridlab.canonical.events import DomainTime
from gridlab.canonical.values import ExactDecimal


UTC = timezone.utc
EVENT_TIME = DomainTime(datetime(2025, 1, 2, tzinfo=UTC))
RUN_ID = "run:ticket-07"
ALLOCATION_ID = "allocation:ticket-07"
EPOCH_1 = "epoch:one"
EPOCH_2 = "epoch:two"
SOURCE_1 = "event:allocation-opened"


def exact(value: str, kind: str = "native_asset_quantity") -> ExactDecimal:
    return ExactDecimal.parse(value, kind=kind)


def posting(
    *,
    position: int,
    asset: str,
    account: Account,
    amount: str,
    cause: PostingCause,
    epoch: str = EPOCH_1,
    source_event_id: str = SOURCE_1,
    transition_id: str | None = None,
    order_id: str | None = None,
    fill_id: str | None = None,
    cycle_id: str | None = None,
    obligation_id: str | None = None,
    reservation_state: ReservationState | None = None,
    lot_id: str | None = None,
    origin_epoch_id: str | None = None,
    paired_lot_id: str | None = None,
) -> AssetPosting:
    return AssetPosting(
        schema_version="asset-posting/v1",
        run_id=RUN_ID,
        allocation_id=ALLOCATION_ID,
        grid_plan_epoch_id=epoch,
        native_asset=asset,
        account=account,
        amount=exact(amount),
        cause=cause,
        source_event_id=source_event_id,
        event_time=EVENT_TIME,
        processing_position=position,
        transition_id=transition_id,
        order_id=order_id,
        fill_id=fill_id,
        cycle_id=cycle_id,
        obligation_id=obligation_id,
        reservation_state=reservation_state,
        lot_id=lot_id,
        origin_epoch_id=origin_epoch_id,
        paired_lot_id=paired_lot_id,
    )


def batch(position: int, *postings: AssetPosting, source: str = SOURCE_1) -> PostingBatch:
    return PostingBatch(
        schema_version="posting-batch/v1",
        run_id=RUN_ID,
        allocation_id=ALLOCATION_ID,
        source_event_id=source,
        event_time=EVENT_TIME,
        processing_position=position,
        postings=postings,
    )


def funded_projection(
    *,
    quote: str = "1000.00",
    base: str = "0",
    third: str = "0",
) -> AllocationProjection:
    initial = AllocationProjection.initial(RUN_ID, ALLOCATION_ID)
    funding = allocation_funding_batch(
        run_id=RUN_ID,
        allocation_id=ALLOCATION_ID,
        grid_plan_epoch_id=EPOCH_1,
        source_event_id=SOURCE_1,
        event_time=EVENT_TIME,
        processing_position=1,
        assets={"EUR": exact(quote), "BTC": exact(base), "BNB": exact(third)},
        inventory_assets={"BTC"},
    )
    return apply_posting_batch(initial, funding)


def test_posting_metadata_and_atomic_batch_invariants() -> None:
    state = funded_projection()
    assert state.last_batch is not None
    stored = state.last_batch.postings[0]

    assert (
        stored.run_id,
        stored.allocation_id,
        stored.grid_plan_epoch_id,
        stored.native_asset,
        stored.amount.source,
        stored.cause,
        stored.source_event_id,
        stored.event_time,
        stored.processing_position,
        stored.schema_version,
    ) == (
        RUN_ID,
        ALLOCATION_ID,
        EPOCH_1,
        "BNB",
        "0",
        PostingCause.ALLOCATION_FUNDING,
        SOURCE_1,
        EVENT_TIME,
        1,
        "asset-posting/v1",
    )
    assert state.last_invariants.passed
    assert state.last_invariants.checks == (
        "native_asset_conservation",
        "posting_balance",
        "allocation_ownership",
        "reservation_coverage",
        "bootstrap_backing",
    )

    invalid = batch(
        2,
        posting(
            position=2,
            asset="EUR",
            account=Account.AVAILABLE,
            amount="-1.00",
            cause=PostingCause.FILL_PRINCIPAL,
            order_id="order:1",
            fill_id="fill:1",
            source_event_id="event:bad-fill",
        ),
        source="event:bad-fill",
    )
    with pytest.raises(ValueError, match="posting balance"):
        apply_posting_batch(state, invalid)
    assert state.processing_position == 1
    assert state.balance("EUR") == exact("1000.00").decimal


def test_allocation_isolation_ownership_and_no_top_up() -> None:
    state = funded_projection()
    foreign = allocation_funding_batch(
        run_id=RUN_ID,
        allocation_id="allocation:foreign",
        grid_plan_epoch_id=EPOCH_1,
        source_event_id="event:foreign",
        event_time=EVENT_TIME,
        processing_position=2,
        assets={"EUR": exact("1.00")},
    )
    with pytest.raises(ValueError, match="allocation"):
        apply_posting_batch(state, foreign)

    top_up = allocation_funding_batch(
        run_id=RUN_ID,
        allocation_id=ALLOCATION_ID,
        grid_plan_epoch_id=EPOCH_1,
        source_event_id="event:account-balance-top-up",
        event_time=EVENT_TIME,
        processing_position=2,
        assets={"EUR": exact("1.00")},
    )
    with pytest.raises(ValueError, match="initial atomic batch"):
        apply_posting_batch(state, top_up)

    overspend = batch(
        2,
        posting(
            position=2,
            asset="EUR",
            account=Account.AVAILABLE,
            amount="-1001.00",
            cause=PostingCause.FILL_PRINCIPAL,
            order_id="order:overspend",
            fill_id="fill:overspend",
            source_event_id="event:overspend",
        ),
        posting(
            position=2,
            asset="EUR",
            account=Account.EXTERNAL,
            amount="1001.00",
            cause=PostingCause.FILL_PRINCIPAL,
            order_id="order:overspend",
            fill_id="fill:overspend",
            source_event_id="event:overspend",
        ),
        source="event:overspend",
    )
    with pytest.raises(ValueError, match="allocation ownership"):
        apply_posting_batch(state, overspend)


def test_reservation_coverage_and_bootstrap_backing() -> None:
    state = funded_projection(base="2.00000000")
    reserve = batch(
        2,
        posting(
            position=2,
            asset="BTC",
            account=Account.INVENTORY,
            amount="-1.50000000",
            cause=PostingCause.RESERVATION,
            order_id="order:sell-1",
            obligation_id="obligation:sell-1",
            reservation_state=ReservationState.ACTIVE,
            lot_id="lot:bootstrap",
            origin_epoch_id=EPOCH_1,
            source_event_id="event:reserve",
        ),
        posting(
            position=2,
            asset="BTC",
            account=Account.RESERVED,
            amount="1.50000000",
            cause=PostingCause.RESERVATION,
            order_id="order:sell-1",
            obligation_id="obligation:sell-1",
            reservation_state=ReservationState.ACTIVE,
            lot_id="lot:bootstrap",
            origin_epoch_id=EPOCH_1,
            source_event_id="event:reserve",
        ),
        posting(
            position=2,
            asset="BTC",
            account=Account.BOOTSTRAP_REQUIREMENT,
            amount="1.50000000",
            cause=PostingCause.BOOTSTRAP_REQUIREMENT,
            source_event_id="event:reserve",
        ),
        posting(
            position=2,
            asset="BTC",
            account=Account.MEMO_OFFSET,
            amount="-1.50000000",
            cause=PostingCause.BOOTSTRAP_REQUIREMENT,
            source_event_id="event:reserve",
        ),
        source="event:reserve",
    )
    reserved = apply_posting_batch(state, reserve)
    assert reserved.reservation("obligation:sell-1").quantity == exact("1.50000000").decimal
    assert reserved.last_invariants.passed

    insufficient = replace(
        reserve,
        postings=tuple(
            replace(item, processing_position=2, amount=exact("2.50000000"))
            if item.account is Account.BOOTSTRAP_REQUIREMENT
            else replace(item, processing_position=2, amount=exact("-2.50000000"))
            if item.account is Account.MEMO_OFFSET
            else item
            for item in reserve.postings
        ),
    )
    with pytest.raises(ValueError, match="bootstrap backing"):
        apply_posting_batch(state, insufficient)

    with pytest.raises(ValueError, match="reservation metadata"):
        posting(
            position=2,
            asset="EUR",
            account=Account.RESERVED,
            amount="10.00",
            cause=PostingCause.RESERVATION,
            source_event_id="event:untracked",
        )


@pytest.mark.parametrize(
    "case",
    json.loads(
        (Path(__file__).parent / "fixtures" / "ticket07_fee_cases.json").read_text(encoding="utf-8")
    ),
    ids=lambda case: case["name"],
)
def test_golden_native_fee_asset_cases(case: dict[str, str]) -> None:
    state = funded_projection(
        base="1.00000000" if case["side"] == "SELL" else "0",
        third="1.00000000",
    )
    fill = spot_fill_batch(
        run_id=RUN_ID,
        allocation_id=ALLOCATION_ID,
        grid_plan_epoch_id=EPOCH_1,
        source_event_id=f"event:{case['name']}",
        event_time=EVENT_TIME,
        processing_position=2,
        side=case["side"],
        base_asset="BTC",
        quote_asset="EUR",
        base_quantity=exact(case["base_quantity"]),
        quote_quantity=exact(case["quote_quantity"]),
        fee_asset=case["fee_asset"],
        fee_quantity=exact(case["fee_quantity"]),
        order_id=f"order:{case['name']}",
        fill_id=f"fill:{case['name']}",
        cycle_id="cycle:one" if case["side"] == "SELL" else None,
        lot_id="lot:bootstrap" if case["side"] == "SELL" else "lot:buy-one",
        origin_epoch_id=EPOCH_1,
        paired_lot_id="lot:bootstrap" if case["side"] == "SELL" else None,
    )
    projected = apply_posting_batch(state, fill)

    assert projected.balance("BTC") == exact(case["expected_base"]).decimal
    assert projected.balance("EUR") == exact(case["expected_quote"]).decimal
    assert projected.fee_paid(case["fee_asset"]) == exact(case["expected_fee"]).decimal
    fee_postings = [
        item
        for item in fill.postings
        if item.cause is PostingCause.FEE and item.account is Account.FEE_EXPENSE
    ]
    assert len(fee_postings) == 1
    assert fee_postings[0].native_asset == case["fee_asset"]


def test_quote_fee_reporting_is_valuation_only() -> None:
    state = funded_projection(third="1.00000000")
    fill = spot_fill_batch(
        run_id=RUN_ID,
        allocation_id=ALLOCATION_ID,
        grid_plan_epoch_id=EPOCH_1,
        source_event_id="event:third-fee",
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
        origin_epoch_id=EPOCH_1,
    )
    projected = apply_posting_batch(state, fill)
    fingerprint = projected.fingerprint

    valuation = fee_quote_valuation(
        projected,
        quote_asset="EUR",
        observations=(ValuationObservation.create("BNB", "EUR", "250.00", "240.00"),),
    )

    assert valuation["BNB"].amount == exact("2.5000000000", "quote_quantity").decimal
    assert projected.fingerprint == fingerprint
    assert projected.balance("BNB") == exact("0.99000000").decimal


def test_paired_lot_and_retained_inventory_preserve_origin_epoch() -> None:
    state = funded_projection()
    bought = apply_posting_batch(
        state,
        spot_fill_batch(
            run_id=RUN_ID,
            allocation_id=ALLOCATION_ID,
            grid_plan_epoch_id=EPOCH_1,
            source_event_id="event:buy",
            event_time=EVENT_TIME,
            processing_position=2,
            side="BUY",
            base_asset="BTC",
            quote_asset="EUR",
            base_quantity=exact("2.00000000"),
            quote_quantity=exact("200.00"),
            fee_asset="EUR",
            fee_quantity=exact("0.20"),
            order_id="order:buy",
            fill_id="fill:buy",
            lot_id="lot:buy",
            origin_epoch_id=EPOCH_1,
        ),
    )
    sold = apply_posting_batch(
        bought,
        spot_fill_batch(
            run_id=RUN_ID,
            allocation_id=ALLOCATION_ID,
            grid_plan_epoch_id=EPOCH_1,
            source_event_id="event:sell",
            event_time=EVENT_TIME,
            processing_position=3,
            side="SELL",
            base_asset="BTC",
            quote_asset="EUR",
            base_quantity=exact("1.00000000"),
            quote_quantity=exact("110.00"),
            fee_asset="EUR",
            fee_quantity=exact("0.11"),
            order_id="order:sell",
            fill_id="fill:sell",
            cycle_id="cycle:paired",
            lot_id="lot:buy",
            origin_epoch_id=EPOCH_1,
            paired_lot_id="lot:buy",
        ),
    )
    retained = apply_posting_batch(
        sold,
        batch(
            4,
            posting(
                position=4,
                asset="BTC",
                account=Account.INVENTORY,
                amount="-1.00000000",
                cause=PostingCause.RETAIN_INVENTORY,
                lot_id="lot:buy",
                origin_epoch_id=EPOCH_1,
                transition_id="transition:stop",
                source_event_id="event:retain",
            ),
            posting(
                position=4,
                asset="BTC",
                account=Account.RETAINED,
                amount="1.00000000",
                cause=PostingCause.RETAIN_INVENTORY,
                lot_id="lot:buy",
                origin_epoch_id=EPOCH_1,
                transition_id="transition:stop",
                source_event_id="event:retain",
            ),
            source="event:retain",
        ),
    )

    lot = retained.lot("lot:buy")
    assert lot.origin_epoch_id == EPOCH_1
    assert lot.inventory_quantity == 0
    assert lot.retained_quantity == exact("1.00000000").decimal
    assert sold.last_batch is not None
    assert sold.last_batch.postings[0].paired_lot_id == "lot:buy"


def test_pending_old_epoch_obligation_cannot_be_reassigned() -> None:
    state = funded_projection()
    active = apply_posting_batch(
        state,
        batch(
            2,
            posting(
                position=2,
                asset="EUR",
                account=Account.AVAILABLE,
                amount="-100.00",
                cause=PostingCause.RESERVATION,
                order_id="order:old",
                obligation_id="obligation:old",
                reservation_state=ReservationState.ACTIVE,
                source_event_id="event:reserve-old",
            ),
            posting(
                position=2,
                asset="EUR",
                account=Account.RESERVED,
                amount="100.00",
                cause=PostingCause.RESERVATION,
                order_id="order:old",
                obligation_id="obligation:old",
                reservation_state=ReservationState.ACTIVE,
                source_event_id="event:reserve-old",
            ),
            source="event:reserve-old",
        ),
    )
    pending = apply_posting_batch(
        active,
        batch(
            3,
            posting(
                position=3,
                asset="EUR",
                account=Account.RESERVED,
                amount="0",
                cause=PostingCause.RESERVATION_STATUS,
                epoch=EPOCH_1,
                transition_id="transition:replace",
                order_id="order:old",
                obligation_id="obligation:old",
                reservation_state=ReservationState.CANCELLATION_PENDING,
                source_event_id="event:cancel-pending",
            ),
            source="event:cancel-pending",
        ),
    )
    reassign = batch(
        4,
        posting(
            position=4,
            asset="EUR",
            account=Account.RESERVED,
            amount="-100.00",
            cause=PostingCause.RESERVATION_RELEASE,
            epoch=EPOCH_1,
            transition_id="transition:replace",
            order_id="order:old",
            obligation_id="obligation:old",
            reservation_state=ReservationState.CANCELLATION_PENDING,
            source_event_id="event:reassign",
        ),
        posting(
            position=4,
            asset="EUR",
            account=Account.RESERVED,
            amount="100.00",
            cause=PostingCause.RESERVATION,
            epoch=EPOCH_2,
            transition_id="transition:replace",
            order_id="order:new",
            obligation_id="obligation:new",
            reservation_state=ReservationState.ACTIVE,
            source_event_id="event:reassign",
        ),
        source="event:reassign",
    )

    with pytest.raises(ValueError, match="pending old-epoch obligation"):
        apply_posting_batch(pending, reassign)
    assert pending.reservation("obligation:old").quantity == exact("100.00").decimal


def test_reconciled_old_epoch_obligation_can_release_exact_commitment() -> None:
    state = funded_projection()
    active = apply_posting_batch(
        state,
        batch(
            2,
            posting(
                position=2,
                asset="EUR",
                account=Account.AVAILABLE,
                amount="-100.00",
                cause=PostingCause.RESERVATION,
                order_id="order:old",
                obligation_id="obligation:old",
                reservation_state=ReservationState.ACTIVE,
                source_event_id="event:reserve-old",
            ),
            posting(
                position=2,
                asset="EUR",
                account=Account.RESERVED,
                amount="100.00",
                cause=PostingCause.RESERVATION,
                order_id="order:old",
                obligation_id="obligation:old",
                reservation_state=ReservationState.ACTIVE,
                source_event_id="event:reserve-old",
            ),
            source="event:reserve-old",
        ),
    )
    pending = apply_posting_batch(
        active,
        batch(
            3,
            posting(
                position=3,
                asset="EUR",
                account=Account.RESERVED,
                amount="0",
                cause=PostingCause.RESERVATION_STATUS,
                transition_id="transition:replace",
                order_id="order:old",
                obligation_id="obligation:old",
                reservation_state=ReservationState.OUTCOME_UNKNOWN,
                source_event_id="event:outcome-unknown",
            ),
            source="event:outcome-unknown",
        ),
    )
    reconciled = apply_posting_batch(
        pending,
        batch(
            4,
            posting(
                position=4,
                asset="EUR",
                account=Account.RESERVED,
                amount="-100.00",
                cause=PostingCause.RESERVATION_RELEASE,
                transition_id="transition:replace",
                order_id="order:old",
                obligation_id="obligation:old",
                reservation_state=ReservationState.RECONCILED_TERMINAL,
                source_event_id="event:reconciled",
            ),
            posting(
                position=4,
                asset="EUR",
                account=Account.AVAILABLE,
                amount="100.00",
                cause=PostingCause.RESERVATION_RELEASE,
                transition_id="transition:replace",
                order_id="order:old",
                obligation_id="obligation:old",
                reservation_state=ReservationState.RECONCILED_TERMINAL,
                source_event_id="event:reconciled",
            ),
            source="event:reconciled",
        ),
    )

    assert reconciled.reservation("obligation:old").quantity == 0
    assert reconciled.reservation("obligation:old").state is ReservationState.RECONCILED_TERMINAL
    assert reconciled.balance("EUR", Account.RESERVED) == 0


def test_current_and_conservative_equity_are_distinct_and_unavailable_is_explicit() -> None:
    state = funded_projection(base="1.00000000", third="0.01000000")
    observations = (
        ValuationObservation.create("BTC", "EUR", "110.00", "105.00"),
        ValuationObservation.create("BNB", "EUR", "250.00", "240.00"),
    )

    current = current_grid_equity(state, quote_asset="EUR", observations=observations)
    conservative = conservative_liquidation_equity(
        state, quote_asset="EUR", observations=observations
    )
    unavailable = current_grid_equity(
        state,
        quote_asset="EUR",
        observations=(observations[0],),
    )

    assert current.amount == exact("1112.5000000000", "quote_quantity").decimal
    assert conservative.amount == exact("1107.4000000000", "quote_quantity").decimal
    assert current.fingerprint != conservative.fingerprint
    assert unavailable.amount is None
    assert unavailable.unavailable_assets == ("BNB",)


def test_fill_identity_is_required_for_fill_postings() -> None:
    with pytest.raises(ValueError, match="order and fill identity"):
        posting(
            position=1,
            asset="EUR",
            account=Account.AVAILABLE,
            amount="-1.00",
            cause=PostingCause.FILL_PRINCIPAL,
        )


def test_posting_batch_and_projection_reject_invalid_canonical_shapes() -> None:
    valid = posting(
        position=1,
        asset="EUR",
        account=Account.EXTERNAL,
        amount="0",
        cause=PostingCause.ALLOCATION_FUNDING,
    )
    invalid_postings = (
        {"schema_version": "asset-posting/v0"},
        {"run_id": ""},
        {"native_asset": "eur"},
        {"amount": ExactDecimal.parse("0", kind="quote_quantity")},
        {"processing_position": 0},
        {
            "cause": PostingCause.RESERVATION_STATUS,
            "amount": exact("1"),
        },
        {
            "account": Account.INVENTORY,
            "lot_id": None,
            "origin_epoch_id": None,
        },
        {"origin_epoch_id": EPOCH_1},
        {
            "paired_lot_id": "lot:other",
            "lot_id": "lot:one",
            "cycle_id": "cycle:one",
        },
        {"cause": PostingCause.RETAIN_INVENTORY},
    )
    for changes in invalid_postings:
        with pytest.raises(ValueError):
            replace(valid, **changes)

    with pytest.raises(ValueError, match="schema"):
        replace(batch(1, valid), schema_version="posting-batch/v0")
    with pytest.raises(ValueError, match="identities"):
        replace(batch(1, valid), source_event_id="")
    with pytest.raises(ValueError, match="position and postings"):
        replace(batch(1, valid), postings=())
    with pytest.raises(ValueError, match="metadata"):
        replace(batch(1, valid), run_id="run:other")
    with pytest.raises(ValueError, match="invariant schema"):
        InvariantResult("allocation-invariants/v0", (), True)
    with pytest.raises(ValueError, match="projection schema"):
        replace(
            AllocationProjection.initial(RUN_ID, ALLOCATION_ID),
            schema_version="allocation-projection/v0",
        )
    with pytest.raises(ValueError, match="replay fingerprint"):
        replace(
            AllocationProjection.initial(RUN_ID, ALLOCATION_ID),
            replay_fingerprint="",
        )
    with pytest.raises(ValueError, match="identity"):
        AllocationProjection.initial("", ALLOCATION_ID)
    with pytest.raises(KeyError):
        AllocationProjection.initial(RUN_ID, ALLOCATION_ID).reservation("missing")
    with pytest.raises(KeyError):
        AllocationProjection.initial(RUN_ID, ALLOCATION_ID).lot("missing")


def test_reservation_and_lot_state_reject_invalid_rewrites() -> None:
    state = funded_projection(base="1.00000000")
    active = apply_posting_batch(
        state,
        batch(
            2,
            posting(
                position=2,
                asset="EUR",
                account=Account.AVAILABLE,
                amount="-10.00",
                cause=PostingCause.RESERVATION,
                order_id="order:one",
                obligation_id="obligation:one",
                reservation_state=ReservationState.ACTIVE,
                source_event_id="event:reserve",
            ),
            posting(
                position=2,
                asset="EUR",
                account=Account.RESERVED,
                amount="10.00",
                cause=PostingCause.RESERVATION,
                order_id="order:one",
                obligation_id="obligation:one",
                reservation_state=ReservationState.ACTIVE,
                source_event_id="event:reserve",
            ),
            source="event:reserve",
        ),
    )
    pending = apply_posting_batch(
        active,
        batch(
            3,
            posting(
                position=3,
                asset="EUR",
                account=Account.RESERVED,
                amount="0",
                cause=PostingCause.RESERVATION_STATUS,
                order_id="order:one",
                obligation_id="obligation:one",
                reservation_state=ReservationState.CANCELLATION_PENDING,
                source_event_id="event:pending",
            ),
            source="event:pending",
        ),
    )
    invalid_transition = batch(
        4,
        posting(
            position=4,
            asset="EUR",
            account=Account.RESERVED,
            amount="0",
            cause=PostingCause.RESERVATION_STATUS,
            order_id="order:one",
            obligation_id="obligation:one",
            reservation_state=ReservationState.ACTIVE,
            source_event_id="event:invalid-transition",
        ),
        source="event:invalid-transition",
    )
    with pytest.raises(ValueError, match="state transition"):
        apply_posting_batch(pending, invalid_transition)

    unknown_release = batch(
        4,
        posting(
            position=4,
            asset="EUR",
            account=Account.RESERVED,
            amount="-1.00",
            cause=PostingCause.RESERVATION_RELEASE,
            order_id="order:unknown",
            obligation_id="obligation:unknown",
            reservation_state=ReservationState.RECONCILED_TERMINAL,
            source_event_id="event:unknown-release",
        ),
        posting(
            position=4,
            asset="EUR",
            account=Account.AVAILABLE,
            amount="1.00",
            cause=PostingCause.RESERVATION_RELEASE,
            order_id="order:unknown",
            obligation_id="obligation:unknown",
            reservation_state=ReservationState.RECONCILED_TERMINAL,
            source_event_id="event:unknown-release",
        ),
        source="event:unknown-release",
    )
    with pytest.raises(ValueError, match="unknown obligation"):
        apply_posting_batch(pending, unknown_release)

    zero_active = batch(
        4,
        posting(
            position=4,
            asset="EUR",
            account=Account.RESERVED,
            amount="0",
            cause=PostingCause.RESERVATION,
            order_id="order:zero",
            obligation_id="obligation:zero",
            reservation_state=ReservationState.ACTIVE,
            source_event_id="event:zero-active",
        ),
        source="event:zero-active",
    )
    with pytest.raises(ValueError, match="must remain committed"):
        apply_posting_batch(pending, zero_active)

    rewritten_lot = batch(
        2,
        posting(
            position=2,
            asset="BTC",
            account=Account.INVENTORY,
            amount="0",
            cause=PostingCause.RETAIN_INVENTORY,
            transition_id="transition:rewrite",
            lot_id="lot:bootstrap",
            origin_epoch_id=EPOCH_2,
            source_event_id="event:rewrite-lot",
        ),
        source="event:rewrite-lot",
    )
    with pytest.raises(ValueError, match="provenance"):
        apply_posting_batch(state, rewritten_lot)

    negative_lot = batch(
        2,
        posting(
            position=2,
            asset="BTC",
            account=Account.INVENTORY,
            amount="-2.00000000",
            cause=PostingCause.FILL_PRINCIPAL,
            order_id="order:negative",
            fill_id="fill:negative",
            lot_id="lot:bootstrap",
            origin_epoch_id=EPOCH_1,
            source_event_id="event:negative-lot",
        ),
        posting(
            position=2,
            asset="BTC",
            account=Account.EXTERNAL,
            amount="2.00000000",
            cause=PostingCause.FILL_PRINCIPAL,
            order_id="order:negative",
            fill_id="fill:negative",
            source_event_id="event:negative-lot",
        ),
        source="event:negative-lot",
    )
    with pytest.raises(ValueError, match="lot quantity"):
        apply_posting_batch(state, negative_lot)


def test_fill_and_valuation_contract_rejections_and_quote_fee_view() -> None:
    common = {
        "run_id": RUN_ID,
        "allocation_id": ALLOCATION_ID,
        "grid_plan_epoch_id": EPOCH_1,
        "source_event_id": "event:invalid-fill",
        "event_time": EVENT_TIME,
        "processing_position": 1,
        "base_asset": "BTC",
        "quote_asset": "EUR",
        "base_quantity": exact("1"),
        "quote_quantity": exact("100"),
        "fee_asset": "EUR",
        "fee_quantity": exact("0.1"),
        "order_id": "order:one",
        "fill_id": "fill:one",
        "lot_id": "lot:one",
        "origin_epoch_id": EPOCH_1,
    }
    with pytest.raises(ValueError, match="side"):
        spot_fill_batch(side="HOLD", **common)
    with pytest.raises(ValueError, match="non-negative"):
        spot_fill_batch(
            side="BUY",
            **{**common, "fee_quantity": exact("-0.1")},
        )

    with pytest.raises(ValueError, match="schema"):
        ValuationObservation(
            "valuation-observation/v0",
            "BTC",
            "EUR",
            ExactDecimal.parse("1", kind="valuation_rate"),
            ExactDecimal.parse("1", kind="valuation_rate"),
        )
    with pytest.raises(ValueError, match="does not require"):
        ValuationObservation.create("EUR", "EUR", "1", "1")
    with pytest.raises(ValueError, match="exact rates"):
        ValuationObservation(
            "valuation-observation/v1",
            "BTC",
            "EUR",
            exact("1"),
            ExactDecimal.parse("1", kind="valuation_rate"),
        )
    with pytest.raises(ValueError, match="cannot exceed"):
        ValuationObservation.create("BTC", "EUR", "1", "2")

    state = funded_projection()
    quote_fee_state = apply_posting_batch(
        state,
        spot_fill_batch(side="BUY", **{**common, "processing_position": 2}),
    )
    quote_fee = fee_quote_valuation(
        quote_fee_state,
        quote_asset="EUR",
        observations=(),
    )
    assert quote_fee["EUR"].amount == exact("0.1").decimal
    assert (
        fee_quote_valuation(
            quote_fee_state,
            quote_asset="EUR",
            observations=(ValuationObservation.create("BTC", "EUR", "100", "90"),),
        )["EUR"].amount
        == exact("0.1").decimal
    )
    with pytest.raises(ValueError, match="wrong quote"):
        current_grid_equity(
            quote_fee_state,
            quote_asset="EUR",
            observations=(ValuationObservation.create("BTC", "USD", "100", "90"),),
        )
    duplicate = ValuationObservation.create("BTC", "EUR", "100", "90")
    with pytest.raises(ValueError, match="unique"):
        current_grid_equity(
            quote_fee_state,
            quote_asset="EUR",
            observations=(duplicate, duplicate),
        )
