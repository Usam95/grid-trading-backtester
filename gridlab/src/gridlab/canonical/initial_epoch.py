from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
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


VENUE_RULE_MAX_AGE_SECONDS = 15 * 60
RESEARCH_PRINCIPAL_POINTS = tuple(Decimal(value) for value in range(10, 21))


@dataclass(frozen=True, slots=True)
class PlanAdmissionContext:
    schema_version: str
    still_effective_quote_commitment: ExactDecimal
    still_effective_inventory_commitment: ExactDecimal
    still_effective_order_count: int

    def __post_init__(self) -> None:
        if self.schema_version != "plan-admission-context/v1":
            raise ValueError("unsupported plan admission context schema")
        if (
            self.still_effective_quote_commitment.kind != "quote_quantity"
            or self.still_effective_quote_commitment.decimal < 0
        ):
            raise ValueError("still-effective quote commitment must be non-negative")
        if (
            self.still_effective_inventory_commitment.kind != "base_quantity"
            or self.still_effective_inventory_commitment.decimal < 0
        ):
            raise ValueError("still-effective inventory commitment must be non-negative")
        if self.still_effective_order_count < 0:
            raise ValueError("still-effective order count must be non-negative")

    @classmethod
    def initial(cls) -> PlanAdmissionContext:
        return cls(
            schema_version="plan-admission-context/v1",
            still_effective_quote_commitment=ExactDecimal.parse("0", kind="quote_quantity"),
            still_effective_inventory_commitment=ExactDecimal.parse("0", kind="base_quantity"),
            still_effective_order_count=0,
        )


@dataclass(frozen=True, slots=True)
class PlanAdmissionAssessment:
    schema_version: str
    capital_envelope: ExactDecimal
    still_effective_quote_commitment: ExactDecimal
    proposed_quote_commitment: ExactDecimal
    bootstrap_quote_commitment: ExactDecimal
    total_quote_commitment: ExactDecimal
    fee_reserve: ExactDecimal
    still_effective_inventory_commitment: ExactDecimal
    additional_bootstrap_inventory: ExactDecimal
    maximum_planned_inventory: ExactDecimal
    total_worst_case_inventory: ExactDecimal
    still_effective_order_count: int
    proposed_order_count: int
    total_order_count: int
    venue_order_capacity: int | None
    foreign_open_orders: int

    def __post_init__(self) -> None:
        if self.schema_version != "plan-admission-assessment/v1":
            raise ValueError("unsupported plan admission assessment schema")
        quote_values = (
            self.capital_envelope,
            self.still_effective_quote_commitment,
            self.proposed_quote_commitment,
            self.bootstrap_quote_commitment,
            self.total_quote_commitment,
            self.fee_reserve,
        )
        if any(value.kind != "quote_quantity" or value.decimal < 0 for value in quote_values):
            raise ValueError("plan admission quote values must be non-negative quote quantities")
        inventory_values = (
            self.still_effective_inventory_commitment,
            self.additional_bootstrap_inventory,
            self.maximum_planned_inventory,
            self.total_worst_case_inventory,
        )
        if any(value.kind != "base_quantity" or value.decimal < 0 for value in inventory_values):
            raise ValueError("plan admission inventory values must be non-negative base quantities")
        counts = (
            self.still_effective_order_count,
            self.proposed_order_count,
            self.total_order_count,
            self.foreign_open_orders,
        )
        if any(count < 0 for count in counts):
            raise ValueError("plan admission order counts must be non-negative")
        if self.venue_order_capacity is not None and self.venue_order_capacity <= 0:
            raise ValueError("venue order capacity must be positive when provided")


@dataclass(frozen=True, slots=True)
class AdjacentCycleEconomics:
    schema_version: str
    buy_rung_index: int
    sell_rung_index: int
    buy_price: ExactDecimal
    sell_price: ExactDecimal
    cycle_quantity: ExactDecimal
    net_margin: ExactDecimal
    positive: bool
    reason: str

    def __post_init__(self) -> None:
        if self.schema_version != "adjacent-cycle-economics/v1":
            raise ValueError("unsupported adjacent-cycle economics schema")
        if (
            self.buy_rung_index < 0
            or self.sell_rung_index < 0
            or self.buy_rung_index >= self.sell_rung_index
        ):
            raise ValueError("adjacent-cycle rung indices are invalid")
        if (
            self.buy_price.kind != "price"
            or self.sell_price.kind != "price"
            or self.buy_price.decimal <= 0
            or self.sell_price.decimal <= 0
        ):
            raise ValueError("adjacent-cycle prices must be positive exact prices")
        if self.cycle_quantity.kind != "base_quantity" or self.cycle_quantity.decimal <= 0:
            raise ValueError("adjacent-cycle quantity must be a positive base quantity")
        if self.net_margin.kind != "quote_quantity":
            raise ValueError("adjacent-cycle net margin must use quote quantity")
        if not self.reason:
            raise ValueError("adjacent-cycle economics reason is required")


