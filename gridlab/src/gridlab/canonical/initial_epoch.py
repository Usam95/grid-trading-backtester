from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR, localcontext
from enum import Enum

from gridlab.canonical._identity import content_identity
from gridlab.canonical.adaptation import (
    AdaptationObservation,
    AdaptationState,
    decide_adaptation,
)
from gridlab.canonical.configuration import Spacing, StrategyConfiguration
from gridlab.canonical.events import DomainTime
from gridlab.canonical.plan import (
    AllocationAssumptions,
    BootstrapObligation,
    DerivedGridPlan,
    GridObligation,
    GridPlanEpoch,
    QuantizedRung,
    VenueRuleEvidence,
)
from gridlab.canonical.values import ExactDecimal


class ActivationLifecycle(str, Enum):
    REJECTED = "REJECTED"
    BOOTSTRAPPING = "BOOTSTRAPPING"
    ACTIVE = "ACTIVE"


class ActivationGateOutcome(str, Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True, slots=True)
class ActivationGate:
    name: str
    outcome: ActivationGateOutcome
    reason: str

    def __post_init__(self) -> None:
        if not self.name or not self.reason:
            raise ValueError("activation gate name and reason are required")


@dataclass(frozen=True, slots=True)
class BootstrapEvidence:
    schema_version: str
    complete: bool
    net_base_confirmed: ExactDecimal
    evidence_id: str | None

    def __post_init__(self) -> None:
        if self.schema_version != "bootstrap-evidence/v1":
            raise ValueError("unsupported bootstrap evidence schema")
        if self.net_base_confirmed.kind != "base_quantity" or self.net_base_confirmed.decimal < 0:
            raise ValueError("confirmed bootstrap inventory must be non-negative base quantity")
        if self.complete and not self.evidence_id:
            raise ValueError("complete bootstrap evidence requires an identity")

    @classmethod
    def incomplete(cls) -> BootstrapEvidence:
        return cls(
            schema_version="bootstrap-evidence/v1",
            complete=False,
            net_base_confirmed=ExactDecimal.parse("0", kind="base_quantity"),
            evidence_id=None,
        )


@dataclass(frozen=True, slots=True)
class InitialEpochActivation:
    schema_version: str
    lifecycle: ActivationLifecycle
    decision_state: AdaptationState
    gates: tuple[ActivationGate, ...]
    derived_width: ExactDecimal | None
    epoch: GridPlanEpoch | None
    bootstrap_obligation: BootstrapObligation | None
    maximum_planned_inventory: ExactDecimal | None
    bootstrap_evidence: BootstrapEvidence
    ladder_placement_allowed: bool
    activation_pending: bool = False
    automatically_armed: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "gates", tuple(self.gates))
        if self.schema_version != "initial-epoch-activation/v1":
            raise ValueError("unsupported initial epoch activation schema")
        if not self.gates:
            raise ValueError("initial epoch activation gates are required")
        if self.activation_pending or self.automatically_armed:
            raise ValueError("initial activation cannot remain pending or automatically armed")
        if self.lifecycle is ActivationLifecycle.REJECTED:
            if self.epoch is not None or self.ladder_placement_allowed:
                raise ValueError("rejected activation cannot retain an epoch or ladder authority")
        elif self.epoch is None or self.bootstrap_obligation is None:
            raise ValueError("non-rejected activation requires an obligation-backed epoch")
        if self.lifecycle is ActivationLifecycle.ACTIVE and not self.ladder_placement_allowed:
            raise ValueError("active initial epoch must permit ladder placement")
        if self.lifecycle is ActivationLifecycle.BOOTSTRAPPING and self.ladder_placement_allowed:
            raise ValueError("bootstrapping cannot permit ladder placement")

    @property
    def replay_fingerprint(self) -> str:
        return content_identity("initial-epoch-activation/v1", self)


def _exact(value: Decimal, kind: str) -> ExactDecimal:
    return ExactDecimal.parse(format(value, "f"), kind=kind)


