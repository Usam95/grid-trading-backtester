from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal, ROUND_FLOOR, localcontext

from gridlab.api.facade import (
    BacktestSpec,
    _build_config,
    _build_data,
    _build_strategy,
    _enrich_indicators,
    run_backtest,
)
from gridlab.canonical._identity import content_identity
from gridlab.canonical.adaptation import (
    AdaptationState,
    AdaptationObservation,
    ConfirmationEvidence,
    EvidenceQuality,
    decide_adaptation,
)
from gridlab.canonical.configuration import (
    AdaptationPolicy,
    Spacing,
    StrategyConfiguration,
)
from gridlab.canonical.events import CanonicalEvent, DomainTime, EventSource
from gridlab.canonical.plan import (
    AllocationAssumptions,
    DerivedGridPlan,
    GridObligation,
    GridPlanEpoch,
    QuantizedRung,
    VenueRuleEvidence,
)
from gridlab.canonical.values import ExactDecimal
from gridlab.config.models import GridConfig
from gridlab.core.events import OrderCancelledEvent
from gridlab.engine.engine import BacktestEngine


def _exact(value: str, kind: str) -> ExactDecimal:
    return ExactDecimal.parse(value, kind=kind)


@dataclass(frozen=True, slots=True)
class LegacyCharacterization:
    legacy_spec: dict
    legacy_result: dict
    configuration: StrategyConfiguration
    observation: AdaptationObservation
    event: CanonicalEvent
    epoch: GridPlanEpoch
    legacy_cancelled_orders: int
    legacy_effective_atr_multiplier: str
    differences: tuple[str, ...]


