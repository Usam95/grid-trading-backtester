# 03 — Prove the manifested production-data tracer bullet

**What to build:** Deliver the smallest complete production-data path: preview and download a bounded official Binance Spot `1m` dataset, verify the source checksum and time representation, normalize it into typed Parquet, run a deterministic backtest, and show source identity and results in Studio.

**Blocked by:** 01 — Freeze the reproducible baseline and current normative contract; 02 — Expand a typed Studio shell around the existing backtest.

**Status:** ready-for-agent

- [ ] A download preview states symbol, interval, UTC range, source objects, estimated bytes, and expected checksums before network work begins.
- [ ] Import distinguishes the documented millisecond and microsecond timestamp eras and rejects an ambiguous or invalid unit.
- [ ] The dataset manifest records source locations, retrieval time, hashes, coverage, counts, gaps, duplicates, schema, and normalization identity.
- [ ] Missing, replaced, corrupt, duplicate, or discontinuous source evidence is reported and cannot silently become an admitted dataset.
- [ ] Normalized Parquet can be read offline to reproduce the same ordered candle sequence and backtest fingerprint.
- [ ] Studio displays the manifest identity and makes clear that production history, not Testnet history, supplied the result.

