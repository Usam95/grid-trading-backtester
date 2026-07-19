Type: grilling
Status: resolved
Blocked by: 02

## Question

Which inputs, decision types, clocks, execution abstractions, fill assumptions, and deterministic guarantees establish meaningful parity across candle backtest, event replay, paper trading, and live trading?

## Comments

- 2026-07-14: Codebase analysis and the recommended tiered data architecture are documented in [`analysis/data-architecture-and-code-reuse.md`](../../../analysis/data-architecture-and-code-reuse.md). The draft maps reusable canonical and legacy capabilities, identifies semantic contradictions, and proposes the event, archive, journal, execution-adapter, storage, and mode seams. Operator confirmation and the remaining parity decisions are still required before resolution.
- 2026-07-14: The operator selected option 1 and accepted the recommended data architecture. The document is now marked accepted, and its canonical data/runtime terms were added to the Online Runtime glossary. The five detailed parity decisions remain open, so this ticket stays claimed.
- 2026-07-14: The operator selected typed canonical events and typed decision batches. The accepted minimum vocabulary covers market evidence and gaps, order execution including unknown status, balances and reconciliation, venue contracts, operator/time inputs, and declarative order, lifecycle, reconciliation, and alert intents. Mode-specific strategy interfaces and unvalidated generic payloads were rejected. Four parity decisions remain open.
- 2026-07-14: The operator selected serialized observed ordering. Online inputs receive an atomic durable processing sequence at admission; causation and source order are preserved; late events never rewrite processed history; replay follows the recorded sequence; and historical events without one use a documented deterministic tie-break. Persistence or sequencing ambiguity blocks unsafe unjournaled processing. Three parity decisions remain open.
- 2026-07-14: The operator selected the conservative promotion fill policy. Primary evidence requires resting eligibility, next-candle and strict-cross candle fills, adverse ambiguity handling, a 5% non-reusable liquidity budget, strict trade-through without depth, and queue-ahead consumption when depth exists. More optimistic assumptions are sensitivity-only, and the current touch/favorable-gap/unlimited-volume defaults are explicitly noncompliant. Two parity decisions remain open.
- 2026-07-14: The operator selected full deterministic replay equality. Identical ordered inputs and immutable context must reproduce byte-identical canonical decisions, every state hash, ordered domain outputs, rebuilt trading/accounting/risk projections, and passing invariants. Operational metadata is excluded, replay is side-effect-free, and the first divergence fails the run even if later state or profit converges. One parity decision remains open.
- 2026-07-14: The operator selected the domain/operational clock boundary. Any deadline capable of changing orders, lifecycle, reconciliation, or risk becomes a durably admitted canonical timer event; housekeeping and measurement clocks cannot directly mutate trading state. This completes the parity decision set.

## Answer

Use the accepted tiered, provenance-first [data architecture and parity specification](../../../analysis/data-architecture-and-code-reuse.md): one typed canonical event vocabulary and deterministic decision core; durable serialized event admission with preserved causation and source order; conservative fidelity-specific fill adapters; exact replay equality across decisions, states, outputs, projections, and invariants; and canonical timer events for every time threshold capable of changing domain state. Paper and live normalize the same market inputs and share the core and journal, while execution authority remains adapter-specific. Candle research remains deliberately lower fidelity and cannot claim exchange queue realism.
