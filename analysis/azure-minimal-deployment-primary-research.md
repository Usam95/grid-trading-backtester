# Minimal Azure deployment: primary-source research

Status: research input for deployment specification  
Research date: 2026-07-18  
Preferred region: Germany West Central (`germanywestcentral`)  
Price basis: Linux pay-as-you-go consumption, 730 hours/month, EUR reference prices, before VAT

## Executive recommendation

Use one always-on Linux Azure VM as the MVP online node. Start with `Standard_B1ms`, one 64-GiB E6 LRS Standard SSD, one Standard static public IPv4 address, one Standard GPv2 Blob Storage account using Hot ZRS for newly sealed recovery/evidence objects, one Key Vault Standard vault, and a minimal Azure Monitor/Log Analytics setup. Run the control gateway, production-data paper runtime, and Binance Testnet runtime as three independently supervised OS processes. Do not run backtests or the full Studio UI on this VM.

This is the smallest practical topology that preserves the accepted local SQLite/WAL semantics, three-process authority isolation, long-lived outbound Binance WebSockets, explicit outbound identity, system-level supervision, and application-controlled verified recovery points. It is a **single failure domain**, not a highly available trading platform.

`Standard_B1ms` has one vCPU, 2 GiB RAM, 20% base CPU performance, 12 credits banked per hour, and 288 maximum banked credits. Azure throttles a B-series VM to its base performance after credits are exhausted. It is therefore a measurement candidate only, not an assumed qualification size. [Microsoft Bv1 size table](https://learn.microsoft.com/en-us/azure/virtual-machines/sizes/general-purpose/bv1-series), [B-family CPU-credit behavior](https://learn.microsoft.com/en-us/azure/virtual-machines/sizes/general-purpose/b-family).

The accepted 24-hour three-process benchmark, restart/replay/reconciliation drill, compaction test, and recovery-point test MUST pass before the 30-day qualifying paper run. Failure triggers resize to the already selected 4-GiB `Standard_B2als_v2` target and repetition of the complete benchmark; it never permits weakened logging, evidence, isolation, RPO, or safety behavior.

## Recommended minimum topology

```text
Operator laptop / local Studio
        |
        | authenticated SSH tunnel; gateway is not public
        v
Standard static IPv4 -> NSG -> Linux Standard_B1ms
                              |- control-gateway.service
                              |- paper-runtime.service -> isolated SQLite/WAL
                              |- testnet-runtime.service -> isolated SQLite/WAL
                              |- bounded backup/offload scheduler
                              |- Azure Monitor Agent
                              |
                              +-> Binance production public streams
                              +-> Binance Testnet REST/WebSockets
                              +-> Key Vault through managed identity
                              +-> Hot ZRS Blob: verified recovery/evidence

Azure Monitor outside the VM -> availability/resource/heartbeat alerts
```

### Mandatory MVP resources and configuration

| Resource | Minimum selection | Why it is required |
| --- | --- | --- |
| Resource group | One deployment resource group | Gives one lifecycle, RBAC, tagging, cost, and teardown boundary. |
| Virtual network | One VNet and one subnet | Supplies the VM network boundary. New VNet API versions after 2026-03-31 make new subnets private by default, so outbound access must be explicit. [Default outbound access](https://learn.microsoft.com/en-us/azure/virtual-network/ip-services/default-outbound-access) |
| Network security group | One deny-by-default NSG | Permit only the operator access path; no public control-gateway or database port. [NSG overview](https://learn.microsoft.com/en-us/azure/virtual-network/network-security-groups-overview) |
| Public IP | Standard static IPv4 on the VM NIC | Cheapest explicit single-node outbound path, stable Binance allowlist identity, and the operator SSH endpoint. A directly attached public IP is an explicit outbound method. [Outbound access design](https://learn.microsoft.com/en-us/azure/networking/design-guide/outbound-egress) |
| Compute | Linux `Standard_B1ms`, always allocated | Hosts the three isolated processes, local durable sequencing, WebSockets, supervision, and bounded background work. B1ms is conditional on the benchmark. |
| Managed disk | One 64-GiB E6 Standard SSD LRS used as the OS/application disk | Holds OS, deployment metadata, isolated SQLite/WAL stores, open capture, local snapshots, bounded logs, and compaction/upload staging. Standard SSD is suitable for low-IOPS application workloads and can be an OS disk. [Managed-disk types](https://learn.microsoft.com/en-us/azure/virtual-machines/disks-types) |
| Storage account | Standard GPv2; Hot ZRS Blob, lifecycle to Cool after 30 days when eligible | Stores verified off-VM recovery points, sealed evidence segments, incident/promotion bundles, and retained diagnostics. ZRS synchronously copies data across three or more availability zones and provides at least 12 nines annual object durability; it does not protect against user deletion or a whole-region disaster. [Azure Storage redundancy](https://learn.microsoft.com/en-us/azure/storage/common/storage-redundancy), [Blob lifecycle management](https://learn.microsoft.com/en-us/azure/storage/blobs/lifecycle-management-overview) |
| Identity | VM system-assigned managed identity | Authenticates the VM to Key Vault and Blob without an embedded Azure credential. [Managed identities overview](https://learn.microsoft.com/en-us/entra/identity/managed-identities-azure-resources/overview) |
| Secrets | One Key Vault Standard vault | Stores separate Testnet/later-live venue credentials and required application secrets; the Production-Data Paper Runtime receives no venue credential. It supports rotation/audit without secret files in Git or deployment variables. Use Azure RBAC and least-privilege roles; Microsoft recommends managed identity and RBAC rather than legacy access policies. [Secure Key Vault](https://learn.microsoft.com/en-us/azure/key-vault/general/secure-key-vault), [Key Vault RBAC guide](https://learn.microsoft.com/en-us/azure/key-vault/general/rbac-guide) |
| Monitoring | Azure platform metrics and activity log; Azure Monitor Agent, one Data Collection Rule, one Log Analytics workspace; metric/log alerts and email/mobile action group | Host metrics exist without guest setup; AMA/DCR adds bounded guest syslog and heartbeat. Recommended VM alerts include availability. [Monitor Azure VMs](https://learn.microsoft.com/en-us/azure/virtual-machines/monitor-vm), [DCR overview](https://learn.microsoft.com/en-us/azure/azure-monitor/data-collection/data-collection-rule-overview), [collect Linux syslog](https://learn.microsoft.com/en-us/azure/azure-monitor/vm/data-collection-syslog) |
| Deployment definition | Versioned IaC plus versioned OS/bootstrap manifest | Makes the accepted 60-minute fresh-VM recovery drill repeatable. The application is restored frozen and reconciled; deployment never grants trading authority. |

### Operator access

For the cost-minimal MVP, bind the control gateway to loopback or the VM private interface and reach it through an SSH local-forward tunnel. Expose only SSH on the Standard public IP, restrict the NSG source to the operator's current public IP, use key-based authentication, disable password and direct root login, and apply the accepted gateway authentication and re-authentication rules inside the tunnel. The application endpoint and SQLite stores are never internet-facing.

This is an encrypted, authenticated private application channel over a public-IP SSH endpoint; it is not an Azure Private Link or private WAN design. It is practical for one operator, but it depends on a stable/updated source-IP rule and operator SSH-key hygiene.

If policy later requires a Microsoft-managed private access plane, use Azure Bastion with native-client tunnelling or a point-to-site VPN and remove public SSH. Bastion requires its own subnet and public IP and has feature/SKU constraints; VPN Gateway has a continuously billed gateway. Both add fixed cost and operational resources that are disproportionate for the first personal single-VM deployment. [Azure Bastion overview](https://learn.microsoft.com/en-us/azure/bastion/bastion-overview), [Bastion native-client connections](https://learn.microsoft.com/en-us/azure/bastion/connect-vm-native-client-windows), [point-to-site VPN](https://learn.microsoft.com/en-us/azure/vpn-gateway/point-to-site-about).

The final security ticket must either approve the SSH-tunnel boundary or select the paid managed-private upgrade. The minimal deployment report does not silently represent a public control API as private.

### Storage network follow-up (2026-07-18)

Microsoft documents that a virtual-network service endpoint can carry Azure Storage traffic directly over the Azure backbone, gives the service the subnet identity used by virtual-network firewall rules, and has no additional endpoint charge. The storage public service endpoint remains, but a default-deny Storage firewall can admit only explicitly selected virtual networks/subnets. This is the recommended MVP middle ground: `Microsoft.Storage` service endpoint on the VM subnet, a matching storage-account virtual-network rule, default network action `Deny`, managed identity/RBAC, and TLS. Network admission never replaces data authorization. [Service endpoint overview](https://learn.microsoft.com/en-us/azure/virtual-network/virtual-network-service-endpoints-overview), [Storage network security](https://learn.microsoft.com/en-us/azure/storage/common/storage-network-security), [default public access rule](https://learn.microsoft.com/en-us/azure/storage/common/storage-network-security-set-default-access).

A Private Endpoint instead assigns the storage service a private VNet address and permits disabling the public endpoint, but adds endpoint billing, private-DNS/recovery configuration, and another dependency. Keep it as a threat-model-triggered upgrade for the personal single-VM baseline. [Storage private endpoints](https://learn.microsoft.com/en-us/azure/storage/common/storage-private-endpoints).

### Managed-identity process-boundary follow-up (2026-07-18)

Microsoft states that the managed-identity security boundary is the Azure resource and that its REST token interface is accessible to any client application running on a VM that can reach IMDS. Microsoft separately recommends local firewall rules when not every VM process needs IMDS. Therefore attaching distinct identities or using distinct Linux users on one VM is not, by itself, a process-level Azure identity boundary. The minimum single-VM design must restrict IMDS locally and mediate cloud credential use through privileged, narrow infrastructure jobs, while acknowledging that root/kernel/VM compromise crosses all local modes. [Acquire a managed-identity token on a VM](https://learn.microsoft.com/en-us/entra/identity/managed-identities-azure-resources/how-to-use-vm-token), [Azure Instance Metadata Service](https://learn.microsoft.com/en-us/azure/virtual-machines/instance-metadata-service), [how VM managed identities work](https://learn.microsoft.com/en-us/entra/identity/managed-identities-azure-resources/how-managed-identities-work-vm).

### Key Vault network follow-up (2026-07-18)

Microsoft documents Key Vault virtual-network service endpoints and firewall rules that deny data-plane access from all networks by default and admit selected virtual networks or IPv4 ranges. The firewall is independent of Entra/RBAC authorization, and Key Vault control-plane resource configuration is distinct from secret/key/certificate data-plane access. The cost-minimal design can therefore use a `Microsoft.KeyVault` service endpoint for the VM subnet and a default-deny vault firewall, with only a time-bounded operator-IP rule for deliberate secret management. Private Link remains the stronger paid/private-DNS alternative. [Key Vault service endpoints](https://learn.microsoft.com/en-us/azure/key-vault/general/overview-vnet-service-endpoints), [configure Key Vault network security](https://learn.microsoft.com/en-us/azure/key-vault/general/network-security), [secure Key Vault](https://learn.microsoft.com/en-us/azure/key-vault/general/secure-key-vault).

## Runtime, restart, and recovery behavior

- The three authoritative applications run as separate, least-privilege OS users and separately supervised services with independent writable directories, databases, journals, outboxes, identities, quotas, and credentials.
- The service supervisor starts them on boot and uses bounded restart backoff. A replacement runtime must acquire its exclusive store/mode lock, replay and reconcile, cancel surviving managed orders as required, and stop in `FROZEN_READY`; no process or VM restart automatically resumes trading.
- Azure attempts platform healing after host failure and can reboot/migrate the VM. This reduces common infrastructure downtime but does not create application HA or guarantee the project's 60-minute RTO. [Understand Azure VM reboots and healing](https://learn.microsoft.com/en-us/azure/virtual-machines/understand-vm-reboots)
- Azure Monitor's VM availability metric and an independent application heartbeat provide the external dead-man path. Host-level data alone can miss or misclassify some guest failures, so application heartbeat absence remains mandatory. [VM availability metric](https://learn.microsoft.com/en-us/azure/virtual-machines/monitor-vm-reference), [known availability-metric limitation](https://learn.microsoft.com/en-us/troubleshoot/azure/virtual-machines/windows/inaccurate-vm-availability-during-vm-restart)
- Application recovery points use SQLite's online-backup mechanism, streaming compression, checksums, reader verification, immutable identities, and manifest publication to Blob every nominal ten minutes when protected state advances. Only a verified published point satisfies the 15-minute RPO.
- The 60-minute RTO is achieved by fresh provisioning from IaC, restore from the newest compatible verified Blob point, deterministic replay, invariant verification, Binance reconciliation, and frozen operator availability. It does not include trading resume.
- Full Azure VM Backup, managed-disk snapshots, and Blob snapshots do not replace the application recovery-point contract: a crash-consistent disk image does not by itself prove a transactionally consistent SQLite/journal boundary or venue reconciliation. Azure VM Backup is an optional OS-recovery convenience if later drills show application-level rebuild is insufficient. [Azure VM Backup overview](https://learn.microsoft.com/en-us/azure/backup/backup-azure-vms-introduction), [managed-disk snapshots](https://learn.microsoft.com/en-us/azure/virtual-machines/snapshot-copy-managed-disk)

## B1ms resource assumptions and resize gate

The following are engineering budgets to measure, not Azure guarantees:

| Consumer | Planning memory assumption |
| --- | ---: |
| Linux OS, SSH, Azure guest/monitor agents | 450-650 MiB |
| Control gateway | 80-150 MiB |
| Production-data paper runtime | 250-450 MiB |
| Testnet runtime | 250-450 MiB |
| SQLite page caches, durable staging, queues, capture buffers | 250-400 MiB |
| One bounded backup/compression phase | no more than 64 MiB application working buffer |
| Required transient/safety headroom | at least 256 MiB, preferably 384-512 MiB |

The ranges overlap and can total roughly 1.3-2.2 GiB before unusual Python allocator growth or OS cache pressure. That is why B1ms may fail even though average workload looks light. The five-minute incident ring remains disk-backed, optional diagnostics are bounded, and only one backup/compaction/offload heavy phase may run at once.

B1ms is rejected and resized if any of the following occurs in the required representative benchmark or drills:

- any OOM kill, process termination from memory pressure, sustained swap/page thrashing, or loss of required memory headroom;
- CPU-credit balance reaches zero or trends toward exhaustion under steady representative load;
- processing latency/freshness, command, reconciliation, or safety deadlines are breached;
- a verified recovery point cannot remain within the 15-minute protected-position RPO;
- restart/replay/reconciliation or fresh-VM restoration cannot meet the accepted 60-minute RTO;
- disk IOPS/transaction pressure, compaction coexistence, or free-space reserve threatens the journal, cancellation, incident, or recovery writes;
- Testnet load can starve or contaminate the paper runtime; or
- required evidence, monitoring, or process isolation must be weakened to make the machine fit.

The first resize is `Standard_B2als_v2` (2 vCPU, 4 GiB); the next is `Standard_B2as_v2` (2 vCPU, 8 GiB). Resizing requires a restart and a complete benchmark/recovery rerun.

## Cost model

Exact prices below come from the repository's first-party Azure Retail Prices API snapshot taken 2026-07-17, one day before this report. The query links are preserved for rerun. Microsoft states that its base pricing currency is USD and non-USD values are reference estimates; Retail Prices API values are public list prices, not the operator's contracted invoice. [Azure Retail Prices API](https://learn.microsoft.com/en-us/rest/api/cost-management/retail-prices/azure-retail-prices), [local price snapshot](azure-mvp-monthly-cost-estimate.md).

### Expected mandatory baseline

| Item | Meter/assumption | Monthly estimate |
| --- | ---: | ---: |
| Linux `Standard_B1ms` | EUR 0.021062/hour x 730 | **EUR 15.38** |
| E6 64-GiB Standard SSD LRS capacity | provisioned tier | **EUR 4.21** |
| E6 transactions | representative bounded workload | **EUR 1-5** |
| Standard static IPv4 | EUR 0.004388/hour x 730 | **EUR 3.20** |
| Hot ZRS Blob capacity, first month | 15-90 GiB at EUR 0.019746/GB-month | **EUR 0.30-1.78** |
| Blob operations | fewer than 3,000 segment writes/month plus recovery points | **small usage charge** |
| Key Vault Standard operations | startup/rotation reads, no HSM | **usage-metered; expected cents, not fixed in snapshot** |
| Azure platform metrics/activity log | default collection | **no ingestion estimate added** |
| Log Analytics | capped at no more than the first 5 GB/month free allowance in the snapshot | **EUR 0 expected** |
| Email/mobile alerts | remain inside published small free allowances | **EUR 0 expected** |
| Internet transfer | inbound free; expected outbound below first 100 GB/month allowance | **EUR 0 expected** |
| **Expected first-month total** | before VAT; no VM Backup/Bastion/VPN/domain/support | **approximately EUR 24-30** |

Retail query evidence: [VM meters](https://prices.azure.com/api/retail/prices?currencyCode=%27EUR%27&api-version=2023-01-01-preview&%24filter=armRegionName%20eq%20%27germanywestcentral%27%20and%20serviceName%20eq%20%27Virtual%20Machines%27%20and%20priceType%20eq%20%27Consumption%27), [Standard SSD meters](https://prices.azure.com/api/retail/prices?currencyCode=%27EUR%27&api-version=2023-01-01-preview&%24filter=armRegionName%20eq%20%27germanywestcentral%27%20and%20serviceName%20eq%20%27Storage%27%20and%20productName%20eq%20%27Standard%20SSD%20Managed%20Disks%27%20and%20priceType%20eq%20%27Consumption%27), [Virtual Network/IP meters](https://prices.azure.com/api/retail/prices?currencyCode=%27EUR%27&api-version=2023-01-01-preview&%24filter=armRegionName%20eq%20%27germanywestcentral%27%20and%20serviceName%20eq%20%27Virtual%20Network%27%20and%20priceType%20eq%20%27Consumption%27), [GPv2 Blob meters](https://prices.azure.com/api/retail/prices?currencyCode=%27EUR%27&api-version=2023-01-01-preview&%24filter=armRegionName%20eq%20%27germanywestcentral%27%20and%20serviceName%20eq%20%27Storage%27%20and%20productName%20eq%20%27General%20Block%20Blob%20v2%27%20and%20priceType%20eq%20%27Consumption%27), [Log Analytics meters](https://prices.azure.com/api/retail/prices?currencyCode=%27EUR%27&api-version=2023-01-01-preview&%24filter=armRegionName%20eq%20%27germanywestcentral%27%20and%20serviceName%20eq%20%27Log%20Analytics%27%20and%20priceType%20eq%20%27Consumption%27).

### Variable and optional costs

- E6 Standard SSD transactions can reach approximately EUR 10.40/month at the published hourly billing cap; measure rather than assume EUR 1-5.
- Ten GiB/month of Analytics Logs would make about five GiB billable in the snapshot, approximately EUR 13.12/month. Collect curated warnings/errors/heartbeats, not complete high-rate trading evidence; canonical evidence belongs in the journal and Blob.
- Blob capacity accumulates. With 15-90 GiB added monthly and a simple 30-day Hot-to-Cool policy, the snapshot estimates month-12 storage at approximately EUR 2.19-13.16/month before retrieval and exceptional operations.
- Azure VM Backup was estimated at approximately EUR 10-13/month for the protected-instance and 50-150 GB vault-storage assumptions. It is not in the selected baseline.
- Bastion, VPN Gateway, NAT Gateway, Azure Firewall, Private Endpoints, SMS/voice alerts, a domain/certificate service, support plans, a second VM, and cross-region replication are excluded.
- The B2als_v2/E10 and B2as_v2/E10 alternatives were estimated at materially higher monthly totals in the [price snapshot](azure-mvp-monthly-cost-estimate.md); a resize budget should be approved before qualification.

Set an initial budget alert at EUR 35 for the B1ms baseline and a second hard review threshold at EUR 50. Cost alerts do not stop resources or trading automatically.

## Material alternatives

| Alternative | Assessment for this MVP |
| --- | --- |
| Azure Container Apps Consumption | Attractive managed restart and usage billing, but continuously active WebSocket runtimes do not scale to zero, replica-local storage is ephemeral, and durable shared storage requires Azure Files or another managed data service. Preserving three isolated SQLite authorities, exact WAL/filesystem behavior, recovery drills, and predictable one-node resource scheduling would become harder rather than simpler. Defer until persistence is redesigned behind its declared port. [Container Apps billing](https://learn.microsoft.com/en-us/azure/container-apps/billing), [storage mounts](https://learn.microsoft.com/en-us/azure/container-apps/storage-mounts), [scaling/minimum replicas](https://learn.microsoft.com/en-us/azure/container-apps/scale-app) |
| Azure App Service | `Always On` requires a paid plan and the platform is optimized for hosted web applications. Three independently supervised long-running workers, isolated local authorities, explicit restart/recovery sequencing, and local SQLite/WAL control are a poor fit. It also does not remove the need for durable external storage. [App Service common configuration/Always On](https://learn.microsoft.com/en-us/azure/app-service/configure-common) |
| Separate VM per process | Stronger compute/failure isolation, but triples VM/disk/network management and cost before evidence shows it is needed. One modular node with OS/process/store isolation is the accepted MVP boundary. |
| Premium SSD | Improves single-VM SLA/performance and removes Standard SSD transaction variability, but capacity cost is higher. Select it only if E6 latency/IOPS or transaction cost fails the benchmark; storage type cannot fix B1ms CPU/RAM exhaustion. [Managed-disk types](https://learn.microsoft.com/en-us/azure/virtual-machines/disks-types) |
| LRS Blob | Cheaper but keeps every off-VM copy in one physical datacenter. ZRS is preferred because it spreads synchronous copies across zones. Neither option is cross-region DR. |
| GZRS/RA-GZRS Blob | Adds regional-disaster protection, but cost and failover/restore behavior exceed the accepted single-region MVP. Reconsider before capital or evidence criticality grows. |
| Local encrypted secret file | Cheapest, but weaker rotation, audit, least-privilege, and backup-copy control. Key Vault plus managed identity is the minimum recommended secret boundary. |
| Key Vault/Blob Private Endpoints | Stronger network isolation but add per-endpoint/hour and data-processing costs plus private DNS complexity. For the first VM, use managed identity, RBAC, TLS, and restricted public/service endpoints; select Private Link only in the security specification if policy requires it. [Private Endpoint pricing](https://azure.microsoft.com/en-us/pricing/details/private-link/) |
| Azure VM Backup/snapshots as primary recovery | Useful for whole-machine convenience but insufficient as the authoritative recovery proof. Keep application-level verified Blob recovery points; add VM Backup only if monthly drills show IaC plus application restore cannot meet RTO. |
| Availability zones/second VM | Needed for application HA, but the runtime currently has single-writer local state and no safe automatic failover design. A second VM without a consensus/fencing design can create split authority. This is intentionally deferred. |

## Availability and failure-domain interpretation

The VM and its E6 LRS disk remain one compute/datacenter failure domain. Azure platform healing can move or reboot the VM, while ZRS Blob protects sealed off-VM objects across zones. A VM/disk loss is recovered from Blob; a region-wide outage is not covered. The 15-minute RPO and 60-minute RTO are application objectives proven by drills, not Azure SLA claims.

The public Retail Prices API returned Germany West Central meters for B1ms, E6, Standard IPv4, Blob ZRS, and Log Analytics on 2026-07-17. A price record is not a promise that the SKU has quota or allocatable capacity in this subscription. Before deployment, the implementation MUST verify:

1. `Standard_B1ms`, `Standard_B2als_v2`, and `Standard_B2as_v2` are enabled and have vCPU quota/capacity in Germany West Central;
2. the chosen Standard GPv2 account supports ZRS and the required access tiers/features in that region;
3. the selected Ubuntu image, disk tier, VM generation, and architecture are compatible;
4. Key Vault, Log Analytics, Azure Monitor Agent, action groups, and any chosen Bastion/VPN SKU are deployable in the subscription/region; and
5. the operator's actual offer/currency/tax invoice matches the planning meters.

These subscription-specific facts could not be verified from public sources and remain explicitly open until an Azure deployment preflight is run.

## Deployment acceptance checklist

The topology is acceptable for qualification only when evidence shows:

- three independent services and stores; no shared writable runtime authority;
- explicit stable outbound IP, Binance allowlisting, and successful long-lived public/private WebSocket rotation/repair;
- no public gateway/database, restricted SSH tunnel, key-only access, and tested operator lockout/recovery procedure;
- managed identity can read only required Key Vault secrets and write only required Blob prefixes; the gateway has no venue credentials;
- system restart and Azure platform reboot end frozen, with exclusive locks, replay, cancellation, reconciliation, and no automatic resume;
- verified Blob recovery-point lag never exceeds 15 minutes while protected state advances;
- fresh-VM frozen recovery completes within 60 minutes in the monthly drill;
- external alerts detect VM absence and runtime-heartbeat absence even when the node cannot report its own failure;
- B1ms resource/CPU-credit/disk headroom passes the representative 24-hour benchmark; and
- cost, Blob growth, log ingestion, disk transactions, and budget alerts are observed for the complete benchmark period.

## Sources and verification limits

Azure capability claims in this report use Microsoft Learn, Azure product/security documentation, and Microsoft service pricing pages. Exact EUR values use the first-party Retail Prices API snapshot captured in the repository on 2026-07-17. A new live API query on 2026-07-18 could not be completed in the restricted research environment, so the one-day-old meter values are retained rather than presented as a separately refreshed snapshot. They must be rerun at deployment and recorded with the final bill-of-materials manifest.

Local requirements reconciled for this report: [online runtime and recovery](online-runtime-and-recovery-spec.md), [event journal and observability](event-journal-observability-spec.md), [MVP scope](mvp-scope.md), [architecture quality requirements](architecture-quality-requirements.md), and the [2026-07-17 Azure cost snapshot](azure-mvp-monthly-cost-estimate.md).
