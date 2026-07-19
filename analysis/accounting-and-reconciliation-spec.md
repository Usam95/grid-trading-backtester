# Accounting and reconciliation specification

Status: accepted accounting and reconciliation specification  
Wayfinder ticket: [Specify accounting invariants and reconciliation](../.scratch/comprehensive-grid-trading-system/issues/04-specify-accounting-invariants-and-reconciliation.md)

## Decision-record policy

At the operator's request, every choice in this specification retains the recommendation, selected behavior, examples and consequences provided during review, plus the declined alternatives and why they were rejected. A later reader must be able to reconstruct the trade-off without relying on conversation history.

## Selected accounting foundation

Selected by the operator on 2026-07-14: use one exact, multi-asset grid subledger derived from the canonical trading event journal. Cost lots, cycle results, equity, and reconciliation views are projections of the same asset postings; none is an independent source of balances.

The subledger is scoped to one grid allocation, not the entire Binance account and not tax or company accounting. It records each asset in its native unit using canonical exact decimals. Quote valuation is a derived view and never replaces native quantities.

### Required dimensions

For every relevant asset, the subledger distinguishes:

- grid-owned quantity;
- available and reserved quantity;
- gross trade quantity and net quantity received or delivered;
- fee quantity in the venue-reported fee asset;
- acquisition/cycle provenance and pending paired quantity;
- retained holdings after a run closes;
- foreign or unexplained changes awaiting reconciliation.

A reservation changes availability but not ownership or total asset quantity. Venue-reported free/locked balances are observations used during reconciliation; they are not silently copied into grid ownership.

### Posting example

For a bootstrap purchase of `0.010 BTC` at `60,000 USDT/BTC` with a `0.00001 BTC` fee:

- decrease grid-owned quote by exactly `600 USDT`;
- increase gross grid-owned base by `0.010 BTC`;
- record fee expense of `0.00001 BTC`;
- increase net grid inventory by `0.00999 BTC`.

If the fee is charged in BNB instead, base increases by the full `0.010 BTC`, quote still decreases by `600 USDT`, and allocated BNB decreases by the reported BNB fee. Any quote value attached to that fee is a timestamped valuation projection, not an asset posting.

### Declined accounting foundations

- **Enhanced cash-plus-FIFO ledger:** less initial change, but reservations, third-asset fees, allocation isolation, native-asset conservation, and venue reconciliation remain awkward and vulnerable to parallel sources of truth.
- **Binance balance snapshots as the accounting model:** simple to display, but whole-account balances mix grid and foreign activity, erase causal explanation, and can hide differences through silent replacement. Binance observations remain authoritative venue evidence, not the grid's historical subledger.

### Foundation invariants

- Every change in grid-owned quantity is explained by allocation, deallocation, fill, fee, transfer, approved adjustment, or retained-holding disposition evidence.
- One event cannot affect the subledger twice; deduplication uses canonical and venue identities.
- Total quantity for an asset equals its availability classifications plus any explicitly defined in-transit classification.
- Reservations never create or destroy assets and cannot exceed grid-owned quantity.
- Spot grid inventory cannot become negative, including after fees, late fills, or repair processing.
- Native asset quantities and asset postings never use binary floating-point arithmetic.
- Rebuilding from the same journal and immutable context produces the exact same subledger and projections.
- Exchange observations and expected subledger state remain separately visible until every difference is classified; reconciliation never silently overwrites history.

## Inventory-lot attribution

Selected by the operator on 2026-07-14: canonical grid-cycle results use paired-lot provenance. FIFO remains a deterministic rule for terminal disposal and may be exposed as a secondary comparison, but it does not redefine ordinary grid cycles.

