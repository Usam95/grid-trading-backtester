# 15 — Run a resumable adaptive research job and visualize its epochs

**What to build:** Turn a canonical adaptive configuration and admitted production dataset into a durable local research job that survives browser closure, reports progress and evidence identity, and produces a return-led result with interactive price, adaptation-state, grid-epoch, transition, gate/refusal, order, fill, cycle, inventory, equity, drawdown, fee, and safety overlays.

**Blocked by:** 02 — Expand a typed Studio shell around the existing backtest; 13 — Run conservative adaptive candle simulation through the canonical core; 14 — Build the synchronized ten-symbol EUR production archive.

**Status:** ready-for-agent

- [ ] The browser creates and observes a durable local job but does not own or execute it.
- [ ] Restarting Studio or its browser reconnects to job progress and final evidence without rerunning completed work.
- [ ] The result binds exact code, configuration, dataset, venue-rule, fee, execution-model, schema, and seed identities.
- [ ] Net return leads the result while correctness, accounting, risk, data, and replay gates remain separately visible and non-compensating.
- [ ] The trade visualization supports drill-down from a fill/cycle/safety event to its causal evidence.
- [ ] The grid adaptation view shows the past-only observation identity, state, active/proposed epoch, transition timeline, gate/refusal reasons, and resulting posture without implementing decisions in the browser.
- [ ] Studio states plainly that the inventory grid is net-long base exposure and that the `250 USDT` Azure MVP is a validation/learning vehicle rather than infrastructure-net-profitable operation.
- [ ] Cancellation and failure leave an explicit resumable or terminal job state without corrupting prior results.