@dataclass(frozen=True, slots=True)
class PrincipalFeasibilityPoint:
    principal: ExactDecimal
    feasible: bool
    reasons: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "reasons", tuple(self.reasons))
        if self.principal.kind != "quote_quantity" or self.principal.decimal <= 0:
            raise ValueError("feasibility principal must be a positive quote quantity")
        if self.feasible and self.reasons:
            raise ValueError("feasible principal points cannot carry rejection reasons")
        if not self.feasible and not self.reasons:
            raise ValueError("infeasible principal points must explain their rejection")


@dataclass(frozen=True, slots=True)
class PrincipalFeasibilityReport:
    schema_version: str
    points: tuple[PrincipalFeasibilityPoint, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "points", tuple(self.points))
        if self.schema_version != "principal-feasibility-report/v1":
            raise ValueError("unsupported principal feasibility report schema")
        if not self.points:
            raise ValueError("principal feasibility points are required")


@dataclass(frozen=True, slots=True)
class PostOnlyRetryPolicy:
    schema_version: str
    order_type: str
    max_attempts: int
    retry_delays: tuple[ExactDecimal, ...]
    max_price_displacement_ratio: ExactDecimal
    max_adjacent_gap_fraction: ExactDecimal
    exhaustion_posture: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "retry_delays", tuple(self.retry_delays))
        if self.schema_version != "post-only-retry-policy/v1":
            raise ValueError("unsupported post-only retry policy schema")
        if self.order_type != "LIMIT_MAKER":
            raise ValueError("ordinary order type must remain LIMIT_MAKER")
        if self.max_attempts != 3 or self.exhaustion_posture != "REDUCE_ONLY":
            raise ValueError("post-only retry policy must preserve the accepted bounds")
        if len(self.retry_delays) != 2 or tuple(delay.decimal for delay in self.retry_delays) != (
            Decimal("0.25"),
            Decimal("1"),
        ):
            raise ValueError("post-only retry delays must remain 250 ms then one second")
        if any(
            delay.kind != "duration_seconds" or delay.decimal <= 0 for delay in self.retry_delays
        ):
            raise ValueError("post-only retry delays must be positive exact durations")
        if (
            self.max_price_displacement_ratio.kind != "ratio"
            or self.max_adjacent_gap_fraction.kind != "ratio"
            or self.max_price_displacement_ratio.decimal != Decimal("0.0025")
            or self.max_adjacent_gap_fraction.decimal != Decimal("0.25")
        ):
            raise ValueError("post-only retry displacement limits must match the accepted policy")

    @classmethod
    def accepted(cls) -> PostOnlyRetryPolicy:
        return cls(
            schema_version="post-only-retry-policy/v1",
            order_type="LIMIT_MAKER",
            max_attempts=3,
            retry_delays=(
                ExactDecimal.parse("0.25", kind="duration_seconds"),
                ExactDecimal.parse("1", kind="duration_seconds"),
            ),
            max_price_displacement_ratio=ExactDecimal.parse("0.0025", kind="ratio"),
            max_adjacent_gap_fraction=ExactDecimal.parse("0.25", kind="ratio"),
            exhaustion_posture="REDUCE_ONLY",
        )


@dataclass(frozen=True, slots=True)
class RuleFeeContract:
    schema_version: str
    venue_rule_evidence_id: str
    maker_fee: ExactDecimal
    taker_fee: ExactDecimal

    def __post_init__(self) -> None:
        if self.schema_version != "rule-fee-contract/v1":
            raise ValueError("unsupported rule/fee contract schema")
        if not self.venue_rule_evidence_id.startswith("sha256:"):
            raise ValueError("rule/fee contract requires a venue-rule evidence identity")
        if (
            self.maker_fee.kind != "fee_rate"
            or self.taker_fee.kind != "fee_rate"
            or self.maker_fee.decimal < 0
            or self.taker_fee.decimal < 0
        ):
            raise ValueError("rule/fee contract requires non-negative fee rates")

    @property
    def contract_id(self) -> str:
        return content_identity("rule-fee-contract/v1", self)


