# Reproducible baseline report

Status: frozen Ticket 01 baseline  
Measured: 2026-07-19  
Canonical scope: `gridlab`, `gridlab-studio`, and the top-level verification contract

## Reproduce it

From the top-level `backtester` repository, run exactly:

```shell
python tools/verify_baseline.py
```

The entry point bootstraps only the pinned `uv` tool, verifies the committed
lock, performs an exact non-editable workspace sync, checks the shared product
version, architecture and static-quality ratchets, and runs both canonical
suites with statement and branch coverage. It writes a
machine-readable `.artifacts/baseline-report.json` containing the exact commit,
clean-tree assertion, lock digest, installed dependency inventory, interpreter
and tool identities, commands, exit codes, and duration for that invocation.

## Frozen source and repository boundary

- The top-level Git repository is the only canonical implementation boundary.
- `gridlab` owns the engine and research foundation.
- `gridlab-studio` owns the product, FastAPI, and Studio boundary.
- `backtester_old`, `grid-backtest-core`, and `grid-backtest-saas` are useful
  **read-only** characterization, requirement, and UX sources. Their nested Git
  histories remain unchanged; they are ignored by and are not members of the
  canonical workspace.
- The root `VERSION`, `.python-version`, `pyproject.toml`, and `uv.lock` identify
  the product, interpreter, dependency graph, and exact resolution.

The generated report is the exact source identity for a particular run. This
document records the observed pre-change baseline rather than pretending that a
report committed inside a source tree can contain its own future commit hash.

## Observed pre-change baseline

| Identity | Observed value |
| --- | --- |
| Root repository | no operational Git metadata before Ticket 01 |
| Product metadata | package/Studio `1.0.0`; engine runtime `1.1.0` (conflict) |
| Python | CPython `3.12.10` on Windows |
| Dependency model | two broad manifests; no shared lock |
| Canonical tests | 94 collected: 82 engine + 12 Studio |
| Normal local result (2026-07-18 audit) | 94 passed |
| Restricted Windows sandbox result (2026-07-19) | 93 passed, 1 permission failure creating a multiprocessing named pipe |
| Pre-existing warning | one Starlette deprecation warning from the `httpx`/`TestClient` integration |

The named-pipe failure is environmental and predates this ticket; it is not a
test relaxation. The same parallel-search test must pass in the ordinary local
environment, and the verification entry point always includes it. The warning
remains visible until a later, explicitly scoped dependency/API migration.

## Ticket 01 locked verification identity

| Identity | Frozen value |
| --- | --- |
| Product | `1.0.0` |
| Python | CPython `3.12.10` |
| uv | `0.11.16` |
| `uv.lock` SHA-256 | `86c696f6bcc35612a83ecf1cad366e1676203d54a40c8ffe37fe8e458a4c2b9f` |
| Resolution | 48 locked packages; 44 installed distributions |
| Core numerical stack | NumPy `2.4.6`; pandas `3.0.3` |
| Product/API stack | FastAPI `0.139.2`; httpx `0.28.1` |
| Test tools | pytest `9.1.1`; pytest-cov `7.1.0`; Hypothesis `6.157.0` |
| Static tools | Ruff `0.15.22`; mypy `2.3.0` |
| Static legacy baseline | 43 formatting files; 15 lint findings; 21 typing findings |
| Coverage baseline | **84.5077% lines**; **65.13% branches** (3,311 lines / 551 branches covered) |
| Locked result, 2026-07-19 | **102 passed**, one pre-existing Starlette deprecation warning |
| Architecture result | 0 cycles; 0 forbidden imports; 0 process-global mutable trading-state findings |

The current frontend is static HTML/CSS/JavaScript and has no package manager or
dependency graph. A committed `package-lock.json` and pinned Node/npm line become
mandatory when the accepted React/TypeScript frontend is introduced; Ticket 01
does not add that dependent modernization work prematurely.

### Recorded legacy quality debt

`quality-baseline.json` is the machine-readable ratchet. The canonical
maintainer owns its 43 formatting, 15 lint, and 21 typing findings and the gap
between the measured 65.13% overall branch coverage and the 80% production
target. The risk is explicitly bounded: this baseline has no online authority
and cannot qualify a release. A changed module may not add findings or reduce
coverage; qualifying online modules must remove applicable debt, and critical
packages must reach 90% branch coverage before Level B. Those milestones belong
to the later owning implementation tickets rather than being waived here.

## Frozen architecture baseline

`architecture-baseline.json` and `tools/check_architecture.py` establish three
ratchets over canonical production Python: dependency cycles, forbidden inward
imports, and process-global mutable trading state. Ticket 01 records zero known
findings for all three checks. A later change may reduce debt but cannot add a
finding without failing verification.

These checks establish the requested starting boundary; they do not claim that
later journal, runtime, accounting, migration, or online-authority tickets have
already been implemented. No live or online command authority is granted here.
