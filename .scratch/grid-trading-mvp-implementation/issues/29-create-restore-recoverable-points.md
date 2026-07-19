# 29 — Create and restore verified recoverable points

**What to build:** Protect the complete online durable state with transactionally consistent, content-verified off-node recoverable points and a deterministic restore path that selects a compatible point, replays the journal tail, verifies invariants, reconciles external facts, and finishes operator-accessible and frozen.

**Blocked by:** 23 — Reconcile ambiguity and restart frozen; 28 — Compact, retain and download verified evidence.

**Status:** ready-for-agent

- [ ] A changed authoritative state triggers complete online backup at the accepted nominal cadence without blocking safety-critical processing.
- [ ] Only a complete uploaded, checksum-verified, reader-verified, catalogued package with exact schema/release/dependency identities counts as a recoverable point.
- [ ] Protected-position lag is measured against committed application history and raises the accepted protection failure before exceeding the 15-minute RPO.
- [ ] Daily, pre-change, post-change, fallback, reference, expiry, and preservation rules retain the accepted point set.
- [ ] Restore rejects partial, corrupt, incompatible, or unverified points and can fall back without overwriting failed evidence.
- [ ] Newest and older-point restores rebuild projections, replay the tail, pass invariants, admit late evidence, reconcile, and finish `FROZEN_READY` without rolling the venue back.
- [ ] Weekly isolated restore and full-disaster drill entry points produce content-identified reports and measure the 60-minute frozen RTO boundary.
- [ ] Credential isolation, unavailable read-only venue evidence, and late-fill-during-outage cases are tested.

