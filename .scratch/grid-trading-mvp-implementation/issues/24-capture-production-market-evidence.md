# 24 — Capture production market evidence with continuity

**What to build:** Normalize and durably capture production public trades, best bid/offer, and targeted depth for one active symbol with explicit stream generations, rotation, ordering, gaps, snapshot bridges, bounded buffers, and replayable source identities.

**Blocked by:** 03 — Prove the manifested production-data tracer bullet; 05 — Persist and exactly replay one canonical decision path; 20 — Run one mode-isolated runtime against a fake venue; 22 — Explain runtime health, incidents and alerts.

**Status:** ready-for-agent

- [ ] Production public streams normalize into the same canonical market-event contracts used by historical replay.
- [ ] Each connection generation records endpoint, subscriptions, source identities, continuity result, link to its predecessor, and closure reason.
- [ ] Finite-stream rotation overlaps before the accepted deadline and proves continuity before retiring the predecessor.
- [ ] Duplicate, out-of-order, missing, stale, overflowed, or contradictory evidence creates an explicit gap/anomaly and cannot be silently dropped or reordered.
- [ ] Depth uses a proven snapshot/diff bridge; missing or inconsistent depth downgrades/fails according to the accepted decision policy.
- [ ] Every observed trade and BBO for the active symbol is retained; decision-relevant depth is retained and raw diff depth stays in the bounded incident ring.
- [ ] Capture load, queue age, disk growth, and fidelity remain observable and bounded under representative bursts.
