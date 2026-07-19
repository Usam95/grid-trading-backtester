# Infrastructure Glossary

## Initial production deployment

A low-cost, single-instance Azure deployment with durable state, automatic restart, exchange reconciliation, and safe failure behavior. Application-level high availability is outside the first live milestone.

## Research workstation

The operator-controlled laptop that runs local `gridlab` backtests and `gridlab-studio` analysis. Its availability affects research throughput only and never grants, holds, or interrupts online trading authority.
_Avoid_: Online execution environment, trading control plane

## Online execution environment

The independent Azure runtime that performs bounded production-data paper trading, Testnet venue-integration testing when required, and later live trading. It is deliberately isolated from historical backtest workloads and the full research UI.
_Avoid_: Research workstation, Azure batch compute

## Local release qualification

The reproducible operator-controlled evidence that one exact source and dependency identity passed every applicable canonical release gate and produced one identified immutable application bundle.
_Avoid_: Ad hoc local test, online health check, trading authorization

## Qualified release bundle

An immutable application package whose exact source, dependencies, target, manifest, test evidence, byte length, and cryptographic digest passed local release qualification; installation never grants trading authority.
_Avoid_: Source checkout, mutable build directory, runtime data

## Qualified dependency set

The exact direct, transitive, build, and runtime package artifacts whose versions, sources, hashes, platform, inventory, tests, and security scan belong to one qualified release.
_Avoid_: Version range, installed environment, latest dependencies

## Applicable vulnerability

A reported weakness whose affected artifact and conditions are present in, or cannot be positively excluded from, the exact qualified release and deployment boundary.
_Avoid_: Scanner finding, severity score, theoretical vulnerability

## Active release

The qualified release bundle currently selected for an installed environment after successful archival and installation acceptance; being active does not itself authorize trading.
_Avoid_: Running process, approved configuration, trading authority

## Rollback release

The immediately preceding compatible accepted release retained with its required recovery identities so an unsuccessful change can be reversed under a frozen verified workflow.
_Avoid_: Latest source, arbitrary old bundle, automatic fallback

## Reboot-required state

A host condition in which an installed system or kernel update is not fully effective for the running machine until it restarts; package installation alone cannot represent this state as fully patched.
_Avoid_: Automatic reboot, update failure, process restart

## Accepted security exception

An explicit operator acceptance of a known security-control deviation and its residual exposure; it remains visible in evidence and qualification and never redefines the unsafe condition as compliant or repaired.
_Avoid_: Risk elimination, incident acknowledgement, hidden waiver

## Single-operator assumption

The declared MVP boundary that exactly one human holds administration and operator authority; it reduces multi-user coordination risk but does not eliminate mistakes, compromise, partial change or provider-caused state differences.
_Avoid_: No-risk system, single process, single account allocation

## Drift scanner

A scheduled read-only comparison of selected deployed resource, host, release or configuration state against its approved baseline that reports unexplained differences without changing them.
_Avoid_: Trading-price drift, file watcher, automatic remediation

## File watcher

A mechanism that observes filesystem changes when they occur; it can report that bytes or metadata changed but does not by itself prove whether the change was approved, safe or complete.
_Avoid_: Drift scanner, integrity proof, source control

## Automatic remediation

A privileged mechanism that changes deployed state toward a declared baseline after detecting a difference; it can itself cause an unsafe change when the baseline or diagnosis is wrong.
_Avoid_: Read-only detection, operator-reviewed repair, reconciliation

## Deployment acceptance run

One identified, resumable, evidence-producing evaluation that proves an exact infrastructure, release and configuration meet every declared pre-qualification requirement without granting trading authority.
_Avoid_: Thirty-day paper qualification, infrastructure deployment, live activation

## Testnet acceptance plan

One immutable, bounded, expiring, operator-confirmed set of virtual-asset venue commands and expected evidence used to qualify authenticated Testnet integration without granting live authority.
_Avoid_: Trading strategy, live activation, open-ended Testnet run

## Re-acceptance

The evidence-producing repetition of every deployment-acceptance phase whose validity may have been affected by an identified change; it cannot reuse evidence without proving the relevant identities unchanged.
_Avoid_: Automatic approval, paper-qualification continuation, full rerun by definition

## B1ms-first runtime profile

The selected initial one-vCPU, two-GiB Azure runtime whose suitability must be established by production-data load, recovery, compaction, and resource-headroom benchmarks before a qualifying paper run. Failure of an accepted guardrail requires resize and retest.
_Avoid_: Production approval, fixed capacity commitment

## Process supervisor

