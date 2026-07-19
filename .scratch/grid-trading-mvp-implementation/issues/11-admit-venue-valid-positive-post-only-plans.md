# 11 — Admit only venue-valid positive post-only plans

**What to build:** Replace static approximate venue assumptions with versioned current Binance Spot rule observations and admit only quantized grid plans that fit allocation, order capacity, fee coverage, minimum/maximum filters, and positive adjacent-cycle economics. Ordinary rungs retain explicit post-only intent.

**Blocked by:** 06 — Activate an obligation-backed static inventory grid; 07 — Account for one grid allocation in exact native assets; 09 — Enforce capital, loss, freshness and venue-anomaly postures; 10 — Operate Pause, Resume, Stop and terminal disposal.

**Status:** ready-for-agent

- [ ] Production and Testnet venue rules are discovered independently and carry source, observation time, schema, and environment identity.
- [ ] Unknown, unsupported, stale, suspended, or contradictory rules reject admission rather than using a generic live fallback.
- [ ] Price and quantity quantization preserves side-specific economics and every applicable min/max/notional/order-capacity constraint.
- [ ] Every adjacent cycle remains strictly positive after the applicable fees, rounding, execution allowance, and safety margin.
- [ ] The accepted `10–20 USDT` research principal range receives an early feasibility report for the proposed venue rules; infeasible points are rejected structurally.
- [ ] Normal rung intents are post-only and can never fall back to taker-capable ordinary orders.
- [ ] A would-take rejection follows the bounded identity-preserving retry policy and exhaustion selects the accepted restrictive posture.
- [ ] The rule/fee contract is re-verifiable without changing historical evidence identities silently.

