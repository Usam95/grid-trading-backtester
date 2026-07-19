# 05 — Validation and statistics findings

Walk-forward design, multiple-testing control, regimes, and the feasibility of the promotion gate
stack. (See also VAL-1 and VAL-2 in file 01.)

---

## VAL-3 — The gate stack is long and non-compensating; estimate the joint pass probability · S2 · finding · `ready-for-human`

Promotion requires passing, independently and without compensation (spec §Acceptance 1–25):
rolling folds, expanding sensitivity, 5-symbol panel, 9-regime coverage, plateau stability, DSR
0.95, sealed minute+event holdout with a 1pp fidelity-parity band, completed-cycle activity,
five adverse-execution scenarios, 30–90d paper, 13 Testnet families + 7-day soak, then a capped
first-live probation.

Each gate is individually reasonable, but they are **conjunctive** on a **single-use holdout** with
**no runner-up substitution** (issue 07). The joint probability that a real grid candidate clears
*all* of them — especially DSR (VAL-1) intersected with modest returns (ECO-1) and small-order
feasibility (ECO-2) — may be low. If the first frozen finalist fails the consumed holdout, the
process demands a **genuinely later** holdout (calendar wait) before retry.

**Risk:** the operator could invest months and never get a candidate through, not because the
method is wrong but because the gate stack is *jointly* very strict for a low-edge strategy.

**Fix:** before committing, run an **end-to-end dry run on already-available history** (treating a
past 12 months as a mock holdout) to estimate the realistic pass rate and identify which gate binds
first. Calibrate the *jointly* binding gates rather than each in isolation.

---

## VAL-4 — Single-use holdout + calendar-gated retry can stall the project for quarters · S2 · finding · `needs-info`

"The holdout is exposed once; a source correction after exposure requires a newly eligible future
holdout" and failure "requires a genuinely later holdout before requalification" (spec §Acceptance
3; issue 07). This is statistically pure, but operationally it means **each failed attempt costs a
new future 12 months** (or at least a fresh eligible window). With a low joint pass rate (VAL-3),
the project can enter a multi-quarter loop.

**Fix:** define, up front, **how many holdout windows** are reserved and the minimum spacing, and
accept that the method may require holding back several years. Alternatively, allow a **nested/rolling
holdout budget** declared in advance (still leak-free) so retries don't each cost a full year.

---

## VAL-5 — Deterministic 5-symbol panel by 10th-percentile volume may be unstable/adversarial · S3 · finding · `ready-for-agent`

The panel is chosen by "10th percentile of monthly median daily quote volume across 48 development
months," with **fewer than five blocking the gate** and "the fifth negative member remains visible
and non-replaceable" (issue 07). Two concerns:
1. Ranking by a **10th-percentile liquidity floor** biases toward symbols that were *consistently*
   liquid — again the majors (VAL-2) — and may exclude the ranging mid-caps grids like.
2. A single deterministic selection with **no replacement** means one unlucky panel member (e.g., a
   symbol that trended hard for 4 years) can sink the "≥4 of 5 positive" gate for reasons unrelated
   to the proposed live symbol.

**Fix:** verify the deterministic rule yields a *grid-relevant* panel on real data; consider
stratifying the panel by regime/behavior rather than by liquidity alone (declared in advance to stay
leak-free).

---

## VAL-6 — Nine-regime cell minimums vs a low-turnover grid may be under-powered · S3 · finding · `ready-for-agent`

Regime cells require ≥20 days each and ≥60 per axis, with ≥5/9 positive and no cell >70% of positive
profit (spec §Acceptance 5; issue 07). A grid that completes only ~24 cycles across an entire fold
(the activity gate, §Acceptance 10) will have **very few cycles per 20-day cell** — many cells will
have near-zero trading activity, making per-cell "positive/negative" a **low-signal, high-variance**
label dominated by inventory mark-to-market rather than realized grid edge.

**Fix:** clarify whether cell positivity is judged on **realized cycle P&L** or **total (incl.
mark-to-market)** equity change; if the former, confirm enough cycles land per cell to be meaningful;
if the latter, acknowledge the regime gate largely measures **base-asset price behavior**, not the
grid.

---

## VAL-7 — Statistical block-resampling deferred — reasonable, but document the residual risk · S3 · finding · `wontfix`

Issue 07 defers block bootstrap / Reality Check / SPA to post-MVP, arguing the other layers provide
robustness. That is a defensible scope call. The residual is that **path-dependent luck** (one
fortunate range period driving results) is only *partially* controlled by folds/regimes. The DSR
gate is the main multiple-testing control and (per VAL-1) may itself be miscalibrated. Keep the
declared extension seam; revisit if DSR is downgraded to diagnostic.

---

## VAL-8 — Fidelity-parity ≤1pp between minute and event holdout may be optimistic for maker fills · S3 · finding · `ready-for-agent`

Spec §Acceptance 9 / issue 07 require total-return and max-drawdown to differ by **≤1.00 pp**
between the **candle** and **event/BBO+depth** holdout passes. For a **post-only maker** grid, fill
realism differs *most* between candle-cross assumptions and real queue position — exactly the
dimension where a 1pp band is easiest to blow. If minute simulation over-fills (assumes a cross =
fill) while event replay models queue-ahead/no-fill, the gap on a low-margin grid can exceed 1pp.

**Fix:** confirm empirically that the conservative candle fill policy (resting eligibility, strict
trade-through, 5% volume budget; issue 03) actually lands within 1pp of event replay on the proposed
symbol before treating the band as a fixed gate; otherwise widen or make asymmetric with rationale.
