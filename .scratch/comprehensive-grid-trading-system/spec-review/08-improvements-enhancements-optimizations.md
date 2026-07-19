# 08 — Improvements, enhancements, and optimizations

Non-blocking betterments. These do not challenge the spec's correctness; they make it cheaper,
faster, clearer, or more robust.

## Improvements (clarity / robustness)

- **IMP-1 · S2 · Add a single "Current normative values" table.** The retain-everything decision
  style is great for provenance but risky for implementation (see CON-2). One canonical table of
  live quantities (ceilings, thresholds, deadlines, sizes) with superseded predecessors marked,
  referenced from `spec.md`, removes most stale-number risk. A starter is in
  [`normative-values.md`](normative-values.md).

- **IMP-2 · S2 · Publish worked numeric reference vectors in the root spec.** The deep analysis
  docs hold examples, but `spec.md` (the "implementation-ready root contract") has none. Ship 3–5
  golden fixtures inline: a full bootstrap→cycle→paired-sell with native fees; the 21-rung boundary
  occupancy case (CON-5); a terminal IOC disposal with dust; a duplicate/late-fill reconciliation.
  These double as the first golden-replay tests.

- **IMP-3 · S2 · State the net-long exposure and the economic premise plainly.** One paragraph each
  for CON-3 (not market-neutral) and ECO-1 (net-negative vs infra at 250 USDT) in the problem
  statement. The operator is described as still learning; these are the two facts most likely to be
  misunderstood.

- **IMP-4 · S3 · Add venue trading-suspension / delist to the anomaly matrix.** See SAF-3. Small
  addition, closes a realistic multi-month-run gap.

- **IMP-5 · S3 · Make "re-verify current Binance API" a live-preflight step.** See CON-7. The
  venue contract is a dated snapshot; bind a re-verification to activation and to the change-impact
  matrix.

- **IMP-6 · S3 · Debounce/median the freshness & clock-offset triggers.** See SAF-4/RUN-6. Prevents
  burstable-VM jitter from manufacturing freezes that then require manual resume and threaten the
  availability gate.

## Enhancements (capability)

- **ENH-1 · S1-adjacent · Venue-native protective stop (OCO/STOP_LOSS_LIMIT) mirroring the domain
  stop.** The single highest-value robustness change: gives the mandatory stop a chance to fire when
  the node is down or lagging (SAF-1/SAF-2/RUN-3). Reconciled by the runtime on recovery; never the
  sole authority, but a genuine floor. Fits the existing "reconcile venue truth" model.

- **ENH-2 · S3 · Bounded automatic de-risk on unacknowledged critical alert.** After N minutes of
  unacknowledged critical + operator unreachable, auto-select `REDUCE_ONLY` (cancel buys, keep
  reducing sells) — a bounded, non-liquidating safety net for the unattended single-operator case
  (DBT-4). Not auto-liquidation; consistent with the fail-closed ethos.

- **ENH-3 · S3 · Risk-free-yield reference line in reports.** See ECO-5. Cheap, and it keeps the
  operator honest about opportunity cost.

- **ENH-4 · S3 · Use Binance `cancelReplace` / order-list where safe to reduce placement latency and
  rate use.** Ordinary rung re-pricing (spec §3 bounded displacement) currently implies
  cancel-then-place; `cancelReplace` is atomic and halves round-trips — but preserve the durable
  managed-identity + `UNKNOWN` handling (spec §6). Verify against current API (CON-7).

- **ENH-5 · S3 · Prefer the Binance user-data-stream + WebSocket API over REST polling for order/
  balance updates** to cut latency and REST rate pressure on the tiny VM (RUN-1/RUN-4). Keep REST
  as the authoritative reconciliation/repair path.

## Optimizations (cost / performance)

- **OPT-1 · S2 · Azure Reserved Instance / Savings Plan for the always-on VM.** A 1- or 3-year
  reservation on the (by definition always-on) VM typically cuts compute ~30–40%, materially
  improving the ECO-1 picture for a long-running validation program. Storage/monitoring unaffected.
  Revisit after the B1ms-vs-B2 capacity decision (RUN-1) so you reserve the right SKU.

- **OPT-2 · S3 · Defer always-on Azure spend during the (extendable) shakedown.** See DBT-6. The
  shakedown (issue 11) can be lengthy; running it on the laptop or on a stop/start VM until the
  qualifying clock starts saves weeks of EUR 24–30/mo. The qualifying run must be on the accepted
  Azure profile; the shakedown arguably need not be, provided the acceptance runner re-proves the
  environment before the clock.

- **OPT-3 · S3 · Stop the Testnet runtime during first-live to reclaim B1ms headroom.** Live uses a
  fresh runtime and Testnet/live are mutually exclusive (issues 09, 11); explicitly shutting Testnet
  down for the live probation frees a whole process worth of CPU credits/memory on the constrained
  node — possibly the difference between B1ms and a resize (RUN-1).

- **OPT-4 · S3 · Cool-tier / lifecycle the capture Parquet aggressively.** Market capture is the
  main storage growth driver (spec §8). The 30-day Hot→Cool rule exists; confirm capture objects are
  eligible early and that the growth guardrails (issue 11) key off *capture* volume specifically,
  since that's what will dominate the bill and the SEC-6 runaway risk.

- **OPT-5 · S3 · Batch/parallelize the research search off the online node (already intended) with
  spot/low-priority compute.** The search budget (up to ~10^5 broad points) is embarrassingly
  parallel and non-authoritative; temporary Azure Spot VMs or the laptop are far cheaper than
  keeping capacity around, and the spec already forbids sizing the online node for research (issue
  07/11). Just confirm the batch tier uses interruptible/cheap capacity.
