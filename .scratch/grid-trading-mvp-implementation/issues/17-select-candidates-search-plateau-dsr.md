# 17 — Select candidates with bounded search, plateaus and DSR

**What to build:** Implement the deterministic strategy-only search and selection procedure: seeded Sobol exploration, bounded local plateau proof, exact finalist evaluation, full trial-family accounting, Deflated Sharpe credibility, and constrained return-led ranking. Rehearse the entire procedure on development-only evidence before any locked holdout is exposed.

**Blocked by:** 16 — Prove symbol, regime and adverse-execution robustness.

**Status:** ready-for-agent

- [ ] Only accepted bounds, rung count, spacing, fixed quote principal, and compatible stop parameters are searchable; costs, accounting, execution, risk, and evidence rules remain fixed.
- [ ] Each spacing stratum uses the declared seeded Sobol budget, maps duplicates deterministically, and records every selection exposure in the trial family.
- [ ] No more than the accepted plateau seeds and neighborhoods are evaluated, with stable-neighbor proof and explicit rejection of isolated spikes.
- [ ] DSR uses frozen daily-return frequency, serial-dependence, higher-moment, trial-family, formula, and numerical-test semantics and requires the accepted probability.
- [ ] Candidate ranking applies every hard gate before the accepted lexicographic return/drawdown tie process and cannot produce a composite trust score.
- [ ] A complete development-only methodology rehearsal reports whether DSR, return, panel, regime, activity, quantization, and adverse gates are jointly feasible without changing thresholds after results.
- [ ] The chosen finalist and every rejected contender retain exact rationale and immutable evidence identities.