- Every net base quantity acquired by a buy fill creates one or more identifiable lot slices carrying fill, order, rung, price, fee, and event provenance.
- A paired rung sell consumes the exact available lot slices attributed to its originating buy quantity. Partial fills split quantities and acquisition fees proportionally without losing the original identities.
- Bootstrap fill lots are assigned to initial sell obligations deterministically: process bootstrap fills in canonical event order and initial sell rungs from the lowest sell price upward. Any unassigned remainder retains bootstrap provenance.
- A global stop-loss or other approved terminal liquidation consumes remaining lots FIFO by acquisition event order. Its realized result is labelled terminal disposal and is not counted as ordinary grid-cycle profit.
- Operator stop with retained holdings preserves every remaining lot and its cost/fee provenance through the retained-holding transition.
- A sell cannot consume more attributed grid inventory than exists. Missing or contradictory provenance is an accounting invariant failure, not permission to choose another lot silently.

Example: if bootstrap inventory was acquired at `100`, a later buy rung acquires at `90`, and that rung's paired sell executes at `95`, the canonical cycle is the `90 → 95` lot. Pure FIFO would incorrectly attribute the sell to bootstrap inventory and obscure whether the paired rung was economically positive.

Lot attribution changes the timing and explanation of realized versus unrealized result but never native asset totals or current grid equity. When all inventory is disposed, total net result must be independent of the attribution view.

### Declined lot-attribution alternatives

- **FIFO for every sell:** deterministic and partly implemented today, but it can match a paired sell against unrelated bootstrap or older inventory and therefore misstate whether the actual rung cycle was profitable.
- **Weighted-average cost:** smooths overall results but removes acquisition, fill, and rung provenance needed for cycle validation, partial-fill diagnosis, retained holdings, and repair audit.

## Decimal precision, venue rounding, and residuals

Selected by the operator on 2026-07-14: use source-exact decimal quantities and round only at explicit venue or presentation boundaries. Persisted accounting values never pass through binary floating point.

- Parse and preserve venue-reported prices, executed quantities, balances, cumulative quantities, and fee quantities as exact decimals. Accounting does not re-quantize authoritative evidence after receipt.
- Store the time-versioned venue-rule identity with every quantized order. Normal post-only buy prices round downward to the valid tick and sell prices round upward, preserving no-worse-than-rung economics. Order quantities round downward to the valid step so reservations and sells cannot be overcommitted.
- Validate minimum quantity, maximum quantity, minimum notional, maximum notional, and other applicable filters only after price and quantity quantization. A value that fails remains unsubmitted rather than being rounded in a risk-increasing direction.
- Exact arithmetic may produce more decimal places than the venue accepts; this is allowed inside calculations. Only an executable order boundary applies venue quantization.
- When dividing a lot, fee, cost, or proceeds among partial slices, allocate deterministic intermediate slices at the original posting's canonical decimal scale and assign the exact remaining amount to the final slice. The slices must sum exactly to the original posting.
- Quantity removed by order quantization remains grid-owned and available or pending; it is not an expense. A residual that cannot yet form a venue-valid paired order remains pending paired quantity and may accumulate.
- At terminal closure, an untradeable base residual becomes a retained holding with its provenance intact unless an explicit supported conversion/disposition is later approved.
- UI and export formatting may round copies for display, but stored values, hashes, equality checks, and reconciliation use canonical exact decimals.
- Reconciliation compares normalized exact native quantities. There is no generic epsilon that makes a nonzero difference disappear; known source precision and in-flight events are modeled explicitly.

Example: with an intended `0.00123456 BTC` quantity and a `0.00001 BTC` step, the submitted quantity is `0.00123 BTC`. The `0.00000456 BTC` remainder stays recorded and owned; it may accumulate into a later venue-valid order or become a retained holding.

### Declined precision alternatives

- **One fixed scale per asset type:** rules such as eight base decimals and two quote decimals are simple but conflict with symbol-specific and time-varying tick, step, notional, and fee precision.
- **Binary floating point with tolerances:** convenient and compatible with the current code, but permits nonzero differences to be dismissed as rounding noise and cannot meet exact replay or reconciliation requirements.

