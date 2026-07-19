# Risk model and safety state-machine specification

Status: accepted on 2026-07-15  
Wayfinder ticket: [Specify risk model and safety state machine](../.scratch/comprehensive-grid-trading-system/issues/06-specify-risk-model-and-safety-state-machine.md)

## Decision-record policy

At the operator's request, every choice in this specification retains the complete recommendation, selected behavior, examples, consequences, assumptions, and declined alternatives. A later reader must be able to reconstruct why a rule exists without relying on conversation history.

## Scope

This specification defines the MVP's economic limits, operational-integrity controls, safety postures, transitions, permitted commands, recovery evidence, and deliberately tested failure behavior. It applies identically to deterministic replay, paper execution, venue-integration tests, and production execution; only the adapter and promotion permissions differ.

The MVP is Binance Spot only, one active grid on one symbol, with no borrowing, margin, leverage, short exposure, or automatic compounding. Controls apply to the isolated grid allocation rather than treating the whole Binance account as grid capital.

## Current-code audit

### Reusable foundations

The canonical `gridlab` code already provides:

- immutable run configuration;
- pre-acceptance rejection reasons for minimum quantity/notional, maximum open orders, maximum base inventory, gross exposure, insufficient cash/base, and prohibited short exposure;
- exchange quantization before constraint evaluation;
- order cancellation and flatten actions in the simulation engine;
- a configurable global price-based stop-loss;
- research metrics such as drawdown.

The legacy runtime additionally contains:

- configurable maximum notional per order, maximum open orders, and maximum base position;
- refusal events for those checks;
- a managed-order cancel-all helper described as a kill switch;
- percent- and ATR-based stop-loss/take-profit policy code;
- a periodic reconciliation setting.

These are candidates for migration or replacement behind canonical interfaces. Their existence is not evidence that the live safety requirements are satisfied.

### Material gaps and unsafe assumptions

- Limits use binary floating point and, in places, whole-account balances. They do not enforce the accepted exact-decimal, per-grid allocation model.
- Individual checks reject a command but do not drive a single explicit safety posture with deterministic permitted actions.
- There is no canonical daily-loss limit, current/conservative-liquidation-equity drawdown control, or combined committed-capital ceiling.
- Stale market data, private-stream gaps, connectivity loss, unknown submission outcomes, rate-limit pressure, reconciliation differences, duplicate/conflicting events, and accounting invariant failures do not map to defined safe transitions.
- Open-order reconciliation is insufficient for late fills, terminal orders, unknown submissions, stream gaps, and restart recovery.
- A cancel-all call does not itself prove that orders were cancelled. Late fills and unknown cancel outcomes still require reconciliation.
- Research drawdown and UI-displayed limits are observational; they are not live enforcement.
- The existing stop-loss trigger does not fully specify cancellation races, liquidation order behavior, partial liquidation fills, fees, retry identity, retained dust, or terminal reconciliation.
- There is no evidence-gated path from a degraded or emergency condition back to normal trading.

## Decision register

No risk decision is accepted merely because related code exists. Operator selections are added here in dependency order, beginning with the safety-posture architecture and then the quantitative capital, inventory, order, loss, data, connectivity, anomaly, stop, and recovery rules.

### Safety posture is separate from grid lifecycle

Selected by the operator on 2026-07-14: model safety as one explicit permission posture overlaid on, and separate from, the grid's business lifecycle.

The lifecycle answers what stage or condition the run is in, such as `BOOTSTRAPPING`, `ACTIVE`, `RANGE_EXHAUSTED`, `STOPPING`, or `CLOSED`. The safety posture answers which classes of command are permitted at that moment. A run may therefore be `ACTIVE + NORMAL`, `RANGE_EXHAUSTED + NORMAL`, or `ACTIVE + FROZEN` without duplicating lifecycle definitions.

The canonical postures are:

- `NORMAL`: normal grid placements, cancellations, and reconciliation are permitted, subject to every economic, venue, accounting, and operational limit.
- `REDUCE_ONLY`: commands that increase base-asset exposure are prohibited. For the spot-inventory MVP this cancels and blocks buys while permitting cancellation, reconciliation, and only valid fully backed sells that reduce grid inventory.
- `FROZEN`: no new order placement or replacement is permitted. The runtime may cancel managed orders, query authoritative evidence, admit late fills, and reconcile until actual venue and accounting state are established.
- `TERMINAL_LIQUIDATION`: the run has entered an approved terminal-disposal path. Only cancellation, reconciliation, and orders required to dispose of remaining grid inventory are permitted; ordinary grid cycling can never resume.
- `CLOSED`: no trading command is permitted. Post-run evidence capture and accounting remain possible.

#### Precedence and transition rules

- Exactly one effective safety posture governs command authorization at a time.
- When several triggers exist, precedence is `CLOSED > FROZEN > TERMINAL_LIQUIDATION > REDUCE_ONLY > NORMAL`. Thus an unknown order outcome freezes even a triggered stop-loss until reconciliation makes liquidation safe.
- Escalation is immediate, deterministic, idempotent, and recorded in the trading event journal with its triggering evidence.
- A command is checked against the effective posture immediately before durable transmission authorization, not merely when strategy intent was created.
- The strategy decision core, backtest, event replay, paper runtime, and live runtime consume the same canonical posture transitions and permissions.
- Expiry of time alone never proves recovery. The triggering conditions must be cleared using the required current evidence, and reconciliation must pass.
- Return from `FROZEN` after a decision-material incident requires explicit operator approval in addition to technical recovery. The trigger-specific rules and accepted decision-based materiality policy below define those incidents.
- `TERMINAL_LIQUIDATION` cannot transition to an open-run posture. It proceeds through reconciled terminal disposal to `CLOSED`.

Example: an `ACTIVE + NORMAL` grid reaches its daily-loss limit and becomes `ACTIVE + REDUCE_ONLY`; managed buys are cancelled while valid backed sells may reduce BTC inventory. If a cancellation has an unknown venue outcome, the effective posture becomes `ACTIVE + FROZEN`. Late fills remain real accounting events. Only after authoritative reconciliation and the required operator approval can a non-terminal run leave `FROZEN`.

#### Consequences

- Lifecycle logic remains comprehensible while safety rules are enforced at one command-authorization boundary.
- A visible posture, trigger set, transition reason, and recovery checklist can be logged, replayed, monitored, and presented consistently in the operator UI.
- The model does not imply that `cancel requested` means `cancelled`; cancellation outcomes and late fills remain subject to reconciliation.
- `REDUCE_ONLY` is a permission policy, not a promise that a sell will fill or that economic loss cannot increase while inventory remains.

#### Declined alternatives

- **One combined lifecycle-and-safety machine:** explicit in small examples, but creates duplicated states such as `active-frozen` and `range-exhausted-frozen`, multiplies transitions, and risks inconsistent safety behavior between lifecycle branches.
- **Independent safety flags:** initially simple, but permits contradictory combinations and forces precedence to be reimplemented at multiple call sites. Flags may exist as trigger evidence, but they do not independently authorize commands.

### Fixed, versioned grid capital envelope

Selected by the operator on 2026-07-14: every run uses a fixed, immutable grid capital envelope combined with an independent live-activation ceiling. The whole-account balance is coverage evidence only and can never enlarge the grid's authority.

The grid capital envelope contains:

- the exact native quantities of quote, base, and any third fee asset allocated to the run;
- one quote-equivalent capital-inflow ceiling for the run;
- a fee reserve included within that ceiling but unavailable for order principal;
- the activation valuation observations used to count allocated non-quote assets toward the ceiling.

The deployment has a separately controlled live-activation ceiling. The effective maximum approved capital is the lower of the run's configured ceiling and the deployment ceiling. Activation is rejected if the exact proposed allocation, conservatively valued where conversion is required, exceeds either ceiling or lacks authenticated account coverage.

#### Capital-flow rules

- A bootstrap acquisition converts allocated quote into allocated base and is not a new capital inflow.
- An existing base-holdings allocation counts toward the ceiling using its recorded conservative activation valuation. Allocated third-asset fee reserve is valued and counted the same way.
- Later market appreciation does not retrospectively breach the capital-inflow ceiling because no new capital entered the grid. Inventory, equity-drawdown, and loss controls govern the changed economic exposure.
- Realized profits and uncommitted quote remain grid-owned, but the non-compounded MVP cannot use them to enlarge rung principal, planned inventory, or the capital envelope.
- The grid cannot draw from free Binance balances, manual funds, or another algorithm's released capital.
- The MVP permits no in-run top-up or envelope increase. More capital requires a new immutable configuration, fresh validation, and explicit activation review. Returning or deallocating capital occurs only through accepted stop/closure evidence and the accounting specification's exact allocation, deallocation, and retained-holding postings.
- Allocation quantities, valuations, ceilings, configuration identity, approving operator action, and coverage evidence are durable activation evidence.

Example: a Binance account contains `10,000 USDT`, while a run has a `500 USDT` grid capital envelope including a `5 USDT` fee reserve and the deployment ceiling is `600 USDT`. The run may commit at most `495 USDT` to bootstrap and rung principal; the other `9,500 USDT` is unavailable. If instead the operator allocates base valued conservatively at `120 USDT` and a third-asset fee reserve valued at `5 USDT`, no more than `375 USDT` of quote may complete the `500 USDT` envelope. A later increase in the base market value changes grid equity but does not authorize more capital or larger rungs.

#### Consequences

- Maximum personal loss begins from a deliberate auditable amount rather than the contents of a shared exchange account.
- Other planned algorithms remain isolated even when they trade the same Binance account or assets.
- Exact native-asset accounting and a human-comprehensible quote-denominated approval limit coexist without replacing one another.
- A separate deployment ceiling limits damage from a mistaken or malicious run configuration.
- The accepted qualifying-paper and first-live ceiling values are fixed in the quantitative profile below; any promoted-live increase requires a new reviewed profile and fresh qualification evidence.

#### Declined alternatives

