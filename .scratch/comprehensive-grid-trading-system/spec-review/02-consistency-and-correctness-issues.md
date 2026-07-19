# 02 — Consistency and correctness issues

Internal contradictions, stale/superseded values, and ambiguities that could cause an implementer
to build the wrong thing.

---

## CON-1 — Fee model is ambiguous: received-asset fees vs a held native reserve · S2 · issue · `needs-info`

Two fee models coexist in the spec without a single normative statement:

- **Received-asset model:** spec §User Story 27 ("actual net base received after native-asset fees")
  and §4 ("each fee counted once", "actual base, quote, and fee assets") describe Binance's default
  behavior where the commission is deducted from the asset you receive.
- **Held-reserve model:** spec §3 mandates a **fee reserve** = greater of 5 USDT or twice projected
  fees, "inside the capital envelope," and issue 06 says "discounts require authoritative proof and
  **allocated fee assets**" — implying a **BNB balance** held for the discount path.

These are materially different: with received-asset fees there is *nothing to reserve* (fees reduce
proceeds automatically); with a BNB reserve you must fund, track, replenish, and value a third
asset, and the adverse-fee scenario (non-discounted rate, spec §Acceptance 11) becomes a *balance*
question, not just a rate question.

**Impact:** net-cycle-margin math, invariant set, equity views, and the fee-reserve/principal
tradeoff ("principal ≤ 245 USDT", spec §3) all depend on which model is canonical.

**Fix:** state one canonical fee model (or make the reserve conditional on the discount path) and
make the ≥5 USDT reserve semantics explicit for each case.

---

## CON-2 — Superseded numeric/architectural decisions remain inline and can mislead · S3 · issue · `ready-for-agent`

Decision records deliberately retain superseded choices (good for provenance) but several **stale
numbers/architectures** are easy to lift by mistake:

- **11 configured rungs / 11 concurrent orders** (issue 06, 2026-07-15) was **superseded** by
  "rung count is a validated search parameter, 20 effective orders" (issue 06, later same day; spec
  §3 and §Acceptance settle on 5–21 rungs / ≤20 effective orders).
- **Microsoft Entra OIDC login** (issue 12, first entry) was **superseded** by "SSH key is the sole
  human access gate" (issue 12, next entry).
- **Key Vault "credential materializer" / several access variants** (issue 11) were iterated
  before landing on restricted direct access.

**Fix (cheap, high value):** add a single **"Current normative values"** table to `spec.md` (or a
new `spec-review/normative-values.md`) listing the *live* value for every quantity and every
superseded predecessor marked `SUPERSEDED`. This removes the main risk of the retain-everything
style. See `normative-values.md` in this folder for a starter.

---

## CON-3 — "Neutral" grid is structurally net-long; naming may set wrong expectations · S3 · issue · `ready-for-human`

The strategy is described as a **static neutral Spot grid** (map; spec §Solution), but because it
must **bootstrap-acquire base inventory to back every initial sell** (spec §User Story 22, §3), the
position at activation is **long the base asset** by construction, and remains long down to the
stop. Its risk profile is "long inventory + range-scalping," not market-neutral.

**Impact:** drawdown, terminal-loss, and regime expectations are dominated by base-asset price
decline, not by grid mechanics. Calling it "neutral" can mislead the operator (who is explicitly
still learning, spec §Problem Statement).

**Fix:** rename to "static **inventory** grid" or add one sentence clarifying the net-long exposure
and that the stop-loss is effectively a long-position stop.

---

## CON-4 — The 20-order ceiling is largely nominal under the 250 USDT envelope · S3 · issue · `ready-for-agent`

Spec §3 permits **≤20 effective managed orders** and **≤20 USDT per exposure-increasing buy**, but
the **250 USDT envelope** (minus base inventory value and ≥5 USDT fee reserve) cannot simultaneously
fund anywhere near 20 buys at 20 USDT. The *binding* constraint is capital, not the order count, so
the "20 orders" limit rarely bites at max principal.

This is not a contradiction, but the spec presents the 20-order ceiling as a primary risk control
when it is mostly redundant given capital. Worth a note so implementers don't build elaborate
order-count logic expecting it to be the active limit. Confirm the intended interaction (buys below
activation share capital with sells' backing inventory).

---

## CON-5 — "Rung count includes both bounds" + activation-on-rung + ≤20 effective needs a worked invariant · S3 · issue · `ready-for-agent`

Spec §User Stories 3–4 and issue 06 (21-rung admission only when activation lands on an initially
inactive rung and every reachable state stays ≤20 effective) define a subtle off-by-one/occupancy
invariant. This is stated prose-only. Given it gates a hard capital/venue limit, it should ship as
an **executable property test with a worked numeric fixture** (the 21-rung boundary case) rather
than remain narrative. Flagging so it is not lost between "configured" and "effective" counts.

---

## CON-6 — Availability arithmetic: "99.5% over 30 days" vs "≤3h36m" vs "extend to 90 days" · S3 · issue · `needs-info`

Spec §Acceptance/issue 07 state ≥99.5% decision-ready over the interval, "≤3h36m total
unavailability in 30 days," and "no single unplanned interval >30 min," *and* the run may extend to
90 days for activity. 99.5% of 30 days = 3.6h (consistent), but over a **90-day** extension 99.5%
would allow ~10.8h. Confirm whether the absolute 3h36m cap is per-30-days or per-whole-interval when
the run extends, and which dominates. Minor but it is a pass/fail boundary.

---

## CON-7 — Binance API assumptions are dated (2026-07) and must be re-verified before live · S2 · issue · `needs-info`

The venue contract (issue 05) fixes `LIMIT_MAKER`, listenKey user-data streams, REST filters, etc.
Binance changes these: Ed25519/RSA keys, session-logon over the WebSocket API, user-data-stream via
WS API, SBE, and periodic deprecations. The research is a **point-in-time snapshot**. Add a
mandatory **"re-verify current Binance Spot API"** step in the live-preflight/change-impact matrix,
not just at spec time, so an API change during the multi-month qualification does not invalidate the
adapter silently.
