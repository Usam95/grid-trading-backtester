# 04 — Expand the canonical exact adaptive-policy and event seam

**What to build:** Add the canonical immutable strategy and adaptation-policy configuration, source-exact numeric values, domain time, event envelopes, past-only observation evidence, grid adaptation states, grid-plan-epoch identities, and stable causal identities beside the current float/candle model. Translate one existing backtest through this seam and expose its adaptation decision and deterministic identity through the typed API and Studio without yet removing the old form.

**Blocked by:** 01 — Freeze the reproducible baseline and current normative contract; 02 — Expand a typed Studio shell around the existing backtest.

**Status:** resolved

- [x] Asset, price, quantity, fee, bound, and venue-rule values preserve decimal source meaning without binary floating-point accounting.
- [x] Configuration is immutable, versioned, content-identified, and distinguishes operator inputs from mechanically derived plans.
- [x] Adaptation policy expresses exact observation windows, thresholds, confirmation, hysteresis, minimum residence, cooldown, expiry, transition-frequency, width, and upward-shift limits without embedding venue, persistence, or UI behavior.
- [x] Only complete past observations at or before the decision boundary can affect `RANGE_NORMAL`, `RANGE_HIGH_VOLATILITY`, `TREND_UP`, `TREND_DOWN`, or `UNCERTAIN`; incomplete, future, stale, gapped, and contradictory evidence fail closed.
- [x] Every mechanically derived ladder is an immutable content-identified grid plan epoch linked to its evidence, decision, predecessor, unquantized values, venue rules, quantized plan, and obligations.
- [x] Canonical events carry stable event, source, correlation, causation, schema, and domain-time identities.
- [x] Domain behavior is executable with an injected clock and without filesystem, database, web, venue, or cloud imports.
- [x] One characterized current scenario translates through the new seam and reports an explicit semantic difference from the legacy adaptive implementation rather than silently inheriting its cancel-all/rebuild or ATR-default behavior.
- [x] Invalid or ambiguous values fail at the boundary and have executable negative tests.

## Answer

Implemented the canonical exact adaptive-policy and event seam in the commit
containing this Answer. The delivery adds source-exact decimal values,
immutable versioned strategy/policy configuration, injected domain time,
canonical causal event envelopes, content-identified past-only observations
and decisions for all five adaptation states, and immutable grid-plan epochs
whose identities cover predecessor, derivation causality/semantics, exact and
quantized rungs, venue rules, obligations, and allocations.

The typed FastAPI endpoint and generated Studio contract present configuration,
observation, event, decision, derivation-causation, epoch identities, operator
inputs, mechanically derived values, and the explicit legacy comparison. The
characterization executes one bounded 120-bar legacy adaptive backtest,
observes its effective ATR default and cancellation behavior, and reports
semantic differences instead of claiming false parity.

Focused domain/property/contract tests, API tests, frontend unit/type/build
checks, architecture and quality ratchets, the complete backend/frontend
baseline, and the real Chromium workflow were run. Browser verification
confirmed deterministic identities remain stable across refresh/navigation
and the legacy Studio remains available. Required evidence is under
`.scratch/grid-trading-mvp-implementation/artifacts/ticket-04/`.

Explicitly excluded: persistence/journaling, full adaptive initialization,
bootstrap acquisition, accounting, order execution/cancellation/reconciliation,
epoch activation or transition behavior, Paper, Testnet, live operation, and
all Ticket 05 or later work.
