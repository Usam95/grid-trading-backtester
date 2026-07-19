# Canonical domain and grid semantics — decision record

Status: confirmed for first MVP on 2026-07-14  
Wayfinder ticket: [Define canonical domain and grid semantics](../.scratch/comprehensive-grid-trading-system/issues/02-define-canonical-domain-and-grid-semantics.md)

This record captures both selected semantics and declined alternatives. The domain glossary defines vocabulary; this document records behavior and trade-offs.

## Resolved decisions

### Market and exposure scope

**Selected:** Spot inventory trading. The grid may sell only grid inventory it owns. Borrowing, margin, short exposure, futures, and options remain outside the MVP.

**Declined:** Quote-only behavior as the only grid form, because it cannot trade both sides immediately. Leveraged or borrowed “neutral” exposure was declined because it introduces liquidation, funding, and repayment risk.

### Activation inventory

**Selected:** A neutral spot grid creates its initial grid inventory through an explicit, journaled bootstrap acquisition using a real market order.

**Declined:** A quote-only start as the MVP default, because it remains inactive on the sell side until a buy fills. Synthetic live conversion was declined because no executable order or real fee/slippage exists. Allocation of existing base holdings was deferred because ownership and cost basis require separate rules.

### Bootstrap acquisition size

**Selected:** Derive the acquisition quantity from the total base quantity required to back all initial sell rungs, including venue rounding and a fee reserve.

**Declined:** Arbitrary capital percentage and fixed 50% allocation can underfund sells or create unnecessary exposure. Backtest-optimized bootstrap percentage was declined because inventory must follow concrete sell obligations.

### Incomplete bootstrap acquisition

**Selected:** The grid remains in the bootstrapping state until all required backing inventory is confirmed. Retries are allowed only within separately approved price, slippage, and time limits. If inventory remains incomplete, no ladder is placed and operator intervention is required; acquired partial inventory remains grid-owned and journaled.

**Declined:** Placing a partially backed ladder or scaling its sell quantities silently changes the approved strategy. Automatic liquidation can compound fees and slippage and is not an appropriate hidden recovery action.

### Fee assets and backing inventory

**Selected:** Record the venue-reported fee asset and quantity for every fill. Backing inventory is based on net base received. If bootstrap fees deducted in base create a shortfall, acquire it only within the approved bootstrap price, slippage, and time limits.

**Declined:** Assuming quote-denominated fees or ignoring the fee asset breaks asset conservation and live reconciliation. Requiring a third-asset fee mode such as BNB makes strategy correctness depend on an optional account setting.

### Rung sizing

**Selected:** Fixed quote sizing. Each rung represents approximately equal quote value. A paired sell always uses the actual filled base quantity from its buy, after fee and venue effects.

**Declined:** Fixed base sizing creates unequal capital exposure across levels. Current-grid-equity sizing changes quantities during a run and complicates reproducibility. Multiple live sizing policies were deferred until independently validated.

### Cycle profit disposition

**Selected:** Rung quote value remains fixed for the approved run. After a completed cycle, replacement buys use the original fixed quote value and net profit accumulates as uncommitted quote inside grid equity.

**Declined:** Automatic compounding changes future exposure and makes the run path-dependent. Automated profit transfer adds treasury behavior outside grid semantics. Reusing the exact sold base quantity makes quote commitment drift. Compounding sizing is retained as a later increment requiring its own specification, backtest evidence, paper validation, and promotion approval.

### Spacing

**Selected:** Support arithmetic and geometric spacing; geometric is the explicit default.

**Declined:** Geometric-only support would unnecessarily exclude a simple research variant. Automatic selection was declined because it obscures the strategy specification and weakens reproducibility.

### Rung count and bounds

**Selected:** Rung count means the total number of configured price rungs including the exact lower and upper bounds. The activation price is not automatically inserted as a rung. Rung prices are derived deterministically from bounds, count, spacing, and venue rounding.

**Declined:** Interval count creates an off-by-one configuration meaning. Separate buy/sell counts make the ladder depend on activation position. Forcing activation price into the ladder mutates the approved geometry.

### Activation price on a rung

**Selected:** A configured rung exactly equal to the validated activation price is initially inactive. Initial buys are strictly below and sells strictly above; the activation rung may later receive a paired order through normal fills.

