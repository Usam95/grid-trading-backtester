from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, localcontext

import pytest

from gridlab.accounting.allocation import (
    AllocationProjection,
    ManagedOrderState,
    allocation_funding_batch,
    apply_posting_batch,
    cumulative_grid_fill_batch,
    managed_order_state_batch,
)
from gridlab.canonical.events import DomainTime
from gridlab.canonical.values import ExactDecimal


UTC = timezone.utc
EVENT_TIME = DomainTime(datetime(2025, 1, 2, tzinfo=UTC))
RUN_ID = "run:ticket-08"
ALLOCATION_ID = "allocation:ticket-08"
EPOCH_ID = "epoch:origin"


def exact(value: str) -> ExactDecimal:
    return ExactDecimal.parse(value, kind="native_asset_quantity")


def funded(*, third_asset: str = "0") -> AllocationProjection:
    return apply_posting_batch(
        AllocationProjection.initial(RUN_ID, ALLOCATION_ID),
        allocation_funding_batch(
            run_id=RUN_ID,
            allocation_id=ALLOCATION_ID,
            grid_plan_epoch_id=EPOCH_ID,
            source_event_id="event:funding",
            event_time=EVENT_TIME,
            processing_position=1,
            assets={
                "EUR": exact("1000.00"),
                "BNB": exact(third_asset),
            },
        ),
    )


def with_buy_order(
    *,
    requested_base: str = "1.00000000",
    fixed_quote_principal: str = "100.00",
    quantity_step: str = "0.00100000",
    minimum_quantity: str = "0.00100000",
    third_asset: str = "0",
) -> AllocationProjection:
    return apply_posting_batch(
        funded(third_asset=third_asset),
        managed_order_state_batch(
            run_id=RUN_ID,
            allocation_id=ALLOCATION_ID,
            grid_plan_epoch_id=EPOCH_ID,
            source_event_id="event:buy-order",
            event_time=EVENT_TIME,
            processing_position=2,
            order_id="order:buy",
            rung_id="rung:buy",
            side="BUY",
            state=ManagedOrderState.ACTIVE,
            base_asset="BTC",
            quote_asset="EUR",
            requested_base_quantity=exact(requested_base),
            fixed_quote_principal=exact(fixed_quote_principal),
            paired_rung_id="rung:sell",
            paired_price=exact("110.00"),
            venue_quantity_step=exact(quantity_step),
            venue_minimum_quantity=exact(minimum_quantity),
            lot_id="lot:buy",
        ),
    )


def buy_fill(
    *,
    position: int,
    fill_id: str,
    source_event_id: str,
    base_quantity: str,
    quote_quantity: str,
    fee_asset: str,
    fee_quantity: str,
    state: ManagedOrderState,
):
    return cumulative_grid_fill_batch(
        run_id=RUN_ID,
        allocation_id=ALLOCATION_ID,
        grid_plan_epoch_id=EPOCH_ID,
        source_event_id=source_event_id,
        event_time=EVENT_TIME,
        processing_position=position,
        side="BUY",
        base_asset="BTC",
        quote_asset="EUR",
        base_quantity=exact(base_quantity),
        quote_quantity=exact(quote_quantity),
        fee_asset=fee_asset,
        fee_quantity=exact(fee_quantity),
        order_id="order:buy",
        fill_id=fill_id,
        lot_id="lot:buy",
        origin_epoch_id=EPOCH_ID,
        order_state=state,
    )