- **Fixed native quantities without an aggregate ceiling:** conserves assets precisely but does not express one clear maximum approved economic contribution when base, quote, and a third fee asset are combined.
- **Percentage of current Binance account equity:** deposits, withdrawals, price changes, and other algorithms would change the grid's authority dynamically and violate allocation isolation.
- **Use available account balance:** flexible but gives the strategy an unbounded and poorly auditable path into assets that were never approved for this run.

### Worst-case committed-inventory limit

Selected by the operator on 2026-07-15: authorize exposure-increasing orders against worst-case committed inventory, not merely the base inventory already received.

For a candidate buy, committed inventory is calculated from source-exact, venue-quantized quantities as:

`current grid inventory`

`+ every open buy's remaining quantity`

`+ every non-terminal buy's remaining quantity whose submission or cancellation outcome is unknown`

`+ the candidate buy quantity`

The result must not exceed the immutable maximum planned inventory derived from the approved grid configuration after venue rounding and fee treatment. Managed-order identity prevents multiple transmissions of the same obligation from being counted twice only when authoritative evidence proves that they represent the same venue order; uncertain possible duplicates remain separate exposure until reconciled.

#### Authorization and accounting rules

- Every exposure-increasing order is assumed capable of filling its entire remaining quantity immediately and before any sell fills.
- A partial buy fill increases current grid inventory, while the order's unfilled remainder remains committed inventory.
- An open, pending, or outcome-unknown sell does not reduce current or committed inventory until an actual fill transfers base to the venue counterparty.
- A buy replacement is prohibited while its predecessor could still execute. The predecessor continues to consume inventory headroom until authoritative terminal evidence is reconciled.
- Every candidate sell and remaining sell obligation must be fully backed by specifically reserved grid inventory. Current account holdings that are foreign to the grid provide no backing.
- Fees, rounding residuals, and late fills remain in exact grid inventory. They cannot be hidden using a tolerance or silently discarded.
- Realized profit and uncommitted quote cannot increase maximum planned inventory in the non-compounded MVP.
- Activation is rejected when the fully quantized grid plan can exceed its maximum planned inventory or when its buy obligations lack quote principal and fee coverage inside the grid capital envelope.
- The committed-inventory check runs when an intent is created, immediately before transmission authorization, and after every admitted order, execution, cancellation, fee, allocation, or reconciliation fact that can change the quantity.

Example: maximum planned inventory is `0.010 BTC`. Current inventory is `0.006 BTC`, an open buy has `0.002 BTC` remaining, and a submission-unknown buy may still acquire `0.001 BTC`. Committed inventory before a new order is `0.009 BTC`. A proposed `0.002 BTC` buy is rejected because it would produce `0.011 BTC`; at most `0.001 BTC` can be authorized. An open `0.003 BTC` sell does not create additional headroom until it fills.

#### Breach response and concentration scope

- A candidate order that alone would exceed the cap is rejected and durably explained. It does not silently resize itself.
- Reconciled actual or committed inventory above the cap transitions the run to `REDUCE_ONLY`, cancels exposure-increasing buys, and permits only valid backed inventory-reducing sells.
- An unexplained excess, possible duplicate venue order, conflicting evidence, or hard accounting violation transitions the run to `FROZEN` until authoritative reconciliation establishes the actual exposure.
- The MVP has one active grid and one symbol. Its grid capital envelope and maximum planned inventory are therefore its concentration boundary; portfolio and cross-grid concentration limits become mandatory before simultaneous live grids are introduced.

#### Consequences

- The system remains within its inventory approval even if every outstanding buy fills before any outstanding sell.
- Partial fills, cancel races, unknown submissions, and late fills are included without optimistic assumptions.
- Valid inventory-reducing orders are not blocked merely because their quote value rises, provided their quantity is fully backed and the current safety posture permits them.
- The existing current-inventory-only checks require replacement or deepening rather than direct reuse.

#### Declined alternatives

- **Current filled inventory only:** ignores executable and outcome-unknown buys, allowing several later fills to exceed the approved inventory.
- **Quote-value exposure only:** varies with price and cannot prove that native sell quantities are backed, although quote valuations remain useful for equity and loss controls.
- **Manual base cap independent of the grid plan:** understandable but can conflict with actual rung quantities after quantization and configuration changes. An independent deployment ceiling may remain a defense-in-depth activation check, but it cannot replace the plan-derived limit.

### Layered plan-derived order limits

Selected by the operator on 2026-07-15: authorize orders through concurrent rung, per-order, run, deployment, account-capacity, and venue-rule limits. No single `max_open_orders` value is sufficient.

An effective managed order is any identified grid obligation that the venue could still accept or execute, including pending transmission authorization, transmitted, submission-unknown, accepted, partially filled, cancellation-pending, and cancellation-unknown states. It stops occupying capacity only when authoritative evidence establishes a terminal outcome and every execution has been reconciled.

#### Rung and per-order limits

- Each rung has at most one effective managed order. An outcome-unknown predecessor continues to occupy its rung, so no replacement is authorized merely because a timeout or cancel request occurred.
- Every exposure-increasing buy has an immutable quote-principal ceiling derived from the approved sizing policy for that rung. Its fully quantized price and quantity must remain within the ceiling and all venue rules.
- A buy that exceeds its ceiling after validation or venue-rule changes is rejected rather than silently resized. A deliberate recalculation requires a new valid intent under the immutable configuration semantics.
- An inventory-reducing sell is limited by its exact backed quantity, paired or initial-sell obligation, safety posture, and venue rules. The buy-principal ceiling is not applied to its quote notional because a higher sell price can make a valid protective sell worth more than the originating buy.
- No order limit may prevent a cancellation request, evidence query, or reconciliation action.

#### Total effective-order capacity

The maximum permitted concurrent effective grid orders is the lowest of:

- the maximum simultaneous rung occupancy implied by the approved grid plan;
- the immutable run-level order ceiling;
- the independently administered deployment live-order ceiling;
- current authenticated venue/account capacity after subtracting all effective account orders and configured safety headroom;
- every applicable current Binance symbol, asset, account, and exchange filter or permission.

Foreign account orders do not become grid orders and do not consume the run-level grid ceiling, but they consume any shared Binance capacity applicable to this grid. A venue rule observation and an authenticated capacity observation are activation evidence. Activation is rejected when the plan's maximum simultaneous occupancy cannot fit the run or deployment ceilings, or current account/venue capacity cannot safely accept the initial ladder.

The count is checked when creating an intent, immediately before transmission authorization, and after every admitted fact that changes an order's effective or terminal status. Possible duplicate venue orders count separately until reconciliation proves their identity and terminal state.

Example: a 20-rung plan has a run ceiling of 20 and a deployment ceiling of 25. Six confirmed open orders and one submission-unknown order count as seven; the unknown order's rung remains occupied. A buy configured for `50 USDT` principal cannot exceed `50 USDT` after quantization. A later fully backed paired sell may have `55 USDT` notional because its price is higher, subject to venue rules and its exact inventory reservation.

#### Consequences

- Configuration mistakes, duplicate/uncertain commands, and unexpectedly large ladders are bounded independently of Binance's much broader protective limits.
- Other algorithms sharing the Binance account cannot silently grant the grid more authority and are included when calculating shared venue capacity.
- Order counts remain consistent across replay, paper, venue-integration, and live modes because the same canonical order states count in every mode.
- The accepted qualifying-paper and first-live run/deployment ceilings and venue headroom are fixed in the quantitative profile below.

#### Declined alternatives

- **One static `max_open_orders`:** resembles the legacy runtime but does not capture rung ownership, uncertain orders, configuration-derived demand, independent deployment protection, or shared venue capacity.
- **Binance limits only:** protects the venue, not the operator's personal risk boundary, and may be shared with unrelated account activity.
- **One order per rung only:** prevents same-rung duplication but allows a mistakenly large rung count to authorize an excessive number of live orders.

### Dual equity views with conservative safety valuation

Selected by the operator on 2026-07-15: maintain both current grid equity and conservative liquidation equity, using flow-adjusted conservative liquidation equity for economic safety decisions while retaining current grid equity for reporting and diagnosis.

Both views are deterministic projections of the same exact grid subledger and the same identified valuation bundle. They never maintain independent balances or apply a posted fee twice.

#### Current grid equity

Current grid equity is the quote value of exact grid-owned quote, base, and third-asset quantities at reproducible current marks. It explains marked portfolio value without pretending that the entire inventory could be converted at that mark. It is used for operator display, research decomposition, and comparison with conservative liquidation equity.

#### Conservative liquidation equity

Conservative liquidation equity estimates the quote asset that would remain if every non-quote grid asset had to be disposed of immediately. The projection includes:

- executable-side price evidence rather than a favorable midpoint;
- conservative spread and quantity-dependent slippage or depth assumptions;
- actual or conservatively selected fee rates and fee assets;
- venue rounding, minimums, and required conversion paths;
- zero liquidation value for a residual that current venue rules make non-disposable, while leaving its marked value visible in current grid equity;
- every already-posted asset quantity and fee exactly once.

For equal timestamps, assets, and conversion scope under non-negative liquidation costs, conservative liquidation equity must not exceed current grid equity. A violation is a valuation-model or evidence error.

Example: the grid owns `300 USDT` and `0.004 BTC`. A `60,000 USDT/BTC` mark produces current grid equity of `540 USDT`. If immediate disposal uses `59,850 USDT/BTC` and a `0.1%` fee, the expected net BTC proceeds are `239.1606 USDT`, producing conservative liquidation equity of `539.1606 USDT` before any other conversion cost.

#### Evidence and mode parity

- Every valuation records its source, event time, received time, processing sequence, conversion path, observed or modeled prices, quantities, fee assumptions, slippage/depth assumptions, venue-rule version, and evidence age.
- Backtests, replay, paper, and live execution use the same equity definitions. Their evidence sources may differ, but promotion comparisons must use the approved conservative assumptions for each fidelity level.
- Drawdown, daily-loss, and live-promotion safety checks use flow-adjusted conservative liquidation equity. Exact baselines, windows, thresholds, and responses are decided separately.
- Current grid equity and the liquidation-cost difference remain visible even when only conservative liquidation equity authorizes risk.
- If sufficiently current deterministic liquidation valuation cannot be produced for a decision-material grid asset, risk exposure cannot be established and the effective posture becomes `FROZEN`. The accepted freshness deadlines and decision-based materiality policy below govern this condition.

