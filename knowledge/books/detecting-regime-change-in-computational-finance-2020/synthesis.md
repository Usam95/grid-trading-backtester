# Synthesis: Detecting Regime Change in Computational Finance

## 1. Bibliographic Orientation

**Title:** Detecting Regime Change in Computational Finance  
**Authors:** Jun Cheng, Edward P K Tsang  
**Publication Year:** 2020  
**Pages:** 165  
**Format:** PDF  
**Subject Area:** Quantitative finance, machine learning, high-frequency market analysis, algorithmic trading  

This is an academic monograph presenting research on detecting financial market regime changes using Directional Change (DC), a data-driven event-sampling approach, combined with Hidden Markov Models (HMMs) and Naive Bayes classifiers. The work spans from theoretical framework development through empirical validation to proof-of-concept trading algorithm design. Primary contribution: demonstrating that regime detection via DC indicators complements and extends conventional time-series volatility approaches, enabling tick-by-tick market monitoring and real-time regime tracking.

**Relevance to Algorithmic Trading Platforms:**
- Grid-based trading: regime detection informs position entry/exit timing
- Stock signal generation: regime classification enables adaptive strategy switching
- Live execution: real-time tick-by-tick monitoring feasible
- Risk management: abnormal-regime identification for early warning
- Research methodology: demonstrates empirical backtesting workflow and regime-based strategy design

---

## 2. Executive Synthesis (≤400 words)

The book presents a complete workflow for regime-change detection in financial markets, starting from data sampling strategy and ending with algorithmic trading applications. Core contributions:

**1. Directional Change as Sampling Framework**  
Instead of fixed-interval time series, the authors propose event-driven sampling where prices are recorded when movement exceeds a threshold theta (e.g., 0.4%). This "intrinsic-time" approach captures regime dynamics at tick-by-tick resolution, allowing early detection of market state shifts before they manifest in daily volatility.

**2. DC Indicator R for Regime Signals**  
The authors develop indicator R combining total price movement and trend duration, proving orthogonal to conventional volatility. Log-transformed R serves as input to HMM for unsupervised regime discovery.

**3. HMM-Based Regime Inference**  
A two-state HMM with Gaussian emissions discovers hidden market regimes from indicator R or realized volatility. The methodology is applied to Brexit 2016 FX data, detecting regime transitions that align with market events; notably, some transitions detected via DC were missed by time-series methods.

**4. Normal vs. Abnormal Regime Classification**  
Regimes are characterized on multi-market data: Regime 1 exhibits lower R and volatility (normal); Regime 2 exhibits higher values (abnormal/crisis). Indicator-space clustering reveals consistent phenotypes, suggesting classification generalizability.

**5. Real-Time Regime Tracking**  
Naive Bayes classifier on DC trends enables probability-based regime assignment, tunable via threshold variants (B-Simple, B-Strict). Tested on equity indices (DJIA, FTSE 100, S&P 500) with successful regime transition tracking.

**6. Regime-Aware Trading Algorithms**  
Proof-of-concept algorithms (JC1, JC2) enter long positions in Normal regime and exit (or short) on transition to Abnormal regime. Backtests show reduced maximum drawdown compared to control strategy.

**Key Findings:**
- DC and time-series approaches are complementary; both together provide richer market intelligence than either alone.
- Regime-transition signals are predictive of volatility spikes (lag 15-60 minutes suggested but not rigorously quantified).
- Threshold theta is critical but selection not systematized; arbitrarily chosen theta=0.4% works across tested currencies but generalization unclear.
- Money management and transaction costs are key but inadequately addressed in proof-of-concept trading algorithms.

**Limitations:**
- All backtests and empirical work conducted on 2016-2018 data; market structure and algorithms have evolved significantly since.
- No live trading validation or post-sample performance testing.
- HMM model fitting may overfit; retraining procedures and drift detection not discussed.
- Strategies do not account for realistic transaction costs, slippage, or market impact.

