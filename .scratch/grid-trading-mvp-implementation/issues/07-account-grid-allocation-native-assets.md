# 07 — Account for one grid allocation across exact epochs and assets

**What to build:** Add one allocation-isolated multi-asset subledger driven only by canonical postings. It must account for base, quote, and any actual fee asset; reservations; paired and grid-plan-epoch provenance; transition-pending obligations; retained quantities; and reproducible current and conservative equity views.

**Blocked by:** 05 — Persist and exactly replay one adaptive decision path; 06 — Derive and activate an obligation-backed adaptive initial epoch.

**Status:** resolved

- [x] Every posting identifies run, allocation, grid plan epoch, asset, cause, source event, relevant transition/order/fill/cycle, event time, processing position, and schema.
- [x] Asset conservation, posting balance, allocation ownership, reservation coverage, and bootstrap backing are checked after each atomic batch.
- [x] Fees reduce the exact venue-reported asset once; quote-valued fee views never create a second deduction.
- [x] Current grid equity and conservative liquidation equity are separate reproducible projections and expose unavailable valuation explicitly.
- [x] Paired-lot provenance governs ordinary cycle holdings while retained inventory preserves its origin.
- [x] Whole-account or foreign balances cannot seed, top up, or silently repair the grid allocation.
- [x] Cancellation-pending and outcome-unknown old-epoch obligations remain committed until reconciled and cannot be reassigned to a proposed epoch.
- [x] Golden fixtures cover received-base, received-quote, and third-asset fee cases.

## Answer

Implemented an immutable exact native-asset posting model, allocation-isolated projection, atomic SQLite journal, five post-batch invariants, exact fee handling for base/quote/third assets, reservation and bootstrap backing, lot/retained provenance, explicit current and conservative valuation views, and deterministic replay/fingerprints. Focused accounting/persistence tests, architecture/static/contract checks, and the complete 257-test repository baseline passed with coverage accepted. The delivery report is at `../artifacts/ticket-07/report.md`; Ticket 08 and later behavior was not started.
