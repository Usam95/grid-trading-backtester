# Verification, release, and migration specification

Status: accepted  
Applies to: `gridlab`, `gridlab-studio`, the online runtimes, and the first MVP release path

## Purpose

This specification defines how a change becomes trustworthy evidence, an immutable release candidate, an installed Azure release, and eventually an eligible Paper, Testnet, or live trading version. Every required gate must trace to an accepted invariant, failure scenario, promotion rule, architecture boundary, security control, evidence guarantee, or B1ms resource budget.

The process is local-first and single-operator. It does not require hosted CI, a generic release platform, or running every expensive operational qualification after every edit.

## Inherited foundation

- `gridlab` and `gridlab-studio` remain the canonical codebase foundation.
- Useful legacy behavior, tests, migration examples, and UI patterns are selectively reimplemented or ported into canonical contracts; legacy projects do not become parallel authorities.
- One local resumable acceptance runner produces machine-readable evidence and explicit operator checkpoints.
- Locally qualified immutable release bundles are delivered to Azure through SSH and identified by a cryptographic digest.
- Paper, Testnet, and later live promotion evidence remains governed by the already accepted validation, runtime, Azure, observability, and security specifications.

## Decision 1: three risk-based verification levels

Verification is divided into three evidence levels. The levels share stable source, build, schema, configuration, dataset, test-plan, and result identities, but one level cannot claim evidence that only another environment can produce.

### Level A — local change feedback

Normal development runs the affected unit, property, state-machine, contract, formatting, linting, typing, architecture-fitness, secret, and unsafe-pattern checks. The change declares its affected contracts and evidence domains so the runner can select relevant checks. Level A is optimized for fast feedback and normally completes in minutes on the operator laptop.

### Level B — immutable release-candidate qualification

Before a deployable bundle is sealed, the exact candidate runs the complete Level A suite plus integration, deterministic replay, accounting/reconciliation invariants, cross-mode decision fingerprints, migration and compatibility tests, required fault injection, security and dependency gates, build-provenance checks, bundle-integrity checks, and bounded resource smoke tests.

Level B evidence belongs to the exact source tree, locked dependencies, toolchain, durable-schema set, configuration contracts, test plan, and built bytes. Rebuilding or changing any identified input creates a different candidate and invalidates the candidate-level result.

### Level C — operational promotion evidence

Checks requiring the real target environment run against the exact Level B candidate. They include Azure installation and restart, frozen recovery and reconciliation, backup restoration and disaster exercises, B1ms CPU/memory/storage/deadline measurement, qualifying production-data Paper operation, Binance Testnet integration, and later capped live probation.

Level C results are cumulative evidence with explicit validity scope; they are not a single test command and cannot be substituted by local simulation.

### Evidence reuse and change impact

Existing operational evidence may remain valid only when a machine-recorded and operator-reviewed impact analysis proves that the changed source, dependencies, schemas, configuration, infrastructure, or behavior is outside that evidence's declared scope. A documentation-only change therefore does not restart a 30-day Paper run. A change to trading decisions, accounting, risk, execution, runtime recovery, market interpretation, venue integration, relevant dependencies, durable schemas, or qualifying configuration invalidates the affected evidence and triggers the conservative requalification rules already accepted by the validation and Azure specifications.

The runner must fail closed when impact is unknown. It must show which evidence remains valid, which evidence is invalidated, why, and which gates are now required.

### Consequences

- Fast checks remain practical during development.
- A release candidate receives comprehensive deterministic qualification before deployment.
- Long-running and environment-specific evidence is rerun only when its validity is materially affected.
- Ad hoc commands cannot silently replace required gates.
- Passing Level A or Level B does not imply that a candidate has qualified operationally.

### Declined alternatives

- **Run every test and 30-day qualification after every change:** declined because it makes safe incremental development impractical and creates incentives to bypass testing.
- **Use only developer-selected ad hoc commands:** declined because required gates and their exact inputs could be omitted or become untraceable.
- **Treat all prior evidence as invalid after any edit:** declined because it restarts unaffected long-running evidence without improving safety.
- **Automatically preserve evidence based only on changed filenames:** declined because semantic, dependency, schema, configuration, and infrastructure effects can cross file boundaries.

## Decision 2: evolve the canonical projects through tested slices

The MVP evolves the existing `gridlab` and `gridlab-studio` projects rather than replacing them with a greenfield backtester and UI. The names identify the canonical product foundation, not a requirement to preserve every current internal design.

### Responsibility target

| Component | Canonical responsibility |
| --- | --- |
| `gridlab` | Venue-independent domain types, static-grid semantics, accounting, risk decisions, deterministic simulation/replay, research evaluation, and the ports needed by outside adapters. |
| `gridlab-studio` backend | Research-job orchestration, configuration and evidence APIs, report/download services, and typed operator-control requests; it does not own trading rules. |
| `gridlab-studio` frontend | Research configuration, results and trade visualization, qualification monitoring, operator workflows, causal evidence, learning, and glossary surfaces. |
| Online-runtime modules | Paper, Testnet, and later live orchestration, lifecycle, ingress sequencing, command dispatch, recovery, reconciliation, and supervision around the canonical core. |
| Adapter modules | Binance, persistence, filesystem/Blob, Key Vault, notification, clock, and other external boundaries implementing canonical ports. |

Missing capabilities may require new packages or modules inside the canonical repository and dependency graph. They must not create a second strategy, accounting, risk, lifecycle, or reconciliation authority. Exact physical package boundaries are fixed during implementation planning from the accepted context and dependency rules; a new module is not treated as a new competing product.

### Evolution protocol