def test_partial_fills_accumulate_monotonically_under_one_paired_obligation() -> None:
    state = with_buy_order()
    first = apply_posting_batch(
        state,
        buy_fill(
            position=3,
            fill_id="fill:buy:1",
            source_event_id="event:buy-fill:1",
            base_quantity="0.40000000",
            quote_quantity="40.00",
            fee_asset="BTC",
            fee_quantity="0.00400000",
            state=ManagedOrderState.PARTIALLY_FILLED,
        ),
    )
    second = apply_posting_batch(
        first,
        buy_fill(
            position=4,
            fill_id="fill:buy:2",
            source_event_id="event:buy-fill:2",
            base_quantity="0.60000000",
            quote_quantity="60.00",
            fee_asset="BTC",
            fee_quantity="0.00600000",
            state=ManagedOrderState.FILLED,
        ),
    )

    first_order = first.managed_order("order:buy")
    second_order = second.managed_order("order:buy")
    assert first_order.cumulative_base_quantity == Decimal("0.40000000")
    assert second_order.cumulative_base_quantity == Decimal("1.00000000")
    assert second_order.cumulative_net_base_quantity == Decimal("0.99000000")
    assert len(second.pair_obligations) == 1
    assert first.pair_obligations[0].obligation_id == second.pair_obligations[0].obligation_id
    assert second.pair_obligations[0].paired_base_quantity == Decimal("0.99000000")
    assert second.pair_obligations[0].origin_epoch_id == EPOCH_ID
    assert len([item for item in second.managed_orders if item.rung_id == "rung:sell"]) == 1


def test_duplicate_fill_is_a_projection_no_op() -> None:
    state = with_buy_order()
    fill = buy_fill(
        position=3,
        fill_id="fill:buy:1",
        source_event_id="event:buy-fill:1",
        base_quantity="1.00000000",
        quote_quantity="100.00",
        fee_asset="EUR",
        fee_quantity="0.10",
        state=ManagedOrderState.FILLED,
    )
    admitted = apply_posting_batch(state, fill)
    duplicate = buy_fill(
        position=4,
        fill_id="fill:buy:1",
        source_event_id="event:duplicate-delivery",
        base_quantity="1.00000000",
        quote_quantity="100.00",
        fee_asset="EUR",
        fee_quantity="0.10",
        state=ManagedOrderState.FILLED,
    )

    assert apply_posting_batch(admitted, duplicate) == admitted


@pytest.mark.parametrize(
    "blocking_state",
    [ManagedOrderState.OUTCOME_UNKNOWN, ManagedOrderState.CANCELLATION_PENDING],
)
def test_each_epoch_rung_has_only_one_effective_order_in_ambiguous_states(
    blocking_state: ManagedOrderState,
) -> None:
    state = with_buy_order()
    unknown = apply_posting_batch(
        state,
        managed_order_state_batch(
            run_id=RUN_ID,
            allocation_id=ALLOCATION_ID,
            grid_plan_epoch_id=EPOCH_ID,
            source_event_id=f"event:{blocking_state.value.lower()}",
            event_time=EVENT_TIME,
            processing_position=3,
            order_id="order:buy",
            rung_id="rung:buy",
            side="BUY",
            state=blocking_state,
            base_asset="BTC",
            quote_asset="EUR",
            requested_base_quantity=exact("1.00000000"),
            fixed_quote_principal=exact("100.00"),
            paired_rung_id="rung:sell",
            paired_price=exact("110.00"),
            venue_quantity_step=exact("0.00100000"),
            venue_minimum_quantity=exact("0.00100000"),
            lot_id="lot:buy",
        ),
    )

    with pytest.raises(ValueError, match="effective managed order"):
        apply_posting_batch(
            unknown,
            managed_order_state_batch(
                run_id=RUN_ID,
                allocation_id=ALLOCATION_ID,
                grid_plan_epoch_id=EPOCH_ID,
                source_event_id="event:conflicting-order",
                event_time=EVENT_TIME,
                processing_position=4,
                order_id="order:other",
                rung_id="rung:buy",
                side="SELL",
                state=ManagedOrderState.ACTIVE,
                base_asset="BTC",
                quote_asset="EUR",
                requested_base_quantity=exact("1.00000000"),
                fixed_quote_principal=exact("100.00"),
                paired_rung_id="rung:sell",
                paired_price=exact("110.00"),
                venue_quantity_step=exact("0.00100000"),
                venue_minimum_quantity=exact("0.00100000"),
                lot_id="lot:other",
            ),
        )


