# Current normative values

Status: authoritative catalogue for the Ticket 01 baseline  
Effective: 2026-07-19  
Authority: comprehensive specification plus its linked accepted decision records

Only values in the **Current value** column are effective. The final section is
visibly non-normative and exists to prevent retained decision history from being
implemented accidentally. Where this catalogue is less strict than an accepted
decision record, that record controls until both are reconciled explicitly.

## Capital, sizing, orders, and loss

| Quantity | Current value | Normative source |
| --- | --- | --- |
| First-live grid capital envelope | **≤ 250 USDT** equivalent, immutable per run | comprehensive spec §3 |
| Principal with minimum reserve | **≤ 245 USDT** | comprehensive spec §3 |
| Fee reserve | greater of **5 USDT** or **2× projected fees** for obligations plus bounded terminal disposal | comprehensive spec §3 |
| Exposure-increasing buy principal | **≤ 20 USDT**, quantized | comprehensive spec §3 |
| Fixed quote principal search domain | **10–20 USDT** | validation decision record |
| Effective managed grid orders | **≤ 20**, one per rung | comprehensive spec §3 |
| Configured rung-count search domain | integer **5–21**; a 21st rung is admissible only when every reachable state remains within 20 effective orders | risk and validation decision records |
| Venue order headroom | greater of **10 slots** or **20%** of the authenticated venue limit | comprehensive spec §3 |
| Daily loss → `REDUCE_ONLY` | lesser of **2%** and **5 USDT** | comprehensive spec §3 |
| Run drawdown → `REDUCE_ONLY` | lesser of **8%** and **20 USDT** | comprehensive spec §3 |
| Terminal equity loss → global stop | lesser of **12%** and **30 USDT** | comprehensive spec §3 |
| Loss warning | **80%** of each accepted loss threshold | comprehensive spec §3 |
| Stop-price safety buffer | **2%** of initial equity | risk decision record |

## Freshness, retries, and operational deadlines

| Quantity | Current value | Normative source |
| --- | --- | --- |
| Executable valuation freshness | older than **5 s** → `FROZEN` | comprehensive spec §3 |
| Strategy-input freshness | older than **15 s** → at least `REDUCE_ONLY` | comprehensive spec §3 |
| Authenticated control-path outage | **10 s** → `FROZEN` | comprehensive spec §3 |
| Clock offset | beyond **500 ms**, or timestamp rejection → `FROZEN` | comprehensive spec §3 |
| Full authenticated reconciliation | startup and at least every **60 s**, plus named triggers | comprehensive spec §4 |
| WebSocket rotation | before **23 h**, with overlap | comprehensive spec §6 |
| External dead-man critical alert | **2 min** | risk decision record |
| Planned shutdown | warn at **30 s**; bound **60 s** | risk decision record |
| Post-only placement sequence | **3 total attempts** within **10 s**; waits **250 ms**, then **1 s** | comprehensive spec §2 |
| Post-only displacement | lesser of **0.25%** of rung price or **25%** of adjacent gap | comprehensive spec §2 |
| Terminal IOC child | ≤ remaining inventory, **50 USDT**, **10%** of fresh depth, within **1%** worst-price band | risk decision record |
| Terminal IOC sequence | **≤ 5 attempts in 30 s** | risk decision record |
| Health/metric age | **≤ 30 s** | comprehensive spec acceptance 30 |
| Journal commit p99 | **≤ 250 ms** | comprehensive spec acceptance 30 |
| Event receipt→commit p99 | **≤ 1 s** | comprehensive spec acceptance 30 |
| Dispatch-ready→attempt p99 | **≤ 1 s** | comprehensive spec acceptance 30 |
| Protected health p95 | **≤ 500 ms** | comprehensive spec acceptance 30 |

## Research and validation thresholds

| Quantity | Current value | Normative source |
| --- | --- | --- |
| Historical window | **60** approved months: **48** development + **12** locked holdout | comprehensive spec acceptance 1 |
| Rolling folds | **8 ×** (24 training months + 3 test months) | comprehensive spec acceptance 2 |
| Robustness panel | **5** symbols; proposed plus at least four of five pass | comprehensive spec acceptance 4 |
| Regime support | each trend/volatility class **≥ 60 days**; each cell **≥ 20 days** | comprehensive spec acceptance 5 |
| Positive regimes | **≥ 5 of 9** plus aggregate sideways; no positive cell contributes over **70%** of positive-cell profit | comprehensive spec acceptance 5 |
| Search budget | **512** Sobol points per spacing stratum; **≤ 4** plateau seeds; **51-point** neighborhoods | comprehensive spec acceptance 6 |
| Deflated Sharpe Ratio confidence | **≥ 0.95** | comprehensive spec acceptance 7 |
| Rolling return gates | **≥ 6/8** positive quarters; median **≥ 0.75%**; linked annualized **≥ 5.0%** | comprehensive spec acceptance 8 |
| Expanding return gates | **≥ 5/8** positive quarters; annualized **≥ 3.0%** | comprehensive spec acceptance 8 |
| Holdout return | minute and event holdouts each **≥ 4.0%** | comprehensive spec acceptance 9 |
| Cross-fidelity difference | absolute return and max-drawdown differences each **≤ 1 percentage point** | comprehensive spec acceptance 9 |
| Cycle evidence | rolling/expanding each **≥ 24** cycles; ≥2 in six of eight folds; each holdout **≥ 12** cycles across ≥8 UTC months | comprehensive spec acceptance 10 |
| Paper participation | baseline **≤ 5%** of reusable observed volume; adverse **2.5%** | comprehensive spec §5 and acceptance 11 |
| Adverse queue ahead | **2×** baseline | validation decision record |

