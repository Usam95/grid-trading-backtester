Type: research
Status: resolved
Blocked by: 02

## Question

What current Binance Spot REST/WebSocket behavior, filters, rate limits, order states, identifiers, test-environment limitations, authentication constraints, and failure semantics must the exchange adapter specification cover?

## Comments

- 2026-07-14: Research claimed after the operator accepted the validation-first MVP boundary. Investigation will use current primary Binance documentation and cross-check the canonical and legacy adapters so the result defines requirements rather than copying existing assumptions.
- 2026-07-14: Official Binance documentation establishes `LIMIT_MAKER` as the post-only mechanism; distinct order-status and execution-type vocabularies; trade-level commission evidence; live, dynamic filter and rate-limit discovery; unknown execution outcomes after timeouts and 5xx responses; finite-lived WebSockets with explicit recovery needs; sequence-based depth reconstruction; and a periodically reset virtual-asset Testnet. The code audit confirms that canonical code has no online adapter and legacy code uses ordinary limits, incomplete float filters, whole-account seeding, open-order-only reconciliation, and reconnect without gap recovery.

## Answer

The current venue contract and its first-MVP implications are recorded in the primary-source [Binance Spot contract](../../../analysis/binance-spot-contract.md). The companion [Binance adapter code-gap audit](../../../analysis/binance-adapter-code-gap-audit.md) identifies which canonical and legacy assumptions may be reused, redesigned, or rejected.

The adapter must use generation-specific durable client identities, exact live venue-rule observations, post-only `LIMIT_MAKER` normal orders, trade-level native commission evidence, explicit unknown-submission recovery, rate-limit-aware backoff, planned WebSocket rotation, authoritative gap reconciliation, and separate paper versus Testnet venue-integration modes. Testnet cannot supply production fill-realism or long-duration persistence evidence. These findings now bound the risk, runtime, security, observability, and verification specifications.
