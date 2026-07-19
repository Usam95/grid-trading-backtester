Type: grilling
Status: resolved
Blocked by: 01

## Question

What canonical domain model and exact static-grid semantics must all modes share, including grid lifecycle, inventory ownership, bootstrap, order intent, fill consequences, exits, pause/stop behavior, and configuration versioning?

## Comments

- 2026-07-14: Operator selected the fail-closed post-only rejection policy: reconcile and refresh first; retry only as a bounded, venue-valid, non-marketable order no worse than the configured rung economics; never fall back to taker; pause and alert if retry bounds are exhausted. Recorded in `analysis/domain-grid-semantics.md`.

## Answer

The operator confirmed the complete first-MVP domain and static-grid semantics on 2026-07-14. The authoritative resolution, including selected behavior and declined alternatives, is [Canonical domain and grid semantics — decision record](../../../analysis/domain-grid-semantics.md). Canonical vocabulary is maintained in the [Trading engine glossary](../../../docs/domain/trading-engine/CONTEXT.md).

The MVP is an open-ended, static Binance Spot inventory grid with immutable versioned configuration. It performs a real neutral-grid bootstrap sized from initial sell obligations; uses fixed quote sizing without automatic compounding; supports arithmetic and geometric spacing with geometric as default; enforces strict activation and positive-net-cycle gates; maintains exact rung geometry, one cumulative order per rung, partial-fill accounting, actual fee assets, bounded outer-rung cycling, and no exposure outside the range.

Ordinary rung orders are post-only. A post-only rejection is reconciled and may be retried only as a bounded maker-safe order no worse than the configured rung economics; it never falls back to taker execution. Range exhaustion, exposure-reducing pause, reconciled resume, operator stop, emergency stop, paired sells, and configurable global stop-loss have distinct canonical lifecycle consequences. Existing-account use requires explicit allocation isolation and pauses on foreign activity.

Quantitative retry limits, formal accounting tolerances, Binance-specific state mappings, and risk thresholds are deliberately routed to their downstream specification tickets.