## Cost, result, fee, and equity valuation

Selected by the operator on 2026-07-14: native-asset postings remain authoritative and produce two reproducible quote-valued views—current grid equity and conservative liquidation equity. Valuation never mutates native quantities.

### Cost basis and realized cycle result

- A lot's acquisition cost is the actual quote outflow attributable to its net acquired base quantity, including quote-denominated acquisition fees. A base-denominated acquisition fee reduces net acquired quantity, so the full quote outflow is carried by the smaller net lot rather than subtracting the fee twice.
- A paired sell's realized cycle result is its actual quote proceeds attributable to the paired lot minus that lot's acquisition cost and all economically attributable fees, each included exactly once.
- Quote fees enter their actual quote cash flow. Base fees enter through the quantity and lot cost they consume. Third-asset fees retain their native posting and use a separately recorded quote valuation at the fee event for performance attribution.
- Fee reports always retain native asset and quantity alongside any quote valuation. If a required conversion price is unavailable, the quote-valued result is explicitly incomplete rather than treating the fee as zero.
- Terminal-disposal results, foreign-activity results, and ordinary grid-cycle results remain separate categories even though all contribute to total result.

### Current grid equity

Current grid equity is the quote value of every asset still owned by the grid allocation: quote holdings plus marked base inventory and marked allocated fee assets. Available, reserved, pending, and retained classifications are all included because reservation does not change ownership. Fee postings have already reduced owned assets and are not subtracted again.

The canonical mark is:

- candle close for candle backtests;
- the synchronized best bid for owned non-quote assets in event replay, paper, and live operation, because liquidation would sell into the bid;
- a recorded, deterministic conversion path to the grid quote asset for a third asset such as BNB.

Every valuation records price, source, event time, received time where applicable, conversion path, and age. A missing or stale required mark makes the affected quote valuation unavailable and triggers the applicable risk/observability rule; the asset is never silently valued at zero and an old price is never presented as current without its age.

### Conservative liquidation equity

Conservative liquidation equity starts from current grid equity and subtracts the configured estimated taker fees, spread, adverse slippage, and required conversion costs for disposing of all non-quote grid assets. Risk and promotion rules use this view; research and operator views show both values and their difference.

Example: `400 USDT + 0.010 BTC` at a synchronized best bid of `60,000 USDT/BTC` gives current grid equity of `1,000 USDT`. If modeled immediate-disposal costs are `1.20 USDT`, conservative liquidation equity is `998.80 USDT`.

### Flow-adjusted total and unrealized result

- Trading performance excludes capital movements. Flow-adjusted total result is the change in current grid equity after removing the effect of allocations, deallocations, and other approved external flows.
- Unrealized result is the marked economic change of remaining attributed lots after their acquisition costs and attributable fees.
- Under complete valuation, flow-adjusted total result must equal realized cycle results plus terminal/other realized results plus unrealized result. The same identity must hold using conservative liquidation equity when its additional modeled disposal costs are shown as a separate adjustment.

### Declined valuation alternatives

- **One equity value using the latest trade:** easy to calculate, but the last trade may be stale or above the executable bid, hides immediate-disposal costs, and gives risk controls an optimistic view.
- **Cost basis without market valuation:** preserves acquisition history but cannot measure current drawdown, unrealized result, capital exposure, stop thresholds, or the amount likely recoverable through liquidation.

## Fail-closed, tiered invariant suite

Selected by the operator on 2026-07-14: evaluate a versioned, fail-closed invariant suite after every atomic posting batch and every reconciliation. A hard invariant failure never becomes a warning that permits additional exposure. External uncertainty and unavailable valuation are classified separately so that the system does not confuse delayed evidence with corrupted accounting.

### Atomic evaluation boundary

A canonical event may require several postings and projection changes. The system prepares and validates that complete atomic batch before committing any part of it. Either the whole batch and its invariant result are durably admitted in canonical order, or none of its accounting effects become visible. Checks then run again after any reconciliation classification or repair.

