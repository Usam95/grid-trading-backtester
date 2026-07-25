# Ticket 04 Worklog

## Start

- Starting commit: `66b46de17b7ba2a54f1c75c6e4a46d18d11bb89f`
- Branch: `codex/ticket-04-adaptive-policy-event-seam`
- Git author and committer email: `usam.sersultanov@gmail.com`
- The external task-title control is unavailable in this environment. The requested title, `Ticket 04 — Expand the canonical exact adaptive-policy and event seam`, is recorded here instead.
- Prerequisites: Tickets 01–03 report resolved and their implementation commits are ancestors of the starting commit.

## Inspected contracts

- Root agent instructions and linked issue-tracker, triage, and domain guidance.
- Complete Ticket 04 and comprehensive adaptive-grid specification.
- Trading-engine, online-runtime, and operator-Studio context documents.
- Existing float configuration, adaptive strategy, immediate `cancel_all` rebuild,
  FastAPI schemas/service, generated OpenAPI types, Studio Research port, unit
  tests, Playwright workflow, architecture ratchet, and baseline verifier.

## Scope

- Implement only the canonical exact adaptive-policy and event seam, one legacy translation, and typed read-only presentation.
- Exclude persistence, full adaptive initialization, accounting, order execution, epoch activation/transitions, Paper, Testnet, and later-ticket behavior.

## Milestones

- RED: `gridlab/tests/test_canonical_adaptive.py` initially failed collection
  because `gridlab.canonical` did not exist.
- GREEN: exact values, immutable configuration, canonical events, past-only
  classification, epoch identities, legacy translation, API contract, and Studio
  presentation passed focused tests.
- Refactor: moved the legacy engine call to `gridlab.api.canonical_translation`
  so `gridlab.canonical` remains pure; added `gridlab.canonical` to the critical
  architecture scope; removed unintended formatter churn in the legacy service.

## Material decisions

- Source-exact values accept decimal strings only, retain their original source
  representation, and reject floats and exponent notation.
- Content identities use canonical JSON and SHA-256 with explicit namespaces.
- `received_time` is operational evidence and is excluded from canonical event
  identity; source event time, source identity/key/sequence, schema, causality,
  and payload are identity material.
- Epoch identity includes an explicit derivation-causation identity without
  implementing transition or activation behavior.
- The policy contains the Ticket 04 gate parameters, but safe epoch transition,
  activation, cancellation, and reconciliation behavior remain unimplemented.
- The characterized legacy scenario is bounded to 120 deterministic synthetic
  bars. Its comparison explicitly reports ATR-default, immediate rebuild, and
  fail-closed semantic differences.
- The quality ratchet now classifies `gridlab.canonical` separately at 99.5%
  line and 100% branch coverage; no existing package floor was lowered.

## Blockers or deviations

- The first full baseline run failed on formatting in new modules; repository
  formatting was applied only to Ticket 04 code.
- The second full baseline run exposed the expected new coverage-package
  classification and an API branch regression. Tests were expanded rather than
  lowering existing floors.
- Independent reviews found constructor-level immutability and consistency
  gaps, missing decision/role invariants, unsupported schema acceptance,
  missing derivation causality, and an unsafe hysteresis bound. Each finding
  was fixed with focused regression coverage.
- A repeated spec review found the canonical coverage floor was temporarily
  aspirational after the final invariants. Negative-path tests were expanded
  until the canonical package again reached the unchanged 99.5% line and 100%
  branch floor.
- No dependency, version, or lock-file change was required.

## Scope exclusions

- No persistence or journal storage.
- No full adaptive initialization or bootstrap acquisition.
- No accounting, order execution, cancellation, reconciliation, safe epoch
  transition, activation, Paper, Testnet, live, or later-ticket behavior.