#### Consequences

- Protective controls measure an exit-aware value rather than an optimistic mark or realized trades alone.
- Operators can distinguish market movement from the modeled cost of immediate liquidation.
- Illiquidity, venue-invalid residuals, and third-asset conversions are made visible instead of being treated as cash.
- The runtime requires sufficiently current price, fee, venue-rule, and liquidity evidence to authorize new exposure.

#### Declined alternatives

- **Current marked equity for all purposes:** simpler but understates the realizable loss under spread, fees, slippage, and illiquidity.
- **Conservative liquidation equity only:** safe for limits but hides useful decomposition between marked asset value and modeled exit friction.
- **Realized result only:** ignores material unrealized losses and liquidation costs in retained inventory.

### Independent run-drawdown and UTC daily-loss guardrails

Selected by the operator on 2026-07-15: maintain independent run-drawdown and daily-loss guardrails, both measured from flow-adjusted conservative liquidation equity and both capable of removing permission to increase exposure.

These are exposure guardrails, not terminal loss guarantees. Crossing one selects `REDUCE_ONLY`; remaining spot inventory can continue losing value until sold or until a separately approved terminal stop-loss triggers.

#### Run drawdown

- The run high-water mark is the greatest valid flow-adjusted conservative liquidation equity observed since the grid allocation was admitted for the run.
- Bootstrap acquisition costs, fees, spread, and slippage therefore count economically; the baseline is not moved to a later favorable post-bootstrap value.
- Run drawdown amount is `high-water equity - current flow-adjusted conservative liquidation equity`, floored at zero.
- Run drawdown ratio is that amount divided by high-water equity. A non-positive or unavailable denominator is an invariant or valuation failure, not a zero drawdown.
- The high-water mark may rise but never resets or falls during the open run. A process restart, pause, range-exhausted period, UTC boundary, or resume does not reset it.

#### Daily loss

- A risk day is the half-open UTC interval `[00:00:00, next 00:00:00)`, represented by a canonical domain-timer boundary rather than the runtime machine's local clock.
- The daily baseline is the first valid flow-adjusted conservative liquidation equity at or after the UTC boundary, or the run's initial valid value when activated later that day.
- Daily loss amount is `daily baseline - current flow-adjusted conservative liquidation equity`, floored at zero.
- Daily loss ratio is that amount divided by the daily baseline. Intraday gains do not raise the daily baseline; giveback from an intraday peak remains visible through run drawdown.
- Approved allocations and deallocations are removed by flow adjustment and cannot manufacture a gain, loss, high-water mark, or daily reset. The MVP separately prohibits in-run top-ups.

#### Thresholds, response, and recovery

- Each guardrail configures both an absolute quote-asset loss threshold and a percentage threshold. Reaching either one triggers the guardrail; a missing or disabled threshold must be explicit and cannot result from absent data.
- Reaching 80% of the currently nearest enabled threshold emits an alert and durable risk observation without changing safety posture. The accepted first-live thresholds are fixed in the quantitative profile below.
- Reaching 100% transitions the run to `REDUCE_ONLY`, blocks and cancels buys, and retains only valid fully backed inventory-reducing sells.
- Each breach is latched and journalled with the equity values, baseline/high-water evidence, absolute and percentage calculations, threshold configuration, valuation bundle, and canonical event that caused evaluation.
- A new UTC day makes a daily-loss breach eligible for recovery but never resumes trading by time alone. Fresh valuation, cleared triggers, successful reconciliation, and explicit operator approval are required.
- A run-drawdown breach remains active until current flow-adjusted conservative liquidation equity is again above every breached threshold or the run terminates; recovery still requires reconciliation and operator approval.
- Historical simulation and replay represent day boundaries and operator decisions as canonical events so the same transition rules remain testable. Validation scenarios must state their operator-resume policy rather than silently assuming one.

Example: a run begins at `500 USDT`, reaches a conservative-liquidation-equity high-water mark of `530 USDT`, starts the current UTC risk day at `515 USDT`, and now has `503 USDT`. Run drawdown is `27 USDT`, or approximately `5.09%`; daily loss is `12 USDT`, or approximately `2.33%`. With illustrative limits of 5% run drawdown and 3% daily loss, run drawdown triggers `REDUCE_ONLY` first. These percentages are examples, not accepted starting values.

#### Consequences

- One severe day and gradual cumulative deterioration are controlled independently.
- UTC provides deterministic boundaries across Azure, Binance, replay, and daylight-saving changes.
- High-water drawdown detects the return of prior profits even when equity remains above initial allocation.
- The explicit latch prevents an oscillating price from rapidly enabling and disabling buys around a threshold.
- A separate terminal boundary remains necessary because reducing future exposure does not dispose of retained inventory.

#### Declined alternatives

- **Run drawdown only:** controls cumulative deterioration but provides no distinct daily operating budget.
- **Daily loss only:** can permit repeated losing days across an open-ended run and ignores giveback relative to the run high-water mark.
- **Realized-loss limits:** ignore unrealized deterioration and immediate-disposal costs in retained grid inventory.

### Dual immutable global stop-loss boundary

Selected by the operator on 2026-07-15: the irreversible global stop-loss has two independently evaluated immutable triggers—an exact price floor and a fixed conservative-liquidation-equity floor. Reaching either trigger permanently ends grid cycling and starts the terminal-disposal workflow.

#### Price floor

- The strategy configuration stores one exact, venue-valid stop price strictly below the grid's lower bound. The UI may explain it as a percentage distance, but the persisted threshold is an exact price.
- The trigger uses a fresh admitted executable-side market observation rather than a midpoint or a candle close.
- The first valid observation at or below the floor triggers the stop. No persistence delay, rebound confirmation, or operator confirmation is required after activation approval.
- In candle simulation, a bar low at or below the price floor proves that the trigger was touched, and the approved conservative intrabar/execution policy applies. Event replay, paper, and live modes use ordered canonical market observations.
- The floor is a trigger, not a guaranteed execution price. A gap or thin book can produce terminal-disposal fills below it.

##### First-live stop-price selection

Selected by the operator on 2026-07-15: treat the exact price floor as a strategy-search parameter selected jointly with symbol, grid bounds, rung count, spacing, fixed quote sizing, maximum planned inventory, and execution assumptions, while subjecting every candidate to an independently fixed capital-safety constraint.

For a candidate plan:

1. Select and validate the stop price through the accepted backtest and walk-forward process; out-of-sample evidence validates rather than retunes the candidate.
2. Round it to an exact venue-valid price strictly below the lower grid bound. Rounding must not weaken the accepted threshold.
3. Project flow-adjusted conservative liquidation equity at that exact stop using maximum planned inventory, actual fee-asset policy, taker fees, executable spread/depth, slippage, the accepted IOC disposal bounds, venue rounding, and zero liquidation value for any venue-invalid residual.
4. Require projected conservative liquidation equity to be at least the terminal equity floor plus a stop-price safety buffer equal to 2% of initial valid conservative liquidation equity.
5. Reject any candidate that fails. The plan must raise the stop, narrow or move the grid range, reduce planned inventory, reduce sizing, or otherwise change strategy parameters; it may not loosen the terminal equity floor or safety buffer to pass.
6. Persist the accepted exact stop and all modeling assumptions in the immutable strategy configuration version. Qualifying paper and first live operation use that same price and semantics.

For a run admitted with the full `250 USDT`, the accepted 12%/`30 USDT` terminal allowance produces a `220 USDT` terminal equity floor. The 2% safety buffer is `5 USDT`, so modeled conservative liquidation equity at the exact stop must be at least `225 USDT`.

Example: a candidate grid has a lower bound of `90` and a venue-valid stop price of `87`. If maximum-inventory disposal at `87`, including all accepted costs and IOC assumptions, projects `227 USDT`, the capital-safety constraint passes. If it projects `221 USDT`, the plan fails even if its historical return is attractive; it must change its strategy parameters rather than expand the accepted loss.

Validation must also report discontinuous gap-through scenarios at 1%, 3%, and 5% below the exact stop, using the same disposal model. These scenarios are stress evidence, not alternate trigger prices and not guaranteed loss caps. A candidate whose gap behavior is unacceptable may be rejected even though its at-stop projection passes.

###### Consequences

- Rung count and stop placement remain jointly testable strategy choices, but the capital loss allowance and buffer remain independent risk policy.
- Different symbols, ranges, inventory plans, or liquidity conditions can require different exact stop prices.
- A historically profitable plan cannot qualify by moving its stop so far away that maximum-inventory liquidation consumes the independent capital boundary.
- Paper/live parity covers the exact trigger; fill prices and completion can still differ because the stop cannot prevent gaps, outages, rejections, or empty books.

###### Declined alternatives

- **Fixed 5% below the lower bound:** simple and comparable, but the resulting economic loss varies with inventory, volatility, spread, fees, and liquidity.
- **Volatility-multiple stop without the capital constraint:** adapts to historical movement but can authorize a loss inconsistent with the fixed first-live capital policy.
- **Equity-only terminal trigger:** directly measures economics but removes the independently visible price boundary already accepted for the global stop-loss.

#### Equity floor

- The fixed equity baseline is the run's initial valid flow-adjusted conservative liquidation equity when its grid allocation is admitted. Bootstrap and later trading costs reduce equity relative to this baseline.
- The configuration contains both an absolute quote-asset terminal-loss allowance and a percentage allowance. The smaller permitted loss produces the higher, more protective equity floor.
- The first valid conservative liquidation equity at or below that floor triggers the stop.
- Unlike run drawdown, this terminal equity floor does not trail a later high-water mark. The separate run-drawdown guardrail detects profit giveback and selects `REDUCE_ONLY` before terminal loss where configured.