@dataclass(frozen=True, slots=True)
class InitialEpochActivation:
    schema_version: str
    lifecycle: ActivationLifecycle
    decision_state: AdaptationState
    gates: tuple[ActivationGate, ...]
    admission_context: PlanAdmissionContext
    admission_assessment: PlanAdmissionAssessment | None
    adjacent_cycle_economics: tuple[AdjacentCycleEconomics, ...]
    principal_feasibility: PrincipalFeasibilityReport
    post_only_retry_policy: PostOnlyRetryPolicy
    rule_fee_contract: RuleFeeContract
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
        object.__setattr__(self, "adjacent_cycle_economics", tuple(self.adjacent_cycle_economics))
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


@dataclass(frozen=True, slots=True)
class _PrincipalEvaluation:
    obligations: tuple[GridObligation, ...]
    buy_principal: Decimal
    bootstrap_inventory: Decimal
    bootstrap_quote_commitment: Decimal
    maximum_inventory: Decimal
    cycle_economics: tuple[AdjacentCycleEconomics, ...]
    reasons: tuple[str, ...]


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
    admission_context: PlanAdmissionContext,
    principal_feasibility: PrincipalFeasibilityReport,
    post_only_retry_policy: PostOnlyRetryPolicy,
    rule_fee_contract: RuleFeeContract,
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
        admission_context=admission_context,
        admission_assessment=None,
        adjacent_cycle_economics=(),
        principal_feasibility=principal_feasibility,
        post_only_retry_policy=post_only_retry_policy,
        rule_fee_contract=rule_fee_contract,
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


def _venue_rules_gate(
    venue_rules: VenueRuleEvidence,
    *,
    decision_time: DomainTime,
) -> ActivationGate:
    age = decision_time.value - venue_rules.observed_at.value
    if age < timedelta(0):
        reason = "venue_rules_observed_in_the_future"
        outcome = ActivationGateOutcome.FAILED
    elif age > timedelta(seconds=VENUE_RULE_MAX_AGE_SECONDS):
        reason = "venue_rules_are_stale"
        outcome = ActivationGateOutcome.FAILED
    elif venue_rules.contradictory:
        reason = "venue_rules_are_contradictory"
        outcome = ActivationGateOutcome.FAILED
    elif venue_rules.symbol_status != "TRADING":
        reason = f"venue_rules_symbol_{venue_rules.symbol_status.lower()}"
        outcome = ActivationGateOutcome.FAILED
    elif not venue_rules.spot_trading_allowed:
        reason = "venue_rules_spot_trading_unsupported"
        outcome = ActivationGateOutcome.FAILED
    elif not venue_rules.limit_maker_supported:
        reason = "venue_rules_post_only_unsupported"
        outcome = ActivationGateOutcome.FAILED
    else:
        reason = "venue_rules_are_current_and_supported"
        outcome = ActivationGateOutcome.PASSED
    return ActivationGate("venue_rule_contract", outcome, reason)


