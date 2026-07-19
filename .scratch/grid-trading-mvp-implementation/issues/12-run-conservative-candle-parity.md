# 12 — Run conservative candle simulation through the canonical core

**What to build:** Route broad candle research through the same canonical grid, accounting, risk, lifecycle, journal, and intent contracts used by later modes, while making the candle execution assumptions explicitly conservative and replayable.

**Blocked by:** 08 — Complete cumulative partial-fill paired cycles; 10 — Operate Pause, Resume, Stop and terminal disposal; 11 — Admit only venue-valid positive post-only plans.

**Status:** ready-for-agent

- [ ] A normal order cannot fill before the candle after it becomes resting.
- [ ] A buy requires a strict trade below its limit and a sell a strict trade above; equality is retained as a touch without a primary fill.
- [ ] Ambiguous intrabar ordering follows the declared adverse path and does not infer favorable gap improvement.
- [ ] Eligible volume is bounded, non-reusable across obligations, and source-supported partial fills are possible.
- [ ] Bootstrap, ordinary-cycle, post-only rejection, fee, spread/slippage, global-stop, and terminal-disposal costs use the canonical paths.
- [ ] The same canonical fixture yields identical decisions, postings, postures, and fingerprints in candle and event-shaped harnesses where inputs are equivalent.
- [ ] Studio labels candle fill limitations and never presents candle results as venue execution proof.