def _round_to_increment(
    value: Decimal,
    increment: Decimal,
    *,
    rounding: str,
) -> Decimal:
    units = (value / increment).to_integral_value(rounding=rounding)
    return units * increment


def _rejected(
    *,
    decision_state: AdaptationState,
    reason: str,
    bootstrap_evidence: BootstrapEvidence,
    gates: tuple[ActivationGate, ...] = (),
) -> InitialEpochActivation:
    return InitialEpochActivation(
        schema_version="initial-epoch-activation/v1",
        lifecycle=ActivationLifecycle.REJECTED,
        decision_state=decision_state,
        gates=gates
        + (
            ActivationGate(
                "activation_eligibility",
                ActivationGateOutcome.FAILED,
                reason,
            ),
        ),
        derived_width=None,
        epoch=None,
        bootstrap_obligation=None,
        maximum_planned_inventory=None,
        bootstrap_evidence=bootstrap_evidence,
        ladder_placement_allowed=False,
    )


def _derive_bounds(
    configuration: StrategyConfiguration,
    state: AdaptationState,
    reference_price: Decimal,
) -> tuple[Decimal, Decimal, Decimal]:
    policy = configuration.adaptation_policy
    width = (
        policy.high_volatility_width.decimal
        if state is AdaptationState.RANGE_HIGH_VOLATILITY
        else policy.normal_width.decimal
    )
    width = min(width, policy.maximum_width.decimal)
    center = reference_price
    if state is AdaptationState.TREND_UP:
        center *= Decimal("1") + policy.maximum_upward_shift.decimal
    lower = max(
        center * (Decimal("1") - width),
        configuration.lower_bound_limit.decimal,
    )
    upper = min(
        center * (Decimal("1") + width),
        configuration.upper_bound_limit.decimal,
    )
    if lower >= upper:
        raise ValueError("immutable policy limits collapse the derived bounds")
    return lower, upper, width


def _derive_geometry(
    lower: Decimal,
    upper: Decimal,
    rung_count: int,
    spacing: Spacing,
) -> tuple[Decimal, ...]:
    if spacing is Spacing.ARITHMETIC:
        step = (upper - lower) / Decimal(rung_count - 1)
        return tuple(
            lower if index == 0 else upper if index == rung_count - 1 else lower + step * index
            for index in range(rung_count)
        )
    with localcontext() as context:
        context.prec = 50
        ratio = (upper / lower) ** (Decimal(1) / Decimal(rung_count - 1))
        return tuple(
            lower if index == 0 else upper if index == rung_count - 1 else lower * ratio**index
            for index in range(rung_count)
        )


