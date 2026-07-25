from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from types import MappingProxyType
from typing import Any, Mapping

from gridlab.canonical._identity import content_identity
from gridlab.canonical.adaptation import (
    AdaptationDecision,
    AdaptationObservation,
    AdaptationState,
)
from gridlab.canonical.configuration import Spacing, StrategyConfiguration
from gridlab.canonical.events import DomainTime, EventSource
from gridlab.canonical.values import ExactDecimal


@dataclass(frozen=True, slots=True)
class QuantizedRung:
    index: int
    price: ExactDecimal
    role: str

    def __post_init__(self) -> None:
        if self.index < 0 or self.price.decimal <= 0:
            raise ValueError("quantized rung index and price are invalid")
        if self.price.kind != "price":
            raise ValueError("quantized rung must use a price value")
        if self.role not in {"BUY", "SELL", "INACTIVE"}:
            raise ValueError("quantized rung role must be BUY, SELL, or INACTIVE")


@dataclass(frozen=True, slots=True)
class DerivedGridPlan:
    schema_version: str
    lower: ExactDecimal
    upper: ExactDecimal
    reference_price: ExactDecimal
    unquantized_rungs: tuple[ExactDecimal, ...]
    rungs: tuple[QuantizedRung, ...]
    fixed_quote_principal: ExactDecimal
    obligations: tuple[GridObligation, ...]
    allocation_assumptions: AllocationAssumptions
    derivation_semantics: str
    activation_price: ExactDecimal | None = None
    bootstrap_obligation: BootstrapObligation | None = None
    maximum_planned_inventory: ExactDecimal | None = None

    def __post_init__(self) -> None:
        if self.schema_version != "grid-plan/v1" or not self.derivation_semantics:
            raise ValueError("unsupported grid plan schema or missing derivation semantics")
        object.__setattr__(self, "unquantized_rungs", tuple(self.unquantized_rungs))
        object.__setattr__(self, "rungs", tuple(self.rungs))
        object.__setattr__(self, "obligations", tuple(self.obligations))
        if self.lower.decimal >= self.upper.decimal:
            raise ValueError("grid plan lower bound must be below upper bound")
        if any(value.kind != "price" for value in (self.lower, self.upper, self.reference_price)):
            raise ValueError("grid plan bounds and reference must use price values")
        if self.fixed_quote_principal.kind != "quote_quantity":
            raise ValueError("grid plan principal must use quote_quantity")
        activation_price = self.activation_price or self.reference_price
        if activation_price.kind != "price" or activation_price.decimal <= 0:
            raise ValueError("grid plan activation price must use a positive price value")
        if not self.lower.decimal < self.reference_price.decimal < self.upper.decimal:
            raise ValueError("reference price must be strictly inside grid bounds")
        if len(self.rungs) < 2:
            raise ValueError("grid plan requires at least two rungs")
        if len(self.unquantized_rungs) != len(self.rungs):
            raise ValueError("unquantized and quantized rung counts must match")
        if any(value.kind != "price" for value in self.unquantized_rungs):
            raise ValueError("unquantized rungs must use price values")
        if (
            self.unquantized_rungs[0].decimal != self.lower.decimal
            or self.unquantized_rungs[-1].decimal != self.upper.decimal
        ):
            raise ValueError("unquantized rungs must include both exact bounds")
        if tuple(rung.index for rung in self.rungs) != tuple(range(len(self.rungs))):
            raise ValueError("grid plan rung indices must be contiguous")
        prices = tuple(rung.price.decimal for rung in self.rungs)
        if prices != tuple(sorted(prices)) or len(set(prices)) != len(prices):
            raise ValueError("grid plan rung prices must be unique and ordered")
        if any(
            (rung.role == "BUY" and rung.price.decimal >= activation_price.decimal)
            or (rung.role == "SELL" and rung.price.decimal <= activation_price.decimal)
            for rung in self.rungs
        ):
            raise ValueError(
                "grid rung roles conflict with the reference price or activation price"
            )
        obligation_roles = tuple(
            (obligation.rung_index, obligation.role) for obligation in self.obligations
        )
        active_rung_roles = tuple(
            (rung.index, rung.role) for rung in self.rungs if rung.role != "INACTIVE"
        )
        if obligation_roles != active_rung_roles:
            raise ValueError("grid plan obligations must cover every active rung")
        if any(obligation.base_quantity is None for obligation in self.obligations):
            if self.bootstrap_obligation is not None or self.maximum_planned_inventory is not None:
                raise ValueError("obligation-backed plans require exact base quantities")
        if self.maximum_planned_inventory is not None:
            if (
                self.maximum_planned_inventory.kind != "base_quantity"
                or self.maximum_planned_inventory.decimal < 0
            ):
                raise ValueError("maximum planned inventory must be non-negative base quantity")
        if self.bootstrap_obligation is not None:
            sell_quantity = sum(
                (
                    obligation.base_quantity.decimal
                    for obligation in self.obligations
                    if obligation.role == "SELL" and obligation.base_quantity is not None
                ),
                Decimal("0"),
            )
            if self.bootstrap_obligation.net_base_required.decimal != sell_quantity:
                raise ValueError("bootstrap obligation must cover every initial sell quantity")


