# Audit Report: Trading Price Action Reversals (2011) — Al Brooks

**Audited:** 2026-07-25  
**Auditor:** Independent Verification Agent  
**Book ID:** trading-price-action-reversals-2011  
**Format:** PDF (578 pages)

---

## Audit Method

This audit followed the VERIFIER_PROMPT contract with focus on:

1. **Source Verification**: Extracted and verified PDF locators for all high-confidence claims and all candidate requirements
2. **Schema Validation**: Parsed JSONL, YAML formats; validated against defined schemas
3. **Critical Trading-Rule Classification**: Examined all 8 candidate requirements to identify which encode discretionary trading rules vs. genuine system requirements
4. **Invariant Verification**: Confirmed that insights >= (requirements + hypotheses)
5. **Sampling**: Reviewed 50% of insights including all TOP-10 requirements and all high-confidence claims
6. **Mechanical Checks**: Verified unique IDs, derived_from references, coverage, absence of long copyrighted passages

---

## Sampling Summary

**Sample Size:** 11 of 18 insights (61%)

- **High-confidence claims:** 7/7 (100%) — all sampled
- **TOP-10 requirements:** 8/8 (100%)
- **20% random spread:** 4 medium-confidence claims sampled

**Sampled Insights:**
- TPAR-C0-001 (Institutional money drives patterns) — PDF page 28 ✓
- TPAR-C1-002 (Trend line breaks required) — PDF pages 101-102 ✓
- TPAR-C2-003 (Signal bar strength) — PDF page 107 ✓
- TPAR-C4-004 (Climactic bars signal reversal) — PDF page 139 ✓
- TPAR-C4-005 (Vacuum effect) — PDF page 140 ✓
- TPAR-C9-009 (Failed breakouts) — PDF page 219 ✓
- TPAR-C25-013 (Fixed-risk position sizing) — PDF page 545 ✓
- Plus 4 additional medium-confidence claims across chapters 8, 15, 18, 20

**Locator Verification Result:** All cited PDF pages exist and contain faithful paraphrases of claims (not verbatim copies). No long copyrighted passages detected.

---

## CRITICAL CHECK: Trading Rules vs. System Requirements

### Finding: 3 Requirements Improperly Encoded Trading Rules

The worker produced **8 candidate requirements** for an Al Brooks price-action book. Per the audit contract, Al Brooks' discretionary trading setups (reversal bar patterns, entry/exit rules, trend/regime decisions) must be classified as **HYPOTHESES with rejection thresholds**, not engineering requirements.

**Analysis of Each Requirement:**

| ID | Title | Encoded Trading Rule? | Classification | Action Taken |
|---|---|---|---|---|
| R001 | Trend line drawing/break detection | NO — infrastructure | ✓ Legitimate | None |
| **R002** | Climactic bar detection (1.8x range, close %) | YES — reversal pattern | ❌ Trading Rule | **RECLASSIFIED** |
| R003 | Multi-timeframe data loading/alignment | NO — infrastructure | ✓ Legitimate | None |
| R004 | Position sizing formula (shares = risk/distance) | NO — risk management | ✓ Legitimate | None |
| **R005** | Failed breakout confirmation (1-3 bars) | YES — entry pattern | ❌ Trading Rule | **RECLASSIFIED** |
| R006 | Overnight gap risk detection | NO — infrastructure | ✓ Legitimate | None |
| **R007** | Always-in discipline enforcement | YES — trading discipline | ❌ Trading Rule | **RECLASSIFIED** |
| R008 | Opening range premarket support | NO — infrastructure | ✓ Legitimate | None |

### Corrections Made

**CORRECTION 1: R002 (Climactic Bar)**
- **Before:** "Backtester shall compute 20-bar rolling average true range; flag bars with range > 1.8x avg and close within 10% of bar extreme opposite open"
  - Problem: Encodes the climactic bar pattern definition (1.8x, 10%) as a requirement threshold
- **After:** "Backtester shall support custom pattern detection with rolling average calculations... provide pattern detector supporting parametrized conditions (e.g., range_ratio, close_position_pct)"
  - Solution: Reframed as infrastructure (rolling averages, configurable detection) while specific climactic thresholds remain in H002 hypothesis
- **Related:** H002 (Climactic bar predicts 70-80% reversal) already captures the trading rule

**CORRECTION 2: R005 (Failed Breakout)**
- **Before:** "Live system shall flag failed breakout (high>swing high, close<swing high) and confirm by next 1-3 bars closing < failed high; do NOT enter until confirmation"
  - Problem: Defines failed breakout pattern and entry rule as system requirement
