Type: research
Status: resolved
Blocked by:

## Question

What capabilities, correctness guarantees, tests, defects, documentation, live-runtime concepts, and UI workflows exist across `gridlab`, `gridlab-studio`, `grid-backtest-core`, `grid-backtest-saas`, and `backtester_old`; which should be retained, migrated, redesigned, or rejected in the canonical foundation?

## Answer

The evidence-backed audit is recorded in [`analysis-reports/canonical-capability-audit.md`](../../../analysis-reports/canonical-capability-audit.md).

Use `gridlab` as the canonical engine and retain/deepen its single fill-derived ledger, I/O-free action-driven engine, conservative candle model, exchange realism, and research tools. Use `gridlab-studio` as the canonical application shell. Selectively reimplement the SaaS project's stronger UI, persisted research jobs, progress, comparison, and tournament workflows against canonical schemas.

Keep all three legacy projects as read-only reference sources until every useful capability has a traceable disposition. Do not import their domain implementations into the canonical runtime. Mine `backtester_old` for Binance adapter scenarios, deterministic order identity, reconciliation, safety, persistence, and recovery requirements, but redesign them around typed ports, an append-only journal, idempotency, explicit failure states, and comprehensive failure-injection tests. Reject dual semantic engines, broad exception swallowing, premature multi-user/distributed infrastructure, and all non-spot product surface from the MVP.

Independent test evidence: `gridlab` passed 81/82 tests with only sandbox-blocked multiprocessing unverified; `gridlab-studio` passed 12; `grid-backtest-core` passed 103 with deprecation warnings; the SaaS suite exceeded two minutes without completing; and `backtester_old` fails collection due to stale imports.
