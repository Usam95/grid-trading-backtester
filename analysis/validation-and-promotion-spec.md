# Validation and promotion-gates specification

Status: accepted  
Wayfinder ticket: [Specify validation and promotion gates](../.scratch/comprehensive-grid-trading-system/issues/07-specify-validation-and-promotion-gates.md)

## Decision-record policy

At the operator's request, every choice in this specification retains the complete recommendation, selected behavior, examples, consequences, assumptions, and declined alternatives. A selected option number alone is never the decision record.

## Scope

This specification defines the reproducible evidence and explicit human approvals required to move one immutable Binance Spot grid strategy configuration from research through historical validation, high-fidelity replay, live-data paper qualification, and tightly capped first-live activation. It also defines invalidation, rollback, and requalification boundaries. Passing a gate never starts trading automatically and never weakens the accepted [risk and safety specification](risk-and-safety-spec.md).

The first MVP remains one static arithmetic or geometric grid, one active symbol, spot inventory only, fixed quote sizing without compounding, and a maximum `250 USDT` qualifying-paper/first-live capital envelope. Research may compare candidates, symbols, and periods; promotion authorizes exactly one immutable configuration and evidence bundle.

## Current-code validation audit

### Reusable canonical `gridlab` foundations

- `research/grid_search.py` performs deterministic Cartesian parameter search, can use multiple processes, records all candidate metrics, and propagates the declared number of tested configurations into the metric layer.
- `research/walk_forward.py` provides expanding-window chronological optimization followed by the next unseen out-of-sample chunk. It records selected parameters, in-sample score, out-of-sample score, return, and drawdown per fold.
- `research/monte_carlo.py` offers seeded trade-PnL bootstrap and shuffled-return simulations with final-return, loss-probability, and drawdown distributions.
- `research/robustness.py` combines out-of-sample profitability, deflated Sharpe, and Monte Carlo path risk into a transparent scorecard.
- `results/metrics.py` supplies total return, CAGR, intrabar drawdown, volatility, Sharpe, Sortino, Calmar, PSR, deflated Sharpe, trade statistics, fee drag, buy-and-hold excess return, capital utilization, grid-cycle result, and related metrics.
- The facade produces JSON-serializable results, benchmarks, series, trades, and HTML reports, while immutable configuration objects support repeated research runs.
- Tests cover basic grid-search ranking, trial-count propagation, walk-forward output, seeded Monte Carlo distributions, metrics, and report generation.

These are migration foundations, not accepted promotion semantics. They predate the accepted canonical accounting, event-parity, Binance execution, and risk-state contracts and must be revalidated against those specifications.

### Useful legacy `grid-backtest-saas` workflow

- Persistent asynchronous research jobs, trial fingerprints, stage results, progress, cancellation, failure capture, and cached/resumable trials are valuable UX and workflow inputs for `gridlab-studio`.
- Its staged pipeline performs broad screening, medium validation, exact-engine validation, train/forward or walk-forward reporting, execution-cost stress runs, constraints, finalist ranking, and stored artifacts.
- The mature UI/API vocabulary for experiments, candidate comparison, progress, final ranking, and reusable artifacts should inform the canonical operator workflow.

The legacy research engines and scores do not become canonical dependencies. Their useful persistent-experiment and UI patterns should be reimplemented around canonical evidence identities and semantics.

### Blocking gaps and unsafe assumptions

1. **Selection leakage:** the legacy staged pipeline ranks candidates on central and full-period data before later calling portions of the same period train/forward or walk-forward validation. The resulting “forward” evidence is not an untouched promotion test.
2. **Insufficient nested validation:** canonical `gridlab` has honest expanding walk-forward optimization, but there is no separately locked final holdout that remains unseen after all parameter ranges, objectives, risk-compatible stop placement, and candidate-family choices are frozen.
3. **Weak dataset identity:** neither implementation supplies the accepted immutable dataset manifest, source lineage, completeness/duplicate/gap findings, rule/fee versions, adjustment history, or deterministic derived-dataset identity required for reproducibility.
4. **Incomplete regime coverage:** synthetic range/trend generators and optional indicator filters exist, but no canonical, evidence-backed regime segmentation or required cross-regime acceptance matrix exists.
5. **Single-symbol bias:** research APIs accept one symbol per run; no promotion rule requires robustness across other eligible symbols or explains how non-promoted symbols contribute external evidence without becoming tuned targets.
6. **Execution-model gap:** existing candle research does not implement all accepted conservative ambiguity, queue/volume participation, post-only rejection, partial-fill, IOC-disposal, native-fee, unknown-outcome, and safety-posture semantics.
7. **Simplistic resampling:** iid trade bootstrap and shuffled returns break serial dependence and regime clustering; they are useful sensitivity tools but cannot alone estimate grid tail risk or certify survival.
8. **Heuristic score:** the current 0–100 trust score uses hand-selected weights and grade cutoffs. It is decision support, not a gate, and must never allow one strong metric to compensate for a mandatory failure.
9. **Incomplete multiple-testing control:** deflated Sharpe receives the Cartesian grid size, but trial-family identity, repeated reruns, changed search spaces, manual candidate inspection, correlated trials, and cross-symbol searches are not fully counted or governed.
10. **No promotion state machine:** no canonical evidence bundle, gate result, approval identity, expiration, invalidation, rollback, capital authorization, or prohibition on automatic activation exists.
11. **No operational qualification:** historical research is not connected to the accepted 30-day live-data paper requirement, parity comparisons, fault drills, reconciliation outcomes, incident rules, or first-live rollback.
12. **No compute-aware evidence contract:** broad proxies can ignore advanced behavior and select the wrong finalists; there is no rule declaring which approximate stage may discard candidates, which stages require exact canonical semantics, or how minimal Azure compute affects latency rather than correctness.

### Reuse judgment

- **Keep and deepen:** immutable experiment configuration, Cartesian search, deterministic seeds, expanding chronological folds, metric registry, benchmarks, reports, and canonical result serialization.
- **Reimplement from the SaaS reference:** persistent experiment/trial identity, staged progress, resumability, comparison workflow, artifact history, and compute-budget presentation.
- **Replace:** leakage-prone staged selection, proxy-based promotion decisions, arbitrary composite trust grades, simplistic final ranking, and any engine-specific evidence that cannot reproduce accepted canonical semantics.
- **Add:** immutable dataset and search-family manifests, nested time-aware validation, locked holdout governance, regime and cross-symbol matrices, dependence-preserving chronological robustness evidence, bounded cost/liquidity stresses, deterministic replay parity, paper/live evidence, explicit gates, approval and invalidation records, and non-compensable mandatory criteria. Statistical block-resampling is deliberately deferred from the MVP gate set below.

## Topics requiring operator decisions

1. Time-series partitioning, nested walk-forward, and locked-holdout governance.
2. Dataset scope, granularity, history length, quality gates, and versioning.
3. Symbols, market regimes, and cross-market robustness requirements.
4. Search-space governance, multiple-testing accounting, objectives, and candidate selection.
5. Mandatory metrics and quantitative historical thresholds.
6. Fee, spread, slippage, liquidity, rejection, latency, and gap stress scenarios.
7. Parameter-neighborhood stability and block-aware resampling requirements.
8. High-fidelity event-replay qualification and cross-mode parity thresholds.
9. Paper entry, minimum 30-day qualifying period, resets, incidents, and operational pass criteria.
10. First-live approval, capital activation, observation period, rollback, evidence expiration, and requalification.

## Historical evaluation architecture

### Walk-forward development plus one locked promotion holdout

Selected by the operator on 2026-07-15: use nested chronological evidence with repeated walk-forward development folds, followed by one separately locked final holdout and then genuinely future live-data paper qualification.

#### Evidence partitions

- **Development data** may be inspected and reused to define the eligible symbol universe, data-quality policy, parameter ranges, objective, cost model, risk-compatible stop placement, and candidate-selection rules.
- Development evaluation uses repeated chronological walk-forward folds. For each fold, optimization sees only that fold's training history; the selected candidate is then evaluated on its immediately following out-of-sample test interval.
- Walk-forward test results are out of sample for their individual fold, but they remain development evidence because the operator and research process can inspect them and change the overall experiment afterward.
- One later chronological interval is reserved as the **locked promotion holdout**. Its market values and candidate results are unavailable to selection until the dataset manifest, search-family manifest, algorithms, parameter ranges, costs, objective, mandatory thresholds, finalist-selection rule, random seeds, and immutable candidate configurations are frozen.
- The holdout is evaluated only after development gates pass. It selects nothing and retunes nothing; it may only confirm or reject the already-frozen candidate and promotion bundle.
- Paper qualification follows historical acceptance and consumes future live Binance market events. It is not another historical split and cannot be backfilled from previously observed data.

Every partition is chronological. Randomly interleaved cross-validation is prohibited because it leaks future market structure into training and destroys serial dependence.

Example:

```text
development: repeated train → next-period test folds | locked holdout | future paper
2020 ─────────────────────────────── 2024-06 | 2024-07 ─ 2025-06 | live events
```

The dates are illustrative; exact history and window lengths are decided separately.

#### Holdout governance

- A holdout evaluation is an auditable, one-way event linked to exact dataset, search-family, code/build, configuration, and evidence identities.
- Merely viewing aggregate holdout results, failure reasons, trades, or charts consumes the holdout for that search family because those facts can influence later design.
- Passing the holdout preserves the frozen candidate for the next gate; it never authorizes paper or live trading automatically.
- Failing the holdout rejects the candidate. The revealed interval may become development data, but the candidate or search family can be tested again for promotion only against a genuinely later, previously locked interval under a new evidence identity.
- Changing strategy semantics, material accounting/execution assumptions, dataset corrections, parameter ranges, objectives, selection rules, mandatory thresholds, or risk profile after holdout evaluation invalidates the historical promotion bundle and requires new development and a new holdout.
- Multiple candidates cannot be tried sequentially on the same holdout until one passes. Every candidate evaluated there belongs to the declared trial family and the pre-frozen finalist rule; the result of one candidate cannot determine which additional candidate is exposed next.

#### Boundary-state rules

- No trading state, open order, inventory lot, high-water mark, or realized result carries from a training interval into its out-of-sample test interval or from development into the locked holdout.
- Each evaluation run activates independently using only the immutable candidate and inputs available at that evaluation boundary, applying the canonical bootstrap, allocation, activation, venue, and risk rules.
- Historical observations required solely for indicator or feature warm-up may precede the scored interval, but cannot contribute trades, results, parameter selection, or future information. Warm-up identity and length are evidence.
- Costs, failures, range exhaustion, risk postures, terminal behavior, and retained holdings at the end of each scored run remain in that run's result; the evaluator cannot flatten or discard them optimistically to improve comparison.

#### Consequences

- Repeated walk-forward results measure stability through several market intervals rather than one favorable split.
- The locked holdout measures whether the entire human-and-software research process generalized after all visible tuning, not merely whether one optimizer fold did.
- Holdout failure is intentionally expensive: it prevents iterative peeking from converting the final test into hidden development data.
- The current canonical expanding walk-forward implementation is reusable but must be extended with manifest identity, strict partition enforcement, independent run activation, and a separate holdout gate.
- The legacy SaaS staged pipeline must be redesigned because its early full-period/central-period ranking contaminates periods later labelled forward validation.

#### Declined alternatives

- **One chronological 70/30 split:** cheap and understandable, but one regime can dominate and repeated redesign after inspecting the 30% silently overfits it.
- **Walk-forward without a locked holdout:** measures fold generalization but does not test the broader research process after repeated inspection and adjustment.
- **Random cross-validation:** gives future observations to training and breaks the time dependence that drives fills, inventory, drawdown, and regime behavior.

### Rolling primary walk-forward with expanding-window sensitivity

Selected by the operator on 2026-07-15: use fixed-length rolling training windows as the primary walk-forward selection method and require an expanding-window analysis as an independent, non-compensating development sensitivity check.

#### Primary rolling analysis

- Every rolling fold uses the same predeclared training duration and the immediately following predeclared out-of-sample duration.
- As folds advance, the oldest training observations leave the window. This bounds compute and makes parameter selection respond to market structure available within a realistic recent-history horizon.
- The eligible parameter/search family is optimized independently inside each fold. No later fold, locked-holdout fact, or future venue-rule observation may influence an earlier selection.
- Primary walk-forward pass criteria apply to the ordered collection of out-of-sample fold results, including losses, risk-posture time, range exhaustion, retained inventory, terminal outcomes, costs, and selected-parameter stability—not only mean return.

#### Expanding-window sensitivity

- The sensitivity run starts from the same earliest eligible development boundary, then retains all earlier training observations as each fold advances.
- It uses the same search-family manifest, candidate semantics, objective, costs, risk policy, fold test boundaries, and evidence rules as the rolling analysis; only the training-window start differs.
- Its purpose is to expose dependence on the rolling cutoff and disagreement between recent-market and long-history parameter evidence.
- Expanding results are mandatory and cannot be blended into a composite score that compensates for failure of the primary rolling analysis. Exact acceptable disagreement and pass thresholds are decided separately.
- Every distinct configuration evaluated in both analyses belongs to the declared multiple-testing family. The second analysis is not statistically free merely because it is labelled sensitivity.

Example with illustrative durations:

```text
rolling primary
[train 24m][test 3m]
   [train 24m][test 3m]

expanding sensitivity
[train 24m][test 3m]
[-------- train 27m --------][test 3m]
```

If a candidate family performs well only after old observations leave the rolling window, the expanding analysis reveals that historical-regime dependency. If it performs well only when all old observations remain, rolling folds reveal that it may not adapt to more recent structure. Neither result automatically proves which history is economically correct; the discrepancy is explicit promotion evidence.

#### Consequences

- The primary method resembles periodic real-world re-evaluation using a bounded amount of recent history.
- The expanding sensitivity preserves evidence from older regimes and detects arbitrary dependence on the rolling-window start.
- Compute approximately increases relative to one walk-forward analysis, but this affects research duration rather than allowing weaker evidence; it need not run continuously on the minimal live Azure node.
- The current canonical `gridlab` expanding implementation remains useful, but rolling windows, common fold-boundary control, manifest identities, non-compensating gates, and complete canonical outputs must be added.
- The later search-space policy must count all rolling and expanding trials, retries, changed ranges, symbols, and manually inspected variants.

#### Declined alternatives

- **Expanding windows only:** preserves every old regime and matches current canonical code, but ancient market structure can dominate selection and training cost grows at each fold.
- **Rolling windows only:** reflects recent conditions and bounds compute, but apparent success may depend on an arbitrary history cutoff that remains untested.
- **One fixed train/test split:** cannot show whether results survive different chronological selection boundaries.

### Five-year historical window profile

Selected by the operator on 2026-07-15: require at least 60 consecutive quality-approved calendar months before a strategy family can qualify for the first-live MVP symbol.

#### Exact partition profile

- The earliest 48 months are development data; the immediately following 12 months are the locked promotion holdout.
- Primary rolling walk-forward uses a fixed 24-month training window followed by a 3-month out-of-sample test window.
- Eight consecutive test folds cover the final 24 months of development data. The training window advances by 3 months for each fold and remains 24 months long.
- Expanding-window sensitivity begins with the same first 24 training months, retains all earlier development observations as it advances, and uses the identical eight 3-month test boundaries.
- Calendar boundaries are canonical UTC boundaries recorded in the dataset and experiment manifests; the implementation cannot substitute approximate bar counts that shift partitions after gaps or timeframe changes.
- The locked holdout is the next 12 complete calendar months and is not included in either rolling or expanding selection.
- Feature/indicator warm-up may read the minimum pre-boundary observations declared by the immutable experiment, but those observations cannot produce trades, results, parameter choices, or future leakage into the scored interval.

```text
development                                                    holdout
initial 24m training | 8 consecutive quarterly test folds      12m
<------------------------ 48 months ------------------------->|<--->
```

The holdout cutoff and manifest are designated before candidate results are exposed. Because cryptocurrency price history is publicly observable, this rule governs access by the research/selection workflow and use in strategy decisions; it does not falsely claim the operator has never seen a historical price chart.

#### Eligibility and incomplete history

- A symbol whose quality-approved history is shorter than 60 months may be explored and used as external sensitivity evidence but cannot be the first-live promoted symbol under this profile.
- More history may be retained for regime research and sensitivity, but adding it to the selection windows changes the experiment manifest and requires the declared analyses to be rerun.
- Missing, duplicated, corrupt, or venue-inapplicable intervals cannot be silently dropped to manufacture 60 months. Exact dataset quality and repair gates are decided separately.
- Research compute may use staged candle screening and exact finalist evaluation under the accepted data-fidelity architecture. The five-year requirement constrains evidence, not a requirement to run every trial at maximum event fidelity or on the minimal live Azure node.

### Fail-closed historical-data quality policy

Selected by the operator on 2026-07-15: historical promotion evidence must contain only observed or authoritatively established market facts. The system never interpolates, forward-fills, synthesizes, or silently removes missing prices, volume, trades, spread, or order-book evidence.

#### Admission and manifest checks

Every raw source object and derived dataset is admitted through a reproducible quality report recorded in its immutable dataset manifest. Checks applicable to the data type include:

- exact source location and retrieval time, declared Binance market and symbol, file/object identity, byte size, and cryptographic checksum;
- expected schema, parseability, source decimal preservation, UTC timestamp range, timestamp alignment, chronological order, and declared interval coverage;
- unique candle/open-time or trade identity across files and file boundaries, with conflicting records for the same identity classified as corruption;
- candle consistency (`low <= open/close <= high`), non-negative volume and counts, and agreement between the record's identity and its declared interval;
- trade/aggregate-trade identity ordering, duplicate and boundary checks, and source-specific continuity evidence where the source contract makes such evidence available;
- symbol-listing and trading-status applicability, venue-rule version applicability, and detection of intervals during which the expected source evidence is absent;
- derivation lineage, transformation version, input checksums, output checksum, and the quality state inherited from every input.

An aggregate candle legitimately derived from complete lower-level observations is allowed and retains their provenance. Creating a candle or trade merely to occupy a missing interval is prohibited. A source-confirmed zero-trade interval is distinct from a missing record and must retain the evidence that establishes it.

#### Recovery and repair

1. Preserve the original raw object unchanged.
2. Retry acquisition from the approved official Binance archive or API path and compare overlapping official evidence where available.
3. Remove an **exact duplicate** only when identity and content are identical; record the deterministic deduplication rule, every removed source record, and the derived dataset's new checksum. Two records with the same identity but different content are not deduplicated—they are conflicting evidence.
4. If Binance later republishes or corrects data, ingest it as a new source version and derive a new manifest. Never edit the prior evidence or silently reuse its results.
5. If authoritative evidence proves that trading or publication was interrupted at the venue, represent a **venue market interruption** explicitly in canonical time. The simulator cannot infer fills or ordinary decisions inside the interruption; decision-changing freshness and continuity behavior follows the same canonical safety semantics used by replay and online modes.
6. If absence remains attributable to collection, transfer, archive, parsing, or unknown origin, classify it as a **source-data gap** and quarantine every affected promotion partition.

#### Promotion consequences

- All 60 months used by the qualifying walk-forward and locked holdout must be quality-approved under the frozen policy. A quarantined interval means the affected development fold or holdout is not promotion evidence and cannot count toward the required window.
- Incomplete data may be used for labelled exploratory diagnosis only. Its report must state the missing scope and it cannot be combined with complete folds, assigned a compensating score, or presented as a promotion result.
- A proven venue interruption remains in the chronology; it is not dropped as an inconvenient period. It exercises the strategy's no-evidence, stale-data, and recovery behavior and contributes no invented fill opportunity.
- Any post-result data correction, newly discovered corruption, checksum mismatch, source-contract change affecting interpretation, or altered repair rule invalidates the affected result bundle and requires regeneration from the new manifest.
- Dataset quality is evaluated before strategy outcomes are inspected where possible. The operator cannot waive a failed quality rule because the resulting performance appears favorable.

#### Example

Three expected one-minute BTC/USDT records are absent at 02:17–02:19 UTC. Copying the 02:16 close into three zero-volume candles is prohibited because it invents market observations and could suppress a stop, rung crossing, or volatility estimate. The acquisition process retries official sources. If authoritative evidence proves a Binance interruption, the manifest records one explicit venue market interruption and the strategy receives no fabricated prices or fills during it. If the absence cannot be proven venue-side, it remains a source-data gap; the affected fold or holdout is quarantined and the five-year qualification does not pass until complete evidence is reacquired or a different eligible chronological window is declared before result inspection.

#### Consequences

- Some apparently usable public datasets and otherwise profitable candidates will be ineligible.
- Raw retention, checksums, lineage, quality reports, and deterministic derived versions add storage and processing work but make results reproducible and auditable.
- Legitimate venue interruptions are tested as real market conditions rather than removed, while local acquisition failures cannot masquerade as calm markets.
- The policy is shared by static and later adaptive strategy families; adaptive features and timers may not bridge a gap with invented inputs.

#### Declined alternatives

- **Interpolate or forward-fill short gaps:** convenient for continuous indicators but invents prices, volume, and potentially fill opportunities; even a short gap can cross a rung or stop boundary.
- **Drop affected days or intervals:** changes regime and path-dependent inventory exposure and can systematically remove difficult market conditions.
- **Permit gaps below a percentage threshold:** a quantity-only tolerance ignores location and materiality; one missing interval at a crash or order touch can matter more than many quiet intervals.
- **Operator waiver after reviewing results:** creates outcome-dependent data selection and weakens the locked-holdout guarantee.

### Tiered fidelity with full high-fidelity holdout replay

Selected by the operator on 2026-07-15: use inexpensive one-minute evidence across the complete historical program, but require the one frozen finalist to survive a full event-sequenced replay of the entire locked holdout and an exact replay of captured paper evidence. Research compute and storage are separate from the minimum always-on trading node.

#### Historical evidence tiers

1. **Complete five-year minute tier.** Every development fold and the 12-month locked holdout uses quality-approved one-minute candles with the accepted conservative candle fill policy. This is the common baseline for search, rolling walk-forward, expanding sensitivity, regime analysis, and holdout comparison.
2. **Development escalation tier.** Before the holdout is exposed, shortlisted candidates are evaluated on quality-approved one-second candles and trade/aggregate-trade replay across declared difficult and representative development periods. These visible results are development evidence used to expose intrabar ambiguity, execution-model sensitivity, and defects before the candidate and gate are frozen.
3. **Full locked-holdout event tier.** The single frozen candidate is evaluated across all 12 holdout months using complete quality-approved one-second candles and the frozen Binance raw-trade or aggregate-trade source. Selecting only days with many fills, attractive performance, unusual volatility, or convenient data size is prohibited.
4. **Captured paper tier.** The qualifying paper run records the production market evidence needed by its decisions and execution model: trades, best bid/offer, relevant shallow depth, market gaps, canonical timers, order decisions, simulated acknowledgements/fills, liquidity-budget changes, accounting, reconciliation, and risk transitions. The retained event stream must reproduce the paper decisions, domain state, and simulated execution results exactly under deterministic replay.

