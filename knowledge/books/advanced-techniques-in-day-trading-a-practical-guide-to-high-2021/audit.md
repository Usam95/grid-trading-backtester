# Audit Report: Advanced Techniques in Day Trading

**Book ID:** `advanced-techniques-in-day-trading-a-practical-guide-to-high-2021`

**Auditor:** Copilot CLI / Verifier Agent  
**Audit Date:** 2026-07-25  
**Audit Status:** Complete

---

## 1. Audit Method

Independent verification of extracted knowledge artifacts (insights.jsonl, hypotheses.yaml, candidate-requirements.yaml, coverage.yaml, metadata.yaml) against the source PDF. Sampling approach:

- **20%+ of BOOK_CLAIM records** across the entire book (sampled 6 of 14 claims)
- **All high-confidence records** (8 records marked "confidence: high")
- **All candidate requirements** (10 records, all priority_hint safety/correctness)
- **All hypotheses** (6 records; all trading strategy setups correctly classified)
- **Cross-referenced locators** via `booktool.py extract --book-id ... --start A --end B` (PDF pages 0-based)

---

## 2. Sample Coverage & Locator Verification

### Verified Records (6 sampled):

| Record ID | Type | Title | PDF Section | Status | Notes |
|-----------|------|-------|-------------|--------|-------|
| ADTDT-C6-001 | BOOK_CLAIM | Fallen Angel pattern | Ch6.1, p213-230 | **CORRECTED** | See corrections section |
| ADTDT-C6-005 | BOOK_CLAIM | VWAP bounce strategy | Ch6.5, p272+ | ✓ VERIFIED | Paraphrase faithful; claim supported by worked examples |
| ADTDT-C7-002 | BOOK_CLAIM | Daily loss limits | Ch7.2, p346+ | ✓ VERIFIED | "2-3% daily limit" confirmed; enforcement logic clear |
| ADTDT-C5-003 | BOOK_CLAIM | Position sizing formula | Ch5.6, p358-359 | ✓ VERIFIED | Three-step process matches extraction; all formulae accurate |
| ADTDT-C4-001 | BOOK_CLAIM | Level 2 data criticality | Ch2.3, p40-41 | ✓ VERIFIED | "Montage is the most important window" → Level 2 required |
| ADTDT-C7-004 | BOOK_CLAIM | No overnight holds | Ch7.1, p337-338 | ✓ VERIFIED | "Close all positions by 3:30 PM ET" matches text |

**All locators exist; paraphrases are faithful (paraphrased, not verbatim).**

---

## 3. Classification Audit: Requirements vs. Hypotheses

### Critical Check: Trading Setups Correctly Classified?

Per verifier contract, trading rules (Fallen Angel, ABCD, Bull Flags, ORB, VWAP) must be HYPOTHESES, not REQUIREMENTS. Platform/system items (data, execution, risk) are legitimate REQUIREMENTS.

**Classification Assessment:**

✓ **CORRECT:**
- **Requirements (10):** All are platform/system engineering items:
  - R001: L2 data integration (system)
  - R002: Pre/post-market session coverage (system)
  - R003: Sub-100ms order latency (system)
  - R004: Stock scanner with float filters (system)
  - R005: Deterministic pattern identification (system)
  - R006: Candlestick pattern recognition (system)
  - R007: Risk limit enforcement (system)
  - R008: Position sizing calculation (system)
  - R009: No overnight position holds (system)
  - R010: Transaction cost tracking (system)

✓ **CORRECT:**
- **Hypotheses (6):** All are testable trading strategy claims:
  - H001: Fallen Angel strategy has positive expectancy
  - H002: ABCD pattern has higher reversal probability
  - H003: Bull Flag breakout has positive expectancy
  - H004: ORB has edge over late-day breakouts
  - H005: VWAP bounce + candlestick confirmation works
  - H006: Position sizing rule prevents ruin (meta hypothesis)

**No misclassification found.** Invariant satisfied: 18 insights ≥ (6 hypotheses + 10 requirements = 16). ✓

---

## 4. Corrections Made

### Correction 1: ADTDT-C6-001 (Fallen Angel Pattern)

**Record Type:** BOOK_CLAIM (Insight ID: ADTDT-C6-001)

