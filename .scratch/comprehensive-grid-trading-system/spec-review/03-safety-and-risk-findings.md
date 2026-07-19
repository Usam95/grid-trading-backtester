# 03 — Safety and risk findings

Focused on the safety-state machine, the mandatory global stop-loss, and failure modes that could
affect real capital.

---

## SAF-1 — The mandatory global stop-loss cannot fire while the single node is down · S1 · finding · `ready-for-human`

The design is single-node, **no application HA**, with a **60-minute frozen RTO** and "trading
resume is outside RTO" (spec §8, §Acceptance 28). During VM/disk loss (or any crash + slow
supervisor replacement), the runtime is not evaluating anything for up to an hour+.

But the grid's **resting orders remain live on Binance**, and — critically — the **terminal
global stop-loss is enforced by the runtime, not by Binance**. Spec §3/§6 place the stop as a
*domain* evaluation over conservative liquidation equity / executable-side price, executed via
runtime-driven IOC disposal. Therefore, **while the only node is down**:

- resting buys can keep filling → inventory grows,
- price can fall **through** the stop with **no terminal disposal firing**,
- the operator's sole intervention is SSH-from-allowlisted-IP or the read-only mobile alert.

**Net effect:** the "mandatory" stop-loss is best-effort, conditional on node liveness. For a
250 USDT probation this is a bounded loss, but it contradicts the spec's framing of the stop as
non-negotiable, and it will not scale.

**Options to consider (decide explicitly, don't leave implicit):**
1. Place a **venue-native protective order** (e.g., a resting `STOP_LOSS_LIMIT`/`OCO` sell of the
   whole inventory just below the stop) so Binance enforces a floor even when the node is dead —
   reconciled by the runtime on recovery. This is the standard mitigation for grid bots.
2. Reduce first-live inventory so worst-case gap loss during a full RTO window is inside the
   accepted terminal loss even with **zero** runtime action.
3. Accept and *document* explicitly that the stop is liveness-conditional and quantify the maximum
   unmanaged loss over a 60-minute (and a "night-time unattended") window.

---

## SAF-2 — Gap-through loss on a long-inventory spot book is only "reported," not bounded · S1 · finding · `ready-for-human`

Issue 06 acknowledges "gaps remain possible" and 1%/3%/5% gap-through stresses "report the
remaining non-guarantee." Crypto routinely gaps far more than 5% (flash crashes, exchange-specific
wicks). Because the position is **net-long inventory** (CON-3) all the way to the stop, a gap
through the stop realizes loss on the *entire* inventory at once via IOC into a thin book.

The spec's safety buffer (stop ≥ terminal floor + 2% of initial equity, issue 06) protects against
*ordinary* traversal, not against gap + thin-book slippage during forced IOC disposal.

**Ask:** quantify worst-case IOC disposal slippage against the **actual observed depth** of the
proposed symbol (not a modeled 5%), and confirm the 250 USDT envelope keeps even a 10–20% gap +
thin-book exit inside the operator's true loss tolerance. Consider a venue-native protective order
(SAF-1 option 1) as the same mitigation.

---

## SAF-3 — No handling for venue-side symbol halt / delist / maintenance during a run · S2 · finding · `needs-info`

The spec covers venue-**rule** changes, foreign activity, stream gaps, and rate limits, but I did
not find explicit handling for **Binance suspending trading on the live symbol**, a **maintenance
window on that pair**, or a **delisting notice** mid-run — all realistic over a 30–90 day live
probation. In these states: no fills, cancels may fail, `LIMIT_MAKER` may be rejected wholesale,
and the stop-loss cannot execute (no market).

**Fix:** add a canonical "**venue trading suspended for symbol**" condition to the safety/anomaly
matrix (issue 06) with a defined posture (likely `FROZEN`, preserve inventory, alert, await
resumption or operator disposal) and a delist runbook (managed wind-down before the delist date).

---

## SAF-4 — Clock-offset freeze (>500 ms) may false-trigger on a burstable VM · S2 · finding · `ready-for-agent`

Spec §3: clock offset beyond **500 ms** selects `FROZEN`. On a **B1ms burstable** VM, scheduler
jitter, CPU-credit throttling, and NTP correction can transiently exceed 500 ms of apparent offset
under load — precisely during the busy periods you least want a spurious freeze. Combined with the
60-second reconciliation and no auto-resume, repeated false freezes could shred the 99.5%
availability gate.

**Fix:** define the offset as a **smoothed/median** measurement over a short window with a debounce,
distinguish *measured venue-time skew* from *local scheduling latency*, and validate the threshold
empirically during the 24h B1ms soak before treating 500 ms as canonical.

---

## SAF-5 — "Fail-closed on unknown" can deadlock into a manual-only state; define the exit · S2 · finding · `needs-info`

The pervasive fail-closed posture (unknown command/order/fill/balance → `FROZEN`, no auto-resume,
manual approval after material frozen incidents; spec §User Story 49–50, issue 06) is correct for
safety but creates an operational trap: a persistent ambiguous condition (e.g., Binance returns
`UNKNOWN` repeatedly, or a reconciliation item cannot converge) can leave the system **frozen
indefinitely with live inventory** and only manual exit. That is *safe from over-trading* but not
safe from *market risk* on the frozen inventory.

**Ask:** specify the **maximum frozen-with-inventory duration** and what the operator is expected to
do (bounded manual disposal path). The spec has the *mechanisms* (operator stop, terminal disposal)
but not a *time-bound expectation* for resolving a stuck freeze while long.

---

## SAF-6 — Emergency Stop in the browser has no confirmation — verify accidental-trigger cost · S3 · finding · `ready-for-agent`

Issue 10: Emergency Stop is **immediately accessible, no confirmation**, blocks/cancels all but does
**not** liquidate. So an accidental click halts trading and forces a reconcile+manual resume — safe,
but disruptive during an unattended live run (cancels all resting orders; grid must be rebuilt).
Confirm this is acceptable, or add a 1-second press-and-hold / undo window that cannot delay a
genuine emergency.