The exact trade source, normalization version, event ordering, simulator version, venue rules, fees, latency assumptions, post-only treatment, fill policy, costs, random seeds, dataset manifests, candidate configuration, and thresholds are frozen before holdout processing. Minute and event-level holdout analyses are one **sealed holdout evaluation bundle**: intermediate results are not exposed and both are released together. This prevents a minute result from being used to alter the candidate before event replay, or vice versa.

If complete quality-approved one-second and selected trade evidence do not cover the entire declared holdout, the full-replay gate does not pass. The operator may continue labelled research, but cannot substitute selected available days after seeing results. Qualification requires a different eligible candidate/symbol or a genuinely eligible chronological holdout declared under the locked-holdout rules.

#### Conservative historical execution boundary

- One-second candles reduce intrabar uncertainty but do not themselves prove trade order, maker status, queue position, or execution.
- Trade replay without historical book evidence uses the already accepted no-depth promotion policy: the simulated order must first be acknowledged as resting; later market evidence must trade strictly through its limit; at-price touches do not fill; eligible volume is capped at 5%, cannot be reused among orders, and produces only source-supported partial quantity.
- Historical trades alone never establish that a `LIMIT_MAKER` order would have been accepted or where it stood in queue. Any placement whose maker eligibility is not established uses the frozen adverse post-only uncertainty rule rather than being assumed successfully resting.
- No favorable price improvement, hidden liquidity, cancellation priority, or queue advancement is inferred. More optimistic variants remain labelled sensitivity evidence and cannot replace the promotion result.
- One-second candles act as an independent coverage and price/volume consistency cross-check against the selected trade source. A decision-material conflict is a dataset-quality failure, not a choice of whichever source produces more profit.
- The one-minute conservative result and the event-replay result must each pass their mandatory thresholds. A favorable result at one fidelity cannot compensate for failure at another, and the accepted one-percentage-point return/drawdown parity band below limits material disagreement.

#### Paper capture and replay boundary

Paper trading provides evidence unavailable in normal public historical archives: observed best bid/offer, targeted depth, reception timing, continuity gaps, post-only eligibility inputs, and the exact execution-model state. It still cannot prove that a real Binance order would have received the identical queue position or fill.

For every qualifying paper interval:

- the market evidence that influenced a decision or simulated fill is durably admitted before the resulting decision batch;
- gaps and dropped/late inputs remain explicit instead of being reconstructed silently;
- the paper simulator journals queue-ahead state, non-reusable liquidity consumption, partial fills, and every reason for accepting or refusing a simulated fill;
- replay from the initial immutable state produces exact canonical decisions, state hashes, simulated order outcomes, accounting postings, risk transitions, and final projections;
- capture completeness and replay equality are promotion gates; detailed retention and alert thresholds remain owned by the observability specification.

#### Compute and storage placement

Full five-year research and the 12-month event replay are batch workloads. They may run on the operator's workstation, compressed local/Blob archives, or temporary scale-up/scale-out Azure research compute that is stopped after use. The minimum always-on Azure deployment needs only the resources required for online ingestion, paper/live decisions, journal durability, reconciliation, monitoring, and bounded replay/repair; it must not be sized to run the full historical search continuously.

Promotion datasets, raw source objects, checksums, normalized Parquet, manifests, sealed outputs, code/build identity, and replay fingerprints remain retained according to the later retention policy so the evidence can be regenerated without keeping expensive compute active.

#### Example

A one-minute candle crosses a buy rung and its paired sell in the same interval. The minute baseline applies adverse intrabar ordering and cannot award both favorable fills. In full holdout replay, one-second candles refine the timing and aggregate trades establish the observed trade sequence. The buy becomes eligible only after its simulated resting acknowledgement and fills only from later strict trade-through volume under the 5% non-reusable cap. Because no historical book proves queue priority, an at-price trade does not fill it. During paper operation, captured best-bid/offer and shallow depth can initialize and evolve an explicit simulated queue; replay must reproduce the same queue consumption and partial fill exactly.

#### Consequences

- The final holdout replay is materially more expensive than minute-only testing, but it is bounded to one frozen candidate and one year rather than every research trial over five years.
- Processing the entire holdout prevents outcome-dependent selection of favorable “interesting” days.
- Minute and event replay can legitimately differ; the differences become visible model-risk evidence rather than being hidden behind one preferred result.
- Exact paper replay validates implementation parity and evidence capture, while the later real-money cap remains necessary because paper execution is still simulated.
- Research cost does not force a permanently larger Azure VM or weaken live safety deadlines.

#### Declined alternatives

- **Minute candles only:** inexpensive but too ambiguous for maker-order sequencing, partial fills, post-only behavior, and closely spaced rung cycles.
- **High-fidelity replay only on selected holdout days:** cheaper but permits conscious or accidental favorable-window selection and misses path-dependent inventory between samples.
- **Event replay for every candidate across all five years:** maximizes detail but wastes compute before cheap screening and adds little value relative to a tiered funnel.
- **Assume exact historical queue position from trades:** produces false precision because trades do not reveal the full resting queue or the hypothetical order's priority.
- **Use the always-on Azure node for all research:** couples live availability and cost to batch throughput and creates avoidable resource contention.

### Cross-symbol validation unit

Selected by the operator on 2026-07-15: cross-symbol robustness validates the strategy family and its complete selection procedure, while promotion authorizes one symbol-specific immutable configuration. Literal price bounds, quantities, and venue-rounded values are not transplanted between assets.

#### Three distinct validation objects

- The **strategy family** defines the static grid semantics shared across symbols: arithmetic/geometric spacing, bootstrap, pairing, sizing-policy semantics, lifecycle, accounting, risk integration, and execution behavior.
- The **strategy selection procedure** defines the frozen data eligibility, scale-normalized search ranges, parameter-generation rules, rolling/expanding evaluation, costs, objective, candidate-selection rule, risk ceilings, and thresholds applied independently to each symbol.
- A **symbol-specific candidate** is the immutable result for one market, with its own absolute bounds, rung prices, venue rules, quantities, fee observations, stop placement, datasets, and activation evidence.

Cross-symbol evidence asks whether the same declared research procedure can identify viable candidates on several eligible markets. It does not ask whether one candidate's literal prices can trade another asset.

#### Rules

- The robustness-symbol universe, eligibility rules, panel-selection rule, parameter normalization, and pass thresholds are frozen before performance inspection under that experiment.
- Percentage, volatility-relative, capital-relative, and other scale-free parameters use the same allowed ranges and selection logic where the domain meaning is shared. Symbol-specific absolute prices, tick/step sizes, minimum notionals, fees, spread, liquidity, and initial activation state are observed inputs, not hand-tuned exceptions.
- Every symbol is trained and activated independently at each fold boundary with no orders, inventory, state, or future data carried from another symbol or partition.
- Every tried symbol, candidate, retry, manually inspected variant, changed universe, and symbol-specific exception is included in the declared search-family and multiple-testing record.
- Cross-symbol procedure results are development evidence. They may be used to select and freeze the one proposed MVP symbol and candidate, but that choice occurs before the proposed symbol's locked holdout is exposed.
- Only the chosen symbol-specific candidate proceeds through its sealed 12-month holdout bundle, qualifying paper run, and manual first-live approval. Other panel symbols do not receive trading authority.
- Profit on another symbol cannot compensate for a failed mandatory gate, risk breach, unexplained difference, or negative required result on the proposed live symbol.
- A later attempt to promote another symbol creates its own candidate evidence bundle and must satisfy the then-current gates; it does not inherit the first symbol's holdout, paper, or live authorization.

#### Example

The shared procedure may search geometric rung spacing as percentages of a symbol's activation price and size each run inside the same `250 USDT` research envelope. It can produce BTC/USDT bounds of `90,000–110,000` and ETH/USDT bounds of `4,000–5,000`, then round each through its own venue-rule observation. Requiring ETH to use BTC's literal bounds would be invalid; quietly giving ETH a wider search range after seeing weak results would also be invalid because it changes the declared selection procedure and trial family.

#### Consequences

- Evidence tests whether the research method generalizes while keeping the actual live configuration operationally precise.
- Scale-normalized parameterization becomes an architectural requirement for reusable search logic, but venue validity and absolute risk remain symbol-specific.
- Selecting the proposed live symbol from development evidence is legitimate; selecting it by comparing locked-holdout outcomes is prohibited.
- The number, composition, and required pass count of the robustness panel are a separate decision under this validation ticket.
- Later adaptive strategies may reuse this validation structure, but they remain separate strategy search families with their own parameterization and evidence.

#### Declined alternatives

- **Test only the proposed symbol:** cannot distinguish a reusable grid-selection process from symbol-specific luck.
- **Transplant one literal configuration across symbols:** ignores different price scales, volatility, liquidity, filters, fees, and activation conditions.
- **Pool all symbols into one result:** allows strong markets to hide a failed symbol and destroys per-market risk visibility.
- **Hand-tune unrelated ranges and rules per symbol:** changes the procedure after observing outcomes and makes “cross-symbol robustness” non-reproducible.
- **Promote every passing panel symbol:** expands the one-symbol MVP scope and multiplies operational risk without separate holdout and paper evidence.

### Frozen five-symbol robustness panel

Selected by the operator on 2026-07-15: the development experiment uses exactly five predeclared eligible Binance Spot symbols and requires the same four or more—including the proposed live symbol—to pass both rolling-primary and expanding-window procedure validation. The fifth member remains visible when economically negative and cannot be replaced after outcomes are known.

#### Eligibility

A symbol is eligible for the panel only when all of the following are established before strategy-performance inspection:

- it is a Binance Spot market quoted in `USDT` and is currently available for ordinary Spot trading when the experiment manifest is frozen;
- it has at least 60 consecutive quality-approved calendar months for the declared historical profile, with every development fold supported by the required minute evidence;
- its venue rules permit the fixed research capital and order-size profile without systematic minimum-notional, quantity-step, price-tick, permission, or maximum-order violations;
- its development history establishes sufficient persistent quote volume for the conservative participation policy rather than only one recent liquidity burst;
- its base asset is not designed to remain pegged to the quote asset or another currency, is not a leveraged/rebalancing token, and is not a duplicate wrapper or representation of substantially the same economic exposure already selected for the panel;
- its source lineage, symbol identity, listing history, redenominations, migrations, and relevant venue-rule changes can be represented without unexplained discontinuity.

A later delisting, restriction, data correction, or eligibility failure invalidates operational promotion of that symbol even if its historical strategy result was positive.

#### Deterministic panel selection

- Build the complete eligible universe using the frozen eligibility rules; do not begin with preferred coin names.
- Rank eligible symbols by the 10th percentile of their monthly median daily quote volume across the 48 development months. This favors persistently tradable markets over a high average dominated by a few bursts and uses no holdout performance.
- Break exact ranking ties by canonical symbol identifier.
- Select the first five after applying the non-peg, non-leveraged, non-duplicate-exposure rules. The selected identities, all excluded identities and reasons, source values, formula version, and ordering are part of the experiment manifest.
- Current trading status and current venue-validity checks are operational eligibility gates, not strategy-profit inputs. A symbol cannot be added merely because its backtest looks good or removed because its grid result looks poor.
- If fewer than five eligible symbols exist, the five-symbol first-live robustness gate does not pass; the panel is not silently reduced.

The exact five symbol names are intentionally produced by the versioned manifest from then-current authoritative eligibility evidence. Hard-coding today's preferred assets would make later reproduction and venue changes ambiguous.

#### Panel pass

For each symbol, concatenate its eight independently activated three-month walk-forward test results without pooling assets or accounting across symbols. Evaluate rolling primary and expanding sensitivity separately under the same frozen costs and conservative fill policy.

The panel passes only when:

- the proposed live symbol has positive net flow-adjusted total result in both its aggregated rolling-primary and expanding-sensitivity development results;
- the same set of at least four of the five symbols has positive net flow-adjusted total result under both analyses;
- the five-symbol median net result is positive under each analysis;
- no symbol has a hard accounting violation, unexplained decision-material difference, unbounded obligation, asset-conservation failure, or breach of the terminal loss boundary;
- all failures, terminal conditions, range exhaustion, negative intervals, and inactive periods remain included in the symbol result;
- the proposed live symbol subsequently passes every separate locked-holdout, high-fidelity replay, risk, paper, and manual-approval gate on its own.

“Positive” here means greater than zero after all declared fees, spread, slippage, post-only rejection, conservative fills, terminal disposal, and other costs, expressed through the accepted accounting model. Later metric decisions may impose a stronger minimum edge, uncertainty, drawdown, and activity threshold; they cannot weaken this strict-positive floor.

The permitted fifth economic failure is not ignored. It is a falsification result used in reports and sensitivity analysis. It may be economically negative, range-exhausted, or terminally stopped within an independently stricter candidate stop, but it may not breach the system's terminal loss boundary or violate correctness/safety invariants.

#### Example

The frozen ranking produces symbols A–E. A, B, C, and D are positive under both rolling and expanding analyses; E is negative but remains within every risk and accounting boundary. If A is the proposed live symbol, the panel passes and A may proceed to its locked holdout. If rolling passes A–D but expanding passes only A, B, C, and E, the panel fails because there is no same set of four; the result suggests sensitivity to training-window construction. Replacing D with a sixth profitable symbol after seeing this outcome is prohibited.

#### Consequences

- Five symbols materially reduce single-market dependence while keeping five-year minute research practical.
- A four-of-five rule tolerates one structurally unsuitable market without allowing nearly half the panel to fail.
- Requiring the same four under both window methods is stricter than separately counting different winners and exposes cutoff sensitivity.
- The deterministic liquidity rule reduces operator cherry-picking, while the exclusion rules avoid padding the panel with pegged or duplicate exposures.
- Only one symbol incurs the full event-level holdout and qualifying-paper cost for the MVP; panel breadth does not authorize multi-symbol live trading.

#### Declined alternatives

- **Two or three symbols:** too easy for a common market episode or highly correlated pair to create apparent generality.
- **Require only three of five:** permits 40% of the declared panel to fail and provides weak falsification evidence.
- **Require all five:** one legitimately unsuitable market can reject an otherwise repeatable method and encourages hidden eligibility manipulation.
- **Different four winners per analysis:** allows rolling and expanding evidence to conceal instability in which symbols actually work.
- **Operator-selected favorite symbols:** permits familiarity, reputation, or observed returns to bias the panel.
- **Replace the negative member:** turns a fixed robustness panel into an open-ended search for favorable outcomes and must instead count as a redesigned experiment.

### Deterministic nine-regime matrix and stress overlays

Selected by the operator on 2026-07-15: every scored UTC day receives one trend label and one volatility label derived only from information available before that day. Their cross-product creates nine mutually exclusive market-regime cells. Separate stress-event overlays may overlap any cell. Labels are evaluation metadata and cannot alter strategy decisions, orders, sizing, lifecycle, or risk state.

#### Daily regime observation

For each symbol, calculate the label at the start of UTC day `D` from quality-approved daily closes strictly before `D`:

- Let `R90` be the log return from the close 90 days before `D` to the close immediately before `D`.
- Let `RV90` be the sample standard deviation of the intervening daily log returns multiplied by `sqrt(90)`.
- Define normalized trend score `T = R90 / RV90`. If `RV90` is exactly zero, define `T = 0` rather than dividing by zero and retain the zero-volatility observation.
- Label **downtrend** when `T <= -1`, **sideways** when `-1 < T < 1`, and **uptrend** when `T >= 1`.
- Let `V30` be the sample standard deviation of the 30 daily log returns immediately before `D`, annualized by `sqrt(365)`.
- Label volatility **low** below the applicable training distribution's 33rd percentile, **normal** from the 33rd through the 67th percentile, and **high** above the 67th percentile. Exact quantile interpolation and equality rules are versioned in the experiment manifest; equality at the lower boundary enters normal and equality at the upper boundary remains normal.

The resulting cells are:

| | Low volatility | Normal volatility | High volatility |
| --- | --- | --- | --- |
| Downtrend | down/low | down/normal | down/high |
| Sideways | sideways/low | sideways/normal | sideways/high |
| Uptrend | up/low | up/normal | up/high |

Daily labels partition calendar time, not just times when an order fills. Results therefore retain inactive, range-exhausted, fully invested, quote-heavy, and terminal periods rather than attributing only successful cycles.

#### Threshold governance and leakage prevention

- For each development fold and symbol, volatility quantiles and any distribution-derived stress thresholds are fitted only from that fold's training window, then frozen for its following test window.
- Rolling and expanding analyses use their own training observations but label the same test dates independently; label differences caused by different training distributions are reported rather than silently reconciled.
- The proposed candidate's locked holdout uses thresholds frozen from the complete 48-month development dataset before holdout exposure. It cannot estimate quantiles from the holdout itself.
- The full event-level holdout replay reuses the same daily labels as its minute evaluation; higher-fidelity data may add stress evidence but cannot retrospectively change the trend/volatility cell.
- Pre-boundary warm-up may supply the required 90 prior closes without producing trades or scored results. A day without sufficient quality-approved lookback is unclassified and cannot be silently assigned to sideways/normal; insufficient classified coverage is handled by the regime coverage gate.
- Regime classification code, parameters, source manifests, and per-day labels are fingerprinted. Changing a threshold, lookback, annualization, boundary, or quantile algorithm changes the experiment and trial family.

#### Stress-event overlays

Overlays are non-exclusive diagnostic tags attached only when their required evidence exists:

- **Sudden crash** or **sudden rebound:** the prior-to-current daily return is at or beyond the fold-training 1st or 99th percentile respectively.
- **Range exhaustion:** the canonical grid is below or above its configured outer rung under the accepted range-exhausted semantics.
- **Volume drought:** daily quote volume is no more than 25% of its trailing 30-day median, using only prior and current observed volume and preserving any zero-trade/venue-interruption distinction.
- **Spread stress:** observed spread in basis points is at or above the frozen 95th percentile of the eligible prior detailed-data calibration distribution.
- **Depth stress:** immediately executable displayed depth inside the declared price band is at or below the frozen 5th percentile of its eligible prior calibration distribution or below the amount required by the relevant bounded obligation.
- **Venue interruption** and **source-data gap:** use the explicit data-quality classifications and are never inferred from a flat price alone.
- **Stop-loss/terminal disposal:** tags the trigger and disposal interval from canonical lifecycle evidence.

Spread and depth overlays are absent—not false—where minute or historical trade data contains no book evidence. Their thresholds for paper/live evidence are frozen before the qualifying interval or derived only from a separately declared non-qualifying calibration interval. Missing book evidence cannot be treated as normal liquidity.

#### Required regime report

For every symbol, fold, analysis type, holdout fidelity, and paper interval, report at least:

- calendar and classified days, active-grid time, capital exposure, committed inventory, average and maximum grid inventory;
- rung fills, paired cycles, partial fills, rejected placements, fees by asset and quote valuation, terminal-disposal cost, and range-exhausted time;
- flow-adjusted total result, realized cycle result, unrealized result, conservative liquidation equity change, drawdown, and terminal/loss-guardrail events;
- results and counts by nine regime cells and by each overlapping stress tag;
- observed sample counts and explicitly labelled uncertainty limitations; no bootstrap confidence interval is a mandatory MVP promotion result under the accepted no-resampling-gate decision below;
- explicit unclassified or unavailable observations and the reason they did not receive a label.

The matrix describes conditional behavior; it does not permit nine separately tuned configurations in the static-grid MVP. An adaptive strategy that uses a regime label for decisions would be a new strategy family requiring independent validation.

#### Example

At the start of a holdout day, the preceding 90-day normalized return is `-1.3`, so the day is downtrend. Its trailing 30-day volatility is above the frozen development 67th percentile, so it is down/high. A 12% fall that day also receives the sudden-crash overlay; if price passes the lower outer rung, the later interval receives range-exhaustion too. The static grid does not see these analytical labels and cannot cancel buys merely because the report calls the day down/high. Its actual decisions remain governed only by the immutable strategy and safety rules.

#### Consequences

- The matrix separates trend direction from volatility, both of which materially affect a long-inventory grid.
- Training-derived thresholds adapt the analytical scale to each symbol without using future test or holdout outcomes.
- Stress overlays preserve rare operationally important scenarios that would be diluted in broad regime averages.
- Some nine cells may have limited observations; the next decision sets minimum coverage and pass rules rather than pretending every estimate is equally reliable.
- Keeping labels outside strategy inputs preserves the static MVP semantics and prevents hidden adaptive behavior.

#### Declined alternatives

- **Label regimes using the full five years:** gives stable quantiles but leaks test and holdout distributions into their own classification.
- **Use calendar bull/bear dates chosen by the operator:** is subjective, difficult to reproduce, and susceptible to outcome-aware selection.
- **Only trend or only volatility:** misses materially different grid behavior such as sideways/high versus sideways/low conditions.
- **Require one exclusive stress regime:** loses overlapping facts—for example, a crash can also be down/high, range-exhausted, and liquidity-stressed.
- **Feed labels into the MVP strategy:** silently converts the accepted static grid into an adaptive strategy family.
- **Treat missing spread/depth as normal:** converts absent evidence into a favorable liquidity assumption.

### Regime coverage and breadth gate

Selected by the operator on 2026-07-15: promotion requires sufficiently broad and partly profitable regime coverage, but does not require an unhedged Spot inventory grid to profit in every adverse regime. Overall profitability, intended-environment profitability, concentration, coverage, and bounded adverse-regime survival are separate non-compensating checks.

#### Non-duplicated primary regime path

For the proposed symbol, the primary regime-breadth calculation concatenates:

1. the eight rolling-primary development test folds, each independently activated; and
2. the full event-replay result for the 12-month locked holdout.

The minute holdout and expanding development analyses cover overlapping dates and therefore are not added again to regime profit or day counts. They remain separate mandatory results that must pass overall and must publish their own regime reports. This prevents double-counting the same market day merely because it was processed at two fidelities or under two training-window methods.

#### Proposed-symbol coverage

Across the non-duplicated primary regime path:

- each of downtrend, sideways, and uptrend must contain at least 60 classified calendar days;
- each of low, normal, and high volatility must contain at least 60 classified calendar days;
- every one of the nine cross-product cells must contain at least 20 classified calendar days;
- a calendar day counts once regardless of the number of fills, orders, or overlapping stress tags;
- unclassified days, source-data gaps, and unavailable book evidence do not count toward the applicable minimum.

If exposure is zero or the run is range-exhausted on a classified day, the day still counts as observed regime coverage and its zero/negative/retained-inventory economics remain included. Coverage measures the candidate's path through market conditions, not only active profitable trading.

#### Proposed-symbol breadth and survival

The proposed symbol passes the regime breadth gate only when:

- at least five of the nine sufficiently covered cells have strictly positive net flow-adjusted total result after every declared cost;
- the three sideways cells combined have a strictly positive net result because sideways movement is the grid family's intended economic environment;
- rolling development, expanding sensitivity, minute holdout, and event-replay holdout are each strictly positive overall under their own non-duplicated result calculation;
- no individual regime cell contributes more than 70% of the sum of all positive cell results on the primary regime path;
- every negative cell remains within the immutable daily-loss, run-drawdown, stop-loss, capital, inventory, and order limits applicable to its independent runs;
- no cell or stress overlay contains a terminal-loss-boundary breach, hard accounting violation, unexplained decision-material reconciliation difference, unbounded obligation, asset-conservation failure, or unsafe recovery;
- range exhaustion, a correctly triggered configured stop, retained inventory, or a negative down/high cell remains visible and cannot be reclassified or removed to satisfy the gate.