def _evaluate_principal(
    *,
    principal: Decimal,
    quantized_rungs: tuple[QuantizedRung, ...],
    configuration: StrategyConfiguration,
    venue_rules: VenueRuleEvidence,
    admission_context: PlanAdmissionContext,
    activation_price: Decimal,
) -> _PrincipalEvaluation:
    reasons: list[str] = []
    obligations: list[GridObligation] = []
    buy_principal = Decimal("0")
    bootstrap_inventory = Decimal("0")
    cycle_economics: list[AdjacentCycleEconomics] = []
    quantities_by_rung: dict[int, Decimal] = {}

    for rung in quantized_rungs:
        if rung.role == "INACTIVE":
            continue
        if rung.price.decimal < venue_rules.minimum_price.decimal:
            reasons.append("quantized_price_below_minimum_price")
            continue
        if (
            venue_rules.maximum_price is not None
            and rung.price.decimal > venue_rules.maximum_price.decimal
        ):
            reasons.append("quantized_price_above_maximum_price")
            continue
        base_quantity = _round_to_increment(
            principal / rung.price.decimal,
            venue_rules.step_size.decimal,
            rounding=ROUND_FLOOR,
        )
        if base_quantity <= 0:
            reasons.append("quantized_obligation_zero_quantity")
            continue
        if base_quantity < venue_rules.minimum_quantity.decimal:
            reasons.append("quantized_obligation_below_minimum_quantity")
            continue
        if (
            venue_rules.maximum_quantity is not None
            and base_quantity > venue_rules.maximum_quantity.decimal
        ):
            reasons.append("quantized_obligation_above_maximum_quantity")
            continue
        notional = rung.price.decimal * base_quantity
        if notional < venue_rules.minimum_notional.decimal:
            reasons.append("quantized_obligation_below_minimum_notional")
            continue
        if (
            venue_rules.maximum_notional is not None
            and notional > venue_rules.maximum_notional.decimal
        ):
            reasons.append("quantized_obligation_above_maximum_notional")
            continue
        quantity = _exact(base_quantity, "base_quantity")
        obligations.append(
            GridObligation(
                rung_index=rung.index,
                role=rung.role,
                fixed_quote_principal=_exact(principal, "quote_quantity"),
                base_quantity=quantity,
            )
        )
        quantities_by_rung[rung.index] = base_quantity
        if rung.role == "BUY":
            buy_principal += principal
        else:
            bootstrap_inventory += base_quantity

    if reasons:
        return _PrincipalEvaluation(
            obligations=(),
            buy_principal=buy_principal,
            bootstrap_inventory=bootstrap_inventory,
            bootstrap_quote_commitment=Decimal("0"),
            maximum_inventory=Decimal("0"),
            cycle_economics=(),
            reasons=tuple(dict.fromkeys(reasons)),
        )

    fee_denominator = Decimal("1") - configuration.taker_fee.decimal
    if fee_denominator <= 0:
        raise ValueError("taker fee must remain below one for bootstrap coverage")
    gross_bootstrap = _round_to_increment(
        bootstrap_inventory / fee_denominator,
        venue_rules.step_size.decimal,
        rounding=ROUND_CEILING,
    )
    bootstrap_quote_commitment = gross_bootstrap * activation_price
    buy_inventory = sum(
        quantity
        for rung_index, quantity in quantities_by_rung.items()
        if next(rung.role for rung in quantized_rungs if rung.index == rung_index) == "BUY"
    )
    maximum_inventory = bootstrap_inventory + buy_inventory

    active_rungs = [rung for rung in quantized_rungs if rung.role != "INACTIVE"]
    for left, right in zip(active_rungs, active_rungs[1:]):
        if left.role != "BUY" or right.role != "SELL":
            continue
        acquired = _round_to_increment(
            quantities_by_rung[left.index] * (Decimal("1") - configuration.maker_fee.decimal),
            venue_rules.step_size.decimal,
            rounding=ROUND_FLOOR,
        )
        if acquired < venue_rules.minimum_quantity.decimal:
            reasons.append("adjacent_cycle_quantity_below_minimum_quantity")
            continue
        execution_allowance = venue_rules.tick_size.decimal * acquired * Decimal("2")
        safety_margin = venue_rules.tick_size.decimal * acquired
        buy_cost = (
            left.price.decimal
            * quantities_by_rung[left.index]
            * (Decimal("1") + configuration.maker_fee.decimal)
        )
        sell_proceeds = (
            right.price.decimal * acquired * (Decimal("1") - configuration.maker_fee.decimal)
        )
        net_margin = sell_proceeds - buy_cost - execution_allowance - safety_margin
        positive = net_margin > 0
        cycle_economics.append(
            AdjacentCycleEconomics(
                schema_version="adjacent-cycle-economics/v1",
                buy_rung_index=left.index,
                sell_rung_index=right.index,
                buy_price=left.price,
                sell_price=right.price,
                cycle_quantity=_exact(acquired, "base_quantity"),
                net_margin=_exact(net_margin, "quote_quantity"),
                positive=positive,
                reason=(
                    "adjacent_cycle_positive_after_fees_rounding_allowance_and_margin"
                    if positive
                    else "adjacent_cycle_not_positive_after_fees_rounding_allowance_and_margin"
                ),
            )
        )

    return _PrincipalEvaluation(
        obligations=tuple(obligations),
        buy_principal=buy_principal,
        bootstrap_inventory=bootstrap_inventory,
        bootstrap_quote_commitment=bootstrap_quote_commitment,
        maximum_inventory=maximum_inventory,
        cycle_economics=tuple(cycle_economics),
        reasons=tuple(dict.fromkeys(reasons)),
    )