---

## 3. Why This Book Is or Is Not Useful

**Highly Useful For:**
- **Researchers designing regime-detection methods:** Complete methodology combining data sampling, feature engineering, and unsupervised learning; provides a replicable template.
- **Platform architects building backtesting systems:** Demonstrates realistic workflow (data preprocessing → indicator calculation → HMM fitting → trading strategy evaluation) with quantifiable metrics.
- **Early-warning system designers for risk management:** Regime classification (normal vs. abnormal) offers framework for market stress detection; tick-by-tick capability enables rapid alerting.
- **High-frequency trading quants:** DC event-driven sampling enables microsecond-level regime tracking, potentially capturing edges before lower-frequency methods.

**Limited Utility For:**
- **Production traders deploying immediately:** Proof-of-concept status; strategies lack realistic cost models and have never been validated live.
- **Machine learning practitioners:** HMM and Naive Bayes are standard tools; limited novel ML methodology (no deep learning, no advanced optimization).
- **Crypto traders:** Empirical studies use only FX and equities; applicability to crypto (24/7 trading, fragmented venues, high volatility) untested.
- **Short-term signal traders (<1 hour horizon):** Regime transitions are slower-moving; may not provide sufficient tradeable signals at ultra-high frequencies.

**Moderate Utility For:**
- **Portfolio managers:** Regime detection can inform asset allocation rebalancing (reduce risk in abnormal regimes), but strategies presented are tactical, not strategic.
- **Risk managers:** Framework for monitoring normal vs. abnormal regimes useful, but causality between regimes and drawdowns not definitively established.

---

## 4. Grid-Backtest Relevance

**Strong Relevance:**

DC-based regime detection is conceptually suited to grid-trading strategies:
- **Entry/exit logic:** Grid algorithms can use regime transitions as boundary conditions (expand grid entry range in normal regime, tighten in abnormal regime).
- **Position sizing:** Normal regime → larger base positions; Abnormal regime → reduced grid size or wider spacing to manage risk.
- **Rebalancing frequency:** DC events provide natural sampling points for grid rebalancing (no fixed time intervals required).
- **Profitability during ranges:** Grid strategies thrive in ranging markets (Normal regime) and underperform in trending, volatile markets (Abnormal regime); regime signal can pause grid during unfavorable regimes.

**Specific Application (REGIME-H1, REGIME-H4):**
- If regime transitions are detectable 15-60 minutes before volatility spikes, grid traders gain a window to reduce exposure or tighten stops.
- Empirical data (Ch 3-4) shows multi-market regime consistency, suggesting a single grid-regime tuning may be transferable across instruments.

**Cautions:**
- Book's proof-of-concept algorithms are simple entry/exit rules; real grid implementations are more complex (multiple price levels, dynamic sizing, hedging).
- Transaction costs of frequent regime-driven rebalancing not analyzed; grid trading already has tight margins.
- Regime definitions are 2016-2018 era; may not apply to modern market conditions (algorithmic proliferation, structural shifts).

---

## 5. Grid Live-Trading Relevance

**Moderate-to-High Relevance:**

Real-time tick-by-tick regime tracking enables live implementation:
- **Latency:** DC calculation on tick data is low-latency; Naive Bayes inference is lightweight (milliseconds).
- **Continuous monitoring:** Unlike daily regime checks, grid systems can adapt in real-time to regime transitions.
- **Risk management:** Automated regime-based position reduction (e.g., close half-grid on abnormal-regime signal) adds real-time risk control without human intervention.

**Challenges:**
- **Reliability:** Data feeds, network latency, and model freshness must be continuously monitored. Stale models or data gaps cause misaligned regime signals.
- **False positives:** Regime signals triggered by noise rather than genuine transitions lead to whipsaws and cost drain.
- **Operational complexity:** Integrating regime monitoring into live trading infrastructure requires robust alerting, logging, and circuit breakers.