Example: initial conservative liquidation equity is `500 USDT`, the exact stop price is `54,000 USDT/BTC`, and terminal allowances are `50 USDT` or 8%. The smaller permitted loss is `40 USDT`, so the equity floor is `460 USDT`. Either a fresh executable-side price at or below `54,000` or conservative liquidation equity at or below `460` permanently triggers the stop. These values are illustrative, not accepted starting thresholds.

#### Trigger and safety behavior

- The terminal trigger is latched, idempotent, journalled with its complete evidence, and cannot be cleared by a price or equity recovery.
- Once latched, no ordinary grid order or future run resume is permitted under this run identity and configuration version.
- The runtime blocks new placements, requests cancellation of every managed grid order, admits and accounts for late fills, and reconciles venue orders, fills, balances, reservations, and grid inventory before or during bounded terminal-disposal waves.
- If a higher-precedence condition prevents safe command authorization—such as stale material valuation, a stream gap, unknown order exposure, or conflicting accounting evidence—the effective posture is `FROZEN`. The terminal trigger remains latched and `TERMINAL_LIQUIDATION` becomes effective only when authoritative evidence makes disposal commands safe.
- Every mode uses the same trigger semantics. Backtests and paper simulations must model gaps, fees, spread, slippage, partial disposal, and rejection rather than filling automatically at the threshold.

#### Consequences

- The price floor provides a transparent market boundary, while the equity floor accounts for actual inventory, fees, and exit friction.
- Either trigger can protect against failure or insufficiency of the other, but both still depend on fresh authoritative evidence.
- The terminal equity floor protects initial approved capital rather than automatically locking every interim profit; the non-terminal high-water drawdown guardrail handles profit giveback.
- A stop cannot promise a maximum realized loss because connectivity failure, gaps, liquidity, rejection, partial fills, and venue constraints can delay or worsen disposal.

#### Declined alternatives

- **Price floor only:** easy to see and backtest, but the economic loss at a given price changes with inventory, fees, execution friction, and capital deployment.
- **Equity floor only:** directly economic but entirely dependent on sufficiently current valuation and liquidity evidence and lacks a simple visible market boundary.
- **Operator-triggered liquidation only:** avoids automatic disposal on brief shocks but provides no unattended terminal protection.

### Staged marketable IOC terminal disposal

Selected by the operator on 2026-07-15: dispose of terminal inventory through bounded waves of marketable limit sells using immediate-or-cancel (`IOC`) time in force. Completion has priority over maker status, while every attempt retains an explicit worst acceptable price and never falls back automatically to an uncapped market order.

An IOC sell may execute immediately against available bids at or above its limit price; any unfilled remainder becomes terminal rather than resting in the book. It is an aggressive order and is accounted as taker liquidity wherever the venue reports it that way.

#### Preconditions

- The terminal loss boundary is durably latched and ordinary grid cycling is permanently disabled.
- All managed grid orders have cancellation requested, and authoritative reconciliation has established every terminal, still-effective, or outcome-unknown obligation sufficiently to calculate safe disposable inventory.
- A higher-precedence `FROZEN` condition blocks disposal placement until unknown orders, conflicting evidence, stale material inputs, and hard accounting violations are resolved.
- Each disposal attempt requires fresh authenticated balances, exact available grid inventory, current venue rules and fees, and fresh executable order-book depth.

#### Disposal waves

- The runtime calculates a venue-valid child quantity from confirmed disposable inventory, observed depth, configured participation/child-size bounds, quantity filters, and fee treatment.
- It calculates an explicit IOC sell limit from current bids and the configured maximum acceptable slippage for that attempt. Price quantization must never weaken the accepted worst-price boundary.
- Each attempt has a unique managed command identity linked to one terminal-disposal plan and the triggering global stop-loss.
- After each response, partial fill, rejection, timeout, cancellation, or execution event, the runtime admits evidence, posts actual assets and fees, reconciles the order, refreshes the book, and recomputes remaining inventory before authorizing another child.
- A submission-unknown or cancellation-unknown disposal order selects `FROZEN`; no next child is sent until the possible execution is reconciled.
- A late grid-buy fill discovered during disposal increases terminal inventory and is included in a later wave after its order and accounting evidence are reconciled.
- Attempts are bounded by immutable maximum child quantity/participation, per-attempt slippage, total attempt count, and total elapsed domain time. The first-live values are specified below.
- No fallback may silently submit `MARKET`, post-only, good-till-cancelled, or a sell below the attempt's approved limit.

Example: confirmed disposable inventory is `0.010 BTC`, while fresh depth supports approximately `0.004 BTC` within the configured slippage bound. The first IOC sell requests `0.004 BTC`. If `0.003 BTC` executes and `0.001 BTC` is cancelled, the runtime posts and reconciles the `0.003 BTC` fill before using fresh evidence to calculate the next child; it never assumes the full request filled.

#### First-live quantitative bounds

Selected by the operator on 2026-07-15: apply all of these independent bounds to each first-live terminal-disposal plan:

- the requested child is the smallest of confirmed remaining disposable inventory, `50 USDT` quote-equivalent notional, and 10% of fresh executable bid depth available inside the attempt's accepted price band;
- the IOC limit may be no more than 1% below the fresh best bid used to authorize that attempt; venue price quantization must preserve or tighten this worst-price boundary;
- authorize at most 5 child attempts;
- authorize children only during the first 30 seconds of domain time after the disposal plan becomes placement-eligible;
- refresh executable depth, venue filters, fee assumptions, balances, order/fill evidence, and remaining inventory after every attempt before authorizing another;
- an unknown attempt outcome immediately selects `FROZEN`, stops the attempt/time progression for placement purposes, and forbids another child until the authoritative result is reconciled.

These are per-attempt execution bounds, not a promise that the complete holding will be sold within 1% of the price that originally triggered the stop. In a falling market, each reconciled attempt can begin from a lower fresh best bid. A gap, empty book, venue rejection, or outage can prevent or worsen completion even though every submitted order respected its own bound.

Example: confirmed disposable inventory is worth `140 USDT`, but 10% of the fresh bid depth inside the 1% band supports only `35 USDT`. The first child is therefore `35 USDT`, not `50 USDT` or the full holding. If only `25 USDT` fills, the runtime reconciles that exact fill and all fees, refreshes the book, and recomputes the next child from the remaining inventory and new depth. It never carries forward the cancelled `10 USDT` as though it executed.

If venue-valid material inventory remains when 5 attempts or 30 eligible seconds are exhausted, the terminal latch remains set, posture becomes `FROZEN`, and a critical alert requires deliberate operator action; the run is not closed. A final venue-invalid residual may instead become an exact retained holding only after authoritative final reconciliation proves that it cannot satisfy the venue's current minimum quantity/notional constraints.

Backtest, replay, and paper qualification must exercise partial fills, successively lower bids, gap-through, rejection, outcome-unknown recovery, attempt exhaustion, elapsed-time exhaustion, material residuals, and venue-invalid retained holdings under these same bounds.

##### Consequences

- A single child cannot consume the whole visible book or more than `50 USDT`, which limits the impact of stale or misleading depth evidence.
- The 1% boundary caps each submitted IOC's authorized price reach while leaving completion explicitly fallible.
- Five attempts and 30 seconds bound automated terminal activity and produce a deterministic escalation point suitable for replay.
- The `250 USDT` first-live capital ceiling makes the `50 USDT` child ceiling at most 20% of initial approved capital, before the depth bound reduces it further.

##### Declined alternatives

- **Tighter `25 USDT`, 0.5%, 10-attempt, 60-second profile:** reduces per-child impact but prolongs exposure and increases command/reconciliation count during a falling market.
- **Aggressive full-inventory, 3%, 3-attempt, 15-second profile:** seeks faster completion but permits much larger impact and loss from thin or rapidly changing liquidity.
- **Entirely backtest-derived disposal bounds:** could optimize to historical liquidity without preserving a hard, independently accepted first-live execution ceiling.

#### Completion, residuals, and failure

- Material inventory remaining when an attempt, elapsed-time, evidence, liquidity, or slippage bound is exhausted leaves the terminal latch active and selects `FROZEN`. The runtime emits a critical alert and requires deliberate operator action; it must not mark the run closed or flat.
- When all executable material inventory is disposed, every disposal order is terminal, and final order/fill/balance/accounting reconciliation passes, the terminal-disposal plan may complete.
- A venue-invalid residual that cannot satisfy current minimum quantity/notional after rounding is preserved as an exact retained holding with its provenance and conservative liquidation value. It is never discarded or reported as zero inventory.
- A run with only a fully reconciled non-disposable residual may close while explicitly reporting that retained holding. Later disposition is foreign to the closed grid unless a separately approved workflow adopts it.
- Actual fills, fees, slippage, residuals, attempts, rejections, unknown outcomes, elapsed time, and final equity/result are durable terminal evidence and are reproduced by replay fixtures.

#### Consequences

- Immediate execution is sought without granting the adapter an unlimited worst price.
- Large or thin-book inventory can be sold in evidence-driven portions rather than one blind command.
- A hard stop can still fail to liquidate fully; the failure becomes a visible frozen terminal incident rather than hidden exposure or an uncapped fallback.
- Backtest and paper models must support IOC partial fills, depth/participation limits, rejection, gaps, and residuals to claim terminal-path parity.

#### Declined alternatives

- **One Binance market sell:** has high immediate execution probability but no explicit worst price and can experience severe or anomalous slippage.
- **One stop-limit or passive limit sell:** controls price but can rest unfilled while the market continues falling, contradicting aggressive terminal-disposal intent.
- **Cancel and wait for the operator:** avoids automated execution mistakes but provides no unattended terminal disposal after an already approved stop.

### Input-specific fail-closed continuity model with staged MVP implementation

Selected by the operator on 2026-07-15: retain a complete input-specific failure model as the live-safety contract, while implementing the first paper MVP through a deliberately minimal three-rule matrix. This is a staged delivery boundary, not permission to omit the controls before real-money promotion.

#### Minimal three-rule matrix

