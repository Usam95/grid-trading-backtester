# 08 — Complete cumulative partial-fill cycles across epochs

**What to build:** Extend the canonical grid through partial and cumulative fills so one epoch-qualified rung obligation produces one cumulative paired obligation and one completed cycle. Quantities and provenance must survive later epoch changes while following actual net inventory, fixed quote sizing, venue residuals, and exact fee evidence.

**Blocked by:** 07 — Account for one grid allocation across exact epochs and assets.

**Status:** resolved

- [x] Several partial fills of one managed order accumulate monotonically without creating duplicate paired orders or cycles.
- [x] A paired sell uses actual net base acquired after all source-exact fee and rounding effects.
- [x] Each rung has no more than one effective managed order and one side at a time, including unknown and cancellation-pending states.
- [x] A completed pair counts exactly one realized cycle with finalized acquisition, proceeds, and attributable native-asset fees.
- [x] Orders, fills, inventory lots, pair obligations, completed cycles, and retained residuals preserve their originating epoch through replay and transition reconciliation.
- [x] Replacement exposure uses the immutable fixed quote principal; profit remains uncommitted and does not compound.
- [x] Pending dust and venue-invalid residuals remain exact owned inventory and cannot be rounded away.
- [x] The cumulative order/cycle state and realized result are visible and exactly replayable.

## Answer

Extended the Ticket 07 allocation projection and atomic journal with deterministic managed-order, cumulative-fill, paired-obligation, residual, and completed-cycle state. Partial and late fills remain idempotent and epoch-qualified; paired quantities follow exact net base and venue quantization; cycle results preserve exact acquisition, proceeds, and native fees; replacements retain fixed principal; and v1 journal fingerprints remain compatible. Focused canonical/accounting/persistence checks and the 280-test canonical repository suite passed with coverage accepted. The delivery report is at `../artifacts/ticket-08/report.md`; Ticket 09 and later behavior was not started.