### Posting and ownership invariants

After every atomic batch:

- For every native asset, closing owned quantity equals opening owned quantity plus the batch's canonical asset postings.
- No Spot grid-owned, available, reserved, pending, retained, or lot quantity may be negative. The system cannot create short inventory through fees, late fills, repair, or classification changes.
- Each owned unit has exactly one availability classification. Owned quantity equals available plus reserved plus each explicitly defined pending or in-transit classification; classifications neither overlap nor omit quantity.
- Every reservation is backed by exactly one active or explicitly uncertain managed-order obligation. Reservation never exceeds owned quantity, and releasing or moving a reservation does not change ownership.
- Aggregate sell obligations do not exceed backing inventory. Aggregate buy obligations do not exceed reserved quote principal. Fee reserve is not counted simultaneously as order principal.
- Grid inventory equals the exact sum of remaining inventory-lot quantities. Every lot and split retains complete acquisition and fee provenance.
- A lot quantity cannot be consumed twice. Paired sells and terminal disposals cannot consume more than their eligible attributed lots.
- Order fills are monotonic and bounded: cumulative filled quantity equals the exact sum of admitted partial fills and never exceeds the venue order quantity. Allocated lot quantities, fees, costs, and proceeds sum exactly to their source postings.
- Canonical event, venue order, trade, fill, and fee identities are idempotent. One piece of venue evidence can affect accounting at most once, including after reconnect or replay.
- Every fee retains its actual asset and exact quantity, is deducted exactly once, and cannot drive the allocated fee-asset balance negative.
- Grid-owned quantities and obligations remain within the approved capital allocation, maximum planned inventory, and other applicable risk limits.
- When all required valuations are available, the selected realized, unrealized, current-equity, conservative-liquidation-equity, and flow-adjusted-result identities hold exactly.
- A permanently closed run has no managed open-order obligation or reservation. Any remaining owned asset is explicitly classified, including retained holdings and pending disposition.
- Rebuilding from the canonical journal with the same immutable configuration, venue rules, and valuation evidence produces exactly the same subledger, lots, reservations, results, and invariant outcomes.

### Reconciliation invariants

After reconciliation:

- Every managed local order is matched to authoritative venue evidence or has an explicit reconciliation classification such as awaiting evidence, missing locally, missing at venue, or foreign. No order silently disappears from either view.
- Every venue fill and fee since the durable checkpoint is admitted exactly once or explicitly shown as evidence still awaiting classification.
- Whole-account venue balances cover the grid's expected allocated assets after other known allocations and foreign activity are accounted for. A whole-account snapshot never becomes proof that an unexplained change belongs to this grid.
- Venue free and locked observations are explainable by known balances, managed orders, foreign orders, and explicitly in-flight venue events. They are not required to equal grid available and reserved classifications directly because the Binance account may contain isolated non-grid activity.
- No unexplained balance, order, fill, fee, or reservation difference remains before a reconciled resume, promotion decision, or continuation that could create new exposure.

The later authority and reconciliation-state decisions will define the exact evidence precedence and state vocabulary used by these checks; they may refine classifications but cannot weaken the fail-closed behavior.

### Failure tiers and consequences

- **Hard accounting violation:** a conservation, non-negativity, backing, idempotency, provenance, fill-bound, allocation-limit, or exact-replay invariant fails. The atomic batch is not partially committed, new exposure is blocked immediately, the violation is durably recorded, and the runtime enters the applicable exposure-reducing safety and reconciliation transition.
- **Pending reconciliation difference:** expected and observed state differ, but the difference is tied to a specific known in-flight command or missing evidence request and has a deadline. New exposure is allowed only if the later reconciliation policy explicitly proves it safe. Expiry or contradictory evidence escalates the difference; `pending` is never an indefinite warning bucket.
- **Valuation unavailable:** a required current or conversion mark is missing or stale. Native quantities may still be internally consistent, so this is not by itself an asset-conservation failure. Risk, promotion, and result decisions that require the valuation remain blocked rather than treating the asset value as zero.