The 70% concentration denominator is the sum of positive cell results, not net total result after negative cells. A zero-result cell is not positive. More demanding statistical confidence and minimum economic-edge thresholds may strengthen these rules later; they cannot make a negative cell positive by rounding or allow overall profit to waive a correctness failure.

#### Panel coverage

Across the five-symbol rolling-development test dates, counting each symbol-date once:

- every regime cell must contain at least 120 symbol-days;
- every cell must be observed in at least three different panel symbols and four distinct test folds;
- rolling versus expanding processing of the same symbol-date does not create a second coverage observation;
- coverage insufficiency blocks first-live promotion and is reported as insufficient evidence, not as a failed or successful return estimate.

The panel's previously selected same-four-symbol profit rule remains independently mandatory. Regime pooling is used only to establish that relevant conditions were observed; it does not allow one symbol's regime profit to offset another symbol's failure.

#### Stress-event acceptance

Naturally observed stress overlays are not required to be profitable. Each must instead demonstrate the expected deterministic safety, accounting, lifecycle, evidence, and replay behavior. At minimum, observed events must retain their inputs and consequences, remain within approved economic limits, and replay exactly at the domain boundary.

An important stress type not naturally observed with sufficient evidence does not disappear from verification. The verification specification must provide deterministic replay fixtures or fault-injection acceptance cases for crashes/gaps, range exhaustion, stale or missing evidence, post-only rejection, partial/late fills, liquidity exhaustion, stop-loss disposal, and recovery. Synthetic fault cases validate behavior but do not count as historical profitability or natural regime coverage.

#### Example

The primary proposed-symbol path has six positive cells, including a positive sideways aggregate. Down/high is negative during two sharp declines but stays within drawdown and stop limits; no invariant fails. Sideways/normal produces 62% of the sum of positive cell results, so concentration remains below 70%. The panel has at least 120 symbol-days for each cell across three symbols and four folds. This may pass. If sideways/normal instead supplies 82% of positive cell results, or down/low has only 12 proposed-symbol days, the gate fails even when total return is positive because the evidence is too concentrated or incomplete.

#### Consequences

- The strategy may lose money in a strong adverse regime without being misrepresented as universally profitable, provided the loss is bounded and the overall/breadth gates pass.
- Sideways profitability is mandatory because a grid without evidence of edge in its intended environment lacks a coherent economic case.
- Coverage thresholds may reject a five-year sample whose realized regime mix is unusually narrow; this is preferable to claiming robustness from absent evidence.
- Concentration limits reduce dependence on one favorable cell while still allowing real market regimes to have unequal duration and contribution.
- Historical stress profitability and safety correctness remain distinct: a crash need not make money, but the system must respond safely and explainably.

#### Declined alternatives

- **Require all nine cells positive:** unrealistic for unhedged Spot inventory in strong declines and encourages distorted regime definitions.
- **Require only total historical profit:** allows one favorable regime to hide broad fragility and adverse inventory behavior.
- **Ignore cells with no trades:** removes range-exhausted and inactive exposure periods from the economic story.
- **Pool minute and event results as extra observations:** double-counts the same holdout days and creates false sample size.
- **Treat insufficient coverage as neutral:** converts absence of evidence into evidence of robustness.
- **Require observed stress events to be profitable:** confuses economic edge with the requirement to survive and recover correctly.

### Predeclared staged hybrid parameter search

Selected by the operator on 2026-07-15: broad exploration uses a deterministic seeded Sobol design within frozen normalized parameter domains, followed by a predeclared local grid around stable training-performance plateaus and exact development evaluation of a bounded finalist set. Holdout data is never searched, refined, or used to decide which trials continue.

#### Search manifest

Before any performance trial, the immutable search manifest fixes:

- strategy-family semantics and version;
- each continuous, integer, ordinal, and categorical parameter, its unit/normalization, legal range or values, transformation, inclusivity, and venue/risk constraints;
- categorical strata such as arithmetic versus geometric spacing rather than pretending categories have continuous distance;
- Sobol generator/implementation version, scrambling rule, seed, dimensional mapping, sample budget, and deterministic duplicate handling;
- structural-validity rules applied before simulation;
- objective, hard gates, minimum activity requirements, plateau definition, clustering/distance rule, number of eligible plateaus, neighborhood widths, local-grid resolution, tie-breakers, and stage budgets;
- training partitions, fidelity per stage, costs, fill policy, venue-rule observations, stopping rules, checkpoint behavior, and finalist count;
- the treatment of invalid configurations, duplicate generated points, failed trials, retries, manual inspection, and every statistical family identity.

Changing any item after inspecting performance creates a new experiment/search family and cannot reuse an unconsumed-holdout claim from the prior frozen family when the exposed evidence could inform the change.

#### Stage 0 — structural admission

Map every generated normalized point deterministically to source-exact domain values, categorical choices, and venue-valid candidate values. Reject before market simulation any configuration that cannot satisfy immutable semantics, strict activation eligibility, positive net cycle margin, capital/inventory/order ceilings, fee coverage, venue filters, or risk-compatible stop construction.

Every generated point receives an identity and an admission result. Exact duplicate executable configurations created by discrete mapping or venue rounding are evaluated once and linked to all generating points; conflicting mapping is an error. Structurally invalid points are reported separately from performance-tested trials and cannot be quietly replaced with hand-selected points.

#### Stage 1 — broad Sobol exploration

- Run a seeded scrambled Sobol sequence in each declared categorical stratum. A Sobol design is a deterministic low-discrepancy sequence that spreads points across a multi-dimensional range more evenly than ordinary random sampling.
- Use the frozen 512-point power-of-two sample count per stratum so the design retains its balance properties.
- Evaluate admitted unique candidates using the minute training data and frozen conservative fill/cost model for that fold only.
- Do not stop a candidate because an interim score appears poor. A canonical terminal condition or hard invariant may end its run according to normal semantics, but its complete terminal result remains in the trial record.
- Failed execution, missing output, timeout, or resource error is not a bad economic score and not a free replacement draw. It is retried only under the predeclared infrastructure-retry policy with the same trial identity and inputs; unresolved failure makes the experiment incomplete.

#### Stage 2 — stable-plateau refinement

Apply the frozen objective and hard gates to training results only. Select up to four distinct high-ranking broad-search seeds per stratum, generate each seed's declared 51-point local neighborhood, and use the frozen bounded local-stability proof to decide whether that neighborhood is a **performance plateau**. Refinement resolution and clipping/deduplication are deterministic.

A high-scoring isolated spike whose local neighborhood lacks required viable support is not a plateau and cannot produce a finalist merely because it is the global maximum. This local proof replaces a separate broad-point clustering or surrogate-model stage.

#### Stage 3 — exact development finalists

- Re-evaluate the bounded finalist set on the declared one-second/trade development escalation periods and all mandatory sensitivity scenarios.
- Use the same canonical strategy, accounting, risk, and execution contracts; only the evidence fidelity changes.
- Apply the frozen candidate-selection rule to choose the fold candidate and, after all development analysis, the one proposed symbol-specific candidate.
- Freeze its complete configuration and evaluation bundle before creating the sealed holdout evaluation bundle.
- The locked holdout produces pass/fail evidence only. It cannot trigger a new local grid, alternative seed, runner-up substitution, or Bayesian/manual follow-up within the same qualification attempt.

#### Trial-family and operational rules

- Every performance-evaluated unique configuration, spacing stratum, symbol, fold, rolling/expanding variant, sensitivity, retry with changed inputs, refinement, and manually inspected result belongs to the declared trial history.
- Generated but structurally rejected and exact duplicate points remain auditable; they do not masquerade as independent performance observations.
- Resume after interruption uses persisted stage state, generator index, seed, trial identity, inputs, and result fingerprints. It may not restart a stage with a favorable new sample.
- Re-running identical inputs to verify determinism retains one economic trial identity while recording every execution attempt and equality result. Any changed input creates a new trial.
- UI-driven manual experiments remain available as labelled exploration. They cannot enter promotion evidence unless they were already generated by the frozen procedure; inspecting them informs a new search family.
- Trial counts and selection exposure feed the accepted DSR multiple-testing credibility gate. A “trust score” or stronger result elsewhere cannot erase undeclared trials.

#### Codebase consequence

The canonical Cartesian search remains useful for bounded local refinement, and the legacy SaaS broad/medium/exact job progression remains useful UX inspiration for persisted stages, progress, comparison, and resume. Neither existing implementation is the accepted selection procedure: canonical code needs Sobol design, immutable manifests, plateau/stage rules, complete trial identity, and resume; legacy code must remove full-period ranking leakage and proxy-engine finalist selection.

#### Example

For geometric spacing, a fixed Sobol design generates normalized lower distance, upper distance, rung count, quote size, and risk-compatible stop parameters. Several points map to the same executable rung set after tick rounding; the manifest evaluates that set once but retains every mapping. The best raw training return is an isolated narrow spike, while a slightly lower region has many neighboring configurations with similar positive results and bounded drawdown. Only the stable region seeds the predeclared local grid. After exact development replay, one candidate is frozen. If its holdout fails, the second-best candidate cannot be tried on that same exposed holdout.

#### Consequences

- Broad coverage is substantially cheaper than an exhaustive high-dimensional Cartesian product while remaining deterministic and reproducible.
- Plateau refinement favors parameter stability over a fragile single optimum and makes later live drift less likely to invalidate the apparent edge immediately.
- Manifests and complete trial history add implementation work but prevent hidden seed changes, retries, and UI tuning from escaping multiple-testing accounting.
- The search remains compatible with local/temporary research compute and resumable jobs without enlarging the always-on trading node.
- Search budgets, searchable parameters, objective, plateau thresholds, and the DSR multiple-testing method are explicit frozen decisions recorded below; none may be changed after performance inspection within the same family.

#### Declined alternatives

- **Exhaustive Cartesian search:** simple and currently available, but grows combinatorially, depends strongly on arbitrary step alignment, and spends equal compute on obviously unpromising high-fidelity combinations.
- **Bayesian optimization for the MVP:** can reduce expensive trials, but adaptive priors/acquisition history complicate reproduction, family accounting, and leakage review before the validation process is mature.
- **Manual iterative tuning:** useful for learning and UI exploration, but creates unbounded human-guided trials and outcome-dependent ranges; it is non-promotion evidence.
- **Pure random search:** easier than Sobol but has uneven coverage and seed variance for the same budget.
- **Refine only the single best point:** encourages narrow overfit peaks and hides local parameter instability.
- **Continue searching after holdout failure:** converts the locked holdout into development data and requires a genuinely later eligible holdout for a redesigned family.

### Bounded strategy-only search authority

Selected by the operator on 2026-07-15: the search may vary only genuine static-grid strategy choices. Values required by those choices are derived mechanically, while evidence assumptions, accounting semantics, execution behavior, and independent safety authority remain fixed and cannot be optimized for profit.

#### Searchable strategy parameters

The first MVP search contains these dimensions only:

1. **Lower-bound distance:** positive percentage distance from the observed activation price to the lower configured bound.
2. **Upper-bound distance:** positive percentage distance from the observed activation price to the upper configured bound, independently allowing an asymmetric static range.
3. **Rung count:** total configured grid prices including both bounds, under the canonical rung-count meaning and subject to proof that every lifecycle state remains within the operational order ceiling.
4. **Spacing family:** arithmetic and geometric are separate categorical strata; both are searched under equivalent rules, and geometric wins an otherwise exact selection tie as the declared default.
5. **Fixed quote principal per rung:** intended quote principal for each buy obligation before venue quantity rounding and fees, greater than zero and no more than the immutable `20 USDT` buy-principal ceiling.
6. **Global stop-loss placement:** exact adverse market-price floor below the lower grid bound, admitted only when maximum-inventory conservative terminal disposal at that price preserves the required terminal-equity floor plus stop-price safety buffer.

For each fold, the activation price is the first eligible observed market price at the independent activation boundary. The percentage distances create absolute bounds around that observation; they do not use a future optimum price. The precise parameter domains and transforms are a separate frozen decision.

#### Mechanically derived values

The following are deterministic consequences of the searched parameters, activation evidence, immutable semantics, venue rules, allocation, and risk profile rather than independent search dimensions:

- absolute lower/upper bounds, rung prices, neighbor distances, and activation-rung relationship;
- venue-rounded price and base quantity for each obligation;
- initial buy/sell rung assignment and number of effective managed orders in every reachable grid state;
- bootstrap acquisition, acquisition fee allowance, backing inventory, initial reservations, and net base received;
- maximum planned inventory, committed inventory/capital, aggregate buy obligations, and uncommitted quote;
- fee coverage and reserve by actual/possible fee asset, rounding residuals, minimum-notional feasibility, and terminal-disposal feasibility;
- exact stop-price safety-buffer result and whether the proposed stop is structurally admissible.

A candidate is structurally rejected if these derivations cannot fit inside the `250 USDT` capital envelope, `20 USDT` buy-principal ceiling, 20-effective-order ceiling, exact allocation coverage, venue filters, fee reserve, inventory limits, or terminal-loss requirements. The search cannot shrink a derived obligation by silently dropping a rung or fee.

#### Fixed evidence and safety values

These are versioned experiment inputs or independent controls and are never optimized:

- accounting, lot provenance, reconciliation, rounding, lifecycle, pairing, bootstrap, range-exhaustion, and stop/disposal semantics;
- conservative candle/event/paper fill rules, resting eligibility, strict trade-through, 5% non-reusable volume participation, queue treatment, post-only retry behavior, latency model, and command-state semantics;
- venue-observed fees and filters plus declared spread, slippage, terminal-disposal, and third-asset conversion costs;
- dataset-quality rules, partitions, regime definitions, fidelity, statistical method, promotion thresholds, and paper requirements;
- capital envelope, live-activation ceiling, maximum buy principal, effective-order ceiling, daily-loss guardrail, run-drawdown guardrail, terminal-equity floor, stop safety buffer, stale/continuity deadlines, and all anomaly/posture transitions;
- compounding, adaptive range movement, global take-profit, short exposure, borrowing, margin, and additional strategies, which remain outside the static non-compounded MVP family.

Conservative assumptions may be varied only as predeclared sensitivity scenarios in the adverse or explicitly labelled direction. A sensitivity value never becomes the selected operating assumption because it yields more profit.

#### Capital comparability

Every candidate is evaluated against the same full `250 USDT` grid capital envelope. When a smaller quote-principal choice leaves more uncommitted quote, that quote remains part of current grid equity and the return denominator; results are not inflated by reporting profit only against capital that happened to trade. Profit does not compound into later rung sizes.

Likewise, a larger rung count or quote principal receives no extra capital. If its worst-case bootstrap, buys, fees, and disposal cannot be funded simultaneously under canonical obligations, it is invalid rather than simulated with implicit leverage or partial allocation.

#### Stop-loss boundary

Stop placement is searchable because it materially changes the static strategy's economic exposure and terminal behavior, but search authority is subordinate to fixed risk authority:

- price must be strictly below the lower grid bound and high enough that the fixed terminal-equity floor plus its required safety buffer remains satisfied under the structural maximum-inventory disposal model;
- the structural maximum-inventory liquidation model must retain the required 2% initial-equity safety buffer above the terminal-equity floor;
- realized simulation still triggers the global stop exactly under canonical semantics, accounts for terminal disposal separately, and includes all costs;
- no candidate may move the terminal-equity floor, safety buffer, disposal band/attempt limits, or drawdown/daily-loss controls.

#### Example

A generated candidate proposes a 12% lower distance, 8% upper distance, 12 geometric rungs, `15 USDT` quote principal, and a stop 4% below the lower bound. At its fold activation price, the engine derives all rung prices and rounded quantities, bootstrap inventory for initial sell obligations, every funded buy, fees, and maximum-inventory disposal. If the combined obligations require `268 USDT`, the candidate is invalid; the engine cannot reduce bootstrap inventory or omit outer buys. If it fits in `250 USDT` but conservative disposal at the stop leaves less than the terminal floor plus 2% initial-equity buffer, its stop is invalid. Neither failure permits raising the capital or loss limit.

#### Consequences

- The optimizer explores the meaningful interaction among range geometry, order density, exposure size, and terminal exit without acquiring authority over the safety envelope.
- Derived obligations stay consistent across backtest, replay, paper, and live because they share one deterministic construction path.
- Fixed envelope accounting makes candidates with different utilization comparable and prevents “return on deployed capital” from rewarding idle-capital omission.
- Searching quote principal and stop placement increases dimensionality and multiple-testing burden relative to a minimal structural search; the staged budget and statistical correction must account for them.
- Later compounding or adaptive behavior requires a separate strategy family rather than adding hidden search dimensions to this one.

#### Declined alternatives

- **Optimize only bounds, rungs, and spacing:** simpler and less prone to overfit, but fixes meaningful exposure-size and stop interactions without validation; retained as a possible sensitivity comparison, not the selected family.
- **Optimize execution assumptions and costs:** selects the simulator rather than the strategy and encourages favorable fee, queue, latency, rejection, spread, or slippage assumptions.
- **Optimize capital and safety limits:** can improve return mechanically by accepting more exposure or loss and violates the independent risk authority.
- **Treat derived obligations as independent parameters:** permits internally inconsistent bootstrap, inventory, reservation, fee, and order states.
- **Report return only on capital used by orders:** rewards smaller utilization by excluding idle allocated assets and makes candidates economically incomparable.

### Balanced static-grid parameter domains

Selected by the operator on 2026-07-15: the first MVP searches bounded ranges intended to cover narrow through moderately wide static grids without spending most of the fixed trial budget on extreme, structurally infeasible plans.

| Parameter | Frozen broad domain | Broad mapping |
| --- | ---: | --- |
| Lower-bound distance from activation | `5%` through `30%` below activation | logarithmic |
| Upper-bound distance from activation | `5%` through `30%` above activation | logarithmic |
| Canonical rung count | integers `5` through `21`, inclusive | uniform discrete |
| Fixed quote principal per rung | `10 USDT` through `20 USDT`, inclusive | uniform linear |
| Stop distance below the lower bound | `2%` through `15%`, inclusive | logarithmic |

Arithmetic and geometric spacing remain separate categorical strata. “Logarithmic” means equal normalized search distance represents equal ratios rather than equal percentage-point differences, providing more resolution among tighter distances while still reaching the wide endpoint. It does not make the live grid adaptive.

These are generator domains, not promises of admissibility. Each point is mapped deterministically, quantized only at declared search and venue rounding boundaries, and structurally checked against activation, adjacent net cycle margin, `250 USDT` capital, fees, backing inventory, 20 effective orders, the `20 USDT` buy-principal ceiling, venue filters, and terminal-loss safety. Invalid and venue-equivalent points remain in the manifested generated count without replacement.

#### Broad coverage is not a fixed-step Cartesian grid

The Sobol stage does not test every possible `1%` or `1 USDT` combination. It maps 512 evenly dispersed normalized points into all five dimensions simultaneously. Fixed increments across every broad range would create a Cartesian product and defeat the accepted bounded search method.

For illustration, even coarse endpoint-inclusive steps of one percentage point for the three distance parameters, one integer rung, and `1 USDT` principal would create:

`26 lower × 26 upper × 17 rung counts × 11 principals × 14 stops = 1,769,768` configurations per spacing stratum.

Across two spacing families, five symbols, eight folds, and two window methods, that becomes `283,162,880` broad configurations before detailed replay or sensitivities. The accepted Sobol budget produces `81,920` manifested broad points for the same evidence structure.

Exact source resolution and the smaller Stage 2 local-neighborhood steps are distinct from the broad ranges and are fixed by the type-aware policy below. They do not use one common increment because percentage distance, integer rung count, and quote principal have different units and economic sensitivity.

#### Example

A Sobol point may map to a lower distance near `7.4%`, an upper distance near `18.6%`, 13 rungs, approximately `16.30 USDT` principal, and a stop near `4.7%` below the lower bound. Another point explores a materially different combination. The venue then applies exact tick, step-size, and notional rules. The search is not limited to integer percentages, nor does it enumerate every decimal combination.

#### Consequences

- Independent lower and upper domains preserve asymmetric grids while applying the same prior coverage to either side.
- Logarithmic distance mapping spends more coverage on economically distinct tighter settings without excluding moderately wide grids.
- The `10 USDT` principal floor stays comfortably above common small-notional behavior while the authoritative venue filter still decides validity; it also avoids consuming trials on very small orders whose fees and rounding dominate.
- The 5–21 rung domain distinguishes configured price levels from effective orders: a 21-rung candidate is admissible only when one activation rung is initially inactive and the deterministic plan proves every reachable state remains at or below 20 effective managed orders.
- A 21-rung candidate whose activation price is not exactly on a configured rung requires 21 initial orders and is rejected. Any other reachable state that could require 21 effective orders also rejects it, even if its initial state happened to fit.
- Values outside these ranges may be explored only as clearly labelled non-promotion research or through a newly frozen search family; favorable development results do not justify silently widening a range.

#### Declined alternatives

- **Narrow conservative domains:** bounds of 8–20%, 7–15 rungs, 12–20 USDT principal, and a 2–8% stop gap reduce structural rejects but may miss stable wider grids.
- **Very broad domains:** bounds of 2–50%, 3–20 rungs, venue-minimum principal through 20 USDT, and a 1–25% stop gap spend substantial fixed coverage on economically dissimilar or infeasible plans.
- **Volatility-relative domains for the MVP:** activation-time volatility multiples may improve scale portability, but add estimator and lookback choices and define a distinct volatility-aware strategy family better validated as a later increment.
- **One fixed increment across all parameters:** confuses different units, generates an impractical Cartesian product, and makes results depend strongly on arbitrary grid alignment.
- **Keep a strict 20-rung ceiling:** simpler but unnecessarily excludes a 21-rung plan that demonstrably maintains one inactive rung and never exceeds the independently accepted 20-effective-order ceiling.
- **Search 22 or more rungs for MVP promotion:** cannot fit the canonical normal-grid occupancy model under the 20-effective-order ceiling and wastes the bounded promotion budget; it belongs only to a separately labelled future scale investigation.
- **Raise the effective-order ceiling:** increases command, reconciliation, rate-limit, recovery, and capital complexity and requires a new risk profile and qualification rather than a parameter-domain amendment.

### Type-aware search resolution and local refinement

Selected by the operator on 2026-07-15: broad Sobol points use small deterministic source resolutions, while stable-plateau refinement uses economically meaningful steps specific to each parameter type. One common increment is prohibited.

#### Broad mapped resolution

- Lower-bound, upper-bound, and stop distances map to source-exact decimals at `0.01` percentage-point resolution after their logarithmic transform.
- Fixed quote principal maps to source-exact decimals at `0.01 USDT` resolution after its linear transform.
- Rung count maps to whole integers from 5 through 21.
- The manifest fixes the exact decimal quantization and tie rule. Venue price and quantity filters are applied only afterward at the declared venue rounding boundaries; they do not rewrite the source search identity.