1. Capture current useful behavior with deterministic characterization tests before materially restructuring it.
2. Define the accepted owning contract and dependency direction for one bounded slice.
3. Implement or adapt that slice behind the contract while keeping the existing test baseline green.
4. Port useful legacy scenarios into canonical fixtures and strengthen them with the new invariants.
5. Compare observable outputs and explicitly approve any intended semantic change; unexplained differences fail the migration.
6. Redirect the canonical caller to the replacement.
7. Remove superseded code only after parity, regression, replay, and migration evidence prove that it is no longer authoritative.

The same approach applies to the accepted incremental Studio modernization: retain the existing product workflow and FastAPI boundary where appropriate while progressively replacing the frontend with typed React/TypeScript/Vite slices. No second permanent UI is developed in parallel.

### Immediate cleanup requirements

- Establish one authoritative product/release version; resolve the observed `1.0.0` versus `1.1.0` conflict.
- Replace broad, editable release dependencies with the locked release model defined later in this specification.
- Move or replace business rules found outside their owning domain modules.
- Add the missing durable journal, migrations, runtime, adapter, recovery, and verification capabilities behind the accepted boundaries.
- Keep legacy repositories read-only as requirements and scenario sources until their useful material is dispositioned; never make them runtime dependencies.

### Consequences

- The current 94 passing canonical tests remain a starting regression asset.
- Existing code is not presumed correct merely because it exists or has tests; accepted specifications take precedence.
- New architecture is introduced incrementally, making behavioral differences reviewable and rollback smaller.
- There is one canonical implementation path rather than an old system, a rewrite, and an MVP accumulating incompatible behavior.

### Declined alternatives

- **Rewrite both projects from scratch:** declined because it discards working behavior and tests while creating a large, hard-to-explain semantic migration.
- **Keep the current internals and bolt on every missing feature:** declined because current gaps and misplaced responsibilities would become permanent coupling.
- **Create a second permanent Studio and switch later:** declined because two UIs and APIs would drift and duplicate workflow validation.
- **Reuse legacy services as runtime dependencies:** declined because they have different assumptions and are not authorities for the accepted domain contracts.

## Decision 3: owner-local tests with shared conformance scenarios

Each behavior is tested primarily in the module that owns its rule. Cross-boundary and cross-mode guarantees reuse versioned executable scenario packs rather than copying the rule or maintaining separate expected behavior for backtest, replay, Paper, Testnet, and later live modes.

### Test ownership

| Behavior or evidence | Primary owner | Required proof |
| --- | --- | --- |
| Static-grid semantics and strategy decisions | `gridlab` domain/strategy | Unit, example, property, and deterministic state-machine tests. |
| Accounting, allocation, fees, inventory, and reconciliation invariants | `gridlab` accounting/reconciliation | Exact-arithmetic examples, property tests, lifecycle scenarios, and fail-closed invariant tests. |
| Risk and trading posture | `gridlab` risk/lifecycle | State-machine tests covering every permitted transition, refusal, limit, pause, stop, degraded state, and recovery precondition. |
| Simulation, fill policy, and replay | `gridlab` simulation/replay | Deterministic fixtures, conservative fill cases, golden replay fingerprints, and dataset/configuration identity tests. |
| External port behavior | Each adapter | The shared contract suite for its port plus adapter-specific error, translation, capability, and recovery cases. |
| Ingress, command dispatch, recovery, and supervision | Online-runtime modules | Integration and fault-injection tests using controlled venue, clock, persistence, stream, and process boundaries. |
| Research and operator workflows | `gridlab-studio` backend/frontend | API contracts, component/workflow tests, and a small set of consequence-focused end-to-end cases. |
| Durable formats, migrations, rebuild, and restore | Persistence/evidence modules | Compatibility, migration, snapshot-tail replay, corruption/refusal, backup, and isolated restore tests. |
| Azure deadlines and resource budgets | Deployment acceptance suite | Measurements on the actual candidate B1ms VM plus declared load, capture, backup, compaction, restart, and degradation scenarios. |
| Release completeness | Root acceptance runner | Orchestration and evidence sealing only; it invokes owning suites and must not duplicate their business expectations. |

### Shared conformance scenario packs

A conformance scenario contains versioned normalized inputs, controlled clocks and random seeds, declared venue capabilities, expected canonical fingerprints, and the invariant or requirement it proves. Only material cross-mode or cross-boundary scenarios become shared packs; ordinary local behavior stays in ordinary owner-local tests.

The minimum shared packs cover:

- activation, real acquisition, initial sell backing, rung placement, and range exhaustion;
- partial and cumulative fills, paired orders, native fee assets, rounding, rejected orders, and late fills;
- duplicate and out-of-order observations, WebSocket gaps, ambiguous command outcomes, reconciliation, pause/stop, crash, frozen restart, and resume;
- accounting identity, allocation isolation, risk transitions, event-journal completeness, snapshot-tail recovery, and evidence export;
- any later fixed defect whose consequence crosses more than one execution mode or authority boundary.

One illustrative scenario may cross a buy rung, partially fill with base-asset commission, cancel the remainder, generate the paired sell, crash before dispatch, receive a late fill, restart frozen, reconcile, and then resume. Lower-level owning tests isolate each rule; the shared scenario proves that their composition has one outcome.

### Parity oracle

When identical normalized market and canonical events are admitted under the same code, strategy configuration, venue-capability profile, costs, initial allocation, clocks, and seeds, simulation, replay, Paper, and live-decision harnesses must produce identical canonical fingerprints for:

- admitted event order and causal relationships;
- strategy and risk decisions;
- order intents before adapter translation;
- lifecycle, execution, reconciliation, and incident transitions;
- accounting postings, final balances, inventory, realized results, and current equity.

Environment facts that cannot legitimately be equal—venue order IDs, network timing, server timestamps, connection IDs, and actual Testnet matching behavior—remain attributable evidence but are excluded from deterministic equality by an explicit schema, never by ad hoc field deletion. Any unexpected difference is a failing replay-diff requiring classification and operator approval if the behavior change is intentional.

