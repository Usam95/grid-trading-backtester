# 32 — Provision the secure minimal Azure node

**What to build:** Define and provision the minimal single-node Azure compute/network/service boundary through reviewed Bicep and local wrappers: B1ms-first Linux, E6 state disk, static outbound identity, source-restricted SSH tunnel, loopback services, separate least-privilege service users, bounded supervision, and frozen startup.

**Blocked by:** 31 — Build a qualified release with forward migrations.

**Status:** ready-for-agent

- [ ] A non-mutating preview identifies the exact Germany West Central resources, configuration, identities, costs, and unresolved provider results before apply.
- [ ] The node starts as the accepted B1ms/no-swap profile with E6 LRS state, static Standard IPv4, measured host headroom, and an explicit resize path rather than weakened requirements.
- [ ] NSG rules admit SSH only from the declared operator source and expose no application, database, health, metrics, or runtime port publicly.
- [ ] Studio reaches the loopback/private gateway only through the dedicated project SSH key and tunnel.
- [ ] Gateway, Paper, and Testnet services run under distinct users with explicit writable paths, locks, CPU/memory/process/file/restart/shutdown, and network/credential boundaries.
- [ ] The qualified bundle uploads through SSH, verifies, installs side by side, and every service starts frozen without a VM reboot or automatic trading resume.
- [ ] The VM has no GitHub credential, public dependency/build workflow, historical-research job, or undeclared administrative service.
- [ ] The deferred-maintenance security exception is visible and cannot be represented as a maintained or fully patched host.

