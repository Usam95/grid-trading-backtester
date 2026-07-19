# Trading Engine

The canonical language for grid behavior, assets, inventory, and consistent decisions across simulation and online operation.

## Language

**Spot inventory trading**:
Trading where quote currency buys base-asset inventory and sells are limited to inventory already owned.
_Avoid_: Long-only trading

**Base asset**:
The asset being bought and sold in a trading pair; BTC is the base asset in BTC/USDT.
_Avoid_: Coin, stock

**Quote asset**:
The asset used to price and pay for the base asset; USDT is the quote asset in BTC/USDT.
_Avoid_: Cash, currency

**Base holdings**:
Base-asset units present in the exchange account, whether or not they belong to a grid.
_Avoid_: Position

**Grid inventory**:
Base holdings explicitly owned and accounted for by one grid.
_Avoid_: Base holdings, position

**Backing inventory**:
The portion of grid inventory reserved to satisfy the full quantities of open sell intents.
_Avoid_: Available inventory

**Maximum planned inventory**:
The greatest grid inventory permitted by the approved grid plan, reached when bootstrap inventory exists and every funded buy rung has filled without offsetting sells.
_Avoid_: Inventory cap

**Committed inventory**:
Current grid inventory plus the maximum additional base asset that all non-terminal or outcome-unknown exposure-increasing buy obligations could still acquire.
_Avoid_: Current inventory, open-order quantity

**Base-holdings allocation**:
The explicit assignment of existing base holdings to a grid as its opening grid inventory.
_Avoid_: Import inventory, adopt balance

**Grid allocation**:
The base and quote assets exclusively reserved for one grid and unavailable to manual or other algorithmic trading while its run is open.
_Avoid_: Account balance

**Grid capital envelope**:
The immutable per-run combination of exact native-asset allocations and their maximum approved quote-equivalent capital inflow, including fee reserve.
_Avoid_: Account balance, available capital

**Live-activation ceiling**:
An independently controlled quote-equivalent maximum above which a grid allocation cannot be authorized for real trading, even when its run configuration or account coverage is larger.
_Avoid_: Account equity, grid capital envelope

**Foreign activity**:
Any order, trade, deposit, withdrawal, or balance change affecting grid-allocated assets that was not caused by the grid.
_Avoid_: Manual trade

**Flat**:
A grid state with zero grid inventory; it does not mean the exchange account has no base holdings.

**Quote-only start**:
Activation with allocated quote asset and zero grid inventory, so the grid initially places only buy rungs.
_Avoid_: Flat start

**Bootstrap acquisition**:
An explicit opening purchase sized to create the backing inventory required by all initial sell rungs, including venue rounding and the configured fee reserve.
_Avoid_: Bootstrap, seed conversion

**Statistical bootstrap**:
A resampling method that repeatedly recombines observed results to estimate statistical uncertainty; it is unrelated to acquiring the grid's opening inventory.
_Avoid_: Bootstrap acquisition, grid activation

**Block bootstrap**:
A statistical bootstrap that resamples contiguous observation blocks to retain some serial dependence, but does not automatically reproduce path-dependent grid state.
_Avoid_: IID trade bootstrap, bootstrap acquisition

**Bootstrapping**:
The pre-active grid state in which bootstrap acquisition is in progress and no rung ladder may be placed until required backing inventory is confirmed.
_Avoid_: Activating

**Acquisition fee**:
The exchange fee charged on a bootstrap acquisition.
_Avoid_: Bootstrap fee

**Fee asset**:
The asset in which the venue actually charges a fee for a fill; it may be base, quote, or a third asset.

**Net base received**:
The base quantity credited to grid inventory after any fee charged in the base asset.
_Avoid_: Filled base quantity

**Fee reserve**:
Grid capital held back to pay anticipated exchange fees rather than fund order principal.

**Fee coverage requirement**:
The conservatively valued exact native-asset quantities required to cover projected fees for approved obligations and bounded terminal disposal.
_Avoid_: Fixed fee estimate, account BNB balance

**Venue rounding**:
Adjustment of price and quantity to the increments accepted by the trading venue.
_Avoid_: Exchange rounding

**Slippage**:
The difference between the expected execution price and the actual execution price.

**Synthetic conversion**:
A simulated exchange of quote asset for base asset without an executable order; permitted in backtesting only when modeled as the equivalent explicit fill and never presented as a live action.
_Avoid_: Bootstrap acquisition

