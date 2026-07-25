# Ticket 06 report

## Implementation summary

Added a pure canonical initial-epoch derivation and activation service. It fails closed on inadmissible evidence, derives policy-bounded arithmetic or geometric ladders, assigns buy/sell/inactive roles against a distinct activation price, computes rounded initial obligations, conservative bootstrap fee coverage, maximum planned inventory, immutable epoch/replay identities, and explicit `REJECTED`, `BOOTSTRAPPING`, or `ACTIVE` outcomes. FastAPI, generated TypeScript contracts, and Studio present the evidence, state, gates, epoch, ladder, and bootstrap obligation.

## Acceptance-criterion mapping

All eight Ticket 06 criteria are covered by focused tests: evidence and boundary rejection never arm or retain activation; bounds, width, geometry, replay, and epoch identity are deterministic; both spacing modes include exact bounds; exact activation rungs are inactive; bootstrap quantity covers all sell obligations after venue rounding and conservative base-fee allowance; incomplete or partial bootstrap evidence blocks placement without scaling; typed API and Studio expose the complete initial-epoch projection.

## Tests, browser, and baseline

Focused domain/persistence/API checks passed; frontend unit tests, typecheck, and build passed. The focused Chromium initial-epoch workflow passed, and complete frontend verification finished with 2 browser tests passed and 1 network-only test skipped. The single complete baseline passed version, frontend, architecture, static quality, and 237 tests before identifying only new canonical coverage below its ratchet; focused invariant coverage was added, then the affected coverage stage passed with 242 tests, 2 skips, and the coverage baseline accepted.

## Final Standards/Spec review findings

The combined review found one actionable issue: rounded base quantity could reduce actual notional below the venue minimum. Activation now rejects that post-quantization condition and has a regression test. No remaining actionable standards or specification findings were found.

## Ticket 07 confirmation

Ticket 07 and later work was not started: no accounting subledger, fill processing, paired cycles, executable orders, command dispatch, epoch replacement, Paper, Testnet, or live behavior was added.