This resolution does not cause Cartesian enumeration. It merely defines reproducible values for the 512 Sobol points and lets generated points that become venue-equivalent be identified and deduplicated transparently.

#### Local plateau neighborhood

For an admitted plateau representative, define one negative and positive perturbation per dimension:

- lower-bound distance: multiply by `0.90` and `1.10`;
- upper-bound distance: multiply by `0.90` and `1.10`;
- stop distance below the lower bound: multiply by `0.90` and `1.10`;
- canonical rung count: subtract and add one rung;
- fixed quote principal: subtract and add `1 USDT`.

After each perturbation, apply the same declared source resolution, clip to the immutable broad domain, and rerun complete structural admission. A clipped value, duplicate executable plan, invalid candidate, or unavailable direction is retained in neighborhood provenance but does not receive a replacement point.

Evaluate only:

1. the plateau representative;
2. ten legal single-dimension perturbations, two for each of five dimensions; and
3. the forty declared pairwise perturbations, four sign combinations for each of the ten dimension pairs.

The nominal neighborhood therefore contains `1 + 10 + 40 = 51` generated configurations before clipping, rejection, and deduplication, remaining below the accepted 64-per-plateau cap. Three-, four-, and five-way local Cartesian combinations are not generated.

#### Example

A representative with a `10%` lower distance, `18%` upper distance, 13 rungs, `16.30 USDT` principal, and `4%` stop distance receives single-dimension neighbors including `9%`/`11%` lower distance, `16.2%`/`19.8%` upper distance, 12/14 rungs, `15.30`/`17.30 USDT`, and `3.6%`/`4.4%` stop distance. Pairwise neighbors include, for example, 14 rungs together with `17.30 USDT`. It does not evaluate all `3^5 = 243` center/lower/upper combinations.

#### Consequences

- Fine source resolution prevents arbitrary whole-percentage alignment without creating an exhaustive grid.
- Relative steps treat a change around a tight distance differently from the same absolute percentage-point change around a wide distance.
- Integer rung and quote-denominated principal steps stay understandable to the operator and match their economic units.
- Pairwise interactions are checked because range, density, size, and stop placement can interact, while excluding higher-order Cartesian expansion keeps the refinement bounded and explainable.
- Boundary plateaus naturally produce fewer trials; the method never spends unused capacity on outcome-driven extra search.

#### Declined alternatives

- **Fixed additive one-percentage-point distance steps:** simple, but a one-point move changes a 2% stop by 50% and a 15% stop by only 6.7%.
- **One normalized-domain step for every parameter:** mathematically uniform but less interpretable in trading units and still needs special integer mapping.
- **Full `3^5` local Cartesian refinement:** evaluates 243 configurations per plateau, violates the accepted cap, and adds compute and multiple-testing exposure for higher-order combinations without an MVP evidence requirement.
- **Adaptive local step chosen from observed curvature:** can be efficient but makes the search path performance-dependent and adds optimizer complexity that is unnecessary for the first static-grid qualification.

### Bounded local performance-plateau proof

Selected by the operator on 2026-07-15: local refinement itself proves whether a promising broad-search region is stable. The procedure reuses the fixed 51-point neighborhood and adds no clustering library, response surface, or surrogate optimizer.

#### Seed selection and overlap

Within each symbol/fold/window-method/spacing stratum, order broad-search candidates by the accepted lexicographic rule using training evidence only. Select the highest candidate as the first **plateau seed**, then continue in rank order until four distinct seeds exist or no candidate remains.

Two candidates occupy the same seed region when, after source mapping, their difference is no greater than one accepted local step in every dimension: 10% relative for each distance, one rung, and `1 USDT` principal. A candidate inside an already selected seed region is retained in trial history but cannot consume another seed slot. Arithmetic and geometric candidates are already in separate strata.

#### Successful local neighbor

The representative is the center of the 51-point set and is not counted as its own neighbor. A generated local neighbor is successful only when it:

- maps to a unique executable configuration distinct from the representative;
- passes structural admission and every applicable training-stage economic/risk/activity gate;
- completes with all required evidence; and
- has median quarterly training return within `0.25` percentage points of the representative's return.

Let `A` be the number of unique admitted, evidence-complete neighbors and `S` the successful subset. The seed becomes a performance plateau only when all of:

- the representative passes every applicable gate;
- `S >= 24`;
- `S / A >= 60%`; and
- for each of the five parameter dimensions, at least one of its positive or negative single-dimension neighbors is successful.

If `A = 0`, the ratio is undefined and the plateau fails. Boundary clipping, structural rejection, and executable deduplication reduce `A` and receive no replacements. A deterministic accounting, replay, or evidence-integrity failure is not an unprofitable neighbor: it makes the experiment incomplete and must be diagnosed before any plateau result is accepted.

#### Finalist eligibility

Only the representative and successful members of a qualifying plateau may enter the bounded finalist ranking. Members are compared by the accepted lexicographic rule; plateau membership does not add a score or allow one member's strength to compensate for another member's failed gate. If no seed qualifies, that stratum supplies no finalist.

#### Example

A seed has 46 unique admitted, evidence-complete neighbors. Twenty-nine pass every applicable gate and fall within 0.25 percentage points of the seed, so `S / A = 63.0%`; every parameter has at least one successful single-axis neighbor. The region qualifies. Another seed has 31 close successful neighbors among 48 admitted, but neither `+1` nor `-1` rung remains close and viable. It fails because performance is locally fragile in rung count despite its 64.6% overall support.

#### Consequences

- Stability is demonstrated through controlled parameter changes rather than inferred from irregular distances among Sobol points.
- The absolute and ratio requirements prevent a tiny surviving neighborhood from looking stable after many structural rejects.
- Per-dimension support catches a strategy whose apparent robustness depends on one parameter being tuned to a single exact value.
- Reusing the fixed local trials satisfies the evidence-sufficiency guardrail and keeps implementation to deterministic generation, counting, and comparison.
- Edge-of-domain seeds may fail more often because clipped directions reduce evidence; the search does not widen domains after viewing that outcome.

#### Declined alternatives

- **Simple majority without per-dimension support:** easier but can label a region stable while one economically important parameter remains a single-point optimum.
- **Nearest-neighbor plateau inference from Sobol points:** avoids local trials but uses irregular uncontrolled parameter differences and needs additional distance choices.
- **Isolated top-trial promotion:** maximizes apparent return while providing no local robustness evidence.
- **DBSCAN, Gaussian-process, or response-surface plateau modeling:** may support later research but introduces model selection and implementation complexity without an MVP promotion need.

### Dimension-aware balanced search budget

Selected by the operator on 2026-07-15: the first MVP uses a fixed, power-of-two broad-search budget sized from the five within-stratum search dimensions, followed by tightly capped plateau refinement and exact finalists. The budget is identical for rolling and expanding analyses and is frozen before any result is inspected.

#### Budget unit and dimensions

The budget applies independently to each symbol, walk-forward fold, training-window method, and spacing stratum. Arithmetic and geometric spacing are categorical strata; they do not consume a Sobol dimension. Within either stratum, `d = 5` covers:

1. lower-bound distance;
2. upper-bound distance;
3. canonical rung count;
4. fixed quote principal; and
5. global stop-loss placement.

The manifest records generated points, not merely successful simulations. Structural rejection, venue-equivalent deduplication, infrastructure attempts, and performance evaluation remain separate counts so that a favorable effective sample size cannot be manufactured after results are known.

#### Stage 1 budget — broad coverage

For each symbol/fold/window-method/spacing stratum, generate:

`N = next power of two greater than or equal to max(256, 64 × d)`

With `d = 5`, `N = 512` seeded scrambled Sobol points per stratum. The generator emits exactly the first 512 manifested points. Structurally invalid or venue-equivalent duplicate points remain visible and do not authorize replacement draws; the later parameter-domain decision must therefore define domains with useful feasible coverage rather than relying on outcome-dependent resampling.

Changing the number of searchable dimensions changes `N` mechanically under the same formula and creates a new manifested search family. The budget cannot be increased because early results look unstable or promising.

#### Stage 2 budget — stable-plateau refinement

- At most four distinct broad-search seeds per stratum receive refinement; only a seed whose local evidence passes the bounded proof becomes a performance plateau.
- Each seed receives one deterministic local Cartesian neighborhood capped at 64 unique admitted executable configurations.
- The neighborhood contains its representative, one declared positive and negative local step on each dimension where legal, and the declared pairwise perturbations; clipping, integer mapping, structural rejection, and deduplication are deterministic.
- Under the selected 51-point neighborhood, a stratum contributes at most 204 generated local candidates per symbol/fold/window method. Fewer qualifying plateaus or fewer unique legal neighbors reduce the evaluated count; unused capacity is not transferred to a favored plateau or stratum.

The neighborhood scale and plateau eligibility are fixed by the type-aware refinement and bounded local-proof policies above and cannot expand the immutable neighborhood or stage caps.

#### Stage 3 budget — exact development finalists

At most eight finalists across both spacing strata may proceed per symbol/fold/window method to the declared one-second/trade development escalation and mandatory sensitivities. The accepted lexicographic objective and bounded plateau rules determine those finalists without manual substitution. If fewer than eight satisfy the hard gates, only those candidates proceed; a failed exact replay is not replaced by the next profitable minute candidate unless the frozen rule classified the failure as an infrastructure retry of the same trial identity.

After the full walk-forward development evidence is complete, at most eight proposed-symbol final candidates across the complete declared development procedure may receive the final detailed development comparison. One immutable candidate is then selected and frozen before the sealed holdout bundle is produced. No holdout result may expand either finalist set.

#### Compute envelope

Before structural rejection and deduplication, Stage 1 has:

`512 × 2 spacing strata × 5 symbols × 8 folds × 2 window methods = 81,920` generated points.

Stage 2 adds at most:

`204 × 2 spacing strata × 5 symbols × 8 folds × 2 window methods = 32,640` manifested local candidates.

Stage 3 admits at most `8 × 5 × 8 × 2 = 640` detailed fold-level finalist evaluations, plus the bounded proposed-symbol final comparison and declared sensitivities. These are maximum experiment counts, not a promise that all configurations are valid or independent.

Research jobs must be checkpointed, resumable, and parallelizable on local or temporary Azure batch compute. The always-on Azure paper/live node is sized for deterministic runtime operation and evidence capture, not for this historical search. Before implementation acceptance, a representative benchmark must estimate wall time, storage, and temporary-compute cost; exceeding that operational estimate pauses the research job for operator review but does not permit a smaller post-result sample.

#### Example

For one geometric BTCUSDT rolling fold, the manifest generates the first 512 Sobol points. Venue rounding maps 17 points to configurations already represented, and 39 fail structural capital or stop safety, leaving 456 unique admitted performance simulations. Three plateaus qualify. Their 51-point deterministic neighborhoods yield 49, 47, and 50 unique admitted candidates after clipping and deduplication, so 146 refinements run; the unused fourth plateau and remaining guard-cap capacity are not reassigned. Six candidates satisfy the frozen finalist rule and receive exact development replay. The search does not draw another 56 Sobol points to replace the rejected and duplicate points, and it does not add two weaker finalists merely to reach eight.

#### Consequences

- The budget provides broad, reproducible coverage without an open-ended optimizer or an exhaustive high-dimensional Cartesian product.
- Equal budgets make symbols, folds, window methods, and spacing strata comparable; the result cannot be improved by selectively spending more trials on a favored case.
- The fixed caps limit multiple-testing exposure and make compute planning possible, while full generated-point accounting exposes loss of effective coverage from bad domains or venue rounding.
- Detailed replay remains concentrated on bounded finalists, keeping high-fidelity cost tractable without weakening the full minute-level baseline.
- The chosen budget is intentionally comprehensive for an MVP research qualification. Performance benchmarking may change the budget only before inspecting strategy results, producing a new manifest and rationale.

#### Declined alternatives

- **Lean fixed budget:** 256 Sobol points per stratum, two plateaus, 32 refinements per plateau, and four finalists roughly halves compute but provides weaker five-dimensional coverage and plateau evidence.
- **Deep fixed budget:** 1,024 Sobol points per stratum, eight plateaus, 64 refinements per plateau, and 16 finalists increases coverage but approximately doubles the broad workload and raises multiple-testing and detailed-replay cost; it is reserved for a separately declared later sensitivity or family.
- **Open-ended search until convergence:** has unpredictable cost and lets observed performance decide trial-family size, undermining reproducibility and statistical correction.
- **Replace every rejected or duplicate point:** makes the generator path and effective search budget dependent on venue/domain mapping and can covertly favor selected strata; generated-point coverage and admitted-trial coverage must instead be reported separately.
- **Use the minimal live Azure node for historical search:** couples qualification latency and compute pressure to the safety-critical online runtime and is unnecessary for a batch workload.

### Constrained lexicographic candidate ranking

Selected by the operator on 2026-07-15: candidate selection uses hard non-compensating gates followed by a short deterministic priority order. It does not combine heterogeneous evidence into a weighted score.

#### Evidence boundary

Within each walk-forward fold, broad-search, plateau, and fold-finalist decisions use that fold's training interval only. The primary economic statistic is the median net return of complete, non-overlapping UTC three-month blocks contained in that training interval, always measured against the full `250 USDT` allocated-equity denominator. The immediately following walk-forward test interval remains unseen until its fold candidate is frozen.

After all fold tests are exposed as development evidence, the same priority order applies to the bounded proposed-symbol final-candidate set using the eight rolling out-of-sample quarterly fold results. The expanding-window analysis is a mandatory independent pass/sensitivity condition; it is neither averaged with rolling results nor allowed to boost a rolling ranking.

#### Hard gates first

A candidate enters ranking only after every applicable structural, accounting, reconciliation, deterministic-replay, data-quality, terminal-risk, activity, cost, regime, and evidence-completeness requirement for that stage passes. A stronger return, smaller drawdown, or simpler configuration can never compensate for a failed gate. Infrastructure failure remains incomplete evidence rather than an economic loss or ranking value.

#### Deterministic priority order

Among candidates that pass every applicable hard gate:

1. prefer the higher median quarterly net return on the stage's permitted evidence;
2. when median returns fall within the fixed `0.25` percentage-point practical-equivalence band, prefer the lower maximum run drawdown measured from conservative liquidation equity;
3. if still equivalent, prefer the higher worst quarterly net return;
4. if still tied, prefer fewer maximum concurrent effective managed orders;
5. then prefer lower gross quote turnover over the compared evidence interval;
6. then prefer geometric spacing as the declared default; and
7. break a remaining exact tie by canonical immutable configuration identifier.

Only the first criterion that materially distinguishes the candidates decides. Later criteria do not contribute points and cannot offset an earlier disadvantage outside the practical-equivalence band.

#### Practical-equivalence band

Selected by the operator on 2026-07-15: two median quarterly returns are economically equivalent for ranking when their absolute difference is no more than `0.25` percentage points. This is an absolute return difference, not a relative percentage: 2.10% and 2.02% differ by 0.08 percentage points and are equivalent, while 2.10% and 2.40% differ by 0.30 percentage points and are not.

On the fixed `250 USDT` allocation denominator, 0.25% corresponds to `0.625 USDT` per quarter. The band acknowledges that smaller simulated differences are not a sound reason to accept higher drawdown. It is a deterministic selection tolerance, not a confidence interval, statistical-significance claim, accounting tolerance, or permission to round reported results.

Apply the band only to the first median-return comparison. Subsequent values retain their exact declared comparisons and tie-break rules; the band is not repeatedly added across a chain of candidates. To prevent non-transitive grouping, rank against the currently highest eligible median-return value: candidates within 0.25 percentage points of that value form the close-return set, and lower-return candidates cannot enter through a chain of pairwise closeness.

#### Example

Candidates A and B pass every hard gate. A has a median quarterly net return of 2.10% and maximum drawdown of 7%; B has 2.02% and 5%. If the frozen practical-equivalence band is 0.25 percentage points, their returns are treated as economically equivalent and B wins on drawdown. Candidate C has 2.60% return and 8% drawdown while remaining inside every risk limit; it beats both because its return difference lies outside that band. Candidate D has 4% return but fails an accounting invariant, so it is rejected before ranking.

#### Consequences

- The result remains explainable: every candidate can be shown as rejected by a named gate or preferred at one named priority.
- Median quarterly return limits dominance by one exceptional interval without inventing composite weights.
- Drawdown and worst-fold behavior decide close economic cases rather than compensating for clearly weaker returns.
- Operational simplicity is a late tie-break only, so it cannot select a materially less effective strategy merely because it has fewer orders.
- The selection rule is implementable as one small deterministic comparison function shared by batch jobs and reports.
- The fixed band avoids false precision without requiring a bootstrap or confidence-interval engine solely for ranking; later statistical promotion gates remain separate.

#### Declined alternatives

- **Highest aggregate return:** simple but permits one exceptional interval to dominate and hide unstable quarterly behavior.
- **One weighted risk-adjusted or trust score:** requires subjective weights and permits strength in one dimension to compensate for a failed or weak unrelated dimension.
- **Manual selection from a Pareto frontier:** useful for exploration, but allows inspected outcomes and operator preference to enter promotion evidence without a frozen deterministic rule.
- **Blend rolling and expanding results:** double-counts common test periods and lets sensitivity evidence compensate for primary-method weakness.
- **Rank primarily by the worst fold:** strongly emphasizes one noisy interval and can select persistently mediocre configurations; worst-fold evidence remains a close-case tie-break and later hard threshold.
- **0.10 percentage-point band:** gives tiny simulated return differences more authority than their likely economic significance.
- **0.50 percentage-point band:** gives drawdown materially more influence but can treat a meaningful `1.25 USDT` quarterly difference on the MVP allocation as equal.
- **No equivalence band:** lets arbitrarily small decimal differences dominate risk and stability, implying false simulator precision.
- **Confidence-interval-based ranking band:** statistically richer but adds resampling choices and implementation complexity not required by the MVP selection decision; statistical confidence and multiple-testing are handled by separate gates.

### Return-primary evaluation with a Deflated Sharpe credibility gate

Selected by the operator on 2026-07-15: net return remains the primary economic measure and the first candidate-ranking criterion. A Deflated Sharpe Ratio (`DSR`) threshold is one secondary hard gate against selection luck after testing many configurations; it is not the main objective, a safety-risk limit, or a replacement for return requirements.

#### Distinct questions

The evidence answers three separate questions in order:

1. **Is it profitable enough?** Net flow-adjusted return after all accepted fees, spread, slippage, rejections, rounding, bootstrap costs, and terminal disposal is evaluated through the explicit return gates and primary ranking.
2. **Is that observed return statistically credible after selection?** DSR checks whether the selected return path's variability, shape, and the declared number of tried strategies make a lucky winner plausible.
3. **Is it safe enough?** Drawdown, daily loss, terminal equity, inventory, accounting, reconciliation, and operational limits are independent hard gates.

A candidate must answer all three successfully. Strong DSR cannot rescue inadequate return; high return cannot rescue low DSR or a safety failure.

#### DSR evidence and threshold

- Calculate DSR for the one proposed symbol-specific candidate from non-duplicated daily flow-adjusted returns on the primary rolling out-of-sample path. Fold allocation/reset flows do not become returns.
- Use the complete declared performance-selection exposure: every unique configuration with an inspected economic result that could have influenced strategy, symbol, spacing, parameter, plateau, finalist, or rule selection. Structurally rejected points and executable duplicates without separate performance results remain reported but do not masquerade as independent trials.
- Freeze the formula/version, return frequency, annualization, serial-dependence treatment, skew/kurtosis handling, benchmark Sharpe, trial-family identity, and numerical tests in the experiment manifest. Existing canonical DSR code is reused only after conformance tests prove these semantics.
- Require DSR probability `>= 0.95` before historical promotion. A lower value fails the credibility gate; it does not trigger a new seed, larger search, alternative trial count, or runner-up holdout attempt.
- Report raw net returns, ordinary Sharpe inputs, trial count, DSR inputs, and DSR output. DSR never hides the economic return series behind one number.

The 0.95 result is not a claim of a 95% probability of future profit. It is model-dependent evidence that the selected risk-adjusted return exceeds the multiple-testing-adjusted benchmark under the frozen calculation.

#### Example

Candidate A earns 12% across development, but most of it comes from a short favorable burst and it was selected after a large trial family; its DSR is 0.71. Candidate B earns 8% with returns distributed more consistently and has DSR 0.97. Return-first ranking does not automatically choose B: A is first recognized as the higher-return candidate, then fails the independent credibility gate and cannot be promoted. B still must pass the explicit minimum-return, holdout, regime, and safety gates. A third candidate with DSR 0.99 but economically inadequate return also fails.

#### Consequences

- The system optimizes what the operator expects—net return—while refusing to confuse the luckiest tested path with reliable evidence.
- DSR uses statistical return variability; it does not redefine the accepted capital-risk and operational-safety model.
- One existing statistical measure is hardened instead of adding a suite of overlapping tests, satisfying the anti-overengineering guardrail.
- The locked holdout remains mandatory because DSR is a development credibility screen, not unseen future evidence.

#### Declined alternatives

- **Use DSR as the primary ranking objective:** can prefer a low-return smooth strategy and conflicts with the accepted return-primary economic objective.
- **Use only raw return:** ignores the increased chance of finding a lucky winner across the large declared search family.
- **Rely only on the locked holdout:** is simple but may consume scarce holdout evidence on a candidate that already shows weak selection-adjusted credibility.
- **Bonferroni-corrected significance:** easy to state but typically over-penalizes the highly correlated grid configurations as if every trial were independent.
- **Bootstrap Reality Check or SPA for the MVP:** can better model some dependencies but adds resampling, block-length, and implementation choices beyond the smallest sufficient first gate.
- **Add several statistical scores and combine them:** creates another trust score and unclear compensation rather than one auditable credibility check.

### Balanced historical net-return gate

Selected by the operator on 2026-07-15: historical promotion requires economically meaningful net return across rolling development, expanding sensitivity, and both locked-holdout fidelities. These are hard minimums after all accepted costs, not ranking bonuses or values that safety/statistical evidence may compensate.

#### Common return basis

- Use flow-adjusted total return on the complete `250 USDT` allocated-equity denominator, including uncommitted quote.
- Include actual/modeled fees by asset, spread, slippage, post-only rejection effects, latency assumptions, rounding residuals, bootstrap acquisition, third-asset conversion, and terminal disposal exactly once under the accepted accounting and execution contracts.
- Fold activation and reset allocations are external flows, not profit. No state crosses fold boundaries.
- “Positive” means strictly greater than zero at source-exact result precision after all costs; display rounding cannot turn zero or a loss into a pass.

#### Primary rolling out-of-sample gate

Across the eight three-month rolling OOS folds for the proposed symbol:

- at least six of eight fold net returns must be strictly positive;
- the median quarterly net return must be at least `0.75%`;
- the geometrically linked, non-duplicated daily OOS return path must annualize to at least `5.00%`; and
- every previously accepted regime, concentration, DSR, correctness, and risk condition must independently pass.