**Buy rung**:
A grid level carrying the intent to buy base asset at its configured price.
_Avoid_: Buy level

**Rung count**:
The total number of configured grid prices, including the lower and upper bounds.
_Avoid_: Interval count, level count

**Strategy-search parameter**:
A strategy choice selected through backtest, walk-forward, replay, and paper evidence within independently fixed risk and operational ceilings.
_Avoid_: Risk limit, deployment ceiling

**Derived grid value**:
A configuration or obligation value computed deterministically from strategy-search parameters, activation evidence, immutable semantics, venue rules, allocation, and risk controls.
_Avoid_: Search parameter, optimizer choice

**Sell rung**:
A grid level carrying the intent to sell grid inventory at its configured price.
_Avoid_: Sell level

**Partial fill**:
An execution that satisfies only part of an order's requested quantity while immediately transferring ownership and affecting accounting.

**Late fill**:
A venue-confirmed execution received while or after cancellation is being processed, which still changes assets and must be included in final grid state.
_Avoid_: Unexpected fill

**Cumulative filled quantity**:
The total executed quantity of an order across all of its partial fills.
_Avoid_: Filled amount

**Paired order**:
The opposite-side order associated with acquired or sold rung quantity: a sell above a filled buy or a buy below a filled sell.
_Avoid_: Counter-order

**Paired rung sell**:
The normal inventory-reducing order one rung above a filled buy; it realizes one grid cycle without ending the run.
_Avoid_: Global take-profit

**Net cycle margin**:
The expected quote profit of an adjacent buy/sell cycle after fees, conservative execution allowance, venue rounding, and the approved safety margin.
_Avoid_: Grid spread

**Post-only maker order**:
A limit order the venue accepts only if it rests without executing immediately; a marketable order is rejected rather than charged as taker liquidity.
_Avoid_: Limit order

**Aggressive order**:
An order used when prompt execution is more important than maker status, such as bootstrap acquisition or stop-loss liquidation.
_Avoid_: Market order

**Pending paired quantity**:
Filled quantity owned by a rung that cannot yet form a venue-valid paired order and must accumulate until it becomes tradeable.
_Avoid_: Dust

**Outer rung**:
The lowest or highest rung in the configured grid range.
_Avoid_: Boundary order

**Outer-rung cycle**:
A repeated in-range pair where the lowest rung remains buy-only, the highest rung remains sell-only, and the opposite order is placed one rung inward.
_Avoid_: Boundary cycle

**Activation rung**:
A configured rung equal to the validated activation price; it is initially inactive and gains an order only through later pairing.
_Avoid_: Center rung

**Rung occupancy**:
The single managed-order slot of a rung, containing at most one cumulative buy or sell order at a time.
_Avoid_: Order list

**Exposure beyond the outer rungs**:
Additional grid inventory or order commitment created at prices outside the configured range.
_Avoid_: Out-of-range price movement

**Recovery-side order**:
An existing in-range order that reduces a range-exhausted condition if price returns: sells after a fall below the range and buys after a rise above it.
_Avoid_: Recovery order

**Retained inventory**:
Grid inventory held through a pause, stop, or range-exhausted condition rather than sold automatically.
_Avoid_: Stranded inventory

**Retained holding**:
Base asset remaining after a grid run ends without liquidation, preserving provenance but carrying no active grid order obligations.
_Avoid_: Grid inventory

**Sizing policy**:
The rule that determines the intended capital or base quantity assigned to a rung.
_Avoid_: Sizing mode, all sizing policies

**Fixed quote sizing**:
A sizing policy that assigns approximately the same quote value to every rung, causing base quantity to vary with price.

**Buy-principal ceiling**:
The maximum quote-asset principal an exposure-increasing buy may commit under its approved rung sizing.
_Avoid_: Sell notional cap, available quote

**Committed capital**:
Grid assets reserved to back approved bootstrap inventory and open or replaceable rung obligations.
_Avoid_: Invested capital

**Uncommitted quote**:
Quote asset owned by the grid but not reserved for any approved order obligation, including accumulated net cycle profit.
_Avoid_: Free cash, available balance

**Compounding sizing**:
A sizing policy that deliberately increases future rung commitments using accumulated grid profit.
_Avoid_: Reinvest profits

**Current grid equity**:
The reproducibly marked quote value of all assets explicitly owned by a grid allocation. Recorded fee postings are already reflected in owned quantities and are not subtracted again.
_Avoid_: Account equity, balance

