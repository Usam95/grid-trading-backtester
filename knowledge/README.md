# Trading Book Library — Knowledge Extraction (First Iteration)

## Mission
Recursively analyze every PDF and EPUB under the source library and produce a
separate, traceable knowledge package per book. The extracted knowledge will
later be used to improve or design:

1. a grid-strategy backtester,
2. a live grid-trading system,
3. a stock-strategy backtester,
4. a live stock algorithmic-trading system, and
5. shared research, data, execution, risk, monitoring, and operational
   capabilities.

The goal is traceable ideas and requirements that improve research quality,
backtest realism, execution safety, risk control, reproducibility, and the
chance of discovering robust strategies. **No book claim is treated as a promise
of profitability.**

## First-iteration boundary (IMPORTANT)
This iteration only performs *extraction*. It preserves the chain:

```
BOOK EVIDENCE
  -> AGENT INFERENCE / HYPOTHESIS / IDEA
  -> PROPOSED CANDIDATE REQUIREMENT
  -> (later) cross-book & system-specific review
```

No accepted requirements, implementation tickets, production code, or
system-specific backlogs are created here. Books are **not** combined into
conclusions during per-book extraction. All candidate requirements have
`status: proposed`.

## Artifacts
| Path | Purpose |
|------|---------|
| `inventory.yaml` | Every discovered source file, its hash, metadata, stable book ID, duplicate relationships. Written before analysis. |
| `run-status.yaml` | Per-book phase status; supports resuming. |
| `failed-files.yaml` | Unreadable / encrypted / extraction-failed files with recovery notes. |
| `SYSTEM_CONTEXT.template.md` | Empty template for the user to describe current systems (used in iteration 2). |
| `schemas/` | JSON Schemas for metadata, coverage, insight, hypothesis, candidate-requirement records. |
| `books/<book-id>/` | Per-book package (see below). |
| `indexes/` | **Generated** mechanical roll-ups. Do **not** edit by hand. |

### Per-book package (`books/<book-id>/`)
- `metadata.yaml` — bibliographic + scoring + status.
- `coverage.yaml` — ledger of every chapter/section and its read status. No chapter disappears.
- `insights.jsonl` — one JSON object per line; BOOK_CLAIM / AGENT_INFERENCE / TEST_HYPOTHESIS / IMPLEMENTATION_IDEA / WARNING_OR_FAILURE_MODE.
- `hypotheses.yaml` — testable strategy hypotheses (catalog for later experiment design).
- `candidate-requirements.yaml` — proposed "shall" statements linked to insight IDs.
- `synthesis.md` — 17-section human-readable synthesis linking to record IDs.
- `audit.md` — independent audit result and reliability grade (A–F).

## Provenance
Every BOOK_CLAIM carries a source locator (PDF file page / printed page, or
EPUB spine item / locator). Hypotheses and candidate requirements link back to
insight IDs via `derived_from`. Indexes retain book IDs, record IDs, locators
and audit grades — they never merge, deduplicate, or resolve conflicts.

## How to resume
The run is resumable. State lives in `run-status.yaml` and each book's
`metadata.yaml` `processing_status`. On restart:
1. Re-run inventory (`booktool.py inventory`) — hashes detect changed sources.
2. Skip books whose `processing_status: complete` and whose source hash,
   schema version, and prompt version are unchanged.
3. Continue incomplete books from their last saved phase.
4. Rebuild indexes (`booktool.py build-indexes`) after each audited book.

## Indexes are generated
`indexes/` is produced mechanically from per-book artifacts by
`booktool.py build-indexes`. Do not edit these files manually; edits will be
overwritten on the next rebuild.

## Second iteration
System-specific synthesis, cross-book conclusions, requirement acceptance, and
prioritization happen in a *later* step, seeded by `SYSTEM_CONTEXT.md` (filled
from the template) plus these indexes.

## Tooling
Mechanical helpers live outside this tree (session tooling). Inventory,
extraction, validation, and index building are all script-driven so LLM agents
never have to hold a whole book in context.