@pytest.mark.parametrize(
    ("fee_asset", "fee_quantity", "third_asset", "expected"),
    [
        ("BTC", "0.01000000", "0", "0.99000000"),
        ("EUR", "0.10", "0", "1.00000000"),
        ("BNB", "0.01000000", "1.00000000", "1.00000000"),
    ],
)
def test_paired_quantity_uses_actual_net_acquired_base(
    fee_asset: str,
    fee_quantity: str,
    third_asset: str,
    expected: str,
) -> None:
    state = with_buy_order(third_asset=third_asset)
    projected = apply_posting_batch(
        state,
        buy_fill(
            position=3,
            fill_id=f"fill:{fee_asset}",
            source_event_id=f"event:{fee_asset}",
            base_quantity="1.00000000",
            quote_quantity="100.00",
            fee_asset=fee_asset,
            fee_quantity=fee_quantity,
            state=ManagedOrderState.FILLED,
        ),
    )

    assert projected.pair_obligations[0].paired_base_quantity == Decimal(expected)


def test_cycle_completes_once_with_exact_result_and_fixed_principal_replacement() -> None:
    bought = apply_posting_batch(
        with_buy_order(),
        buy_fill(
            position=3,
            fill_id="fill:buy",
            source_event_id="event:buy",
            base_quantity="1.00000000",
            quote_quantity="100.00",
            fee_asset="BTC",
            fee_quantity="0.01000000",
            state=ManagedOrderState.FILLED,
        ),
    )
    obligation = bought.pair_obligations[0]
    sold = apply_posting_batch(
        bought,
        cumulative_grid_fill_batch(
            run_id=RUN_ID,
            allocation_id=ALLOCATION_ID,
            grid_plan_epoch_id=EPOCH_ID,
            source_event_id="event:sell",
            event_time=EVENT_TIME,
            processing_position=4,
            side="SELL",
            base_asset="BTC",
            quote_asset="EUR",
            base_quantity=exact("0.99000000"),
            quote_quantity=exact("108.90"),
            fee_asset="EUR",
            fee_quantity=exact("0.1089"),
            order_id=obligation.paired_order_id,
            fill_id="fill:sell",
            lot_id="lot:buy",
            origin_epoch_id=EPOCH_ID,
            order_state=ManagedOrderState.FILLED,
            paired_obligation_id=obligation.obligation_id,
        ),
    )

    assert len(sold.completed_cycles) == 1
    cycle = sold.completed_cycles[0]
    assert cycle.origin_epoch_id == EPOCH_ID
    assert cycle.acquisition_quote_quantity == Decimal("100.00")
    assert cycle.proceeds_quote_quantity == Decimal("108.90")
    assert cycle.attributable_fees == (
        ("BTC", Decimal("0.01000000")),
        ("EUR", Decimal("0.1089")),
    )
    assert cycle.realized_quote_result == Decimal("8.7911")
    replacement = sold.managed_order(cycle.replacement_order_id)
    assert replacement.fixed_quote_principal == Decimal("100.00")
    assert replacement.fixed_quote_principal != cycle.proceeds_quote_quantity

    duplicate = cumulative_grid_fill_batch(
        run_id=RUN_ID,
        allocation_id=ALLOCATION_ID,
        grid_plan_epoch_id=EPOCH_ID,
        source_event_id="event:sell-duplicate",
        event_time=EVENT_TIME,
        processing_position=5,
        side="SELL",
        base_asset="BTC",
        quote_asset="EUR",
        base_quantity=exact("0.99000000"),
        quote_quantity=exact("108.90"),
        fee_asset="EUR",
        fee_quantity=exact("0.1089"),
        order_id=obligation.paired_order_id,
        fill_id="fill:sell",
        lot_id="lot:buy",
        origin_epoch_id=EPOCH_ID,
        order_state=ManagedOrderState.FILLED,
        paired_obligation_id=obligation.obligation_id,
    )
    assert apply_posting_batch(sold, duplicate) == sold