The mechanism outside an authoritative runtime that starts it, constrains resources, observes termination, and applies bounded restart policy without owning trading state or granting resume authority.
_Avoid_: Trading runtime, safety controller, automatic resume

## Deployment packaging

The replaceable operational form used to install and run the same declared application roles and infrastructure contracts. Changing packaging does not change trading semantics, but it requires impact assessment and applicable operational requalification.
_Avoid_: Trading strategy, deployment topology, release authority

## Infrastructure definition

The versioned declarative description of required Azure resources, relationships, protections, and non-secret parameters from which an equivalent frozen online environment can be reviewed and rebuilt.
_Avoid_: Portal configuration, application release, runtime database

## Infrastructure apply authority

The narrowly scoped operator capability to preview and make an approved infrastructure definition effective in the declared Azure environment; it cannot administer venue secrets or grant trading authority.
_Avoid_: Runtime command authority, trading authority, source push

## Availability zone

A physically separate Azure location within one region. Placing one runtime in a named zone identifies its location but does not by itself provide redundancy or failover.
_Avoid_: High availability, failure domain, region

## Failure domain

The infrastructure components that can become unavailable together from one failure. The initial VM and its LRS disk form one failure domain; separately verified ZRS objects do not make that runtime highly available.
_Avoid_: Availability zone, backup scope, application high availability

## Zone-redundant storage

Azure storage redundancy that synchronously maintains an object across multiple availability zones in one region. It protects against a zone failure, not logical deletion, invalid content, account compromise, or whole-region loss.
_Avoid_: Backup, application high availability, cross-region recovery

## Blob container

A private logical bucket that groups stored objects under an access and lifecycle boundary; it is not a running application or Docker container.
_Avoid_: Deployment container, filesystem, database

## Resource headroom

The measured capacity remaining after representative peak workload, required agents, declared background work, and protected safety/recovery reserves are accounted for. Average unused capacity is not sufficient evidence.
_Avoid_: Free memory, VM size, unused disk

## Capacity qualification report

A sealed evidence record that binds one exact deployment profile and representative workload to resource, latency, recovery, isolation, cost, log, and incident measurements and produces an accepted, resize-required, or inconclusive outcome.
_Avoid_: Monitoring dashboard, benchmark summary, resize recommendation

## Stable outbound identity

The declared fixed network address from which an online execution environment is permitted to contact a venue and against which venue credential restrictions and runtime readiness are verified.
_Avoid_: Public endpoint, operator access, dynamic outbound address

## Platform-managed encryption

Azure encryption at rest whose encryption-key lifecycle is operated by the Azure service rather than by Gridlab or the operator.
_Avoid_: Key Vault secret storage, customer-managed key, application encryption

## VM managed identity

An Azure-managed service identity whose security boundary is the virtual machine resource, not an individual process inside it. Local process controls can restrict ordinary use but do not turn one VM into independent cloud-identity failure domains.
_Avoid_: Process identity, Binance credential, Linux service account

## Secret-entry path

The sole approved route by which the operator transfers a newly issued venue credential into its versioned Key Vault object without involving Studio, deployment, or runtime storage.
_Avoid_: Secret configuration, credential upload, deployment input

## Hybrid evidence storage

The selected split in which a bounded local SSD owns active transactional and temporary working state while Azure Blob owns verified off-VM backups and closed retained evidence. Publication and checksum/reader verification precede deletion of any eligible local copy.
_Avoid_: Blob-mounted database, local-only retention

## Verified offload

The idempotent seal, upload, checksum/length/reader verification, and manifest-publication boundary after which a non-required local closed copy may become eligible for deletion.
_Avoid_: Upload attempt, pressure deletion

## Recovery point objective

The maximum permitted lag between the newest protected committed application history and a verified off-VM recoverable point. The MVP target is 15 minutes while protected state is changing.
_Avoid_: Backup schedule, recovery time objective

## Recovery time objective

The maximum elapsed time from externally detected total service/disk loss to verified restore, replay, invariant checks, venue reconciliation, and operator-accessible frozen service. The MVP target is 60 minutes and excludes trading resume.
_Avoid_: Recovery point objective, automatic resume

## Recoverable point

A sealed, manifest-described, checksum/reader-verified off-VM application backup and dependency set that can restore one exact durable processing boundary. It never rolls the venue back or authorizes trading.
_Avoid_: Local recovery snapshot, uploaded file

## Protected processing lag

The elapsed age and sequence distance between the newest protected committed application state and the newest verified off-VM recoverable point. It is the operational measurement of RPO when state is changing.
_Avoid_: Backup timer age, market quiet time

## Online database backup

