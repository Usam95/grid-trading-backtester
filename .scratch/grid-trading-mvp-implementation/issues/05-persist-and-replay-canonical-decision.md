# 05 — Persist and exactly replay one adaptive decision path

**What to build:** Persist one admitted closed market observation and its exact adaptation classification, transition request or explanatory no-action, posture effect, and all other canonical consequences as one decision-complete schema-versioned transaction. Rebuild the projection and prove exact replay equality.

**Blocked by:** 04 — Expand the canonical exact adaptive-policy and event seam.

**Status:** ready-for-agent

- [ ] Admission assigns one durable processing position after validation and deduplication.
- [ ] The admitted input, resulting decision batch, projection effects, invariant outcome, and explanatory refusal or non-action commit atomically.
- [ ] Classification evidence, prior adaptation state, confirmation/hysteresis/residence/cooldown gates, requested epoch cause, and posture effect are decision-complete.
- [ ] A crash injected at every transaction boundary leaves either the complete transaction or no admitted progress.
- [ ] Rebuilding from the journal produces the same domain state, decisions, and fingerprint as original processing.
- [ ] Golden replay covers one accepted classification, one threshold no-action, one stale-evidence `UNCERTAIN` decision, and one confirmed-downtrend `REDUCE_ONLY` decision with no buy or downward-shift intent.
- [ ] Duplicate and late inputs preserve their evidence and cannot create duplicate consequences.
- [ ] Schema identity and a tested compatible-reader/upcast seam exist from the first persisted record.
