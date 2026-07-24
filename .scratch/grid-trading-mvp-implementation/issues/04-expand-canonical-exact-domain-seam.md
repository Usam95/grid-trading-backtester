# 04 — Expand the canonical exact adaptive-policy and event seam

**What to build:** Add the canonical immutable strategy and adaptation-policy configuration, source-exact numeric values, domain time, event envelopes, past-only observation evidence, grid adaptation states, grid-plan-epoch identities, and stable causal identities beside the current float/candle model. Translate one existing backtest through this seam and expose its adaptation decision and deterministic identity through the typed API and Studio without yet removing the old form.

**Blocked by:** 01 — Freeze the reproducible baseline and current normative contract; 02 — Expand a typed Studio shell around the existing backtest.

**Status:** ready-for-agent

- [ ] Asset, price, quantity, fee, bound, and venue-rule values preserve decimal source meaning without binary floating-point accounting.
- [ ] Configuration is immutable, versioned, content-identified, and distinguishes operator inputs from mechanically derived plans.
- [ ] Adaptation policy expresses exact observation windows, thresholds, confirmation, hysteresis, minimum residence, cooldown, expiry, transition-frequency, width, and upward-shift limits without embedding venue, persistence, or UI behavior.
- [ ] Only complete past observations at or before the decision boundary can affect `RANGE_NORMAL`, `RANGE_HIGH_VOLATILITY`, `TREND_UP`, `TREND_DOWN`, or `UNCERTAIN`; incomplete, future, stale, gapped, and contradictory evidence fail closed.
- [ ] Every mechanically derived ladder is an immutable content-identified grid plan epoch linked to its evidence, decision, predecessor, unquantized values, venue rules, quantized plan, and obligations.
- [ ] Canonical events carry stable event, source, correlation, causation, schema, and domain-time identities.
- [ ] Domain behavior is executable with an injected clock and without filesystem, database, web, venue, or cloud imports.
- [ ] One characterized current scenario translates through the new seam and reports an explicit semantic difference from the legacy adaptive implementation rather than silently inheriting its cancel-all/rebuild or ATR-default behavior.
- [ ] Invalid or ambiguous values fail at the boundary and have executable negative tests.