**Book's Gaps:**
- No discussion of operational resilience, monitoring, or failure modes for live systems.
- No analysis of cost of incremental regime-driven trades vs. benefit of risk reduction.
- No discussion of latency SLAs or acceptable downtime.

---

## 6. Stock-Backtest Relevance

**High Relevance:**

Book empirically validates regime detection on equity indices (DJIA, FTSE 100, S&P 500) and demonstrates trading applications:
- **Backtesting methodology:** Complete end-to-end workflow (data → preprocessing → indicator → HMM → trading algorithm → performance metrics) is directly applicable to stock strategy development.
- **Regime classification:** Normal vs. Abnormal regimes empirically shown to correlate with returns volatility; provides foundation for regime-conditional strategy design.
- **Trading algorithm templates:** JC1/JC2 algorithms are simple enough to adapt to other stock-based strategies (e.g., momentum, mean reversion).

**Applicability to Stock Strategies:**
- **Mean-reversion strategies:** Tend to work in Normal regimes (ranging markets); regime signals can gate strategy or reduce sizing in Abnormal regimes.
- **Momentum strategies:** May benefit from Abnormal-regime identification to avoid chasing loses during regime-transition whipsaws.
- **Tactical rebalancing:** Portfolio rebalance timing can be informed by regime transitions (e.g., rebalance only when entering Normal regime to avoid locking in losses).

**Limitations:**
- Stock-specific dynamics (earnings, sector rotation, liquidity patterns) not addressed; regime definitions may be generic and miss stock-specific drivers.
- Book tests only equity indices, not individual stocks; stock-level regime detection validity untested.
- Backtests use relatively short windows (2016-2018, Brexit); limited to test cross-regime behavior (bull, bear, crisis cycles).

---

## 7. Stock Live-Trading Relevance

**Moderate Relevance:**

Real-time regime tracking is feasible for stock markets but with caveats:
- **Data availability:** Tick data for liquid stocks is available; calculation overhead is manageable.
- **Trading frequency:** Regime transitions are slower than HFT scales; trading frequency is minutes-to-hours, compatible with stock execution (not flash-order rates).
- **Latency tolerance:** 60-second regime detection latency (REGIME-REQ-001) is acceptable for most stock strategies.

**Operational Challenges:**
- **Multi-asset regimes:** Stock market regime may differ across sectors, cap sizes, or individual stocks; single global regime may be too coarse.
- **Cost structure:** Stock commissions are lower than FX; regime-driven trading overhead may be acceptable.
- **Data quality:** Stock data is generally high-quality; less a concern than in crypto or exotic FX pairs.

**Book's Gaps:**
- No analysis of sector- or single-stock regime detection; only index-level regimes tested.
- No discussion of how regime definitions scale from index to individual stock level.
- Transaction costs and market impact for stock orders not modeled.

---

## 8. Shared-Platform Relevance

**Relevance to Multi-Asset, Multi-Strategy Platforms:**

Regime detection is a shared infrastructure component applicable across grid, stock, portfolio strategies:
- **Unified regime model:** If regimes generalize across assets (REGIME-H2), a single platform-level regime model could serve all strategies, reducing operational burden.
- **Early-warning layer:** Abnormal-regime alerts can be broadcast to all active strategies for coordinated risk management.
- **Backtesting realism:** Including regime-conditional strategy behavior improves backtest fidelity vs. regime-agnostic approaches.
- **Monitoring and alerting:** Real-time regime transitions provide actionable market intelligence for operations teams.

**Platform Design Implications (REGIME-REQ-001, REGIME-REQ-005, REGIME-REQ-006):**
- Regime model must be treated as shared, versioned asset (like data dictionaries or risk models).
- Retraining and validation procedures must be documented and automated.
- Alerting on model staleness or accuracy degradation is critical for operational reliability.
- Multiple strategies may respond differently to same regime signal; platform must support strategy-specific thresholds and rules.

