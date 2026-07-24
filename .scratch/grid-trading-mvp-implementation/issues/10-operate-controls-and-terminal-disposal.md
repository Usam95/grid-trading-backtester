# 10 — Operate controls and terminal disposal during adaptation

**What to build:** Implement the canonical operator and terminal lifecycle through the domain, API, evidence, and Studio surface while an epoch is active or transitioning. Pause reduces exposure, Resume is evidence-gated, Operator Stop handles retained/disposed inventory deliberately, and emergency/global-stop paths latch and dispose only authoritative reconciled inventory.

**Blocked by:** 09 — Enforce adaptive, capital, loss, freshness and venue-anomaly postures.

**Status:** ready-for-agent

- [ ] Pause cancels and blocks exposure-increasing buys while retaining valid backed inventory-reducing sells.
- [ ] Pause, Stop, Emergency Stop, and terminal loss preempt a pending epoch activation without reordering admitted facts or permitting new-epoch placement.
- [ ] Resume is refused until current evidence, reconciliation, invariants, plan validity, and authority all pass.
- [ ] Operator Stop cancels managed obligations, admits late fills, reconciles, and records an explicit retained-holding or disposal disposition.
- [ ] Emergency Stop is immediately available, idempotent, environment-bound, and distinct from automatic liquidation.
- [ ] Either global stop trigger latches irreversibly; uncertainty retains `FROZEN` precedence until disposal quantity is authoritative.
- [ ] Terminal IOC children obey quantity, notional, fresh-depth, price-band, attempt, and elapsed-time bounds and reconcile between waves.
- [ ] Gap-through, partial disposal, rejection, unknown outcome, attempt exhaustion, and residual holdings have golden replay cases.
- [ ] Every operator preview and Studio projection identifies the active/proposed epoch, transition state, posture, and authoritative inventory basis.