Annualization compounds the concatenated non-duplicated daily fold returns over their exact elapsed trading-day evidence and scales to 365 UTC days. It does not compound strategy sizing or carry inventory between folds.

#### Expanding-window sensitivity gate

On the same eight OOS boundaries under expanding training:

- at least five of eight fold net returns must be strictly positive; and
- the non-duplicated daily OOS path must annualize to at least `3.00%`.

The lower sensitivity threshold recognizes that expanding training deliberately retains older regimes. It remains a hard independent pass: a stronger rolling result cannot average away expanding failure.

#### Locked-holdout return gate

The one frozen proposed-symbol candidate must earn at least `4.00%` total net return over the complete 12-month locked holdout independently in:

- the minute-level conservative evaluation; and
- the event-level evaluation in the sealed bundle.

Neither result compensates for the other and both use the same starting `250 USDT` denominator, frozen candidate, costs, terminal valuation/disposal, and holdout boundaries. The later fidelity-parity decision constrains disagreement between the two results in addition to these independent minimums.

#### Benchmarks

- **Untraded quote cash:** `250 USDT` held without interest is the hard zero-return benchmark. The strategy thresholds above already exceed it materially.
- **Buy-and-hold:** report conversion of the same `250 USDT` to the base asset at the activation boundary, passive holding, and terminal conversion under the same applicable acquisition, fee, spread, slippage, and disposal assumptions. It is diagnostic, not a universal hard gate, because its full long exposure differs from a neutral Spot grid's changing base/quote inventory.

Reports show strategy and benchmarks together by overall period and regime. They may explain opportunity cost, but exceptional buy-and-hold performance cannot make a grid that passes its frozen absolute gates fail, and poor buy-and-hold cannot rescue a grid that fails.

#### Example

Rolling OOS quarterly returns are `1.2%, 0.9%, -0.4%, 1.0%, 0.8%, 0.6%, -0.2%, 1.1%`: six are positive and the median exceeds 0.75%. If the linked daily path annualizes to 5.4%, rolling passes its return gate. Expanding has six positive folds and annualizes to 3.3%. The frozen holdout earns 4.6% in minute simulation and 4.2% in event replay. These return gates pass, subject to all other gates. A 7% buy-and-hold result is reported but does not invalidate the grid.

#### Consequences

- Return is explicitly the primary economic criterion rather than implied by a risk-adjusted statistic.
- Quarterly breadth prevents one favorable fold from carrying the full development result.
- The holdout requires a meaningful annual result in both fidelities rather than merely `> 0` after simulation noise.
- A percentage gate evaluates scalability of the strategy evidence even though the first-live capital amount is deliberately small.
- Two simple benchmarks provide context without adding a benchmark optimizer or changing the strategy objective.

#### Declined alternatives

- **Positive aggregate return only:** can pass on one exceptional period while most quarterly evidence loses money.
- **Permissive five-of-eight and merely positive holdout:** may promote an economically insignificant edge that disappears under modest model error.
- **Demanding seven-of-eight, 1.25% median, 8% annualized, and 6% holdout:** offers stronger economics but may reject a useful conservative first grid before paper evidence.
- **Require universal buy-and-hold outperformance:** compares different exposure profiles and wrongly rejects grids during strong bull trends even when they meet their intended sideways-market and drawdown objectives.
- **Return on deployed order capital:** excludes idle allocated quote and inflates configurations that deliberately use less of the common envelope.
- **Gross grid-cycle profit:** omits inventory valuation, costs, terminal disposal, and inactive/range-exhausted periods and is not total economic return.

### One-percentage-point holdout fidelity-parity band

Selected by the operator on 2026-07-15: minute and event-level results in the sealed 12-month holdout bundle must each pass independently and must remain economically close enough to support the minute simulator's role as the broad-search approximation.

#### Mandatory comparisons

For the identical frozen candidate, holdout boundaries, starting `250 USDT` allocation, accounting semantics, risk policy, costs, and terminal valuation/disposal:

- each fidelity must independently earn at least the accepted `4.00%` total net return;
- the absolute difference between their total net returns must be no more than `1.00` percentage point; and
- the absolute difference between their maximum run-drawdown ratios must be no more than `1.00` percentage point.

These are absolute percentage-point differences, not relative percentages. Compare source-exact results before display rounding. Equality at exactly 1.00 percentage point passes.

Both runs must independently preserve accounting, asset conservation, inventory backing, order obligations, risk transitions, terminal-state validity, and deterministic behavior for their own canonical evidence. Their fills and resulting assets need not be identical because the event tier resolves sequencing unavailable to one-minute candles.

#### Diagnostic attribution

The sealed report must show and attribute differences in at least:

- accepted/rejected/post-only order outcomes;
- partial and cumulative fills;
- completed paired cycles and pending paired quantity;
- fees by actual asset, spread/slippage, and terminal-disposal costs;
- time in active, range-exhausted, paused/reducing, and terminal states;
- terminal base/quote/fee-asset quantities; and
- return and drawdown by regime and stress overlay.

These diagnostics receive no additional arbitrary promotion tolerances in the MVP. They explain the two mandatory economic comparisons and expose model defects; they do not form a compensating score.

#### Failure handling

Exceeding either one-percentage-point band blocks historical promotion even if both individual returns exceed 4%. The discrepancy must be classified as expected evidence-resolution difference, data defect, execution-model defect, accounting defect, or unexplained. It cannot be waived because the event result is favorable.

Changing the minute model, event model, cost assumption, candidate, or threshold after viewing the sealed bundle creates a new search/evidence family. The exposed holdout may support diagnosis and deterministic regression tests, but cannot be reused as unseen promotion evidence; a genuinely later eligible holdout is required.

#### Example

Minute evaluation returns 4.8% with 6.2% maximum drawdown; event replay returns 4.1% with 6.9% drawdown. Both exceed 4%, and differences of 0.7 percentage points pass. If minute return is 5.5% and event return is 4.2%, the 1.3-point return disagreement fails even though both are individually profitable. A minute result of 4.7% and event result of 3.9% also fails the independent event return gate before parity can rescue anything.

#### Consequences

- The fast minute simulator must be directionally useful, not merely profitable by coincidence.
- One simple return band and one drawdown band cover the decision-material economic disagreement without overengineering thresholds for every fill statistic.
- Symmetric treatment catches material optimism and pessimism; both can distort parameter selection and compute planning.
- Detailed attribution remains available for debugging while promotion logic stays small and deterministic.

#### Declined alternatives

- **Asymmetric 1.5-point conservative/0.5-point optimistic band:** expresses a conservative preference but adds direction-specific policy and can hide a materially under-responsive minute model.
- **Two-percentage-point band:** is too large relative to the 4% minimum annual holdout return and permits substantial model disagreement.
- **Independent passing only:** allows large economic divergence and fails to validate the minute model used for broad selection.
- **Threshold every fill, cycle, fee, and inventory difference:** creates many arbitrary correlated gates; these remain diagnostic unless evidence later proves a specific additional boundary is needed.
- **Calibrate on the exposed holdout and rerun it for promotion:** converts final evidence into development data and violates the locked-holdout contract.

### Balanced completed-cycle activity gate

Selected by the operator on 2026-07-15: a promoted candidate must demonstrate recurring, economically positive grid cycling. Total return alone is insufficient because bootstrap base inventory can appreciate while the grid completes little or no trading.

#### Counting rule

One **completed paired cycle** is counted when one venue-valid cumulative paired-order obligation reaches its terminal filled quantity and its paired-lot acquisition cost, proceeds, and attributable fees produce a finalized realized cycle result under the accounting specification.

- Multiple partial executions of the same cumulative paired order count as one cycle, not one cycle per fill.
- Pending paired quantity, an open/partially filled paired order, bootstrap acquisition, initial inventory placement, recovery-side retention, global stop-loss or operator-stop disposal, and terminal valuation do not count.
- Repeated valid outer-rung cycles count normally because each is a new completed paired obligation inside the immutable range.
- A cycle remains counted even if the run later loses money elsewhere; its exact realized result remains in the evidence.

#### Rolling and expanding development

The non-duplicated OOS paths for rolling and expanding analyses must each satisfy:

- at least 24 completed paired cycles across the eight test folds;
- at least two completed paired cycles in at least six of the eight folds; and
- a strictly positive aggregate realized cycle result after every fee attributable to those cycles.

Fold boundaries remain independent. A cycle cannot begin in one fold and finish in another, and duplicated evaluation of the same date under another analysis does not increase either path's count.

#### Locked holdout

Minute and event-level evaluation must each independently satisfy across the complete 12-month holdout:

- at least 12 completed paired cycles;
- at least one completed paired cycle in at least eight distinct UTC calendar months; and
- a strictly positive aggregate realized cycle result after attributable fees.

The activity counts need not match across fidelities and receive no separate parity tolerance. Their differences are already diagnostic evidence, while each fidelity must pass the same minimum activity gate.

#### Example

A rolling OOS path completes 29 cycles, has at least two cycles in seven folds, and realizes a positive 6.20 USDT cycle result after fees. Its activity gate passes. A candidate with a 7% total return but only six completed cycles fails even if most profit came from rising base inventory. In holdout, 14 cycles spread across nine months pass; 20 cycles concentrated into four volatile months fail the calendar-breadth requirement.

#### Consequences

- Historical evidence must show the grid mechanism operating, not merely long base exposure.
- Modest counts avoid favoring extremely narrow, high-turnover grids while still requiring repeated observations across time.
- Positive realized cycle result confirms that cycling survives actual fees; total return still remains the primary overall economic measure.
- The rule reuses canonical order and accounting evidence and requires no new analytical subsystem.

#### Declined alternatives

- **Eight development and four holdout cycles:** is easy to pass but provides little recurring evidence across a multi-year validation path.
- **Forty-eight development and twenty-four holdout cycles with activity everywhere:** produces more observations but biases selection toward narrow high-turnover grids and against valid wide grids/regimes.
- **Total return without activity:** can promote a mostly passive base holding while attributing appreciation to grid trading.
- **Count every partial fill:** lets fragmented execution inflate activity without completing additional economic cycles.
- **Require cycle profit to be most of total profit:** attempts to decompose changing inventory exposure with an arbitrary ratio; positive realized cycle result plus explicit buy-and-hold attribution is sufficient for MVP.

### Evidence-continuity 30-day paper clock

Selected by the operator on 2026-07-15: paper qualification requires 30 consecutive UTC calendar days of one immutable candidate and decision-critical build with continuous, replayable evidence. Safe restart and recovery are evidence to be demonstrated, not automatic clock failures.

#### Clock identity and boundary

The clock starts only after historical promotion passes, all pre-paper automated acceptance/fault tests pass, paper activation eligibility succeeds, and the admitted paper run records its exact start instant. It reaches duration at `start + 30 × 24 hours`; local time, daylight-saving changes, and partial calendar dates do not alter it.

One qualifying identity freezes:

- symbol and immutable strategy configuration version;
- decision, execution-simulation, accounting, reconciliation, and risk code build;
- risk profile, venue-rule/fee observations, execution model, latency/cost assumptions, and allocation;
- canonical event and evidence-schema versions; and
- dataset/capture, alert, replay, and deterministic-build identities required by promotion.

Passing the duration never activates live trading automatically.

#### Interruptions that preserve the clock

A planned infrastructure restart, forced-process recovery drill, Azure host interruption, or transient safety posture preserves elapsed time only when all of:

- no decision-material public, private, control, valuation, or persistence evidence is lost or left unproven;
- the runtime follows the accepted frozen-startup and recovery state machine within its deadlines;
- authoritative query evidence reconstructs every order, simulated fill, balance, inventory, reservation, fee, risk state, and command outcome;
- reconciliation ends with zero unresolved items and every invariant passes;
- no missed or duplicate decision/order/fill is found; and
- the retained stream replays to the exact paper decisions, state, accounting, simulated execution, and terminal recovery position.

Time spent safely `FROZEN` during such evidenced recovery remains part of the consecutive wall-clock period and is reported separately from active time. A safe recovery proves operational behavior; it cannot delete the interruption from availability and incident reports.

#### Events that reset qualification

The current qualification attempt ends and a new 30-day clock is required after any of:

- strategy configuration, decision-critical deployed code, risk threshold, execution model, material cost/latency assumption, or evidence-schema semantic change;
- decision-material market/account/control/persistence gap that cannot be repaired authoritatively;
- missed, duplicated, unsupported, or unreconciled order or simulated fill;
- unexplained asset/accounting difference or hard invariant failure;
- unsafe, incomplete, deadline-exceeding, or non-replayable recovery;
- unresolved critical incident or redaction/evidence-integrity failure; or
- a terminal operator stop or global stop-loss, or another safety action that permanently closes the qualifying run.

The failed attempt remains retained evidence. A corrective build or semantic change begins a new identity; good days before the change cannot be carried forward.

#### Economic interpretation

Paper return, completed cycles, drawdown, costs, range state, and benchmark comparisons are reported. The 30-day gate is primarily operational because one future month is too regime-dependent to replace the five-year historical and 12-month holdout return gates. No standalone positive-return minimum is imposed merely to finish the paper clock, but all accepted risk ceilings remain hard and the later paper-to-live gate may reject unexplained material divergence from replay expectations.

#### Production-data paper boundary

The qualifying paper run consumes real-time **Binance Spot production public market evidence** for the selected symbol. Trades, best bid/offer, relevant targeted depth, stream timing, and continuity observations are real venue observations. They are durably captured as canonical inputs and are not replaced by a fabricated favorable price path.

A **paper order** is nevertheless local and non-executable. The shared decision core emits the same order intent it would emit in live mode, but the paper execution adapter—not the Binance production trading endpoint—creates the acknowledgement, resting state, partial fills, cancellation outcomes, balances, fees, and order-event lifecycle. Its outcomes are deterministic consequences of the frozen conservative policy and the captured production evidence, including post-only eligibility, queue-ahead state, strict execution evidence, 5% non-reusable volume participation, partial fills, latency, fees, and venue rounding. The paper account starts with the qualifying virtual `250 USDT` allocation; no real asset is reserved, bought, sold, or transferred.

“Simulated order” therefore does **not** mean synthetic or randomly generated market data. It means that the strategy observes the real market while the order and account consequences remain hypothetical. Exact retained inputs must reproduce the same paper order lifecycle and accounting under captured paper replay.

Binance Testnet remains a separate venue-integration mode. It may send actual API orders against Testnet assets to validate authentication, signing, identifiers, REST/WebSocket lifecycle, unknown-outcome recovery, and protocol handling. Its market liquidity and fills are not accepted as strategy-profitability or production-fill evidence and cannot replace the production-data paper clock.

#### Concurrent Production-Data Paper and Testnet qualification

Selected by the operator on 2026-07-15, terminology-aligned and lifecycle-refined on 2026-07-18: the **Production-Data Paper Run** and Binance Spot **Testnet Run** run concurrently for exactly one algorithm and symbol at a time. Both use the same decision-critical build, canonical strategy candidate, accounting/reconciliation contracts, risk rules and evidence schemas, while retaining separate market inputs, run identities, command authority, ledgers, orders, fills, balances, fees, reports and gate claims.

MVP1 first receives a flexible shakedown period in both run types, expected to take roughly three weeks but extended whenever first-launch defects or improvements require it. Each corrected increment receives local qualification, frozen replacement, new identities and applicable Azure acceptance; shakedown evidence remains diagnostic and no earlier days are carried into a changed candidate. Once an exact candidate satisfies every clock-start prerequisite and has no unresolved decision-material incident, the operator explicitly freezes it and starts the 30-day Production-Data Paper qualification. A later start is normal, not a delay failure.

After the clock starts, a decision-critical correction ends that attempt and the corrected candidate starts a fresh 30-day clock after requalification. Proven non-decision Studio/documentation/diagnostic changes follow the evidence-impact matrix. For at least the first two months there is no overlap between algorithms and no multiple-symbol online operation. Later feature increments replace both online runs sequentially and any candidate intended for real money completes its own immutable 30-day Production-Data Paper and applicable Testnet qualification.

The production-data paper run remains the qualifying forward-market path. It consumes live Binance production public trades, BBO, targeted depth, timing, and continuity evidence; produces non-executable paper orders and conservative local fills; owns the 30-to-90-day evidence-continuity, natural-activity, availability, replay, accounting, risk, and operational gates; and supplies the future production-market diagnostic economics.

The Testnet run is a venue-integration test. It consumes Testnet market/account evidence, sends authenticated commands to Binance Testnet, processes Binance Testnet acknowledgements, execution reports, partial/full fills, cancellations, queries, balances, and filters, and reconciles its local Testnet ledger to the Testnet-authoritative account. It must exercise the selected strategy implementation end to end, but any activation-relative Testnet configuration is explicitly diagnostic and receives no production authority because Testnet prices and liquidity can differ from production.

The two runs are never reconciled to each other. A production paper order need not equal a Testnet order, and a production paper balance must not be forced to match a Testnet balance. Each is reconciled only to its own authority:

```text
production public market evidence -> local paper execution -> paper ledger
Testnet market/account evidence   -> Binance Testnet orders -> Testnet ledger
```

Testnet orders, closed-order history, account information, realized cycles, inventory, drawdown, and P&L are retained and reported as a **Testnet result**. They prove end-to-end functional and venue-contract behavior in that environment. Testnet P&L cannot satisfy or compensate for rolling, holdout, production-paper, regime, activity, or production-return evidence because it is generated by a separate market and virtual account. Conversely, strong production-paper economics cannot compensate for failed Testnet authentication, order lifecycle, reconciliation, recovery, or protocol behavior.

A Binance Testnet environment reset is recorded as authoritative Testnet environment evidence. It ends or restarts only the affected Testnet continuity claim and must exercise safe disappearance/reinitialization handling; it does not reset the independent production-data paper clock when production evidence and operation remain valid. Testnet balances or cycles before and after a reset are never combined as one continuous account result.

Running both concurrently avoids adding a serial calendar month and exposes shared-build defects sooner. Resource isolation must ensure Testnet load or failure cannot delay production-paper evidence admission or weaken its safety deadlines on the minimal Azure deployment.

Consequences:

- The selected strategy is exercised both against real future production observations and through genuine Binance non-production order/account interfaces.
- Separate ledgers prevent artificial Testnet fills from contaminating production-paper accounting or performance.
- Reports can show complete Testnet activity and P&L without overstating what those economics predict.
- Shared decision semantics increase reuse, while environment-specific adapters and authorities remain explicit architectural seams.
- The separately accepted 13-family Testnet scenario suite, seven-day reset-free soak, reset-generation handling, and per-scenario reconciliation/replay thresholds complete the Testnet qualification contract.

Declined alternatives:

- **Testnet as the sole qualifying paper system:** provides genuine Testnet order feedback but replaces production-market evidence with a separate artificial market and virtual account.
- **Production-data paper without Testnet:** supplies future production-market behavior but leaves authenticated Binance order, private-event, query, and reconciliation integration less proven.
- **Merge or cross-reconcile paper and Testnet accounts:** treats different market paths and fills as if they described one account, creating unexplained differences by construction.
- **Use Testnet P&L as a production return gate:** assigns predictive authority to an environment whose participants, queue, liquidity, balances, and resets are not production.
- **Run the two campaigns serially:** lengthens qualification without improving evidential independence when safe resource isolation permits concurrent operation.

#### Scenario-complete Testnet campaign plus seven-day soak

Selected by the operator on 2026-07-15: Binance Spot Testnet qualification requires both a mandatory integration-scenario suite and a seven-consecutive-day reset-free Testnet soak. The scenario suite proves named protocol and lifecycle cases; the soak proves that the same build can maintain Testnet market/account streams, orders, state, reconciliation, and evidence over time. Neither receives production-profitability authority.

The seven-day soak may start only after the mandatory scenario suite passes on the decision-critical build and the Testnet run has:

- an identified Testnet account generation and API-key identity;
- a source-exact initial Testnet balance and open-order snapshot;
- zero unresolved Testnet reconciliation items;
- current Testnet exchange/symbol rules and permissions;
- an admitted venue-valid diagnostic grid configuration based only on Testnet activation evidence; and
- an immutable start instant, build, schema, strategy semantics, risk profile, and adapter configuration.

Duration reaches at `start + 7 × 24 hours`; local dates and daylight-saving changes do not alter it. Safe process restarts, finite-stream rotation, repaired WebSocket disconnects, and bounded unknown-outcome recovery may preserve elapsed time only when Testnet-authoritative queries reconstruct the complete account/order state, reconciliation returns to zero unresolved items, all invariants pass, no order/fill is missed or duplicated, and retained evidence replays exactly. Interruptions and recovery remain reported.

The current soak ends and restarts from zero after:

- a Binance Testnet environment reset or disappearance/reinitialization of its orders and balances;
- decision-critical build, strategy semantics, adapter behavior, risk profile, or evidence-schema change;
- an unrepairable required market/account/control evidence gap;
- missed, duplicate, unsupported, conflicting, or unreconciled Testnet order/fill/account fact;
- unexplained accounting difference, hard invariant failure, unsafe recovery, or unresolved critical incident; or
- terminal closure of the identified Testnet run.

After a Binance Testnet reset, the prior account generation and result remain archived and are never spliced into the new one. The same unchanged build may establish a new baseline, rerun every scenario whose evidence depended on the prior account generation, and begin a fresh seven-day soak. Scenarios whose proof is purely build/protocol-level remain retained only when their inputs and relevant Testnet contract have not changed; the scenario manifest states which were invalidated and why. The independent production-data paper run continues unless its own evidence or operation fails.

No Testnet return, completed-cycle, or natural-fill minimum applies to the soak. Testnet market activity is not controllable enough to make those reliable integration gates; the mandatory scenario suite owns case coverage, while all naturally occurring Testnet orders, fills, balances, accounting, and P&L remain visible diagnostics.

Example: the scenario suite passes on Monday at 10:00 UTC and an authoritative Testnet baseline is admitted. A process restart on day 3 reconstructs every order and balance and replays exactly, so the soak continues. Binance resets Testnet on day 6; the six days remain archived but cannot qualify. The runtime safely detects the new account generation, re-establishes its baseline, reruns account-generation-dependent scenarios, and starts a new seven-day soak. Production-data paper is unaffected.

Consequences:

- Scenario coverage supplies stronger evidence than waiting for rare Testnet events to occur naturally.
- Seven consecutive days expose multi-day stream, reconciliation, restart, identifier, and state-retention defects without making promotion depend on surviving an approximately monthly external reset.
- Reset-aware account generations prevent false continuity and balance splicing.
- Concurrent execution preserves calendar efficiency and keeps Testnet limitations outside production-paper qualification.
- The exact mandatory scenario list and per-scenario acceptance evidence remain the next decision.

Declined alternatives:

- **Thirty consecutive Testnet days:** increases soak evidence but is unnecessarily coupled to an approximately monthly unannounced external reset and duplicates the longer production-paper operational clock.
- **Scenario suite without a soak:** validates named cases but does not expose multi-day stream, persistence, reconciliation, and unattended-runtime degradation.
- **Thirty cumulative days across resets:** combines unrelated account generations and converts broken continuity into an aggregate duration.
- **Require natural Testnet P&L or cycles:** makes integration qualification depend on artificial Testnet market activity and confuses protocol evidence with production economics.
- **Treat a Testnet reset as a production-paper reset:** couples independent environments and discards valid production evidence for an unrelated Testnet lifecycle event.

#### Balanced mandatory Testnet integration-scenario suite

Selected by the operator on 2026-07-15: the first-live evidence bundle requires a bounded suite of Testnet integration scenarios covering every Binance behavior directly consumed by the MVP command, order, account, reconciliation, and recovery paths. Real Binance Testnet calls and authoritative responses are mandatory wherever the condition can be safely and deterministically established. Tagged injection is reserved for transport ambiguity, delivery order, rate-limit, rare partial/late-fill, and environment-reset conditions that cannot responsibly be forced; injected cases must terminate in real Testnet queries or an explicit no-venue-effect proof.

The immutable suite manifest defines each case's build, Testnet account generation, initial balance/open-order/rule snapshot, diagnostic configuration, exact commands, client identities, expected venue or injected evidence, expected safety posture, allowed follow-up commands, reconciliation authority, deadline, invariant result, replay fingerprint, cleanup, and pass/fail condition. Manual observation without retained evidence is not a pass.

The mandatory scenario families are:

1. **Environment, authentication, time, and permissions.** Prove every URL and credential is Testnet-scoped; successful signed query; controlled invalid signature/key and timestamp-window rejection; clock-offset handling; required permissions; withdrawals and production-order transport unavailable by construction.
2. **Venue-rule acquisition and sizing.** Admit current exchange/symbol filters and permissions; construct source-exact venue-valid price/quantity/notional; prove local rejection of tick, step, notional, side, or capacity violations before transmission; classify a harmless authoritative Testnet rejection without changing expected exposure.
3. **Maker-only placement.** Submit a venue-valid `LIMIT_MAKER` away from the Testnet spread, receive and correlate acceptance, observe it as resting through stream/query evidence, and cancel/reconcile it. Submit a controlled would-take `LIMIT_MAKER` and require authoritative rejection with no order or asset effect.
4. **Approved aggressive execution.** Exercise the bounded Testnet equivalent of bootstrap acquisition and terminal/aggressive execution using the MVP's permitted order types, then prove executed quantity, quote amount, commission asset/quantity, balances, and accounting postings from authoritative evidence. It cannot authorize aggressive ordinary grid orders.
5. **Managed-order identity and idempotency.** Prove generation-specific client identity across submit, acknowledgement, query, execution, cancellation, restart, and replay; test duplicate identity while the original is effective; prove duplicate event delivery changes no economic state; prohibit replacement while an earlier outcome remains unknown.
6. **Fill and cumulative-order processing.** Process venue-native full and any naturally available partial fills. When a deterministic Testnet partial fill cannot be obtained safely, use a tagged venue-shaped partial/cumulative-fill fixture against the same parser and accounting path, then reconcile the real Testnet order to prove that injected quantity never contaminates venue/account state.
7. **Cancellation, fill race, and late evidence.** Exercise accepted cancellation and already-terminal cancellation/query outcomes. Inject the admissible delivery ordering in which a fill precedes or arrives after cancellation evidence; require cumulative quantity, paired obligation, fees, reservations, and final status to reconcile without lost or double-counted fill.
8. **Ambiguous submit and cancellation outcomes.** Allow a real Testnet command through a fault boundary while withholding or corrupting its immediate response. Freeze replacement, query by generation-specific client/venue identity, recover the authoritative outcome, and prove exactly one economic effect for accepted, rejected, and not-found branches.
9. **User-data stream continuity and recovery.** Establish authenticated account-event reception, deliberately disconnect/rotate the stream, detect the gap, buffer/admit ordered events, query authoritative orders/account/trades, deduplicate overlap, and resume only after zero unresolved reconciliation and freshness/continuity success.
10. **Frozen restart with effective orders.** Terminate the process while a real Testnet order is resting or outcome-unknown, rebuild projections from durable evidence, start frozen, query Testnet, reconstruct reservations and obligations, prevent duplicate replacement, and reach the declared reconciled posture through explicit authority.
11. **Account, fee, order, and trade reconciliation.** Compare local expectations with Testnet balances, open orders, identified order status, account trades, executed quantities, commissions, and applicable rules; prove exact supported differences, foreign Testnet activity isolation, allocation coverage, evidence-preserving repair, and zero unresolved decision-material items.
12. **Rate-limit and retry discipline.** Inject representative `429`/retry guidance and exhausted request-weight/order-capacity conditions at the adapter boundary; prove reserved safety-query/cancel capacity, bounded backoff, no retry storm, no duplicate command, appropriate posture, and alert. Intentionally exceeding Binance limits or provoking an IP ban is prohibited.
13. **Terminal cleanup and Testnet reset.** Cancel/reconcile all managed orders, execute only the approved terminal path, prove final balances/retained holdings/closed state, and prohibit later commands. If no natural Testnet reset occurs, inject a new-account-generation observation and require safe detection, non-splicing, archived prior evidence, new baseline, and no effect on production paper; a natural reset must satisfy the same case with authoritative evidence.

Every family is mandatory, but one manifested case may cover several families only when each family's inputs, expected results, authority, and assertions remain independently visible. A rare condition unavailable from Testnet may use injection only at the smallest boundary needed; it cannot fabricate a favorable Testnet P&L, natural fill count, account balance, or venue acknowledgement.

The suite passes only when all cases complete on the proposed decision-critical build, every real command has one bounded authoritative outcome, expected rejections change no assets or obligations, all actual and injected events are distinguishable, local/Testnet state ends reconciled, every accounting/risk/order invariant passes, cleanup succeeds, and retained canonical evidence replays exactly. An infrastructure or evidence failure is incomplete—not a favorable retry with changed inputs. A code, schema, adapter, or scenario-semantic correction creates a new build identity and reruns every affected case before the seven-day soak.

Example: a `LIMIT_MAKER` submit reaches Testnet, but the fault boundary hides the HTTP response. The runtime records `SUBMISSION_UNKNOWN`, prohibits another order for that rung, and queries by the original client identity. Testnet reports the resting order; the runtime admits that evidence, restores its reservation, reconciles to zero, and later cancels it once. Submitting a replacement before the query, treating timeout as rejection, or accepting both original and replacement fails the case.

Consequences:

- The suite proves the complete grid-used venue boundary rather than only a happy path.
- Real Testnet evidence is maximized without making promotion depend on naturally rare races or encouraging abusive API behavior.
- Tagged injection remains auditable and cannot be mistaken for Testnet execution or economics.
- Scenario families map directly to named promotion failures, satisfying the MVP evidence-sufficiency guardrail without testing unused Binance products or endpoints.
- The same canonical parsers, identities, accounting, reconciliation, risk, and replay paths are exercised across Testnet and later live operation.

Declined alternatives:

- **Minimal authentication/place/query/cancel suite:** is quick but leaves ambiguity, duplicate prevention, partial/late evidence, restart, reconciliation, terminal, and backoff behavior unproven.
- **Every Binance endpoint and documented error:** tests capabilities outside the grid MVP, creates brittle maintenance, and violates the smallest-sufficient-evidence rule.
- **Natural seven-day events only:** cannot ensure that would-take rejection, unknown outcome, disconnect, late fill, rate limiting, or reset behavior occurs.
- **Fully mocked venue suite:** is deterministic but does not prove signing, endpoint behavior, Binance acknowledgements, queries, streams, filters, balances, and reconciliation against a Binance server.
- **Force rare failures directly against Testnet:** risks uncontrolled state or abusive rate-limit behavior; bounded fault injection followed by authoritative query provides safer evidence.

#### Required balanced recovery and fault-drill suite

Selected by the operator on 2026-07-15: the same immutable qualifying deployment must deliberately exercise a bounded set of realistic operational failures during the 30-day attempt. Fault injection changes connection, command, delivery, or process conditions; it does not substitute a synthetic market-price path for Binance production data.

The qualifying attempt must contain at least:

1. three planned process restarts, including at least one while paper orders are resting;
2. one forced process termination while open paper obligations exist;
3. one production public-market-stream disconnect or detected gap followed by the declared repair path;
4. one disconnect of the local venue-shaped paper order-event stream followed by authoritative local reconstruction and reconciliation;
5. one injected ambiguous submit or cancellation outcome at the paper-adapter boundary;
6. one partial-fill/cancellation race that delivers a late paper fill;
7. one injected rate-limit/backoff response at the adapter boundary, without intentionally abusing Binance production endpoints; and
8. one external dead-man alert proving that loss of the runtime health signal is detected outside the trading process.

Every drill is predeclared, time-bounded, durably tagged as injected, and has an expected safety posture, allowed command set, recovery deadline, evidence query, reconciliation result, alert, and replay result. Passing requires restoration of every paper order, cumulative fill, paired obligation, reservation, balance, inventory lot, fee, risk state, and command outcome; zero unresolved reconciliation items; no missed or duplicate decision/order/fill; all accounting and risk invariants; and exact captured replay. A drill that violates these conditions resets the clock under the existing reset rules rather than being waived as planned maintenance.

Terminal operator-stop and global-stop behavior must be proven by automated acceptance cases on the same decision-critical build before the clock begins, because deliberately closing the qualifying run would end its identity. Their execution may also be rehearsed in a separate non-qualifying paper run, but evidence from that run does not count toward the 30 consecutive days.

Synthetic fault events and deterministic acceptance fixtures validate safety behavior only. They do not count as historical regime observations, paper-market activity, completed economic cycles, or return evidence. Naturally received Binance production events remain the sole market path for the qualifying paper interval.

#### 99.5% decision-ready availability gate

Selected by the operator on 2026-07-15: the complete qualifying paper observation interval, never shorter than 30 days and extended when required by the natural-activity gate below, must achieve at least `99.5%` decision-ready availability. Planned restarts, deliberate fault drills, recovery, Azure interruptions, and every safety-frozen interval are included. No scheduled-maintenance or drill exclusion is subtracted from the denominator.

**Decision-ready availability** means that all evidence and authority required for the next possible paper decision are usable within their accepted deadlines. The runtime must have fresh and continuous required market inputs, available durable persistence and control paths, a fully recovered and reconciled canonical state, and permission to admit a canonical event and produce the appropriate decision batch. It need not generate an order: a valid no-action or risk-restriction decision is decision-ready. A running process, open websocket, responsive UI, or healthy Azure VM alone is insufficient.

For the exact interval from paper-clock start through the final qualifying observation instant, let `T` be total elapsed seconds and `U` the union of all source-timestamped intervals in which the system is not decision-ready. Availability is `(T - U) / T`. Intervals are counted once when causes overlap and are compared at source precision before display rounding. At the minimum 30-day duration, `T = 2,592,000` seconds and the `99.5%` floor permits at most `12,960` unavailable seconds, or exactly `3 hours 36 minutes`, in total. If observation extends, both numerator and denominator continue uninterrupted through the extension; day 30 cannot freeze the availability evidence.

In addition:

- no single unplanned contiguous decision-unavailable interval may exceed 30 minutes;
- every planned or injected interval must satisfy its stricter predeclared drill/recovery deadline;
- unavailable and `FROZEN` time remains visible by cause, incident, start/end time, and recovery outcome;
- one brief return to readiness cannot erase earlier unavailable duration; all intervals remain additive after overlap removal; and
- the percentage is non-compensating: an unrepairable evidence gap, missed/duplicate action, unsafe recovery, unresolved reconciliation item, invariant failure, or other clock-reset event fails qualification even when availability remains above 99.5%.

Example: three planned restarts consume 8 minutes, the forced-termination drill consumes 14 minutes, a public-stream repair consumes 17 minutes, and other freezes total 35 minutes. Total unavailability is 74 minutes, so availability is approximately `99.829%`; no unplanned interval exceeds 30 minutes, and the gate may pass if every independent continuity, recovery, reconciliation, invariant, alert, and replay condition also passes. Conversely, one 31-minute unplanned outage fails even when total availability is `99.93%`. An unrepaired five-second market-evidence gap also resets the paper attempt rather than passing because its percentage is small.

Consequences:

- The threshold is credible for a minimal single-node Azure MVP while still bounding cumulative interruption.
- Counting drills and maintenance prevents a nominal uptime value from hiding required operational exercises.
- Decision readiness measures the trading system's safe usefulness, not infrastructure liveness.
- The 30-minute incident cap prevents one material outage from disappearing inside the 3-hour-36-minute total allowance.
- Exact evidence continuity remains stricter than availability, so the percentage never becomes permission to lose market or order facts.

Declined alternatives:

- **99.9% availability:** permits only 43 minutes 12 seconds across 30 days and is unnecessarily brittle for a deliberately fault-tested single-node first MVP; it remains a sensible later production target after measured operation.
- **Recovery deadlines without an aggregate percentage:** keeps individual incidents bounded but allows many short interruptions to accumulate without failing qualification.
- **99% availability:** permits 7 hours 12 minutes of unavailability, which is too weak before unattended real-money operation.
- **Exclude planned maintenance and drills:** improves the displayed number without measuring the actual service experienced by the strategy and encourages classification games.
- **Measure process or VM uptime:** can report healthy while market evidence is stale, state is unreconciled, persistence is unavailable, or the runtime cannot make a safe decision.

#### Modest natural paper-activity gate with bounded extension

Selected by the operator on 2026-07-15: operational duration alone is insufficient. The unchanged qualifying paper run must also demonstrate ordinary grid execution against naturally observed Binance production market evidence without imposing a high-turnover or one-month-profit requirement.

Qualification requires all of:

- at least 30 consecutive days under the evidence-continuity clock;
- at least two naturally completed paired cycles under the same cumulative paired-order counting and accounting rules used by historical validation; and
- at least one natural paper fill on each of at least three distinct UTC calendar days.

A **natural paper fill** is a partial or full fill of an ordinary managed grid-rung paper order caused solely by qualifying observed Binance production trades, BBO, targeted depth, and the frozen conservative paper execution policy. Multiple fills on one UTC date contribute one fill-active day. Bootstrap acquisition, terminal disposal, operator/global-stop execution, injected fill, fault-drill outcome, deterministic fixture, manually fabricated event, and Testnet or live order do not count. Partial fills may establish a fill-active day, but they do not inflate the paired-cycle count: one cumulative paired obligation still counts once only when completed.

If both activity requirements are already met at `start + 30 × 24 hours`, the natural-activity gate can finish then. Otherwise the same immutable candidate, build, risk profile, execution model, evidence schemas, and virtual allocation continue without interruption until both requirements are met or `start + 90 × 24 hours`, whichever occurs first. Existing reset conditions remain in force throughout, and availability, incidents, economics, replay, reconciliation, and invariant evidence continue across the entire observed interval. Days may not be removed, reordered, or selected because they were inactive or unprofitable.

Reaching 90 days without both activity requirements is an **insufficient natural paper evidence** failure, not a zero-profit result and not permission to count injected activity. The retained attempt remains diagnostic evidence but cannot authorize first-live activation. A later attempt must declare a new future start and satisfy its own uninterrupted duration and activity requirements; it cannot carry cycles or fill-active days from the failed attempt.

No standalone paper-return minimum is added. All paper economics, completed-cycle results, inventory exposure, costs, drawdown, range exhaustion, and benchmark comparison remain visible, while the accepted historical return gates retain primary authority. Any risk, accounting, reconciliation, replay, continuity, or availability failure remains independently disqualifying even when the activity counts pass.

Example: after 30 days, the run has one completed paired cycle and natural ordinary-rung fills on four UTC days. The duration and fill-day conditions pass, but the cycle condition does not, so observation continues unchanged. A second paired cycle completes on day 41; qualification may finish at that instant if the full 41-day availability calculation and every other paper gate pass. If day 90 arrives with two cycles but fills on only two distinct UTC days, activity remains insufficient and the attempt fails.

Consequences:

- The paper stage proves at least a modest amount of natural order and paired-cycle behavior rather than qualifying from a quiet process alone.
- Two cycles and three fill-active days are deliberately small relative to historical evidence, reducing bias toward narrow high-turnover grids.
- Bounded continuation accommodates a quiet 30-day market interval while keeping the qualification schedule finite.
- The unchanged identity and continuous evidence prevent extending only favorable fragments or changing the grid to manufacture activity.
- Fault drills validate failure handling but cannot masquerade as naturally observed execution.

Declined alternatives:

- **Thirty days without natural activity:** can qualify a deployment that never naturally exercises ordinary paper fills or paired-cycle accounting.
- **Six cycles and ten fill-active days inside 30 days:** provides stronger activity evidence but materially biases promotion toward narrow, high-turnover grids and can reject a valid wider grid after one quiet month.
- **Continue without a maximum until 12 cycles:** gathers more execution evidence but makes qualification duration unpredictable and potentially indefinite.
- **Count bootstrap, terminal, injected, or partial fragments as cycles:** inflates evidence with non-grid or non-completed economic actions and conflicts with the canonical paired-cycle definition.
- **Require positive paper return:** overweights one to three future months and duplicates the role of the five-year, holdout, and realized historical-cycle gates.

#### Example

On day 12, the process is deliberately killed while simulated orders exist. It restarts frozen, restores the journal, queries current evidence, reconciles all obligations, proves no gap, replays exactly, and resumes under explicit approval within accepted deadlines. The clock continues and the incident remains reported. On day 24, a private-stream gap leaves one simulated fill timing unprovable. Even if balances later appear plausible, the attempt ends; after correction and a fresh qualifying activation, the clock restarts at day zero.

Here, the day-12 prices and trades came from Binance production. Only the paper order acknowledgements, fills, and virtual balances were hypothetical. The day-24 “private stream” is the venue-shaped local paper order-event stream, not evidence that Binance executed an order against real assets.

#### Consequences

- Qualification tests the restart/recovery design instead of rewarding a process that happened never to restart.
- Consecutive evidence prevents selecting and summing only good days from an unstable deployment.
- Immutable critical identity makes the 30 days evidence about the build and candidate that could later be approved.
- Reporting frozen time separately preserves honest reliability evidence without treating safe restriction as active trading.

#### Declined alternatives

- **Reset after every process restart:** discourages the deliberate recovery tests required for promotion and confuses safe infrastructure lifecycle with lost evidence.
- **Accumulate 30 valid days inside 45 days:** permits failed or missing periods to be excluded and can hide recurring reliability problems.
- **Fixed 30-day wall clock regardless of gaps/incidents:** can pass without continuous authoritative evidence and makes the duration largely ceremonial.
- **Carry good days across decision-critical builds:** combines evidence from different products and does not qualify the build proposed for live activation.
- **Require positive paper profit for one month:** overweights one short future regime; economic divergence remains visible, while historical gates carry the primary return burden.
- **Use synthetic prices for the qualifying paper market path:** is useful for deterministic acceptance fixtures but cannot demonstrate operation against real production timing, liquidity, spread, depth, gaps, and market behavior.
- **Send qualifying paper orders to Binance Testnet:** validates real API protocol handling but its artificial assets, liquidity, and reset behavior do not provide production-market execution evidence.
- **Send tiny production orders during paper qualification:** produces real execution evidence but is live trading and would bypass the mandatory first-live approval and capital authorization boundary.
- **Run no deliberate faults and accept natural incidents:** may complete 30 quiet days without ever proving restart, ambiguity, late-fill, backoff, or external-alert behavior.
- **Run an exhaustive chaos program during qualification:** adds unnecessary operational variability to the MVP; the bounded suite covers the named promotion failure scenarios and leaves broader resilience testing for later increments.

### Two-step evidence-bound first-live activation

Selected by the operator on 2026-07-15: passing every historical, replay, production-data paper, Testnet, accounting, reconciliation, risk, and operational gate never starts live trading. First-live activation requires two separate deliberate actions by the single operator: approval of one sealed promotion bundle, followed by a re-authenticated confirmation authorizing exactly one live start within 15 minutes.

#### Step 1: promotion approval

The system generates a human-reviewable promotion bundle and a machine-verifiable manifest. The bundle identifies at least:

- the exact decision-critical build, source revision, dependency lock, event/accounting schemas, and deterministic replay identity;
- the immutable strategy/configuration version, symbol, grid parameters, quantized rung plan, activation semantics, bootstrap obligations, and terminal behavior;
- the production Binance account or sub-account identity and permission profile, allocation identity, `250 USDT` ceiling, exact proposed native-asset allocation, fee reserve, risk-profile version, and deployment identity;
- every historical, walk-forward, panel, regime, DSR, holdout, fidelity-parity, paper, Testnet, reconciliation, invariant, fault-drill, availability, activity, and incident result consumed by the decision;
- all applicable dataset, market-archive, venue-rule, fee-rate, executable-build, report, and evidence digests; and
- a zero-unresolved-gate statement plus any diagnostic warnings that do not affect authorization.

Approval requires the operator to inspect this bundle and explicitly accept its exact digest. It creates a pending activation authorization, not an order and not a running grid. A failing, missing, expired, superseded, or unresolved mandatory item prevents approval; a UI acknowledgement cannot override a hard gate.

#### Step 2: re-authenticated activation confirmation

Within 15 domain minutes of approval, the operator must re-authenticate and confirm one live activation. Immediately before confirmation and again immediately before any executable bootstrap command is durably authorized, the runtime performs a fail-closed live preflight using fresh authoritative evidence. It proves at least:

- the approved build, configuration, symbol, risk profile, deployment, account/sub-account, API-key permission set, and allocation identity still match the approved manifest;
- the current price is strictly inside the configured bounds and every accepted activation-eligibility rule passes;
- current venue filters, order limits and headroom, fee rates/assets, balances, allocations, reservations, foreign orders, connectivity, clock synchronization, market/account stream continuity, persistence, alerts, and control paths satisfy their accepted freshness and safety requirements;
- the exact quantized bootstrap and initial order plan remains fully funded inside the `250 USDT` ceiling and maximum planned inventory; and
- there is no unresolved reconciliation item, incident, unknown command outcome, conflicting evidence, or invariant failure.

The resulting authorization is bound to the promotion-bundle digest and exact activation context, is single-use, and expires 15 minutes after promotion approval. It authorizes one activation attempt only; success, confirmed rejection, uncertain transmission, operator cancellation, expiration, or a failed preflight consumes or invalidates it. An uncertain bootstrap outcome enters the accepted frozen reconciliation path and can never be treated as permission to issue a second bootstrap.

Decision-critical build, configuration, strategy semantics, evidence, risk profile, deployment, account/sub-account identity, permission, allocation, fee treatment, or venue-rule changes invalidate the authorization and require a newly generated bundle and fresh approval. Ordinary price or order-book movement does not by itself rewrite the historical bundle, but every activation-dependent market observation must be refreshed and pass preflight; price leaving the bounds or another eligibility failure rejects the activation. Unrelated whole-account movement is not automatically invalidating unless it changes allocation coverage, permissions, order headroom, fee coverage, reconciliation, or another decision-material condition.

