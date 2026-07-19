# Minimal Azure deployment specification

Status: accepted deployment specification  
Target: the first qualifying online execution environment in Germany West Central  
Cost basis: Linux pay-as-you-go list pricing before VAT, using current Azure Retail Prices API evidence

## Purpose

Select the smallest practical Azure deployment that can satisfy the already accepted runtime, evidence, recovery, operator-control, and observability contracts without turning a personal single-operator MVP into a distributed platform. Cost is minimized only inside the correctness and qualification boundary; an undersized node that misses safety, recovery, or evidence requirements is not cheaper in the relevant sense.

This specification owns Azure resource selection, deployment wiring, resource budgets, supervision, recoverability infrastructure, operational monitoring, and cost controls. The later security specification owns the detailed threat model, authentication protocol, credential permissions/rotation, cryptographic policy, and hardening acceptance tests. Where an Azure resource must be selected before that work—for example Key Vault or an access path—this specification fixes the deployment seam and minimum capability but leaves the detailed policy to the security ticket.

## Inherited decisions that are not reopened

- The research workstation owns source development, canonical tests and quality checks, release-bundle construction, historical-data acquisition, historical backtests/research, Bicep validation/application, and full Studio analysis. Azure runs only work that must remain available independently of the laptop: the control gateway, production-data Paper, Testnet venue-integration operation, later live operation, authoritative online state/evidence, recoverable-point publication, and operational monitoring. No broad Azure backtesting, source build, or full Studio UI is provisioned.
- Qualification uses three independently supervised processes on one node: control gateway, production-data Paper runtime, and Testnet runtime. Live is a distinct runtime/store/credential scope, never a relabelled Testnet process.
- Every authoritative runtime is a single writer with its own SQLite database, journal, outbox, ledger, identities, reconciliation state, and evidence. No Redis, managed message bus, Kubernetes, or managed relational database is required.
- Start with the **B1ms-first runtime profile**: one vCPU and 2 GiB RAM. A representative 24-hour three-process benchmark plus restart, replay, reconciliation, backup, compaction, and fault drills must prove it before qualifying Paper. Any accepted guardrail failure forces resize and retest.
- Use one 64-GiB E6 LRS Standard SSD as the bounded active working disk and Hot ZRS Blob Storage for verified off-VM recoverable points and closed evidence. Eligible objects may transition to Cool after 30 days. Blob never hosts active SQLite/WAL or open capture/compaction state.
- A recoverable point uses SQLite online backup, exact manifests/checksums/read verification, and off-VM Blob publication. The protected-processing RPO is 15 minutes and complete frozen-service RTO is 60 minutes. Recovery never authorizes automatic trading resume.
- Process replacement starts frozen, obtains exclusive ownership, rebuilds/replays/reconciles, cancels surviving managed orders under policy, and waits for explicit operator authority. Infrastructure health cannot grant trading permission.
- An external dead-man path outside the process/VM detects a missing 30-second heartbeat after two elapsed minutes and delivers the accepted critical email plus mobile notification policy.
- Application-level high availability, a paid standby node, multiple simultaneous live grids, and cross-region automatic failover are outside the MVP.

## Codebase deployment audit

The canonical projects do not yet contain production Azure infrastructure-as-code, service definitions, backup/upload tooling, or a qualifying online deployment. `gridlab-studio` currently has only a development `uvicorn` launcher.

Legacy material includes Dockerfiles, a Docker Compose development stack, an ACI/Terraform sketch, environment-variable secret lookup, Azure Files-oriented file logging, and an Interactive Brokers deployment note. It remains useful as a catalogue of deployment concerns, but its topology is not canonical because it assumes some combination of PostgreSQL/Redis, ACI, Azure Files as active storage, broad environment credentials, optional monitoring, paper-as-Testnet semantics, or Interactive Brokers resources. Those conflict with the accepted deterministic Paper/Testnet split, single-node SQLite authority, supported online backups, verified Blob evidence, mandatory external monitoring, and B1ms-first budget.

No legacy deployment file may be promoted by renaming it. Useful Docker build practices, service health concepts, and secret-provider seams must be reimplemented against the accepted contracts and tested resource envelope.

## Decision overview

The deployment research and operator review resolved these topics in dependency order:

1. **Host and process packaging:** native system services versus containers on the selected VM, including isolation, resource limits, restart, logs, release identity, and B1ms overhead.
2. **Region and availability posture:** Germany West Central placement, single-instance limitations, zone selection where available, region/zone failure consequences, and why no standby node is accepted.
3. **Compute and active disk profile:** exact B1ms/E6 configuration, swap/temporary-disk rules, measured headroom, CPU-credit behavior, and deterministic resize targets/triggers.
4. **Network and stable outbound identity:** VNet/subnet/NSG, explicit Binance-capable outbound path and IP allowlisting, DNS/time synchronization, egress budget, and prohibited network appliances.
5. **Protected operator access:** how the laptop Studio reaches the control gateway and how operators administer the VM without exposing trading/database services; detailed auth and hardening remain in the security ticket.
6. **Blob and storage-account wiring:** account type, ZRS/LRS roles, containers/prefixes, lifecycle tiers, soft deletion/versioning/immutability boundary, private/public access, verified offload, and capacity alerts.
7. **Recoverable points and restore drills:** ten-minute online backup workflow, 15-minute protected-position enforcement, weekly isolated restore, monthly fresh-VM drill, disposable resource lifecycle, and 60-minute RTO proof.
8. **Managed identities and secret service:** Key Vault/managed-identity boundary, process credential isolation limitations on one VM, bootstrap/rotation seam, and separation of gateway/Testnet/live authority.
9. **Monitoring, logs, alerts, and external dead-man:** which facts remain authoritative locally, which curated diagnostics/metrics reach Azure Monitor, outside-VM heartbeat evaluation, email/mobile routing, retention, and ingestion limits.
10. **Provisioning, releases, patching, and supervision:** infrastructure-as-code choice, immutable release/paper-candidate identities, service accounts, boot/restart behavior, security update workflow, maintenance freeze, rollback, and configuration drift detection.
11. **Cost model and guardrails:** mandatory fixed resources, usage-sensitive meters, free allowances, restore-drill costs, Blob growth, cost anomaly/budget alerts, and B1ms versus resize budgets.
12. **Deployment acceptance and runbooks:** provisioning/restore timing, failure injection, resource benchmark, access loss, storage/monitoring degradation, rebuildability, and exact evidence required before the 30-day qualifying Paper run.

Each decision record will retain the recommendation, realistic alternatives, examples, consequences, and declined options. The final topology must trace every paid resource to an accepted requirement; optional upgrades remain explicit rather than silently entering the MVP baseline.

## Primary-source research

The completed [primary-source Azure research](azure-minimal-deployment-primary-research.md) recommends one Linux B1ms-first node, one E6 Standard SSD LRS OS/application disk, a directly attached Standard static IPv4, Standard GPv2 Hot ZRS Blob with eligible lifecycle tiering, VM managed identity plus Key Vault Standard, and bounded Azure Monitor/Log Analytics. Current Microsoft documentation supports the service capabilities; exact EUR amounts use the repository's first-party Azure Retail Prices API snapshot from 2026-07-17 because the research agent's 2026-07-18 live refresh was blocked. Price facts are snapshots rather than guarantees of subscription quota, allocatable regional capacity, contracted invoice pricing, or VAT.

The expected first-month B1ms baseline is approximately **EUR 24-30 before VAT**, excluding Azure VM Backup, paid Bastion/VPN/NAT/Firewall/Private Endpoints, domain/support costs, trading capital, and Binance fees. The selected warning threshold is EUR 35 and the selected mandatory operator-review threshold is EUR 50; cost alerts never stop infrastructure or trading automatically.

The research rejects an automatic upgrade to B2 or full VM Backup. B1ms remains the selected starting measurement profile. B2als_v2 is the first mandatory resize only if representative load, CPU credits, memory, disk, isolation, RPO, RTO, or safety deadlines fail. Application-level verified SQLite recoverable points in Blob remain authoritative; whole-VM backup is an optional recovery convenience only if drills later prove the rebuild path insufficient.

The following deployment-time preflight facts remain intentionally unverified by public research: B1ms/B2 quota and allocatable capacity in the operator's subscription, exact zone/SKU availability, Ubuntu/image compatibility, storage features, actual invoice offer/currency/tax, and any access SKU selected by the later security decision.

## Decisions

### Decision 1: native services now, container-ready boundary later

Selected by the operator on 2026-07-18: package the MVP as native Linux services supervised by `systemd`. Install one immutable, digest-identified Python application release and start the control gateway, Paper runtime, and Testnet runtime through separate unit files under separate least-privilege OS users. Each receives only its declared configuration/credentials, writable state directory, runtime lock, and bounded log/spool paths. Unit-level memory, CPU, process, file-descriptor, restart-rate, shutdown-time, and dependency limits are explicit and benchmarked rather than left at host defaults.

`systemd` proves only process supervision. It may start/restart a binary, enforce resource limits, and expose liveness, but it cannot set a grid lifecycle, grant command authority, call a trading resume path, edit a store, or represent successful reconciliation. Every start still follows the canonical frozen startup, exclusive-lock, replay, cancellation, reconciliation, and operator-authorization workflow. Canonical journal evidence remains application-owned; supervisor logs are diagnostic evidence only.

The application preserves a deliberate container migration seam:

- one stable non-daemonizing entry point per gateway/runtime role;
- explicit read-only configuration and credential inputs plus separate declared writable paths;
- signal-driven bounded shutdown and machine-readable liveness/readiness surfaces independent of `systemd`;
- no domain, accounting, risk, command, recovery, or state-path rule implemented in a unit file;
- dependency-locked, reproducible release artifacts whose identity can later become an OCI image identity; and
- infrastructure adapters for service supervision and secrets that do not enter the deterministic core.

Docker Compose MAY replace native packaging in a later increment if image portability, release reproducibility, host isolation, or operating experience justifies its daemon/storage overhead. The change is not automatic after a VM resize and does not permit databases, identities, or modes to be merged. It requires an evidence-impact assessment plus repetition of shutdown/crash/restart, exclusive-lock, resource-headroom, 24-hour load, recoverable-point, restore/RTO, secret isolation, monitoring/dead-man, and deployment rollback tests. Strategy/backtest evidence may remain reusable only where the change is proven unable to affect decision semantics; online operational qualification is rerun.

Declined for the MVP:

- Docker Compose immediately, because daemon/image/mount/logging overhead and recovery indirection spend scarce B1ms capacity before a measured need;
- Container Apps, ACI, or App Service, because persistent SQLite/WAL authority, three independently supervised processes, fixed egress, and exact recovery sequencing become more complex or require a different persistence design; and
- one combined service for lower overhead, because it violates the already accepted gateway/Paper/Testnet authority isolation.

### Decision 2: one non-zone-pinned Germany West Central failure domain

Selected by the operator on 2026-07-18: deploy one non-zone-pinned VM in Germany West Central. Azure may place it in available regional capacity; the deployment definition does not require a named availability zone. The VM and its E6 LRS disk remain one failure domain. Platform healing may restart or relocate the VM, but it is not application failover and every replacement follows frozen recovery.

Hot ZRS Blob is deliberately outside the VM/disk failure domain and retains verified recoverable points and sealed evidence synchronously across regional availability zones. It does not make the running application highly available and does not protect against a whole-region outage, operator deletion, invalid retention policy, or an unpublished/unverified local object. The application RPO starts only at verified publication.

After VM/disk loss, IaC recreates the node in available Germany West Central capacity and restores it from a verified Blob recoverable point. The 60-minute RTO applies to this in-region frozen-service recovery. It does not apply to an unavailable region. The external monitor must distinguish process/VM loss, Azure resource-health impairment, storage impairment, and regional unavailability rather than repeatedly attempting blind provisioning.

Deployment preflight must prove subscription quota and allocatable capacity for B1ms plus the B2als_v2/B2as_v2 fallbacks. If Germany West Central cannot supply the selected or required fallback SKU, the system stays undeployed/frozen until the operator explicitly approves another region after price, Binance latency, storage redundancy/features, access path, data boundary, recovery, monitoring, and evidence effects are reassessed. A script may report alternatives but cannot choose a new region automatically.

Declined alternatives:

- pin one VM to a named zone, because location specificity does not create redundancy and may reduce scarce B1ms/fallback capacity;
- treat ZRS Blob as application HA, because it protects sealed objects rather than executing a fenced runtime; and
- multi-zone/cross-region standby, because safe replicated state, fencing, failover, and split-authority prevention form a different, higher-cost architecture outside the first MVP.

### Decision 3: no swap and a complete capacity-qualification record

Selected by the operator on 2026-07-18: the qualifying node has no configured swap. B1ms must fit in real RAM with measured safety headroom rather than use disk as hidden memory. Deployment verification proves the swap set is empty after provisioning and reboot. The node must retain at least 384 MiB host-available memory at the worst representative point after OS/agent needs, all three services, SQLite/cache/staging, required monitoring, and one permitted bounded background phase. This is a qualification minimum, not a target for routine consumption.

Each service receives measured `MemoryHigh`/`MemoryMax`-style budgets and the host retains an unallocated reserve. Optional diagnostics, export, and background work yield first. Pressure that threatens admission, journal, cancellation, reconciliation, incident, recovery, or evidence capacity invokes the already accepted degraded/frozen behavior; it never enables swap, drops evidence, merges services, or raises a limit without review. Any OOM, service memory-limit kill, sustained memory/CPU/I/O pressure, lost headroom, CPU-credit exhaustion trend, or safety/objective breach rejects B1ms and requires the declared resize/retest path.

The Azure temporary disk may hold only explicitly classified reproducible scratch/cache data. It cannot hold SQLite/WAL, journal/outbox, runtime locks, credentials, the only capture/evidence copy, recoverable points, manifests, incident state, or anything required after reboot/redeploy. A deliberate temporary-disk-loss test must have zero domain, accounting, evidence, or frozen-recovery effect.

Every 24-hour benchmark and material operating review produces a sealed **capacity qualification report**. It binds:

- VM/SKU, image/kernel, disk/storage/network profile, release/build/package/configuration identities, enabled services, quotas, and exact workload/scenario interval;
- host and per-service CPU utilization/time/throttling, B-series credits remaining/consumed/trend, resident/virtual/peak memory, host available memory, cgroup pressure/limits, page faults, OOM/kill/restart facts, descriptors, tasks/threads, and event-loop lag;
- disk used/free/reserved bytes, inode-equivalent, IOPS, throughput, latency, queue/pressure, transaction estimate, SQLite/WAL/checkpoint behavior, capture/segment/compaction volume and duration, and predicted time to unsafe reserve;
- network connection continuity, reconnects, ingress/egress, DNS/time state, WebSocket lag/gaps, REST latency/rate limits, and operator/control-path availability;
- admitted backlog/rate/age, journal commit p50/p95/p99/max/count, event-to-commit and dispatch-ready-to-attempt latency, reconciliation duration/freshness, command unknowns, and every missed or near-missed deadline;
- backup working-set peak, point creation/compression/upload/verification duration, protected processing lag, Blob retry/cost/volume, restore/replay/invariant/reconciliation phase timings, and achieved RPO/RTO;
- structured diagnostic event codes, warning/critical incidents, external heartbeat/alert results, canonical evidence identities, and exact references to detailed retained logs/journal/market evidence; and
- every hard gate and threshold with actual value, provenance, missing/invalid sample classification, result, reviewer, decision time, rationale, and next action.

Benchmark resource series are sampled frequently enough to expose bursts (initially five seconds, with higher-frequency application latency histograms); ordinary Azure Monitor export remains curated at the accepted cadence and ingestion budget. Detailed structured logs, resource series, and supporting evidence are sealed to Blob and downloadable into Studio. Log Analytics holds bounded operational queries/alerts, not a duplicate of every journal/market/debug record.

The report outcome is exactly `B1MS_ACCEPTED`, `RESIZE_REQUIRED`, or `INCONCLUSIVE_RERUN`. A missing/invalid decision-relevant measurement can never produce acceptance. Any single hard safety, correctness, OOM, RPO, RTO, isolation, evidence, or deadline failure produces `RESIZE_REQUIRED` when capacity is a plausible cause, while non-representative/instrumentation failure produces `INCONCLUSIVE_RERUN`. The operator sees the complete evidence and approves the infrastructure change, but cannot override a hard failure to keep B1ms.

The first resize is B2als_v2 (2 vCPU/4 GiB); B2as_v2 (2 vCPU/8 GiB) is next. Resizing is a planned frozen restart and requires the complete representative benchmark, restart/replay/reconciliation, recoverable-point, restore/RTO, monitoring/dead-man, and cost evidence again. Historical B1ms reports remain immutable for comparison.

Declined alternatives:

- emergency or ordinary swap, because it can turn an honest memory failure into unpredictable I/O latency and hide an undersized node;
- an average-only dashboard or one peak-memory number, because CPU credits, disk contention, queues, deadlines, backup, and recovery can reject a VM whose average RAM looks acceptable; and
- sending every detailed record to Log Analytics, because canonical evidence belongs in the journal/Blob and unbounded ingestion would add cost/cardinality without improving the decision.

### Decision 4: one Standard static public IPv4 as the declared outbound identity

Selected by the operator on 2026-07-18: attach one Standard static IPv4 directly to the VM NIC. It is the lowest-cost explicit outbound path (about EUR 3.20/month in the current snapshot) and is the sole declared source identity for Binance REST and WebSocket traffic from this deployment. The applicable Binance API-key restriction allowlists this address; the deployment manifest, evidence, monitoring, and operator view all expose the expected and observed outbound identity.

The IP resource is provisioned and retained through infrastructure as code. Startup/readiness and periodic checks compare the observed outbound address with the declared address and Binance credential scope. A mismatch, missing address, or inability to verify it prevents new exposure and raises an operational incident; it never falls back to an implicit or dynamic address. Deliberate IP replacement requires frozen runtimes, operator approval, Binance allowlist update, connectivity/credential verification, and an immutable configuration/evidence update before any resume decision.

The subnet is private-by-default and the NSG denies inbound traffic except the separately accepted operator/administration path. Attaching a public IP does **not** authorize a public control-gateway, Studio, database, metrics, or runtime endpoint. Required exchange, Blob, Key Vault, monitoring, package/update, DNS, and time traffic is explicitly classified and measured; detailed destination restrictions and failure behavior belong to the security specification. Connectivity qualification covers long-lived Binance streams, REST, reconnect/rotation, DNS and time health, rate limits, egress volume/cost, and loss/recovery of the outbound path.

Declined alternatives:

- NAT Gateway plus a Standard public IP, because its additional fixed and per-data cost and SNAT scale are unnecessary for one low-connection-count VM, while a separate protected operator path would still be required;
- Azure Firewall-managed egress, because its fixed cost and inspection/operations surface are disproportionate for this personal MVP; and
- default or dynamic outbound access, because it is implicit, unstable for Binance IP allowlisting, and incompatible with the declared private-subnet boundary.

### Decision 5: source-restricted, key-authenticated SSH for administration and Studio tunnelling

Selected by the operator on 2026-07-18: ordinary OpenSSH over the VM's Standard static public IPv4 is sufficient for both server administration and the encrypted Studio-to-gateway tunnel. The NSG admits TCP 22 only from the operator's currently declared public source IP and denies every application/database inbound port. Studio connects to a laptop-loopback address forwarded by SSH to a gateway listener bound only to VM loopback/private scope; the control gateway, databases, runtime health endpoints, dashboards, and metrics never become public listeners.

SSH login uses a modern passphrase-protected private key held by the operator; the VM holds only its public counterpart. Password authentication and direct root login are disabled before qualification. The passphrase protects the local private key and is not a remotely accepted VM password. Administrative privilege uses an individually attributable non-root account and controlled elevation. SSH and privilege events are retained as bounded security diagnostics without logging private keys, passphrases, gateway tokens, or venue secrets.

The access runbook covers initial host-key verification, expected fingerprint/configuration identity, tunnel establishment and failure, session termination, a changed operator source IP, lost/compromised key revocation, replacement-key enrollment, Azure-side emergency recovery, and proof that a lockout can be recovered without enabling broad or password access. Exact key algorithm, rotation interval, gateway authentication protocol, session limits, hardening, and emergency-recovery authorization remain owned by the security specification.

SSH network access never grants trading authority. The gateway still applies its accepted authentication, command authorization, idempotency, expiry, concurrency, re-authentication, audit, and explicit resume rules. The Paper, Testnet, and future live processes do not accept direct SSH commands as trading commands.

Declined alternatives:

- persistent password-based SSH, because a remotely guessable/reusable credential is not an acceptable qualification boundary for a host that may later access live venue credentials;
- Azure Bastion, because its extra resources, feature/SKU constraints, and recurring cost are unnecessary for the accepted single-operator boundary; and
- point-to-site VPN, because its continuously billed gateway and client/certificate lifecycle add complexity without a current multi-user/private-network requirement.

### Decision 6a: one GPv2 account with private purpose boundaries and Hot ZRS

Selected by the operator on 2026-07-18: use one Standard general-purpose v2 storage account with Hot ZRS Blob for newly published objects. ZRS synchronously maintains each object across three or more availability zones inside Germany West Central. Therefore a loss of one zone need not remove the verified Blob objects used to recover the single VM/LRS-disk failure domain. ZRS is storage redundancy, not a standby trading runtime: it does not keep the process running or provide automatic application failover.

Separate non-public Blob containers and explicit prefixes partition Paper, Testnet, future live, recoverable points, market/journal evidence, diagnostics/capacity reports, incident/promotion bundles, and published manifests. A Blob container is a logical storage bucket, not a Docker/application container. Each object carries exact runtime, run, evidence, schema, retention, and checksum identities; name/prefix separation is never treated as sufficient authorization or integrity evidence.

The account disables anonymous public access. Access uses declared Azure identity/RBAC over TLS; the control gateway has no general Blob data permission. Active SQLite/WAL, open journal/capture segments, runtime locks, credentials, and compaction work never live in Blob. A closed object becomes authoritative remotely only after the accepted seal, length/checksum/reader verification, and manifest-publication boundary. Growth, operation volume, tier, protected lag, failures, and cost feed monitoring and the capacity qualification report.

ZRS does not protect against valid-but-wrong deletion, overwrite, bad lifecycle policy, compromised authorization, storage-account deletion, corrupted data uploaded as valid, or loss of the whole Azure region. Provider deletion/version safeguards are therefore a separate decision, while the accepted manifest, verification, retention, hold, restore, and regional-scope rules remain mandatory.

Declined alternatives:

- separate storage accounts per runtime, because they multiply configuration, policy, monitoring, recovery, and identity wiring before the one-VM MVP can obtain meaningful process-level Azure-identity isolation from them; and
- LRS Blob, because its copies remain in one datacenter and can share a datacenter-loss scenario with the VM/LRS disk, contrary to the accepted zone-separated recovery intent.

### Decision 6b: 30-day provider recovery with versioning, soft deletion, and an account lock

Selected by the operator on 2026-07-18: enable Blob versioning, 30-day Blob soft deletion, 30-day container soft deletion, and an Azure `CanNotDelete`-style resource lock on the storage account. An accidental overwrite or object/container deletion normally remains provider-recoverable for 30 days, while deleting the storage-account resource requires a separate authenticated and audited lock-removal action. These controls complement ZRS; they do not replace the accepted application catalogue, content-addressed identities, checksums, reader verification, retention classes, preservation holds, or restore tests.

The catalogue tracks the exact current and former object-version identities. A soft-deleted or prior Azure version is classified `PROVIDER_RECOVERABLE`; it is not an active valid recovery point or evidence object merely because Azure can return its bytes. Restore selects only a manifest-referenced, checksum-verified, reader-compatible version. RPO is satisfied only by a currently verified published recoverable point, never by hoping a deleted version can later be found.

Lifecycle and secure deletion enumerate the exact object, version, snapshot, and container state before action. Expected deletion is not complete until the configured provider-recovery window expires, at which time the deletion tombstone can record `CONFIRMED_EXPIRED`. Capacity and cost monitoring includes retained previous and soft-deleted versions so protection overhead cannot become invisible. Qualification deliberately tests overwrite recovery, object/container deletion, version selection, partial cleanup, account-lock enforcement/removal, and restoration without weakening permissions.

No account-wide WORM/immutable-retention policy is applied in the MVP. Canonical evidence is immutable by application identity, hash, append/publication semantics, authorization, and audit, while the 30-day provider recovery layer protects mistakes. Broad WORM is deferred because an incorrect retention policy, sensitive-data accident, invalid test upload, or excessive object can become impossible to correct until expiry. The later security threat model may require selective WORM for narrowly scoped live/promotion/critical bundles; that would require separate containers, policy/recovery tests, and explicit cost/retention approval.

Declined alternatives:

- WORM for every sealed object, because its operational rigidity and policy-error consequences are disproportionate before a demonstrated tamper-resistance requirement; and
- application retention without versioning, soft deletion, or a resource lock, because ZRS would faithfully replicate a valid-but-wrong deletion and an account mistake could remove every zone copy.

### Decision 6c: Hot publication, selective Cool tiering after 30 days, and no Archive

Selected by the operator on 2026-07-18: every verified object is first published into Hot ZRS. An eligible closed evidence or diagnostic object may move to Cool ZRS after 30 days when its exact retention class, references, preservation holds, incident/promotion use, recovery role, and minimum-tier-duration constraints permit it. Current and fallback recoverable points, active incident/promotion/hold dependencies, incomplete bundles, and anything required to meet the 60-minute RTO remain Hot.

Azure lifecycle automation may propose or perform a class-aware tier transition for an exact eligible object/version, but it never deletes merely because an age or prefix matches. Deletion remains an application-catalogue plan that checks all references, holds, recovery coverage, provider versions, and policy identity immediately before execution. A changed lifecycle rule is versioned, reviewed, dry-run against the catalogue, cost/impact reported, and tested on non-authoritative objects before production application.

Every transition records exact object/version, source and target tier, eligibility proof, policy identity, request/completion time, provider outcome, minimum-duration/retrieval consequences, and estimated/actual cost. Monitoring includes Hot/Cool bytes and growth by class, transitions, early-deletion/retrieval charges, failed moves, objects unexpectedly left Hot, and time until budget/capacity thresholds. Studio displays tier, completeness, price/latency consequence, and expected availability before retrieval.

Archive is excluded from the MVP. Its offline rehydration delay, additional operation/cost constraints, and recovery paths would complicate interactive debugging and evidence access. It can be reconsidered only after measured long-term growth justifies it, exact archive-eligible classes are proven irrelevant to the 60-minute RTO and active investigations, Studio represents offline retrieval correctly, and rehydration/failure drills pass.

Declined alternatives:

- keeping all retained data Hot, because it needlessly increases accumulating storage cost for rarely accessed long-lived evidence; and
- adding Archive immediately, because measured volume has not justified the extra state, delay, cost, and recovery complexity.

### Decision 6d: subnet-restricted Storage service endpoint

Selected by the operator on 2026-07-18: enable the `Microsoft.Storage` service endpoint on the declared runtime subnet and configure the storage firewall with default action `Deny` plus an allow rule for only that subnet. Blob traffic follows the Azure backbone and the subnet supplies the admitted network identity. The Blob service still has a public service endpoint; this design is not called Private Link or a private endpoint. Requests arriving from other networks are rejected even if they know the storage-account name.

Network admission is only one control. Every permitted request still requires TLS, the expected managed identity, least-privilege RBAC data action, correct runtime/purpose scope, and application object/manifest validation. Conversely, possession of a valid Azure identity outside the accepted network does not bypass the firewall. Anonymous access, account keys in application configuration, broad SAS credentials, direct laptop/Studio Blob access, and blanket trusted-Microsoft-service exceptions are disabled. A named required Azure service exception needs its own exact permission, risk, expiry, evidence, and acceptance test.