A transactionally consistent SQLite copy created through the supported online backup protocol while the source may remain active, with an exact durable processing boundary recorded for restore.
_Avoid_: Copying the database file, recovery snapshot

## Isolated restore verification

A disposable non-trading restoration of a verified recoverable point that checks database integrity, compatibility, replay, invariants, dependencies, and frozen posture without modifying the active system.
_Avoid_: Backup verification, disaster-recovery drill

## Disaster-recovery drill

A timed fresh-infrastructure exercise beginning from declared total VM/disk loss and ending at verified restore, replay, venue reconciliation, and operator-accessible frozen service. It measures the complete RTO and cannot place orders.
_Avoid_: Restart test, automatic failover

## Secure deletion

Policy-governed removal of retention-expired, unreferenced, unheld data across local and provider versions, with provider-recoverability tracking and a non-sensitive audit tombstone. It does not promise physical file overwrite on SSD/cloud media.
_Avoid_: Retention expiry, file overwrite

## Deletion tombstone

A durable non-sensitive record proving which identity/version class was authorized for deletion, under which policy, when provider deletion was requested/confirmed, and its outcome, without retaining reconstructable content.
_Avoid_: Deleted payload, preservation hold

## Provider-recoverable deletion

The interval after logical deletion during which Azure soft-delete, version, snapshot, or immutability policy still permits or requires provider recovery. It is tracked separately from confirmed expiry.
_Avoid_: Confirmed erasure, active retention

## Evidence-protection freeze

The canonical exposure-blocking response when authoritative persistence, required recovery protection, critical external supervision, or safe evidence capacity is unavailable. Valid inventory-reducing orders may remain only when their state and backing are certain.
_Avoid_: Diagnostic degradation, automatic emergency cancellation

## Diagnostic degradation

A replaceable observability-sink failure during which operation may continue temporarily because authoritative persistence, local bounded diagnostics, safety controls, and required external alerting remain intact.
_Avoid_: Evidence-protection failure, healthy operation

## Fault-injection oracle

The complete deterministic expected outcome for an injected failure: durable evidence/order, posture/deadline, venue effects, accounting/invariants, incident/notification, replay/recovery, and cleanup. Process survival alone is not an oracle.
_Avoid_: Test action, line coverage

## Structured diagnostic log

A versioned non-authoritative JSON record explaining technical operation through a stable event code, allowlisted fields, and applicable durable evidence identities.
_Avoid_: Trading event, text log line

## Diagnostic event code

A stable namespaced identifier defining one searchable diagnostic-log meaning independently of its human message wording.
_Avoid_: Exception message, journal event type

## Diagnostic capture session

A time-bounded authenticated operator request enabling scoped DEBUG records for an identified component and optional run, correlation, order, or incident.
_Avoid_: Permanent debug mode, packet capture

## Metric-series cardinality

The number of distinct monitoring time series created by a metric's label combinations; durable event and order identities are excluded because they grow without a fixed bound.
_Avoid_: Event count, metric count

## Process liveness

Evidence that the runtime and its main event loop respond, without implying that durable state, dependencies, or trading permission are ready.
_Avoid_: Decision readiness, trading health

## Service readiness

Evidence that protected API and operator workflows can safely access compatible durable application state, even when trading remains frozen.
_Avoid_: Process liveness, trading permission

## Operational service objective

A measurable availability, latency, or freshness target used to expose degradation before a safety deadline; failure warns but cannot extend or override canonical safety rules.
_Avoid_: Risk limit, accounting invariant

## Diagnostic span

A bounded non-authoritative timing record for one technical step within a traced workflow, linked to durable business correlation without replacing it.
_Avoid_: Canonical event, correlation identity

## Operational incident

A durable correlated lifecycle for one material root condition, its repeated occurrences, notification, recovery evidence, acknowledgement, resolution, and review.
_Avoid_: Log error, alert delivery

## Incident fingerprint

The deterministic bounded rule-and-scope identity used to update one active operational incident across repeated matching occurrences.
_Avoid_: Error message, incident identity

## Alert delivery

One identified external notification attempt and provider outcome for a durable incident; it cannot acknowledge the incident or change trading state.
_Avoid_: Operational incident, operator action

## Incident closure review

The operator's post-resolution examination and recorded conclusion required before a warning or critical operational incident becomes closed.
_Avoid_: Acknowledgement, incident resolution

## Evidence preservation hold

An authenticated time-bounded or reviewed instruction that prevents otherwise eligible evidence from expiring while a declared incident, review, legal, or operational need remains.
_Avoid_: Retention class, backup lock