Every invariant evaluation is journaled with invariant identifier and version, canonical event sequence, evaluated inputs or input hashes, outcome, relevant evidence identities, and resulting safety action. Successful checks must be observable as well as failures so replay and incident analysis can prove which rules governed a decision.

### Worked examples

**Valid reservation:** the grid owns `0.010 BTC`, with `0.006 BTC` reserved for managed sells and `0.004 BTC` available. The ownership classification and sell-backing invariants pass because the classifications sum exactly and every sell is inventory-backed.

**Duplicate late fill:** after a cancellation request, a late fill for `0.003 BTC` is admitted once. If reconnect delivers the same trade again, its venue identity is already present and idempotency prevents a second deduction. If apparently new evidence would make available or owned inventory negative, the complete new batch fails atomically and the safety/reconciliation transition begins.

**Unexplained fee difference:** the subledger expects `0.010 BTC`, but the venue observation shows the grid allocation may be covered by only `0.00999 BTC`. The system does not overwrite expected inventory. The difference may remain pending only while a specific missing fill or fee report is being retrieved under a deadline. It must then be explained by canonical evidence, classified as foreign activity under the later policy, or escalated as a hard unresolved difference.

### Declined invariant alternatives

- **End-of-run checks only:** simpler and useful as an additional test, but corrupted balances, duplicate fills, or unsupported obligations could influence subsequent orders before the run ends. It cannot protect paper or live operation and is insufficient as the canonical invariant policy.
- **Warning-based checks with generic tolerances:** permits trading to continue through unexplained differences and can hide duplicate fees, fills, rounding defects, or true asset loss. Source precision and known in-flight evidence are modeled explicitly instead; no generic epsilon or warning-only continuation weakens a hard invariant.

## Fact-specific authority and reconciliation states

Selected by the operator on 2026-07-14: authority belongs to the source qualified to prove each kind of fact. Neither the local runtime nor Binance is universally authoritative. Reconciliation preserves expected state, observed state, source identity, and evidence time separately until the comparison reaches an explicit state; no latest-value-wins rule silently replaces one with the other.

### Authority matrix

| Fact | Authoritative evidence | Boundary and consequence |
| --- | --- | --- |
| Approved strategy behavior and limits | The immutable strategy configuration version and its approval record | Later UI edits or process defaults cannot change an open run. |
| What the strategy observed, decided, and intended | The durably admitted canonical events and decision batches in the trading event journal | An order intent proves desired action, not transmission, venue acceptance, or execution. |
| What command the runtime attempted | The durably recorded outbound command, stable client identity, payload, and attempt metadata | A timeout after transmission remains uncertain; it does not prove rejection and cannot justify an immediate duplicate order. |
| Whether a venue order exists and its venue state | Authenticated Binance order evidence carrying venue and client identities | Streaming evidence provides timely updates; an explicit reconciliation query supplies a point-in-time observation. Conflicting observations remain visible and are ordered by their venue semantics and evidence times, not arrival time alone. |
| Executed quantity, price, trade identity, and actual fee | Authenticated Binance trade/fill evidence | Trade-level evidence governs postings. Order cumulative quantity is a cross-check and missing-evidence signal, not permission to invent an unidentified fill or fee. |
| Whole-account free and locked asset quantities | Authenticated Binance account observations at a stated observation time | These prove venue custody at account scope, not which quantity belongs to this grid. |
| Grid ownership, availability, reservations, lot provenance, and result attribution | The exact grid subledger projected from canonical evidence and approved allocations | Binance does not know the internal boundary between this grid, another algorithm, and manual holdings. A venue snapshot cannot silently rewrite the subledger. |
| Price used by a decision or valuation | The exact recorded canonical market event or valuation observation selected by the applicable policy | A newer price cannot retroactively replace evidence used by an earlier decision. |
| Venue eligibility, filters, and quantization applied to an order | The recorded time-versioned venue-rule observation used at the order boundary | Later rule changes do not alter the historical explanation of an already-created order. Current rules must be revalidated before a new submission or reconciled resume. |

