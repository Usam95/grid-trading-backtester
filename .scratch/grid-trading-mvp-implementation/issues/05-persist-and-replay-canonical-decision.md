# 05 — Persist and exactly replay one adaptive decision path

**What to build:** Persist one admitted closed market observation and its exact adaptation classification, transition request or explanatory no-action, posture effect, and all other canonical consequences as one decision-complete schema-versioned transaction. Rebuild the projection and prove exact replay equality.

**Blocked by:** 04 — Expand the canonical exact adaptive-policy and event seam.

**Status:** resolved

- [x] Admission assigns one durable processing position after validation and deduplication.
- [x] The admitted input, resulting decision batch, projection effects, invariant outcome, and explanatory refusal or non-action commit atomically.
- [x] Classification evidence, prior adaptation state, confirmation/hysteresis/residence/cooldown gates, requested epoch cause, and posture effect are decision-complete.
- [x] A crash injected at every transaction boundary leaves either the complete transaction or no admitted progress.
- [x] Rebuilding from the journal produces the same domain state, decisions, and fingerprint as original processing.
- [x] Golden replay covers one accepted classification, one threshold no-action, one stale-evidence `UNCERTAIN` decision, and one confirmed-downtrend `REDUCE_ONLY` decision with no buy or downward-shift intent.
- [x] Duplicate and late inputs preserve their evidence and cannot create duplicate consequences.
- [x] Schema identity and a tested compatible-reader/upcast seam exist from the first persisted record.

## Answer

Implemented a schema-versioned SQLite decision journal around the canonical adaptive-policy seam. Validated Ticket 04 observations now admit through one deterministic writer transaction that persists the complete input, decision/gate evidence, posture effect, invariant, explanation, projection effect, and cumulative full-event replay fingerprint. Duplicate, late, and conflicting deliveries retain exact evidence without consequences; projection rebuilding is writer-atomic and rejects any replay divergence.

Focused golden/fault/upcast tests, architecture and quality contracts, and the complete Ticket-constrained backend/engine baseline passed. The concise delivery report is at `../artifacts/ticket-05/report.md`. Ticket 06 and later behavior was not started.
