# 35 — Run Azure acceptance and B1ms capacity qualification

**What to build:** Create one resumable local acceptance runner with operator checkpoints that verifies the exact infrastructure/release/configuration identity, executes bounded Testnet and recovery actions, injects accepted failures, and runs the representative 24-hour three-process workload to produce an objective capacity decision.

**Blocked by:** 26 — Execute and exactly replay adaptive Production-Data Paper; 27 — Qualify the Binance Testnet adapter and generation; 32 — Build a qualified release with forward migrations; 34 — Connect Azure evidence, secrets and monitoring.

**Status:** ready-for-agent

- [ ] The runner seals exact Bicep, release, configuration, schema, permission, network, storage, secret, monitoring, dataset, and tool identities before mutation.
- [ ] Explicit checkpoints govern provisioning/apply, Testnet plan authorization, candidate-VM restart, destructive test setup, and cleanup.
- [ ] Access/isolation, static outbound identity, venue permissions, Storage/Key Vault boundaries, secret negatives, alerts/dead-man, backup/restore, replay, reconciliation, and frozen recovery are verified end to end.
- [ ] The representative campaign runs Gateway, Production-Data Paper, Testnet, capture, monitoring, backup, compaction/offload, and required faults for 24 hours with no swap/OOM/evidence/correctness failure.
- [ ] Measured memory headroom, CPU credits, ingress/burst throughput, clock evidence, journal/dispatch/health latency, RPO, RTO, disk/storage growth, and monthly-cost forecast meet their accepted thresholds.
- [ ] The exact candidate VM completes one controlled restart and external outage observation, returning reconciled and frozen.
- [ ] Results are exactly `B1MS_ACCEPTED`, `RESIZE_REQUIRED`, or `INCONCLUSIVE_RERUN`; failure never relaxes safety/evidence thresholds and names the prescribed resize/retest path.
- [ ] The sealed report identifies every passed/failed/inconclusive case and the change-impact conditions requiring partial or full reacceptance.