**Neutral spot grid**:
A spot grid bootstrapped with grid inventory so it can place buy rungs below and sell rungs above the activation price; it still has long price exposure.
_Avoid_: Market-neutral grid

**Short exposure**:
Exposure that gains when the base-asset price falls and loses when it rises; it is not available through unborrowed spot inventory.
_Avoid_: Sell exposure

**Borrowing**:
Obtaining assets from a venue or lender that must later be repaid, enabling sales beyond owned inventory.

**Margin trading**:
Trading backed by borrowed assets or collateral, with venue-defined repayment and risk constraints.
_Avoid_: Spot inventory trading

**Static grid**:
A grid whose price bounds and rungs do not adapt automatically during a run; it may use arithmetic or geometric spacing.
_Avoid_: Fixed strategy

**Strategy configuration version**:
An immutable, identifiable set of strategy parameters and semantics used to generate evidence and govern one or more approved runs.
_Avoid_: Settings, config

**Run**:
One continuous lifecycle governed by exactly one strategy configuration version, from activation attempt through permanent closure.
_Avoid_: Backtest, session

**Terminal condition**:
An approved event that permanently closes a run, such as operator stop or global stop-loss.
_Avoid_: Pause, range exhaustion

**Arithmetic spacing**:
Grid spacing with equal absolute price distance between adjacent rungs.

**Geometric spacing**:
Grid spacing with equal percentage distance between adjacent rungs; it is the default static-grid spacing.

**Range-exhausted**:
An active static-grid state in which price is outside the configured range and the grid creates no exposure beyond its outer rungs while retaining valid recovery-side orders.
_Avoid_: Out of range, stopped

**Exposure-reducing pause**:
An operator-requested state that cancels and blocks buy orders while retaining valid sell orders that reduce grid inventory.
_Avoid_: Pause, freeze

**Reconciled resume**:
An explicit return from pause after venue orders, fills, balances, grid inventory, price state, venue rules, and risk limits have been revalidated.
_Avoid_: Resume

**Operator stop**:
A deliberate, permanent end to a grid run that cancels and reconciles all managed orders before the operator's selected inventory disposition.
_Avoid_: Pause, process shutdown

**Emergency stop**:
A safety transition that blocks new commands, cancels all managed orders, reconciles venue state, and retains inventory until authoritative state and deliberate next action are available.
_Avoid_: Operator stop, liquidation

**Global stop-loss**:
An approved adverse threshold that cancels and reconciles all grid orders, liquidates remaining grid inventory, and permanently closes the run when triggered.
_Avoid_: Emergency stop, lower bound

**Terminal loss boundary**:
The immutable combination of an exact market-price floor and a fixed conservative-liquidation-equity floor, either of which irreversibly triggers the global stop-loss.
_Avoid_: Loss guardrail, lower grid bound

**Stop-price safety buffer**:
The required conservative-equity margin between modeled maximum-inventory disposal at the exact stop price and the terminal equity floor.
_Avoid_: Extra capital, stop-loss allowance

**Global take-profit**:
An approved favorable threshold that permanently closes the entire grid run; it is distinct from ordinary paired rung sells.
_Avoid_: Paired rung sell

**Strategy decision core**:
The deterministic domain component that consumes canonical market and account inputs and emits canonical order intents.
_Avoid_: Backtest engine

**Candle simulation**:
A fast historical simulation using OHLCV bars and explicit conservative assumptions where intrabar event order is unknowable.

**Event replay**:
A higher-fidelity validation mode that feeds recorded market and account events through the strategy decision core.

**Live parity**:
The guarantee that equivalent canonical inputs and state lead the strategy decision core to equivalent order intents across backtest, replay, paper, and live modes.
_Avoid_: Identical fills

**Accounting specification**:
The authoritative definitions and invariants governing grid assets, fees, fills, inventory, realized results, and equity.
_Avoid_: Accounting

**Reconciliation specification**:
The authoritative rules for comparing grid state with venue state and classifying or resolving every difference.
_Avoid_: Reconciliation logic

**Grid subledger**:
The per-asset record of expected quantities owned, available, reserved, received, delivered, and paid as fees by one grid allocation, derived from its canonical events.
_Avoid_: Account balance, PnL ledger

**Asset posting**:
An explained increase, decrease, or classification change in one native asset quantity caused by canonical evidence.
_Avoid_: Balance correction

