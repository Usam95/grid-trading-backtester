# Ticket 14 Report

## Implementation summary

Built the synchronized ten-symbol EUR production archive seam for local research. The implementation now plans the fixed EUR panel against official Binance Spot history, previews bounded acquisition cost/storage, verifies source checksums and timestamp units, admits only continuity-clean evidence into immutable monthly Parquet partitions, persists durable local index state, and creates fail-closed snapshot manifests for offline deterministic replay.

Studio and typed FastAPI now expose the archive explicitly as EUR production history, separate it from synthetic scenarios, and let the operator choose only verified local ranges when running a production-history backtest.

## Acceptance-criterion mapping

- The archive freezes the exact ten EUR Spot symbols in the required order and preserves each symbol's own first available date.
- Preview exposes source-object count, estimated download bytes, and estimated local storage before synchronization.
- Completed months use monthly `1m` archives and the incomplete current month uses daily `1m` archives only.
- Admission verifies `.CHECKSUM` sidecars, detects millisecond versus microsecond timestamps, and blocks gaps, duplicates, disorder, and invalid partition boundaries.
- Verified evidence normalizes into immutable monthly Parquet partitions with stable per-symbol dataset identities and atomic publish behavior.
- The local index records per-partition identity, checksum evidence, row count, byte size, verification state, verified local ranges, and pending months.
- Reruns reuse only partitions whose manifest and Parquet checksums still match; tampered or missing evidence is redownloaded and replaced.
- Snapshot manifests freeze exact partition identities/checksums, prune to the requested verified local `[start, end)` range, and fail closed on missing or drifted evidence during replay.
- Studio and typed APIs surface EUR quote context, exact provenance identities, candle counts, requested/verified ranges, and partition identities while keeping Production history distinct from Synthetic runs.

## Tests and verification

- `python -m pytest gridlab/tests/test_binance_panel.py -q`
- `python -m pytest gridlab-studio/tests/test_production_data_contract.py -q`
- Frontend `typecheck`
- Frontend `vitest` (`src/App.test.tsx`)
- Frontend production `build`
- Playwright browser checks: migrated workflow, production-history provenance, candle limitations
- `python tools/verify_frontend.py`
- `python tools/check_quality_baseline.py --static`
- `python tools/check_architecture.py`

The bounded live-data browser replay spec remains intentionally skipped unless `GRIDLAB_REAL_BINANCE_BROWSER=1` is set.

## Review

Direct final review found no remaining actionable standards or spec findings after:

- hardening partition reuse and snapshot replay against local tampering;
- binding Studio date inputs to a selected verified local range instead of broad remote coverage;
- backfilling `manifest_identity` for older local archive entries so typed archive reads remain compatible.

Ticket 15 and later work was not started.
