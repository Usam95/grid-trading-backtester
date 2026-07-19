# 22 — Explain runtime health, incidents and alerts

**What to build:** Make every material runtime decision, refusal, fault, and recovery explainable through secret-safe structured diagnostics, bounded metrics, causal spans, separate health dimensions, durable root-condition incidents, Studio timelines, and external notification/dead-man paths.

**Blocked by:** 20 — Run one mode-isolated runtime against a fake venue; 21 — Admit authenticated idempotent operator commands.

**Status:** ready-for-agent

- [ ] Structured records carry stable mode, run, configuration, release, event, command, order, cycle, reconciliation, and incident identities where applicable.
- [ ] Approved-field serialization plus recursive redaction/canaries prevent credentials, signatures, tokens, signed requests, sensitive headers, and secret fragments from reaching any sink.
- [ ] Liveness, service readiness, decision readiness, evidence freshness, safety posture, reconciliation, protection, storage, and external-alert health remain separate.
- [ ] Clock/skew metrics use representative observations rather than event-loop delay and exercise the accepted freeze boundary without weakening immediate timestamp-rejection handling.
- [ ] Repeated occurrences update one deterministic root-condition incident with lifecycle, severity, counts, acknowledgements, recovery, and review.
- [ ] Critical and warning notification destinations, retry, deduplication, repeat, escalation, and external dead-man behavior are tested without changing canonical posture from delivery success.
- [ ] Local diagnostic rotation, metric cardinality, and resource bounds match the accepted retention profile.