def derive_initial_epoch(
    *,
    configuration: StrategyConfiguration,
    observation: AdaptationObservation,
    decision_time: DomainTime,
    activation_price: ExactDecimal,
    derivation_causation_id: str,
    venue_rules: VenueRuleEvidence,
    bootstrap_evidence: BootstrapEvidence,
) -> InitialEpochActivation:
    if activation_price.kind != "price" or activation_price.decimal <= 0:
        raise ValueError("activation price must be a positive exact price")
    decision = decide_adaptation(
        configuration.adaptation_policy,
        observation,
        decision_time,
    )
    evidence_gate = ActivationGate(
        "quality_approved_past_only_evidence",
        (
            ActivationGateOutcome.PASSED
            if decision.state is not AdaptationState.UNCERTAIN
            else ActivationGateOutcome.FAILED
        ),
        decision.reason,
    )
    if decision.state is AdaptationState.UNCERTAIN:
        return _rejected(
            decision_state=decision.state,
            reason=decision.reason,
            bootstrap_evidence=bootstrap_evidence,
            gates=(evidence_gate,),
        )

    lower, upper, width = _derive_bounds(
        configuration,
        decision.state,
        observation.reference_price.decimal,
    )
    bounds_gate = ActivationGate(
        "activation_price_strictly_inside_bounds",
        (
            ActivationGateOutcome.PASSED
            if lower < activation_price.decimal < upper
            else ActivationGateOutcome.FAILED
        ),
        (
            "activation_price_inside_derived_bounds"
            if lower < activation_price.decimal < upper
            else "activation_price_at_or_outside_derived_bounds"
        ),
    )
    if bounds_gate.outcome is ActivationGateOutcome.FAILED:
        return _rejected(
            decision_state=decision.state,
            reason=bounds_gate.reason,
            bootstrap_evidence=bootstrap_evidence,
            gates=(evidence_gate, bounds_gate),
        )

    unquantized = _derive_geometry(
        lower,
        upper,
        configuration.rung_count,
        configuration.spacing,
    )
    quantized_rungs: list[QuantizedRung] = []
    obligations: list[GridObligation] = []
    for index, price in enumerate(unquantized):
        if decision.state is AdaptationState.TREND_DOWN:
            provisional_role = "SELL" if price > activation_price.decimal else "INACTIVE"
        else:
            provisional_role = (
                "BUY"
                if price < activation_price.decimal
                else "SELL"
                if price > activation_price.decimal
                else "INACTIVE"
            )
        rounding = ROUND_FLOOR if provisional_role != "SELL" else ROUND_CEILING
        quantized_price = _round_to_increment(
            price,
            venue_rules.tick_size.decimal,
            rounding=rounding,
        )
        role = (
            "INACTIVE"
            if quantized_price == activation_price.decimal
            else "BUY"
            if provisional_role == "BUY"
            else "SELL"
            if provisional_role == "SELL"
            else "INACTIVE"
        )
        rung = QuantizedRung(index, _exact(quantized_price, "price"), role)
        quantized_rungs.append(rung)
        if role != "INACTIVE":
            base_quantity = _round_to_increment(
                configuration.fixed_quote_principal.decimal / quantized_price,
                venue_rules.step_size.decimal,
                rounding=ROUND_FLOOR,
            )
            if base_quantity < venue_rules.minimum_quantity.decimal:
                return _rejected(
                    decision_state=decision.state,
                    reason="quantized_obligation_below_minimum_quantity",
                    bootstrap_evidence=bootstrap_evidence,
                    gates=(evidence_gate, bounds_gate),
                )
            if quantized_price * base_quantity < venue_rules.minimum_notional.decimal:
                return _rejected(
                    decision_state=decision.state,
                    reason="quantized_obligation_below_minimum_notional",
                    bootstrap_evidence=bootstrap_evidence,
                    gates=(evidence_gate, bounds_gate),
                )
            obligations.append(
                GridObligation(
                    rung_index=index,
                    role=role,
                    fixed_quote_principal=configuration.fixed_quote_principal,
                    base_quantity=_exact(base_quantity, "base_quantity"),
                )
            )
    prices = tuple(rung.price.decimal for rung in quantized_rungs)
    if prices != tuple(sorted(set(prices))):
        return _rejected(
            decision_state=decision.state,
            reason="venue_quantization_collapsed_rungs",
            bootstrap_evidence=bootstrap_evidence,
            gates=(evidence_gate, bounds_gate),
        )

    net_bootstrap = sum(
        (
            obligation.base_quantity.decimal
            for obligation in obligations
            if obligation.role == "SELL" and obligation.base_quantity is not None
        ),
        Decimal("0"),
    )
    fee_denominator = Decimal("1") - configuration.taker_fee.decimal
    if fee_denominator <= 0:
        raise ValueError("taker fee must remain below one for bootstrap coverage")
    gross_bootstrap = _round_to_increment(
        net_bootstrap / fee_denominator,
        venue_rules.step_size.decimal,
        rounding=ROUND_CEILING,
    )
    bootstrap_obligation = BootstrapObligation(
        schema_version="bootstrap-obligation/v1",
        net_base_required=_exact(net_bootstrap, "base_quantity"),
        gross_base_required=_exact(gross_bootstrap, "base_quantity"),
        fee_base_coverage=_exact(gross_bootstrap - net_bootstrap, "base_quantity"),
    )
    buy_inventory = sum(
        (
            obligation.base_quantity.decimal
            for obligation in obligations
            if obligation.role == "BUY" and obligation.base_quantity is not None
        ),
        Decimal("0"),
    )
    maximum_inventory = _exact(net_bootstrap + buy_inventory, "base_quantity")
    buy_principal = sum(
        (
            obligation.fixed_quote_principal.decimal
            for obligation in obligations
            if obligation.role == "BUY"
        ),
        Decimal("0"),
    )
    planned_quote = buy_principal + gross_bootstrap * activation_price.decimal
    capital_gate = ActivationGate(
        "capital_and_fee_coverage",
        (
            ActivationGateOutcome.PASSED
            if planned_quote + configuration.fee_reserve.decimal
            <= configuration.maximum_quote_capital.decimal
            else ActivationGateOutcome.FAILED
        ),
        (
            "planned_obligations_fit_capital_envelope"
            if planned_quote + configuration.fee_reserve.decimal
            <= configuration.maximum_quote_capital.decimal
            else "planned_obligations_exceed_capital_envelope"
        ),
    )
    if capital_gate.outcome is ActivationGateOutcome.FAILED:
        return _rejected(
            decision_state=decision.state,
            reason=capital_gate.reason,
            bootstrap_evidence=bootstrap_evidence,
            gates=(evidence_gate, bounds_gate, capital_gate),
        )
    plan = DerivedGridPlan(
        schema_version="grid-plan/v1",
        lower=_exact(lower, "price"),
        upper=_exact(upper, "price"),
        reference_price=observation.reference_price,
        unquantized_rungs=tuple(_exact(value, "price") for value in unquantized),
        rungs=tuple(quantized_rungs),
        fixed_quote_principal=configuration.fixed_quote_principal,
        obligations=tuple(obligations),
        allocation_assumptions=AllocationAssumptions(
            quote_allocation=_exact(planned_quote, "quote_quantity"),
            base_allocation=_exact(Decimal("0"), "base_quantity"),
            fee_reserve=configuration.fee_reserve,
        ),
        derivation_semantics=(
            f"adaptive-initial-obligation-backed-{configuration.spacing.value.lower()}/v1"
        ),
        activation_price=activation_price,
        bootstrap_obligation=bootstrap_obligation,
        maximum_planned_inventory=maximum_inventory,
    )
    epoch = GridPlanEpoch.derive(
        configuration=configuration,
        observation=observation,
        decision=decision,
        predecessor_epoch_id=None,
        derivation_causation_id=derivation_causation_id,
        venue_rules=venue_rules,
        plan=plan,
    )
    bootstrap_complete = (
        bootstrap_evidence.complete
        and bootstrap_evidence.net_base_confirmed.decimal
        >= bootstrap_obligation.net_base_required.decimal
    )
    bootstrap_gate = ActivationGate(
        "bootstrap_inventory_complete",
        (ActivationGateOutcome.PASSED if bootstrap_complete else ActivationGateOutcome.BLOCKED),
        (
            "required_backing_inventory_confirmed"
            if bootstrap_complete
            else "required_backing_inventory_not_confirmed"
        ),
    )
    return InitialEpochActivation(
        schema_version="initial-epoch-activation/v1",
        lifecycle=(
            ActivationLifecycle.ACTIVE if bootstrap_complete else ActivationLifecycle.BOOTSTRAPPING
        ),
        decision_state=decision.state,
        gates=(evidence_gate, bounds_gate, capital_gate, bootstrap_gate),
        derived_width=_exact(width, "ratio"),
        epoch=epoch,
        bootstrap_obligation=bootstrap_obligation,
        maximum_planned_inventory=maximum_inventory,
        bootstrap_evidence=bootstrap_evidence,
        ladder_placement_allowed=bootstrap_complete,
    )
