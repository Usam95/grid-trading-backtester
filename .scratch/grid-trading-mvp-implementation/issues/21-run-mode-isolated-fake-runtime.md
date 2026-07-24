# 21 — Run one mode-isolated adaptive runtime against a fake venue

**What to build:** Establish the online runtime boundary with one isolated store, one bounded ingress sequencer, one authoritative writer, one atomic journal/outbox, and one deterministic fake venue. Process adaptation evidence through a guarded epoch transition into durable command intents and simulated outcomes, then crash and recover into frozen readiness.

**Blocked by:** 05 — Persist and exactly replay one adaptive decision path; 10 — Operate controls and terminal disposal during adaptation; 11 — Admit only venue-valid positive grid-epoch plans; 12 — Transition safely between immutable grid epochs.

**Status:** ready-for-agent

- [ ] Transport callbacks can submit observations but cannot call the domain core or mutate authoritative state directly.
- [ ] Bounded admission measures items, bytes, oldest age, persistence latency, freshness, and disk headroom and exposes explicit backpressure consequences.
- [ ] Input, canonical consequences, projection updates, and command outbox intent commit atomically before dispatch eligibility.
- [ ] Every command has a durable managed identity and a lifecycle independent of venue order state.
- [ ] Runtime lifecycle phases remain distinct from grid lifecycle, safety posture, process liveness, and decision readiness.
- [ ] A crash at each processing/dispatch boundary reconstructs ambiguity, replays exactly, and reaches `FROZEN_READY` without automatic command replay or trading resume.
- [ ] The fake adapter satisfies the same public contract later required of Paper, Testnet, and live adapters.
