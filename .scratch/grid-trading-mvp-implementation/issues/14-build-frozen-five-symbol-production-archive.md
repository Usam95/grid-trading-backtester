# 14 — Build the synchronized ten-symbol EUR production archive

**What to build:** Synchronize the fixed ten-symbol Binance Spot EUR production archive on local disk, using official monthly `1m` archives for completed months and official daily `1m` archives only for the incomplete current month, while preserving each symbol's full available history, durable partition/index evidence, resumable incremental synchronization, immutable snapshot manifests, and fail-closed local replay.

**Blocked by:** 03 — Prove the manifested production-data tracer bullet; 11 — Admit only venue-valid positive grid-epoch plans.

**Status:** resolved

- [ ] The frozen production archive uses exactly these EUR Spot symbols in this exact order: BTCEUR, ETHEUR, SOLEUR, XRPEUR, ADAEUR, PEPEEUR, BNBEUR, DOGEEUR, XLMEUR, LTCEUR.
- [ ] Each symbol acquires its complete available official Binance Spot `1m` history, preserves its own first available date, and never forces a shared start date.
- [ ] A coverage/storage preview runs before bulk acquisition and exposes source object count, estimated download bytes, and estimated local storage.
- [ ] Completed months use official monthly archives and only the incomplete current month uses official daily archives.
- [ ] Admission verifies official `.CHECKSUM` sidecars, detects millisecond versus microsecond timestamp units correctly, and blocks gaps, duplicates, disorder, and invalid partition boundaries instead of silently accepting them.
- [ ] Verified data normalizes into immutable monthly Parquet partitions with atomic publish semantics and one stable local dataset identity per symbol.
- [ ] A durable local coverage/partition index records per-symbol per-month identity, checksum evidence, row count, byte size, and verification status.
- [ ] Synchronization is incremental, idempotent, and resumable: reruns reuse verified partitions, resume safely after interruption, and download only missing or invalid partitions.
- [ ] Immutable snapshot manifests freeze exact partition identities/checksums for reproducible backtests, support arbitrary verified local `[start, end)` windows, prune to required partitions/rows, and fail closed on missing local ranges.
- [ ] Studio and typed APIs keep Production history separate from Synthetic scenarios, label this archive in EUR, and surface exact source, symbol, UTC range, candle count, coverage, dataset identity, manifest identity, and partition identities.

## Answer

Implemented the synchronized ten-symbol EUR production archive as a local official-Binance evidence seam:

- fixed the exact EUR symbol panel and per-symbol full-history planning, with monthly `1m` archives for completed months and daily `1m` archives only for the incomplete current month;
- added bounded preview, official `.CHECKSUM` verification, timestamp-unit detection, gap/duplicate/disorder/boundary rejection, immutable monthly Parquet publish, durable archive index state, incremental/resumable synchronization, and immutable snapshot manifests for fail-closed local replay;
- exposed the archive and snapshot workflow through typed FastAPI/Studio contracts, including explicit EUR production-history provenance, verified local range selection, dataset identity, manifest identity, and partition identities while keeping Production history separate from Synthetic scenarios.

Verification completed locally:

- `python -m pytest gridlab/tests/test_binance_panel.py -q`
- `python -m pytest gridlab-studio/tests/test_production_data_contract.py -q`
- frontend `typecheck`, `vitest`, `build`, and Playwright browser workflow checks
- `tools/verify_frontend.py`
- `tools/check_quality_baseline.py --static`
- `tools/check_architecture.py`

The live-data browser replay spec remains explicitly bounded and skipped unless `GRIDLAB_REAL_BINANCE_BROWSER=1` is enabled.