1. When strategy-decision market inputs are stale but independent executable valuation, private order/fill state, authenticated balances, and the control path remain trustworthy, select `REDUCE_ONLY`: cancel and block buys while valid backed sells may remain.
2. When executable pricing/valuation, material orders, fills, balances, allocation coverage, authenticated control, or clock validity is uncertain, select `FROZEN`: authorize no placement or replacement, cancel managed orders where the control path permits, and reconcile.
3. Connection restoration or passage of time never resumes trading. Recovery requires fresh evidence, continuity/gap repair, successful reconciliation, cleared triggers, and explicit operator approval after a material frozen incident.

The more restrictive rule wins. For example, stale strategy candles alone can select `REDUCE_ONLY`, but stale executable quotes make conservative liquidation equity unavailable and therefore escalate to `FROZEN`.

#### Evidence distinctions

- Connection health and data freshness are independent. A socket may remain connected while its data is stale; a quiet private stream may be healthy despite having no recent fill event.
- Public decision and executable-market freshness use source event time, received time, processing order, and an explicit maximum age appropriate to the input.
- Private-stream continuity uses connection/sequence evidence plus periodic authenticated snapshots and reconciliation; it is never inferred from time since the last trade.
- Planned finite-lifetime WebSocket rotation changes no posture when overlap and continuity are proven before the old connection is retired. An unproven gap selects `FROZEN`.
- Authenticated REST reconciliation/control unavailability, material clock skew or timestamp rejection, and inability to preserve API capacity for safety actions select `FROZEN`.
- Rate-limit pressure sheds nonessential research/UI requests before safety, cancellation, order-query, account-query, and reconciliation capacity. Exhausting reserved safety capacity is a frozen incident.
- Every critical input class has an explicit configured freshness/continuity deadline. Missing required deadlines reject activation; the accepted provisional first-live values are fixed in the quantitative profile below and may be tightened by paper evidence.

#### Required delivery stages

The first paper MVP must include:

- market-decision and executable-valuation freshness detection;
- private-stream disconnect and unproven-gap detection;
- authenticated REST/control availability detection;
- clock-skew and authenticated timestamp-failure detection;
- deterministic `REDUCE_ONLY` and `FROZEN` transitions;
- reconciliation and operator approval before resume;
- structured journal/log/metric/alert evidence for every transition;
- deliberate fault tests that disconnect or stale each critical channel.

Before any real-money activation, the system must additionally demonstrate:

- planned overlapping WebSocket rotation;
- authenticated snapshot/backfill and reconciliation after gaps;
- reserved request-weight/order capacity for cancellations, queries, and reconciliation;
- tested `429`, `418`, `Retry-After`, timeout, and timestamp-error behavior;
- accepted quantitative freshness, retry, backoff, and recovery deadlines;
- restart and recovery fault tests using the same state-machine rules.

Deferred beyond the first live-safe MVP are redundant market-data providers, automatic cross-region failover, adaptive timeout calculation, fully automated material-incident recovery, and application-level high availability.

Example: the strategy event stream stops, while an independent executable quote, private stream, authenticated account snapshot, and REST control path remain valid. The grid selects `REDUCE_ONLY`. If executable valuation later exceeds its deadline, the grid escalates to `FROZEN`. Reconnecting the strategy stream does not authorize a resume until continuity and current state are proven and the required operator approval is admitted.

#### Consequences

- The architecture remains safe enough to grow into live trading without implementing expensive redundancy before paper evidence exists.
- The paper run exercises the same fundamental degraded states that live trading requires.
- Azure service reliability cannot mask failures in Binance, internet paths, authenticated requests, local clocks, or event continuity.
- The distinction between required semantics and deferred automation prevents both under-specification and premature high-availability engineering.

#### Declined alternatives

- **One global timeout:** easy to configure but treats market decisions, executable valuation, private state, control access, and clock validity as if they had identical meaning and safe response.
- **Continue with cached values:** preserves apparent uptime by authorizing decisions from obsolete prices or incomplete account evidence.
- **Cancel everything on every disconnect:** needlessly disrupts proven planned rotation and recoverable public-decision staleness while still failing to define connected-but-stale or missed-private-event behavior.
- **Defer the entire topic until live:** prevents the mandatory paper period from validating the degraded states and recovery behavior used as live-promotion evidence.

### Three-tier evidence-based anomaly classification

Selected by the operator on 2026-07-15: classify anomalies by whether exact exposure and authoritative state remain established, using one canonical three-tier policy rather than subsystem-specific severity.

#### Tier A — explained and bounded

Tier A causes no safety-posture change when durable evidence proves that exposure and state remain known. Examples include:

- a local validation refusal before transmission authorization;
- an expected post-only rejection with an authoritative rejection response;
- a duplicate canonical event whose identity and complete payload are identical to the already admitted event;
- identified pending evidence that cannot change exposure, reservations, assets, order identity, or risk state.

Every Tier A condition has an explicit retry, count, displacement, or evidence deadline. Exhausting its bound escalates according to what is then known: a fully known economic restriction becomes Tier B, while uncertain state becomes Tier C.

#### Tier B — known economic restriction

Tier B selects `REDUCE_ONLY` because state is reconciled but increasing exposure is no longer authorized. Examples include:

- reconciled actual or committed inventory above maximum planned inventory;
- a daily-loss or run-drawdown guardrail;
- a venue-rule change that makes new exposure invalid while existing orders, assets, and obligations remain fully established;
- insufficient plan, deployment, account, or venue capacity for normal cycling with no uncertain order outcome.

Tier B does not permit silent resizing, reconfiguration, capital use, or automatic resume. Valid fully backed inventory-reducing sells remain subject to the effective posture and current venue rules.

#### Tier C — state uncertainty or invariant failure

Tier C selects `FROZEN` because exact exposure or trustworthy state cannot be proven. Examples include:

- submission-unknown or cancellation-unknown commands;
- a possible duplicate venue order or conflicting reuse of an identity;
- an unproven private-stream gap;
- an unexplained, local-ahead, venue-ahead beyond its evidence deadline, or conflicting reconciliation item affecting material grid state;
- a hard accounting violation, impossible reservation, negative spot inventory, or failure to reconstruct the same state from the journal;
- foreign activity affecting grid-allocated assets or managed order identity;
- durable journal/state persistence failure;
- unavailable evidence required to calculate exact orders, balances, allocation coverage, or conservative liquidation equity.

The runtime blocks placements, cancels managed orders where safely possible, preserves all original evidence, and reconciles. A terminal loss trigger remains latched through Tier C and disposal resumes only after the frozen cause is cleared.

#### Classification and recovery rules

- Classification depends on the proven effect on exact exposure and state, not the exception class, HTTP code, log severity, or subsystem that observed it.
- Identical duplicate evidence may be deduplicated idempotently; the same identity with different content is conflicting evidence and Tier C.
- Foreign activity unrelated to allocated assets or managed order identities remains foreign, is logged/monitored, and does not change grid posture. Foreign activity touching the allocation is Tier C until attributed and reconciled.
- No repair overwrites journal, order, fill, or accounting history. Repairs append authoritative evidence or compensating records with provenance.
- Tier B recovery requires cleared restrictions, fresh risk evidence, reconciliation, and operator approval where already required by the triggering guardrail.
- Tier C recovery requires authoritative evidence, deterministic journal rebuild, all invariant checks, complete reconciliation, cleared triggers, and explicit operator approval.
- Materiality and evidence deadlines never authorize omission, tolerance-netting, or deletion of a native-asset difference; the accepted first-live policy below governs only how quickly the difference changes posture.

Example: an order submission times out. Because the buy may exist or may already have filled, it is Tier C and selects `FROZEN`; blind retry is prohibited. If an authoritative query later proves that Binance never accepted the identified order and all orders, fills, balances, reservations, and accounting reconcile, the incident becomes eligible for operator-cleared recovery.

#### First-live decision-based materiality and evidence deadline

Selected by the operator on 2026-07-15: record and reconcile every source-exact native-asset difference without a fixed quote-value or percentage tolerance. Materiality is determined by whether the difference can change a domain decision or makes authoritative state uncertain, not merely by its current marked value.

Any of the following is decision-material and selects `FROZEN` immediately:

- an unidentified, conflicting, missing, or outcome-unknown managed order, fill, trade, fee, balance event, or command identity;
- a difference that can change grid inventory, committed inventory, backing inventory, a reservation, allocation coverage, fee coverage, maximum planned inventory, or authorization of any candidate command;
- a difference that can change current or conservative liquidation equity across a loss warning, guardrail, terminal boundary, capital ceiling, or stop-price safety constraint;
- a failed accounting invariant, impossible native quantity, journal-rebuild mismatch, or inability to reproduce the difference from canonical evidence;
- one difference, or the source-exact aggregate of related differences in the same asset and causal scope, that reaches a current venue-valid tradeable quantity/notional;
- any smaller difference whose cause or possible consequences are not sufficiently identified to prove that none of the preceding conditions applies.

A difference may remain Tier A `Pending evidence` only when it has a specific expected evidence source, cannot change exposure, assets available to commands, order identity, accounting validity, or any risk decision, and remains exact and visible in reconciliation. Its deadline is the earlier of 60 domain seconds after detection or completion of the next full reconciliation cycle. If the expected evidence has not explained and reconciled it by that boundary, it becomes an unexplained difference and selects `FROZEN` regardless of size.

Confirmed venue rounding, fee postings, and venue-invalid residuals are not ignored tolerances. Once authoritative evidence explains them and the exact postings/classifications reconcile, they are ordinary reconciled state and do not change posture. Related small differences are aggregated before materiality is evaluated, so fragmentation cannot keep a tradeable or decision-changing amount below the rule.

Example: an authoritative venue rule and exact postings prove a `0.20 USDT` rounding residual that remains grid-owned; reconciliation passes and no freeze occurs. An unexplained `0.20 USDT` observation with an identified in-flight balance update may remain pending only within the 60-second/next-cycle bound. An unknown `0.20 USDT` fee that could invalidate native fee coverage, or an unknown order/fill of the same value, freezes immediately.

The qualifying 30-day paper run must finish with zero unresolved reconciliation items of any size. Transient pending items are acceptable only when they remain inside this policy, later reconcile completely, and are included in the qualification evidence; no unexplained difference may be waived by value.

