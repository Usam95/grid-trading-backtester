# 07 — Account for one grid allocation across exact epochs and assets

**What to build:** Add one allocation-isolated multi-asset subledger driven only by canonical postings. It must account for base, quote, and any actual fee asset; reservations; paired and grid-plan-epoch provenance; transition-pending obligations; retained quantities; and reproducible current and conservative equity views.

**Blocked by:** 05 — Persist and exactly replay one adaptive decision path; 06 — Derive and activate an obligation-backed adaptive initial epoch.

**Status:** ready-for-agent

- [ ] Every posting identifies run, allocation, grid plan epoch, asset, cause, source event, relevant transition/order/fill/cycle, event time, processing position, and schema.
- [ ] Asset conservation, posting balance, allocation ownership, reservation coverage, and bootstrap backing are checked after each atomic batch.
- [ ] Fees reduce the exact venue-reported asset once; quote-valued fee views never create a second deduction.
- [ ] Current grid equity and conservative liquidation equity are separate reproducible projections and expose unavailable valuation explicitly.
- [ ] Paired-lot provenance governs ordinary cycle holdings while retained inventory preserves its origin.
- [ ] Whole-account or foreign balances cannot seed, top up, or silently repair the grid allocation.
- [ ] Cancellation-pending and outcome-unknown old-epoch obligations remain committed until reconciled and cannot be reassigned to a proposed epoch.
- [ ] Golden fixtures cover received-base, received-quote, and third-asset fee cases.