**Challenges:**
- Different strategies may prefer different regime definitions (e.g., stock momentum wants finer-grained regime breakdowns; grid wants coarse normal/abnormal).
- Cross-asset regimes may not be fully synchronized (equity normal, crypto abnormal simultaneously possible).
- Shared model update cycles may conflict with individual strategy update needs.

---

## 9. Testable Hypotheses Derived

Four primary hypotheses extracted and documented in hypotheses.yaml:

1. **REGIME-H1:** DC indicator R detects high-frequency regime transitions faster than daily realized volatility (lead time 15-60 minutes).
   - Testable on FX/equity tick data with labeled regime transitions.
   - Critical for assessing informational edge of DC approach.

2. **REGIME-H2:** Normal/Abnormal regime classification generalizes across independent markets without retraining.
   - Testable via cross-market validation (train on market A, test on market B).
   - Essential for platform-wide regime model feasibility.

3. **REGIME-H3:** Real-time regime tracking via Naive Bayes is predictive of 1-hour-ahead volatility spikes.
   - Testable on intra-day data; measures lag between regime transition and realized volatility.
   - Determines practical trading edge and profitability.

4. **REGIME-H4:** Regime-aware trading strategies reduce maximum drawdown by 15-30% without sacrificing returns.
   - Testable via backtest with realistic transaction costs and out-of-sample validation.
   - Validates core book thesis: regime information improves risk-adjusted returns.

All four hypotheses are medium-to-high confidence but require rigorous testing with realistic market conditions, costs, and post-sample validation.

---

## 10. Research, Data, and Simulation Lessons

**Data Sampling and Preprocessing:**
- Event-driven sampling (DC) is informationally richer than fixed intervals; consider for any regime-detection or volatility-monitoring system.
- High-frequency tick data is essential; lower-frequency data may miss regime transitions (REGIME-C3-002 shows daily volatility misses some DC-detected transitions).
- Data quality issues (gaps, duplicates, outliers) must be handled robustly; naive algorithms fail on real market data (REGIME-REQ-002).

**Feature Engineering:**
- Combining orthogonal measures (price movement + duration in DC indicator R) improves signal vs. single-measure volatility.
- Log-transformation of indicators often improves normality assumption for downstream models (HMM).
- Threshold selection (e.g., DC threshold theta) is critical and should be systematized, not arbitrary (REGIME-REQ-004).

**Model Development:**
- Unsupervised learning (HMM) can discover regime structures without labeled data; efficient for exploratory regime research.
- Number of states/regimes should be domain-driven or validated, not arbitrary; book assumes 2 states without justification for all markets.
- Model validation requires held-out test set; in-sample fit is not sufficient (REGIME-REQ-003).

**Empirical Study Design:**
- Comparison periods matter: testing during Brexit 2016 is good (clear regime shift) but limited (one event, short period).
- Multiple markets/assets should be tested to assess generalization; book tests multiple but lacks crypto, commodities, longer time series.
- Statistical significance testing is missing; regime differences shown graphically but not tested (e.g., t-tests on regime means).

**Reproducibility Concerns:**
- HMM hyperparameters (initialization, convergence threshold, number of EM iterations) not fully specified; may affect reproducibility.
- DC threshold theta chosen arbitrarily; threshold-tuning procedure not documented, hindering reproducibility.
- Code and data not released with book; claims cannot be independently verified (REGIME-C3-002 reported as anecdotal evidence, not independently confirmed).

---

## 11. Execution, Risk, and Operations Lessons

**Execution Realism:**
- Book's proof-of-concept algorithms assume perfect execution (instant fills at mid-price, no market impact). Real trading incurs bid-ask spread, commissions, and partial fills (REGIME-C6-003).
- Transaction cost model required: every regime-driven trade (entry/exit) costs money. High-frequency regime switching may not be profitable after costs.
- Slippage is especially important for regime-transition trades: rapid exits during abnormal-regime onset often face liquidity squeeze.

