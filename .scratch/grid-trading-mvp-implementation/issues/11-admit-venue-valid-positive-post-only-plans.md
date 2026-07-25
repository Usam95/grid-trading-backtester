# 11 — Admit only venue-valid positive grid-epoch plans

**What to build:** Replace approximate venue assumptions with versioned current Binance Spot rule observations and admit an initial or replacement grid plan epoch only when its quantized plan fits allocation, transition commitments, order capacity, fee coverage, minimum/maximum filters, and positive adjacent-cycle economics. Ordinary rungs retain explicit post-only intent.

**Blocked by:** 06 — Derive and activate an obligation-backed adaptive initial epoch; 07 — Account for one grid allocation across exact epochs and assets; 09 — Enforce adaptive, capital, loss, freshness and venue-anomaly postures; 10 — Operate controls and terminal disposal during adaptation.

**Status:** resolved

- [x] Production and Testnet venue rules are discovered independently and carry source, observation time, schema, and environment identity.
- [x] Unknown, unsupported, stale, suspended, or contradictory rules reject admission rather than using a generic live fallback.
- [x] Price and quantity quantization preserves side-specific economics and every applicable min/max/notional/order-capacity constraint.
- [x] Every adjacent cycle remains strictly positive after the applicable fees, rounding, execution allowance, and safety margin.
- [x] Proposed epoch admission includes all still-effective old-epoch commitments, additional bootstrap, maximum planned inventory, fee coverage, and the immutable capital envelope.
- [x] The accepted `10–20 USDT` research principal range receives an early feasibility report for the proposed venue rules; infeasible points are rejected structurally.
- [x] Normal rung intents are post-only and can never fall back to taker-capable ordinary orders.
- [x] A would-take rejection follows the bounded identity-preserving retry policy and exhaustion selects the accepted restrictive posture.
- [x] The rule/fee contract is re-verifiable without changing historical evidence identities silently.

## Answer

Implemented fail-closed venue-rule admission, exact min/max/order-capacity quantization, positive adjacent-cycle checks, principal-feasibility reporting, explicit post-only retry policy, and rule/fee contract identity across the canonical initial-epoch seam, Studio API contract, generated typed frontend contract, and regression coverage. Focused Ticket 06/07/09/10 regressions, architecture/static checks, frontend type/unit/build/browser verification, and the full 336-test baseline all passed; the delivery report is at `../artifacts/ticket-11/report.md`. Ticket 12 and later behavior was not started.
