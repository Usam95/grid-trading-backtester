from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from gridlab.canonical.adaptation import AdaptationState, PriorDecisionEvidence
from gridlab.canonical.candle_simulation import (
    CandleBar,
    CandleLimitOrder,
    build_observation_from_closed_candles,
    conservative_fill_assumptions,
    parity_snapshot,
    resolve_candle_limit_fills,
)
from gridlab.canonical.configuration import AdaptationPolicy, Spacing, StrategyConfiguration
from gridlab.canonical.events import DomainTime, EventSource
from gridlab.canonical.initial_epoch import BootstrapEvidence
from gridlab.canonical.plan import VenueRuleEvidence
from gridlab.canonical.values import ExactDecimal


UTC = timezone.utc
BOUNDARY = datetime(2025, 1, 2, 12, 0, tzinfo=UTC)


def exact(value: str, kind: str = "ratio") -> ExactDecimal:
    return ExactDecimal.parse(value, kind=kind)


def policy() -> AdaptationPolicy:
    return AdaptationPolicy(
        schema_version="adaptation-policy/v1",
        observation_window=timedelta(hours=4),
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


def configuration() -> StrategyConfiguration:
    return StrategyConfiguration(
        schema_version="strategy-configuration/v1",
        symbol="BTCEUR",
        base_asset="BTC",
        quote_asset="EUR",
        adaptation_policy=policy(),
        rung_count=5,
        spacing=Spacing.GEOMETRIC,
        fixed_quote_principal=exact("20.00", "quote_quantity"),
        maker_fee=exact("0.0010", "fee_rate"),
        taker_fee=exact("0.0010", "fee_rate"),
        maximum_quote_capital=exact("250.00", "quote_quantity"),
        fee_reserve=exact("5.00", "quote_quantity"),
        stop_price=exact("80.00", "price"),
        lower_bound_limit=exact("85.00", "price"),
        upper_bound_limit=exact("120.00", "price"),
        execution_policy_id="limit-maker-ordinary/v1",
        risk_profile_id="mvp1-first-live-ceilings/v1",
    )


def venue_rules() -> VenueRuleEvidence:
    return VenueRuleEvidence(
        schema_version="venue-rules/v1",
        source=EventSource("fixture", "BTCEUR-rules"),
        observed_at=DomainTime(BOUNDARY),
        environment="production",
        tick_size=exact("0.01", "price_increment"),
        step_size=exact("0.00001", "quantity_increment"),
        minimum_price=exact("0.01", "price"),
        maximum_price=None,
        minimum_quantity=exact("0.00010", "base_quantity"),
        maximum_quantity=None,
        minimum_notional=exact("5.00", "quote_quantity"),
        maximum_notional=None,
        max_open_orders=100,
        foreign_open_orders=0,
        symbol_status="TRADING",
        spot_trading_allowed=True,
        limit_maker_supported=True,
        contradictory=False,
    )


def candles(*, closes: list[str], highs: list[str] | None = None, lows: list[str] | None = None):
    start = BOUNDARY - timedelta(hours=len(closes) - 1)
    bars: list[CandleBar] = []
    prior = closes[0]
    for index, close in enumerate(closes):
        high = highs[index] if highs is not None else format(max(float(prior), float(close)), ".2f")
        low = lows[index] if lows is not None else format(min(float(prior), float(close)), ".2f")
        bars.append(
            CandleBar(
                sequence=index + 1,
                closed_at=DomainTime(start + timedelta(hours=index)),
                open=exact(prior, "price"),
                high=exact(high, "price"),
                low=exact(low, "price"),
                close=exact(close, "price"),
                volume=exact("10.00000000", "base_quantity"),
                complete=True,
            )
        )
        prior = close
    return tuple(bars)


def test_conservative_fill_requires_resting_strict_penetration_and_shared_volume() -> None:
    bar = CandleBar(
        sequence=2,
        closed_at=DomainTime(BOUNDARY),
        open=exact("100.00", "price"),
        high=exact("101.00", "price"),
        low=exact("95.00", "price"),
        close=exact("96.00", "price"),
        volume=exact("10.00000000", "base_quantity"),
        complete=True,
    )
    results = resolve_candle_limit_fills(
        orders=(
            CandleLimitOrder(
                order_id="buy-same-candle",
                side="BUY",
                limit_price=exact("99.00", "price"),
                remaining_quantity=exact("1.00000000", "base_quantity"),
                resting_after_sequence=2,
            ),
            CandleLimitOrder(
                order_id="buy-touch-only",
                side="BUY",
                limit_price=exact("95.00", "price"),
                remaining_quantity=exact("1.00000000", "base_quantity"),
                resting_after_sequence=1,
            ),
            CandleLimitOrder(
                order_id="buy-partial",
                side="BUY",
                limit_price=exact("99.00", "price"),
                remaining_quantity=exact("1.00000000", "base_quantity"),
                resting_after_sequence=1,
            ),
            CandleLimitOrder(
                order_id="sell-partial",
                side="SELL",
                limit_price=exact("100.50", "price"),
                remaining_quantity=exact("1.00000000", "base_quantity"),
                resting_after_sequence=1,
            ),
        ),
        candle=bar,
        mode=conservative_fill_assumptions(),
    )

    assert results["buy-same-candle"].status == "NOT_RESTING"
    assert results["buy-touch-only"].status == "TOUCHED"
    assert results["sell-partial"].status == "FILLED"
    assert results["sell-partial"].filled_quantity.decimal == Decimal("0.5000000000")
    assert results["buy-partial"].status == "EXHAUSTED_VOLUME"


def test_conservative_fill_does_not_infer_favorable_gap_improvement() -> None:
    bar = CandleBar(
        sequence=3,
        closed_at=DomainTime(BOUNDARY),
        open=exact("90.00", "price"),
        high=exact("92.00", "price"),
        low=exact("88.00", "price"),
        close=exact("91.00", "price"),
        volume=exact("10.00000000", "base_quantity"),
        complete=True,
    )
    result = resolve_candle_limit_fills(
        orders=(
            CandleLimitOrder(
                order_id="buy-gap",
                side="BUY",
                limit_price=exact("95.00", "price"),
                remaining_quantity=exact("1.00000000", "base_quantity"),
                resting_after_sequence=2,
            ),
        ),
        candle=bar,
        mode=conservative_fill_assumptions(),
    )["buy-gap"]

    assert result.status == "FILLED"
    assert result.fill_price == exact("95.00", "price")


@pytest.mark.parametrize(
    ("series", "expected_state"),
    [
        (candles(closes=["100.00", "100.20", "100.10", "100.00"]), AdaptationState.RANGE_NORMAL),
        (
            candles(
                closes=["100.00", "100.40", "99.80", "100.10"],
                highs=["100.30", "103.00", "101.00", "102.90"],
                lows=["99.70", "97.00", "98.80", "97.10"],
            ),
            AdaptationState.RANGE_HIGH_VOLATILITY,
        ),
        (candles(closes=["100.00", "101.50", "102.50", "103.00"]), AdaptationState.TREND_UP),
        (candles(closes=["100.00", "98.50", "97.50", "96.50"]), AdaptationState.TREND_DOWN),
    ],
)
def test_candle_and_event_snapshots_match_for_equivalent_inputs(series, expected_state) -> None:
    snapshot = parity_snapshot(
        configuration=configuration(),
        venue_rules=venue_rules(),
        candles=series,
        decision_time=DomainTime(BOUNDARY),
        source=EventSource("fixture", "BTCEUR-1h"),
        bootstrap_evidence=BootstrapEvidence.incomplete(),
    )

    assert snapshot.candle.decision.state is expected_state
    assert snapshot.candle.decision == snapshot.event.decision
    assert snapshot.candle.batch == snapshot.event.batch
    assert snapshot.candle.state == snapshot.event.state
    assert snapshot.candle.activation == snapshot.event.activation


def test_candle_observation_excludes_future_and_incomplete_candles() -> None:
    closed = candles(closes=["100.00", "100.10", "100.20", "100.30"])
    incomplete = replace(closed[-1], sequence=5, complete=False, closed_at=DomainTime(BOUNDARY + timedelta(hours=1)))
    observation = build_observation_from_closed_candles(
        policy=policy(),
        candles=closed + (incomplete,),
        decision_time=DomainTime(BOUNDARY),
        source=EventSource("fixture", "BTCEUR-1h"),
    )

    assert observation.sequence_end == 4
    assert observation.event_time == DomainTime(BOUNDARY)
    assert observation.complete is True


def test_downtrend_no_chase_respects_prior_epoch_evidence() -> None:
    active = parity_snapshot(
        configuration=configuration(),
        venue_rules=venue_rules(),
        candles=candles(closes=["100.00", "100.20", "100.10", "100.00"]),
        decision_time=DomainTime(BOUNDARY),
        source=EventSource("fixture", "BTCEUR-1h"),
        bootstrap_evidence=BootstrapEvidence.incomplete(),
    ).candle
    observation = build_observation_from_closed_candles(
        policy=policy(),
        candles=candles(closes=["100.00", "98.50", "97.50", "96.50"]),
        decision_time=DomainTime(BOUNDARY),
        source=EventSource("fixture", "BTCEUR-1h"),
        prior_decision=PriorDecisionEvidence(
            state=active.decision.state,
            decision_id=active.decision.decision_id,
            decision_time=active.decision.decision_time,
        ),
    )

    snapshot = parity_snapshot(
        configuration=configuration(),
        venue_rules=venue_rules(),
        candles=candles(closes=["100.00", "98.50", "97.50", "96.50"]),
        decision_time=DomainTime(BOUNDARY),
        source=EventSource("fixture", "BTCEUR-1h"),
        bootstrap_evidence=BootstrapEvidence.incomplete(),
        prior_decision=observation.prior_decision,
    )

    assert snapshot.candle.decision.state is AdaptationState.TREND_DOWN
    assert snapshot.candle.decision.permits_exposure_increasing_buy is False
    assert snapshot.candle.decision.requested_bound_shift is None
    assert snapshot.candle.batch.requested_epoch_cause is None
