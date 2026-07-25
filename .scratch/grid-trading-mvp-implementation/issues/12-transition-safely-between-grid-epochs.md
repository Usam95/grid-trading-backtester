# 12 — Transition safely between immutable grid epochs

**What to build:** Implement the complete guarded grid epoch transition through the canonical domain, journal, accounting, venue plan, API, and Studio seams. A confirmed change blocks old-epoch exposure, cancels and reconciles every effective obligation including late fills, derives and admits a replacement plan, optionally completes bounded bootstrap inside the original capital envelope, and activates without ambiguous old/new overlap.

**Blocked by:** 07 — Account for one grid allocation across exact epochs and assets; 08 — Complete cumulative partial-fill cycles across epochs; 09 — Enforce adaptive, capital, loss, freshness and venue-anomaly postures; 10 — Operate controls and terminal disposal during adaptation; 11 — Admit only venue-valid positive grid-epoch plans.

**Status:** resolved

- [x] The canonical transition is `ACTIVE → CHANGE_CONFIRMED → TRANSITION_REQUESTED → OLD_EXPOSURE_BLOCKED → CANCELLING → RECONCILING → DERIVING → VALIDATING → optional BOOTSTRAPPING → ACTIVATING → ACTIVE`.
- [x] Confirmation, hysteresis, minimum residence, cooldown, maximum frequency, and expiry use injected domain time and record an exact no-action or refusal when unsatisfied.
- [x] A transition request immediately prohibits old-epoch exposure-increasing placement/replacement while keeping cancellation, reconciliation, and permitted inventory reduction available.
- [x] Every effective old-epoch order becomes proven terminal or remains explicitly outcome-unknown; partial and late fills post to their original epoch before replacement validation.
- [x] The replacement plan is derived only from the admitted decision evidence and is revalidated against authoritative allocation, inventory, fees, posture, venue rules, order headroom, and positive economics.
- [x] Additional bootstrap is permitted only when exact backing remains inside the original immutable capital envelope and fee coverage; refusal never silently scales, tops up, or remains armed.
- [x] `TREND_DOWN` never derives or activates a downward-shifted epoch and remains recovery/`REDUCE_ONLY` until deterministic re-entry gates pass; `UNCERTAIN` remains `FROZEN`.
- [x] Old and new epoch exposure never overlaps ambiguously, and managed identities cannot be reused or transferred between epochs.
- [x] Crash injection at every transition boundary, unknown cancel, late-fill race, rule change, operator preemption, expiry, and restart rebuilds exactly and fails closed.
- [x] The typed API and Studio show current evidence/state, active/proposed epoch identities, transition progress, satisfied/failed gates, posture, inventory basis, and explanatory refusal.
- [x] Shared canonical fixtures produce identical decisions, postings, states, and fingerprints in direct-domain, persistence-replay, and fake-runtime harnesses.

## Answer

Implemented a guarded epoch-transition seam with canonical transition facts/evaluation, immutable old-order and late-fill provenance, replacement-plan revalidation through existing admission/venue economics, a replayable SQLite transition journal, deterministic fake-runtime parity, and a typed Studio/FastAPI epoch-transition contract with refreshed OpenAPI/TypeScript artifacts. Focused canonical, persistence, Studio contract, prerequisite regression, typed-frontend, browser, architecture, typing, static-quality, coverage, and final baseline checks passed. Later tickets were not started.