def test_cycle_completion_waits_for_later_terminal_order_evidence() -> None:
    bought = apply_posting_batch(
        with_buy_order(),
        buy_fill(
            position=3,
            fill_id="fill:buy",
            source_event_id="event:buy",
            base_quantity="1.00000000",
            quote_quantity="100.00",
            fee_asset="EUR",
            fee_quantity="0",
            state=ManagedOrderState.PARTIALLY_FILLED,
        ),
    )
    obligation = bought.pair_obligations[0]
    sold = apply_posting_batch(
        bought,
        cumulative_grid_fill_batch(
            run_id=RUN_ID,
            allocation_id=ALLOCATION_ID,
            grid_plan_epoch_id=EPOCH_ID,
            source_event_id="event:sell",
            event_time=EVENT_TIME,
            processing_position=4,
            side="SELL",
            base_asset="BTC",
            quote_asset="EUR",
            base_quantity=exact("1.00000000"),
            quote_quantity=exact("110.00"),
            fee_asset="EUR",
            fee_quantity=exact("0.11"),
            order_id=obligation.paired_order_id,
            fill_id="fill:sell",
            lot_id="lot:buy",
            origin_epoch_id=EPOCH_ID,
            order_state=ManagedOrderState.FILLED,
            paired_obligation_id=obligation.obligation_id,
        ),
    )
    assert sold.completed_cycles == ()

    finalized = apply_posting_batch(
        sold,
        managed_order_state_batch(
            run_id=RUN_ID,
            allocation_id=ALLOCATION_ID,
            grid_plan_epoch_id=EPOCH_ID,
            source_event_id="event:buy-terminal",
            event_time=EVENT_TIME,
            processing_position=5,
            order_id="order:buy",
            rung_id="rung:buy",
            side="BUY",
            state=ManagedOrderState.FILLED,
            base_asset="BTC",
            quote_asset="EUR",
            requested_base_quantity=exact("1.00000000"),
            fixed_quote_principal=exact("100.00"),
            paired_rung_id="rung:sell",
            paired_price=exact("110.00"),
            venue_quantity_step=exact("0.00100000"),
            venue_minimum_quantity=exact("0.00100000"),
            lot_id="lot:buy",
        ),
    )

    assert len(finalized.completed_cycles) == 1
    assert finalized.completed_cycles[0].proceeds_quote_quantity == Decimal("110.00")


def test_later_source_fill_creates_one_new_effective_pair_generation() -> None:
    first_buy = apply_posting_batch(
        with_buy_order(),
        buy_fill(
            position=3,
            fill_id="fill:buy:1",
            source_event_id="event:buy:1",
            base_quantity="0.40000000",
            quote_quantity="40.00",
            fee_asset="EUR",
            fee_quantity="0",
            state=ManagedOrderState.PARTIALLY_FILLED,
        ),
    )
    obligation = first_buy.pair_obligations[0]
    first_sell = apply_posting_batch(
        first_buy,
        cumulative_grid_fill_batch(
            run_id=RUN_ID,
            allocation_id=ALLOCATION_ID,
            grid_plan_epoch_id=EPOCH_ID,
            source_event_id="event:sell:1",
            event_time=EVENT_TIME,
            processing_position=4,
            side="SELL",
            base_asset="BTC",
            quote_asset="EUR",
            base_quantity=exact("0.40000000"),
            quote_quantity=exact("44.00"),
            fee_asset="EUR",
            fee_quantity=exact("0.044"),
            order_id=obligation.paired_order_id,
            fill_id="fill:sell:1",
            lot_id="lot:buy",
            origin_epoch_id=EPOCH_ID,
            order_state=ManagedOrderState.FILLED,
            paired_obligation_id=obligation.obligation_id,
        ),
    )
    accumulated = apply_posting_batch(
        first_sell,
        buy_fill(
            position=5,
            fill_id="fill:buy:2",
            source_event_id="event:buy:2",
            base_quantity="0.60000000",
            quote_quantity="60.00",
            fee_asset="EUR",
            fee_quantity="0",
            state=ManagedOrderState.FILLED,
        ),
    )

    cumulative = accumulated.pair_obligations[0]
    assert len(accumulated.pair_obligations) == 1
    assert cumulative.cumulative_sold_base_quantity == Decimal("0.40000000")
    assert cumulative.paired_base_quantity == Decimal("1.00000000")
    assert cumulative.paired_order_id != obligation.paired_order_id
    active_pairs = [
        item
        for item in accumulated.managed_orders
        if item.rung_id == "rung:sell" and item.state is ManagedOrderState.ACTIVE
    ]
    assert len(active_pairs) == 1
    assert active_pairs[0].requested_base_quantity == Decimal("0.60000000")


