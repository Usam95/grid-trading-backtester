# Operator Studio Glossary

## Operator identity

The one accepted non-root SSH account and public-key fingerprint permitted to open the personal MVP's operator path; every command is attributed to this identity but still requires command-level validation and admission.
_Avoid_: Azure subscriber, Binance account, browser user

## Operator workstation

The secured, single-operator control surface for research, validation, approvals, paper/live status, start/pause/stop actions, reconciliation, alerts, and audit history.

## Live-qualified operator workstation

An operator-owned, full-disk-encrypted workstation whose dedicated access key, network path, local evidence handling, and recovery posture have passed the live security boundary.
_Avoid_: Work laptop, development machine, SSH client

## Operator-access recovery

The audited replacement of a lost or unsafe operator key and restoration of the accepted Studio/SSH path without granting trading resume or changing venue credentials.
_Avoid_: Key backup, runtime recovery, credential rotation

## Research workspace

The workstation area for local historical research, evidence analysis, candidate selection, and preparation of an immutable handoff, with no online trading authority.
_Avoid_: Backtest mode, paper workspace

## Operations workspace

The workstation area for authenticated inspection and control of Azure paper, Testnet, and live runtimes through the control gateway, with no authority to edit admitted candidate evidence.
_Avoid_: Live mode, trading dashboard

## System operation

Normal inspection and allowlisted control of the Gridlab runtimes through Studio and the Gateway, without arbitrary operating-system authority.
_Avoid_: VM management, remote administration

## VM administration

Exceptional operating-system diagnosis or repair performed through the SSH terminal outside Studio's trading-system controls.
_Avoid_: System operation, Studio command

## Command Center

The current-runtime operational view that relates safety/capital state, market and trade evidence, rung/order obligations, allocation/accounting, and causal activity for one explicit environment.
_Avoid_: Trading terminal, portfolio dashboard, authority header

## Research experiment

A provenance-identified historical evaluation activity—one backtest or one bounded multi-trial search—with immutable inputs, lifecycle evidence, and resulting records.
_Avoid_: Backtest portfolio, live run

## Research job

The durable queued execution of a research experiment's declared work plan, including its progress, checkpoints, worker history, and terminal outcome.
_Avoid_: Browser request, live runtime, experiment result

## Trade overlay

An evidence-linked visualization that maps canonical managed orders, fills, fees, rungs, and paired cycles onto their market and accounting context for analysis.
_Avoid_: Reconstructed trade markers, authoritative trade record

## Grid adaptation view

The evidence-linked Studio presentation of the current grid adaptation state, active grid plan epoch, transition progress, satisfied and failed gates, and resulting safety posture without making or overriding the underlying decision.
_Avoid_: Trading signal, strategy control, market-regime cell

## Local evidence cache

The rebuildable laptop copy of checksum-verified sealed online evidence used for local analysis without becoming an authoritative runtime history.
_Avoid_: Local runtime database, backup authority

## Exploratory experiment

A research experiment permitted to use declared non-qualifying evidence or assumptions and therefore permanently excluded from candidate promotion under that identity.
_Avoid_: Failed promotion experiment, candidate

## Authority context header

The persistent workstation summary that identifies the selected workspace, environment, target, evidence freshness, and current permission-relevant condition without itself granting authority.
_Avoid_: Health light, command bar, mode selector

## View freshness state

The Studio classification of whether its selected online projection is current, stale, disconnected, or recovering, independent from runtime readiness and trading permission.
_Avoid_: Runtime health, safety posture, websocket status

## Contextual explanation

An evidence-linked learning view that defines a canonical concept, explains its current consequence with an example, and points to deeper material without changing authority.
_Avoid_: Tooltip-only help, generated advice, gate override

## Promotion gate

A mandatory evidence check controlling movement from historical validation to paper trading and from paper trading to limited-capital live trading. Passing gates never activates live trading automatically.

## Strategy search family

The complete declared set of related strategy semantics, parameter ranges, objectives, datasets, variants, and inspected trials treated as one multiple-testing and promotion unit.
_Avoid_: Winning configuration, grid-search run

## Development data

Historical market evidence available for designing, tuning, comparing, and walk-forward testing a strategy search family.
_Avoid_: Training data

## Walk-forward fold

A chronological development partition in which parameters are selected from a past training window and evaluated on its immediately following unseen test window.
_Avoid_: Random cross-validation fold

## Rolling training window

A fixed-duration walk-forward training interval whose oldest observations leave as the fold advances.
_Avoid_: Expanding training window

## Expanding-window sensitivity

A mandatory development analysis whose training interval retains all earlier observations to expose dependence on a rolling-history cutoff.
_Avoid_: Primary promotion score

## Locked promotion holdout

A final chronological historical interval unavailable to strategy selection and evaluated once only after the complete candidate and promotion rules are frozen.
_Avoid_: Forward fold, test data

## Consumed holdout

A promotion holdout whose results have been exposed and therefore cannot provide unseen evidence for a redesigned search family or retuned candidate.
_Avoid_: Failed dataset

## Quality-approved dataset

A manifested market dataset that passes every frozen, applicable source-integrity, continuity, consistency, provenance, and derivation rule required for its evidence role.
_Avoid_: Clean data, mostly complete dataset

## Sealed holdout evaluation bundle

The indivisible minute-level and event-level result package produced for one frozen candidate from one locked promotion holdout and exposed only after every declared analysis completes.
_Avoid_: Final backtest, best holdout result

