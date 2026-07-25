# 13 — Run conservative adaptive candle simulation through the canonical core

**What to build:** Route broad candle research through the same canonical adaptation, grid-plan-epoch, guarded-transition, accounting, risk, lifecycle, journal, and intent contracts used by later modes, while making candle execution and closed-observation assumptions explicitly conservative and replayable.

**Blocked by:** 08 — Complete cumulative partial-fill cycles across epochs; 10 — Operate controls and terminal disposal during adaptation; 11 — Admit only venue-valid positive grid-epoch plans; 12 — Transition safely between immutable grid epochs.

**Status:** resolved

- [x] A normal order cannot fill before the candle after it becomes resting.
- [x] Adaptation uses only completed candles strictly available at the decision boundary; warm-up, confirmation, residence, cooldown, and expiry cannot look ahead.
- [x] A buy requires a strict trade below its limit and a sell a strict trade above; equality is retained as a touch without a primary fill.
- [x] Ambiguous intrabar ordering follows the declared adverse path and does not infer favorable gap improvement.
- [x] Eligible volume is bounded, non-reusable across obligations, and source-supported partial fills are possible.
- [x] Bootstrap, ordinary-cycle, post-only rejection, fee, spread/slippage, global-stop, and terminal-disposal costs use the canonical paths.
- [x] The same canonical fixture yields identical decisions, postings, postures, and fingerprints in candle and event-shaped harnesses where inputs are equivalent.
- [x] All five adaptation states, guarded transition/refusal paths, and downtrend no-chase behavior have deterministic golden candle replays.
- [x] Studio labels candle fill limitations and never presents candle results as venue execution proof.

## Answer

Implemented a conservative candle-simulation seam and parity fixtures in the canonical layer, added deterministic candle/event replay coverage, and updated the Studio contract/UI/browser flow to label candle-fill limits and reject any implication of venue execution proof. Focused regressions, frontend contract/type/unit/build/browser checks, and the full pytest baseline passed. Later tickets were not started.
