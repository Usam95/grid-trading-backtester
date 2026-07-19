# Verification, release, and migration code-gap audit

Status: working evidence for the Wayfinder ticket **Specify verification, release, and migration**  
Audit date: 2026-07-18  
Canonical foundation: `gridlab` and `gridlab-studio`

## Purpose

This audit records what the current codebase can already prove and what must still be specified and implemented before a build can become a qualified Paper, Testnet, or live release. Passing the current tests means the existing implementation has a useful tested foundation; it does not by itself prove the accepted accounting, replay, recovery, security, operational, or promotion contracts.

## Canonical test baseline

### `gridlab`

- The package contains tests for the core, engine, execution, ledger, metrics, research, strategies, Spot behavior, and property-based invariants.
- Existing property tests include cash identity, equity, and FIFO-style behaviors.
- The complete current suite passes when run outside the Windows filesystem sandbox. The sandboxed run failed only when the multiprocessing test attempted to create a Windows named pipe; the same test passed in the normal local environment.
- Result observed on 2026-07-18: all 82 collected tests passed.

### `gridlab-studio`

- The package contains 12 API smoke and contract tests.
- Result observed on 2026-07-18: `12 passed`.
- The run emitted one Starlette deprecation warning concerning the current `httpx`/`TestClient` integration. This is technical debt to remove before dependencies are frozen; it was not a test failure.

## Existing build and dependency state

- `gridlab/pyproject.toml` declares package version `1.0.0`, Python `>=3.11`, broad runtime dependency ranges, and broad development dependency ranges.
- `gridlab-studio/pyproject.toml` declares package version `1.0.0`, Python `>=3.10`, broad FastAPI/Uvicorn/Pydantic ranges, and an editable path dependency on `gridlab`.
- `gridlab/src/gridlab/__init__.py` declares `__version__ = "1.1.0"`; the Studio application reports `1.0.0`. A release therefore does not currently have one authoritative version identity.
- No canonical dependency lock, immutable build manifest, build-provenance record, or reproducible release-bundle process exists yet.
- Ruff configuration exists in the core manifest, but Ruff is not part of the declared development dependencies. No canonical enforced type-checking policy or coverage threshold was found.
- No canonical GitHub Actions or other CI workflow was found. This is not itself a defect because the accepted MVP uses local qualification, but the local runner and its sealed evidence do not yet exist.

## Existing persistence and migration state

- The canonical projects do not yet provide the accepted durable event journal, online-runtime database, schema-version registry, or migration runner.
- The canonical projects therefore have no forward-migration, compatibility-reader, backup/restore, rollback, or historical-replay migration tests.
- `grid-backtest-saas` contains legacy Alembic migrations `0001` through `0005`. They are useful implementation references, not the canonical schema and not migration evidence for the new architecture.
- Historical evidence must not be rewritten to adopt these legacy schemas. Any useful design is to be reimplemented behind the accepted canonical persistence contracts.

## Useful legacy verification material

- `grid-backtest-core` has additional engine, execution, research, metrics, and strategy scenarios that can be reviewed and selectively converted into canonical characterization or regression tests.
- `grid-backtest-saas` has backend/API tests and migration examples that can inform new contract and migration tests.
- `backtester_old` has a small set of basic tests. Its `reqs/requirements.txt` is a prose requirements catalogue rather than an installable dependency manifest and must not be treated as a lockfile.
- Legacy tests are requirements and scenario sources only. They become qualifying evidence only after being ported to canonical contracts, reviewed, made deterministic, and included in the accepted release gates.

## Material verification gaps

The following accepted behaviors do not yet have a complete canonical executable gate:

1. Exact multi-asset accounting, fee-asset handling, allocation isolation, and reconciliation invariants across the entire lifecycle.
2. Identical decision and state fingerprints across backtest event replay, Paper, Testnet decision observation, and later live decision harnesses.
3. Durable command identity, unknown-outcome recovery, partial and late fills, WebSocket gaps, authoritative reconciliation, restart in frozen posture, and duplicate-event resistance.
4. Decision-complete event-journal transactions, outbox dispatch, snapshots, rebuild, evidence export, retention, compaction, and recoverable-point restore.
5. Risk and lifecycle state-machine behavior under dependency failure, storage pressure, stale data, rejected orders, operator commands, stop-loss, and emergency stop.
6. Security acceptance: command authentication and authorization, nonce/idempotency/expiry, least privilege, secret redaction and canary scanning, dependency vulnerability gates, and credential incident recovery.
7. Binance adapter contract tests for filters, rounding, commissions, identifiers, order states, rate limits, rejected orders, ambiguous submissions, and REST/WebSocket repair.
8. Operator end-to-end workflows for sealed candidate handoff, consequence confirmation, reconciliation cases, incident evidence, downloads, and live activation separation.
9. Architecture fitness checks for forbidden imports, dependency cycles, process-global trading state, one execution/risk boundary, versioned durable contracts, and declared extension seams.
10. B1ms CPU, memory, storage, latency, capture, backup, compaction, restart, and degraded-mode budgets on the actual selected deployment profile.
11. Versioned configuration, API, event, journal, snapshot, manifest, and projection compatibility; deterministic forward migrations; downgrade/rollback safety; and replay-diff review.
12. One immutable release identity tying source, dependencies, toolchain, schemas, configuration contracts, tests, results, and the installed bundle together.

## Specification consequence

The verification design should add only gates that trace to an accepted invariant, failure scenario, promotion decision, architecture boundary, security control, evidence guarantee, or B1ms operating budget. It should use the already accepted local resumable acceptance runner and immutable SSH-delivered release bundle, not introduce mandatory hosted CI or a generic release platform.

The specification must distinguish three kinds of evidence:

- **change feedback** that is fast enough for normal local development;
- **release-candidate qualification** that proves the immutable candidate and its migrations;
- **operational promotion evidence** that can only be produced by the real candidate VM, qualifying production-data Paper run, Binance Testnet integration run, restore drills, or later capped live probation.

These evidence classes must share identities and reports, but they must not be conflated: local tests cannot replace a 30-day qualifying Paper run, while a 30-day run should not need to restart because a documentation-only change occurred.