##### Consequences

- Operational response follows economic and state consequences rather than an arbitrary `USDT` epsilon.
- Small, causally identified evidence races receive one bounded reconciliation opportunity without becoming invisible.
- Unknown order/fill exposure and accounting contradictions fail closed even when their marked amount is small.
- Exact aggregation prevents many sub-threshold differences from accumulating outside safety decisions.

##### Declined alternatives

- **Freeze on every observed difference immediately:** literal but treats normal, causally identified ordering delays between authoritative evidence sources as invariant failures before reconciliation can complete.
- **Fixed `1 USDT` tolerance:** simple but can hide accumulated discrepancies or a smaller difference that changes fee coverage, order validity, or a loss boundary.
- **One percent of grid capital:** scales numerically but is unrelated to venue tradability and would permit up to `2.50 USDT` of unexplained difference in the full first-live envelope.

#### Consequences

- Routine bounded refusals remain observable without turning every harmless event into an incident.
- Known economic restrictions stop new exposure while preserving safe inventory reduction.
- Any uncertainty about real orders, assets, or accounting fails closed consistently across adapters and modes.
- The classification can be logged, alerted, replayed, tested, and displayed without each subsystem inventing its own safety action.

#### Declined alternatives

- **Freeze on every anomaly:** conservative but makes harmless local refusals and identical duplicate delivery operationally disruptive.
- **Log and continue for every anomaly:** allows unknown commands, unexplained assets, and invariant failures to accumulate behind apparent uptime.
- **Subsystem-specific decisions:** flexible locally but creates inconsistent severity, conflicting transitions, and no single auditable authorization policy.

### Cancel on planned shutdown and always restart frozen

Selected by the operator on 2026-07-15: a planned process shutdown cancels and reconciles every managed order, while every process start or restart begins `FROZEN` and can never automatically resume trading. Azure may restart infrastructure automatically; it cannot grant domain trading authority.

Process shutdown is operational, not a terminal grid condition. It neither closes the run nor disposes of grid inventory. This differs from operator stop, emergency stop, exposure-reducing pause, and global stop-loss, whose accepted domain meanings remain unchanged.

#### Planned shutdown

- Admit and durably record a shutdown-request event, select `FROZEN`, and block new placement/replacement authorization before beginning teardown.
- Request cancellation of every managed buy and sell, including inventory-reducing sells. A shutdown is not an exposure-reducing pause because no order should remain executable while the single runtime is intentionally absent.
- Continue admitting user-stream and query evidence during shutdown; account for racing/late fills; reconcile cancellations, effective orders, fills, balances, reservations, allocation coverage, grid inventory, and safety state.
- Persist and verify the journal position, durable domain state or rebuild evidence, outstanding reconciliation items, terminal latches, and shutdown outcome before clean exit when possible.
- Apply the accepted 60-second graceful-shutdown interval below. Exceeding it records a critical incomplete-shutdown incident with all unresolved command identities and evidence; it never records a clean or reconciled shutdown merely because the operating system deadline expired.
- If the platform forcibly terminates the process before completion, recovery follows the crash path.

##### First-live graceful-shutdown bound

Selected by the operator on 2026-07-15: a planned process shutdown has 60 domain seconds from admission of the shutdown request to cancel and reconcile every managed order and persist a provably clean shutdown outcome.

- The runtime selects `FROZEN` and requests all managed cancellations immediately; the timer does not delay safety action.
- At 30 seconds, an incomplete shutdown produces a warning containing outstanding effective/outcome-unknown orders, reconciliation items, control-path health, journal position, and remaining platform allowance.
- Until the 60-second boundary, the runtime continues admitting late fills and authoritative responses, posting fees/assets, querying as capacity permits, reconciling, and durably updating the shutdown incident.
- A clean exit is permitted only when all managed orders are terminal, orders/fills/balances/allocation/accounting reconcile, invariant and journal-integrity checks pass, and the final durable shutdown record is verified.
- At 60 seconds, any unresolved item produces a critical incomplete-shutdown record with every identity and known fact. The process persists recoverable state and exits unsuccessfully; it does not report clean shutdown or infer cancellation from elapsed time.
- The hosting termination allowance must exceed 60 seconds by enough to persist the incomplete outcome; the deployment specification selects the exact infrastructure allowance. Forced termination before durable completion follows the crash path.
- Azure may restart the unsuccessful process, but every replacement begins `FROZEN`, presumes unresolved venue orders survived, performs the accepted startup recovery, cancels surviving orders, reconciles, and waits for an operator choice.

Example: nine cancellations are confirmed, but the tenth order cannot be queried because the authenticated control path remains unavailable. At 30 seconds the runtime warns. At 60 seconds it records the tenth identity as unresolved, persists the incomplete outcome, and exits unsuccessfully. The restarted runtime does not recreate or assume cancellation of that order; it remains frozen until Binance evidence establishes its fills and terminal state.

This process shutdown neither triggers terminal disposal nor closes the grid run. It is distinct from operator stop and global stop-loss; retained inventory and terminal latches survive recovery exactly.

###### Consequences

- Routine shutdown gets bounded time for late evidence and rate-limit-aware queries without being able to hang indefinitely.
- Unfinished cancellation is converted into explicit frozen-recovery work rather than a false clean shutdown.
- Infrastructure restart improves recovery availability but never grants trading authority.
- The external dead-man and critical incident paths can detect failure even when the old process disappears.

###### Declined alternatives

- **30 seconds:** shortens deployments but leaves less time for late fills, rate-limit backoff, authoritative cancellation evidence, and durable reconciliation.
- **120 seconds:** gives the venue more recovery time but delays replacement recovery while the old single-node runtime remains responsible.
- **Unbounded wait:** maximizes the chance of eventual clean reconciliation but allows a failed control path to hang shutdown permanently.

#### Crash, forced termination, and startup

- A crash cannot be assumed to cancel any venue order. Venue orders may execute throughout the outage.
- Every startup loads in `FROZEN` before opening any order-submission capability.
- Verify durable journal integrity and rebuild the exact expected subledger, order obligations, lifecycle, risk triggers, and prior safety posture from admitted evidence.
- Establish fresh public and private continuity, authenticated control-path availability, clock validity, current venue rules/fees, and allocation coverage.
- Query authoritative managed and recent orders, executions/trades, balances, and account state over a window sufficient to cover the outage and all non-terminal command identities.
- Admit missing venue facts, classify every difference, account for late fills and fees, and cancel every surviving effective managed order.
- Reconcile to the accepted invariant suite and recalculate inventory, current/conservative liquidation equity, loss guardrails, terminal boundaries, and range state.
- A terminal latch survives restart and prohibits resume. A material unresolved item keeps the process `FROZEN`.

#### Operator recovery choice

After complete recovery evidence exists, the operator may request either:

- reconciled resume, which revalidates all activation/risk/venue conditions and creates only currently missing valid grid orders; or
- operator stop, which permanently closes the run under the accepted retain-by-default disposition workflow.

The operator decision is canonical evidence. Successful service health, process uptime, WebSocket reconnection, a clean database open, or a completed replay is necessary but never sufficient for trading resume.

Example: Azure restarts the VM while three buys and four sells are live. On restart, the runtime does not recreate seven orders. It starts frozen, rebuilds expected state, queries Binance, admits a buy fill that occurred during the outage, cancels the six surviving orders, reconciles the resulting inventory and fee, and waits for an operator resume or stop decision. Resume later creates only orders valid for the reconciled current state.

#### Consequences

- Routine deployment causes cancellations and requires operator involvement, trading some availability for a substantially simpler and safer single-node recovery model.
- Fills during a crash remain first-class economic facts rather than being discarded because the local process was offline.
- Infrastructure auto-restart supports recovery availability without creating unsafe trade auto-resume.
- A later proven high-availability handover may preserve selected venue orders, but it requires a separate specification and validation increment.

#### Declined alternatives

- **Leave orders active and automatically resume:** maximizes continuity but permits unmonitored fills and re-enables exposure without proving recovered state.
- **Leave orders active, reconcile, then request approval:** safer than auto-resume but materially complicates offline pairing and risk behavior; it is deferred until evidence justifies higher availability.
- **Treat shutdown as operator stop:** deterministic but would permanently close an open-ended run for routine deployment or Azure maintenance.

### Risk-control acceptance matrix and external critical alerting

Selected by the operator on 2026-07-15: every safety rule is incomplete until its trigger, permitted actions, evidence, alert, restart behavior, recovery, and parity are executable acceptance cases. Safety-acceptance failures block promotion.

This section fixes the risk contract. Detailed event/log schemas, Azure services, dashboards, retention periods, alert destinations, escalation schedules, and storage cost remain owned by the observability and deployment specifications.

#### Acceptance case contract

Every risk control declares and verifies:

- authoritative trigger inputs and freshness/continuity requirements;
- immediately below, exactly at, and immediately above every numeric or temporal boundary;
- resulting lifecycle condition, effective safety posture, latch state, and precedence with simultaneous triggers;
- every command class permitted, refused, cancelled, retained, or deferred;
- partial fill, late fill, duplicate delivery, rejection, timeout, and unknown-outcome behavior;
- canonical journal facts, structured diagnostic logs, metrics, health state, alert severity, and incident correlation produced;
- process termination and frozen restart at each material transition point;
- authoritative recovery evidence, invariant suite, reconciliation result, and operator approval required;
- deterministic replay and mode-parity expectations across candle simulation, event replay, paper, venue integration, and live where applicable.

Mandatory fault scenarios include unknown submission/cancellation, identical and conflicting duplicates, public/private gaps, stale decision and valuation inputs, REST/control outage, `429`/`418` pressure, clock skew, partial/late fills, accounting/reconciliation violations, foreign allocation activity, persistence failure, crash during placement/cancellation/disposal, post-only retry exhaustion, IOC partial disposal, exhausted terminal bounds, and every operator safety command.

#### Alert severity