## Strategy selection procedure

The frozen data, parameter-generation, evaluation, cost, objective, risk, and candidate-selection rules applied independently when searching a strategy family on an eligible symbol.
_Avoid_: Best parameters, optimizer

## Cross-symbol robustness panel

A predeclared set of eligible markets used to test whether one strategy selection procedure generalizes beyond the proposed live symbol.
_Avoid_: Portfolio, multi-symbol live grid

## Symbol-specific candidate

One immutable configuration and evidence identity produced for one market by the strategy selection procedure.
_Avoid_: Universal grid configuration

## Candidate selection record

The durable operator decision linking one exact candidate to the ranking policy, gate evidence, alternatives, and rationale reviewed when it was chosen for package preparation.
_Avoid_: Promotion, paper activation, candidate package

## Package admission

The Azure verification decision that one exact sealed paper candidate package is complete, compatible, current, and preserved for qualification, without starting a runtime or granting trading authority.
_Avoid_: Upload, paper start, promotion

## Qualification workspace

The workstation area that relates production-data paper and Testnet qualification for one package/build while preserving their distinct purposes, evidence, clocks, balances, controls, and results.
_Avoid_: Paper trading mode, combined qualification account

## Panel pass

The cross-symbol state in which the same required members of a frozen robustness panel satisfy both primary and sensitivity rules without any correctness or terminal-risk failure.
_Avoid_: Profitable portfolio, average symbol result

## Market-regime cell

One mutually exclusive analytical combination of a trailing trend label and a training-relative volatility label assigned without future information.
_Avoid_: Strategy mode, market prediction

## Stress-event overlay

A non-exclusive analytical tag identifying an observed extreme market, liquidity, range, data-continuity, or terminal-execution condition.
_Avoid_: Market regime, trading signal

## Regime coverage

The non-duplicated classified calendar evidence establishing how broadly a candidate and robustness panel encountered the declared market-regime cells.
_Avoid_: Number of trades, duplicated simulation days

## Regime breadth pass

The state in which regime coverage, intended-environment profit, positive-cell breadth, result concentration, and adverse-regime safety each satisfy their independent gate.
_Avoid_: Overall profitable backtest

## Staged hybrid search

A frozen parameter-search procedure combining broad low-discrepancy coverage, local refinement of stable regions, and bounded higher-fidelity finalist evaluation.
_Avoid_: Grid search, manual tuning

## Sobol design

A seeded deterministic low-discrepancy sequence used to distribute broad-search trials evenly across normalized parameter ranges.
_Avoid_: Random search

## Performance plateau

A connected parameter neighborhood whose nearby configurations satisfy declared stability and viability rules rather than one isolated best-performing point.
_Avoid_: Best trial, optimum

## Plateau seed

A distinct high-ranking broad-search candidate whose fixed local neighborhood is evaluated to determine whether it forms a performance plateau.
_Avoid_: Winning candidate, cluster center

## Fixed evidence assumption

A versioned cost, fill, data, or evaluation rule held constant during candidate search and varied only through declared non-selecting sensitivity evidence.
_Avoid_: Search parameter, optimizer setting

## Search budget

The immutable maximum generated-point and evaluated-trial allowances assigned to each declared search stage and evidence stratum before results are inspected.
_Avoid_: Compute limit, trials completed

## Parameter domain

The immutable legal range, scale, mapping, and resolution through which a declared strategy-search parameter may be generated before performance is inspected.
_Avoid_: Suggested range, optimizer freedom

## Evidence-sufficiency guardrail

The rule that admits an MVP research capability only when a declared promotion decision, invariant, parity requirement, or named failure scenario consumes its deterministic evidence.
_Avoid_: Feature completeness, research-platform scope

## Lexicographic candidate ranking

A deterministic selection order in which hard gates reject first and the earliest materially distinguishing approved criterion decides between surviving candidates without weighted compensation.
_Avoid_: Trust score, composite ranking

## Practical-equivalence band

The fixed absolute difference within which candidate returns are treated as economically equal for the first ranking comparison so that risk and stability may decide.
_Avoid_: Accounting tolerance, confidence interval

## Deflated Sharpe credibility gate

A secondary multiple-testing check of whether a selected return path remains credible after accounting for its statistical shape and the declared strategy-selection exposure.
_Avoid_: Return objective, safety-risk limit, probability of future profit

## Historical net-return gate

The non-compensating minimum after-cost return evidence required across declared development and holdout paths before historical promotion.
_Avoid_: Gross cycle profit, target return

## Buy-and-hold benchmark

The diagnostic return from converting the common quote allocation to base at activation, holding without trading, and disposing at the terminal boundary under comparable costs.
_Avoid_: Grid return requirement, cash benchmark

## Fidelity-parity band

The maximum permitted economic disagreement between minute and event evaluation of the same frozen candidate and historical interval.
_Avoid_: Exact fill parity, accounting tolerance

## Completed-cycle activity gate

The minimum recurring evidence that cumulative paired-order obligations completed with positive aggregate realized cycle result across the required periods.
_Avoid_: Fill count, order count, total return

## Qualifying paper clock

The consecutive 30-day UTC evidence interval tied to one immutable candidate and decision-critical build, preserved only through fully evidenced safe interruptions and recovery.
_Avoid_: Uptime counter, cumulative good days