**Asset conservation**:
The invariant that every change in a grid's native asset quantities is fully explained by canonical asset postings.
_Avoid_: Balance matching

**Atomic accounting batch**:
The complete indivisible set of asset postings and classification changes caused by one canonical event; either all of it becomes grid state or none of it does.
_Avoid_: Ledger update

**Hard accounting violation**:
A failed accounting invariant that makes the proposed grid state unsafe or internally contradictory and therefore prohibits new exposure.
_Avoid_: Warning, reconciliation difference

**Pending reconciliation difference**:
A specific expected-versus-observed difference temporarily awaiting identified in-flight evidence under a deadline.
_Avoid_: Tolerance, warning

**Valuation unavailable**:
A state in which an owned asset lacks a sufficiently current deterministic quote valuation while its native quantity may remain valid.
_Avoid_: Zero value, accounting loss

**Reservation**:
Grid-owned asset quantity committed to an approved order obligation and unavailable to other obligations without changing grid ownership.
_Avoid_: Expense, exchange balance

**Inventory lot**:
An identifiable quantity of grid inventory sharing acquisition and fee provenance that may be split while retaining that provenance.
_Avoid_: Position

**Paired-lot provenance**:
The attribution of a paired rung sell to the inventory lot acquired by its associated buy quantity.
_Avoid_: FIFO cycle matching

**Terminal disposal**:
The sale of remaining grid inventory to close a run, accounted separately from ordinary paired grid cycles.
_Avoid_: Paired rung sell

**Terminal-disposal wave**:
One reconciled sequence of aggressive child sells used to dispose of confirmed grid inventory after a terminal condition, including any later quantity created by late fills.
_Avoid_: Paired rung sell, sell ladder

**Immediate-or-cancel order**:
An aggressive limit order that executes immediately only at prices within its limit and makes any unfilled remainder terminal instead of resting.
_Avoid_: Market order, post-only maker order

**Non-disposable residual**:
Exact retained grid inventory that current venue quantity, notional, or rounding rules prevent from being sold after all material terminal inventory is disposed.
_Avoid_: Zero inventory, discarded dust

**Source-exact decimal**:
An asset quantity or price preserved exactly from its authoritative decimal representation without conversion through binary floating point.
_Avoid_: Float, approximate value

**Rounding boundary**:
A point where a value is deliberately quantized for a venue-valid order or presentation, without changing the source-exact accounting evidence.
_Avoid_: General rounding

**Rounding residual**:
Grid-owned asset quantity excluded by venue quantization that remains explicitly accounted for rather than being discarded.
_Avoid_: Rounding error, dust

**Realized cycle result**:
The quote-valued economic result of a completed paired grid cycle using its paired-lot acquisition cost, actual proceeds, and attributable fees exactly once.
_Avoid_: Sell proceeds, closed-trade profit

**Unrealized result**:
The quote-valued economic change of remaining grid inventory relative to its attributed acquisition cost and fees at a stated valuation observation.
_Avoid_: Paper profit

**Conservative liquidation equity**:
Current grid equity reduced by the estimated fees, spread, slippage, and conversion costs of immediately disposing of all non-quote grid assets.
_Avoid_: Current grid equity, cash balance

**Valuation observation**:
The price evidence, source, time, conversion path, and age used to express a native asset quantity in the grid's quote asset.
_Avoid_: Current price

**Flow-adjusted total result**:
The change in grid equity after removing the effect of allocations, deallocations, and other approved external capital flows.
_Avoid_: Equity change

**Run high-water mark**:
The greatest valid flow-adjusted conservative liquidation equity observed since the grid allocation was admitted to a run.
_Avoid_: Starting balance

**Run drawdown**:
The decline of flow-adjusted conservative liquidation equity from the run high-water mark, expressed as an exact quote amount and ratio.
_Avoid_: Realized loss

**Risk day**:
The UTC interval from one midnight up to but excluding the next, used to establish one deterministic daily-loss baseline.
_Avoid_: Calendar day, rolling 24 hours

**Daily loss**:
The decline of flow-adjusted conservative liquidation equity from the risk day's fixed baseline, expressed as an exact quote amount and ratio.
_Avoid_: Realized daily profit and loss

**Loss guardrail**:
A latched economic boundary that removes permission to increase exposure without itself requiring terminal disposal of retained inventory.
_Avoid_: Global stop-loss, maximum final loss