def _admission_failures(
    *,
    evaluation: _PrincipalEvaluation,
    configuration: StrategyConfiguration,
    venue_rules: VenueRuleEvidence,
    admission_context: PlanAdmissionContext,
) -> tuple[str, ...]:
    reasons: list[str] = []
    total_order_count = (
        admission_context.still_effective_order_count
        + venue_rules.foreign_open_orders
        + len(evaluation.obligations)
    )
    if venue_rules.max_open_orders is not None and total_order_count > venue_rules.max_open_orders:
        reasons.append("planned_orders_exceed_venue_capacity")
    total_quote_commitment = (
        admission_context.still_effective_quote_commitment.decimal
        + evaluation.buy_principal
        + evaluation.bootstrap_quote_commitment
    )
    if (
        total_quote_commitment + configuration.fee_reserve.decimal
        > configuration.maximum_quote_capital.decimal
    ):
        reasons.append("planned_obligations_exceed_capital_envelope")
    total_worst_case_inventory = (
        admission_context.still_effective_inventory_commitment.decimal
        + evaluation.maximum_inventory
    )
    if total_worst_case_inventory > evaluation.maximum_inventory:
        reasons.append("planned_inventory_exceeds_maximum_inventory")
    if any(not item.positive for item in evaluation.cycle_economics):
        reasons.append("adjacent_cycle_not_positive_after_fees_rounding_allowance_and_margin")
    return tuple(dict.fromkeys(reasons))


