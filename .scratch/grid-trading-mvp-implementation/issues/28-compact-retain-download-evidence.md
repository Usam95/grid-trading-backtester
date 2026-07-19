# 28 — Compact, retain and download verified evidence

**What to build:** Publish closed captured market evidence as lossless typed Parquet, manage the accepted retention classes and preservation holds, rotate bounded diagnostics, and let Studio build and download checksum-verified evidence bundles for local causal analysis without changing source authority.

**Blocked by:** 22 — Explain runtime health, incidents and alerts; 24 — Capture production market evidence with continuity; 25 — Execute and exactly replay Production-Data Paper; 26 — Qualify the Binance Testnet adapter and generation; 27 — Operate Paper and Testnet through Command Canvas.

**Status:** ready-for-agent

- [ ] Compaction preserves every required type, value, count, identity, sequence, ordering, and manifest dependency and performs reader/checksum verification before raw replacement deletion.
- [ ] Journal/authoritative, promotion, one-year diagnostic, metrics, collected-log, local-buffer, and temporary evidence receive their exact retention classes and clocks.
- [ ] Content-identity references, open runs/incidents/reconciliations, activation/promotion authority, migrations/restores, and authenticated holds prevent premature expiry.
- [ ] Local JSONL, collected diagnostics, metrics, and raw diff-depth obey their accepted bounded retention without becoming canonical authorities.
- [ ] Deletion is planned, idempotent, audited with non-sensitive tombstones, and tracks provider-recoverable versus confirmed-expired state.
- [ ] Evidence bundles include exact content identities, checksums, source authority, schemas, retention/hold status, and causal completeness.
- [ ] Downloads verify before admission to the local cache; offline views identify cached source/time and never rewrite cloud authority.
- [ ] Interrupted upload/compaction/download/deletion and concurrent hold creation have deterministic fault cases.

