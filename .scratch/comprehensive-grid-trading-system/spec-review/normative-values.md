# Current normative values (starter)

A single-source table of the **live** quantities in the spec, with **superseded** predecessors
marked. Proposed as a fix for CON-2 / IMP-1 (the retain-everything decision style scatters stale
numbers across records). Values below are transcribed from `../spec.md` and `../issues/*` as of the
2026-07-19 synthesis; **verify against the analysis docs before treating as authoritative.**

## Capital, sizing, orders

| Quantity | Current value | Source | Superseded values |
| --- | --- | --- | --- |
| First-live capital envelope (hard max) | **250 USDT** equiv (immutable per run) | spec §3; issue 06 | declined 100 / 500 / 1000 |
| Max principal (when min reserve applies) | **≤ 245 USDT** | spec §3 | — |
| Fee reserve | greater of **5 USDT** or **2× projected fees** (obligations + bounded terminal disposal) | spec §3; issue 06 | — |
| Exposure-increasing buy principal | **≤ 20 USDT** quantized | spec §3 | — |
| Fixed quote principal (search domain) | **10–20 USDT** | issue 07 | — |
| Max effective managed orders | **≤ 20** (one per rung) | spec §3; issue 06 | **11** (superseded, issue 06) |
| Configured rung count (search domain) | integer **5–21** | issue 07 | **5–20** then amended to 5–21; fixed **11** superseded |
| 21st-rung admission | only if activation lands on an initially inactive rung AND all reachable states stay ≤20 effective | issue 06/07 | — |
| Venue capacity headroom | greater of **10 slots** or **20%** of authenticated limit | spec §3 | — |

## Loss / risk thresholds (on flow-adjusted conservative liquidation equity)

| Quantity | Current value | Source |
| --- | --- | --- |
| Daily loss → `REDUCE_ONLY` | lesser of **2%** / **5 USDT** | spec §3 |
| Run drawdown → `REDUCE_ONLY` | lesser of **8%** / **20 USDT** | spec §3 |
| Terminal equity loss → global stop latch | lesser of **12%** / **30 USDT** | spec §3 |
| Warning threshold | **80%** of each accepted loss threshold | spec §3 |
| Stop-price safety buffer above terminal floor | **2%** of initial equity (≈225 USDT floor for a 250 envelope) | issue 06 |

## Freshness / timing deadlines (first-live provisional; paper may tighten)

| Quantity | Current value | Source |
| --- | --- | --- |
| Executable valuation freshness → `FROZEN` | **5 s** | spec §3; issue 06 |
| Strategy-input freshness → ≥`REDUCE_ONLY` | **15 s** | spec §3 |
| Full reconciliation cadence | startup + at least every **60 s** | spec §4 |
| REST control unavailability → `FROZEN` | **10 s** | spec §3 |
| Clock offset → `FROZEN` | **500 ms** | spec §3 |
| WebSocket rotation | before **23 h**, with overlap | spec §6 |
| External dead-man critical alert | **2 min** | spec §3 |
| Planned shutdown bound (warn 30 s) | **60 s** | issue 06 |
| Post-only retry sequence | **3** total `LIMIT_MAKER` within **10 s**; timers **250 ms** then **1 s** | spec §3 |
| Post-only displacement cap | lesser of **0.25%** of rung price or **25%** of adjacent gap | spec §3 |
| Terminal IOC disposal | each child ≤ remaining inv, **50 USDT**, **10%** of fresh depth, within **1%** worst-price band; ≤**5** attempts in **30 s** | issue 06 |

## Data / validation

| Quantity | Current value | Source |
| --- | --- | --- |
| History window | **60** quality-approved months = **48** dev + **12** locked holdout | spec §Acceptance 1 |
| Rolling folds | **8** × (24 train + 3 test) | spec §Acceptance 2 |
| Robustness panel | **5** symbols (≥4 incl. proposed must pass) | spec §Acceptance 4 |
| Regime matrix | **9** cells (3 trend × 3 vol); ≥5 positive; no cell >70% of positive profit | spec §Acceptance 5 |
| Sobol budget | **512** points / spacing stratum; ≤4 plateau seeds; 51-pt neighborhoods | spec §Acceptance 6; issue 07 |
| DSR confidence | **≥ 0.95** across full trial family | spec §Acceptance 7 |
| Return gates | rolling ≥6/8 positive qtrs, median ≥**0.75%**, annualized ≥**5.0%**; expanding ≥5/8, ≥**3.0%**; holdout ≥**4.0%** each fidelity | spec §Acceptance 8–9 |
| Fidelity-parity band | ≤**1.00 pp** return & max-drawdown between minute and event holdout | spec §Acceptance 9 |
| Adverse settings | fees max(1.25×, non-discounted); spread+slip max(1.5×, +5 bps); participation 5%→**2.5%**; queue-ahead ×2; latency max(2×, +500 ms) | issue 07 |

## Operations / promotion

| Quantity | Current value | Source |
| --- | --- | --- |
| Paper qualification | **30** consecutive UTC days (extend to **90** for activity) | spec §Acceptance 12–13 |
| Paper availability | ≥**99.5%** decision-ready; no unplanned interval >**30 min**; ≤**3h36m**/30d | spec §Acceptance 14; issue 07 |
| Testnet | **13** scenario families + **7** consecutive reset-free days | spec §Acceptance 16–17 |
| Activation | approve sealed digest, then re-auth + confirm within **15 min**, single-use, **2** fail-closed preflights | spec §Acceptance 21 |
| First-live probation | **30** days (extend to 90); daily reviews **7** days then weekly | spec §Acceptance 23 |

## Infrastructure / cost

| Quantity | Current value | Source |
| --- | --- | --- |
| VM | Linux **Standard_B1ms** (1 vCPU / 2 GiB), Germany West Central, no swap, ≥**384 MiB** free | spec §10; issue 11 |
| Resize path | B1ms → **B2als_v2** (2/4) → **B2as_v2** (2/8) | spec §Acceptance 31 |
| Disk | **64 GiB** E6 LRS Standard SSD | spec §10 |
| Storage | GPv2 **Hot ZRS**, Cool after 30 d, no Archive; versioning + 30-d soft delete + delete-lock | spec §10; issue 11 |
| RPO / RTO | **15 min** / **60 min** frozen | spec §8 |
| Backup cadence | nominal **10 min** on changed state | issue 08 |
| Journal commit p99 | ≤**250 ms** | spec §Acceptance 30 |
| Cost | ~EUR **24–30**/mo; warn **35**, review **50** | issue 11 |
| Coverage | **90%** branch (critical paths), **80%** overall | spec §11 |

## Superseded / reversed decisions to watch (do not implement)

| Superseded item | Replaced by | Source |
| --- | --- | --- |
| Fixed **11** configured rungs / 11 orders | validated 5–21 rungs, ≤20 effective orders | issue 06 |
| **Microsoft Entra OIDC** operator login | **SSH key** as sole human access gate | issue 12 |
| Key Vault **credential materializer** & early access variants | restricted direct Key Vault access, one-time `latest` at startup | issue 11 |
| Scheduled OS updates / Livepatch / reboot policy | **no maintenance** — `SECURITY_MAINTENANCE_DEFERRED` | issue 11 |
| Scrubber-only observability | approved-fields + central redactor + canaries | issue 12 |