### Testnet boundary

Binance Testnet proves adapter protocol behavior, authentication, request construction, response parsing, order-state handling, reconciliation, and virtual-account integration. Testnet market movement and fills are not a parity or profitability oracle. Decision parity is proven by the controlled event harness; production-behavior qualification is proven by the production-data Paper run.

### Isolation and regression rules

- Level A and normal Level B suites are hermetic: no live network, real wall clock, uncontrolled randomness, Azure resource, or mutable Binance dependency.
- Sanitized Binance payloads and failures are stored as versioned fixtures with source-contract provenance.
- Explicit Testnet and Azure checks are Level C and cannot run accidentally from the ordinary unit-test command.
- Every production defect adds the smallest test at the owning layer and, when it crossed a mode or authority boundary, a shared regression scenario.
- Flaky tests are release failures. A test may be quarantined only with a recorded issue, owner, risk, expiry, and proof that no required release claim depends on it; safety, accounting, migration, recovery, security, and parity gates cannot be quarantined.

### Consequences

- Failures are diagnosed near the rule that owns them.
- The system has one expected strategy/accounting/risk behavior across modes.
- Large end-to-end suites remain bounded to workflows that genuinely require composition.
- Adding a later adapter or strategy means passing declared contracts and scenarios, not cloning the entire suite.

### Declined alternatives

- **Separate expected-behavior suites for every mode:** declined because expectations can drift and conceal duplicate domain implementations.
- **Primarily end-to-end testing:** declined because it is slow, hard to diagnose, and weak at covering exact state and failure branches.
- **Treat Testnet fills as the parity oracle:** declined because Testnet is a separate virtual environment and does not reproduce production matching behavior.
- **Create a generic scenario framework for every test:** declined as unnecessary abstraction; shared packs are reserved for material contracts and mode parity.

## Decision 4: strict critical-path quality with a legacy ratchet

New code and all safety-, money-, evidence-, migration-, and authority-critical paths meet the complete quality policy immediately. Existing noncritical code begins from a measured baseline that may only improve. This preserves incremental delivery without granting legacy code a permanent exemption from the qualification standard.

### Mandatory static and test checks

The locked Level A toolchain provides:

- deterministic Python formatting and linting;
- strict static typing for public contracts and qualifying production paths;
- unit, property, contract, state-machine, integration, and required workflow tests through the owning suites;
- statement and branch coverage reporting with package classifications;
- import-boundary, forbidden-dependency, dependency-cycle, and mutable-global-state fitness tests;
- secret, unsafe-pattern, and dependency/security scans;
- deterministic TypeScript formatting/linting, `tsc --noEmit`, and component/API/workflow tests as the typed Studio frontend is introduced.

Exact tool versions are part of the locked release toolchain. A tool replacement is a deliberate build-policy change with before/after results, not an invisible local preference.

### No-exemption critical scope

The complete policy applies from the first implementation to:

- price, quantity, fee, inventory, valuation, and all other authoritative asset arithmetic;
- accounting, allocation, sizing, strategy decisions, order intents, risk, lifecycle, reconciliation, and execution state;
- journal admission/transactions, commands/outbox, migrations, snapshots, rebuild, restore, and evidence manifests;
- Binance and other authority-boundary translations;
- authentication, operator-command authorization, secret handling, redaction, and incident control;
- all new public contracts, versioned durable types, and code used by a qualifying Paper, Testnet, or later live run.

### Coverage floors and stronger semantic rule

- Accounting, risk, lifecycle, reconciliation, migration, and recovery packages require at least **90% branch coverage**.
- Production code as a whole requires at least **80% branch coverage**.
- The measured critical-package and overall baselines must not decrease.
- Every accepted invariant, safety transition, command refusal, ambiguity response, migration failure, and recovery outcome requires an explicit executable case even when the numerical floor is already satisfied.
- Changed critical behavior covers successful, refused, boundary, and failure outcomes appropriate to the change.
- Generated files, type declarations, and declarative packaging glue may be excluded only through a reviewed path-specific rationale in the coverage configuration.

Coverage is therefore a gap detector, not a claim that exercised lines are correct. A candidate that meets the percentage but lacks a required semantic case still fails.

### Architecture fitness failures

A release fails on any of the following:

- domain code imports UI/web frameworks, exchange SDKs, database drivers, Azure APIs, filesystem adapters, or other infrastructure implementations;
- a forbidden context dependency or dependency cycle exists;
- process-global mutable trading state exists;
- a venue command bypasses the one authorization, risk, durable-identity, and dispatch boundary;
- strategy, sizing, accounting, fill, lifecycle, risk, or reconciliation rules have competing authorities;
- binary floating point is used for authoritative asset accounting;
- a durable event, command, configuration, snapshot, manifest, or projection lacks an explicit schema version;
- a mode-specific trading-decision implementation replaces or copies the canonical core;
- infrastructure-specific representations leak into canonical domain contracts;
- a deterministic replay difference remains unexplained.

Some rules are enforced structurally through imports, AST/static checks, or contract tests; duplicate semantic authority also remains a mandatory review item because a numerical tool cannot reliably prove its absence.

### Legacy ratchet and deadlines

The first implementation records a reproducible lint, typing, coverage, and architecture baseline for existing noncritical code. After that:

- a change cannot add a new violation or lower a measured baseline;
- a materially changed file or module is brought to the applicable current standard rather than merely preserving its old debt;
- every module on the qualifying online execution path meets the strict policy before the qualification clock starts;
- every critical module meets the policy before Level B can pass;
- remaining noncritical debt is tracked with owner, risk, and removal milestone.

