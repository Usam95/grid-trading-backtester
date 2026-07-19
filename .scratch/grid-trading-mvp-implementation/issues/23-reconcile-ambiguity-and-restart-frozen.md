# 23 — Reconcile ambiguity and restart frozen

**What to build:** Implement fact-specific authoritative reconciliation and ambiguity-safe recovery across commands, orders, fills, fees, balances, allocation, venue rules, and foreign activity. Planned shutdown and crash recovery must preserve evidence, cancel safely, admit late facts, and end frozen for explicit operator authority.

**Blocked by:** 07 — Account for one grid allocation in exact native assets; 10 — Operate Pause, Resume, Stop and terminal disposal; 20 — Run one mode-isolated runtime against a fake venue; 21 — Admit authenticated idempotent operator commands; 22 — Explain runtime health, incidents and alerts.

**Status:** ready-for-agent

- [ ] Submit/cancel timeout or uncertain transmission becomes `UNKNOWN`, blocks replacement, and resolves only by original managed identity and authoritative evidence.
- [ ] Reconciliation retains expected and observed facts, source, event/observation time, processing boundary, difference, state, materiality, deadline, and resolution.
- [ ] Missing authoritative fills/fees can be admitted idempotently with original identity/time; prior facts and postings are never edited.
- [ ] Automatic repair is deterministic, evidence-backed, non-exposure-increasing, and history-preserving; material allocation/economic adjustments require explicit operator approval.
- [ ] Startup and periodic reconciliation cover effective/unknown orders, recent/terminal history, trades, commissions, balances, allocation, permissions, limits, and foreign activity.
- [ ] Planned shutdown and forced termination continue admission/cancellation/reconciliation within accepted bounds and never report an incomplete stop as clean.
- [ ] Replacement starts frozen, replays, reconstructs ambiguity, reconciles, cancels survivors safely, and awaits an authenticated operator choice.
- [ ] Studio exposes the complete reconciliation case rather than only a green/red summary.