## Qualification and promotion intervals

| Quantity | Current value | Normative source |
| --- | --- | --- |
| Production-Data Paper qualification | **30 consecutive UTC days**, extend unchanged to **90 days** only for activity | comprehensive spec acceptance 12–13 |
| Paper natural activity | **≥ 2** paired cycles and ordinary fills on **≥ 3 UTC dates** | comprehensive spec acceptance 13 |
| Paper decision-ready availability | **≥ 99.5%**; unavailable **≤ 3 h 36 min / 30 d**; no unplanned interval over **30 min** | comprehensive spec acceptance 14 and §7 |
| Paper planned recovery evidence | **≥ 3 restarts**, one with a resting order, plus named fault drills | comprehensive spec acceptance 15 |
| Testnet campaign | **13** scenario families + **7 consecutive reset-free days** | comprehensive spec acceptance 16–17 |
| Paper start freshness | no later than **30 elapsed days** after locked holdout endpoint | comprehensive spec acceptance 19 |
| Promotion evidence freshness | complete Paper and Testnet/reconciliation endpoints each **≤ 24 h** old | comprehensive spec acceptance 20 |
| Live confirmation | re-authenticate and confirm within **15 domain minutes**; single use; **2** fresh fail-closed preflights | comprehensive spec acceptance 21 |
| First-live probation | **30 days**, extend unchanged to **90 days** only for activity | comprehensive spec acceptance 23–24 |
| First-live probation activity | **≥ 1** real cumulative paired cycle and ordinary live fills on **≥ 2 UTC dates** | comprehensive spec acceptance 24 |
| Probation review cadence | daily for first **7 UTC observation days**, then at least once per **7-day** interval | comprehensive spec acceptance 23 |

## Retention, recovery, infrastructure, and cost

| Quantity | Current value | Normative source |
| --- | --- | --- |
| Local JSONL diagnostic rotation | **7 days or 500 MiB**, whichever comes first | comprehensive spec §7 |
| Collected logs and spans | **30 days** | comprehensive spec §7 |
| Low-cardinality metrics | **120 days** | comprehensive spec §7 |
| Raw diff-depth ring | **5 min**, unless a material incident seals it | comprehensive spec §8 |
| Complete authoritative evidence: journals, configurations, schemas, migrations, operator actions, accounting, reconciliation, risk, lifecycle, live venue facts, and incident history | **Life of the system** | comprehensive spec §8 |
| Exact promotion datasets and captures | **Life of the system** | comprehensive spec §8 |
| Qualifying Paper, Testnet, and first-live bundles | **Life of the system** | comprehensive spec §8 |
| Critical incidents | **Life of the system** | comprehensive spec §8 |
| Failed non-promoted Paper/Testnet evidence | **1 year** | comprehensive spec §8 |
| Warning incident bundles and non-promoted full replays | **1 year** | comprehensive spec §8 |
| Backup cadence while protected state advances | nominally every **10 min** | comprehensive spec §8 |
| Protected-state objective | **15 min RPO**; **60 min frozen RTO** | comprehensive spec §8 |
| Verified recoverable points | one per UTC day for **30 days**, plus named change points | comprehensive spec §8 |
| Restore/disaster cadence | isolated restore **weekly**; fresh-VM drill **monthly** and at named gates | comprehensive spec §8 |
| Azure VM baseline | `Standard_B1ms`, **1 vCPU / 2 GiB**, no swap, **≥ 384 MiB** available | comprehensive spec §10 and acceptance 29 |
| Capacity campaign | **24 h** representative workload | comprehensive spec acceptance 29 |
| Resize path | `B1ms` → `B2als_v2` (**2/4**) → `B2as_v2` (**2/8**) | comprehensive spec acceptance 31 |
| Managed disk | **64 GiB E6 LRS** Standard SSD | comprehensive spec §10 |
| Blob tier | new objects Hot ZRS; eligible closed evidence Cool after **30 days**; no automatic Archive | comprehensive spec §10 |
| Azure cost thresholds | warn at **EUR 35**; operator-review incident at **EUR 50** | comprehensive spec §10 |
| Branch coverage | **90%** critical packages; **80%** production overall | comprehensive spec §11 |

## Superseded values (not effective)

The following retained historical decisions are **excluded** from implementation:

| Superseded item | Effective replacement | Decision source |
| --- | --- | --- |
| Engine runtime version **1.1.0** conflicting with package/Studio **1.0.0** | root `VERSION` is authoritative; all Ticket 01 surfaces report **1.0.0** | verification/release decision 5 |
| Fixed **11** configured rungs / 11 orders | validated **5–21** rungs with **≤ 20** effective orders | risk and validation records |
| Rung domain **5–20** | amended **5–21** domain with the 21st-rung admission rule | validation record |
| Microsoft Entra OIDC operator login | source-IP-restricted non-root **SSH key** is the sole human access gate | security record |
| Key Vault credential materializer and early access variants | restricted direct Key Vault access; resolve `latest` once during frozen startup and pin exact version | security/Azure records |
| Scheduled OS updates, Livepatch, and reboot policy | accepted visible `SECURITY_MAINTENANCE_DEFERRED` exception for MVP1 | Azure record |
| Scrubber-only observability | approved fields/types plus centralized recursive redaction and canary tests | security record |
