from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from enum import Enum

from gridlab.canonical._identity import content_identity
from gridlab.canonical.values import ExactDecimal


class Spacing(str, Enum):
    ARITHMETIC = "ARITHMETIC"
    GEOMETRIC = "GEOMETRIC"


def _require_kind(value: ExactDecimal, expected: str, field_name: str) -> None:
    if value.kind != expected:
        raise ValueError(f"{field_name} must use exact kind {expected}")


@dataclass(frozen=True, slots=True)
class AdaptationPolicy:
    schema_version: str
    observation_window: timedelta
    maximum_observation_age: timedelta
    trend_threshold: ExactDecimal
    high_volatility_threshold: ExactDecimal
    confirmation_count: int
    hysteresis: ExactDecimal
    minimum_epoch_residence: timedelta
    transition_cooldown: timedelta
    transition_expiry: timedelta
    maximum_transitions_per_day: int
    normal_width: ExactDecimal
    high_volatility_width: ExactDecimal
    maximum_width: ExactDecimal
    maximum_upward_shift: ExactDecimal

    def __post_init__(self) -> None:
        durations = (
            self.observation_window,
            self.maximum_observation_age,
            self.minimum_epoch_residence,
            self.transition_cooldown,
            self.transition_expiry,
        )
        if self.schema_version != "adaptation-policy/v1":
            raise ValueError("unsupported adaptation policy schema version")
        if any(duration <= timedelta(0) for duration in durations):
            raise ValueError("adaptation policy durations must be positive")
        if self.confirmation_count < 1 or self.maximum_transitions_per_day < 1:
            raise ValueError("adaptation policy counts must be positive")
        exact_values = (
            self.trend_threshold,
            self.high_volatility_threshold,
            self.hysteresis,
            self.normal_width,
            self.high_volatility_width,
            self.maximum_width,
            self.maximum_upward_shift,
        )
        if any(value.decimal < 0 for value in exact_values):
            raise ValueError("adaptation policy exact values must be non-negative")
        for field_name in (
            "trend_threshold",
            "high_volatility_threshold",
            "hysteresis",
            "normal_width",
            "high_volatility_width",
            "maximum_width",
            "maximum_upward_shift",
        ):
            _require_kind(getattr(self, field_name), "ratio", field_name)
        if self.trend_threshold.decimal <= 0 or self.high_volatility_threshold.decimal <= 0:
            raise ValueError("classification thresholds must be positive")
        if self.hysteresis.decimal >= self.trend_threshold.decimal:
            raise ValueError("hysteresis must remain below the trend threshold")
        if self.normal_width.decimal > self.high_volatility_width.decimal:
            raise ValueError("normal width cannot exceed high-volatility width")
        if self.high_volatility_width.decimal > self.maximum_width.decimal:
            raise ValueError("high-volatility width cannot exceed maximum width")

    @property
    def policy_id(self) -> str:
        return content_identity("adaptation-policy/v1", self)


@dataclass(frozen=True, slots=True)
class StrategyConfiguration:
    schema_version: str
    symbol: str
    base_asset: str
    quote_asset: str
    adaptation_policy: AdaptationPolicy
    rung_count: int
    spacing: Spacing
    fixed_quote_principal: ExactDecimal
    maker_fee: ExactDecimal
    taker_fee: ExactDecimal
    maximum_quote_capital: ExactDecimal
    fee_reserve: ExactDecimal
    stop_price: ExactDecimal
    lower_bound_limit: ExactDecimal
    upper_bound_limit: ExactDecimal
    execution_policy_id: str
    risk_profile_id: str

    def __post_init__(self) -> None:
        if self.schema_version != "strategy-configuration/v1":
            raise ValueError("unsupported strategy configuration schema version")
        if not self.symbol or not self.base_asset or not self.quote_asset:
            raise ValueError("symbol and asset identities are required")
        if self.symbol != f"{self.base_asset}{self.quote_asset}":
            raise ValueError("symbol must equal the canonical base and quote asset pair")
        if self.rung_count < 2:
            raise ValueError("rung count must include at least both bounds")
        _require_kind(self.fixed_quote_principal, "quote_quantity", "fixed_quote_principal")
        _require_kind(self.maker_fee, "fee_rate", "maker_fee")
        _require_kind(self.taker_fee, "fee_rate", "taker_fee")
        _require_kind(self.maximum_quote_capital, "quote_quantity", "maximum_quote_capital")
        _require_kind(self.fee_reserve, "quote_quantity", "fee_reserve")
        for field_name in ("stop_price", "lower_bound_limit", "upper_bound_limit"):
            _require_kind(getattr(self, field_name), "price", field_name)
        positive = (
            self.fixed_quote_principal,
            self.maximum_quote_capital,
            self.fee_reserve,
            self.stop_price,
            self.lower_bound_limit,
            self.upper_bound_limit,
        )
        if any(value.decimal <= 0 for value in positive):
            raise ValueError("strategy price and quantity values must be positive")
        if self.maker_fee.decimal < 0 or self.taker_fee.decimal < 0:
            raise ValueError("fee assumptions must be non-negative")
        if self.lower_bound_limit.decimal >= self.upper_bound_limit.decimal:
            raise ValueError("lower bound limit must be below upper bound limit")
        if self.stop_price.decimal >= self.lower_bound_limit.decimal:
            raise ValueError("stop price must remain below the lower bound limit")
        if self.fee_reserve.decimal >= self.maximum_quote_capital.decimal:
            raise ValueError("fee reserve must remain below maximum quote capital")
        if not self.execution_policy_id or not self.risk_profile_id:
            raise ValueError("execution policy and risk profile identities are required")

    @property
    def configuration_id(self) -> str:
        return content_identity("strategy-configuration/v1", self)