Authority establishes what a source can prove, not that every observation is complete or current. Each evidence item retains source, native identifiers, event or venue time, received time, request context where applicable, and canonical admission identity. Derived caches and UI projections are never authoritative.

### Reconciliation item and states

Each material comparison is a durable reconciliation item scoped to one fact or tightly coupled fact set. It has exactly one current state and retains its full transition history:

- **Reconciled:** authoritative evidence supports the expected and observed state, including all material fills, fees, reservations, and ownership effects.
- **Pending evidence:** a specific command, query, stream gap, or other known in-flight evidence source could explain the difference and has an explicit deadline. This is temporary uncertainty, not success.
- **Venue ahead:** authenticated venue evidence proves an order, fill, fee, or state change that has not yet been admitted into the canonical local history.
- **Local ahead:** the canonical local state expects a venue object or state that the current authoritative venue evidence does not establish.
- **Conflicting evidence:** sources that should agree describe the same identified fact incompatibly and ordinary event ordering does not explain the difference.
- **Foreign activity:** valid venue activity affects relevant account assets but did not originate from the grid's canonical command identity.
- **Unexplained difference:** the expected-versus-observed difference has no accepted evidence-backed explanation, or a pending-evidence deadline expired without resolution.

`Resolved` is not used to erase the prior classification. A repaired item transitions to `reconciled` and links the evidence and repair action that resolved it; the complete state history remains queryable.

### State consequences

- Both expected and observed values remain visible in every non-reconciled state. The newest observation may supersede an older observation for its own source but cannot overwrite canonical history or grid ownership.
- `Pending evidence` is permitted only for an identified cause, evidence request, deadline, and safety posture. The repair policy will specify whether the particular uncertainty permits only inventory-reducing actions or blocks all commands.
- `Venue ahead` requires idempotent admission of the missing venue evidence before dependent local decisions proceed.
- `Local ahead`, `conflicting evidence`, `unexplained difference`, and foreign activity that may impair allocated assets block new exposure and require the applicable safety transition.
- Reconciled resume, promotion, and live continuation require every material item to be `reconciled` or to have a separately approved terminal disposition that creates no unsupported obligation.
- Every transition records previous and next state, reason, evidence identities, expected and observed exact values, deadline where applicable, automated or operator actor, and resulting safety action.

### Worked examples

**Submission timeout:** the journal proves that a command carrying a stable client-order identity was transmitted, but the response timed out. The order is `pending evidence`, and the runtime queries the venue using that identity rather than submitting a replacement. If Binance proves the order exists, the missing acknowledgement and any fills become `venue ahead` evidence and are admitted until the item is `reconciled`. If sufficiently authoritative venue evidence proves absence, the item becomes `local ahead`; its reservation is released only through the selected repair policy. A replacement is never submitted while the original could still exist because that could duplicate exposure.

**Manual or other-algorithm sale:** Binance reports a BTC trade with no managed grid-command identity. The venue evidence is authoritative for the trade and account-level asset effect, while the subledger remains authoritative for grid allocation. The item is `foreign activity`, not grid-cycle profit. If the sale may have consumed BTC allocated to this grid, new exposure is blocked until the allocation and sell backing are repaired explicitly.

### Declined authority alternatives

- **Local journal is always authoritative:** deterministic but unsafe when Binance accepted an order, fill, cancellation, or fee whose response or stream event was lost. Local intent cannot establish venue reality.
- **Binance snapshots are always authoritative:** reflects current whole-account custody but cannot identify internal grid ownership, reservations, lots, or foreign activity and erases causal history if copied over expected state. Venue observations remain authoritative only for the venue facts they actually prove.