A temporary waiver requires a specific violation, reason, risk, compensating control, owner, and expiry. Safety, accounting, reconciliation, migration, recovery, security, deterministic-parity, and required release gates cannot be waived or quarantined. Flaky mandatory tests are failures, consistent with Decision 3.

### Consequences

- Existing code can be modernized without an unrelated big-bang cleanup.
- New and qualifying behavior is held to the target standard immediately.
- Coverage thresholds remain meaningful because explicit domain and failure cases take precedence.
- Architecture rules are executable and cannot depend only on future reviewer memory.

### Declined alternatives

- **Require the final standard across every legacy file before feature work:** declined because it creates a large non-behavioral rewrite before the accepted architecture exists.
- **Use only formatting and unit-test success:** declined because it misses type, dependency, architecture, failure-branch, security, and coverage regressions.
- **Require 100% global coverage:** declined because it encourages low-value tests and still cannot prove financial or recovery correctness.
- **Allow permanent legacy exemptions:** declined because qualifying paths would retain unbounded and poorly understood risk.

## Decision 5: one locked workspace and one content-identified release

The canonical repository uses one locked Python workspace, one locked frontend dependency graph when the typed frontend is introduced, and one machine-readable release manifest whose content identities bind every qualification result to the exact candidate bytes.

### Python workspace and toolchain

- `gridlab`, `gridlab-studio`, and later canonical Python packages remain separate workspace members with their own `pyproject.toml` contracts but share one committed root `uv.lock`.
- The supported Python runtime and `uv` tool versions are pinned for a release line. The first exact Python patch is selected by dependency compatibility and target-VM acceptance during implementation; laptop and Azure qualification use the same supported minor and declared patch unless a cross-patch parity exception is explicitly proved.
- Runtime, development, test, lint, type, build, migration, security-scan, and acceptance-runner dependencies are declared in the workspace and lock. Qualification cannot depend on undeclared globally installed packages.
- Qualification runs a lock consistency check and exact non-editable environment sync. It must fail rather than rewrite an outdated lock or retain undeclared packages.
- An upgrade is an explicit source-controlled change to project metadata and the lock, with vulnerability review, change-impact classification, affected tests, and new candidate identity.
- A standardized `pylock.toml` export and CycloneDX dependency inventory are generated as inspectable release evidence; the committed `uv.lock` remains the canonical workspace resolution.