**Risk Management:**
- Normal/Abnormal regime classification is useful for risk monitoring: abnormal regimes correlate with higher drawdown risk (REGIME-C4-001, REGIME-C4-002).
- Regime-based position sizing (reduce exposure in abnormal regime) is intuitive risk control but requires validation (does it reduce realized drawdowns?).
- Regime switching may interact with other risk controls (VaR limits, stop losses); redundancy or conflicts must be analyzed.

**Operational Resilience:**
- Real-time regime tracking requires continuous data feed and model availability. Data gaps or model staleness silently undermine regime signals (REGIME-REQ-002, REGIME-REQ-006).
- Alerting on regime transitions must be low-noise (avoid false positives causing alert fatigue) yet high-sensitivity (detect true regime shifts quickly).
- Model retraining and revalidation must be automated; manual regime-model updates are operationally fragile (REGIME-REQ-003, REGIME-REQ-006).

**Monitoring and Diagnostics:**
- Regime classification accuracy should be continuously monitored on recent data; accuracy drops >15% indicate model staleness (REGIME-REQ-006).
- Operational dashboard should display: current regime, regime probability (from Naive Bayes), last transition timestamp, model version, validation accuracy.
- Alerts on data quality issues (gaps, outliers, feed disconnections) are essential to detect operational problems before they affect regime signals.

---

## 12. Failure Modes and Anti-Patterns

**Failure Mode 1: Threshold Arbitrariness (REGIME-C3-003)**
- **Manifestation:** DC threshold theta chosen without systematic tuning; threshold works for one market but not another.
- **Consequence:** Regime detection in new markets unreliable or requires manual retuning.
- **Mitigation:** Implement grid-search threshold tuning procedure (REGIME-REQ-004); test generalization across markets.

**Failure Mode 2: Backtest Overfitting (REGIME-C6-003)**
- **Manifestation:** Trading algorithms tuned on 2016-2018 data but fail post-2020 due to changed market structure or regime definitions.
- **Consequence:** Paper-trading results don't match live performance; capital loss.
- **Mitigation:** Walk-forward backtesting, out-of-sample validation, periodic model retraining (REGIME-REQ-003, REGIME-REQ-006).

**Failure Mode 3: Transaction Cost Underestimation (REGIME-C6-003)**
- **Manifestation:** Backtests ignore realistic costs; strategies profitable in backtest but unprofitable live.
- **Consequence:** Strategy disappoints; investor confidence eroded.
- **Mitigation:** Include realistic cost model in backtests; paper-trade to validate cost assumptions (REGIME-REQ-005).

**Failure Mode 4: Non-Stationary Regimes (REGIME-H2, REGIME-H4)**
- **Manifestation:** Regime definitions are time-dependent (different in 2016 vs. 2023); model trained on old data is invalid.
- **Consequence:** Regime signals become unreliable; strategies underperform.
- **Mitigation:** Continuous model monitoring and retraining; alerts on accuracy degradation (REGIME-REQ-006).

**Failure Mode 5: Regime Lag (REGIME-C5-002, REGIME-C6-002)**
- **Manifestation:** Regime is detected too slowly; by time trading algorithm reacts, volatility spike has already occurred.
- **Consequence:** Exit signals too late; entry signals miss the bottom.
- **Mitigation:** Quantify detection latency (REGIME-REQ-001); optimize Naive Bayes thresholds to reduce lag (REGIME-C5-002); consider leading indicators.

**Failure Mode 6: Regime Independence Assumption (REGIME-C5-001)**
- **Manifestation:** Naive Bayes assumes independence of regime features (DC return, trend duration), but they are correlated.
- **Consequence:** Posterior probabilities miscalibrated; regime classification unreliable.
- **Mitigation:** Validate independence assumption or use more flexible classifier (e.g., logistic regression, boosting).

