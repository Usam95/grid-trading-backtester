# 06 — Runtime, recovery, and availability findings

Capacity, RTO/RPO, reconciliation, and the operational envelope of the single Azure node.

---

## RUN-1 — B1ms (1 vCPU burstable, 2 GiB) will very likely fail the 24h capacity gate — plan for B2 · S2 · finding · `ready-for-human`

The 24h qualification runs **gateway + Production-Data Paper + Testnet + monitoring + capture +
backup + compaction + injected faults**, with **p99 journal commit ≤250 ms**, event-to-commit and
dispatch ≤1 s, **≥384 MiB free**, **no swap**, on **B1ms** (spec §Acceptance 29–31; issue 11).

Concerns specific to **B-series burstable**:
- **CPU credits:** B1ms earns credits at a low baseline; an always-on runtime with 2–4 persistent
  WebSockets, JSON serialization, SQLite WAL fsyncs, Parquet compaction, and backup upload can sit
  **above baseline for sustained periods**, depleting the credit bank and getting throttled — at
  which point the 250 ms p99 commit and 1 s deadlines are at serious risk.
- **Memory:** three CPython processes + SQLite page cache + capture buffers + compaction working set
  in **2 GiB with no swap and a 384 MiB reserve** is tight; a compaction/backup overlap spike can
  breach it and OOM-kill an authoritative writer.

The spec *anticipates* this (resize path to B2als_v2 → B2as_v2). The finding is to **expect
`RESIZE_REQUIRED`** and not treat B1ms acceptance as the likely outcome — budget the EUR delta and
schedule the requalification. Do not tune deadlines down to fit B1ms.

**Also:** compaction and backup are named as lower-priority/sheddable (spec §6), but they still
compete for the *same single vCPU credits*; verify the priority scheme actually protects commit
latency under credit throttling, not just under CPU scheduling.

---

## RUN-2 — 15-min RPO with a 10-min backup cadence leaves little margin on a throttled node · S2 · finding · `ready-for-agent`

Backups are "nominally every 10 minutes ... leaving 5 minutes for completion/retry/verification
inside the 15-minute RPO" and cap backup memory at 64 MiB with no heavy-phase overlap (issue 08).
On a **credit-throttled B1ms**, streaming compression + upload + readback-verify of a growing SQLite
DB may not reliably finish in 5 minutes, and "only a fully uploaded, verified, catalogued object is
a recovery point" (spec §8). A few missed verifications in a row silently pushes real RPO past 15
min until the **evidence-protection freeze** trips.

**Fix:** measure end-to-end backup wall-time under *throttled* conditions during the soak, not just
nominal; confirm the 5-minute margin holds, or lengthen the RPO / shrink the backup unit.

---

## RUN-3 — Recovery reconciles *late fills* but the grid is unmanaged during the outage · S2 · finding · `ready-for-human`

This is the operational face of SAF-1. Spec §6 correctly reconciles Binance-side late fills into
restored history and "never rolls Binance back." But between crash and `FROZEN_READY` (up to the
60-min RTO), **new fills are not paired/replaced**, inventory can drift, and risk postures cannot
act. On recovery the system is frozen and awaits the operator. So a crash during a volatile hour
means: orders kept executing, no risk control ran, and resumption is manual.

**Fix:** pair with SAF-1 mitigation (venue-native protective order and/or bounded inventory so the
unmanaged window is inside tolerance). Add the **"maximum adverse fills during RTO"** to the
recovery drill's success criteria, not just "reconciled correctly."

---

## RUN-4 — Single-writer ingress sequencer is a throughput/liveness chokepoint under burst · S3 · finding · `ready-for-agent`

Each runtime has **one durable ingress sequencer and one authoritative writer** (spec §6). Correct
for determinism, but it means every market tick, order event, timer, and command serializes through
one durable-commit path. Under a **market burst** (mass BBO/trade updates during a spike) plus
capture + backup, the single writer + fsync can become the bottleneck that trips the 1 s
event-to-commit deadline → `FROZEN`. The backpressure design (drop public-stream overflow to an
explicit gap; issue 09) mitigates but a **gap during a spike** is exactly when decisions matter.

**Fix:** validate the sequencer's sustained and burst commit throughput on the target VM early;
confirm "explicit gap under burst" does not routinely defeat decision-readiness during the very
volatility a grid needs to trade.

---

## RUN-5 — 60-min RTO drill uses "read-only recorded Binance reconciliation" — verify it exercises the hard path · S3 · finding · `ready-for-agent`

Monthly fresh-VM drills reconcile against **recorded/read-only** Binance evidence with **no trading
credentials** (issue 08). That validates restore/replay/invariants but **not** the live-credentialed
reconciliation + late-fill convergence + survivor-order cancellation path that a *real* live crash
would hit. The distinction matters because the riskiest recovery logic (cancel survivors, reconcile
ambiguous commands) only runs with real venue authority.

**Fix:** ensure at least the **Testnet** recovery drills exercise the full credentialed
survivor-cancel/late-fill path (issue 07's fault suite implies this — confirm the fresh-VM disaster
drill, specifically, covers it and not only the read-only variant).

---

## RUN-6 — "No auto-resume, ever" + burstable false-freezes may make 99.5% hard to hit · S3 · finding · `needs-info`

Combine SAF-4 (possible false clock/latency freezes), RUN-1 (credit throttling), and the strict
**no-auto-resume** rule (every freeze needs operator action) with the **99.5% decision-ready** gate
counting frozen time as unavailable (issue 07). A handful of spurious freezes requiring manual
resume during a 30-day unattended paper run could each blow the "no single unplanned interval
>30 min" sub-gate if the operator is asleep. Verify the freeze triggers are robust enough that the
*only* freezes are genuine, or the availability gate becomes an operator-responsiveness test.