@dataclass(frozen=True, slots=True)
class GridObligation:
    rung_index: int
    role: str
    fixed_quote_principal: ExactDecimal
    base_quantity: ExactDecimal | None = None

    def __post_init__(self) -> None:
        if self.rung_index < 0 or self.role not in {"BUY", "SELL"}:
            raise ValueError("grid obligation rung and role are invalid")
        if (
            self.fixed_quote_principal.kind != "quote_quantity"
            or self.fixed_quote_principal.decimal <= 0
        ):
            raise ValueError("grid obligation principal must be positive quote quantity")
        if self.base_quantity is not None and (
            self.base_quantity.kind != "base_quantity" or self.base_quantity.decimal <= 0
        ):
            raise ValueError("grid obligation base quantity must be positive")


@dataclass(frozen=True, slots=True)
class BootstrapObligation:
    schema_version: str
    net_base_required: ExactDecimal
    gross_base_required: ExactDecimal
    fee_base_coverage: ExactDecimal

    def __post_init__(self) -> None:
        if self.schema_version != "bootstrap-obligation/v1":
            raise ValueError("unsupported bootstrap obligation schema")
        for field_name in (
            "net_base_required",
            "gross_base_required",
            "fee_base_coverage",
        ):
            value = getattr(self, field_name)
            if value.kind != "base_quantity" or value.decimal < 0:
                raise ValueError(f"{field_name} must be non-negative base quantity")
        if self.gross_base_required.decimal < self.net_base_required.decimal:
            raise ValueError("gross bootstrap quantity cannot be below the net obligation")
        if (
            self.gross_base_required.decimal - self.net_base_required.decimal
            != self.fee_base_coverage.decimal
        ):
            raise ValueError("bootstrap fee coverage must reconcile exactly")


@dataclass(frozen=True, slots=True)
class AllocationAssumptions:
    quote_allocation: ExactDecimal
    base_allocation: ExactDecimal
    fee_reserve: ExactDecimal

    def __post_init__(self) -> None:
        expected = {
            "quote_allocation": "quote_quantity",
            "base_allocation": "base_quantity",
            "fee_reserve": "quote_quantity",
        }
        for field_name, kind in expected.items():
            value = getattr(self, field_name)
            if value.kind != kind or value.decimal < 0:
                raise ValueError(f"{field_name} must be a non-negative {kind}")


@dataclass(frozen=True, slots=True)
class VenueRuleEvidence:
    schema_version: str
    source: EventSource
    observed_at: DomainTime
    tick_size: ExactDecimal
    step_size: ExactDecimal
    minimum_quantity: ExactDecimal
    minimum_notional: ExactDecimal

    def __post_init__(self) -> None:
        if self.schema_version != "venue-rules/v1":
            raise ValueError("unsupported venue-rule schema version")
        values = (
            self.tick_size,
            self.step_size,
            self.minimum_quantity,
            self.minimum_notional,
        )
        if any(value.decimal < 0 for value in values):
            raise ValueError("venue-rule values must be non-negative")
        expected = (
            (self.tick_size, "price_increment"),
            (self.step_size, "quantity_increment"),
            (self.minimum_quantity, "base_quantity"),
            (self.minimum_notional, "quote_quantity"),
        )
        if any(value.kind != kind for value, kind in expected):
            raise ValueError("venue-rule values use an invalid exact kind")
        if (
            self.tick_size.decimal <= 0
            or self.step_size.decimal <= 0
            or self.minimum_quantity.decimal <= 0
        ):
            raise ValueError("venue tick, step, and minimum quantity must be positive")

    @property
    def evidence_id(self) -> str:
        return content_identity("venue-rule-evidence/v1", self)