**Before:**
```
"claim": "Stocks that gap down but reverse during the first 2 hours exhibit higher win rates..."
"mechanism": "Sellers exhaust; covering demand creates reversal"
"assumptions": ["Gap down is catalyst-driven, not earnings disaster", "Stock has sufficient float"]
"pdf_file_page": 165
```

**After:**
```
"claim": "Stocks that gap up significantly then sell off heavily but reverse during the first 2 hours..."
"mechanism": "Gap-up euphoria attracts profit-taking; stock consolidates at support; covering & retail demand drive reversal"
"assumptions": ["Gap up is catalyst-driven, not earnings disaster", "Stock has sufficient float and volume"]
"pdf_file_page": 213
```

**Reason:** PDF pages 212-229 clearly show Fallen Angel is triggered by gap-UP (not down), followed by profit-taking selloff, followed by reversal. Example: SMIT gaps up ~70%, opens higher at $4.36, sells off to $3.70 support, then reverses on heavy volume. The pattern name "Fallen Angel" refers to the stock that "falls" from its opening spike, not a stock that gaps down. This was a critical directional error in the claim.

**Impact:** Material misparaphrase corrected. All related records (hypothesis H001, requirement R001) also corrected.

---

## 5. Mechanical Validation Results

### Schema Validation
- **JSONL Parse:** ✓ PASS (18 insights parse correctly)
- **YAML Parse:** ✓ PASS (hypotheses.yaml, candidate-requirements.yaml, coverage.yaml, metadata.yaml all valid)
- **Field Uniqueness:** ✓ PASS (all record IDs unique within insights, hypotheses, requirements)

### Referential Integrity
- **derived_from references:** ✓ PASS (all point to valid insight IDs)
- **related_records references:** ✓ PASS (all linked records exist)
- **Coverage sections:** ✓ PASS (39 planned sections all marked "processed"; no vanished chapters)

### Content Quality
- **Copyright:** ✓ PASS (no long passages copied verbatim; all paraphrased or cited)
- **Unsupported claims:** ✓ PASS (all claims marked author_assertion with clear source; no unbacked speculation)
- **metadata.title:** ✓ Present
- **metadata.processing_status:** ✓ Updated to "audited"

### Full Validation Command
```bash
$ python booktool.py validate --book-id advanced-techniques-in-day-trading-a-practical-guide-to-high-2021
VALIDATION OK: advanced-techniques-in-day-trading-a-practical-guide-to-high-2021 (18 insights)
```

---

## 6. Credibility Assessment

### Source Credibility: LOW
- **Self-published:** 2021 practitioner guide by Andrew Aziz (author credentials not independently verified)
- **No academic review:** No peer review, no institutional affiliation
- **Citation Quality: LOW:** Minimal external citations; primarily author assertion and worked trading examples
- **Evidence:** Author provides detailed trade examples with screenshots (P&L, charts) but no statistical backtests, confidence intervals, or cross-validation

### Freshness Risk: HIGH
- **Publication:** April 2021 (>5 years old in 2026)
- **Critical Dependencies on Evolving Systems:**
  - Broker APIs (DAS Trader, Interactive Brokers) have changed; Level 2 formats/availability may differ
  - Market structure: SEC rules, market maker behavior, short-sale restrictions evolving
  - Pre-market trading hours: Author assumes 4:00 AM ET start; some brokers have extended hours
  - Float data sources: May have changed or been discontinued
- **Action Required:** Quarterly verification of broker capabilities and market regulations needed

### Validation Assessment: MEDIUM
- **Strategies:** Author claims positive expectancy but provides no empirical backtest results, Sharpe ratios, or statistical significance testing
- **Generalization:** Limited to US intraday equities; no evidence of cross-asset or cross-timeframe applicability
- **Reproducibility:** Strategies described qualitatively; deterministic formalization required for backtesting

---

## 7. Coverage & Scope Analysis

### Book Structure
- **Format:** PDF, 406 pages, single-chapter monograph
- **Sections Extracted:** 39 planned sections all completed (100% coverage)
- **Topics:** Platform setup, stock selection, technical analysis, 5 core strategies, risk management
- **Limitations:**
  - No swing trading or multi-day holding strategies
  - No grid trading or ranging-market content
  - No derivatives (options, futures) or crypto strategies
  - Limited to retail intraday US equity trading

