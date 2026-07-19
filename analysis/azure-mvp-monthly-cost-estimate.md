# Azure MVP monthly cost estimate

Status: research snapshot; baseline recommendation superseded by [`azure-minimal-deployment-primary-research.md`](azure-minimal-deployment-primary-research.md)

Price snapshot date: 2026-07-17

Target region: Germany West Central (`germanywestcentral`)

Operator decision on 2026-07-17: begin with `Standard_B1ms` and require a 24-hour production-data/resource benchmark plus recovery and compaction drills before the 30-day qualifying paper run. The 4-GiB profile remains the first resize target if B1ms fails any accepted resource or performance guardrail.

Storage decision on 2026-07-17: use one 64-GiB E6 LRS Standard SSD as the bounded active working disk plus Hot ZRS Blob Storage for verified off-VM application backups and closed evidence, with eligible objects moving to Cool after 30 days. Full Azure VM Backup is not in the initial baseline. On the current assumptions this places normal B1ms operation at approximately EUR 24-30/month before VAT; the backup method, cadence, and restore objectives remain to be specified and tested.

## Result

For one always-on personal grid-trading node, the following historical comparison includes the then-conservative Azure VM Backup allowance. VM Backup was later excluded from the accepted baseline in favor of verified application-level SQLite recoverable points in Blob:

| Capacity alternative | Suggested Linux VM | Expected monthly budget | Heavy-observability / maximum-SSD-transaction case |
| --- | --- | ---: | ---: |
| 2 GiB RAM + 64 GiB disk | `Standard_B1ms` | **EUR 34-42** | about **EUR 61** |
| 4 GiB RAM + 128 GiB disk | `Standard_B2als_v2` | **EUR 51-59** | about **EUR 86** |
| 8 GiB RAM + 128 GiB disk | `Standard_B2as_v2` | **EUR 78-87** | about **EUR 114** |

The accepted baseline is now **B1ms plus E6 without full VM Backup**, approximately **EUR 24-30/month before VAT**. B1ms must pass the complete 24-hour three-process/resource/recovery benchmark. `Standard_B2als_v2` is the first resize target if any guardrail fails; it is not the starting assumption. See the superseding primary-source research for the current bill of materials and cost thresholds.

The expected range includes one VM, one Standard SSD, a static public IPv4 address, first-month market-evidence storage, low-volume Azure Monitor use, and a conservative Azure VM Backup allowance. It excludes trading capital and Binance fees.

## Measured Microsoft retail meters

