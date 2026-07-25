# 06 — Derive and activate an obligation-backed adaptive initial epoch

**What to build:** Use quality-approved past-only evidence and the immutable adaptation policy to classify the initial state, derive the first immutable Spot grid plan epoch, prove strict activation eligibility, compute the real bootstrap obligation, and visualize the evidence, state, epoch identity, gates, and inactive/initial ladder without assuming fills.

**Blocked by:** 04 — Expand the canonical exact adaptive-policy and event seam; 05 — Persist and exactly replay one adaptive decision path.

**Status:** resolved

- [x] Insufficient warm-up, incomplete/future/stale/gapped evidence, or `UNCERTAIN` state rejects activation without a pending armed action.
- [x] The derived exact bounds and width are deterministic consequences of the admitted observations and immutable policy limits.
- [x] Rung count includes both exact derived bounds and geometric spacing is the explicit default while arithmetic remains supported.
- [x] The activation price is never inserted into the geometry and an exact activation rung begins inactive.
- [x] Price at or outside either derived bound rejects activation before acquisition and does not leave a pending armed action.
- [x] Bootstrap base quantity is derived from all initial sell obligations, venue rounding, and conservative fee coverage.
- [x] Incomplete bootstrap evidence keeps the run bootstrapping and prevents ladder placement or silent scaling.
- [x] The adaptation evidence/state, grid plan epoch identity, quantized plan, initial buy/sell/inactive roles, maximum planned inventory, and bootstrap obligation are visible through the typed Studio contract and replay exactly.

## Answer

Implemented a pure obligation-backed adaptive initial-epoch service with fail-closed evidence and activation gates, deterministic arithmetic/geometric geometry, exact rung roles, conservative rounded bootstrap coverage, maximum planned inventory, immutable replay identity, and explicit `REJECTED`/`BOOTSTRAPPING`/`ACTIVE` presentation. FastAPI and Studio now expose the evidence, state, gates, epoch, ladder, and bootstrap obligation without order placement or later-ticket accounting.

Focused domain, persistence, API, frontend, and browser checks passed. The complete baseline's test, frontend, architecture, and static stages passed; its initial canonical coverage ratchet finding was closed with focused invariant tests, after which 242 tests passed and coverage was accepted. The delivery report is at `../artifacts/ticket-06/report.md`. Ticket 07 and later work was not started.