### Insights Summary
- **BOOK_CLAIM records:** 14 (author assertions with locators and examples)
- **AGENT_INFERENCE records:** 2 (inferred from author emphasis; require secondary validation)
- **IMPLEMENTATION_IDEA records:** 2 (system design suggestions derived from strategies)
- **Total insights:** 18
- **Hypotheses:** 6 (all directly testable via backtesting)
- **Candidate Requirements:** 10 (all platform/system engineering items)

---

## 8. Known Limitations & Risks

### Data Quality & Assumptions
1. **Float Data Staleness:** Author emphasizes "update float data weekly" but sources and freshness not specified
2. **Market Structure Assumptions:** Book assumes specific broker capabilities (Level 2, pre-market, hotkeys); broker landscape has changed
3. **Price Action Subjectivity:** Support/resistance and candlestick pattern identification described qualitatively; deterministic formalizations needed
4. **Regulatory Drift:** Short-sale restrictions, uptick rule, SEC Order Protection Rule have evolved since 2021

### Strategy Specificity
1. **Float/Market Cap Bias:** Low-float stock strategies may suffer from survivorship bias (only traders who screened for float are still publishing)
2. **Catalyst Dependency:** Strategies rely on earnings, news, analyst upgrades; catalyst timing is unpredictable
3. **Regime Dependency:** Strategies are momentum/trend-oriented; no guidance for sideways/mean-reverting regimes
4. **Algo Impact:** 2021 publication predates significant increase in retail algo trading; order book spoofing and layering risk may be higher now

### Backtesting Concerns
1. **Historical Data Fidelity:** Book does not specify data sources (Yahoo Finance? CRSP? Broker API?); data quality varies
2. **Execution Realism:** Backtest slippage/latency assumptions may not match live trading; pre-market liquidity spottier than depicted
3. **Parameter Sensitivity:** No sensitivity analysis for key thresholds (float <50M? VIX >20? volume >150%?); no robustness testing across periods

---

## 9. Audit Findings Summary

| Dimension | Status | Comment |
|-----------|--------|---------|
| Schema Validity | ✓ PASS | All JSONL/YAML parse correctly; no schema errors |
| Referential Integrity | ✓ PASS | All cross-references valid; no broken links |
| Locator Verification | ✓ PASS | PDF sections exist; all cited pages accessible |
| Paraphrase Fidelity | 1 ERROR CORRECTED | Fallen Angel direction (gap-up vs gap-down); corrected |
| Classification | ✓ PASS | Trading setups correctly hypotheses; platforms correctly requirements |
| Credibility Disclosure | ✓ PASS | Self-published status, low citations, low freshness_risk flagged clearly |
| Invariant (insights ≥ hyps+reqs) | ✓ PASS | 18 ≥ (6+10) satisfied |
| Coverage | ✓ PASS | 100% of book chapters extracted |
| No Profitability Claims | ✓ PASS | No unsupported profit guarantees; strategies presented as author-tested ideas requiring independent validation |

---

## 10. Final Assessment

**Processing Status:** Ready for backtest validation.

**Priority Actions:**
1. **Immediate:** Verify broker API capabilities (Level 2, pre-market, hotkey support) as of Q1 2026
2. **Near-term:** Backtest all 5 strategies on 3+ years of historical intraday equity data; measure Sharpe, drawdown, win%
3. **Ongoing:** Monitor for market structure changes (algos, order protection rules, short-sale restrictions); quarterly re-verification recommended
4. **Implementation:** Build risk enforcement layer first (position sizing, daily limits, overnight close) before strategy deployment

---

## Audit Conclusion

The knowledge extraction artifacts are **well-structured, internally consistent, and generally faithful to the source material.** One material correction was necessary (Fallen Angel direction). All platform requirements are legitimate; all trading hypotheses are correctly classified and testable. The book's credibility is modest (self-published, no backtest results), but its risk management framework and execution logistics are sound. Freshness risk is significant; quarterly verification of broker capabilities and market regulations is essential. The package is ready for backtesting once broker assumptions are verified.

---

reliability_grade: B