**Declined:** Placing either or both sides at the current price risks immediate taker execution, removes planned spacing, and creates ambiguous initial direction.

### Order liquidity intent

**Selected:** Ordinary rung buys and sells use post-only maker orders. Bootstrap acquisition and global stop-loss liquidation use aggressive orders because completion has priority over maker status.

**Selected post-only rejection policy:** A post-only rejection never falls back to a taker-capable order. The engine first reconciles by managed order identity, obtains a fresh best bid/offer and current venue filters, and then retries only with a venue-valid non-marketable limit price that is no worse than the configured rung economics: a buy may move down but never above its rung price; a sell may move up but never below its rung price. Attempts, elapsed time, and allowed displacement are strictly bounded and journaled. Exhausting any bound leaves the rung unplaced, enters an exposure-reducing safety pause, and alerts the operator. Every retry remains associated with the same rung and cumulative obligation.

**Declined:** Standard limits may cross and silently pay taker fees. Automatic order-type selection makes fee behavior path-dependent. Market orders for rungs destroy the approved ladder economics. Immediate taker fallback after post-only rejection breaks the validated fee model. Unlimited repricing can chase the market and detach execution from the approved rung.

### Rung occupancy

**Selected:** Each rung has at most one managed order with cumulative quantity and exactly one side at a time. Its side may change through the fill-driven pairing cycle.

**Declined:** Multiple or per-fill orders duplicate exposure and fragment reconciliation. Simultaneous buy and sell orders at one price have no grid spread and create self-crossing ambiguity.

### Account and asset isolation

**Selected:** The MVP may use the existing Binance account but requires exclusive control of the active symbol and explicit grid allocation. Foreign activity affecting allocated assets triggers a safety pause and reconciliation. Grid ownership is established by allocation and managed-order identity, not inferred from total account balances.

**Declined:** Inferring ownership after concurrent manual or algorithmic activity is ambiguous. A separate account or subaccount is not mandatory for the MVP. Concurrent strategies will later require either venue-level isolation or an account-level portfolio allocator with shared reservations and cross-strategy risk controls.

### Adjacent-cycle viability

**Selected:** Activation is rejected if any adjacent rung cycle lacks positive net cycle margin after maker fees, conservative execution allowance, venue rounding, and an approved safety margin. Validation reports the failing cycle but never alters the grid automatically.

**Declined:** Warnings permit knowingly loss-making turnover. Any-positive-spacing ignores real costs. Automatic widening changes the strategy configuration version that produced the evidence.

### Activation range eligibility

**Selected:** A grid may activate only when the current validated market price is strictly inside its configured lower and upper bounds. If price is at or outside a bound, activation is rejected before bootstrap acquisition or order placement. A fresh operator activation is required; the system does not remain armed for automatic later execution.

**Declined:** One-sided activation changes the validated inventory behavior. Automatic shifting or widening changes the approved strategy. Pending automatic activation could acquire inventory much later under changed conditions. Pending notification plus reapproval was declined in favor of the simpler explicit fresh activation workflow.

### Active price outside the range

**Selected:** An already-active static grid enters the range-exhausted state. It creates no exposure beyond the outer rungs, retains grid inventory and valid recovery-side orders, alerts the operator, and resumes normal cycling if price returns to the configured range.

**Declined:** Cancel-all pause discards valid recovery behavior. Immediate liquidation realizes exposure solely because a boundary was crossed. Automatic range shifting changes the approved static strategy and is deferred to a separately specified and validated adaptive-grid increment. A mandatory global stop-loss is not bundled into this state and will be decided separately.

### Operator pause

**Selected:** Pause is exposure-reducing: cancel and block buy orders, retain valid sell orders that reduce grid inventory, retain inventory, and block bootstrap or configuration changes.

**Declined:** Canceling every order removes safe inventory-reducing opportunities. Leaving buys active permits exposure to increase despite the pause. A UI-only pause does not change trading behavior and is not a trading state.

### Resume from pause

**Selected:** Resume requires an explicit operator request followed by reconciliation and revalidation of venue orders, fills, balances, grid inventory, current price state, venue rules, and risk limits. Only missing valid orders may be rebuilt. If price is outside the range, resume enters range-exhausted rather than creating new exposure.