Studio requests sealed bundles through the authenticated control gateway, which applies the accepted authorization, manifest, redaction, and audit rules. A weekly isolated restore or monthly disaster drill admits its declared disposable subnet through a versioned, time-bounded infrastructure change; access is removed and tested after the drill. Rebuilding the production VM into the declared subnet restores its network eligibility but never its trading authority.

Qualification proves: allowed-subnet plus allowed-identity success; wrong subnet rejection; wrong identity rejection; public/anonymous rejection; endpoint/firewall drift detection; upload/verification and restore behavior; temporary drill admission/removal; audit visibility; and the accepted evidence-protection response if the network path threatens the 15-minute RPO. Service-endpoint state, firewall rules, access failures, request latency, protected lag, and relevant Azure activity become capacity/incident evidence.

Declined alternatives:

- a billed Private Endpoint, because its private DNS, endpoint resource, monitoring, and recovery dependency are not justified for the first personal single-VM threat boundary; and
- an all-networks public endpoint protected only by identity, because the no-additional-charge subnet restriction materially narrows exposure.

Primary sources: [Azure service endpoints](https://learn.microsoft.com/en-us/azure/virtual-network/virtual-network-service-endpoints-overview), [Azure Storage firewall rules](https://learn.microsoft.com/en-us/azure/storage/common/storage-network-security), and [Azure Storage private endpoints](https://learn.microsoft.com/en-us/azure/storage/common/storage-private-endpoints).

### Decision 6e: automated benchmark-derived growth forecasts plus Azure billing alerts

Selected by the operator on 2026-07-18: combine detailed automated operational monitoring with Azure invoice/budget alerts. The 24-hour qualification establishes approved per-class daily bytes, object/version count, operations, Hot/Cool/soft-deleted volume, upload/verification latency, and monthly cost forecast. Warn when trailing 24-hour growth exceeds 150% of the qualified daily baseline or projected storage cost exceeds its approved budget; require operator review at 200%, on unexplained/unclassified growth, or when version/lifecycle behavior invalidates the forecast. RPO, verification, local-disk, or evidence-integrity danger remains a critical safety incident under existing rules. Alerts never delete evidence or stop trading merely to save money.

Option 1 has explicit automated ownership and does not add a fourth trading runtime:

- each Paper/Testnet/future-live runtime publishes its own bounded application measurements for protected position, local backlog, evidence production, queue age, and safety-critical storage failures alongside canonical durable facts;
- short-lived backup, offload, verification, retention, and tiering jobs publish exact manifests, byte/operation counts, timings, versions, and outcomes;
- Azure platform metrics and the Azure Monitor Agent supply external VM, disk, process/service, network, and Storage measurements at the accepted bounded cadence;
- a lightweight non-trading capacity-evaluator job, scheduled by `systemd`, joins those declared inputs hourly, calculates growth/cost forecasts and threshold results, and seals the daily and 24-hour qualification reports; it has no Binance credential, trading command, resume authority, or permission to delete evidence;
- Azure Monitor evaluates the curated external alert conditions and delivers notifications, while complete detailed evidence is retained in the journal/Blob and downloaded into Studio for explanation; and
- the operator reviews warnings and approves any resize, retention, lifecycle, logging, or budget change. The operator is not expected to manually collect or calculate routine measurements.

Failure, lateness, missing input, or disagreement in the capacity evaluator is itself visible monitoring evidence and cannot produce a healthy/accepted conclusion. Safety-critical RPO, integrity, and local-capacity checks remain continuously enforced by the owning runtime/offload path rather than waiting for the hourly cost evaluator.

Until the representative benchmark replaces the planning assumption, more than 3 GiB/day or a 90-GiB monthly addition raises a provisional warning. These are observation thresholds, not deletion limits or proof that B1ms must resize. Every alert links to the complete capacity/evidence report so a resize, retention fix, compaction fix, logging fix, lifecycle correction, or approved budget change follows the actual cause.

Declined alternatives:

- one fixed Blob byte cap, because it becomes obsolete as valid retention accumulates and cannot distinguish legitimate evidence from duplication, debug excess, versioning overhead, or lifecycle defects; and
- Azure invoice/budget alerts alone, because billing aggregation cannot diagnose protected lag, failed verification/tiering, per-class growth, or local backlog early enough.

### Decision 7: reuse the accepted application recovery protocol; do not add VM Backup

The Azure deployment implements without reopening the recovery contract already selected in the event-journal and runtime specifications: complete transactionally consistent SQLite online backups at a nominal ten-minute cadence when protected state advances; verification and Blob publication within the 15-minute protected-processing RPO; every verified routine point for 24 hours, one daily for 30 days, and referenced/pre/post-change points as long as required; weekly isolated restore; monthly fresh-VM/disk-loss drill; and complete restore, replay, invariant checks, Binance reconciliation, and operator-accessible frozen service within the 60-minute RTO.

The bounded backup/offload path streams compression/upload without loading the complete database into memory, uses at most 64 MiB working memory initially, runs one recovery-point job per runtime at a time, yields to safety/venue persistence, and does not overlap its heavy phase with market-segment compaction. Exact protected position, source database/journal/configuration/build/schema, object/version/checksum, job/retry, timing, resource, verification, catalogue, and incident evidence is retained. A partial, late, corrupt, unverified, incompatible, or unpublished point never satisfies RPO.

Restore creates no venue authority. It selects a verified compatible point, verifies every dependency, replays the tail, proves accounting/risk invariants, reconciles authoritative Binance orders/trades/balances including late fills, and finishes frozen. Weekly/monthly test targets have no trading-capable credentials. Any RPO/RTO/integrity/replay/reconciliation/isolation failure invalidates qualification until correction and successful retest.

Azure VM Backup remains outside the baseline because an image/snapshot neither proves application consistency nor replaces exact replay and venue reconciliation. It may be reconsidered only as a convenience if measured infrastructure-as-code plus application restore cannot meet RTO; the application recovery protocol remains authoritative either way.

Canonical detail: [event journal and observability recovery contract](event-journal-observability-spec.md#application-recovery-objectives-and-recoverable-points) and [online runtime recovery contract](online-runtime-and-recovery-spec.md).

### Decision 8a: restricted direct Key Vault access for the current credentialed runtime

Microsoft defines the managed-identity security boundary as the Azure resource—in this case the VM—and documents that any client application on that VM able to call IMDS can request a token. Multiple Linux users or multiple user-assigned identities attached to the same VM therefore do not create a provable Azure process-identity boundary by themselves. [VM managed-identity token access](https://learn.microsoft.com/en-us/entra/identity/managed-identities-azure-resources/how-to-use-vm-token), [Azure IMDS security guidance](https://learn.microsoft.com/en-us/azure/virtual-machines/instance-metadata-service).

Selected by the operator on 2026-07-18: do not add a credential-materializer job. Permit direct managed-identity/Key Vault access only for the currently deployed credentialed venue runtime and reviewed root-owned infrastructure jobs. Local firewall policy blocks the control-gateway and Paper service users from the IMDS identity/token endpoint. Paper uses production public market data and has no Binance private/trading secret; the gateway has neither venue secret nor authoritative trading-store access.

In the Paper-plus-Testnet deployment profile, the VM identity has no production/live Binance secret permission. The Testnet runtime retrieves one exact configured Testnet secret version directly from Key Vault at frozen startup or controlled rotation, retains it only in process memory, and never places it in Git, ordinary configuration/environment files, command lines, crash/core dumps, logs, journals, metrics, alerts, backups, Blob, or Studio. Root-owned backup/offload/infrastructure jobs may also use the VM identity for their declared Azure operations; this means a compromise of an IMDS-admitted process may exercise other permissions assigned to that VM identity. That residual single-VM risk is accepted and tested, not described as process-level cloud isolation.

The first live profile is a new live runtime, store, configuration, credential scope, and qualification—not a relabelled Testnet process. Before live credentials are introduced, Testnet runtime authority is stopped/disabled, Testnet Key Vault permission is revoked, the live-only permission/profile is installed while frozen, and denial of the Testnet and every undeclared secret is proven. Testnet and live secrets are never simultaneously readable by this VM identity in the initial MVP. Reintroducing concurrent Testnet/live operation requires a new identity-isolation decision and requalification.

The whole VM, kernel, root authority, and every intentionally IMDS-admitted process remain the admitted cloud-identity trust boundary. Separate Linux users, service units, or multiple managed identities attached to this same VM are defense-in-depth and configuration clarity, not a claim of isolation from root/VM compromise. Any IMDS firewall drift, unexpected token request, undeclared secret access, secret in a prohibited sink, ambiguous credential version, or production permission in a non-live profile is a critical security/qualification failure and triggers revocation/rotation and frozen recovery.

Qualification includes allowed-runtime token/secret retrieval; gateway/Paper/wrong-user IMDS denial; wrong-vault/secret/version/environment denial; Azure-storage permission abuse probes; exact Key Vault audit correlation; startup/restart without Key Vault; mid-run Key Vault loss; version rotation/revocation; secret canaries across every sink/core dump/backup; firewall/reboot persistence; Testnet-to-live permission replacement; and the explicit root/VM compromise assumption. The security specification owns exact firewall rules, runtime memory/core-dump controls, Azure RBAC, Key Vault networking, operator roles, rotation cadence, and incident runbooks.

Declined alternatives:

- a credential materializer, because the operator selected the simpler direct-read path and accepted its documented VM-identity residual risk;
- unrestricted IMDS/Key Vault access for every process, because it violates the gateway/Paper credential boundary; and
- separate VMs per authority, because the stronger Azure-resource boundary multiplies infrastructure and cost before simultaneous isolated live/Testnet operation is required.

### Decision 8b: one shared Key Vault with mutually exclusive environment permission

Selected by the operator on 2026-07-18: use one Standard Key Vault for the deployment, with distinct immutable secret identities/versions and metadata for Testnet and future live credentials. Paper has no Binance credential. Secret names or prefixes are organizational labels rather than a security boundary; exact Azure RBAC data permissions, expected vault/secret/version/environment identity, runtime configuration, and negative tests establish the boundary.

The Testnet deployment permits the VM identity to retrieve only the selected Testnet secret/version. A live secret may later exist in the shared vault, but Testnet deployment evidence must prove it is unreadable. The initial live transition stops/disables Testnet authority, revokes the Testnet secret permission, proves revocation, grants only the selected live secret permission, installs a new live runtime/store/configuration while frozen, and proves every Testnet/undeclared secret remains unreadable before operator activation review. The VM identity never has simultaneous Testnet and live secret read permission in the initial MVP.

The shared vault has soft-deletion/purge safeguards, an infrastructure deletion lock, Azure RBAC rather than legacy broad access policy, versioned network/RBAC/purge configuration, diagnostic audit, and alerts for permission/network/purge changes and every secret access anomaly. Operator/deployment roles that create, version, grant, revoke, recover, or purge secrets are distinct from the VM's narrow data-read role and require the accepted SSH/Azure operator access and audit policy. Secret values remain prohibited from IaC state, Git, deployment output, shell history, tickets, logs, alerts, backups, and Studio.

The accepted consequence is a larger configuration and privileged-operator blast radius than separate vaults: a vault-wide role mistake, privileged account compromise, or vault-level destructive action can affect both environments. Qualification deliberately injects wrong secret names/versions, overbroad role assignments, stale grants, revoked access, environment-transition races, vault recovery, and audit/alert failures. A shared-vault result cannot be described as physical or Azure-resource isolation between Testnet and live.

Declined alternatives:

- separate Testnet/live vaults, because the operator preferred one resource and accepted the documented permission/configuration blast radius; and
- encrypted local files, because they create local encryption-key, backup, rotation, audit, and VM/disk-exposure problems.

### Decision 8c: subnet-restricted Key Vault with a time-bounded operator window

Selected by the operator on 2026-07-18: enable the `Microsoft.KeyVault` service endpoint on the runtime subnet and configure the shared vault firewall to deny data-plane traffic from every network except the declared subnet. Keep the broad trusted-Microsoft-services bypass disabled. Ordinary runtime retrieval follows the Azure backbone and still requires the exact managed identity, object-scoped RBAC permission, vault/secret/version/environment identity, and TLS.

Creating, rotating, disabling, recovering, or inspecting secret versions is an explicit operator workflow. It authenticates the operator under the later security policy, records reason, ticket/change identity, expected secret identities (never values), source IP, expiry, and intended operations; temporarily adds only the operator's current public IP to the vault firewall; performs secret-safe data-plane actions without command-line/history/output leakage; verifies audit and the intended positive/negative access results; removes the IP rule immediately; and independently proves removal. The rule has a short maximum expiry and an external cleanup/alert path if the initiating session disappears.

Ordinary Studio use never opens this window, talks directly to Key Vault, or retrieves/displays a secret. SSH access does not itself grant Key Vault permission. Key Vault control-plane resource changes and data-plane secret actions are distinguished in evidence: successful firewall/RBAC configuration does not prove secret readability, and a readable secret does not prove that firewall/RBAC configuration is least-privilege.

Qualification tests runtime-subnet success; other-subnet/network denial; wrong identity/object/version denial; trusted-service bypass absence; operator-window open/expiry/forced cleanup; changed home IP; interrupted rotation; audit/alert delivery; firewall drift/reboot/redeploy; Key Vault outage; and the accepted frozen/revocation response. No test includes real secret values in evidence.

Declined alternatives:

- a billed Private Endpoint, because the private DNS, operator/recovery path, monitoring, and additional dependency are not justified for the first personal single-VM boundary; and
- a disabled Key Vault firewall with identity-only protection, because it permits attempts from every network despite an available subnet restriction.

Firewall/network permission and Azure RBAC permission are both required and independently tested. Key Vault control-plane operations are distinguished from secret data-plane operations; a successful resource configuration change does not prove that the intended runtime can read—or that an unintended caller cannot read—the secret.

Primary sources: [Key Vault virtual-network service endpoints](https://learn.microsoft.com/en-us/azure/key-vault/general/overview-vnet-service-endpoints), [Key Vault network security](https://learn.microsoft.com/en-us/azure/key-vault/general/network-security), and [secure Key Vault](https://learn.microsoft.com/en-us/azure/key-vault/general/secure-key-vault).

### Decision 8d: resolve `latest` once at frozen startup and pin the exact version for that process

Threat-model assumption supplied by the operator on 2026-07-18: the operator is the only intended human principal permitted to create, modify, enable, disable, or select Key Vault secret versions. No team member, CI job, runtime, Studio client, or deployment automation receives secret-write permission. Strong operator authentication and audit are still required because sole ownership reduces multi-user risk but does not remove accidental input, stale sessions, account compromise, incorrect Binance permissions/IP restriction, or runtime cutover ambiguity.

Selected by the operator on 2026-07-18: runtime configuration names the environment-specific logical secret, and the runtime resolves its enabled Key Vault `latest` version exactly once during frozen process startup. It immediately records the exact non-secret vault/secret/version identity and approved credential fingerprint in the immutable startup/configuration evidence, then retains that credential only in memory for the process lifetime. It never polls, refreshes, or hot-reloads `latest` while running. Thus the operator does not type a version identifier, but every decision and side effect still has one exact credential-version boundary.

Every process replacement already starts frozen. If the resolved version differs from the last accepted version, the runtime treats startup as a credential-change workflow: validate expected Testnet/live environment and account, minimal Spot permissions, withdrawals disabled, accepted static outbound-IP restriction, time/authenticated reads, and private-stream behavior; reconcile existing orders, trades, fees, balances, and unknown commands; and show the exact non-secret change evidence. Invalid, unavailable, ambiguous, disabled, overprivileged, wrong-environment, or audit-incomplete credentials leave the runtime frozen. No secret creation or successful validation grants resume authority; explicit operator review remains required.

For planned rotation, the operator creates and stores the replacement while the old credential remains usable. The next deliberate frozen restart resolves the replacement. The old Binance key is revoked only after the replacement passes validation/reconciliation and all in-flight or outcome-unknown requests under the old identity are resolved. If replacement validation fails, the runtime remains frozen and the operator may disable the bad version so a subsequent frozen start resolves the prior enabled version. Emergency compromise revokes first when containment demands it, accepts loss of ordinary overlap/rollback, and requires full reconciliation before any new authority.

The runtime records key/version/fingerprint identities, clocks, validation/permission results, request/private-stream generation boundaries, reconciliation, operator decision, and revocation outcome without ever recording the API secret, signature, token, signed query, or reusable authentication material. Testnet proves successful rotation, failed-new-version rollback, crash at every cutover boundary, Key Vault unavailability, old/new in-flight outcomes, and no hot reload before the mechanism can qualify for live.

Declined alternatives:

- hot-reloading `latest` while trading, because even a sole authorized writer would create an ambiguous in-process authority boundary and break immutable replay evidence;
- requiring the operator to manually copy exact Key Vault version identifiers, because frozen one-time resolution provides the same process-lifetime identity with less error-prone operation; and
- revoking the old key before replacement validation during ordinary rotation, because it makes open orders temporarily unmanageable and removes rollback.

Exact routine rotation frequency and compromise-response timing remain in the security specification; this deployment decision fixes the safe activation seam.

### Decision 9: deploy the already accepted journal, monitoring, alert, and external dead-man contract

The Azure deployment adopts the completed [event journal and observability specification](event-journal-observability-spec.md) without reopening its semantics. Each authoritative runtime retains its atomic canonical journal, structured redacted diagnostics, metrics, health/readiness, incident lifecycle, and evidence identities locally; verified closed evidence and reports offload to Blob. Azure Monitor receives a deliberately bounded operational projection rather than every journal, market-data, order, fill, trace, or DEBUG record.

Azure platform metrics plus the Azure Monitor Agent and one versioned Data Collection Rule collect the accepted host/service heartbeat, CPU/credits, memory/pressure, disk/IO/capacity, network, selected syslog/service failures, and bounded application operational signals. Metric labels remain bounded; material event identities stay in the journal/Blob. Log Analytics ingestion is budgeted below the accepted allowance during qualification, while complete detailed evidence remains downloadable through the gateway into Studio. Missing monitoring data is classified rather than interpreted as zero or healthy.

An evaluator outside the runtime process/VM observes the declared 30-second heartbeat and opens/delivers the accepted critical incident when two elapsed minutes pass without it. Email plus mobile notification delivery, provider failure, duplication, delay, redaction, and recovery are tested; a notification cannot acknowledge an incident, grant resume, or contain secrets/exact sensitive trading state. Azure activity/resource-health, VM availability, process/service, RPO/protected-lag, disk/resource, Blob/Key Vault, drift, budget, and external dead-man conditions remain distinct enough to diagnose.

Canonical durable evidence and local fallback diagnostics survive temporary replaceable monitoring-sink failure within the accepted diagnostic-degradation boundary. Loss of authoritative evidence, required recoverable-point protection, external critical supervision, or safe local capacity invokes the accepted evidence-protection freeze. Alerts never auto-resize, auto-delete evidence, change risk limits, or resume trading. All monitoring resource use and ingestion feeds the B1ms capacity report.

### Decision 10a: Azure Bicep as the canonical infrastructure definition

The canonical repositories currently contain no production Bicep/Terraform deployment to preserve. Legacy deployment notes and sketches remain requirements input only.

Selected by the operator on 2026-07-18: use Azure Bicep as the canonical declarative infrastructure definition, with thin reviewed Azure CLI/PowerShell wrappers only for validation, preview, deployment invocation, evidence capture, and operational sequencing. Azure Resource Manager retains resource state, so the MVP does not add a Terraform-style state file/backend/locking/recovery system. Every infrastructure change receives a non-mutating `what-if` preview; unevaluated/ignored/ambiguous preview results are explained or block application rather than being assumed safe.

Use cohesive Bicep modules for subscription/resource-group policy and budget seam, network/NSG/static IP/service endpoints, VM/disk/identity, Storage/containers/firewall/lifecycle/protection, Key Vault/firewall/RBAC/protection, monitoring/DCR/alerts/dead-man, and declared outputs. Environment/profile parameter files cover Paper-plus-Testnet and later live without branching resource semantics. Parameters and outputs are typed, validated, non-sensitive, and contain only Key Vault references/identities—not secrets, Binance keys, SSH private material, tokens, or signed URLs.

Pin Bicep/Azure CLI or PowerShell versions and Azure resource API versions in the deployment manifest. Run formatting/lint, compile, module/unit/policy checks, secret scanning, normalized snapshot comparison, preflight validation, and `what-if` before apply. A deployment records source commit, module/parameter/tool identities, operator/change identity, exact preview, approved exceptions, Azure deployment/resource identities, outputs, duration, result, post-deploy drift/health/permission denials, cost forecast, and frozen application posture. Failed/partial deployment never grants trading authority and is repaired idempotently or rebuilt under the runbook.

Portal/emergency changes are not a second configuration source. They are time-bounded, audited exceptions followed immediately by Bicep reconciliation or explicit reversion and a clean `what-if`. Resource deletion, replacement, role widening, firewall opening, IP change, Key Vault/Storage protection weakening, and destructive deployment-mode changes require explicit operator review and applicable preservation/recovery evidence. Application data, runtime databases, and secret values are never managed as Bicep state.

The same definitions provision a fresh compatible node for the monthly disaster drill and must meet the 60-minute frozen RTO. Bicep deployment success alone is insufficient: OS/bootstrap, application artifact, restore, replay, invariant checks, Binance reconciliation, access, alerts, and resource qualification still have to pass.

Declined alternatives:

- Terraform, because its state/backend/provider/recovery surface adds little value to this Azure-only one-node MVP and no working canonical Terraform implementation exists to preserve; and
- imperative provisioning scripts as the authority, because custom ordering, drift, retries, update preview, and partial-failure recovery would be harder to review and reproduce.

Primary sources: [What is Bicep?](https://learn.microsoft.com/en-us/azure/azure-resource-manager/bicep/overview) and [Bicep what-if](https://learn.microsoft.com/en-us/azure/azure-resource-manager/bicep/deploy-what-if).

### Decision 10b: the operator alone applies reviewed Azure changes from the trusted laptop

Selected by the operator on 2026-07-18 and clarified by the local-first boundary: the sole operator applies infrastructure changes from the trusted laptop after reproducible local validation and an interactive `what-if` review. GitHub stores reviewed Bicep, non-secret parameter files, application source, lock files, and release metadata as version control and an off-laptop source copy; GitHub CI is optional later and is not an MVP dependency. A push never changes Azure, restarts a runtime, or grants trading authority.

For each change, the operator checks out and records the exact reviewed commit, uses the pinned deployment toolchain, authenticates interactively to Azure under a least-privilege deployment role, regenerates and reviews `what-if`, explicitly accepts any explained exceptional result, applies the exact approved definition, and captures the deployment and post-check evidence required by Decision 10a. Apply scripts refuse a dirty tree, source/parameter mismatch, stale preview, secret-bearing input, non-approved subscription/resource group/profile, or missing frozen posture. A separate privileged emergency path is time-bounded, audited, and reconciled back into Bicep; it is not ordinary deployment authority.

The deployment role may change only the declared MVP resource scope and may not create or read Binance secrets, authorize trading, acknowledge operational incidents, or issue runtime commands. Key Vault secret administration remains the separately accepted operator-only workflow. Infrastructure success leaves all new or replaced services frozen until application installation, restore/replay, reconciliation, health, monitoring, qualification, and explicit runtime-resume gates pass.

Disaster recovery therefore depends on the operator retaining tested access to a protected repository copy, the pinned toolchain/bootstrap instructions, Azure login and recovery factors, SSH key/recovery procedure, and deployment evidence. The monthly fresh-node drill proves these dependencies within the accepted 60-minute frozen RTO; an absent operator is not hidden by claiming unattended recovery.

Declined alternatives:

- protected manually dispatched GitHub Actions with workload-identity federation, because it adds a GitHub-to-Azure write path, federation/environment controls, hosted-runner trust, and GitHub availability to a personal MVP without removing the required operator decision; and
- automatic deployment from `main`, because a source-control action must not directly mutate or restart a trading environment.

Application artifact delivery and service restart/rollback are specified separately in Decision 10c. This infrastructure-apply decision does not permit the VM to `git pull` mutable source.

### Decision 10c: locally qualified release bundles are uploaded through SSH

Selected by the operator on 2026-07-18: the trusted research workstation performs the MVP's application build and every required release test locally, then uploads the exact qualified immutable bundle through the already accepted SSH path. GitHub Actions is neither required nor an Azure deployment authority. The VM has no GitHub credential, does not clone source, does not resolve dependencies from the public internet during installation, does not compile application code, and does not run historical backtests.

One versioned local release command is the reproducible gate. It refuses a dirty/unidentified source tree; binds the exact Git commit, dependency lock, toolchain, target OS/architecture/Python ABI, configuration-schema and database-schema compatibility; runs the declared canonical unit, property, integration, replay/accounting, adapter-contract, migration, lint/type, dependency, and secret checks; and stores complete results. Legacy/reference-repository suites are diagnostic until their behavior is deliberately migrated into the canonical foundation; they cannot silently become a release gate or block an unrelated canonical release.

Only after every applicable canonical gate passes does the command build an application wheel plus a target-compatible offline dependency wheelhouse, migrations, schemas, service entry points, install/health scripts, and a non-secret manifest into one release archive. It computes and records the archive byte length and SHA-256 digest. A later independent signature/attestation or GitHub CI replication may strengthen producer assurance, but it cannot replace the local exact-input/result evidence or gain Azure/trading authority without a new decision.

The deployment command verifies the archive and manifest on the laptop, confirms the intended Azure subscription/environment/runtime and frozen posture, uploads to a non-active staging path over SSH, and makes the VM independently verify digest, size, target, release identity, permissions, available capacity, schema/migration plan, and absence of forbidden content. The VM installs offline into a new versioned read-only release directory beside the retained current and rollback releases; persistent databases, journals, configurations, secrets, captures, logs, and evidence remain outside release directories.

Before an affected credentialed runtime stops, it first freezes new exposure, persists authoritative state, reconciles outstanding venue outcomes, and seals the pre-change checkpoint. A required database migration receives a verified recoverable point and tested forward/rollback classification. An atomic stable pointer selects the staged release only after preflight. `systemd` restarts the minimum affected services in declared dependency order, and every replacement process starts frozen.

Post-install validation proves process/host health, replay and accounting invariants, configuration/schema identity, isolation and permission denials, market-stream recovery, venue reconciliation where applicable, recoverable-point/monitoring/dead-man operation, and B1ms headroom. The evidence binds the source commit, bundle digest, configuration version, database version, runtime instance, operator action, checks, incidents, and result. Installation acceptance and trading resume are separate operator decisions; a healthy release cannot resume itself.

Failure keeps the runtime frozen. Rollback selects the retained compatible release and, when required, its compatible recoverable database point, then repeats replay, invariants, reconciliation, health, and explicit resume review. An interrupted upload or partial install cannot change the active pointer. Each initial increment binds its Production-Data Paper Run and Testnet Run to the same exact qualified bundle digest and strategy candidate rather than separate builds of nominally equivalent source. Their mode profiles, stores, pointers and restart scopes remain isolated. A later live promotion likewise uses the exact already-qualified candidate bundle; bytes under one release identity never differ.

The laptop is therefore required for planned application/infrastructure changes and the accepted operator-driven fresh-node recovery, but not for uninterrupted Azure Paper/Testnet/live operation. Loss or shutdown of the laptop leaves an already healthy Azure runtime operating and externally monitored; it prevents new deployments and local analysis until the workstation/repository/toolchain/access are restored. The monthly fresh-node drill must prove that protected GitHub source, pinned workstation bootstrap, release evidence/bundle retention, Azure login, and SSH recovery can still meet the 60-minute frozen RTO.

Declined MVP alternatives:

- GitHub CI as a mandatory build/release dependency, because the operator prefers local engineering and a personal MVP does not need another execution authority; it remains a useful later independent verification layer;
- publishing releases to a private Blob release container for VM pull, because the already accepted SSH path is sufficient and avoids release-publisher/reader permissions in the first increment; and
- building from a VM Git checkout, because mutable source, remote dependencies, build tools, and branch state would make production installation less reproducible and enlarge the online attack/resource surface.

### Decision 10d: retain the active and rollback qualified release bundles in private Blob

Selected by the operator on 2026-07-18: retain exact recovery copies of the accepted active release and its immediate compatible rollback release in a private `releases` class/prefix in the already selected Blob account. This is recovery retention, not Blob-pull deployment: ordinary delivery remains a locally qualified bundle uploaded through SSH, and neither Blob availability nor object presence grants install, activation, restart, or trading authority.

A **qualified release bundle** is the immutable installable archive produced from one exact clean source commit only after every applicable canonical release gate passes. It contains the application wheel, offline locked dependency wheelhouse, migrations/schemas and install/health entry points plus a non-secret manifest. Its evidence binds source commit, dependency/toolchain and target identities, test/scan outcomes, configuration/database compatibility, byte length and SHA-256 digest. Qualification says “this exact archive passed the declared engineering gates”; it does not say that a strategy is profitable, that a particular runtime configuration is approved, that installation succeeded, or that trading may resume.

Before a newly installed frozen release can be accepted as active, a narrowly scoped reviewed release-archival job publishes its exact archive, manifest and required qualification evidence under a content-addressed release identity, reads them back, verifies length/digest/manifest and records the exact Blob version/object identities. The application runtimes and Gateway receive no general release-container permission. The archive contains no venue secret, runtime database, journal, account state, operator credential or environment-specific authorization.

Blob versioning, 30-day soft deletion, account deletion lock, default-deny network policy, managed identity/RBAC, monitoring and evidence-catalog controls apply. Active and rollback objects remain Hot and deletion-ineligible while referenced by deployment, recovery, incident, audit or hold state. After a newer release is accepted and its rollback path is proven, the former rollback may become catalogue-eligible under the accepted retention workflow; no age/prefix rule silently deletes it. Storage bytes, object/version count, publication/readback latency, failures and projected cost join the accepted capacity/cost evidence.

Failure to publish or verify the candidate bundle may leave it staged and frozen but blocks its acceptance and trading resume. During recovery, the operator authorizes the exact recorded digest/version to be restored through the reviewed frozen recovery workflow; the VM verifies it again, installs beside other releases, restores a compatible recoverable data point where required, and repeats replay, accounting invariants, health, permission denial and venue reconciliation. There is no “latest bundle” auto-selection.

Declined alternatives:

- laptop-only retention, because laptop loss could remove the exact qualified bytes and jeopardize the 60-minute frozen RTO even when source remains in GitHub; and
- GitHub Releases as the recovery store, because the selected private ZRS Blob protections, access boundary, monitoring and recovery drill already form the online recovery plane and avoid making GitHub availability part of restoration.

### Decision 10e: no automatic update activity; defer the entire maintenance concept

Final operator direction on 2026-07-18: after provisioning from one exact supported Ubuntu LTS image, the MVP performs no scheduled repository refresh, security-update discovery, package inventory comparison, package download, package installation, host-service restart, Gridlab-process restart, update-driven reboot, Azure guest patching or Canonical Livepatch. Actual security maintenance and its monitoring, deadlines, installation, restart/reboot and rollback workflow will be designed only in a later increment if the trading system proves successful and is scaled.

The initial frozen deployment evidence still records the exact Azure image reference, installed/running kernel, installed package manifest and repository configuration so the deployed host remains identifiable. This is a one-time deployment identity, not recurring patch discovery or compliance monitoring. Application dependencies remain inside locally qualified offline release bundles and do not mutate the OS package set.

Paper, Testnet and real-money live remain permitted under an explicit `SECURITY_MAINTENANCE_DEFERRED` accepted security exception. Qualification may report `ACCEPTED_WITH_SECURITY_EXCEPTION`; it may not describe the host as maintained, current or fully patched. There is no claim that unknown or unapplied security fixes are measured, and no alert can be expected for update availability because the operator explicitly removed discovery.

If the VM restarts for an unrelated cause—Azure host maintenance, crash, power/administrative action or rebuild—every Gridlab process still starts through recovery/replay/reconciliation into `FROZEN_READY` and waits for explicit operator resume. No unrelated restart grants package installation or trading permission.

Accepted residual risks include indefinite unknown exposure to security fixes, inability to measure patch age/severity, possible future maintenance jumps, larger compromise likelihood for the single-VM trust boundary and weaker live-security assurance. The later increment must design repository refresh, staging, package selection, recoverable point, planned cancellation/reconciliation, installation, service restart/reboot, rollback/rebuild, validation, monitoring and deadlines before any update action is introduced.

Declined or deferred MVP alternatives include automatic discovery/download, automatic installation, controlled update/reboot deadlines, Livepatch, Azure Automatic VM Guest Patching, Ubuntu Pro image changes and Paper/Testnet-only restriction. The safer controlled-maintenance recommendation remains documented but is intentionally outside this personal MVP.

Primary sources: [Ubuntu automatic updates and reboot behavior](https://documentation.ubuntu.com/server/how-to/software/automatic-updates/), [Azure Automatic Guest Patching](https://learn.microsoft.com/en-us/azure/virtual-machines/automatic-vm-guest-patching), and [Canonical Livepatch](https://ubuntu.com/security/livepatch/docs).

### Decision 10f: no periodic drift system; validate only deliberate changes and recovery

Selected by the operator on 2026-07-18 for a pure one-person project: do not deploy a periodic Azure/host drift scanner, file-change watcher, compliance agent or automatic remediation service. There is exactly one authorized human operator, CI has no Azure write authority, the VM does not pull mutable source, and no other administrator is expected to modify files or resources. This materially lowers ordinary multi-user drift risk and avoids background B1ms work and operational complexity.

The minimum change boundary remains: before any deliberate Bicep apply, the operator reviews a fresh `what-if`; before an application deployment, the installer verifies the exact qualified bundle, manifest, target, configuration/schema identity and intended environment; and during rebuild/recovery, the declared Bicep, release and protected evidence are verified. These checks execute only because the operator initiated a change/recovery and are not periodic drift monitoring.

Emergency/manual Azure Portal, SSH or host changes are operator-owned exceptions. The operator records them and either reconciles the reviewed Bicep/release/configuration or explicitly retains the new baseline before the next deliberate change. The system does not watch arbitrary file modifications, auto-freeze because a file hash changed or auto-repair a resource. Existing runtime safety checks still enforce single-writer locks, immutable run/config identity, evidence integrity, credentials/permissions needed for operation and venue reconciliation; they are not renamed as general configuration-drift detection.

The single-operator assumption does not make drift mathematically impossible: operator mistakes, partial commands, Azure-side changes, storage corruption or credential compromise may still alter state. Those residual risks are accepted for this MVP and cannot be reported as monitored. Automated read-only detection and auto-remediation were declined. Reconsider drift monitoring when another human/automation gains write access, infrastructure becomes multi-node/multi-region, deployment frequency/material live allocation grows, or operational evidence shows unexplained change.

### Decision 11a: warn at EUR 35 and require operator cost review at EUR 50

The first-party price snapshot estimates the selected B1ms-first VM, E6 LRS disk, Standard static IPv4, GPv2 Hot ZRS Blob, Key Vault and bounded monitoring at approximately **EUR 24-30 per month before VAT**, subject to subscription offer, regional capacity, usage and price changes. Blob growth, Log Analytics ingestion, transactions, outbound data, restore drills and a benchmark-triggered resize are the main variable additions. Azure budgets/alerts are delayed financial signals, not real-time safety controls; they never stop the VM, delete evidence, cancel orders or change trading authority automatically.

Selected by the operator on 2026-07-18: warn when forecast or actual monthly Azure cost reaches EUR 35 and require an operator cost review at EUR 50. This leaves modest headroom above the expected baseline while catching an unexpected resize, monitoring ingestion or storage-growth change. “Require review” opens a persistent cost incident and blocks optional new Azure resources until acknowledged; it does not stop the VM, interrupt trading, delete evidence, cancel orders, resize resources or change trading authority.

Retain per-resource cost attribution, daily forecast/actual evidence when available, anomaly alerts and the already accepted storage-growth thresholds. The operator review records expected baseline versus actual/forecast, top resource/meter deltas, Blob and monitoring growth, restore/drill activity, price/offer/tax changes, incidents and the accepted response. A planned B1ms-to-B2 resize requires an updated forecast before approval regardless of current spend.

Declined alternatives were EUR 30/EUR 40, because normal variation could create noisy reviews, and EUR 50/EUR 75, because an unplanned increase would run too long before attention. Budget alerts remain delayed financial evidence, not real-time safety controls.

### Decision 12a: one local resumable acceptance runner with operator checkpoints

All options use the already accepted tests and evidence requirements; the choice is how consistently they are orchestrated. Passing infrastructure deployment alone is never sufficient, and acceptance never grants live trading authority.

Selected by the operator on 2026-07-18: one versioned local acceptance command orchestrates the complete Azure deployment acceptance with explicit operator checkpoints and one sealed result report. From the trusted laptop it validates exact Bicep/release/configuration/tool identities, provisions or verifies the node, uploads the qualified bundle, starts services frozen, checks access/isolation/permissions/Storage/Key Vault/monitoring/dead-man, performs declared failure/restart/recovery/reconciliation tests, runs the representative Paper-plus-Testnet B1ms workload and 24-hour soak, and evaluates every accepted threshold.

The runner is local engineering tooling, not another Azure service, CI deployment path or trading authority. Destructive actions, credential/profile transitions and any test capable of venue commands require the applicable explicit operator checkpoint. It cannot resume live trading. It stores detailed evidence locally and in the accepted Blob classes; every phase records start/end, exact inputs/targets, observations, output/error, resource measurements and pass/fail/inconclusive result.

Resume is allowed only from a verified checkpoint bound to the same acceptance-run identity, VM/deployment, release/configuration/schema, protected state and preceding evidence. Changed identity invalidates affected downstream phases; failed/missing/corrupt evidence never becomes passed. The final report is `ACCEPTED`, `REJECTED`, or `INCONCLUSIVE_RERUN`, with all accepted security exceptions explicit. Only a complete accepted result makes the exact deployment eligible to begin—not complete—the separate uninterrupted 30-day qualifying Paper observation.

The manual-checklist alternative was declined because repeatability and evidence comparison would be weaker. Treating the 30-day Paper run itself as infrastructure acceptance was declined because late deployment defects would contaminate or invalidate algorithm/operational evidence.

### Decision 12b: one confirmation authorizes one bounded immutable Testnet acceptance plan

The acceptance runner must validate actual Binance Testnet signing, filters, identifiers, submission, partial/final order states, cancellations, user-stream evidence, unknown-outcome recovery, rate-limit handling and reconciliation. Dry-run or production-data Paper alone cannot prove those venue-integration paths. Live credentials are absent/revoked under the accepted mutually exclusive Key Vault profile.

Selected by the operator on 2026-07-18: one fresh explicit operator confirmation authorizes one bounded, fully previewed immutable Binance Testnet acceptance plan. Before confirmation, Studio/CLI displays the Testnet environment and endpoint, exact credential-version fingerprint, virtual-asset/notional limits, order types/count/price bounds, client-order-ID namespace, expected state transitions, timing/failure cases, cleanup/reconciliation requirements, maximum duration and abort command. The live secret/version is absent and denied.

The authorization binds the exact acceptance-run and plan digest, expires before dispatch if unused, cannot be replayed for a changed plan/run/environment and authorizes no command outside the preview. Each submit/cancel/query remains durably identified, rate/risk bounded and subject to the accepted outcome-unknown/reconciliation contract. Pause/emergency abort remains continuously available. Completion cancels or accounts for every managed Testnet order, reconciles fills/fees/balances and proves the final isolated Testnet state before the phase can pass.

A Testnet reset, virtual-balance problem, unavailable feature or external outage produces explicit environment evidence and rejected/inconclusive rerun classification; it is never interpreted as successful production-style behavior. Per-order confirmations were declined as cumbersome and timing-distorting. Sending no Testnet orders was declined because authenticated venue integration would remain unproven.

### Decision 12c: restart the actual candidate VM once during pre-Paper acceptance

The accepted recovery contract claims that `systemd`, exclusive ownership, journal replay, SQLite recovery, unknown-outcome reconstruction, managed-order cancellation, Binance reconciliation, monitoring/dead-man recovery and frozen-ready posture survive host replacement. A process-kill test cannot prove the complete VM boot path. This acceptance restart is unrelated to the separately deferred OS-update/reboot concept: it installs no update and occurs before the qualifying 30-day Paper run and any live credential/profile.

Selected by the operator on 2026-07-18: perform one controlled full restart of the exact candidate VM during acceptance. The runner first freezes Paper/Testnet, blocks dispatch, cancels/reconciles all managed Testnet orders, seals journals/evidence and verifies a recoverable point. After fresh explicit operator confirmation it restarts the VM and observes the outage from outside the VM.

Acceptance verifies the expected static public/outbound identity, network/DNS/time, managed identity, Storage/Key Vault paths and monitoring return; proves boot ordering and exclusive store locks; proves every service starts in recovery/frozen posture rather than trading; replays journals and SQLite state; reconstructs unknown outcomes; reconciles Testnet and Paper; tests external dead-man incident/delivery/recovery; and records every lifecycle and recovery deadline. No service resumes trading automatically.

Failure or incomplete evidence rejects or inconclusively reruns acceptance. The restart is not qualifying Paper downtime because the 30-day clock has not started. Process-crash-only testing was declined because it does not prove the boot/host path. A disposable-VM-only restart was declined because it does not prove the exact candidate node/store/network used for qualification.

### Decision 12d: conservative impact-based re-acceptance after a change

Selected by the operator on 2026-07-18: Azure acceptance applies to one exact infrastructure, qualified release, configuration/schema, permission/network/monitoring and capacity identity. Every change declares its affected contracts before deployment and reruns the corresponding acceptance phases. VM SKU/disk/OS image, process topology/supervision, runtime or adapter code, dependency lock, database/journal semantics, network/outbound identity, RBAC/Key Vault, Storage/recovery, monitoring/dead-man, resource limits or safety configuration trigger their named phases. Uncertain or cross-cutting impact triggers the full suite and 24-hour soak. Documentation, Studio-only presentation or proven byte-identical metadata changes run only their exact checks.

Evidence may be reused only when unchanged identities and links are machine-verifiable; the operator cannot waive a failed applicable phase. During a 30-day Production-Data Paper qualification, a proven Testnet-adapter-only correction reruns Testnet plus every affected shared-interface/capacity phase without necessarily invalidating the unchanged Paper evidence. A shared decision, strategy, accounting, risk, persistence or execution change ends the affected qualification attempt. If shared-resource or contract evidence cannot prove Paper remains unaffected, the broader phases apply. Infrastructure re-acceptance cannot preserve a Paper interval that a material change invalidated.

Declined alternatives:

- rerun the complete suite and 24-hour soak after every change, because harmless documentation or Studio-only work should not delay unrelated qualification;
- preserve acceptance until an observed failure, because changed online code or infrastructure could otherwise enter qualification without proving affected recovery, isolation or capacity behavior; and
- let the operator waive a failed applicable phase, because acceptance evidence—not convenience—determines qualification.

### Decision 12e: one algorithm in both online runs, followed by sequential increments

Terminology selected by the operator on 2026-07-18:

1. a **Production-Data Paper Run** consumes Binance production public market data and simulates its orders, fills, fees and balances locally; it sends no orders to Binance; and
2. a **Testnet Run** consumes Binance Testnet data, sends API orders to Binance Testnet, and receives Binance-authoritative Testnet order, fill, fee and virtual-account feedback.

Selected by the operator on 2026-07-18 and refined after considering first-launch defects: MVP1 runs one static-grid algorithm concurrently as one Production-Data Paper Run and one Testnet Run. No second algorithm, Testnet Run or symbol is added. This keeps the first deployment to the accepted three-process profile—Gateway, Production-Data Paper Runtime and Testnet Runtime—while collecting infrastructure, accounting, recovery, reconciliation, logging and strategy evidence.

The first deployment begins in an explicit **shakedown period**. Its expected duration is roughly three weeks but it has no forced qualification start date: defects, missing diagnostics and useful improvements are corrected as they are discovered. Every increment still passes applicable local gates, freezes and reconciles both online runs, seals the old evidence, receives new immutable identities, and passes impact-based Azure acceptance. Shakedown evidence is retained for debugging and learning but is never retroactively counted as qualifying time for a changed candidate.

When one increment has passed all historical/promotion, deployment, replay/accounting, reconciliation, risk, Testnet and operational prerequisites and has no unresolved decision-material incident, the operator explicitly freezes that exact candidate and starts its **30-day qualifying clock**. This start may therefore occur later than the first launch or the initially expected three weeks. The qualifying interval is 30 consecutive elapsed days of one immutable candidate and decision-critical build; it is not a deadline measured from first deployment.

After the clock starts, a strategy, configuration, shared decision-critical code, accounting, risk, execution-model or evidence-semantic change ends that qualification attempt. The fix is welcome—correctness takes priority over preserving elapsed days—but after local qualification, frozen replacement and acceptance, the corrected identity starts again at day zero. Proven Studio-only presentation, documentation or non-decision diagnostic changes follow the impact matrix and need not reset Paper. Earlier attempts remain available for diagnosis and comparison but their days are never spliced together.

After a successful 30-day campaign, later feature increments again use the same sequential replacement process. “Deploy directly after local tests” means no parallel old/new strategy campaign and no unnecessary waiting period; it never means in-place mutation, automatic activation, skipped reconciliation or bypassed acceptance.

For at least the first two months, Azure continues to run only one algorithm and one symbol in both online run types. Local backtests may explore other strategies and symbols concurrently, but cannot create online authority. Multiple simultaneous algorithms, Testnet Runs, Production-Data Paper Runs or symbols are deferred until the accumulated operational evidence justifies a new capacity, account-allocation, rate-limit, reconciliation, comparison and isolation decision. The architecture keeps repeatable run boundaries so that later expansion is possible without changing the deterministic core.

Declined for the initial period:

- overlapping MVP1 and MVP2 Testnet Runs, because preserving the simple three-process B1ms profile is more valuable than simultaneous early strategy campaigns;
- start the 30-day clock automatically at first launch, because expected early defects and corrections would make its identity unstable;
- retroactively count shakedown days or pause around a bug fix and resume the same clock, because qualifying evidence must describe one immutable candidate; and
- defer a necessary correction merely to preserve elapsed qualifying days, because correctness and evidence integrity take priority over calendar progress;
- introducing multiple symbols during the first two months, because symbol-level allocations, rate limits, market streams, risk aggregation and result interpretation need evidence from the simpler single-symbol system first.
