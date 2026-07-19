# 26 — Qualify the Binance Testnet adapter and generation

**What to build:** Implement the current Binance Spot Testnet REST, public-stream, private/account-stream, signing, rate-limit, and reconciliation adapter behind the canonical venue port. Exercise bounded real Testnet commands with virtual assets and retain a generation identity that safely detects and isolates resets.

**Blocked by:** 11 — Admit only venue-valid positive post-only plans; 20 — Run one mode-isolated runtime against a fake venue; 21 — Admit authenticated idempotent operator commands; 22 — Explain runtime health, incidents and alerts; 23 — Reconcile ambiguity and restart frozen.

**Status:** ready-for-agent

- [ ] The adapter discovers current Testnet symbols, filters, permissions, limits, time, and endpoints rather than copying production or documentation examples.
- [ ] Signing, timestamps, receive windows, managed client identities, `LIMIT_MAKER`, approved aggressive orders, query, cancel, and account/trade reads map to canonical evidence without float conversion.
- [ ] Submission/cancellation ambiguity, would-take rejection, rate limits, bans, transport failures, clock rejection, and stream gaps follow the accepted fail-closed recovery contracts.
- [ ] Private execution/account events deduplicate by authoritative identity and actual commission quantity/asset.
- [ ] A bounded preview plus fresh operator confirmation authorizes one immutable Testnet plan; live credentials and endpoints are absent and denied.
- [ ] Testnet reset establishes a new generation, archives prior local evidence, prevents state splicing, and leaves Production-Data Paper unaffected.
- [ ] The accepted integration scenario families are executable with deterministic fixtures where Testnet cannot naturally produce a safe partial/failure case.
- [ ] Testnet P&L is retained but cannot satisfy production economic gates.

