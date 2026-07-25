# 19 — Replay `1s` and individual-trade evidence

**What to build:** Add manifested high-fidelity ingestion and deterministic replay for native one-second candles and official individual trades, using conservative no-depth execution when historical queue evidence is absent. Compare this path with minute simulation on development evidence before the final candidate is frozen.

**Blocked by:** 03 — Prove the manifested production-data tracer bullet; 05 — Persist and exactly replay one adaptive decision path; 13 — Run conservative adaptive candle simulation through the canonical core; 14 — Build the synchronized ten-symbol EUR production archive.

**Status:** ready-for-agent

- [ ] Coverage probing records the actual per-symbol `1s`/trade availability and never invents pre-introduction history or fills a missing archive silently.
- [ ] Individual trade IDs, event times, price, quantities, quote quantities, and maker-side evidence normalize source-exactly with deterministic ordering.
- [ ] An order must already be acknowledged resting and a later trade must pass strictly through its limit; at-price trades do not fill without queue proof.
- [ ] Eligible trade volume is non-reusable and bounded by the accepted participation rule; partial fills remain canonical cumulative fills.
- [ ] One-second candles cross-check price/volume coverage but do not manufacture intrasecond order or queue information.
- [ ] Closed-observation boundaries and epoch-transition ordering are explicit, and higher-frequency evidence cannot retroactively alter an earlier adaptation decision.
- [ ] Optional `30s` views are derived, parent-identified diagnostics only; no native `30s` download or promotion authority exists.
- [ ] Development parity reports explain return, drawdown, fill, cycle, inventory, cost, and decision differences without exposing the locked holdout.
