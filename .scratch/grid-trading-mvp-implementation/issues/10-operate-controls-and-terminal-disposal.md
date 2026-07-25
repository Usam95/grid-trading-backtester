# 10 — Operate controls and terminal disposal during adaptation

**What to build:** Implement the canonical operator and terminal lifecycle through the domain, API, evidence, and Studio surface while an epoch is active or transitioning. Pause reduces exposure, Resume is evidence-gated, Operator Stop handles retained/disposed inventory deliberately, and emergency/global-stop paths latch and dispose only authoritative reconciled inventory.

**Blocked by:** 09 — Enforce adaptive, capital, loss, freshness and venue-anomaly postures.

**Status:** resolved

- [x] Pause cancels and blocks exposure-increasing buys while retaining valid backed inventory-reducing sells.
- [x] Pause, Stop, Emergency Stop, and terminal loss preempt a pending epoch activation without reordering admitted facts or permitting new-epoch placement.
- [x] Resume is refused until current evidence, reconciliation, invariants, plan validity, and authority all pass.
- [x] Operator Stop cancels managed obligations, admits late fills, reconciles, and records an explicit retained-holding or disposal disposition.
- [x] Emergency Stop is immediately available, idempotent, environment-bound, and distinct from automatic liquidation.
- [x] Either global stop trigger latches irreversibly; uncertainty retains `FROZEN` precedence until disposal quantity is authoritative.
- [x] Terminal IOC children obey quantity, notional, fresh-depth, price-band, attempt, and elapsed-time bounds and reconcile between waves.
- [x] Gap-through, partial disposal, rejection, unknown outcome, attempt exhaustion, and residual holdings have golden replay cases.
- [x] Every operator preview and Studio projection identifies the active/proposed epoch, transition state, posture, and authoritative inventory basis.

## Answer

Implemented the deterministic canonical operator-control and terminal-disposal slice with bounded pause/resume/stop/emergency previews, authoritative inventory-basis projection, golden terminal replay coverage, typed FastAPI/Studio contracts, and read-only Operations UI evidence. Focused backend/frontend/browser checks and the full baseline passed; the delivery report is at `../artifacts/ticket-10/report.md`. Ticket 11 and later behavior was not started.