## Evidence-preserving repair and foreign activity

Selected by the operator on 2026-07-14: automatic repair is limited to deterministic, evidence-backed actions that preserve history and do not increase exposure. Material changes to ownership, allocation, economic attribution, or accepted loss require explicit operator approval. A repair appends evidence and state transitions; it never edits the facts that produced the discrepancy.

### Safe automatic actions

The runtime may perform the following automatically when their stated preconditions are proven and journaled:

- Deduplicate repeated delivery of an already admitted venue event without applying its economic effect again.
- Admit authenticated `venue ahead` order acknowledgements, state transitions, fills, actual fees, and late fills using their stable identities and exact source values.
- Rebuild the grid subledger, lots, reservations, accounting results, and other deterministic projections from the canonical journal and immutable context.
- Replace or discard a derived cache or UI projection when exact replay proves that the cache is stale; authoritative journal history remains unchanged.
- Recalculate reservations from reconciled managed-order obligations. A reservation may be released only after authoritative evidence proves the order terminal and all fills and fees through that terminal state are accounted for.
- Automatically cancel a positively identified managed order when it creates or preserves unsupported exposure. Cancellation is followed by reconciliation because acceptance is not proof that the order did not fill late.
- Re-run the strategy decision core after reconciliation. Any replacement or restored rung order is a new, limit-checked strategy decision from reconciled state, never an accounting correction.

Every automatic action must be idempotent, identify the evidence and rule version authorizing it, pass the full post-action invariant suite, and retain its before-and-after reconciliation state.

### Operator-approved actions

Explicit operator approval is required to:

- assign a foreign event or asset effect to the grid;
- increase, decrease, or otherwise redefine grid ownership or capital allocation;
- replenish an impaired grid allocation from separately unallocated holdings;
- reduce the allocation and cancel or resize the obligations it can no longer support;
- append an evidence-backed compensating posting for a proven external correction or source defect;
- accept an unrecoverable asset loss or other terminal discrepancy;
- choose retention, conversion, or disposal of remaining holdings outside an already approved terminal policy;
- resume after a material reconciliation incident when the lifecycle and risk specifications require manual authorization.

Approval records the operator identity, exact proposed postings and obligation effects, evidence, reason, before-and-after allocation coverage, and resulting run state. Approval cannot make an internally contradictory state valid; the resulting batch must still pass every hard invariant.

### Forbidden repairs

Neither automation nor operator approval may:

- edit, delete, reorder, or silently replace canonical journal evidence;
- fabricate an order, fill, fee, transfer, price, or venue response;
- copy a whole-account Binance balance into grid ownership as a correction;
- round away, tolerance-dismiss, or reclassify an unexplained nonzero difference without evidence;
- release an order reservation while the order may still exist or have unadmitted fills;
- submit a replacement while the original order remains uncertain;
- classify foreign or unexplained activity as grid-cycle profit;
- make one event affect native assets more than once.

If source evidence is later proven erroneous, the original remains immutable and a linked compensating posting records the accepted correction. The audit trail must show both claims and why the later evidence governs the corrected projection.

### Foreign-activity isolation and coverage

