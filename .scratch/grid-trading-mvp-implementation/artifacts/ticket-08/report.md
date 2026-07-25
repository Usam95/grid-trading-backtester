# Ticket 08 report

## Implementation summary

Extended the canonical Ticket 07 allocation subledger and atomic SQLite journal with managed-order occupancy, cumulative fill evidence, one epoch-qualified paired obligation, deterministic paired-order generations, exact residual inventory, completed-cycle results, fixed-principal replacements, and replay-compatible fingerprints.

## Acceptance-criterion mapping

- Partial and late fills accumulate monotonically by deterministic fill identity; duplicate fills and source events are no-ops or rejected on conflicting economics.
- Each epoch/rung has one effective order across active, cancellation-pending, and outcome-unknown states; one source order retains one cumulative paired obligation.
- Paired quantities use exact net acquired base after native fees and deterministic venue quantization; invalid and rounded residuals remain owned with lot and epoch provenance.
- Cycles finalize exactly once after cumulative economic completion, including later terminal reconciliation, with exact acquisition, proceeds, native-asset fees, and immutable fixed-principal replacement sizing.
- Orders, fills, lots, obligations, cycles, and residuals persist and rebuild through the existing allocation projection and journal with deterministic identities and legacy v1 fingerprint compatibility.

## Focused tests and final baseline

Focused Ticket 08 plus Ticket 07 accounting/persistence: 37 passed. Focused canonical/accounting/persistence suite: 132 passed. Architecture, static-quality, formatting, lint, focused typing, and coverage checks passed. The complete baseline entrypoint was run once and stopped at its unchanged frontend precheck because Node/pnpm were unavailable; the canonical repository test/coverage baseline then passed with 280 passed, 2 skipped, and coverage accepted.

## Final combined Standards/Spec review findings

The review found and fixed delayed terminal cycle completion, new paired-order generation after an earlier cumulative slice completed, authoritative late fills after cancellation evidence, deterministic decimal quantization, source-scale fee/cost attribution, duplicate source-event handling, and legacy v1 journal fingerprint compatibility. No actionable findings remain.

## Ticket 09 and later

Ticket 09 and later behavior was not started.
