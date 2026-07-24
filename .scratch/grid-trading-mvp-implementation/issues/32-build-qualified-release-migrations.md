# 32 — Build a qualified release with forward migrations

**What to build:** Produce one locally qualified, target-compatible, content-identified offline release bundle with exact dependency/tool/schema/configuration identities, security and architecture evidence, forward-only durable migrations, side-by-side frozen installation, and compatibility-driven rollback decisions.

**Blocked by:** 01 — Freeze the reproducible baseline and current normative contract; 30 — Create and restore verified recoverable points; 31 — Contract the superseded engine and Studio paths.

**Status:** ready-for-agent

- [ ] One clean local qualification command runs all applicable formatting, lint, typing, architecture, unit/property/state/replay/contract/fault, coverage, dependency, licence, secret, and vulnerability gates.
- [ ] Critical paths meet their accepted branch threshold and production code its overall threshold without using percentages to excuse missing semantic cases.
- [ ] The manifest binds source, authoritative version, dependency locks, toolchain, schemas, migrations, configuration contracts, tests/results, SBOM/inventory, scans, and final archive hash.
- [ ] Installation resolves no public dependency, builds no source on the target, verifies bytes independently, and installs beside the active/rollback release.
- [ ] Durable changes use expand–migrate–contract with a compatibility matrix, verified pre-change point, immutable migration ledger, rebuild/upcast proof, and no assumed destructive down-migration.
- [ ] A candidate starts frozen and must pass store, schema, replay, invariant, reconciliation, health, resource, and evidence checks before installation acceptance.
- [ ] Abandon-before-switch, compatible binary rollback, point-assisted rollback, and forward-repair outcomes are selected from proven compatibility and never blindly replay commands.
- [ ] Documentation-only or proven read-only changes reuse evidence only through the accepted impact classification.
