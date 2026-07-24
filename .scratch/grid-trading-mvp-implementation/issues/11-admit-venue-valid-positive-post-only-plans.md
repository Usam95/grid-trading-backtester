# 11 — Admit only venue-valid positive grid-epoch plans

**What to build:** Replace approximate venue assumptions with versioned current Binance Spot rule observations and admit an initial or replacement grid plan epoch only when its quantized plan fits allocation, transition commitments, order capacity, fee coverage, minimum/maximum filters, and positive adjacent-cycle economics. Ordinary rungs retain explicit post-only intent.

**Blocked by:** 06 — Derive and activate an obligation-backed adaptive initial epoch; 07 — Account for one grid allocation across exact epochs and assets; 09 — Enforce adaptive, capital, loss, freshness and venue-anomaly postures; 10 — Operate controls and terminal disposal during adaptation.

**Status:** ready-for-agent

- [ ] Production and Testnet venue rules are discovered independently and carry source, observation time, schema, and environment identity.
- [ ] Unknown, unsupported, stale, suspended, or contradictory rules reject admission rather than using a generic live fallback.
- [ ] Price and quantity quantization preserves side-specific economics and every applicable min/max/notional/order-capacity constraint.
- [ ] Every adjacent cycle remains strictly positive after the applicable fees, rounding, execution allowance, and safety margin.
- [ ] Proposed epoch admission includes all still-effective old-epoch commitments, additional bootstrap, maximum planned inventory, fee coverage, and the immutable capital envelope.
- [ ] The accepted `10–20 USDT` research principal range receives an early feasibility report for the proposed venue rules; infeasible points are rejected structurally.
- [ ] Normal rung intents are post-only and can never fall back to taker-capable ordinary orders.
- [ ] A would-take rejection follows the bounded identity-preserving retry policy and exhaustion selects the accepted restrictive posture.
- [ ] The rule/fee contract is re-verifiable without changing historical evidence identities silently.
