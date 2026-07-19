# 01 — Doubts and open questions

Items here need a human decision or a fact the spec does not settle. Each is phrased so it can
become a numbered issue ticket if the operator wants to reopen a topic.

---

## VAL-1 — Are the DSR gate and the return gate jointly satisfiable? · S1 · doubt · `needs-info`

Issue 07 sets a **Deflated Sharpe Ratio ≥ 0.95** across the *full non-duplicated trial family*
(spec §Acceptance 7), while the trial family can reach ~81,920 broad + ~32,640–40,960 refinement
points (issue 07, 2026-07-15 budget entries). DSR deflation grows with the number of trials and
their variance; clearing 0.95 after ~10^5 trials typically requires a **high raw Sharpe**.

Meanwhile the return gate is deliberately *modest*: rolling median quarterly ≥0.75%, annualized
≥5%, holdout ≥4% (spec §Acceptance 8–9). Grid strategies characteristically produce **many small,
serially-dependent** cycle returns — often a low Sharpe even when profitable.

**Doubt:** these two gates may pull in opposite directions — a candidate strong enough to pass DSR
after 10^5 trials may need returns well above the "modest" thresholds, and a candidate that only
just clears 5% may never clear DSR 0.95. Before implementation, run a **paper feasibility study**:
does any plausible candidate clear *both*? If not, the deflation baseline (trial count, variance
estimator, return frequency for the Sharpe) needs recalibration, or DSR should become diagnostic.

**Ask:** confirm the DSR estimator inputs (return frequency, trial-count definition, variance
assumption) and validate joint feasibility on at least one real symbol before freezing the gate.

---

## VAL-2 — Can five symbols with 60 quality-approved months *and* grid-suitable behavior be found? · S1 · doubt · `needs-info`

The frozen robustness panel needs **five** eligible USDT-Spot symbols, each with **60 consecutive
quality-approved months** (5 years) and persistent development-period liquidity (spec §Acceptance
1, 4; issue 07). Grids profit in **ranging / mean-reverting** markets and are penalized by strong
trends.

Two facts collide:
1. The symbols with a clean 5-year Binance USDT history are mostly **majors** (BTC, ETH, BNB, LTC,
   XRP, ADA, …) which have spent long stretches strongly trending — the *worst* case for a neutral
   grid that must pre-buy inventory.
2. The mid-cap / range-bound pairs that suit grids often **lack** 5 clean years or have quality
   gaps that the fail-closed data policy (issue 07) will quarantine.

**Doubt:** the eligibility filter may leave a panel dominated by trend-heavy majors, making the
positive-across-regimes gates (§Acceptance 5) hard to pass for the strategy that is actually being
sold. Confirm the eligible universe empirically and check the proposed live symbol is both
history-eligible and grid-suitable.

---

## DBT-3 — Is the fee reserve denominated in BNB or taken from the received asset? · S2 · doubt · `needs-info`

See CON-1 (file 02). The spec simultaneously implies (a) fees are deducted from the received asset
("actual net base received after native-asset fees", spec §User Story 27) and (b) a **held native
fee reserve** of ≥5 USDT inside the envelope (spec §3). These are two different fee models with
different accounting, net-cycle-margin, and adverse-scenario consequences. Decide explicitly:
**BNB-funded fees (discount path)** or **received-asset fees (no discount)** — or support both and
make the reserve conditional.

---

## DBT-4 — Who acts on the dead-man alert, and how, if the operator is unreachable? · S2 · doubt · `ready-for-human`

The design relies on a single operator, mobile channel is **read-only**, and remote control is
**SSH only from a declared source IP** (issues 10, 11, 12). The external dead-man fires in 2 minutes
(spec §3). But if the operator is asleep/traveling/off-IP, **no one can intervene** and the node
has no HA. For real money this is the whole safety story reducing to "operator answers the phone
and is near an allowlisted machine."

**Ask:** define an explicit, tested *unavailable-operator* runbook and an acceptable maximum
unattended window for live money. Consider whether the runtime should auto-`FROZEN`/`REDUCE_ONLY`
after N minutes of unacknowledged critical alert (a bounded automatic de-risking, not
liquidation).

---

## DBT-5 — Is a 7-day *reset-free* Testnet soak achievable given Binance Testnet reset cadence? · S2 · doubt · `needs-info`

Issue 07 requires **seven consecutive reset-free** Testnet days on one account generation, and a
reset restarts the soak. Binance **periodically wipes the Spot Testnet** (announced, roughly
monthly, sometimes more often) and it suffers outages and thin/odd liquidity. The gate could be
blocked by Binance's schedule rather than by the system.

**Ask:** confirm current Testnet reset cadence and add an explicit policy for "reset outside our
control" so the campaign can resume without being treated as a system failure (the spec treats a
reset as restarting the soak but does not bound how often that could recur).

---

## DBT-6 — Should the MVP spend on always-on Azure during the (≈3-week, extendable) shakedown? · S3 · doubt · `ready-for-human`

Issue 11 defines a flexible shakedown *before* the 30-day qualifying clock. The always-on B1ms +
storage + monitoring runs the full EUR 24–30/month during shakedown, which may be lengthy. See
OPT-2 (file 08) for a possible deferral. Decide whether shakedown must be on Azure or may use
cheaper capacity until the qualifying clock starts.

---

## DBT-7 — What is the authoritative source and license for 5-year 1-minute history? · S3 · doubt · `needs-info`

The data policy (issue 07) mandates checksums, manifests, and fail-closed gap handling, but the
**acquisition method** is unnamed (Binance public data dumps vs REST klines vs a vendor). Binance's
own dumps have known bad/duplicated candles and occasional missing days. Naming the source and its
known-defect handling avoids surprises during the (single-use) holdout construction.