def test_authoritative_late_fill_after_cancel_preserves_terminal_order_state() -> None:
    cancelled = apply_posting_batch(
        with_buy_order(),
        managed_order_state_batch(
            run_id=RUN_ID,
            allocation_id=ALLOCATION_ID,
            grid_plan_epoch_id=EPOCH_ID,
            source_event_id="event:cancelled",
            event_time=EVENT_TIME,
            processing_position=3,
            order_id="order:buy",
            rung_id="rung:buy",
            side="BUY",
            state=ManagedOrderState.CANCELLED,
            base_asset="BTC",
            quote_asset="EUR",
            requested_base_quantity=exact("1.00000000"),
            fixed_quote_principal=exact("100.00"),
            paired_rung_id="rung:sell",
            paired_price=exact("110.00"),
            venue_quantity_step=exact("0.00100000"),
            venue_minimum_quantity=exact("0.00100000"),
            lot_id="lot:buy",
        ),
    )
    late = apply_posting_batch(
        cancelled,
        buy_fill(
            position=4,
            fill_id="fill:late",
            source_event_id="event:late",
            base_quantity="0.50000000",
            quote_quantity="50.00",
            fee_asset="EUR",
            fee_quantity="0.05",
            state=ManagedOrderState.FILLED,
        ),
    )

    assert late.managed_order("order:buy").state is ManagedOrderState.CANCELLED
    assert late.managed_order("order:buy").cumulative_base_quantity == Decimal("0.50000000")
    assert late.pair_obligations[0].origin_epoch_id == EPOCH_ID


def test_venue_quantization_is_independent_of_ambient_decimal_context() -> None:
    with localcontext() as context:
        context.prec = 3
        projected = apply_posting_batch(
            with_buy_order(quantity_step="0.01000000", minimum_quantity="0.01000000"),
            buy_fill(
                position=3,
                fill_id="fill:context",
                source_event_id="event:context",
                base_quantity="1.00000000",
                quote_quantity="100.00",
                fee_asset="BTC",
                fee_quantity="0.00500000",
                state=ManagedOrderState.FILLED,
            ),
        )

    assert projected.pair_obligations[0].paired_base_quantity == Decimal("0.99000000")


def test_venue_dust_remains_owned_with_origin_epoch_provenance() -> None:
    bought = apply_posting_batch(
        with_buy_order(quantity_step="0.01000000", minimum_quantity="0.01000000"),
        buy_fill(
            position=3,
            fill_id="fill:buy",
            source_event_id="event:buy",
            base_quantity="1.00000000",
            quote_quantity="100.00",
            fee_asset="BTC",
            fee_quantity="0.00500000",
            state=ManagedOrderState.PARTIALLY_FILLED,
        ),
    )

    obligation = bought.pair_obligations[0]
    assert obligation.paired_base_quantity == Decimal("0.99000000")
    assert obligation.residual_base_quantity == Decimal("0.00500000")
    assert bought.residuals[0].origin_epoch_id == EPOCH_ID
    assert bought.residuals[0].quantity == Decimal("0.00500000")
    assert bought.lot("lot:buy").inventory_quantity == Decimal("0.99500000")

    finalized = apply_posting_batch(
        bought,
        managed_order_state_batch(
            run_id=RUN_ID,
            allocation_id=ALLOCATION_ID,
            grid_plan_epoch_id=EPOCH_ID,
            source_event_id="event:buy-finalized",
            event_time=EVENT_TIME,
            processing_position=4,
            order_id="order:buy",
            rung_id="rung:buy",
            side="BUY",
            state=ManagedOrderState.RECONCILED_TERMINAL,
            base_asset="BTC",
            quote_asset="EUR",
            requested_base_quantity=exact("1.00000000"),
            fixed_quote_principal=exact("100.00"),
            paired_rung_id="rung:sell",
            paired_price=exact("110.00"),
            venue_quantity_step=exact("0.01000000"),
            venue_minimum_quantity=exact("0.01000000"),
            lot_id="lot:buy",
        ),
    )
    assert finalized.residuals[0].classification == "RETAINED_RESIDUAL"


