# 34 — Connect Azure evidence, secrets and monitoring

**What to build:** Attach the accepted private-purpose ZRS Blob, Key Vault/managed-identity, off-VM recovery, monitoring, alerting, storage-growth, provider-recovery, and cost boundaries to the provisioned node while keeping Gateway, Paper, Testnet, and future live authority isolated.

**Blocked by:** 23 — Explain runtime health, incidents and alerts; 29 — Compact, retain and download verified evidence; 30 — Create and restore verified recoverable points; 33 — Provision the secure minimal Azure node.

**Status:** ready-for-agent

- [ ] Blob and Key Vault data planes default-deny other networks and admit only the declared subnet/service-endpoint and exact RBAC identities.
- [ ] New evidence publishes Hot ZRS into private purpose boundaries with versioning, 30-day soft deletion, container protection, resource delete lock, and rule-governed Cool transition.
- [ ] Paper and Gateway cannot retrieve a Binance secret; the credentialed Testnet runtime resolves only its exact secret/version once at frozen startup and records only non-secret identity/fingerprint.
- [ ] Testnet and future live permissions are mutually exclusive and denial of every undeclared environment secret is executable evidence.
- [ ] Recoverable points, promotion evidence, active/fallback releases, incidents, holds, and retention/catalogue identities offload and restore with exact checksums.
- [ ] Application measurements and Azure monitoring expose health, protection, growth, resource use, dead-man, objective, and cost evidence without secret leakage or high-cardinality explosion.
- [ ] Growth warnings/review thresholds and EUR 35/EUR 50 cost actions are tested and cannot delete evidence or alter trading authority.
- [ ] Azure identity/storage compromise concentration, operator-source-IP change, and deferred-maintenance risks remain explicit in the acceptance report and runbooks.