No scheduled job, passing gate, paper completion, Testnet completion, deployment, process restart, or API caller may synthesize either operator action. The same person may perform both steps; separation is temporal and intentional rather than a two-person-control requirement. Every view, digest, approval, authentication event, preflight input/result, confirmation, expiry, invalidation, command authorization, and outcome is durably retained and exactly replayable where decision-relevant.

Example: the operator reviews bundle `P7`, whose digest binds build `B12`, BTC/USDT configuration `C4`, the production sub-account, `250 USDT` allocation `A2`, and risk profile `R3`, then approves it at 18:00 UTC. At 18:08 the operator re-authenticates. Fresh evidence shows price inside the bounds, unchanged venue rules and permissions, sufficient allocated assets and fee reserve, zero foreign-order headroom conflict, and zero unresolved reconciliation, so one activation is confirmed and the authorization is consumed. If the symbol filter changes at 18:05, the authorization is invalidated and a regenerated plan and bundle are required. If only price changes but remains eligible, the live preflight uses the fresh price without altering the sealed historical results.

Consequences:

- Research and operational success can recommend promotion but can never grant executable authority automatically.
- The operator sees exactly what is being trusted, while the machine prevents approval of a report that does not match the executable deployment.
- The short, single-use window limits stale account, permission, venue-rule, and allocation evidence without requiring a second human operator.
- Fresh activation eligibility remains authoritative; approval cannot force an out-of-range, underfunded, unreconciled, or unsafe start.
- Later capital increases, new symbols, configuration changes, decision-critical fixes, or account changes require explicit new evidence and authorization rather than inheriting first-live approval.

Declined alternatives:

- **One confirmation that both accepts evidence and starts the grid:** is simpler but makes careful review and executable authorization one accidental action and weakens the audit boundary.
- **Approval followed by a mandatory 24-hour cooling-off period:** encourages deliberation but makes market, account, permission, fee, and venue evidence stale and adds friction disproportionate to the capped personal MVP.
- **Automatic activation when all gates pass:** removes the operator's final capital decision and permits a research or operational pipeline to acquire real-money authority.
- **Two-person approval:** offers stronger organizational separation but is unnecessary and impractical for the explicitly single-operator personal MVP; it remains a later organizational-control option.

### Thirty-day first-live probation

Selected by the operator on 2026-07-15: the first real-money activation remains a probationary run for 30 consecutive elapsed days under the exact approved decision-critical build, immutable strategy configuration, production account/sub-account, allocation identity, maximum `250 USDT` capital envelope, and risk profile. Probation begins when the first executable live activation command is durably authorized; an ambiguous first command therefore cannot create an unobserved pre-probation exposure.

The system does not describe the run as normally validated live operation merely because activation succeeded. During probation:

- no configuration, strategy semantics, symbol, account/sub-account, allocation identity, decision-critical build, risk-profile, or capital-ceiling change is permitted;
- profit cannot compound into larger rung principal, planned inventory, or authorized capital;
- all live commands, acknowledgements, venue executions, fees in their actual assets, balances, orders, inventory, risk transitions, reconciliation observations, incidents, alerts, recovery actions, operator actions, and market/account evidence remain durably attributable to the approved promotion bundle;
- safe restarts and repaired transport interruptions do not restart or pause elapsed time, but all unavailable and frozen intervals remain visible and every accepted recovery must preserve exact state, reconciliation, invariants, and replay;
- the operator performs and durably acknowledges one evidence review for each of the first seven UTC observation days and at least one review in each subsequent seven-day interval through probation completion or failure, including any activity-based extension through day 90; and
- the run remains under the accepted automatic risk controls at all times; an operator review can restrict or stop authority but can never waive a limit or invariant.

Each review presents, at minimum, current conservative grid equity and return, realized paired-cycle result, fees and fee assets, inventory and reservations, effective and foreign orders, order/fill/account reconciliation, range and safety posture, loss-limit proximity, post-only rejection/retry behavior, stream and control-path continuity, restart/recovery outcomes, alerts/incidents, replay result, and divergence from the corresponding paper/execution assumptions. The acknowledgement binds the exact review snapshot and records any required action. A missed review does not silently mark the run safe or permit later evidence to overwrite the omission; it blocks successful probation completion and invokes the separately specified operator-unavailability policy where timely action is required.

The minimum 30 elapsed days alone do not constitute a pass. Successful completion requires the accepted live-activity gate below, all required reviews, complete attributable evidence, zero unresolved decision-material reconciliation items or critical incidents, passing accounting/risk/order invariants, and exact decision replay. A terminal stop, operator closure, invalidating change, unsafe or non-replayable recovery, unexplained balance/order/fill difference, or other declared rollback condition ends the probation attempt. The evidence remains diagnostic, but a later attempt starts under a new explicit approval rather than splicing days.

Range-exhausted waiting, a valid `REDUCE_ONLY` interval, or a safely recovered `FROZEN` interval does not automatically reset the 30-day elapsed period because each can be correct live behavior. It remains fully reported and may still prevent successful completion when the later acceptance criteria show insufficient real execution, excessive restriction, or an operational failure. The clock is never paused to remove unfavorable or inactive time.

Completing probation grants no capital increase, new symbol, new grid, configuration change, compounding, or automatic production status. It creates first-live evidence that may support a separate future promotion and scaling decision with a new quantitative profile and explicit authorization. One-month live profit is reported and compared with historical and paper expectations, but is not a standalone profitability gate; the five-year development and holdout evidence remains the primary economic basis.

Example: the live grid activates at 14:20 UTC on 1 August. A safe restart on day 4 takes nine minutes and reconstructs every order, fill, reservation, fee, and balance exactly, so probation continues and the interval remains visible. The operator acknowledges daily reviews for days 1–7 and reviews on days 14, 21, and 28. At 14:20 UTC on 31 August, 30 elapsed days have passed. Completion is still refused if one fee remains unexplained or a required review is missing; it cannot be repaired by ignoring that day or extending only through a favorable week.

Consequences:

- The first live exposure remains explicitly experimental even after extensive historical, paper, and Testnet qualification.
- Daily early review detects integration or accounting surprises quickly, while weekly later review is proportionate to a capped personal deployment.
- Consecutive evidence prevents selection of only favorable live days and exercises real venue fees, execution, reconciliation, alerts, and recovery.
- The probation remains operational evidence rather than a statistically unsupported one-month return test.
- Scaling stays a separate deliberate decision instead of becoming an implicit reward for surviving 30 days.

Declined alternatives:

- **Fourteen-day probation:** provides faster feedback but covers less real execution, fee, restart, reconciliation, and market-condition variation before a later scaling decision.
- **Seven-day probation:** is useful as a technical smoke test but is too short to serve as the accepted first-live observation period.
- **No fixed probation:** treats one successful activation as normally validated operation and provides no explicit experimental boundary or completion evidence.
- **Automatic capital increase after 30 days:** confuses operational observation with authorization and bypasses new scale-specific risk, venue-validity, and strategy evidence.

### Tiered fail-closed probation abort

Selected by the operator on 2026-07-16: a serious first-live failure aborts probation through the accepted safety-posture state machine rather than through one unconditional liquidation or an ad-hoc operator choice. The immediate response depends on whether material state is uncertain or terminal danger is already authoritatively established; no failure permits automatic resume, silent evidence repair, or automatic software rollback.

#### State-uncertain or decision-critical failure

An unknown or conflicting order, fill, balance, fee, inventory, reservation, allocation, accounting, command, persistence, replay, or decision-critical software outcome selects `FROZEN` immediately. The runtime blocks placement and replacement, requests cancellation of managed orders where the authenticated control path and known evidence make cancellation safe, preserves every original fact, queries Binance authoritatively, admits late evidence, and reconciles before any disposal or replacement decision.

The same response applies to an unauthorized command, possible duplicate, missed admitted fill, unexplained decision-material difference, broken hard invariant, lost critical evidence, non-replayable decision, unsafe recovery, capital/permission breach, or a defect capable of changing economic or safety decisions. A terminal trigger detected during uncertainty remains irreversibly latched, but `FROZEN` retains precedence until exact exposure and safe disposal authority are established.

Once reconciliation establishes authoritative state:

- if the global stop-loss, emergency-stop, or another accepted terminal condition is latched, the existing bounded terminal-disposal workflow becomes effective and the run can close only after exact final reconciliation;
- if no terminal condition exists, the affected probation still has no automatic trading resume: the operator ends or restricts the affected run under the accepted operator-stop/retained-holding semantics, records the incident and disposition, and any later live activation requires a new promotion decision; and
- if material inventory cannot yet be disposed within accepted bounds, the run remains visibly frozen with the terminal or probation-abort latch and a critical alert rather than being labelled closed, flat, or successfully rolled back.

Not every deliberately tested or safely recovered restriction is a probation abort. A planned restart, bounded explained anomaly, or transient incident explicitly permitted by the probation profile may preserve the clock only when it satisfies its existing deadlines, reconciliation, invariant, incident, review, and replay requirements. The abort boundary is crossed by the terminal conditions above or by a declared probation-critical evidence, correctness, authorization, or safety failure; later evidence cannot retroactively turn that failed probation into a pass.

#### Evidence-sufficiency failure without confirmed danger

A missing required operator review, insufficient real execution evidence, incomplete diagnostic comparison, or another non-safety completion shortfall prevents probation from passing but does not by itself authorize an unnecessary market sale. The run follows its current valid safety posture while the failure and available evidence are reported. Any operator-unavailability or other independent safety trigger still applies normally.

Continuing observation cannot erase a mandatory missed review or splice the invalid interval into a passing attempt. If the operator elects to stop, inventory is handled through the accepted operator-stop disposition. A later qualifying attempt receives a fresh identity and cannot inherit elapsed days, reviews, fills, or incident-free intervals from the failed attempt.

#### Re-entry and software-version rules

After an abort, re-entry to live trading requires:

1. authoritative final state and zero unresolved decision-material reconciliation items for the affected run;
2. a durable incident report identifying trigger, timeline, commands, exposure, economic result, evidence gaps, root cause where determinable, containment, disposition, and affected contracts/evidence;
3. a corrected decision-critical build, configuration, environment, or operational control where correction is required;
4. requalification of every affected gate under the separately specified evidence-invalidation matrix;
5. a new sealed promotion bundle and two-step evidence-bound activation; and
6. a new 30-consecutive-day first-live probation when the candidate returns to first-live status.

An earlier or corrected software version may not be deployed merely because it is called a rollback. While any venue order, execution, balance, inventory, allocation, journal position, schema transition, or exposure is unresolved, no version change may acquire order authority. A later deployment must prove state/schema compatibility, exact replay through the handover boundary, authoritative reconciliation, and new activation authority. Repository rollback, deployment rollback, economic inventory disposition, and promotion rollback are distinct operations and cannot substitute for one another.

Example: a live buy submission times out on day 9. Because Binance may have accepted or filled it, the runtime selects `FROZEN`, sends no replacement, and queries by the original managed identity. It discovers that the order filled and that the private event was missed. The fill and fee are admitted and balances reconcile, but the missed decision-critical evidence violates the probation-critical continuity rule. The system cancels remaining managed orders safely, records the incident, and does not resume the old probation. It does not immediately sell while the fill is unknown, and it does not deploy a prior build over the unresolved state. If the terminal equity floor had also been crossed, that latch would survive reconciliation and then authorize bounded terminal disposal.

Consequences:

- Uncertainty is contained before economic action, preventing duplicate orders and liquidation based on guessed exposure.
- Confirmed terminal danger still receives irreversible bounded disposal once authoritative evidence makes commands safe.
- Evidence-only shortcomings cannot masquerade as safety triggers or force avoidable conversion costs.
- A failed probation cannot be repaired by deleting an incident, extending only favorable days, or swapping software in place.
- Re-entry is auditable and proportional because the next decision can rerun affected evidence rather than automatically repeating unrelated research.

Declined alternatives:

- **Liquidate after every probation failure:** is simple but can submit the wrong quantity, duplicate an unknown execution, or force an unnecessary loss before exact state is known.
- **Freeze and retain inventory after every failure:** avoids premature sale but fails to execute the already accepted irreversible terminal-disposal policy when danger is confirmed.
- **Operator chooses every response case by case:** is flexible but makes safety depend on judgment under pressure and prevents deterministic backtest, replay, paper, Testnet, and live parity.
- **Automatic deployment rollback and resume:** confuses code deployment with economic recovery and can give an old build authority over incompatible or unresolved live state.

### Change-impact evidence invalidation and requalification matrix

Selected by the operator on 2026-07-16: every change made after qualifying evidence exists receives a durable evidence-impact assessment before any evidence is reused or any promotion authority is granted. The assessment follows declared dependency and contract relationships from changed source, configuration, data, schema, dependency, infrastructure, venue behavior, or operating control to every affected decision and evidence artifact. It reruns the smallest sufficient affected set, but uncertainty is always classified upward into the stricter category.

Evidence reuse is never justified only by an unchanged strategy parameter file, a passing unit test, a familiar filename, semantic-version wording, or developer judgment. Reuse requires a machine-verifiable non-impact attestation identifying:

- the prior and proposed component, dependency, schema, configuration, data, environment, and contract digests;
- the exact changed surfaces and their transitive consumers;
- every evidence artifact proposed for reuse and why none of its inputs, decisions, states, outputs, invariants, metrics, or interpretation can change;
- deterministic compatibility/equivalence tests and their retained results;
- the reviewer, classification, time, assumptions, and any unresolved uncertainty; and
- the strictest applicable row of the matrix below.

When one change spans several rows, the union of their rerun obligations applies. A lower row cannot compensate for or waive a higher-impact obligation. All regenerated or reused artifacts appear in a new promotion-bundle manifest; prior bundles remain immutable and lose activation authority when invalidated.

#### Requalification matrix

| Change class | Typical examples | Minimum mandatory evidence response |
| --- | --- | --- |
| **A — Strategy, selection, economic, or risk semantics** | grid or bootstrap behavior; parameter values/domains; candidate selection/ranking; activation/range/stop semantics; accounting or fee meaning; fill/slippage model; capital, inventory, order, or loss limits; compounding; a new symbol; material dataset correction; loosened or behavior-changing risk policy | Invalidate the candidate and historical promotion bundle. Repeat affected research development under a new declared trial family, freeze a new candidate, and use a newly eligible unexposed 12-month holdout. Then repeat full production-data paper qualification, affected Testnet qualification, promotion approval, activation, and first-live probation. |
| **B — Shared decision, accounting, reconciliation, replay, or risk implementation** | a defect or schema/algorithm change that can alter canonical events, event ordering, timers, decisions, orders, fills, postings, balances, inventory, risk posture, reconciliation, recovery, or replay | Recompute all affected historical development paths and metrics from immutable source evidence. Re-evaluate selection if rankings or gate outcomes can change. Because the correction follows exposure to prior promotion results, obtain a newly eligible holdout wherever the change can affect holdout decisions or outputs. Repeat every affected paper, Testnet, fault, recovery, invariant, promotion, and first-live stage. |
| **C — Production market-data or paper-execution boundary** | trade/BBO/depth ingestion, continuity repair, timestamp normalization, paper acknowledgement/fill/queue/participation behavior, simulated fees, or local paper private-event lifecycle | Retain unrelated research only with non-impact proof. Repeat affected historical event replay when the same normalization or execution contract is used, and repeat the complete 30-to-90-day production-data paper qualification with its availability, natural-activity, fault, reconciliation, parity, and replay evidence. Repeat Testnet cases only where shared contracts or components are affected. |
| **D — Binance command/account adapter or live operational boundary** | signing, timestamps, REST/WebSocket parsing, client identities, submit/query/cancel handling, account/trade reconciliation transport, rate-limit behavior, secrets/permissions, deployment process, persistence driver, alert/control path, or recovery orchestration with proven unchanged canonical strategy/accounting semantics | Historical and production-paper economic evidence may be reused only with component-boundary equivalence and non-impact proof. Repeat every affected Testnet scenario, the seven-day Testnet soak when its build/contract identity changes, and applicable restart, persistence, alert, recovery, reconciliation, security, and deployment acceptance cases. Generate a new promotion bundle and activation authority; repeat first-live probation when the change follows or aborts first-live operation. |
| **E — Non-decision presentation or reporting** | copy, visual layout, accessibility, read-only filtering, export formatting, or diagnostic report rendering that cannot influence commands, state, evidence calculation, approval context, or operator interpretation of a mandatory gate | Regenerate and verify affected reports/UI acceptance evidence. Reuse trading evidence only after proving read-only isolation and unchanged underlying evidence digests. A changed value, gate interpretation, approval display, warning severity, control, or writable path is not class E. |

#### Mandatory classification rules

- A strategy configuration value change is class A even when code is unchanged.
- A dependency, compiler/runtime, database, schema, clock, serialization, numeric, or infrastructure change is classified by behavior and consumers, not by the label “maintenance.” If decision impact cannot be excluded, it is at least class B.
- A risk change that only tightens authority still reruns every stage whose decisions or results can change. A loosened ceiling or threshold also requires a newly approved quantitative profile and cannot inherit evidence collected under the stricter behavior as proof of the looser behavior.
- A source-data correction after holdout exposure invalidates the prior historical bundle under the already accepted holdout rule. Corrected old-holdout output is retained diagnostically, while promotion requires a new candidate freeze and newly eligible holdout rather than treating the exposed corrected period as sealed again.
- An execution or venue-rule update that makes a previously valid plan invalid blocks activation immediately even if historical economics are unchanged. Current venue validity is always re-proven at live preflight.
- A fix made in response to paper, Testnet, or live observations cannot claim those same observations as independent qualification of the fix. The changed stage and all downstream stages run again under the new identity.
- Pure refactoring may reuse evidence only when deterministic characterization, replay, public-contract, and artifact-equivalence tests prove unchanged decision outputs for all applicable retained inputs. Otherwise it assumes the class of the behavior it could affect.
- Security-only changes that alter credentials, identities, permissions, secrets access, network authority, or operator authentication are at least class D even when trading algorithms are untouched.
- A class E interface becomes class D or higher when it can approve, activate, stop, resume, modify configuration, hide a mandatory warning, misstate a gate, or write evidence.

#### Dependency-manifest and approval procedure

Before the changed build becomes eligible for promotion, the system produces one impact manifest containing the change set, old/new digests, affected bounded contexts, classification, dependency traversal, reused evidence, invalidated evidence, required reruns, completed reruns, equivalence results, and open questions. The manifest itself is immutable evidence and is included in the next promotion bundle.

The operator approves the impact classification when reviewing the new promotion bundle; approval cannot downgrade an unresolved or technically unproven impact. Any later discovery that a reused artifact was affected invalidates the bundle, freezes any active promotion authority, and invokes the probation-abort policy if live decisions may be wrong. Evidence is appended and superseded, never edited to appear as if it had been produced by the new build.

Example: a defect is fixed in Binance REST timeout reconciliation while the canonical decision, accounting, and paper-execution contracts are unchanged. Dependency and equivalence evidence classify it as D. Historical walk-forward, holdout, and production-paper economics remain attributable to unchanged component digests; the affected ambiguous-submit/cancel, identity, account reconciliation, restart, and backoff Testnet scenarios rerun, followed by a fresh seven-day soak, operational recovery cases, new promotion bundle, and new activation. If investigation reveals that the defect could duplicate a canonical fill posting, classification rises to B, accounting/replay evidence and every affected upstream/downstream stage rerun, and prior holdout independence cannot be asserted.

Consequences:

- Small isolated fixes do not automatically incur five years of research and another month of paper evidence.
- Economic or decision-semantic changes cannot hide behind a narrow code diff or unchanged strategy parameters.
- Evidence reuse remains auditable because it is attached to stable component and contract identities rather than one opaque monolithic version label.
- The architecture must expose deep module boundaries and explicit evidence dependencies, supporting maintainability and later venue/strategy extensions without weakening promotion safety.
- Holdout independence and forward-stage independence survive bug fixes and data corrections instead of being retroactively claimed.

Declined alternatives:

- **Repeat every stage after every change:** is simple and conservative but wastes months for proven presentation- or adapter-isolated changes and discourages small safety fixes.
- **Developer judgment without a fixed matrix:** is fast but produces inconsistent evidence reuse and cannot be audited or replayed as a promotion decision.
- **Reuse everything when strategy parameters are unchanged:** ignores accounting, execution, data, risk, reconciliation, venue, security, and operational defects that can change real outcomes.
- **Classify from changed filenames or package names:** assumes the existing module boundary is truthful and misses transitive behavior, configuration, schema, dependency, and data effects.

### Modest first-live activity gate with bounded extension

Selected by the operator on 2026-07-16: successful first-live probation must demonstrate a small amount of genuine Binance production execution in addition to elapsed time and operational correctness. The unchanged probation requires all of:

- at least 30 consecutive elapsed days from the first durably authorized executable activation command;
- at least one real completed cumulative paired grid cycle; and
- ordinary managed live-grid fills on at least two distinct UTC calendar days.

A **live fill-active day** is a UTC date on which Binance authoritatively reports at least one partial or full execution of an ordinary managed rung order for the probation run. Multiple executions on the same date count as one day. A partial execution can establish a fill-active day but cannot inflate cycle count. One **real completed paired cycle** is counted only when the cumulative initial rung order and its canonical cumulative paired obligation have both completed under the existing cycle identity and all actual native-asset fees have posted or been authoritatively bounded and reconciled.

Bootstrap acquisition, initial backing placement without execution, terminal disposal, operator-stop execution, retained holdings, foreign account orders, manual trades, balance transfers, injected events, fixtures, paper fills, and Testnet fills do not count. A fill discovered late through authoritative reconciliation retains its real event time and counts only if the evidence remains complete and the late discovery does not independently invalidate probation. Orders that rest or cancel without execution are operational evidence but are not fill activity or completed cycles.

If both activity requirements are satisfied by day 30, probation may complete at the day-30 boundary when every other review, evidence, reconciliation, invariant, incident, and replay requirement passes. If either is missing, the same build, configuration, symbol, account/sub-account, allocation, `250 USDT` ceiling, risk profile, run identity, journal, high-water mark, and evidence chain continue without interruption until both requirements pass or day 90 is reached. No parameter, bound, rung size, stop, activation price, or order behavior may be changed to manufacture activity.

All economics, safety postures, unavailable/frozen intervals, reviews, alerts, incidents, reconciliations, venue facts, and replay evidence remain measured through the full extension. The weekly review cadence continues. Days, fills, cycles, or losses cannot be removed, reordered, carried from another run, or selected after outcome inspection.

If the requirements first become complete on day 47, the probation observation endpoint is day 47 rather than day 30 or day 90. If day 90 arrives without both, the attempt fails for **insufficient live activity evidence**, not for zero profitability. Probationary authority then permits no new exposure: the effective posture is at least `REDUCE_ONLY`, managed buys are cancelled under the accepted rules, valid backed sells may reduce existing inventory, and the operator selects the accepted stop/retained-holding disposition. Observation cannot continue indefinitely to turn the failed attempt into a pass; a later attempt requires new promotion authority and begins its own clock and activity counts.

