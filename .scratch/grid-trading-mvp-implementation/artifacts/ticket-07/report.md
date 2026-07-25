# Ticket 07 report

## Implementation summary

Added one immutable allocation-isolated multi-asset subledger derived solely from exact canonical postings, with atomic SQLite persistence, deterministic replay/fingerprints, native fee accounting, reservations, bootstrap backing, lot provenance, retained inventory, and separate current/conservative equity projections with explicit unavailable valuation.

## Acceptance-criterion mapping

- Posting records carry run, allocation, epoch, asset, exact amount, cause, source event/time, processing position, schema, and applicable transition/order/fill/cycle identities.
- Every atomic batch enforces native-asset conservation, posting balance, allocation ownership, reservation coverage, and bootstrap backing.
- Base, quote, and venue-reported third-asset fees are deducted exactly once; quote fee values are non-mutating valuations.
- Paired lots and retained holdings preserve originating epoch provenance.
- Initial allocation funding is exact and one-time; foreign allocations, whole-account top-ups, and silent repairs are rejected.
- Cancellation-pending and outcome-unknown old-epoch commitments cannot be released or reassigned until a reconciled terminal posting proves the outcome.
- Current grid equity and conservative liquidation equity are deterministic, distinct, and unavailable when required valuation evidence is absent.
- Golden fixtures cover fees in received base, received quote, and a third asset.

## Focused tests and final baseline

Focused Ticket 07 accounting/persistence: 20 passed. Adjacent canonical persistence/initial-epoch checks: 41 passed. Architecture, static-quality, and baseline contract checks passed. Complete repository baseline: 257 passed, 2 skipped; focused coverage additions closed the new-module ratchet and the final coverage baseline was accepted.

## Final combined Standards/Spec review findings

The review found and fixed the reconciled pending-obligation release guard and replaced replay-on-read persistence with a full deterministic projection snapshot plus replay verification. The final review found no remaining actionable issues.

## Ticket 08 and later

Ticket 08 and later behavior was not started.