This uses the workspace, locked execution, exact synchronization, and export behavior described by the official [uv workspace](https://docs.astral.sh/uv/concepts/projects/workspaces/), [locking and syncing](https://docs.astral.sh/uv/concepts/projects/sync/), and [lock export](https://docs.astral.sh/uv/concepts/projects/export/) documentation.

### Frontend dependency graph

- The React/TypeScript frontend commits `package-lock.json` and pins the Node.js and npm versions used by the release line.
- Qualification performs a clean `npm ci` installation using the committed lock and source-controlled install configuration.
- An ordinary dependency-resolving `npm install` is permitted only while deliberately changing dependencies; the resulting manifest and lock change are reviewed together.
- Built frontend assets are checksummed and included in the same product release manifest as the backend.

This follows the clean, lock-enforced behavior in the official [`npm ci` documentation](https://docs.npmjs.com/cli/commands/npm-ci/).

### Authoritative version and release identity

The existing `1.0.0`/`1.1.0` disagreement is removed. One root source declares the human-readable semantic product version and generates package/application version surfaces from it.

Every candidate records at least:

- semantic product version;
- exact Git commit and assertion that the qualified source tree was clean;
- Python, Node/npm, operating-system target, and build-tool identities;
- Python and frontend lockfile digests;
- source, migration-set, generated-asset, and individual bundle-file digests;
- final archive SHA-256 digest.

The final archive digest is the authoritative identity of the bytes transferred and installed. A friendly identifier such as `gridlab-0.1.0-94bf51c-5f47a2` may combine the semantic version, abbreviated commit, and digest prefix, but it never replaces the full values. Rebuilding creates a new candidate until byte identity and all affected qualifications are established; matching source alone does not allow results to be attached to unverified bytes.

### Required release manifest

The sealed manifest contains:

- all identities above;
- application/workspace package versions and complete direct/transitive dependency inventory;
- event, command, configuration, API, database, journal, snapshot, projection, and evidence-manifest schema compatibility declarations;
- ordered migration identifiers and checksums;
- included runtime services, frontend assets, installation definitions, and infrastructure-definition compatibility;
- required venue-capability contract and target Azure profile;
- Level A and Level B test-plan/result/report digests;
- dependency/security scan inputs, results, and accepted nonblocking findings;
- operator approval state and timestamps, kept separate from the immutable build fields.

The build manifest is immutable. Approval and installation records refer to its digest rather than editing the manifest after sealing.

### Personal-MVP trust boundary

The MVP does not introduce a hosted package registry, mandatory hosted CI, artifact-signing service, certificate authority, or multi-party approval system. Integrity and provenance rely on committed clean source, locked dependencies/toolchain, content digests, local qualification, trusted SSH transfer, private Blob retention of active/rollback bundles, and the single operator's explicit approval. This does not claim protection if the trusted laptop or operator account is fully compromised; that residual risk is already recorded in the security specification.

The exact Linux-target bundle construction and offline/online dependency-install boundary is decided with the release-construction workflow later in this specification.

### Declined alternatives

- **Independent locks per canonical Python package:** declined because the deployed application could qualify incompatible dependency resolutions.
- **Broad version ranges without a committed lock:** declined because repeated tests and installations could use different transitive code.
- **Use the Git commit alone as the release identity:** declined because toolchain, generated assets, dependencies, and final archive bytes can differ for the same source commit.
- **Add enterprise signing/registry infrastructure now:** declined because it adds single-operator cost and complexity without removing the accepted trusted-laptop boundary.

## Decision 6: forward-only expand–migrate–contract with immutable evidence

Durable evolution uses forward-only, ordered migrations and an expand–migrate–contract sequence. Authoritative history is never rewritten to make it look as if it was originally produced by a newer schema. Every durable migration requires a verified pre-migration recovery point and runs only while trading commands are disabled and the runtime is frozen.

### Migration sequence

1. Enter a command-disabled frozen posture and complete authoritative venue reconciliation.
2. Verify database integrity, schema/migration history, migration-set checksums, release compatibility, and required local/Blob capacity.
3. Create a named application-consistent pre-migration recovery point and pass its required verification.
4. Apply the immutable migration set in declared order, transactionally where SQLite supports it and through copy–verify–switch where an in-place atomic transformation is not safe.
5. Rebuild or invalidate replaceable projections and snapshots as declared by the release manifest.
6. Run schema, journal, accounting, replay, configuration, projection-rebuild, and migration invariants against the resulting database.
7. Start the new release in frozen recovery, validate identities, replay the required tail, and reconcile again.
8. Permit operation only through the normal operator-controlled reconciled-resume workflow.

No migration is performed silently during an operating run. A startup that detects a required unapplied migration remains frozen and presents the migration plan rather than applying it automatically.

### Expand–migrate–contract

- **Expand:** introduce an additive representation that the declared active and rollback paths can tolerate.
- **Migrate:** read old and new representations, deterministically create new projections/configuration versions where needed, and prove equivalent canonical outcomes.
- **Contract:** remove obsolete compatibility fields/readers only in a later release after the rollback window, retained-evidence readership, and explicit compatibility obligations allow it.

A physical database change need not keep every obsolete projection forever. The rule protects authoritative meaning and the declared rollback pair while allowing rebuildable data to be replaced.

### Artifact-specific rules

| Artifact | Evolution rule |
| --- | --- |
| Trading journal and authoritative events | Original stored records and schema identity remain immutable. Versioned readers/upcasters produce the current in-memory form. |
| Database schema | Ordered, forward-only, checksummed migrations recorded in a dedicated migration ledger. |
| Immutable configuration | A migration creates a new identified configuration version and a provenance link; it does not edit the old version. |
| Active-run configuration | The run stays pinned to its admitted version unless a separately authorized lifecycle transition permits a new version. |
| Snapshots | Rebuild or discard when compatibility is not proved; snapshots are accelerators, not authorities. |
| Read models/dashboard projections | Rebuild deterministically from authoritative evidence when their schema changes. |
| Evidence exports | Never modified; importers declare and test the historical versions they support. |
| Studio/API payloads | Explicit schema versions and compatibility for the installed active/rollback bundle pair; no unsupported public multi-client compatibility promise. |

An upcaster is a pure deterministic reader that maps an older stored event into the current canonical in-memory representation without changing the original bytes. Readers must support every authoritative version required by retained evidence, directly or through tested upcaster chains.

### Compatibility matrix

Each release manifest states for every durable contract:

- schema versions the release can read, write, and migrate;
- minimum source version for each migration and resulting target version;
- whether the retained rollback release can open and safely operate on the expanded schema;
- whether rollback instead requires the pre-migration recovery point;
- snapshots/projections to invalidate or rebuild;
- historical fixtures and replay fingerprints that must remain equal;
- whether any intentional semantic change invalidates prior research or operational evidence.

An unknown authoritative version, missing migration, edited migration checksum, incompatible reader, or unexplained replay difference is a fail-closed frozen condition.

### Migration implementation and verification

- Every migration has a permanent identifier, checksum, source/target schema, preconditions, postconditions, resource estimate, failure behavior, and test fixtures.
- A migration included in a sealed or released bundle is immutable; a correction is a new migration.
- A migration is transactional or safely restartable with an explicit durable progress marker. Re-execution must either be idempotent or refuse with a precise already/partially-applied diagnosis.
- Destructive transformations operate on a verified copy and switch only after invariant and row/object-count checks; the only authoritative copy is never destructively transformed in place.
- Tests cover empty, representative, boundary, realistically large, interrupted, insufficient-space, corrupted, duplicate-run, and already-migrated states.
- Golden historical evidence is replayed before and after migration. Equal semantics produce equal canonical fingerprints. Intended semantic changes require explicit approval and affected-evidence invalidation rather than a changed golden file with no explanation.

### Rollback relationship

General destructive down-migrations are not maintained. When the compatibility matrix proves the previous qualified bundle can use the expanded state, binary rollback may retain the database. Otherwise rollback restores the verified pre-migration recovery point, starts frozen, repairs the local/venue knowledge gap through the accepted reconciliation protocol, and preserves post-point evidence separately. The exact rollback decision follows this migration policy.

### Consequences

- Historical evidence remains attributable to the code and schema that produced it.
- Replaceable projections do not create permanent compatibility burden.
- Migration failure occurs while exposure-increasing commands are disabled and a tested recovery point exists.
- Rollback capability is explicit per candidate rather than assumed from a version number.

### Declined alternatives

- **Automatic startup migration:** declined because an ordinary restart could unexpectedly alter the only durable state before recovery and reconciliation.
- **Rewrite historical events/configurations in place:** declined because it destroys original evidence and makes prior results irreproducible.
- **Maintain general-purpose down-migrations:** declined because destructive reversal is difficult to prove and weaker than verified recovery plus reconciliation.
- **Unlimited backward compatibility for every projection:** declined because projections are rebuildable and the resulting complexity would not protect authoritative evidence.

## Decision 7: offline side-by-side deployment with frozen acceptance

One local command constructs and qualifies the exact target-compatible release. One SSH workflow stages and installs it beside the retained versions. Installation acceptance and trading resume are separate durable operator decisions; neither a passing local build nor a healthy installed process grants trading authority.

### Local construction and qualification

From an exact clean commit, the resumable acceptance runner:

1. verifies source, semantic version, runtime/toolchain, workspace/frontend locks, target OS/architecture/Python ABI, schemas, migrations, and compatibility declarations;
2. runs every applicable Level A and Level B gate and seals their machine-readable reports;
3. builds non-editable application wheels and Studio assets;
4. creates a complete target-compatible offline dependency wheelhouse;
5. includes immutable migrations/schemas, service entry points, installation/preflight/health scripts, and required non-secret runtime definitions;
6. generates the Decision 5 manifest and dependency inventory;
7. creates one archive and records its exact byte length and SHA-256 digest.

The candidate is not qualified when a mandatory check is skipped, stale, flaky, waived where waivers are prohibited, or bound to different bytes. The VM does not clone Git, resolve application dependencies from the internet, compile application code, or run historical research backtests during installation.

### SSH staging and independent preflight

The deployment action displays the exact source release, target Azure environment/host, affected services, current/rollback release identities, configuration/database compatibility, and expected frozen impact. It verifies the local archive, uploads it to a non-active staging path, and requires the VM to independently verify:

- digest, length, manifest/file checksums, release identity, and target compatibility;
- archive path safety, ownership/permissions, absence of secrets and prohibited content;
- disk/memory headroom and installation resource estimate;
- required external persistent paths and service identities;
- schema/migration plan, preconditions, compatibility/rollback classification, and recovery-point requirement.

An interrupted, duplicate, or corrupted upload cannot modify the active pointer or persistent trading state.

### Runtime preparation

Before an affected credentialed runtime stops, it follows the accepted posture state machine: prevent new exposure, durably settle ingress/outbox state, classify outstanding command outcomes, reconcile venue evidence, seal a pre-change checkpoint, and create/verify any required migration recovery point. Existing orders are managed according to the accepted pause/stop/reconciliation rules; deployment never performs an untracked blanket cancel or assumes cancellation succeeded.

Paper, Testnet, and later live stores, configurations, process identities, pointers, permissions, and restart scopes remain isolated. An unaffected runtime need not stop unless the shared dependency/capacity assessment says continued operation is unsafe.

### Side-by-side installation

Each release is installed into its own versioned, read-only directory beside the retained current and rollback bundles. Databases, journals, configurations, secrets, market captures, logs, reports, and evidence remain outside release directories. Installation never mutates the old release.

Only after preflight and migration eligibility pass may an atomic stable pointer select the new directory. The VM does not require a reboot; `systemd` restarts only the minimum affected service processes in declared order. Every replacement process starts in frozen recovery rather than its former operating state.

### Post-install verification

Before installation acceptance, the exact installed bytes must prove:

- release/configuration/schema/migration/service identities and database integrity;
- journal, accounting, allocation, snapshot-tail replay, and deterministic fingerprint invariants;
- required filesystem, network, environment, credential, and cross-runtime permission denials;
- ingress/market-stream recovery and authoritative venue reconciliation where applicable;
- control gateway authentication/command admission, health, alerts, dead-man monitoring, evidence capture, backup/recoverable-point operation, and required operator visibility;
- B1ms CPU, memory, disk, I/O, freshness, and deadline headroom under the declared post-install acceptance load.

Failure keeps the affected runtime frozen, preserves the failed candidate/install/migration evidence, and enters the rollback decision path. There is no automatic trading resume.

### Separate authorities

The workflow records three non-equivalent states:

1. **Release qualified:** the exact archive passed its declared local engineering gates.
2. **Installation accepted:** those bytes installed on the identified VM and passed environment-specific frozen checks.
3. **Trading resumed or activated:** the operator separately authorizes an eligible reconciled runtime under its Paper, Testnet, or later live workflow.

For first live use, installation acceptance still grants neither promotion-bundle approval nor the separately confirmed `250 USDT` activation attempt.

### Shared build and retained recovery artifacts

Production-data Paper and Testnet qualification use the same exact bundle digest and strategy candidate with separate mode profiles and state. A later live promotion uses the exact already-qualified candidate bytes rather than rebuilding nominally identical source. After installation acceptance, the exact active and immediate compatible rollback archives, manifests, reports, and compatibility matrices are retained locally and in the private Blob release area under the accepted retention policy.

### Declined alternatives

- **VM Git pull and online build/install:** declined because mutable source, public resolution, build tools, and branch state would break exact candidate identity and enlarge the online surface.
- **Replace the active directory in place:** declined because an interrupted installation would damage both current operation and rollback.
- **Restart every process or reboot the VM for every release:** declined because isolated services have separate state and restart scopes; broader restart is required only by an explicit dependency or acceptance scenario.
- **Automatically resume after health checks:** declined because health cannot grant trading authority or prove current reconciliation/activation eligibility.

## Decision 8: compatibility-driven rollback with reconciliation, never command replay

Rollback is a frozen evidence-driven recovery workflow, not an automatic response to a failed health probe. The retained previous bundle is usable only through its sealed identity, current qualification/evidence status, and the candidate-specific compatibility matrix. Rollback never assumes that switching code reverses database changes or Binance effects.

### Path A — pre-switch abandonment

An upload, staging, preflight, or installation failure before the active pointer changes leaves the current release and durable state untouched. The failed staging attempt, checks, and incident are preserved. An incomplete directory is deleted only after it no longer has diagnostic or retention value. This is an abandoned candidate, not a runtime rollback.

### Path B — compatible binary rollback

When the compatibility matrix proves that the retained release can safely read and write the current durable schemas and interpret every event already produced:

1. freeze the affected runtime and disable exposure-increasing authority;
2. durably settle ingress/outbox processing and reconcile outstanding venue outcomes;
3. stop the candidate process;
4. atomically select the exact retained previous bundle;
5. start it in frozen recovery using the current database;
6. rebuild/replay, verify accounting/risk/journal invariants, and reconcile;
7. require separate operator installation acceptance and reconciled resume.

### Path C — release plus state recovery

When the previous release cannot safely use the migrated state:

1. freeze and stop the affected runtime;
2. preserve the failed database, journal tail, logs, captures, release, migration progress, and incident evidence as a non-active diagnostic set;
3. restore and verify the named pre-migration recovery point;
4. select its declared compatible previous bundle;
5. start frozen, rebuild, and replay only authoritative local events contained by the recovery boundary;
6. query Binance and ingest later order, execution, commission, and balance facts through canonical reconciliation using their stable identities;
7. resolve every unknown command and prove accounting/allocation/inventory/order invariants;
8. require operator acceptance and reconciled resume.

Commands recorded after the restored point are evidence to query, not instructions to resend. No command or order is blindly replayed. Stable client/venue identities and reconciliation prevent a restored runtime from creating a duplicate submission.

### Path D — forward recovery

If the new release has produced a durable semantic or external effect that the old release cannot understand safely, or if the previous release contains the same dangerous defect, rollback is refused. The runtime remains frozen under the accepted exposure-reducing safety policy while the operator reconciles venue state and constructs a separately qualified corrective release. Restoring an older version number is never valued above safe interpretation of current reality.

### Automation and authority

Automation may refuse the active-pointer switch, restart the same release frozen, calculate and present an exact rollback plan, and execute identity-bound steps after operator authorization. It may not automatically select an earlier release after the candidate could have written durable state or communicated with Binance. Emergency Stop remains immediately available; supervisor restart follows the accepted same-release frozen recovery contract.

### Failed migration handling

- A transactional failure rolls back the transaction and records the attempt.
- A restartable migration resumes only from its verified durable progress marker.
- A partially applied non-restartable transformation selects recovery Path C.
- An edited checksum, missing migration, uncertain phase, invariant failure, or insufficient recovery evidence blocks retry.
- The same failure is never retried in an unbounded loop; a new attempt requires diagnosis and a declared recovery/retry plan.
- Failed state is preserved outside the active path and cannot be selected accidentally.

### Objectives and evidence

The existing 15-minute protected-evidence RPO and 60-minute safe frozen RTO apply. RTO completion means an identified, invariant-clean, recoverable, reconciled-or-explicitly-reconciling frozen service—not automatic trading operation. The rollback record binds reason, trigger, operator command, source/target releases, compatibility decision, database/recovery point, venue reconciliation boundary, preserved evidence, timing, RPO/RTO result, incidents, and final posture.

### Qualification effect

- A change or rollback affecting strategy, accounting, risk, execution, reconciliation, market interpretation, decision-critical dependencies, or evidence semantics invalidates the affected 30-day Paper attempt.
- Testnet soak restarts when adapter/protocol/runtime/recovery behavior in its claim changed.
- A proven presentation-only or non-decision diagnostic rollback may preserve unrelated qualification through the accepted impact analysis.
- Attempts before and after a decision-critical identity change remain separate evidence and their elapsed days cannot be combined.
- Live rollback never claims that real venue exposure reverted; venue orders/assets are reconciled under current risk limits before any next action.

### Mandatory proof

Before qualification, the candidate process exercises compatible binary rollback, recovery-point rollback, interrupted install/migration, corrupted/insufficient recovery input, late fill and unknown-command reconciliation, no-command-replay, and failed rollback/forward-recovery selection. Affected cases rerun whenever installation, migration, durable state, reconciliation, recovery, or command identity changes. Operational restore/disaster drill cadences remain additional Level C evidence.

### Declined alternatives

- **Automatic previous-version selection after crash/health failure:** declined because the database and venue may already contain effects the previous release cannot interpret.
- **Always keep the current database:** declined because a migration may make it unsafe for the retained release.
- **Always restore the database:** declined because a compatible binary rollback is faster and avoids an unnecessary local knowledge gap.
- **Replay commands from the restored journal:** declined because an uncertain or already accepted Binance command could be submitted twice.

## Decision 9: contract-only extension proofs and measured B1ms qualification

The MVP proves each named future variation through a small compile-time/executable contract implementation and change-isolation test. It does not implement, expose, configure, deploy, or qualify the future capability. Separately, the real three-process MVP release must pass the accepted 24-hour representative B1ms capacity campaign before the qualifying Paper clock may start.

### Required seam proofs

| Later variation | MVP contract proof | Explicitly not implemented |
| --- | --- | --- |
| Adaptive/dynamic grid | A test-only alternate strategy consumes canonical events and produces canonical decisions while reusing accounting, execution, risk, journal, replay, and promotion contracts. | Dynamic logic, configuration UI, online selection, evidence, and promotion. |
| Interactive Brokers | A deterministic test adapter implements the venue-capability, market-data, command, and observation ports and proves venue-specific representations remain outside the domain. | IB API connectivity, account semantics, deployment, credentials, and trading. |
| Additional strategy family | A minimal test strategy can be composed without copying ledgers, reconciliation, lifecycle, risk, or runtime orchestration. | Production strategy catalogue or plugin discovery. |
| Multiple runs/symbols | Two in-memory run/allocation instances prove identity, state, reservation, event, command, and accounting isolation with no process-global trading state. | Multiple simultaneous Azure algorithms, symbols, credentials, or capital allocations. |
| Compounded sizing | A test-only sizing policy passes the canonical sizing/accounting contract without altering immutable fixed-sizing runs. | Production compounding or UI controls. |
| Persistence replacement | In-memory test persistence and canonical SQLite implementations pass the same authoritative contracts. | PostgreSQL, managed database, or replication. |
| Deployment replacement | Domain/application suites run without Azure, systemd, network, filesystem, or cloud imports; outside composition supplies those adapters. | Containers, Kubernetes, HA, or another cloud. |

These proofs use explicit typed construction/dependency injection. The MVP does not add a generic plugin loader, runtime discovery framework, feature marketplace, dormant production adapters, or empty service hierarchy. A future implementation receives new independent validation and cannot claim the static-grid/Binance evidence merely because its seam compiled.

### Change-isolation oracle

Each seam proof declares its allowed owning modules and prohibited unrelated modules. Adding the reference implementation may add its own contract implementation, configuration type, fixtures, and tests; it must not duplicate or edit unrelated accounting, journal, execution, reconciliation, risk, or existing strategy semantics. Unexpected cross-cutting edits are architecture feedback and fail the fitness review until the boundary or impact is deliberately re-specified.

### B1ms candidate and workload

The exact installed candidate runs continuously for at least 24 hours on the selected one-vCPU, 2-GiB-RAM B1ms node with no swap and the 64-GiB E6 Standard SSD. The representative deployment includes the control gateway, Production-Data Paper runtime, Binance Testnet runtime, required SQLite/journal/outbox stores, monitoring, local logging, targeted market capture, backup, compaction, Blob transfer, and external dead-man path.

The campaign includes representative normal and burst market traffic, Paper/Testnet order lifecycle, WAL/checkpoint work, capture/log rotation, backup/compression/upload/verification, compaction, Blob throttling/retry, one permitted bounded background phase, process restart/replay/reconciliation, dependency faults, and resource-pressure cases. Historical research backtests and the complete local Studio frontend do not run on the Azure VM.

### Hard B1ms gates

- At least **384 MiB host-available memory** remains at the worst representative point after OS/agent, all three services, SQLite/cache/staging, monitoring, and one bounded background phase.
- No swap, OOM, service memory-limit kill, unsafe allocation failure, sustained resource pressure, or CPU-credit exhaustion trend occurs.
- No material event/evidence is dropped; optional diagnostics/background work yields before admission, journal, cancellation, reconciliation, incident, recovery, or required capture capacity is threatened.
- No accepted safety/control deadline or zero-tolerance correctness condition fails.
- Active disk, WAL, captures, logs, backups, staging, and compaction retain the accepted unsafe-reserve/time-to-exhaustion margin, and the temporary-disk-loss case has zero authoritative effect.
- The 15-minute protected-evidence RPO and 60-minute safe frozen RTO pass under the accepted restore/reconciliation cases.
- Paper/Testnet state, authority, resources, incidents, commands, and evidence remain isolated.

The accepted normal-load objectives also pass: journal transaction p99 at most 250 ms; eligible fact receipt through committed processing p99 at most one second; dispatch-ready command through first attempt p99 at most one second when eligible; health/metric age at most 30 seconds; and protected health endpoint p95 at most 500 ms. Stricter market, control, reconciliation, clock, and heartbeat safety deadlines remain authoritative.

### Report, frequency, and resize

The sealed capacity report binds the exact release/configuration/schema/VM/disk/network identities, scenario/load interval, host/per-process CPU and memory, B-series credits, queues/latencies, disk/SQLite/capture/backup/compaction, network/stream/rate-limit, RPO/RTO, incidents, evidence references, missing samples, and every threshold with actual value and provenance.

Its result is exactly `B1MS_ACCEPTED`, `RESIZE_REQUIRED`, or `INCONCLUSIVE_RERUN`. Missing/invalid decision-relevant measurements cannot pass. Any hard capacity-related failure requires resize; the operator cannot waive it to preserve the lower price.

- A bounded resource smoke test runs for each Level B release candidate.
- The full 24-hour Level C campaign passes before first qualifying Paper.
- It repeats after changes affecting process topology, runtime dependencies, persistence/journal/capture, backup/compaction, resource controls, background scheduling, deployment profile, or expected workload.
- Impact-proven presentation/documentation-only changes do not repeat it.
- Continuous operational metrics and sealed capacity reviews remain inputs to resize decisions.

The first resize remains B2als_v2 (2 vCPU/4 GiB), followed by B2as_v2 (2 vCPU/8 GiB) if required. A resize is a planned frozen change and repeats the complete capacity, restart/replay/reconciliation, backup/restore, RPO/RTO, monitoring/dead-man, and cost qualification.

### Consequences

- The target architecture has executable evidence for its named seams without carrying unused production features.
- A later strategy, venue, or deployment begins behind a proved boundary but receives its own semantics, risks, migrations, and qualification.
- B1ms remains a measured hypothesis, not a cost-driven assumption.
- Resource failures cause resize and retest rather than reduced evidence or relaxed safety.

### Declined alternatives

- **Implement partial future features now:** declined because dormant algorithms/adapters expand safety-critical scope without MVP value.
- **Generic plugin architecture:** declined until multiple real implementations demonstrate a need beyond explicit typed composition.
- **Architecture diagrams without executable seam proofs:** declined because dependency drift would remain undetected.
- **Use average CPU/RAM or a short smoke test to accept B1ms:** declined because credits, bursts, backup/compaction contention, restart, and recovery are the relevant failure modes.
- **Keep B1ms after a hard failure by reducing evidence or safety work:** declined because cost cannot override correctness, recoverability, or deadlines.

## Completion

Decisions 1–9 form the accepted verification, release, migration, compatibility, deployment, rollback, extension-fitness, and resource-qualification policy. Implementation traceability must map every mandatory statement to an owning test, acceptance case, release-manifest field, operator checkpoint, or explicitly inherited operational evidence source. No unresolved decision remains in this specification.