- **Critical:** `FROZEN`; unknown exposure; hard accounting or persistence failure; lost safety/control path; terminal-disposal failure or material residual; failed recovery/rebuild; or any condition requiring immediate deliberate intervention.
- **Warning:** `REDUCE_ONLY`; 80% of a loss guardrail; approaching an evidence/retry/capacity deadline; range exhaustion; repeated bounded refusal; or degraded input that remains within its allowed recovery window.
- **Informational:** expected lifecycle/safety transitions, successful reconciliation, ordinary explained refusal, clean shutdown, completed recovery milestones, and operator actions.

Every material condition creates or updates one durable correlated incident rather than emitting an unbounded alert storm. Repeated-notification destinations and schedules belong to the later observability specification; they cannot weaken the posture, critical classification, external dead-man requirement, occurrence counts, or evidence fixed here.

#### External detection and evidence safety

- At least one monitoring path outside the trading process detects missing heartbeat/health, process death, or inability of the application to emit its own critical alert before real-money activation.
- Domain transitions live in the append-only trading event journal. Diagnostic logs and metrics explain operation but never replace domain evidence or become an alternative balance/order source of truth.
- Correlation connects market input, decision, command, managed order, venue response, fill, accounting batch, reconciliation item, safety transition, operator action, and incident.
- API secrets, signatures, credentials, authentication payloads, and sensitive headers are prohibited from journals, logs, metrics, alerts, and captured incident evidence. Redaction failures block promotion.

#### Promotion evidence

- All mandatory acceptance and fault cases pass in deterministic automation before the 30-day paper qualification period.
- Fault injection is repeated during paper operation without unreconciled orders, duplicated commands, missed admitted fills, unexplained asset differences, unsafe resume, or lost incident evidence.
- The qualifying paper period ends with zero unresolved critical incidents and zero unexplained accounting/order differences. A resolved incident remains part of the evidence and may still invalidate the period under later promotion rules.
- External critical-alert delivery and dead-man detection are deliberately tested, not inferred from configuration.

#### Consequences

- Safety behavior is a verifiable product contract rather than prose or logging conventions.
- Failures during transitions and recovery receive the same rigor as normal order placement.
- External monitoring covers the important case where the trading process is unable to report its own failure.
- Observability implementation choices can evolve without weakening canonical risk evidence.

#### Declined alternatives

- **Automated tests without external alerts:** validates logic but cannot notify the operator when the deployed process is frozen, dead, or unable to reconcile.
- **Logging and manual inspection only:** provides retrospective clues but does not prove transitions, permissions, parity, or timely notification.
- **Normal-path testing before paper:** uses the qualification period to discover fundamental failure semantics rather than validate them.

## Provisional quantitative profile

Quantitative defaults in this section are hard safety ceilings for qualification and first live activation, not investment targets or evidence that a strategy is profitable. Strategy validation may require lower values. It can never raise these ceilings automatically.

### Qualification and first-live capital ceiling

Selected by the operator on 2026-07-15: use `250 USDT` as both the hard deployment live-activation ceiling and the maximum grid capital envelope for the final qualifying paper run and first live run.

- An individual run may allocate less but cannot allocate more.
- Fee reserve and any conservatively valued base or third fee asset are included inside `250 USDT`.
- Research backtests may examine other capital sizes, but promotion evidence must include the actual `250 USDT` scale with current venue filters, rounding, fees, rung quantities, and bootstrap requirements.
- If a venue-valid neutral grid cannot fit within the ceiling, activation is rejected. The system cannot draw more account funds or silently reduce economic obligations to force activation.
- Increasing the ceiling requires a new approved quantitative profile, strategy evidence at that scale, another qualification/promotion decision, and deliberate deployment configuration change.
- The whole Binance balance remains irrelevant except as allocation-coverage evidence.

The selected amount is intended to be large enough for a small multi-rung BTC/USDT neutral spot grid while limiting unproven first-live exposure. That feasibility remains a property of the eventually selected symbol, range, rung count, sizing, fee treatment, and live venue rules—not an assumption guaranteed by this limit.

#### Declined starting ceilings

- **`100 USDT`:** lower exposure, but bootstrap backing, multiple venue-valid rungs, minimum notionals, rounding, and fees may make the qualifying strategy unrealistically constrained.
- **`500 USDT`:** provides more sizing flexibility but doubles unproven initial live exposure without operational evidence.
- **`1,000 USDT`:** comfortable for sizing but unnecessarily large for the first personal live promotion stage.

### Dynamic fee reserve with a `5 USDT` minimum

Selected by the operator on 2026-07-15: reserve at least `5 USDT` quote-equivalent fee coverage inside the `250 USDT` envelope, increasing it when twice the projected native-asset fees for currently approved obligations and one bounded terminal-disposal sequence exceeds that minimum.

The fee reserve is an accounting/authorization classification, not a separate source of money. Coverage is held in the exact fee assets Binance may charge; the `USDT` amount is the conservative approval valuation across those native quantities.

#### Required calculation

Before activation and each exposure-increasing order authorization:

1. Query or validate current authenticated commission rates, discount state, possible fee assets, venue rules, and the valuation paths for non-quote fee assets.
2. Project fees for bootstrap acquisition where still applicable, every effective order obligation under its possible full execution, the candidate order, and one complete bounded terminal-disposal sequence for maximum planned inventory.
3. Use the highest fee treatment that can validly apply when maker/taker status, discount eligibility, or fee asset is not yet certain. A discount counts only when current authoritative configuration and allocated fee-asset coverage prove it usable.
4. Multiply the projected total by two as the fee-uncertainty/continuity buffer.
5. Reserve the greater of that buffered result and `5 USDT` quote-equivalent, expressed as exact required native asset quantities with conservative valuations.

The required reserve reduces principal available to bootstrap and rung obligations. It never increases the grid capital envelope. At the minimum, no more than `245 USDT` of the `250 USDT` ceiling is available for order principal.

#### Runtime behavior

- Actual venue-reported fees post in their native assets and reduce exact reserve coverage or other explicitly available allocated quantities according to the accounting specification.
- Uncommitted realized proceeds may restore required fee coverage, but the non-compounded MVP cannot use a later surplus to enlarge rung principal, maximum planned inventory, or the capital envelope.
- If current or projected native fee coverage falls below the requirement, the condition is a known economic restriction: select `REDUCE_ONLY`, block buys, alert, and retain valid fully backed sells when their own fee treatment remains executable.
- If actual fee asset/rate behavior is uncertain, contradicts authenticated evidence, or creates an unexplained allocation difference, select `FROZEN` under the anomaly policy.
- Activation is rejected if the required native fee assets are unavailable, unallocated, unvalued, or insufficient after considering bootstrap and planned obligations.

Example: twice the projected total fees equals `3.20 USDT`, so the `5 USDT` minimum governs and `245 USDT` remains at most for principal. If the projection rises to `6.40 USDT`, the reserve becomes `6.40 USDT` and maximum principal falls to `243.60 USDT`; the envelope stays `250 USDT`.

#### Consequences

- The small starting envelope retains a meaningful buffer without assuming one static fee rate or asset.
- Bootstrap, normal maker cycles, and aggressive terminal disposal are covered by the same explicit native-asset policy.
- Open-ended lifetime fees need not all be pre-funded at activation; current obligations and terminal capacity remain continuously covered, while realized proceeds may replenish the classification.
- Supporting account-level BNB fee discounts does not permit unallocated BNB use or hide the third asset from accounting.

#### Declined alternatives

- **Fixed `2.50 USDT`:** preserves principal but leaves little uncertainty coverage for bootstrap, repeated obligations, fee changes, and aggressive disposal.
- **Fixed `5 USDT` without recalculation:** simple but cannot respond when actual rates, assets, or obligations require more.
- **No fee reserve:** maximizes initial principal but can authorize a plan without sufficient assets for fees or terminal disposal.

### Backtest-selected rung count with first-live operational ceilings

Selected by the operator on 2026-07-15, superseding the earlier same-day 11-rung recommendation: rung count is a strategy-search parameter selected jointly with symbol, bounds, geometric/arithmetic spacing, activation price, fixed quote size, stop price, fees, slippage, and regime evidence. The risk profile does not preselect a rung count.

The rung count cannot be ignored by calculation or validation. It affects adjacent net cycle margin, bootstrap backing inventory, maximum planned inventory, committed capital, venue rounding/minimums, simultaneous order demand, fee consumption, and reconciliation/rate-limit complexity. It is merely deferred as a choice until backtesting and walk-forward validation have evidence.

The independent risk/operational ceilings are:

- no exposure-increasing buy may exceed `20 USDT` fully quantized principal or its lower strategy-configured size;
- no run or deployment may authorize more than 20 concurrent effective managed grid orders;
- one effective managed order per rung remains mandatory;
- the full exact plan must fit the `250 USDT` capital envelope, dynamic fee reserve, maximum planned inventory, and every current venue rule;
- every adjacent cycle must retain positive net cycle margin under the approved conservative costs;
- final paper qualification and first live activation use the identical backtest-selected rung count, prices, sizing, and quantized obligations.

Pending, partially filled, submission-unknown, cancellation-pending, and cancellation-unknown orders continue to occupy their rung and count toward 20. A possible duplicate beyond the ceiling is a Tier C incident and remains possible exposure until reconciled; the ceiling never makes it disappear.

At every applicable symbol, account, and exchange order limit, preserve safety/account headroom equal to the greater of 10 order slots or 20% of the current authenticated limit. Effective foreign account orders consume shared venue capacity before headroom and grid occupancy are evaluated. Insufficient headroom rejects activation or new exposure.

#### Backtest and promotion consequences

- Research may compare rung counts freely within capital, venue, economic, and operational constraints instead of optimizing around an arbitrary 11-rung assumption.
- Rung count is evaluated together with bounds and spacing; reporting it without those parameters is not meaningful strategy evidence.
- The 20-order ceiling limits first-live operational complexity without implying that 20 rungs are desirable or capital-feasible.
- A validated configuration requiring more than 20 effective orders fails the first-live operational profile or requires a separately approved higher-scale profile and new qualification evidence.

#### Superseded and declined alternatives