- **After:** "Live system shall support entry confirmation logic with multi-bar sequence validation... support conditions that require validation across N subsequent bars"
  - Solution: Reframed as generic confirmation infrastructure while specific failed-breakout pattern logic remains in H003 hypothesis
- **Related:** H003 (Failed breakout predicts 60-70% reversal) already captures the trading rule

**CORRECTION 3: R007 (Always-in Discipline)**
- **Before:** "Live system shall enforce 'always-in' position discipline when trend active... no profit-taking exits until trend line break or risk limit breach"
  - Problem: Encodes a specific trading discipline as system requirement
- **After:** "Live system shall support position management policies with configurable discipline rules... allow trader to set discipline mode (e.g., 'always-in' vs 'profit-taking')"
  - Solution: Reframed as generic policy framework while always-in discipline benefits remain testable as a hypothesis
- **New Hypothesis:** H009 added to encode the always-in discipline hypothesis ("Always-in discipline increases profit capture by 20-40% vs profit-taking exits")

### Invariant Check

After reclassification:
- **Legitimate Requirements:** 5 (R001, R003, R004, R006, R008)
- **Hypotheses:** 9 (H001-H008 + new H009 for always-in discipline)
- **Insights:** 18
- **Invariant:** 18 ≥ 5 + 9 = 14 ✓ **SATISFIED**

---

## Schema and Mechanical Validation

**JSONL Parsing:** ✓ All 18 lines parse correctly as JSON objects  
**YAML Parsing:** ✓ candidate-requirements.yaml, hypotheses.yaml parse correctly  
**Unique IDs:** ✓ All ids (TPAR-C*, TPAR-R*, TPAR-H*) are unique within their types  
**derived_from References:** ✓ All derived_from point to valid insight ids (TPAR-C*)  
**Coverage:** ✓ No source chapters vanished; coverage.yaml consistent with extraction  
**Copyright:** ✓ No long (>100 word) verbatim passages detected; all claims paraphrased  

**Validation Command Result:**
```
VALIDATION OK: trading-price-action-reversals-2011 (18 insights)
```

---

## Quality Assessment by Category

### Source Credibility & Citation Quality

**Metadata Scores:**
- `source_credibility: 3/5` — Respected trader/author but methodology is discretionary
- `citation_quality: 2/5` — Mostly author assertions with limited external references
- `reproducibility: 2/5` — Discretionary rules hard to codify without expert annotation
- `likely_freshness: 2/5` — 2011 publication; market structure has changed significantly

**Assessment:** Appropriate scores given the subjective nature of price action methodology. No profitability claims presented as fact; limitations properly documented (discretionary patterns, no formal backtests, market structure evolution).

### Claim Strength vs. Evidence

**Sample of Claims vs. Evidence:**

| Claim | Evidence Type | Confidence | Appropriate? |
|---|---|---|---|
| "Institutional money drives 90% of volume" (C0-001) | Author assertion | High | ✓ Yes (baseline framing) |
| "Trend line breaks precede reversals" (C1-002) | Worked example with chart | High | ✓ Yes (testable pattern) |
| "Climactic bars → 70-80% reversals" (H002) | Multiple worked examples | Medium | ✓ Yes (with rejection threshold) |
| "Failed breakouts → 60-70% reversals" (H003) | Pattern assertion | Medium | ✓ Yes (with rejection threshold) |
| "Fixed-risk sizing outperforms fixed-share" (H008) | Theoretical mechanism | High | ✓ Yes (but unvalidated) |

**Finding:** All major claims appropriately scored for confidence and testability. No unsupported claims presented as fact. Hypotheses include explicit rejection criteria (e.g., "If reversal probability < 52%... reject").

### Applicability Tags

**Verified Sample:**
- All claims correctly tagged `lifecycle: [backtest, live]` where appropriate
- All tagged `asset_class: [equities]` — matches book focus (stocks, ES, CAT)
- `strategy` tags split appropriately between `stock_signal` (directional) and `shared` (universal)
- `concern` tags (alpha, execution, risk, reproducibility) are defensible

**Finding:** Applicability tagging is consistent and well-justified.

---

## Locator Problems & Ambiguities

**None Found.** All sampled claims have precise PDF page numbers and section references. Extract verification confirmed citations are faithful and accurate.

---

## Corrections Made During Audit

### Summary of Corrections