---

## 13. Likely Obsolete, Jurisdiction-Specific, or Venue-Specific Material

**Time-Sensitive Findings:**
- Brexit 2016 is analyzed as a case study; market structure, volatility regimes, and trading behavior have evolved significantly by 2024.
- High-frequency trading landscape has changed; algorithmic dominance and machine learning adoption post-2016 may have eliminated regime-based trading edges.
- Central bank policies (QE, ZIRP, post-pandemic tightening) have fundamentally altered volatility and regime dynamics compared to 2016-2018 baseline.
- Crypto market 2016 was nascent; applicability of equity/FX regime methodology to 2024 crypto (highly fragmented, 24/7 trading, leverage) untested.

**Venue-Specific Assumptions:**
- Data sourced from CCFEA/Kibot; assumes standard tick data format and data quality. Venue-specific quirks (circuit breakers, trading halts, market hours) vary.
- FX market 24/5 structure; equities trade 6.5 hours/day US market time; regime definitions may not transfer between venue types.

**Regulatory/Jurisdictional Shifts:**
- Tick-size regulations vary by jurisdiction and have changed since 2016; affects DC threshold applicability.
- Market impact models and liquidity profiles differ; regulatory changes post-2016 (Mifid II, FRTB, etc.) altered market structure.

**Technological Obsolescence:**
- HMM and Naive Bayes are classical methods; newer deep-learning approaches (LSTMs, Transformers, VAEs) may outperform.
- Computational resources have evolved; real-time regime tracking is now feasible with lightweight models not possible in 2016.

---

## 14. Internal Contradictions

**Contradiction 1: Generalizability of Threshold theta**
- **Claim:** "Power law in DC observations suggests same stylized facts at different thresholds" (Ch 2, Glattfelder et al.).
- **Finding:** theta=0.4% works for EUR-GBP, GBP-USD, EUR-USD, and equities in book's experiments.
- **Contradiction:** No threshold-tuning procedure provided; no sensitivity analysis showing robustness to ±20% theta variation; claimed generalizability not rigorously validated.
- **Resolution Needed:** Formal proof that power law implies threshold robustness, or explicit tuning-procedure algorithm.

**Contradiction 2: Causality of Regime → Volatility**
- **Claim:** "Regime transitions precede volatility spikes; regime signals provide early warning" (implied in Ch 5-6).
- **Finding:** Regime is detected from statistical properties (R indicator, volatility); regimes and volatility are not independent variables.
- **Contradiction:** Potential circular reasoning: if regime is derived from volatility, using regime to predict volatility is tautological.
- **Resolution Needed:** Explicit temporal-precedence analysis; show regime transitions occur before volatility spikes (not simultaneously).

**Contradiction 3: Two-State HMM Universality**
- **Claim:** "Two-state HMM sufficient for regime detection" (Ch 3-4).
- **Finding:** Two states tested for 2-month periods (Brexit); extended to longer time series (Ch 4, 5) with same 2-state assumption.
- **Contradiction:** Multi-year time series likely contain >2 distinct regimes (bull, bear, crisis, transition periods); 2-state assumption may be oversimplified.
- **Resolution Needed:** Formal model selection (e.g., BIC, AIC) to determine optimal number of states per dataset.

---

## 15. External Claims Needing Primary-Source Verification

**Claims About Regime-Switching Models:**
- "Hamilton concluded time series can show dramatic breaks in economic variables" → original Hamilton 1989 paper should be consulted; book cites [31].
- "Regime switching could result from policy changes or Lehman Brothers bankruptcy" (Ang & Timmermann) → verify causality claim in original [8].

**Claims About Directional Change:**
- "Power law exhibited in DC observations" (Glattfelder et al.) → original paper [27] should be reviewed; mechanism of power law explained.
- "DC allows same stylized facts across different thresholds" → quantify "same" (±10%? ±50%?); provide empirical validation.

