# 08 — Complete cumulative partial-fill paired cycles

**What to build:** Extend the canonical grid through partial and cumulative fills so one rung obligation produces one cumulative paired obligation and one completed cycle. Quantities must follow actual net inventory, fixed quote sizing, venue residuals, and exact fee evidence.

**Blocked by:** 07 — Account for one grid allocation in exact native assets.

**Status:** ready-for-agent

- [ ] Several partial fills of one managed order accumulate monotonically without creating duplicate paired orders or cycles.
- [ ] A paired sell uses actual net base acquired after all source-exact fee and rounding effects.
- [ ] Each rung has no more than one effective managed order and one side at a time, including unknown and cancellation-pending states.
- [ ] A completed pair counts exactly one realized cycle with finalized acquisition, proceeds, and attributable native-asset fees.
- [ ] Replacement exposure uses the immutable fixed quote principal; profit remains uncommitted and does not compound.
- [ ] Pending dust and venue-invalid residuals remain exact owned inventory and cannot be rounded away.
- [ ] The cumulative order/cycle state and realized result are visible and exactly replayable.