| Record ID | Type | Before → After | Reason |
|---|---|---|---|
| TPAR-R002 | Requirement | Pattern encoding → Infrastructure framing | Separated trading rule thresholds from system feature |
| TPAR-R005 | Requirement | Failed-breakout rule → Confirmation infrastructure | Separated pattern logic from generic confirmation system |
| TPAR-R007 | Requirement | Always-in enforcement → Policy framework | Separated discipline rule from configurable policy support |
| (New) | Hypothesis | (None) → H009: Always-in discipline benefits | Captured trading discipline hypothesis with rejection criteria |
| metadata.yaml | Metadata | processing_status: synthesized → audited | Mark audit completion |

**All corrections validated by `python booktool.py validate`.**

---

## Limitations

1. **Discretionary Pattern Recognition:** Al Brooks' methodology (e.g., "strong signal bar," "proper trend line," "sufficient climax") relies on visual/intuitive judgment. Reproducibility will require either expert annotation or machine learning parameter tuning.

2. **Freshness Risk:** 2011 publication; modern market structure (HFT, passive flows, reduced tick spreads, options market growth) may invalidate edge claims. Hypotheses include freshness_concerns field; recommend testing on recent data.

3. **No Black-Box Backtests:** Book provides anecdotal examples, not formal statistical backtests with transaction costs, slippage, or confidence intervals. Worker correctly noted this limitation in metadata.

4. **Institutional Behavior Assumptions:** Assumptions about institutional positioning, order-book dynamics, and market-maker behavior are not independently validated. Market microstructure changes may reduce effectiveness.

5. **Pattern Sensitivity:** Some patterns (double-tops, wedges, final flags) are context-dependent (trending vs. range-bound markets). Worker captured open questions but did not fully specify context sensitivity.

---

## Coverage Analysis

**Chapter Coverage:** All 25 chapters referenced in insights; no gaps.  
**Pattern Types Covered:** 12 distinct reversal patterns (climactic, double-top/bottom, wedge, final flag, etc.)  
**Timeframes:** 5-60 min intraday, daily, swing  
**Asset Classes:** Equities (primary), brief index futures (ES), no crypto/forex  
**Risk Topics:** Position sizing, stop placement, gap risk, overnight exposure  

**Finding:** Good breadth across book content.

---

## Key Insights & Hypotheses Summary

**8 Testable Hypotheses:**
1. H001: Trend break + signal bar → 55-65% reversal probability
2. H002: Climactic bar (2x range) → 70-80% reversal within 2-3 bars
3. H003: Failed breakout → 60-70% reversal
4. H004: Double-top + pullback → 60-70% short success
5. H005: Opening range breakout → 55-60% continuation
6. H006: Shallow pullback (<50% retracement) → stronger reversal
7. H007: Multi-timeframe alignment +5-10% edge
8. H008: Fixed-risk sizing +10-15% Sharpe vs fixed-share
9. **H009 (NEW):** Always-in discipline +20-40% profit capture vs profit-taking

**5 Legitimate System Requirements:**
1. R001: Trend line detection & break calculation
2. R003: Multi-timeframe data loading & alignment
3. R004: Position sizing formula (max_risk / stop_distance)
4. R006: Overnight gap detection & impact measurement
5. R008: Premarket/opening range support

---

## Recommendations for Use

**Suitable For:**
- Backtesting framework development (R001-R008 features enable pattern testing)
- Risk management training (position sizing, stop placement rules are sound)
- Pattern library reference (H001-H008 provide taxonomy of price action setups)

**Requires Caution:**
- Live trading without validation on recent data (2011 market structure outdated)
- High-frequency or algorithmic trading (patterns are discretionary, not algorithmic)
- Cross-asset generalization (book focused on equities; crypto/forex applicability unclear)

---

## Final Validation

**Validation Command (Final):**
```bash
$ python booktool.py validate --book-id trading-price-action-reversals-2011
VALIDATION OK: trading-price-action-reversals-2011 (18 insights)
```

**Processing Status:** audited (updated in metadata.yaml)  
**All corrections applied and validated.**

---

## Conclusion

The trading-price-action-reversals-2011 package extraction is **well-executed overall** with **good coverage and appropriate credibility scoring**. The critical audit identified and corrected an important conceptual issue: **3 requirements improperly encoded trading rules rather than system requirements**. After reclassification (R002, R005 refactored to infrastructure-focused; R007 refactored + new H009 added), the package now properly separates:

- **Trading hypotheses** (H001-H009): Testable market behavior patterns with rejection criteria
- **System requirements** (R001, R003-R004, R006, R008): Infrastructure features enabling backtest/live execution
- **Insights** (18 total): Source claims and observations from the book

The invariant (18 insights ≥ 5 requirements + 9 hypotheses) is satisfied. All locators verified, schemas validated, and corrections logged.

---

reliability_grade: B
