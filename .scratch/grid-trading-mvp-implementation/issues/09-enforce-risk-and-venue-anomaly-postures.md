# 09 — Enforce capital, loss, freshness and venue-anomaly postures

**What to build:** Apply the accepted capital, commitment, loss, freshness, connectivity, clock, and venue-anomaly rules as a deterministic safety-posture overlay independent of grid lifecycle. Include range exhaustion and explicit handling for symbol suspension, maintenance, and delisting evidence.

**Blocked by:** 07 — Account for one grid allocation in exact native assets; 08 — Complete cumulative partial-fill paired cycles.

**Status:** ready-for-agent

- [ ] The immutable capital envelope, fee reserve, per-buy principal, effective-order capacity, venue headroom, and maximum planned inventory are enforced from worst-case commitments.
- [ ] Daily loss and run drawdown select `REDUCE_ONLY`; terminal equity loss latches the global stop; warnings occur at the accepted approach thresholds.
- [ ] Missing or stale valuation, strategy input, private-stream continuity, control-path availability, and clock evidence select their exact accepted posture.
- [ ] Clock-offset decisions use defensible venue-time observations and distinguish scheduling delay while any authenticated timestamp rejection still fails closed.
- [ ] Range exhaustion prevents exposure beyond outer rungs while preserving valid recovery-side obligations and owned inventory.
- [ ] Symbol trading suspension or maintenance freezes unsafe commands and preserves evidence; a delisting notice creates a visible time-bounded wind-down case.
- [ ] Grid lifecycle, runtime lifecycle, safety posture, freshness, and reconciliation are presented as separate facts.