**Declined:** Timeout-based or immediate resume assumes state remained unchanged. Starting a new bootstrap would incorrectly replace continuity with a different grid lifecycle.

### Normal operator stop

**Selected:** A normal stop permanently ends the run. Cancel all managed buy and sell orders, reconcile cancellation responses and racing fills, determine final grid inventory, then execute an explicitly selected disposition: retain or liquidate. Retain is the safe default. Liquidation requires a separate confirmation with estimated fees, slippage, and proceeds. Retained inventory becomes a retained holding linked to the closed run.

**Declined:** Always retaining removes a useful deliberate liquidation workflow. Waiting indefinitely for sell rungs prevents deterministic closure. Automatic liquidation conflates ending a strategy with selling an asset and may realize avoidable costs.

### Emergency stop

**Selected:** Block all new trading commands, cancel every managed buy and sell order, reconcile venue state including late fills, retain inventory, and require deliberate follow-up after authoritative state is restored. Emergency stop does not automatically liquidate.

**Declined:** Automatic liquidation can amplify an incident when market data, balances, or connectivity are unreliable. Leaving sells active permits continued execution after the system has declared an unsafe state. Per-grid emergency behavior weakens a universal safety invariant.

### Grid exits

**Selected:** The MVP uses paired rung sells for normal cycle profit and supports a configurable global stop-loss. When triggered, the stop-loss blocks new orders, cancels all managed orders, reconciles late fills, liquidates remaining grid inventory, records actual costs, and permanently closes the run. The threshold form and approval constraints belong to the risk specification.

**Declined:** Paired sells alone do not bound loss below the range. Global take-profit is deferred because upper sell rungs already reduce inventory and a whole-run favorable exit is not essential to the first validated strategy. Requiring every possible exit reduces deliberate strategy choice.

### Configuration identity and mutation

**Selected:** An approved strategy configuration version is immutable throughout a run. Changing bounds, rung count, spacing, sizing, bootstrap, or stop-loss creates a new version requiring new evidence and a new run. Operational risk limits may be tightened in place but not loosened without a new approval.

**Declined:** In-place or pause-time strategy edits break provenance and live parity. Automatically applying changes can alter capital exposure without explicit evidence or activation.

### Natural completion

**Selected:** A successfully activated static-grid run is open-ended. It continues until an explicit terminal condition such as operator stop, global stop-loss, or emergency termination permanently closes it.

**Declined:** Duration, cycle count, or zero inventory do not inherently complete a continuing grid strategy. They may become separately approved termination policies in later increments.

### Partial rung fills

**Selected:** After activation, every partial rung fill transfers ownership and is accounted for immediately. The strategy maintains one paired order per destination rung using cumulative filled quantity. Quantity below venue minimums remains pending and is added when more tradeable quantity accumulates.

**Declined:** Waiting for full fill leaves acquired inventory unpaired and understates state changes. Creating a separate paired order per execution fragments order count and complicates reconciliation.

### Outer-rung cycling

**Selected:** The lowest rung is buy-only and pairs inward to a sell one rung above. The highest rung is sell-only and pairs inward to a buy one rung below. Interior rungs may alternate sides. Repeated cycles never create orders beyond either bound.

**Declined:** Allowing outer rungs to reverse outward breaks the configured exposure boundary. Stopping after an outer fill prevents normal recovery cycles. Extending the ladder changes the approved static grid.

## Routed to downstream specifications

- Formal asset conservation, fee valuation, rounding, and reconciliation tolerances belong to **Specify accounting invariants and reconciliation**.
- Event ordering, deterministic command schemas, cancel/replace mechanics, and cross-mode fill behavior belong to **Specify simulation and execution parity**.
- Venue order states, post-only rejection, partial fills, identifiers, and filter refresh belong to **Research Binance Spot contract**.
- Exact post-only retry counts, elapsed-time bounds, displacement limits, backoff, and stale-book tolerances belong to **Specify simulation and execution parity** and **Specify risk model and safety state machine**; all modes must nevertheless implement the fail-closed policy above.
- Stop-loss thresholds, activation retry limits, safety margin, and risk-state transitions belong to **Specify risk model and safety state machine**.