There is no standalone first-live return minimum. Actual total return, realized cycle result, fees, inventory exposure, drawdown, range exhaustion, benchmark comparison, and divergence from historical/paper execution assumptions remain mandatory reported evidence. The long historical development and holdout gates remain the primary profitability basis; one to three live months are too regime-dependent to retune or reject a strategy solely by return. Independent loss, stop, accounting, reconciliation, and safety rules remain hard failures regardless of activity.

Example: by day 30 the live grid has three partial fills across two UTC days, but the paired sell for the cumulative buy is still incomplete. The fill-day gate passes and the cycle gate does not, so the immutable probation continues. The paired sell completes on day 38 with actual BTC and USDT fees reconciled; probation may complete then if every other requirement passes. If no pair completes by day 90, the system blocks further buys and reports insufficient live activity rather than calling the run profitable, unprofitable, or successfully qualified.

Consequences:

- First-live completion proves at least one real order-pair, fee, inventory, and reconciliation path rather than only process uptime.
- The threshold is deliberately lighter than paper qualification, limiting pressure toward narrow high-turnover grids or unnecessary real exposure.
- Bounded extension accommodates a quiet market while keeping the experimental period finite.
- Actual losses remain visible but cannot dominate the stronger multi-year economic evidence through a one-month profit rule.
- Failure to obtain activity stops exposure growth without forcing an economically unnecessary immediate liquidation.

Declined alternatives:

- **Thirty days regardless of activity:** may pass without one real execution, actual fee, paired obligation, or inventory cycle.
- **Two cycles and three live fill-active days:** provides more evidence but duplicates the paper threshold and biases the first-live profile further toward turnover.
- **Continue without a maximum until activity occurs:** can leave the system in experimental live status indefinitely and encourages waiting selectively for a favorable period.
- **Require positive first-live return:** overweights one short future regime and invites post-activation tuning despite the accepted historical profitability gates.

### Continuous pre-activation evidence freshness chain

Selected by the operator on 2026-07-16: promotion evidence remains activation-eligible through a continuous, source-timestamped chain from the locked historical holdout into production-data paper, concurrent Testnet qualification, promotion approval, and the 15-minute activation authorization. Long-horizon historical evidence does not expire merely because a fixed number of calendar days passes while fresh unchanged forward evidence continuously bridges it to activation.

The chain has these mandatory boundaries:

1. The qualifying production-data paper clock must start no later than 30 consecutive elapsed days after the locked holdout observation endpoint. The same frozen candidate, selection procedure, critical semantics, and evidence identities used by the historical bundle must enter paper; the gap cannot contain tuning, substituted evidence, or an unclassified decision-critical change.
2. Paper and Testnet may run concurrently under their separate identities and ledgers. After each reaches its accepted minimum qualification, its observation remains open and continuously governed by all of its continuity, availability, reconciliation, incident, invariant, activity, replay, reset, and immutability rules until promotion approval. Passing on an earlier day cannot hide a later failure.
3. At promotion approval, the latest complete captured paper evidence endpoint and the latest authoritative Testnet/account reconciliation endpoint must each be no more than 24 elapsed hours old. Both endpoints must report zero unresolved decision-material items and no intervening invalidating event.
4. The Testnet evidence must still belong to the same current account generation that completed the applicable mandatory scenarios and seven-day reset-free soak. A Testnet reset at any time before approval or activation invalidates that generation's current qualification; a new authoritative baseline, applicable reset-dependent scenarios, and a new seven-day soak are required, while proven unaffected scenario evidence may be reused under the change-impact matrix.
5. Promotion approval creates only the already accepted single-use activation authorization. Confirmation remains limited to 15 minutes, and the immediately preceding activation preflight applies the stricter second-level freshness, venue-rule, account, permission, allocation, reconciliation, market, control-path, and risk deadlines from the safety specification.

“Remain running” means the qualifying observation and evidence process remains operationally continuous, not that orders must always rest or that the strategy must generate activity. Safe planned restarts, range exhaustion, and permitted restricted postures preserve the chain only under their existing exact continuity and recovery rules. A stopped process with an unclassified decision gap, an unrepairable market/account evidence gap, a closed qualifying run, an expired account generation, or a post-pass critical incident breaks the chain. Data cannot be backfilled after the fact to pretend that online decisions were continuously available when the runtime was not operating.

If current price is outside the configured activation bounds, the operator simply withholds promotion approval while paper and Testnet evidence continue. No stale 15-minute authorization is created and no acquisition occurs. Ordinary market movement therefore does not force historical requalification, but all forward stages must remain valid until a later eligible activation instant.

#### Broken-chain behavior

- If paper did not start within 30 days of the locked holdout endpoint, the historical-to-forward link is stale. The old evidence remains diagnostic, but activation requires an updated historical promotion sequence ending in a newly eligible, previously unexposed holdout under the frozen selection governance; the exposed old holdout cannot be relabelled as sealed.
- If production-data paper loses its qualifying chain after it started or passed, the affected paper stage restarts its full 30-to-90-day qualification on the unchanged or requalified identity as required by the impact matrix. Earlier days remain evidence but cannot be spliced into the new clock.
- If Testnet resets or its chain becomes invalid, the current generation is closed and a new generation completes the required baseline, affected scenarios, and seven-day soak. Production paper does not restart solely because Testnet reset.
- If only the 24-hour promotion endpoint age is missed while both qualifying observations actually continued without an invalidating event, their manifests may advance to a new complete endpoint and become current; no stage reruns merely because the operator waited to review the next complete snapshot.
- If a build, configuration, contract, data, account, permission, risk, venue, or infrastructure change occurs, the accepted change-impact matrix determines the union of invalidated and reusable evidence. Freshness can never excuse a change-impact rerun.

All boundary times use authoritative UTC event/observation timestamps and exact durations before presentation rounding. The promotion bundle records every endpoint, gap, chain edge, freshness calculation, generation identity, ongoing qualification result, and invalidation. Evidence that becomes stale remains immutable and auditable; it loses activation authority rather than being deleted.

Example: the locked holdout ends at 00:00 UTC on 1 January and production paper begins on 20 January, so the historical-to-paper gap is 19 days. Paper qualifies on 20 February but continues unchanged. Testnet qualifies on 5 February and continues on the same generation. On 25 February, both latest complete manifests end less than 24 hours before approval, so the chain may be current. If Testnet resets one hour before approval, Testnet qualification is invalid even though its earlier seven-day soak passed; paper remains valid, while the new Testnet generation must re-establish its required evidence. If instead the operator waits until April while both observations remain valid and current, historical evidence does not expire merely because more than 90 or 180 calendar days passed.

Consequences:

- Promotion remains connected to recent real market, account, venue, and operational behavior without repeatedly discarding valid five-year research.
- Keeping qualified paper and Testnet observation open exposes failures that occur after their minimum duration rather than freezing a favorable endpoint.
- The 30-day initial bridge limits activation from an old historical regime, while the continuous forward chain accommodates a 30-to-90-day paper activity extension.
- Environment resets and stage-specific failures invalidate only their affected chain segment when independence is proven.
- Operators can wait for price to re-enter the grid bounds without approving stale authority or changing the candidate.

Declined alternatives:

- **Fixed 180-day expiration for the whole bundle:** is simple but declares continuously operating forward evidence stale solely because of an arbitrary calendar boundary.
- **Repeat full qualification every 90 days before activation:** maximizes recency but needlessly repeats five-year research and month-long paper evidence even when an unbroken forward chain remains current.
- **No evidence-age or continuity limits:** can activate a candidate long after the market, account, Testnet generation, venue contract, and operational evidence ceased to be representative.
- **Freeze paper/Testnet evidence at the first passing instant:** permits failures after that instant to be ignored while the operator waits for activation.

### Five-scenario adverse execution sensitivity panel

Selected by the operator on 2026-07-16: after the normal selection procedure freezes one proposed candidate, exactly five additional deterministic adverse execution sensitivities test whether modest error in cost and fill assumptions destroys its result. The panel is a bounded falsification check, not another search, candidate-ranking input, or permission to alter the strategy.

The five scenarios are:

1. **Higher fees:** increase applicable maker, taker, bootstrap, conversion, and disposal fee assumptions in their actual assets while leaving all other promotion assumptions at baseline.
2. **Worse spread and aggressive-order slippage:** worsen only the execution prices/costs for bootstrap acquisition, required conversion, terminal valuation, and bounded aggressive disposal; ordinary resting maker fills remain at their limit prices.
3. **Scarcer executable liquidity:** reduce the eligible non-reusable volume participation and increase queue-ahead where genuine book/queue evidence exists, producing fewer or later fills without inventing volume.
4. **Longer command latency and post-only rejection exposure:** delay placement/cancellation arrival before applying the same `LIMIT_MAKER` eligibility rule, so additional rejection or missed placement arises only from the observed market path and bounded retry semantics rather than an arbitrary favorable fill.
5. **Combined adverse execution:** apply the exact accepted settings from scenarios 1–4 simultaneously.

Each scenario uses the same immutable candidate, activation boundaries, data partitions, event order, capital, risk profile, accounting, terminal behavior, and random/deterministic identities as its corresponding baseline evidence. Only the named adverse assumption changes. Values are frozen before the panel is run, manifested exactly, and never adjusted after seeing results.

#### Balanced adverse settings

Selected by the operator on 2026-07-16: apply these exact deterministic settings:

1. **Fees:** for every modeled fee event, use the greater of `1.25 ×` the baseline applicable rate and the applicable non-discounted rate in the frozen fee schedule. Preserve the venue-valid fee asset, quantity rounding, conversion valuation, and posting semantics; the stress cannot assume a discount asset that is unavailable.
2. **Aggressive execution cost:** for each bootstrap acquisition, required fee-asset conversion, terminal valuation, and bounded aggressive disposal, let `c` be the baseline adverse spread-plus-slippage cost as a fraction of notional. Use `max(1.50 × c, c + 0.0005)`. The `0.0005` increment is five basis points, or `0.05%`. Apply the worse effective execution price without changing reference price, quantity, order bounds, or ordinary maker fill price.
3. **Executable liquidity:** reduce the accepted maximum non-reusable participation from `5%` to `2.5%` of eligible observed volume. Where the promotion replay has an evidenced queue-ahead quantity, multiply that quantity by `2`. Preserve source precision and never invent absent depth or volume.
4. **Latency and maker eligibility:** for each modeled placement, cancellation, acknowledgement, and decision-material delivery delay, use `max(2 × baseline delay, baseline delay + 500 milliseconds)`. Evaluate venue arrival and `LIMIT_MAKER` eligibility against the observed market state at the delayed arrival time. Any resulting confirmed would-take rejection follows the existing bounded post-only retry sequence; no random rejection percentage is injected.
5. **Combined:** apply settings 1–4 together, with no offset, netting, or relaxation because another stress reduces trading activity.

Example: if an aggressive bootstrap has a baseline fee of `0.10%` and adverse spread-plus-slippage cost of `0.08%`, the fee stress is `0.125%`. The execution-cost stress uses the worse of `0.12%` (`1.5 × 0.08%`) and `0.13%` (`0.08% + 0.05%`), therefore `0.13%`. A baseline 300-millisecond placement delay becomes the worse of 600 and 800 milliseconds, therefore 800 milliseconds.

#### Evidence scope and pass rules

- The fee-only and aggressive-cost-only scenarios run across the complete non-duplicated rolling and expanding out-of-sample paths and both full holdout fidelities because those assumptions are representable there.
- Liquidity, queue, latency, and delayed maker eligibility run on every declared detailed development replay period and the complete event-level holdout. Minute evidence cannot create queue or sub-minute arrival claims.
- The combined mandatory economic result is the complete event-level holdout, where all four adverse dimensions can be represented together. Detailed development stress periods remain required falsification evidence but are not selectively concatenated into a new return estimate.
- Every complete rolling, expanding, minute-holdout, or event-holdout scope to which a scenario applies must have exact net total return greater than zero on the full `250 USDT` allocation denominator after all stressed costs. It need not retain the baseline's `0.75%` quarterly, `5%`/`3%` annualized, or `4%` holdout minimum; those remain baseline gates.
- Every sensitivity must retain valid accounting, reconciliation, capital, reservation, inventory, order, fee, risk, lifecycle, terminal-disposal, and exact replay behavior. A correctness or evidence-integrity failure makes the panel incomplete, not economically negative.
- No sensitivity may trigger the immutable global terminal stop in any mandatory scope. Ordinary `REDUCE_ONLY`, range exhaustion, missed fills, post-only rejection, and lower cycle activity remain visible consequences and do not fail by themselves when every other stress rule passes.
- The combined event-level holdout must independently remain net-positive and avoid the global terminal stop. Equality to zero fails before display rounding.
- Individual and combined results, baseline deltas, fills, cycles, fees, inventory, drawdown, posture time, rejection/retry counts, terminal valuation, and attribution remain mandatory report fields.

The five sensitivities occur only after the candidate is frozen and cannot choose among candidates, so they do not enlarge the DSR selection trial family. Failure rejects that candidate for promotion; it cannot promote a runner-up on the exposed holdout. Any redesign informed by failure creates a new declared search family and newly eligible holdout.

The panel runs only for the proposed finalist on evidence capable of representing the changed assumption. Full minute paths may represent fee and declared price-cost changes; queue, latency, and delayed maker-eligibility conclusions require the declared detailed event evidence and full holdout event replay. Missing book or timing evidence never becomes a favorable normal value and cannot be fabricated to complete a sensitivity.

The normal baseline remains independently authoritative and must pass every existing return, activity, regime, parity, DSR, risk, accounting, and reconciliation gate. All five sensitivities must preserve accounting, inventory, capital, order, risk, terminal-disposal, and deterministic replay correctness. A sensitivity cannot rescue baseline failure, select a different candidate, widen a parameter, loosen a safety limit, or become the production execution assumption because it happens to earn more.

The combined scenario is a mandatory economic robustness gate: under the subsequently accepted exact values it must remain net-positive on its declared non-duplicated evaluation scope and must not trigger the immutable global terminal stop. Individual scenarios provide mandatory attribution and cannot violate any hard correctness or terminal-safety boundary; their exact economic threshold is fixed with the multiplier decision rather than selected after results.

Example: the candidate earns `12 USDT` in its baseline event holdout. The same events and grid are replayed with higher fees, then with worse acquisition/disposal pricing, then with less executable volume, then with delayed maker submissions, and finally with all four. If the combined run loses money or reaches the global stop, the robustness gate fails. The engine cannot widen the grid or choose a runner-up after seeing that result; a revised strategy becomes a new search family with a new eligible holdout.

Consequences:

- Five bounded reruns expose thin execution margins without creating another combinatorial search.
- Separating individual effects makes failure understandable, while the combined case tests simultaneous moderate error.
- Event-only phenomena are tested only where retained evidence can support them, avoiding invented queue precision in minute data.
- Deterministic delayed arrival produces realistic extra maker rejections from observed prices instead of adding a random rejection percentage.
- The panel directly supplies the promotion decision required by the MVP evidence-sufficiency guardrail.

Declined exact profiles:

- **Mild settings:** fees `+10%`, execution cost `+25%`, `4%` participation, queue `×1.25`, and `+250 ms` latency provide little margin beyond an already conservative baseline.
- **Strict settings:** fees `+50%`, execution cost `×2`, `1%` participation, queue `×3`, and `+1 second` latency can reject a viable small grid under an unusually harsh simultaneous assumption.
- **Set the values from qualifying paper results:** appears empirical but permits future candidate-specific observations to choose the stress boundary after historical selection and delays a gate that can be fixed ex ante.

Declined panel alternatives:

- **Use only the baseline conservative model:** minimizes compute but gives no quantified margin for ordinary estimation error.
- **Evaluate a Cartesian grid of many stress levels:** turns robustness into another large trial family, increases multiple testing, and exceeds the smallest sufficient MVP evidence.
- **Monte Carlo execution perturbations:** adds unvalidated distributions and dependence assumptions for queue, latency, liquidity, and rejection.
- **Retune the candidate after a stress failure:** consumes the stress result as optimization evidence and invalidates the frozen candidate/holdout boundary.

### No mandatory statistical block-resampling gate in the MVP

Selected by the operator on 2026-07-16: the first MVP does not add a statistical-bootstrap or block-bootstrap confidence gate. Chronological evidence, rather than recombined synthetic result paths, remains the mandatory basis for promotion.

The accepted gate set already supplies several distinct checks against a lucky or fragile result:

- eight consecutive rolling out-of-sample quarters plus independent expanding-window sensitivity;
- a frozen five-symbol panel and deterministic nine-regime matrix with coverage/breadth requirements;
- bounded local parameter-plateau stability;
- a `DSR >= 0.95` multiple-testing credibility gate on non-duplicated rolling OOS daily returns;
- one separately sealed 12-month holdout at minute and event fidelity;
- completed-cycle activity and positive realized-cycle evidence;
- the five-scenario adverse execution panel;
- 30-to-90-day future production-data paper qualification, independent Testnet qualification, and capped first-live probation.

Existing iid trade-PnL bootstrap and shuffled-return functions may remain available only as clearly labelled exploratory diagnostics. They cannot satisfy, compensate for, rank, or alter a promotion gate because they break serial dependence, volatility clustering, regime persistence, inventory path, order pairing, and terminal-state relationships. Their outputs must say that they are not promotion evidence.

The MVP also does not implement a moving-block, circular-block, stationary-bootstrap, Reality Check, SPA, or bootstrap confidence-bound framework merely to produce another statistic. For a path-dependent grid, even block resampling of already-produced daily returns does not reconstruct the underlying market/order/inventory state, while resampling raw market blocks introduces boundary and reactivation semantics that require their own validation. Choosing block length, overlap, statistic, repetitions, seed, confidence level, and pass threshold after seeing results would add another research degree of freedom.

The architecture preserves an explicit statistical-resampling extension seam: immutable non-duplicated result series, regime/fold identities, deterministic seeded experiment manifests, plugin-independent report artifacts, and the trial-history/evidence-impact machinery. A later increment may propose a predeclared moving/stationary-block method when measured evidence shows that the accepted chronological, DSR, holdout, and stress gates leave a specific promotion decision unresolved. That proposal must state the exact estimator, source series, block-length rule, boundary semantics, repetitions, seed, confidence statistic, threshold, trial-family treatment, compute budget, acceptance tests, and whether prior holdout exposure requires new evidence.

Example: the frozen candidate passes six of eight rolling quarters, both aggregate return gates, the DSR threshold, regime/panel gates, and its sealed holdout. Running 10,000 iid resamples of individual trade profits would create an impressive-looking interval but would separate trades from the inventory and regimes that caused them. It is reported, if run, as exploratory only and cannot improve the promotion result. If later research shows the DSR calculation is unstable under clustered daily losses, a separately approved block-resampling increment can be designed prospectively rather than retrofitted to this candidate.

Consequences:

- The validation MVP remains comprehensive but does not add a second statistical framework without a distinct decision need.
- Promotion evidence preserves real chronological paths and stateful grid behavior rather than claiming false certainty from synthetic recombinations.
- Existing diagnostic code can still aid exploration when its limitations and non-authority are explicit.
- A future dependence-aware method remains addable through declared evidence interfaces without changing canonical trading semantics.

Declined alternatives:

- **Add a diagnostic block bootstrap now:** can illustrate uncertainty but adds block-length, boundary, seed, repetition, and interpretation choices without changing a declared MVP decision.
- **Require a positive 95% block-bootstrap lower confidence bound:** appears strong but makes promotion highly sensitive to a disputed resampling design for a path-dependent strategy and duplicates existing credibility layers.
- **Use the existing iid trade bootstrap as a gate:** is easy but destroys the dependence and inventory relationships the gate is supposed to protect.
- **Remove all resampling code:** reduces confusion but discards potentially useful exploratory tooling; explicit non-promotion labelling is sufficient.

#### Applicability to adaptive or dynamic grids

The partition method is intentionally strategy-agnostic and can validate adaptive or dynamic grids in later increments. This does not add them to the first MVP, whose promoted strategy family remains one static arithmetic/geometric grid.

An adaptive or dynamic grid changes decision semantics and introduces additional parameters, path dependence, recalculation events, and overfitting opportunities. It therefore requires:

- a separate declared search family and immutable strategy semantics;
- all adaptive decisions and timers reproduced by the canonical event core;
- its own complete trial accounting, rolling/expanding evidence, locked-holdout decision, replay evidence, paper qualification, thresholds, and approval;
- a newly eligible holdout after its family is frozen when prior holdout exposure could have informed its design;
- no inheritance of a static grid's passing result, even when it reuses the same raw market archive or risk ceilings.

Example: a static geometric grid passes its historical gates. Adding ATR-based range movement creates a different search family. The five-year window structure still applies, but the ATR periods, multipliers, movement rules, and every tried variant count as new research; the static result cannot authorize the adaptive configuration.

#### Consequences

- Eight quarterly folds show whether results persist across several contiguous market intervals rather than one annual average.
- A 24-month rolling window balances recent relevance with exposure to more than one seasonal cycle, while expanding sensitivity retains earlier regimes.
- A 12-month holdout gives the frozen research process a substantial final test before future paper operation.
- Newer assets remain researchable but cannot become the first real-money symbol on short favorable histories.
- The profile increases historical compute and storage, but tiered fidelity keeps broad search practical and does not enlarge the continuous Azure runtime requirement.

#### Declined alternatives

- **Four years with 18-month rolling training, six quarterly folds, and a 12-month holdout:** reduces compute but observes fewer independent chronological conditions.
- **Three years with 12-month training, six quarterly folds, and a 6-month holdout:** faster, but weak for a grid whose edge and inventory risk depend strongly on regime.
- **No minimum history:** flexible for new symbols but permits first-live qualification from a single favorable market regime.

### MVP evidence-sufficiency guardrail

Selected by the operator on 2026-07-15 as a standing scope constraint: the backtest is comprehensive enough to support truthful promotion, but it is not a generalized quantitative-research platform in the first MVP.

A proposed backtest capability enters MVP scope only when it has all of:

1. a direct trace to an accepted promotion gate, accounting/risk invariant, parity requirement, or named failure scenario;
2. a declared decision that consumes its output;
3. a deterministic acceptance test and retained evidence identity; and
4. no smaller implementation that supplies the same required evidence with acceptable fidelity.

Capabilities without that trace are deferred even when architecturally interesting. In particular, the MVP does not add a generic strategy-plugin marketplace, portfolio optimizer, machine-learning/Bayesian optimizer, GPU framework, distributed always-on research cluster, reconstructed historical queue positions, continuous full-depth archive, unlimited custom metrics, or implementation of adaptive/IBKR/multi-symbol behavior. The architecture preserves their relevant seams only where already justified by the accepted quality requirements.

The initial implementation sequence must prefer a vertical evidence path: one deterministic grid core, one-minute baseline, bounded search, selected event replay, accounting/risk verification, one reproducible report, and explicit gate outcome. Enhancements are admitted afterward only when a failed verification, measured performance bottleneck, or unresolved promotion decision proves the need. Complexity, runtime, storage, and operator comprehension are reviewed together; “more comprehensive” never means more components by default.