These are Microsoft retail prices returned in EUR by the [official Azure Retail Prices API](https://learn.microsoft.com/en-us/rest/api/cost-management/retail-prices/azure-retail-prices). Microsoft states that USD is its base pricing currency and that non-USD prices are reference estimates. All calculations use Linux pay-as-you-go consumption, 730 hours/month, no reservation, and no savings plan.

### Compute

| Resource | Capacity | Retail meter | Monthly calculation |
| --- | --- | ---: | ---: |
| `Standard_B1ms` | 1 vCPU, 2 GiB | EUR 0.021062/hour | **EUR 15.38** |
| `Standard_B2als_v2` | 2 vCPU, 4 GiB | EUR 0.037911/hour | **EUR 27.68** |
| `Standard_B2as_v2` | 2 vCPU, 8 GiB | EUR 0.075823/hour | **EUR 55.35** |

The sizes and memory amounts come from Microsoft's [Bv1 size table](https://learn.microsoft.com/en-us/azure/virtual-machines/sizes/general-purpose/bv1-series) and [Basv2 size table](https://learn.microsoft.com/en-us/azure/virtual-machines/sizes/general-purpose/basv2-series). These are burstable VMs: after CPU credits are depleted, Azure throttles them to their base performance. The benchmark must therefore measure CPU-credit balance as well as CPU and memory. Microsoft also states that disks are billed separately.

Retail API evidence: [Germany West Central VM consumption meters](https://prices.azure.com/api/retail/prices?currencyCode=%27EUR%27&api-version=2023-01-01-preview&%24filter=armRegionName%20eq%20%27germanywestcentral%27%20and%20serviceName%20eq%20%27Virtual%20Machines%27%20and%20priceType%20eq%20%27Consumption%27).

### Local durable disk

| Resource | Capacity | Base price | Transaction price | Maximum paid transactions/hour | Maximum transaction charge/month |
| --- | ---: | ---: | ---: | ---: | ---: |
| Standard SSD E6 LRS | 64 GiB | **EUR 4.21/month** | EUR 0.001755/10,000 | 81,200 | **EUR 10.40** |
| Standard SSD E10 LRS | 128 GiB | **EUR 8.42/month** | EUR 0.001755/10,000 | 147,200 | **EUR 18.86** |

The maximum is calculated from Microsoft's hourly cap and 730 hours. The expected totals budget EUR 1-5/month for disk operations; the high case uses the full hourly billing cap for every hour. Azure bills managed disks by the rounded-up provisioned tier, not by used capacity. A single-VM disk does not pay the separate shared-disk mount meter. See [managed-disk billing](https://learn.microsoft.com/en-us/azure/virtual-machines/disks-understand-billing) and [managed-disk pricing](https://azure.microsoft.com/en-us/pricing/details/managed-disks/).

Retail API evidence: [Germany West Central Standard SSD meters](https://prices.azure.com/api/retail/prices?currencyCode=%27EUR%27&api-version=2023-01-01-preview&%24filter=armRegionName%20eq%20%27germanywestcentral%27%20and%20serviceName%20eq%20%27Storage%27%20and%20productName%20eq%20%27Standard%20SSD%20Managed%20Disks%27%20and%20priceType%20eq%20%27Consumption%27).

### Static outbound identity

A Standard static IPv4 address is EUR 0.004388/hour, or **EUR 3.20/month**. It provides an explicit, predictable outbound address suitable for Binance IP allowlisting. New VNet APIs after 2026-03-31 default to private subnets, so explicit outbound connectivity is required; a Standard public IP on the VM NIC is the low-cost single-node choice. A NAT Gateway is not included. See [default outbound access](https://learn.microsoft.com/en-us/azure/virtual-network/ip-services/default-outbound-access) and [Azure outbound methods](https://learn.microsoft.com/en-us/azure/load-balancer/load-balancer-outbound-connections).

Retail API evidence: [Germany West Central IP-address meters](https://prices.azure.com/api/retail/prices?currencyCode=%27EUR%27&api-version=2023-01-01-preview&%24filter=armRegionName%20eq%20%27germanywestcentral%27%20and%20serviceName%20eq%20%27Virtual%20Network%27%20and%20priceType%20eq%20%27Consumption%27).

### Market-evidence Blob storage

The estimate uses Hot ZRS for newly sealed evidence:

- Hot ZRS: EUR 0.019746/GB-month.
- Cool ZRS: EUR 0.011496/GB-month.
- Hot ZRS writes: EUR 0.047389/10,000 operations.

At the current planning assumption of 15-90 GiB added per active month, the first month's Hot ZRS capacity costs approximately **EUR 0.30-1.78**. Ninety-six 15-minute segments/day produce fewer than 3,000 writes/month, so operation cost is negligible at this scale.

Storage is cumulative. With a simple 30-day Hot then Cool lifecycle and constant capture, the storage charge in month 12 would be about **EUR 2.19-13.16/month**. Retrieval, rehydration, early-deletion, replication, and unusually high operation charges are not included. A real 24-hour capture benchmark must replace the 0.5-3 GiB/day planning range before the 30-day qualification run.

Retail API evidence: [Germany West Central General Block Blob v2 meters](https://prices.azure.com/api/retail/prices?currencyCode=%27EUR%27&api-version=2023-01-01-preview&%24filter=armRegionName%20eq%20%27germanywestcentral%27%20and%20serviceName%20eq%20%27Storage%27%20and%20productName%20eq%20%27General%20Block%20Blob%20v2%27%20and%20priceType%20eq%20%27Consumption%27).

### Logs, metrics, and alerts

The Germany West Central Analytics Logs ingestion meter is:

- First 5 GB/month per billing account: **EUR 0**.
- Usage above 5 GB: **EUR 2.623958/GB**.
- Therefore, 10 GB/month costs about **EUR 13.12** for the five billable GB.
- Analytics Logs include approximately 31 days of interactive retention at no additional retention charge.

The expected totals assume at most 5 GB/month of centrally collected logs. The high case assumes 10 GB/month. Platform metrics are ingested free, and the Azure Monitor price schedule includes free allowances for small numbers of metric time series, email notifications, and Azure mobile-app push notifications. A small single-node deployment can remain inside those allowances if high-rate application metrics stay curated. SMS is excluded because price depends on destination/operator and is unnecessary if Azure mobile push is selected.

See [Azure Monitor pricing](https://azure.microsoft.com/en-us/pricing/details/monitor/) and [Azure Monitor Logs cost rules](https://learn.microsoft.com/en-us/azure/azure-monitor/logs/cost-logs).

Retail API evidence: [Germany West Central Log Analytics meters](https://prices.azure.com/api/retail/prices?currencyCode=%27EUR%27&api-version=2023-01-01-preview&%24filter=armRegionName%20eq%20%27germanywestcentral%27%20and%20serviceName%20eq%20%27Log%20Analytics%27%20and%20priceType%20eq%20%27Consumption%27).

### Backup allowance

The totals include a conservative **EUR 10-13/month** allowance:

- Azure VM protected-instance meter: EUR 8.775779/month.
- LRS backup storage: EUR 0.026327/GB-month.
- Assumed backup-vault usage: 50-150 GB, or EUR 1.32-3.95/month.

Azure bills VM protected size from actual data, excluding temporary storage, and backup storage from data retained in recovery points. Actual churn and retention policy can materially change the storage part. The estimate conservatively budgets the full protected-instance meter even if the initial used size qualifies for a smaller billing category. See [Azure VM backup costs](https://learn.microsoft.com/en-us/azure/backup/backup-azure-vms-introduction) and [Azure Backup pricing](https://azure.microsoft.com/en-us/pricing/details/backup/).

Retail API evidence: [Germany West Central Azure Backup meters](https://prices.azure.com/api/retail/prices?currencyCode=%27EUR%27&api-version=2023-01-01-preview&%24filter=armRegionName%20eq%20%27germanywestcentral%27%20and%20serviceName%20eq%20%27Backup%27%20and%20priceType%20eq%20%27Consumption%27).

### Bandwidth

Inbound internet transfer is free, and the first 100 GB/month of internet egress is free. The totals therefore budget **EUR 0** for bandwidth. Beyond 100 GB/month, the Germany West Central Internet-routing meter is EUR 0.070206/GB for the next tier. Binance market input is inbound; order/API traffic and operator views should remain far below 100 GB outbound. See [Azure bandwidth pricing](https://azure.microsoft.com/en-us/pricing/details/bandwidth/).

Retail API evidence: [Germany West Central bandwidth meters](https://prices.azure.com/api/retail/prices?currencyCode=%27EUR%27&api-version=2023-01-01-preview&%24filter=armRegionName%20eq%20%27germanywestcentral%27%20and%20serviceName%20eq%20%27Bandwidth%27%20and%20priceType%20eq%20%27Consumption%27).

## Calculation assumptions

Expected-range assumptions:

- One always-on Linux VM for 730 hours/month.
- One Standard SSD used as the durable OS/application disk; no separate journal data disk.
- Standard static IPv4 attached directly to the VM NIC; no NAT Gateway, load balancer, Bastion, VPN Gateway, or firewall appliance.
- Disk transaction charge of EUR 1-5/month.
- 15-90 GB of new market evidence in the first month on Hot ZRS.
- At most 5 GB/month of Azure Monitor log ingestion.
- Azure VM Backup allowance of EUR 10-13/month.
- Bandwidth remains within the free 100-GB outbound allowance.

## Ultra-lean subtotal versus qualifying MVP

An estimate of USD 14-19/month can describe an older, discounted, or cheaper-region prototype subtotal, but it is not the current Germany West Central B1ms total on the same basis as this report. The 2026-07-17 USD retail meters are:

| Ultra-lean item | Current Germany West Central amount |
| --- | ---: |
| `Standard_B1ms` Linux VM, 730 hours | USD 17.52/month |
| E4 32-GiB Standard SSD LRS base capacity | USD 2.40/month |
| 100 GiB Blob capacity | approximately USD 0.18-2.50/month, tier/replication dependent |
| Infrastructure subtotal before disk operations and outbound identity | **approximately USD 20.10-22.42/month** |
| Standard static public IPv4, if used | add USD 3.65/month |

This produces approximately USD 23.75-26.07/month before paid SSD transactions and backup. Allowing USD 1-5 for SSD transactions gives an operational ultra-lean range of roughly USD 25-31/month. Adding the conservative VM Backup allowance raises it by roughly USD 11-15/month.

The 32-GiB disk is also a capacity risk for the accepted design: the operating system shares it with the journal, local logs, raw-plus-candidate compaction space, recovery snapshots, and incident capture. The 2-GiB VM remains a prototype/measurement option rather than the recommended 30-day qualifying-paper node unless the 24-hour benchmark proves the memory, disk, latency, CPU-credit, and recovery budgets with adequate headroom.

High-case assumptions:

- The Standard SSD reaches its maximum paid transaction count every hour.
- Log ingestion reaches 10 GB/month, producing about EUR 13.12 of billable ingestion.
- Market evidence reaches 90 GB in the first month.
- Backup reaches the top of the stated allowance.

## Exclusions and uncertainty

- Prices exclude VAT and other taxes, support plans, trading capital, Binance fees, SMS/voice charges, domain/DNS purchases, and development or backtest compute outside the always-on node.
- The Retail Prices API returns list prices, not the user's contracted invoice price. Microsoft notes that EUR values are reference conversions and may change with exchange rates or offer terms.
- A price record does not guarantee that a VM SKU has deployment capacity in the user's subscription at deployment time; verify quota and availability in the Azure portal.
- This is a single-node cost model. A second VM, availability-zone failover, NAT Gateway, managed database, Azure Firewall, or cross-region disaster recovery would materially increase cost.
- Blob cost grows with retained evidence. Lifecycle tiering reduces capacity cost but introduces minimum-retention, retrieval, and rehydration tradeoffs that belong in the Azure deployment specification.
- Standard SSD transaction cost and B-series CPU credits are the largest variable infrastructure risks. The required 24-hour benchmark must measure both before committing to the 30-day paper qualification environment.

## Recommendation

Start with `Standard_B1ms`, one E6 64-GiB Standard SSD LRS disk, Hot ZRS evidence storage with lifecycle tiering, a Standard static IPv4 address, Key Vault Standard, and Azure Monitor capped below the included Log Analytics allowance. Do not add Azure VM Backup to the baseline; use the accepted verified application-level recoverable points. Plan **EUR 24-30/month before VAT**, alert at EUR 35, review at EUR 50, and resize first to `Standard_B2als_v2` only if the mandatory benchmark or recovery drills fail.
