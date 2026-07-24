# 08 — Complete cumulative partial-fill cycles across epochs

**What to build:** Extend the canonical grid through partial and cumulative fills so one epoch-qualified rung obligation produces one cumulative paired obligation and one completed cycle. Quantities and provenance must survive later epoch changes while following actual net inventory, fixed quote sizing, venue residuals, and exact fee evidence.

**Blocked by:** 07 — Account for one grid allocation across exact epochs and assets.

**Status:** ready-for-agent

- [ ] Several partial fills of one managed order accumulate monotonically without creating duplicate paired orders or cycles.
- [ ] A paired sell uses actual net base acquired after all source-exact fee and rounding effects.
- [ ] Each rung has no more than one effective managed order and one side at a time, including unknown and cancellation-pending states.
- [ ] A completed pair counts exactly one realized cycle with finalized acquisition, proceeds, and attributable native-asset fees.
- [ ] Orders, fills, inventory lots, pair obligations, completed cycles, and retained residuals preserve their originating epoch through replay and transition reconciliation.
- [ ] Replacement exposure uses the immutable fixed quote principal; profit remains uncommitted and does not compound.
- [ ] Pending dust and venue-invalid residuals remain exact owned inventory and cannot be rounded away.
- [ ] The cumulative order/cycle state and realized result are visible and exactly replayable.