def characterize_legacy_backtest(
    *,
    symbol: str,
    decision_time: DomainTime,
    trend: str = "0.0000",
    volatility: str = "0.0100",
    reference_price: str = "100.00",
    complete: bool = True,
    quality: EvidenceQuality = EvidenceQuality.ADMITTED,
) -> LegacyCharacterization:
    if not symbol.endswith("EUR") or len(symbol) <= 3:
        raise ValueError("canonical characterization requires an EUR-quoted symbol")
    legacy_spec = {
        "symbol": symbol,
        "market_type": "spot",
        "initial_cash": 1000.0,
        "grid": {
            "levels": 5,
            "spacing": "geometric",
            "direction": "neutral",
            "adaptive": True,
            "lookback": 24,
            "atr_period": 14,
            "recenter_drift_frac": 0.20,
        },
        "sizing": {"mode": "fixed_quote", "value": 20.0},
        "fees": {"maker": 0.001, "taker": 0.001},
        "data": {
            "kind": "synthetic",
            "n": 120,
            "start_price": 100.0,
            "seed": 7,
            "sigma": 0.004,
            "regime": "range",
            "interval_minutes": 60,
        },
    }
    legacy_result = run_backtest(legacy_spec, include_trades=False)
    legacy_spec_object = BacktestSpec.from_dict(legacy_spec)
    legacy_grid = GridConfig(**legacy_spec_object.grid)
    legacy_data = _enrich_indicators(_build_data(legacy_spec_object), legacy_grid)
    legacy_engine_result = BacktestEngine(_build_config(legacy_spec_object)).run(
        legacy_data, _build_strategy(legacy_spec_object)
    )
    legacy_cancelled_orders = sum(
        isinstance(event, OrderCancelledEvent) for event in legacy_engine_result.events
    )
    policy = AdaptationPolicy(
        schema_version="adaptation-policy/v1",
        observation_window=timedelta(hours=24),
        maximum_observation_age=timedelta(minutes=15),
        trend_threshold=_exact("0.0100", "ratio"),
        high_volatility_threshold=_exact("0.0250", "ratio"),
        confirmation_count=2,
        hysteresis=_exact("0.0010", "ratio"),
        minimum_epoch_residence=timedelta(hours=6),
        transition_cooldown=timedelta(hours=2),
        transition_expiry=timedelta(minutes=10),
        maximum_transitions_per_day=3,
        normal_width=_exact("0.0400", "ratio"),
        high_volatility_width=_exact("0.0800", "ratio"),
        maximum_width=_exact("0.1000", "ratio"),
        maximum_upward_shift=_exact("0.0300", "ratio"),
    )
    configuration = StrategyConfiguration(
        schema_version="strategy-configuration/v1",
        symbol=symbol,
        base_asset=symbol.removesuffix("EUR"),
        quote_asset="EUR",
        adaptation_policy=policy,
        rung_count=5,
        spacing=Spacing.GEOMETRIC,
        fixed_quote_principal=_exact("20.00", "quote_quantity"),
        maker_fee=_exact("0.0010", "fee_rate"),
        taker_fee=_exact("0.0010", "fee_rate"),
        maximum_quote_capital=_exact("250.00", "quote_quantity"),
        fee_reserve=_exact("5.00", "quote_quantity"),
        stop_price=_exact("80.00", "price"),
        lower_bound_limit=_exact("85.00", "price"),
        upper_bound_limit=_exact("120.00", "price"),
        execution_policy_id="limit-maker-ordinary/v1",
        risk_profile_id="mvp1-first-live-ceilings/v1",
    )
    trend_decimal = Decimal(trend)
    if trend_decimal <= -policy.trend_threshold.decimal:
        candidate_state = AdaptationState.TREND_DOWN
    elif trend_decimal >= policy.trend_threshold.decimal:
        candidate_state = AdaptationState.TREND_UP
    elif Decimal(volatility) >= policy.high_volatility_threshold.decimal:
        candidate_state = AdaptationState.RANGE_HIGH_VOLATILITY
    else:
        candidate_state = AdaptationState.RANGE_NORMAL
    confirmations = tuple(
        ConfirmationEvidence(
            schema_version="adaptation-confirmation/v1",
            state=candidate_state,
            observation_id=content_identity(
                "legacy-confirmation-observation/v1",
                {"symbol": symbol, "position": position, "state": candidate_state},
            ),
            decision_time=DomainTime(decision_time.value - timedelta(minutes=3 - position)),
        )
        for position in range(1, policy.confirmation_count + 1)
    )
    observation = AdaptationObservation(
        schema_version="adaptation-observation/v1",
        source=EventSource("legacy-backtest-translation", f"{symbol}:synthetic:7"),
        event_time=decision_time,
        window_start=DomainTime(decision_time.value - timedelta(hours=24)),
        window_end=decision_time,
        complete=complete,
        quality=quality,
        sequence_start=1,
        sequence_end=24,
        expected_count=24,
        observed_count=24,
        confirmations=confirmations,
        prior_decision=None,
        trend=_exact(trend, "ratio"),
        volatility=_exact(volatility, "ratio"),
        reference_price=_exact(reference_price, "price"),
    )
    decision = decide_adaptation(policy, observation, decision_time)
    event = CanonicalEvent.create(
        schema=observation.schema_version,
        source=observation.source,
        source_event_key=observation.observation_id,
        source_sequence=observation.sequence_end,
        event_time=observation.event_time,
        received_time=decision_time,
        correlation_id=f"legacy-characterization:{symbol}",
        causation_id=None,
        payload={
            "observation_id": observation.observation_id,
            "trend": observation.trend,
            "volatility": observation.volatility,
            "reference_price": observation.reference_price,
        },
    )
    with localcontext() as context:
        context.prec = 40
        lower = Decimal("90.00")
        upper = Decimal("110.00")
        ratio = (upper / lower) ** (Decimal(1) / Decimal(4))
        unquantized_rungs = tuple(
            lower if index == 0 else upper if index == 4 else lower * ratio**index
            for index in range(5)
        )
    quantized_prices = tuple(
        price.quantize(Decimal("0.01"), rounding=ROUND_FLOOR) for price in unquantized_rungs
    )
    if decision.state is AdaptationState.UNCERTAIN:
        roles = tuple("INACTIVE" for _ in quantized_prices)
    elif decision.state is AdaptationState.TREND_DOWN:
        roles = tuple(
            "SELL" if price > Decimal(reference_price) else "INACTIVE" for price in quantized_prices
        )
    else:
        roles = tuple(
            "BUY"
            if price < Decimal(reference_price)
            else "SELL"
            if price > Decimal(reference_price)
            else "INACTIVE"
            for price in quantized_prices
        )
    plan = DerivedGridPlan(
        schema_version="grid-plan/v1",
        lower=_exact("90.00", "price"),
        upper=_exact("110.00", "price"),
        reference_price=_exact(reference_price, "price"),
        unquantized_rungs=tuple(_exact(format(price, "f"), "price") for price in unquantized_rungs),
        rungs=tuple(
            QuantizedRung(
                index,
                _exact(format(price, "f"), "price"),
                roles[index],
            )
            for index, price in enumerate(quantized_prices)
        ),
        fixed_quote_principal=_exact("20.00", "quote_quantity"),
        obligations=tuple(
            GridObligation(
                rung_index=index,
                role=role,
                fixed_quote_principal=_exact("20.00", "quote_quantity"),
            )
            for index, role in enumerate(roles)
            if role != "INACTIVE"
        ),
        allocation_assumptions=AllocationAssumptions(
            quote_allocation=_exact("245.00", "quote_quantity"),
            base_allocation=_exact("0.00000", "base_quantity"),
            fee_reserve=_exact("5.00", "quote_quantity"),
        ),
        derivation_semantics="bounded-symmetric-geometric/v1",
    )
    venue_rules = VenueRuleEvidence(
        schema_version="venue-rules/v1",
        source=EventSource("legacy-backtest-translation", f"{symbol}:rules"),
        observed_at=decision_time,
        environment="production",
        tick_size=_exact("0.01", "price_increment"),
        step_size=_exact("0.00001", "quantity_increment"),
        minimum_price=_exact("0.01", "price"),
        maximum_price=None,
        minimum_quantity=_exact("0.00010", "base_quantity"),
        maximum_quantity=None,
        minimum_notional=_exact("5.00", "quote_quantity"),
        maximum_notional=None,
    )
    epoch = GridPlanEpoch.derive(
        configuration=configuration,
        observation=observation,
        decision=decision,
        predecessor_epoch_id=None,
        derivation_causation_id=event.event_id,
        venue_rules=venue_rules,
        plan=plan,
    )
    return LegacyCharacterization(
        legacy_spec=legacy_spec,
        legacy_result=legacy_result,
        configuration=configuration,
        observation=observation,
        event=event,
        epoch=epoch,
        legacy_cancelled_orders=legacy_cancelled_orders,
        legacy_effective_atr_multiplier=format(legacy_grid.atr_mult, ".1f"),
        differences=(
            "canonical policy does not inherit the legacy nonzero atr_mult default",
            "canonical seam emits no immediate cancel-all/rebuild transition",
            "canonical classification fails closed on incomplete or ambiguous evidence",
            "canonical characterization applies the MVP 250.00 EUR capital envelope instead of the legacy 1000.0 initial cash",
            "canonical venue-rule evidence is an explicit translation assumption absent from the legacy backtest",
        ),
    )