@dataclass(frozen=True, slots=True)
class GridPlanEpoch:
    schema_version: str
    configuration: StrategyConfiguration
    observation: AdaptationObservation
    decision: AdaptationDecision
    predecessor_epoch_id: str | None
    derivation_causation_id: str
    venue_rules: VenueRuleEvidence
    plan: DerivedGridPlan
    presentation: Mapping[str, Any] = field(default_factory=dict, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "presentation",
            MappingProxyType(dict(self.presentation)),
        )
        if self.schema_version != "grid-plan-epoch/v1":
            raise ValueError("unsupported grid-plan-epoch schema version")
        if not self.derivation_causation_id:
            raise ValueError("grid plan epoch derivation causation is required")
        if self.decision.policy_id != self.configuration.adaptation_policy.policy_id:
            raise ValueError("decision policy does not match strategy configuration")
        if self.decision.observation_id != self.observation.observation_id:
            raise ValueError("decision evidence does not match epoch observation")
        if len(self.plan.rungs) != self.configuration.rung_count:
            raise ValueError("grid plan rung count does not match configuration")
        if self.plan.fixed_quote_principal != self.configuration.fixed_quote_principal:
            raise ValueError("grid plan principal does not match configuration")
        if self.plan.reference_price != self.observation.reference_price:
            raise ValueError("grid plan reference price does not match observation")
        if (
            self.plan.lower.decimal < self.configuration.lower_bound_limit.decimal
            or self.plan.upper.decimal > self.configuration.upper_bound_limit.decimal
        ):
            raise ValueError("grid plan bounds exceed configuration limits")
        allocation = self.plan.allocation_assumptions
        if (
            allocation.quote_allocation.decimal + allocation.fee_reserve.decimal
            > self.configuration.maximum_quote_capital.decimal
        ):
            raise ValueError("grid plan allocation exceeds the capital envelope")
        if any(
            obligation.fixed_quote_principal != self.configuration.fixed_quote_principal
            for obligation in self.plan.obligations
        ):
            raise ValueError("grid obligations do not match fixed quote principal")
        if any(
            obligation.fixed_quote_principal.decimal < self.venue_rules.minimum_notional.decimal
            for obligation in self.plan.obligations
        ):
            raise ValueError("grid obligations are below venue minimum notional")
        if any(
            rung.price.decimal % self.venue_rules.tick_size.decimal != 0 for rung in self.plan.rungs
        ):
            raise ValueError("grid plan prices are not venue-quantized")
        if self.configuration.spacing is Spacing.GEOMETRIC:
            ratios = tuple(
                right.decimal / left.decimal
                for left, right in zip(
                    self.plan.unquantized_rungs,
                    self.plan.unquantized_rungs[1:],
                )
            )
            if ratios and any(abs(ratio - ratios[0]) > Decimal("1e-30") for ratio in ratios[1:]):
                raise ValueError("grid plan does not use geometric spacing")
        else:
            differences = tuple(
                right.decimal - left.decimal
                for left, right in zip(
                    self.plan.unquantized_rungs,
                    self.plan.unquantized_rungs[1:],
                )
            )
            if differences and any(difference != differences[0] for difference in differences[1:]):
                raise ValueError("grid plan does not use arithmetic spacing")
        roles = {rung.role for rung in self.plan.rungs}
        if self.decision.state is AdaptationState.TREND_DOWN and "BUY" in roles:
            raise ValueError("TREND_DOWN grid plans cannot contain buy obligations")
        if self.decision.state is AdaptationState.UNCERTAIN and roles != {"INACTIVE"}:
            raise ValueError("UNCERTAIN grid plans must freeze every rung")

    @property
    def epoch_id(self) -> str:
        material = {
            "schema_version": self.schema_version,
            "configuration": self.configuration,
            "observation": self.observation,
            "decision": self.decision,
            "predecessor_epoch_id": self.predecessor_epoch_id,
            "derivation_causation_id": self.derivation_causation_id,
            "venue_rules": self.venue_rules,
            "plan": self.plan,
        }
        return content_identity("grid-plan-epoch/v1", material)

    @classmethod
    def derive(
        cls,
        *,
        configuration: StrategyConfiguration,
        observation: AdaptationObservation,
        decision: AdaptationDecision,
        predecessor_epoch_id: str | None,
        derivation_causation_id: str,
        venue_rules: VenueRuleEvidence,
        plan: DerivedGridPlan,
        presentation: Mapping[str, Any] | None = None,
    ) -> GridPlanEpoch:
        return cls(
            schema_version="grid-plan-epoch/v1",
            configuration=configuration,
            observation=observation,
            decision=decision,
            predecessor_epoch_id=predecessor_epoch_id,
            derivation_causation_id=derivation_causation_id,
            venue_rules=venue_rules,
            plan=plan,
            presentation=dict(presentation or {}),
        )
