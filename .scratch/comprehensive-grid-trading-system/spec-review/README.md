# Spec Review — Comprehensive Grid-Trading System

Independent critical review of the specification produced during the concept/grilling
session for the `gridlab` grid-trading workstation.

- **Reviewed artifacts:** `../spec.md`, `../map.md`, and all 14 decision records under `../issues/`.
- **Reviewer stance:** adversarial-but-constructive. The goal is to surface doubts, latent
  inconsistencies, feasibility risks, safety gaps, and concrete improvements — not to restate
  what the spec already does well.
- **Not covered here:** the deeper `analysis/*.md` records (linked from each issue) were *not*
  re-derived line-by-line; where a concern may already be resolved there, the item is marked
  **"verify in analysis doc."**

## Overall assessment

The specification is exceptionally thorough, internally cross-referenced, and safety-biased.
The dominant risks are **not** under-specification — they are (a) a handful of **economic and
statistical feasibility tensions** that may make the stated MVP gates jointly unpassable or
unprofitable, (b) a few **single-node safety gaps** (most importantly: the mandatory global
stop-loss cannot fire while the only VM is down or while price gaps through it), and (c) some
**venue/operational realities** (Binance API drift, Testnet resets, tiny-order quantization,
B1ms capacity) that deserve explicit contingency handling before real money.

## How to read this folder

| File | Focus |
| --- | --- |
| [`01-doubts-and-open-questions.md`](01-doubts-and-open-questions.md) | Questions that need an operator/maintainer decision |
| [`02-consistency-and-correctness-issues.md`](02-consistency-and-correctness-issues.md) | Internal contradictions, stale/superseded values, ambiguities |
| [`03-safety-and-risk-findings.md`](03-safety-and-risk-findings.md) | Safety-state, stop-loss, and failure-mode gaps |
| [`04-economics-and-strategy-findings.md`](04-economics-and-strategy-findings.md) | Grid economics, capital sizing, profitability vs cost |
| [`05-validation-and-statistics-findings.md`](05-validation-and-statistics-findings.md) | Walk-forward, DSR, regimes, history availability, feasibility of gates |
| [`06-runtime-recovery-availability-findings.md`](06-runtime-recovery-availability-findings.md) | B1ms capacity, RTO/RPO, reconciliation, clocks |
| [`07-deployment-security-findings.md`](07-deployment-security-findings.md) | Azure, SSH, secrets, deferred-maintenance exception |
| [`08-improvements-enhancements-optimizations.md`](08-improvements-enhancements-optimizations.md) | Non-blocking betterments and cost/latency optimizations |

## Legend

**Kind:** `doubt` (needs a decision) · `issue` (defect/contradiction) · `finding` (risk/observation)
· `improvement` · `enhancement` · `optimization`.

**Severity:**

- **S1 — Critical:** threatens safety, real-money correctness, or the economic/feasibility premise of the MVP.
- **S2 — Significant:** likely to cause rework, a failed gate, or an operational incident if unaddressed.
- **S3 — Minor:** clarity, provenance, or polish.

**Triage label** (house vocabulary, see `docs/agents/triage-labels.md`): `needs-triage`,
`needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`.

## Top items (start here)

| ID | Sev | Kind | Title |
| --- | --- | --- | --- |
| SAF-1 | S1 | finding | Mandatory global stop-loss is unenforceable while the single node is down |
| ECO-1 | S1 | finding | At 250 USDT, Azure cost exceeds every passing return threshold (net-loss by construction) |
| VAL-1 | S1 | doubt | Deflated-Sharpe ≥0.95 over ~10^5 trials vs modest ≥5% return may be jointly unpassable |
| VAL-2 | S1 | finding | 5-year quality-approved history conflicts with grid-suitable (ranging, mid-cap) symbols |
| SAF-2 | S1 | finding | Stop-loss gap-through risk on a spot long-inventory book is only "reported," not bounded |
| RUN-1 | S2 | finding | B1ms (1 vCPU burstable) very likely fails the 24h capacity gate → plan for B2 |
| ECO-2 | S2 | finding | 10–20 USDT orders collide with Binance minNotional/stepSize; net-positive-cycle gate is fragile |
| SAF-3 | S2 | finding | No handling for venue-side symbol halt/delist/maintenance during a 30–90 day run |
| CON-1 | S2 | issue | Fee model ambiguity: received-asset fees vs a separate native fee reserve |
| CON-2 | S3 | issue | Superseded numeric decisions (e.g., 11-rung, Entra OIDC) remain inline and can mislead |

Each ID is defined in the corresponding topic file.
