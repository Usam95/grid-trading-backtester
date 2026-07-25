# 09 — Enforce adaptive, capital, loss, freshness and venue-anomaly postures

**What to build:** Apply the accepted grid-adaptation, capital, commitment, loss, freshness, connectivity, clock, and venue-anomaly rules as one deterministic safety-posture overlay independent of grid and transition lifecycle. Include downtrend recovery, uncertain evidence, range exhaustion, and symbol suspension, maintenance, and delisting evidence.

**Blocked by:** 07 — Account for one grid allocation across exact epochs and assets; 08 — Complete cumulative partial-fill cycles across epochs.

**Status:** resolved

- [x] The immutable capital envelope, fee reserve, per-buy principal, effective-order capacity, venue headroom, and maximum planned inventory are enforced from worst-case commitments.
- [x] Daily loss and run drawdown select `REDUCE_ONLY`; terminal equity loss latches the global stop; warnings occur at the accepted approach thresholds.
- [x] Missing or stale valuation, strategy input, private-stream continuity, control-path availability, and clock evidence select their exact accepted posture.
- [x] Clock-offset decisions use defensible venue-time observations and distinguish scheduling delay while any authenticated timestamp rejection still fails closed.
- [x] Range exhaustion prevents exposure beyond outer rungs while preserving valid recovery-side obligations and owned inventory.
- [x] `TREND_DOWN` selects at least `REDUCE_ONLY`, emits no exposure-increasing buy or downward-bound-shift intent, and retains valid fully backed inventory-reducing recovery.
- [x] `UNCERTAIN` adaptation evidence selects `FROZEN` for placement and replacement; `RANGE_HIGH_VOLATILITY` cannot increase fixed quote sizing.
- [x] Symbol trading suspension or maintenance freezes unsafe commands and preserves evidence; a delisting notice creates a visible time-bounded wind-down case.
- [x] Grid lifecycle, grid adaptation state, epoch-transition state, runtime lifecycle, safety posture, freshness, and reconciliation are presented as separate facts.

## Answer

Implemented the deterministic canonical safety-posture overlay with accepted precedence, exact capital/loss/freshness/clock/adaptive/range/venue rules, persistent latch and recovery facts, deterministic identities, and separate typed FastAPI/Studio presentation. Focused backend, Ticket 07-08 regression, frontend, browser, architecture, static, and coverage checks passed; the delivery report is at `../artifacts/ticket-09/report.md`. Ticket 10 and later behavior was not started.
