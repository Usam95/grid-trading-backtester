# 06 — Derive and activate an obligation-backed adaptive initial epoch

**What to build:** Use quality-approved past-only evidence and the immutable adaptation policy to classify the initial state, derive the first immutable Spot grid plan epoch, prove strict activation eligibility, compute the real bootstrap obligation, and visualize the evidence, state, epoch identity, gates, and inactive/initial ladder without assuming fills.

**Blocked by:** 04 — Expand the canonical exact adaptive-policy and event seam; 05 — Persist and exactly replay one adaptive decision path.

**Status:** ready-for-agent

- [ ] Insufficient warm-up, incomplete/future/stale/gapped evidence, or `UNCERTAIN` state rejects activation without a pending armed action.
- [ ] The derived exact bounds and width are deterministic consequences of the admitted observations and immutable policy limits.
- [ ] Rung count includes both exact derived bounds and geometric spacing is the explicit default while arithmetic remains supported.
- [ ] The activation price is never inserted into the geometry and an exact activation rung begins inactive.
- [ ] Price at or outside either derived bound rejects activation before acquisition and does not leave a pending armed action.
- [ ] Bootstrap base quantity is derived from all initial sell obligations, venue rounding, and conservative fee coverage.
- [ ] Incomplete bootstrap evidence keeps the run bootstrapping and prevents ladder placement or silent scaling.
- [ ] The adaptation evidence/state, grid plan epoch identity, quantized plan, initial buy/sell/inactive roles, maximum planned inventory, and bootstrap obligation are visible through the typed Studio contract and replay exactly.