def _principal_feasibility(
    *,
    quantized_rungs: tuple[QuantizedRung, ...],
    configuration: StrategyConfiguration,
    venue_rules: VenueRuleEvidence,
    admission_context: PlanAdmissionContext,
    activation_price: Decimal,
) -> PrincipalFeasibilityReport:
    points = []
    for principal in RESEARCH_PRINCIPAL_POINTS:
        evaluation = _evaluate_principal(
            principal=principal,
            quantized_rungs=quantized_rungs,
            configuration=configuration,
            venue_rules=venue_rules,
            admission_context=admission_context,
            activation_price=activation_price,
        )
        points.append(
            PrincipalFeasibilityPoint(
                principal=_exact(principal, "quote_quantity"),
                feasible=not (
                    evaluation.reasons
                    or _admission_failures(
                        evaluation=evaluation,
                        configuration=configuration,
                        venue_rules=venue_rules,
                        admission_context=admission_context,
                    )
                ),
                reasons=evaluation.reasons
                or _admission_failures(
                    evaluation=evaluation,
                    configuration=configuration,
                    venue_rules=venue_rules,
                    admission_context=admission_context,
                ),
            )
        )
    return PrincipalFeasibilityReport(
        schema_version="principal-feasibility-report/v1",
        points=tuple(points),
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
    admission_context: PlanAdmissionContext | None = None,
) -> InitialEpochActivation:
    if activation_price.kind != "price" or activation_price.decimal <= 0:
        raise ValueError("activation price must be a positive exact price")
    context = admission_context or PlanAdmissionContext.initial()
    post_only_retry_policy = PostOnlyRetryPolicy.accepted()
    rule_fee_contract = RuleFeeContract(
        schema_version="rule-fee-contract/v1",
        venue_rule_evidence_id=venue_rules.evidence_id,
        maker_fee=configuration.maker_fee,
        taker_fee=configuration.taker_fee,
    )
    decision = decide_adaptation(
        configuration.adaptation_policy,
        observation,
        decision_time,
    )
    placeholder_quantized_rungs = (
        QuantizedRung(0, activation_price, "INACTIVE"),
        QuantizedRung(
            1, _exact(activation_price.decimal + venue_rules.tick_size.decimal, "price"), "SELL"
        ),
    )
    principal_feasibility = _principal_feasibility(
        quantized_rungs=placeholder_quantized_rungs,
        configuration=configuration,
        venue_rules=venue_rules,
        admission_context=context,
        activation_price=activation_price.decimal,
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
            admission_context=context,
            principal_feasibility=principal_feasibility,
            post_only_retry_policy=post_only_retry_policy,
            rule_fee_contract=rule_fee_contract,
            gates=(evidence_gate,),
        )
    venue_gate = _venue_rules_gate(venue_rules, decision_time=decision_time)
    if venue_gate.outcome is ActivationGateOutcome.FAILED:
        return _rejected(
            decision_state=decision.state,
            reason=venue_gate.reason,
            bootstrap_evidence=bootstrap_evidence,
            admission_context=context,
            principal_feasibility=principal_feasibility,
            post_only_retry_policy=post_only_retry_policy,
            rule_fee_contract=rule_fee_contract,
            gates=(evidence_gate, venue_gate),
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
            admission_context=context,
            principal_feasibility=principal_feasibility,
            post_only_retry_policy=post_only_retry_policy,
            rule_fee_contract=rule_fee_contract,
            gates=(evidence_gate, venue_gate, bounds_gate),
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
    prices = tuple(rung.price.decimal for rung in quantized_rungs)
    if prices != tuple(sorted(set(prices))):
        return _rejected(
            decision_state=decision.state,
            reason="venue_quantization_collapsed_rungs",
            bootstrap_evidence=bootstrap_evidence,
            admission_context=context,
            principal_feasibility=principal_feasibility,
            post_only_retry_policy=post_only_retry_policy,
            rule_fee_contract=rule_fee_contract,
            gates=(evidence_gate, venue_gate, bounds_gate),
        )
    quantized_rung_tuple = tuple(quantized_rungs)
    principal_feasibility = _principal_feasibility(
        quantized_rungs=quantized_rung_tuple,
        configuration=configuration,
        venue_rules=venue_rules,
        admission_context=context,
        activation_price=activation_price.decimal,
    )
    evaluation = _evaluate_principal(
        principal=configuration.fixed_quote_principal.decimal,
        quantized_rungs=quantized_rung_tuple,
        configuration=configuration,
        venue_rules=venue_rules,
        admission_context=context,
        activation_price=activation_price.decimal,
    )
    if evaluation.reasons:
        return _rejected(
            decision_state=decision.state,
            reason=evaluation.reasons[0],
            bootstrap_evidence=bootstrap_evidence,
            admission_context=context,
            principal_feasibility=principal_feasibility,
            post_only_retry_policy=post_only_retry_policy,
            rule_fee_contract=rule_fee_contract,
            gates=(evidence_gate, venue_gate, bounds_gate),
        )
    obligations = list(evaluation.obligations)

    net_bootstrap = sum(
        (
            obligation.base_quantity.decimal
            for obligation in obligations
            if obligation.role == "SELL" and obligation.base_quantity is not None
        ),
        Decimal("0"),
    )
    gross_bootstrap = _round_to_increment(
        net_bootstrap / (Decimal("1") - configuration.taker_fee.decimal),
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
    planned_quote = (
        context.still_effective_quote_commitment.decimal
        + buy_principal
        + (gross_bootstrap * activation_price.decimal)
    )
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
            admission_context=context,
            principal_feasibility=principal_feasibility,
            post_only_retry_policy=post_only_retry_policy,
            rule_fee_contract=rule_fee_contract,
            gates=(evidence_gate, venue_gate, bounds_gate, capital_gate),
        )
    capacity_gate = ActivationGate(
        "order_capacity",
        (
            ActivationGateOutcome.PASSED
            if venue_rules.max_open_orders is None
            or (
                context.still_effective_order_count
                + venue_rules.foreign_open_orders
                + len(obligations)
                <= venue_rules.max_open_orders
            )
            else ActivationGateOutcome.FAILED
        ),
        (
            "planned_orders_fit_venue_capacity"
            if venue_rules.max_open_orders is None
            or (
                context.still_effective_order_count
                + venue_rules.foreign_open_orders
                + len(obligations)
                <= venue_rules.max_open_orders
            )
            else "planned_orders_exceed_venue_capacity"
        ),
    )
    if capacity_gate.outcome is ActivationGateOutcome.FAILED:
        return _rejected(
            decision_state=decision.state,
            reason=capacity_gate.reason,
            bootstrap_evidence=bootstrap_evidence,
            admission_context=context,
            principal_feasibility=principal_feasibility,
            post_only_retry_policy=post_only_retry_policy,
            rule_fee_contract=rule_fee_contract,
            gates=(evidence_gate, venue_gate, bounds_gate, capital_gate, capacity_gate),
        )
    inventory_gate = ActivationGate(
        "maximum_planned_inventory",
        (
            ActivationGateOutcome.PASSED
            if context.still_effective_inventory_commitment.decimal + maximum_inventory.decimal
            <= maximum_inventory.decimal
            else ActivationGateOutcome.FAILED
        ),
        (
            "still_effective_inventory_fits_proposed_maximum"
            if context.still_effective_inventory_commitment.decimal + maximum_inventory.decimal
            <= maximum_inventory.decimal
            else "planned_inventory_exceeds_maximum_inventory"
        ),
    )
    if inventory_gate.outcome is ActivationGateOutcome.FAILED:
        return _rejected(
            decision_state=decision.state,
            reason=inventory_gate.reason,
            bootstrap_evidence=bootstrap_evidence,
            admission_context=context,
            principal_feasibility=principal_feasibility,
            post_only_retry_policy=post_only_retry_policy,
            rule_fee_contract=rule_fee_contract,
            gates=(
                evidence_gate,
                venue_gate,
                bounds_gate,
                capital_gate,
                capacity_gate,
                inventory_gate,
            ),
        )
    economics_gate = ActivationGate(
        "adjacent_cycle_economics",
        (
            ActivationGateOutcome.PASSED
            if all(item.positive for item in evaluation.cycle_economics)
            else ActivationGateOutcome.FAILED
        ),
        (
            "adjacent_cycles_are_strictly_positive"
            if all(item.positive for item in evaluation.cycle_economics)
            else "adjacent_cycle_not_positive_after_fees_rounding_allowance_and_margin"
        ),
    )
    if economics_gate.outcome is ActivationGateOutcome.FAILED:
        return _rejected(
            decision_state=decision.state,
            reason=economics_gate.reason,
            bootstrap_evidence=bootstrap_evidence,
            admission_context=context,
            principal_feasibility=principal_feasibility,
            post_only_retry_policy=post_only_retry_policy,
            rule_fee_contract=rule_fee_contract,
            gates=(
                evidence_gate,
                venue_gate,
                bounds_gate,
                capital_gate,
                capacity_gate,
                inventory_gate,
                economics_gate,
            ),
        )
    assessment = PlanAdmissionAssessment(
        schema_version="plan-admission-assessment/v1",
        capital_envelope=configuration.maximum_quote_capital,
        still_effective_quote_commitment=context.still_effective_quote_commitment,
        proposed_quote_commitment=_exact(
            buy_principal + gross_bootstrap * activation_price.decimal,
            "quote_quantity",
        ),
        bootstrap_quote_commitment=_exact(
            gross_bootstrap * activation_price.decimal,
            "quote_quantity",
        ),
        total_quote_commitment=_exact(planned_quote, "quote_quantity"),
        fee_reserve=configuration.fee_reserve,
        still_effective_inventory_commitment=context.still_effective_inventory_commitment,
        additional_bootstrap_inventory=_exact(gross_bootstrap, "base_quantity"),
        maximum_planned_inventory=maximum_inventory,
        total_worst_case_inventory=_exact(
            context.still_effective_inventory_commitment.decimal + maximum_inventory.decimal,
            "base_quantity",
        ),
        still_effective_order_count=context.still_effective_order_count,
        proposed_order_count=len(obligations),
        total_order_count=(
            context.still_effective_order_count + venue_rules.foreign_open_orders + len(obligations)
        ),
        venue_order_capacity=venue_rules.max_open_orders,
        foreign_open_orders=venue_rules.foreign_open_orders,
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
            quote_allocation=_exact(
                buy_principal + gross_bootstrap * activation_price.decimal,
                "quote_quantity",
            ),
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
        gates=(
            evidence_gate,
            venue_gate,
            bounds_gate,
            capital_gate,
            capacity_gate,
            inventory_gate,
            economics_gate,
            bootstrap_gate,
        ),
        admission_context=context,
        admission_assessment=assessment,
        adjacent_cycle_economics=evaluation.cycle_economics,
        principal_feasibility=principal_feasibility,
        post_only_retry_policy=post_only_retry_policy,
        rule_fee_contract=rule_fee_contract,
        derived_width=_exact(width, "ratio"),
        epoch=epoch,
        bootstrap_obligation=bootstrap_obligation,
        maximum_planned_inventory=maximum_inventory,
        bootstrap_evidence=bootstrap_evidence,
        ladder_placement_allowed=bootstrap_complete,
    )
