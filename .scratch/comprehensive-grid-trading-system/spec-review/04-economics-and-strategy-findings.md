# 04 — Economics and strategy findings

Whether the MVP, as gated, can make economic sense and whether the grid mechanics are feasible at
the chosen scale.

---

## ECO-1 — At 250 USDT, infrastructure cost exceeds every passing return threshold · S1 · finding · `ready-for-human`

The passing bar is deliberately modest (spec §Acceptance 8–9): annualized ≥5% rolling, holdout
≥4%. On a **250 USDT** envelope:

- 5%/yr ≈ **12.5 USDT/year**; 4% holdout ≈ **10 USDT**.
- Azure runs at **EUR 24–30/month ≈ EUR 288–360/year** (issue 11), warning at EUR 35, review at
  EUR 50.

So the always-on infrastructure costs **~25–30×** the *best-case* annual trading profit. The MVP is
**net-negative by construction** at this capital, before Binance fees and the operator's time.

This is almost certainly intentional — the spec repeatedly frames the MVP as a **learning and
validation** exercise (spec §Problem Statement) and the thresholds are **percentages** that scale.
But it is not stated in cost terms anywhere, and an operator "still learning" (spec's own words)
should see it explicitly.

**Fix:** add one paragraph to §Problem Statement / §Acceptance stating that the 250 USDT MVP is
expected to be **net-negative after infrastructure** and exists to prove correctness/parity/
operations; profitability is a *scaling* question deferred behind a separate capital-increase
decision. Optionally define the **capital level at which % thresholds cover Azure cost** (≈ EUR
300/yr ÷ 5% ≈ **6,000 USDT** just to break even on infra at the 5% bar) as forward guidance.

---

## ECO-2 — 10–20 USDT orders collide with Binance minNotional/stepSize; the net-positive-cycle gate is fragile · S2 · finding · `ready-for-agent`

Search domain: fixed quote principal **10–20 USDT** (issue 07). Binance Spot `MIN_NOTIONAL` is
commonly **5–10 USDT** and `LOT_SIZE.stepSize` / `PRICE_FILTER.tickSize` force quantization. At
these tiny notionals:

- Quantization rounding can be a **meaningful fraction** of the per-cycle margin.
- The mandatory "every adjacent cycle net-positive after fees, rounding, execution allowance, and
  safety margin" gate (spec §User Story 29) becomes **tight**: with ~0.1% maker fee round-trip
  (0.2%) plus rounding on a 10 USDT order, the geometric step must clear ~0.3–0.5%+ to be reliably
  positive, which constrains rung count against the 5–30% bound range.
- **Dust** accumulation (spec §4 residual handling) is proportionally larger at small sizes and can
  strand base that fails `MIN_NOTIONAL` on disposal.

**Impact:** the feasible parameter region may be much smaller than the search domain implies, and
some "valid" candidates will fail venue admission. This interacts with VAL-1 (few candidates may
survive all gates).

**Fix:** run a **venue-quantization feasibility pass** on the proposed symbol's *actual* filters
early, and confirm the net-positive-cycle gate is satisfiable across the intended rung/step range
at 10–20 USDT. Consider raising the minimum principal if the proposed symbol's filters demand it.

---

## ECO-3 — Bootstrap taker cost + long inventory is a persistent, front-loaded drag · S2 · finding · `ready-for-agent`

Activation performs an **aggressive (taker) bootstrap** to acquire base backing every initial sell
(spec §3, §User Story 22). This incurs taker fee + spread + slippage **up front**, and leaves the
allocation heavily in base inventory that must appreciate or be scalped to overcome the drag.

For a grid whose per-cycle edge is a few tenths of a percent, a bootstrap that spends 0.1–0.2%
taker + slippage on a large fraction of capital is a **material** hurdle, and it recurs every time a
run is (re)activated. The validation gates include bootstrap costs in the denominator (good), but
the *sensitivity* of results to bootstrap sizing (i.e., activation price near lower vs upper bound →
more vs less pre-buy) is not called out as a first-class search/robustness dimension.

**Fix:** treat **activation-price position within the bounds** (hence bootstrap fraction) as an
explicit reported sensitivity, and confirm the strategy is not merely profiting from base
appreciation on the bootstrapped inventory (the completed-cycle activity gate, §Acceptance 10,
partly guards this — verify it is sufficient).

---

## ECO-4 — Fixed (non-compounding) principal is fine for MVP but guarantees sublinear growth · S3 · finding · `wontfix?`

Spec §3 fixes quote principal and explicitly **does not compound** (profit stays uncommitted quote).
This is a deliberate, defensible MVP simplification for reproducibility. Noting only so the operator
is aware that realized profit **idles as cash** and does not participate — combined with ECO-1 this
reinforces that the MVP is a validation vehicle, not a return vehicle. Deferred behind the declared
compounding seam. No action beyond acknowledgement.

---

## ECO-5 — "Untraded USDT cash" as the hard benchmark understates opportunity cost · S3 · finding · `ready-for-human`

Issue 07 sets **untraded USDT cash (zero return)** as the hard benchmark and reports buy-and-hold
diagnostically. Given the strategy ties up capital for a small edge, the honest comparison for the
operator is also **risk-free/stablecoin yield** (USDT on-exchange earn / T-bill equivalent), which
during the development window has often been **>4%/yr** — i.e., *above* the holdout pass bar. A grid
that returns 4% while a savings product returns 4–5% at lower risk is not obviously worth running.

**Fix:** add a risk-free-yield reference line to reports (diagnostic, not a gate) so the operator
evaluates the strategy against the real alternative, not just against zero.
