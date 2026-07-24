# 26 — Execute and exactly replay adaptive Production-Data Paper

**What to build:** Run the canonical regime-aware adaptive grid over live Binance production public market evidence while simulating epoch transitions, orders, fills, fees, balances, and account feedback locally. Paper must retain conservative queue/liquidity state and reproduce every classification, gate, transition, decision, and simulated outcome exactly without any production private credential or venue order authority.

**Blocked by:** 13 — Run conservative adaptive candle simulation through the canonical core; 19 — Replay `1s` and individual-trade evidence; 24 — Reconcile ambiguity and restart frozen; 25 — Capture production market evidence with continuity.

**Status:** ready-for-agent

- [ ] Paper has no Binance private/trading credential and cannot transmit any production order.
- [ ] Simulated acknowledgements, order states, partial/full fills, cancellations, fees, balances, and reconciliation use venue-shaped canonical contracts in an isolated Paper store.
- [ ] Resting eligibility, displayed queue ahead, strict trade-through, non-reusable liquidity, and the accepted participation cap drive fills from admitted production evidence only.
- [ ] Every fill or refusal links to the exact trade/BBO/depth/timer evidence and execution-model state that caused it.
- [ ] Duplicate/late market facts, simulated stream gaps, ambiguous simulated commands, cancel/fill races, and rate-limit/backoff fixtures preserve invariants and fail closed.
- [ ] Shared fixtures exercise all five grid adaptation states, guarded transition and refusal paths, late fills during cancellation, and confirmed-downtrend recovery without downward shifting or new buys.
- [ ] Restart restores the simulator, queue/liquidity budget, obligations, journal, and ledger exactly and ends frozen when required.
- [ ] Recorded market and Paper evidence replays to identical decisions, fills, postings, postures, and final projections.
- [ ] Studio labels Paper orders, balances, returns, activity, and incidents as locally simulated over production data.
