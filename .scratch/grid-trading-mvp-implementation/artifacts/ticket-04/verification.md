# Ticket 04 Verification

## Focused RED/GREEN

| Command | Result | Outcome |
| --- | --- | --- |
| `.venv\Scripts\python.exe -m pytest gridlab\tests\test_canonical_adaptive.py -q` | exit 2 | RED: missing `gridlab.canonical` package. |
| Same focused domain command after implementation | exit 0 | 7 initial seam tests passed. |
| `.venv\Scripts\python.exe -m pytest gridlab\tests\test_canonical_adaptive.py gridlab-studio\tests\test_studio_contract.py -q` | exit 0 | Domain and typed API contract passed. |
| Expanded focused domain/API suite | exit 0 | 61 tests passed after review-driven invariant and coverage cases. |
| Focused canonical branch coverage | exit 0 | Canonical validation and safety branches reached 100% branch coverage. |

## Static and contract checks

| Command | Result | Outcome |
| --- | --- | --- |
| Focused `ruff check` | exit 0 | No new lint findings. |
| Focused `mypy` | exit 0 | No type errors in canonical/API schemas. |
| `python tools/check_architecture.py` | exit 0 | No cycles, forbidden imports, or mutable global trading state. |
| OpenAPI export and `pnpm run contracts:generate` | exit 0 | FastAPI and generated TypeScript contract aligned. |
| `pnpm run typecheck` | exit 0 | Typed Studio accepted. |
| `pnpm run test` | exit 0 | 5 frontend tests passed. |
| `pnpm run build` | exit 0 | Production bundle built. |

## Browser

| Command | Result | Outcome |
| --- | --- | --- |
| `pnpm exec playwright test migrated-backtest.spec.ts` | exit 0 | 2 Chromium workflows passed. |
| Complete baseline browser phase | exit 0 | 2 passed; 1 explicitly opt-in production-network workflow skipped. |

## Complete baseline

| Command | Result | Outcome |
| --- | --- | --- |
| `python tools/verify_baseline.py` (first attempt) | exit 1 | Reached static gate; new files required formatting. |
| `python tools/verify_baseline.py` (second attempt) | exit 1 | 152 passed, 2 skipped; exposed new canonical coverage classification and one API branch below its unchanged floor. |
| Complete backend coverage rerun | exit 0 | 184 passed, 2 skipped. Canonical measured 99.5% line and 100% branch coverage before the final API invalid-symbol case. |
| `python tools/verify_baseline.py` (post-review first attempt) | exit 1 | Stopped at byte-for-byte generated TypeScript contract verification because line endings were stale. |
| Pinned `pnpm run contracts:generate` | exit 0 | Regenerated the exact committed TypeScript contract. |
| `python tools/verify_baseline.py` (final) | exit 0 | Lock/version checks, generated contracts, frontend typecheck/unit/build, browser, architecture/static quality, 199 backend tests with 2 skips, and coverage ratchets all passed. |

## Final baseline distinction

- Focused checks covered the Ticket 04 canonical domain, API contract, typed
  Studio, and review-driven negative cases.
- The final complete baseline used the repository entry point
  `tools/verify_baseline.py`; it included the complete backend and frontend
  suites, generated-contract comparison, production build, real browser phase,
  architecture checks, static quality ratchets, and coverage ratchets.
