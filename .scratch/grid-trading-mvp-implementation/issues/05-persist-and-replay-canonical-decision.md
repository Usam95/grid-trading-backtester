# 05 — Persist and exactly replay one canonical decision path

**What to build:** Persist one admitted market observation and all of its canonical consequences as one decision-complete, schema-versioned transaction, rebuild its projection, and prove exact replay equality. This establishes the evidence spine that later grid, accounting, risk, Paper, and venue slices extend.

**Blocked by:** 04 — Expand the canonical exact event and configuration seam.

**Status:** ready-for-agent

- [ ] Admission assigns one durable processing position after validation and deduplication.
- [ ] The admitted input, resulting decision batch, projection effects, invariant outcome, and explanatory refusal or non-action commit atomically.
- [ ] A crash injected at every transaction boundary leaves either the complete transaction or no admitted progress.
- [ ] Rebuilding from the journal produces the same domain state, decisions, and fingerprint as original processing.
- [ ] Duplicate and late inputs preserve their evidence and cannot create duplicate consequences.
- [ ] Schema identity and a tested compatible-reader/upcast seam exist from the first persisted record.