- Every venue order and trade that lacks the grid's managed identity is classified as foreign activity, including manual actions and other algorithms. Deposits, withdrawals, transfers, and fees without canonical grid provenance are handled the same way when relevant to allocated assets.
- Foreign activity never becomes a grid fill, fee, cycle result, or lot merely because it affects the same whole-account asset.
- Reconciliation tests aggregate allocation coverage per native asset: the authenticated whole-account quantity must cover this grid's ownership together with every other known allocation that shares the account. Unallocated surplus is visible separately and is not silently assigned to a grid.
- If a foreign event changes only unallocated surplus and aggregate coverage and all managed obligations remain valid, the event may reach a reconciled terminal classification as excluded foreign activity. Grid accounting is unchanged.
- If aggregate coverage is impaired or cannot be proven, new exposure is blocked immediately. Unsupported managed orders are cancelled; only obligations proven to be backed and permitted by the safety lifecycle may remain.
- The operator must then choose an evidence-backed resolution: replenish from unallocated holdings, reduce an allocation and its supported obligations, or stop the affected run under its approved disposition policy. The system does not guess which strategy economically owns a fungible account-level loss.
- Separate stable client-order identities and explicit allocations are mandatory for every algorithm sharing the Binance account. They improve attribution but do not replace the aggregate custody and coverage check.

### Worked examples

**Covered foreign sale:** the grid allocation owns `0.010 BTC`, while the account holds `0.020 BTC` in total and other known allocations require none of the remaining `0.010 BTC`. A manual or other-algorithm sale of `0.005 BTC` leaves `0.015 BTC`. The foreign sale is excluded from grid result, and the grid remains fully covered; after all related venue evidence is complete, the item can be reconciled without changing grid ownership.

**Impaired foreign sale:** under the same `0.010 BTC` grid allocation, foreign activity leaves only `0.008 BTC` in the account. The grid is undercovered by `0.002 BTC`; new exposure is blocked and unsupported obligations are cancelled. The system cannot arbitrarily assign the shortage. The operator must approve replenishment, allocation reduction with obligation changes, or run termination.

**Recovered missing fee:** a fill was admitted before its authenticated fee evidence arrived. When the exact fee and fee asset become `venue ahead`, automatic admission is safe because it records proven venue reality and is idempotent. If the resulting fee exposes undercoverage, the repair completes its accounting batch but triggers the required safety state rather than hiding or rejecting the real fee.

### Declined repair alternatives

- **Automatically converge grid state to Binance balances:** simple and superficially self-healing, but destroys allocation isolation and can silently assign manual or other-algorithm activity to the grid. It also erases the causal evidence needed to explain a loss.
- **Require manual approval for every difference:** conservative in appearance, but routine duplicate delivery, stream gaps, missing acknowledgements, and deterministic replay repairs would cause unnecessary downtime and repetitive operator actions. This increases operational error without adding judgment where authoritative evidence already determines the answer.

## Existing-code consequences

- Retain the canonical ledger's single fill-derived path and its property-testing intent.
- Replace binary floats and quote-only `Fill.fee` with exact native-asset postings.
- Remove futures/short-lot behavior from the Spot accounting boundary.
- Do not seed grid state from total exchange balances.
- Replace independent live PnL ledgers with projections from the canonical subledger.

## Accepted decisions

1. **Selected:** paired-lot provenance governs grid-cycle results; terminal disposals consume remaining lots FIFO and retained holdings preserve provenance.
2. **Selected:** source-exact decimals, boundary-only venue quantization, deterministic remainder assignment, exact reconciliation, and preserved pending or retained residuals.
3. **Selected:** native-asset cost and fees feed current grid equity and conservative liquidation equity; results are flow-adjusted, fees are counted once, and missing/stale valuation is explicit.
4. **Selected:** a versioned, fail-closed invariant suite runs after every atomic posting batch and reconciliation; hard accounting violations block exposure, bounded external uncertainty remains explicit, and unavailable valuation cannot masquerade as zero.
5. **Selected:** fact-specific authority distinguishes configuration, journaled intent, attempted commands, Binance order/fill/account evidence, grid subledger ownership, market observations, and venue-rule versions; every difference occupies an explicit durable reconciliation state without silent overwrite.
6. **Selected:** automatic repair is evidence-preserving, deterministic, idempotent, and non-exposure-increasing; ownership and allocation changes require operator approval; forbidden repairs cannot rewrite or invent evidence; and foreign activity remains isolated unless an explicit approved allocation action accounts for its effects.
