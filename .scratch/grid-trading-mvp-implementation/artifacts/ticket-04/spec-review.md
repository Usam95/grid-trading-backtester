# Ticket 04 Spec Review

## Acceptance mapping

| Criterion | Evidence |
| --- | --- |
| Source-exact values | `ExactDecimal` preserves string source text and rejects floats, exponents, inconsistent direct construction, and semantically wrong kinds. |
| Immutable identified configuration | Frozen, versioned strategy/policy objects expose SHA-256 content identities and remain distinct from `DerivedGridPlan`. |
| Complete policy vocabulary | Exact windows, thresholds, confirmations, hysteresis, residence, cooldown, expiry, transition frequency, widths, and upward-shift limit are represented without runtime coupling. |
| Past-only fail-closed decisions | Future, stale, incomplete, gapped, contradictory, ambiguous, unconfirmed, or temporally invalid evidence yields `UNCERTAIN`; TREND_DOWN forbids exposure-increasing buys and downward shifts. |
| Epoch identity | Covers configuration, observation, decision, predecessor, derivation causality/semantics, exact and quantized rungs, venue evidence, obligations, and allocations; presentation is excluded. |
| Canonical events | Stable event/source/correlation/causation/schema/domain-time identity and deterministic ordering inputs are implemented. |
| Pure domain | Architecture checks prohibit web, persistence, filesystem, venue/cloud SDK, network, and wall-clock imports from `gridlab.canonical`. |
| Legacy characterization | A bounded 120-bar real legacy adaptive run reports effective ATR `2.0`, 64 observed cancellation events, and five explicit legacy-to-canonical differences. |
| Boundary rejection | Domain, FastAPI, generated TypeScript, unit, contract, and browser tests cover malformed and ambiguous inputs. |

## Findings and disposition

Early review findings covering immutability, geometric derivation, venue-rule
validation, confirmation/hysteresis evidence, epoch material, legacy evidence,
and fail-closed roles were fixed and re-reviewed. The final spec review found
one quality-gate blocker: newly added validation branches had reduced
`gridlab.canonical` below its committed 99.5% line/100% branch floor. Targeted
negative tests were added rather than lowering the floor.

The final repeated spec review inspected the successful repository baseline and
measured coverage. It confirmed `gridlab.canonical` at 100% line and 100%
branch coverage against the unchanged 99.5%/100% floor and reported no
actionable findings.

## Scope-creep check

No Ticket 05 or later persistence, bootstrap, accounting, order execution,
cancellation/reconciliation, epoch activation/transition, Paper, Testnet, or
live behavior is present. Derivation causality is identity material only.