**Claims About Regime Profitability:**
- Book avoids claims of profitability; emphasizes proof-of-concept. However, REGIME-C6-001 suggests "reduced drawdown" benefit → needs statistical significance testing and live-trading validation.

**Claims About Market Events:**
- "GBP plunged to 30-year low on June 24, 2016 Brexit referendum result" → verify exact date and magnitude against primary FX data sources (e.g., FRED, Bloomberg).
- "Global stock sell-offs triggered by Brexit" → quantify "sell-offs"; cite official market indices.

**Market Microstructure Assumptions:**
- Bid-ask spreads, commissions, market impact models used in trading algorithms [REGIME-C6-002] not cited; should be compared against actual market data or broker reports.

---

## 16. Top 10 Records by Decision Value (by ID)

1. **REGIME-C3-001:** Two-state HMM for regime inference. Core methodology; enables all downstream regime classification and tracking.

2. **REGIME-C3-002:** Brexit empirical validation. Demonstrates that DC method works on real data during known market stress; establishes credibility.

3. **REGIME-C2-002:** DC indicator R definition combining price and time. Key contribution; enables regime detection without assuming stationarity.

4. **REGIME-H1:** DC faster than time-series detection. Highest-priority hypothesis; if validated, establishes informational edge of DC approach.

5. **REGIME-REQ-001:** Real-time latency SLA for regime tracking. Critical for live trading applicability; if latency is too high, edge is lost.

6. **REGIME-C4-001:** Normal vs. Abnormal regime classification. Enables risk management application (abnormal-regime alerts).

7. **REGIME-H4:** Regime-aware strategies reduce drawdown. Core business hypothesis; if validated, justifies investment in regime-detection infrastructure.

8. **REGIME-C6-003:** Proof-of-concept trading algorithms lack realistic costs. Critical warning; prevents false confidence in backtest results.

9. **REGIME-REQ-004:** DC threshold tuning procedure. Operationally necessary; without it, generalization to new markets is unreliable.

10. **REGIME-REQ-006:** Model retraining and drift detection. Essential for operational longevity; without it, deployed model becomes stale.

---

## 17. What the Book Does NOT Establish

**Does NOT Establish:**
1. **Profitability of regime-based trading:** Book presents proof-of-concept algorithms with reduced drawdown but does NOT claim strategies are profitable, consistently outperforming baselines, or suitable for live trading.

2. **Causality between regimes and volatility:** Shows regimes and volatility are correlated but does NOT prove regimes cause volatility (potential endogeneity or simultaneity bias).

3. **Universality of regime definitions:** Tested on FX and equities during 2016-2018; does NOT claim regime definitions generalize to crypto, commodities, or post-2020 market conditions without revalidation.

4. **Optimality of HMM model:** Two-state HMM chosen for convenience; does NOT prove it is optimal or that other models (e.g., Markov-switching GARCH, Hidden Semi-Markov Model) would not perform better.

5. **Realistic transaction cost impact:** Algorithms backtested without slippage, partial fills, or market impact; does NOT account for realistic execution frictions.

6. **Statistical significance of regime detection:** Regime transitions shown graphically but NOT tested for statistical significance vs. random walk or stochastic-noise null.

7. **Generalization across time periods:** Empirical studies span 2016-2018 largely; does NOT establish robustness to 10-year time series, multiple market cycles, or unprecedented regimes.

8. **Superiority over existing methods:** DC approach shown to be "as good as" and sometimes "better than" time-series volatility but NOT compared to modern machine-learning alternatives (neural networks, ensemble methods, Bayesian methods).

9. **Implementation feasibility:** Algorithms described in theory; does NOT provide production-grade code, open-source libraries, or operational infrastructure for live deployment.

10. **Regulatory compliance:** Does NOT address market-making rules, position limits, circuit breakers, or other regulatory constraints on regime-based trading.

---

**End of Synthesis**