def test_venue_invalid_quantity_remains_owned_without_creating_a_paired_order() -> None:
    bought = apply_posting_batch(
        with_buy_order(
            requested_base="0.00500000",
            fixed_quote_principal="0.50",
            quantity_step="0.00100000",
            minimum_quantity="0.01000000",
        ),
        buy_fill(
            position=3,
            fill_id="fill:small-buy",
            source_event_id="event:small-buy",
            base_quantity="0.00500000",
            quote_quantity="0.50",
            fee_asset="EUR",
            fee_quantity="0",
            state=ManagedOrderState.FILLED,
        ),
    )

    obligation = bought.pair_obligations[0]
    assert obligation.paired_base_quantity == 0
    assert obligation.residual_base_quantity == Decimal("0.00500000")
    assert obligation.paired_order_id not in {item.order_id for item in bought.managed_orders}
    assert bought.lot("lot:buy").inventory_quantity == Decimal("0.00500000")


def test_late_old_epoch_fill_keeps_its_origin_after_newer_epoch_evidence() -> None:
    cancelling = apply_posting_batch(
        with_buy_order(),
        managed_order_state_batch(
            run_id=RUN_ID,
            allocation_id=ALLOCATION_ID,
            grid_plan_epoch_id=EPOCH_ID,
            source_event_id="event:cancel-pending",
            event_time=EVENT_TIME,
            processing_position=3,
            order_id="order:buy",
            rung_id="rung:buy",
            side="BUY",
            state=ManagedOrderState.CANCELLATION_PENDING,
            base_asset="BTC",
            quote_asset="EUR",
            requested_base_quantity=exact("1.00000000"),
            fixed_quote_principal=exact("100.00"),
            paired_rung_id="rung:sell",
            paired_price=exact("110.00"),
            venue_quantity_step=exact("0.00100000"),
            venue_minimum_quantity=exact("0.00100000"),
            lot_id="lot:buy",
        ),
    )
    newer_epoch = apply_posting_batch(
        cancelling,
        managed_order_state_batch(
            run_id=RUN_ID,
            allocation_id=ALLOCATION_ID,
            grid_plan_epoch_id="epoch:newer",
            source_event_id="event:newer-epoch-order",
            event_time=EVENT_TIME,
            processing_position=4,
            order_id="order:newer",
            rung_id="rung:newer",
            side="BUY",
            state=ManagedOrderState.ACTIVE,
            base_asset="BTC",
            quote_asset="EUR",
            requested_base_quantity=exact("0.50000000"),
            fixed_quote_principal=exact("100.00"),
            paired_rung_id="rung:newer-sell",
            paired_price=exact("120.00"),
            venue_quantity_step=exact("0.00100000"),
            venue_minimum_quantity=exact("0.00100000"),
            lot_id="lot:newer",
        ),
    )
    late_fill = apply_posting_batch(
        newer_epoch,
        buy_fill(
            position=5,
            fill_id="fill:late-old",
            source_event_id="event:late-old",
            base_quantity="1.00000000",
            quote_quantity="100.00",
            fee_asset="EUR",
            fee_quantity="0.10",
            state=ManagedOrderState.FILLED,
        ),
    )

    assert late_fill.managed_order("order:buy").grid_plan_epoch_id == EPOCH_ID
    assert late_fill.fills[-1].origin_epoch_id == EPOCH_ID
    assert late_fill.lot("lot:buy").origin_epoch_id == EPOCH_ID
    assert late_fill.pair_obligations[0].origin_epoch_id == EPOCH_ID