- **Fixed 11-rung ceiling:** initially selected as a balanced illustrative profile, then superseded because it prematurely constrained strategy search before bounds, spacing, costs, and regime behavior were validated.
- **No rung or effective-order ceiling:** maximizes research freedom but permits an optimizer to promote excessive live command/reconciliation complexity.
- **Fixed 7/15/21-rung profiles:** each assumes a grid granularity before joint strategy evidence exists; they remain valid research candidates below the independent operational limits, not risk-policy defaults.

### First-live loss thresholds

Selected by the operator on 2026-07-15: apply the following conservative-loss profile to the final qualifying paper run and first live run, using the smaller permitted loss produced by its percentage and absolute limits:

- daily-loss guardrail: 2% of the daily baseline or `5 USDT`, whichever permits less loss, selecting `REDUCE_ONLY`;
- run-drawdown guardrail: 8% of the run high-water mark or `20 USDT`, whichever permits less loss, selecting `REDUCE_ONLY`;
- terminal equity loss: 12% of initial flow-adjusted conservative liquidation equity or `30 USDT`, whichever permits less loss, irreversibly triggering the global stop-loss;
- warning at 80% of each currently effective threshold under the accepted alert policy.

At a full `250 USDT` baseline, the percentage and absolute values align. At a lower run allocation, the percentages become more protective: a `200 USDT` run has `4 USDT` daily, `16 USDT` drawdown, and `24 USDT` terminal-loss thresholds.

These limits are fixed ex ante as personal/operational risk acceptance criteria. Backtesting, walk-forward analysis, replay, and paper qualification determine whether a proposed strategy can operate positively and robustly inside them. Validation cannot automatically loosen the limits merely because a historical configuration loses more; a strategy that repeatedly reaches them fails this first-live profile or requires a separately reviewed profile before new evidence is collected.

#### Consequences

- Strategy research optimizes within a predetermined risk budget rather than fitting the budget to historical losses.
- Daily deterioration and high-water drawdown stop new exposure well before the terminal capital boundary where configured behavior is orderly.
- Conservative liquidation costs and unrealized inventory movement remain included through the accepted equity definition.
- Threshold hits, near misses, regime distribution, time spent `REDUCE_ONLY`, recovery assumptions, and terminal outcomes are required backtest/paper evidence, not only final profit.

#### Declined profiles

- **1% daily, 5% drawdown, 8% terminal:** more protective but likely to suppress meaningful neutral-grid behavior during ordinary volatility before sufficient evidence exists.
- **3% daily, 12% drawdown, 18% terminal:** permits more fluctuation but increases unproven first-live loss exposure.
- **Backtest-derived limits without fixed defaults:** risks selecting thresholds that accommodate historical losses instead of enforcing an independent capital boundary.

### First-live post-only placement retry bounds

Selected by the operator on 2026-07-15: an ordinary rung placement that receives a confirmed Binance post-only-would-take rejection may use one bounded post-only placement sequence. The sequence contains at most 3 submission attempts in total, including the original attempt, and expires 10 domain seconds after the first submission is authorized.

#### Retry authorization

- Every attempt remains Binance `LIMIT_MAKER`; no retry may use ordinary `LIMIT`, `MARKET`, IOC, or another taker-capable fallback.
- A confirmed rejected attempt has no fill. Before another attempt, the runtime reconciles its managed order identity, refreshes fresh best bid/ask and applicable venue rules, and proves that no effective or outcome-unknown order occupies the rung.
- Each attempt receives its own generation-specific managed command identity while remaining linked to the same rung and cumulative order obligation.
- After the first confirmed rejection, the earliest second attempt is authorized by a 250-millisecond domain timer. After a second confirmed rejection, the earliest third attempt is authorized by a 1-second domain timer.
- The retry price is the nearest venue-valid, demonstrably non-marketable price that preserves or improves the configured rung economics: a buy may move downward but never upward from its rung; a sell may move upward but never downward.
- Absolute displacement from the configured rung cannot exceed the smaller of 0.25% of the configured rung price and 25% of the gap to the next configured rung in the displacement direction.
- Displacement can never leave the configured grid bounds, cross or equal the neighboring rung, violate one-order-per-rung occupancy, reduce the approved net cycle margin, or create exposure beyond an outer rung. An outer buy at the lower bound and an outer sell at the upper bound therefore have no outward displacement allowance.
- All authorization evidence must also meet the accepted 5-second executable-market freshness limit, venue-rule validity, order/inventory/capital limits, accounting invariants, and effective safety posture.

Example: a buy rung is `90` and the next lower rung is `89.10`, so the rung gap is `0.90`. Twenty-five percent of the gap is `0.225`, while 0.25% of the rung price is also `0.225`; the lowest permitted retry price is therefore `89.775` before venue rounding. If fresh maker placement would require `89.70`, the retry is not authorized. If `90` were the configured lower outer rung, no retry below `90` would be authorized at all.

#### Exhaustion and uncertainty

- The sequence exhausts when the third total submission is confirmed rejected, 10 domain seconds expire, the displacement ceiling is insufficient, or another authorization constraint prevents safe retry within those bounds.
- Exhaustion leaves the rung unplaced, latches the associated known economic restriction, selects `REDUCE_ONLY`, journals the complete attempts and evidence, and alerts the operator. It never causes a taker fallback.
- A submission timeout, `5XX`, disconnect, or any other outcome-unknown result is not a retryable rejection: it immediately selects `FROZEN`, and no further attempt is permitted until authoritative reconciliation proves the outcome.
- A non-marketability rejection, such as an invalid filter, insufficient allocated balance, or rate-limit/control failure, follows its own evidence-based anomaly classification and cannot be relabelled as a post-only retry.
- Returning to `NORMAL` after exhaustion requires repaired conditions, full reconciliation, passing invariants and limits, a fresh placement plan, and explicit operator approval under the accepted recovery policy.

Backtest, event replay, paper, and venue-integration acceptance cases must cover first-attempt acceptance, one and two confirmed maker rejections followed by acceptance, displacement-edge rounding, outer-rung refusal, ten-second expiry, third-attempt exhaustion, unknown outcome, and proof that no taker-capable command is emitted. Where candle data cannot prove the contemporaneous book needed for a retry, the promotion simulation must use the accepted conservative ambiguity policy rather than inventing successful maker placement.

#### Consequences

- Brief book movement gets a small deterministic opportunity to recover without allowing the engine to chase the market.
- The displacement bound scales with both price and grid geometry and preserves separation from the neighboring rung.
- A retry failure is an economic placement restriction rather than state uncertainty only while every rejected outcome and current obligation remains authoritative.
- Domain timers and immutable attempt identities make the behavior reproducible across replay, paper, and live modes.

#### Declined alternatives

- **Exact rung only:** preserves literal ladder prices but can repeatedly reject after the market crosses the rung even when a small economically favorable maker adjustment is safe.
- **Five attempts, 30 seconds, and 50% of the adjacent gap:** improves placement probability but permits more command churn and materially weakens the relationship between configured and placed rung prices.
- **No automatic retry:** is operationally simple but turns one transient confirmed maker rejection into an immediate grid-wide restriction.

### First-live freshness, continuity, and recovery deadlines

Selected by the operator on 2026-07-15: use the following balanced provisional deadlines in the qualifying paper run and first live run:

- executable best bid/ask, order-book depth, or material liquidation valuation older than 5 seconds selects `FROZEN`;
- strategy-decision market input older than 15 seconds selects `REDUCE_ONLY` only while executable valuation and all account/control evidence remain healthy;
- private user-stream disconnect or unproven continuity gap selects `FROZEN` immediately;
- perform full authenticated managed/recent-order, fill/trade, balance, allocation-coverage, and accounting reconciliation at startup and at least every 60 seconds while trading;
- authenticated REST safety/control path unavailable for 10 seconds selects `FROZEN`;
- any safety-critical submission/cancellation whose outcome becomes unknown selects `FROZEN` immediately without waiting for the control-path deadline;
- measured venue/runtime clock offset above 500 milliseconds, or any authenticated timestamp-window rejection, selects `FROZEN`;
- begin planned WebSocket rotation no later than connection age 23 hours, prove overlap and continuity, then retire the old connection;
- missing external process heartbeat for 2 minutes produces a critical dead-man alert.

All ages use recorded event/received times and domain timers under the accepted continuity model. The 60-second reconciliation cadence does not make a snapshot authoritative indefinitely; a contradictory or unknown event freezes immediately. Conversely, quiet private-stream traffic alone does not imply staleness when continuity and authenticated reconciliation remain proven.

Paper evidence may tighten these deadlines without increasing risk. Loosening any deadline requires documented latency/disconnect distributions, fault-test evidence, risk review, a new quantitative profile version, and explicit approval before a new qualification period.

#### Consequences

- The deadlines are cheap timers and periodic queries suitable for the minimal Azure node; they do not require redundant infrastructure.
- Public strategy degradation can preserve safe backed sells, while uncertainty in executable valuation or real account state fails closed.
- Planned stream rotation is distinguished from an unproven disconnect.
- A process that cannot emit its own alert is detected by an external two-minute liveness bound.

#### Declined profiles

- **2-second pricing, 5-second strategy inputs, 30-second reconciliation:** more responsive but likely to cause excessive transient freezes and REST usage before latency evidence exists.
- **15-second pricing, 60-second strategy inputs, 5-minute reconciliation:** more tolerant but leaves materially longer stale-price and missed-account-event exposure.
- **No provisional deadlines until paper measurement:** makes stale/gap behavior nondeterministic during the very paper period intended to validate it.

## Resolution

The operator accepted this specification on 2026-07-15 as the canonical risk and safety contract for the qualifying paper MVP and first-live profile. It fixes the domain semantics and provisional quantitative starting values required by downstream validation, observability, runtime, operator-workflow, Azure, security, and verification specifications. It does not authorize implementation, promotion, activation, or real-money trading by itself.

No foundation-level operator decisions remain in this specification. Detailed journal/log schemas, alert delivery and repetition, dashboards, retention, hosting termination allowance, and promoted-live increases remain owned by their downstream Wayfinder tickets and cannot weaken the controls accepted here.
