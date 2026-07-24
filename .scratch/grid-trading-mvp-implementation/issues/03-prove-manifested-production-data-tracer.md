# 03 — Prove the manifested production-data tracer bullet

**What to build:** Deliver the smallest complete EUR-first production-data path. Discover the current Binance Spot symbols that are simultaneously available on public Spot Testnet and global production, let the operator select an eligible `EUR`-quoted symbol and a bounded official production-history range, preview and download the official Binance Spot `1m` archives, verify source checksums and time representation, normalize them into typed Parquet, run a deterministic backtest, and show catalog, source, manifest, liquidity, and result identity in Studio.

**Blocked by:** 01 — Freeze the reproducible baseline and current normative contract; 02 — Expand a typed Studio shell around the existing backtest.

**Status:** resolved

**Baseline implementation:** The original single-symbol, single-day `BTCUSDT` tracer was delivered at commit `a3f3cf38328f2903d438b7221537be46e63771bb`. The operator-approved EUR scope extension below is implemented by this resolution.

## Scope revision — 2026-07-23

- Discover Testnet and production catalogs independently from their public Spot `exchangeInfo` endpoints.
- Admit only the live intersection whose production and Testnet entries are `TRADING`, allow Spot trading, support `LIMIT_MAKER`, and have `EUR` as the quote asset.
- Treat discovery as dated evidence, not a permanent allowlist. Store the endpoint identities, retrieval times, filters, canonical sorted symbol set, and catalog fingerprint so a past selection remains reproducible after Binance changes its listings.
- Use the following 29-symbol discovery result as a deterministic development and browser-test fixture, not as a hard-coded runtime ceiling: `ADAEUR`, `APTEUR`, `ATOMEUR`, `AVAXEUR`, `BCHEUR`, `BNBEUR`, `BTCEUR`, `DOGEEUR`, `DOTEUR`, `EGLDEUR`, `ETHEUR`, `ICPEUR`, `LINKEUR`, `LTCEUR`, `NEAREUR`, `PEPEEUR`, `POLEUR`, `RENDEREUR`, `SEUR`, `SHIBEUR`, `SOLEUR`, `SUIEUR`, `TRXEUR`, `VETEUR`, `WINEUR`, `WLDEUR`, `WLFIEUR`, `XLMEUR`, and `XRPEUR`.
- Discover official production-archive coverage for each eligible symbol. Studio must expose the actual first and last complete UTC archive dates and must not imply that every symbol has identical history.
- Keep `1m` as the canonical acquisition and deterministic-backtest interval required by the comprehensive specification. Other official archive intervals may be reported as informational availability, but downloading or backtesting them is outside this ticket.
- Rank and describe symbols with reproducible production-market evidence useful for selection, including 30-day median EUR quote volume, trade activity, current spread when available, history length, and detected archive gaps. Liquidity metadata is selection context, not profitability evidence.
- Let the operator search or select an eligible symbol, choose a complete UTC date range within its discovered production coverage, preview the bounded work, then download, verify, normalize, and backtest that selection.
- Apply explicit configurable caps to days, source objects, and expected bytes. A request that exceeds a cap must fail before archive bytes are downloaded and explain how to reduce the request.
- Label the result and P&L in the selected quote asset (`EUR`). Testnet proves protocol and symbol compatibility only; official production archives supply every historical candle and every profitability result.
- Make clear that the public catalog intersection is not proof that an authenticated German account may currently trade a symbol. Account-specific permissions and live execution remain separate concerns.
- Do not add automatic `USDT`, `USDC`, `EURI`, or other stablecoin fallback. Do not begin Ticket 04 or revise later canonical robustness/live-capital contracts in this ticket.

## Acceptance criteria

- [x] The delivered baseline previews and downloads one bounded official Binance Spot `1m` dataset, verifies it, normalizes it, manifests it, replays it offline, and displays its production provenance in Studio.
- [x] Catalog discovery returns the canonical current EUR-quoted Testnet/production intersection and a stable fingerprint from bounded official responses.
- [x] Catalog validation rejects stale, malformed, duplicate, non-Spot, non-`TRADING`, or non-`LIMIT_MAKER` entries instead of silently admitting them.
- [x] The Studio symbol picker is populated by the discovered catalog rather than a hard-coded `BTCUSDT` value, while deterministic fixtures reproduce the 29-symbol snapshot above.
- [x] Each catalog entry exposes source identities, retrieval time, base and quote assets, exchange filters, production-history coverage, available archive intervals as informational metadata, and reproducible liquidity-selection evidence.
- [x] A selected symbol exposes only its verified production-history range; unavailable dates and known archive gaps cannot be selected as if they were continuous evidence.
- [x] A download preview states symbol, interval, UTC range, source objects, estimated bytes, expected checksums, and applicable caps before network work begins.
- [x] Multi-day requests remain bounded, resolve to a deterministic ordered source plan, and fail before download when their day, object, or byte cap is exceeded.
- [x] Import distinguishes the documented millisecond and microsecond timestamp eras and rejects an ambiguous or invalid unit.
- [x] The dataset manifest records catalog identity, selected symbol metadata, source locations, retrieval time, hashes, coverage, counts, gaps, duplicates, schema, and normalization identity.
- [x] Missing, replaced, corrupt, duplicate, overlapping, or discontinuous source evidence is reported and cannot silently become an admitted dataset.
- [x] Normalized Parquet can be read offline to reproduce the same ordered candle sequence and deterministic backtest fingerprint for any admitted selection.
- [x] Studio displays the catalog and manifest identities, EUR-denominated result context, and an explicit statement that production history—not Testnet history—supplied the result.
- [x] Studio distinguishes public Testnet/production compatibility from authenticated German-account trading eligibility.
- [x] The typed Studio/FastAPI boundary and legacy frontend remain compatible, and no Ticket 04 behavior is introduced.

## Required test seams

- [x] Public catalog acquisition and canonical intersection use bounded deterministic fixtures; one explicitly bounded real-network acceptance test may refresh and validate the current snapshot.
- [x] Production-archive coverage and liquidity evidence are tested for symbols with different listing dates, missing days, unavailable intervals, and changing catalog membership.
- [x] Range planning is tested at both sides of every cap and across daily/monthly archive boundaries without relying on routine network access.
- [x] Checksum, timestamp-unit, archive-content, duplicate, overlap, discontinuity, manifest, typed-Parquet, and deterministic-offline-replay failures remain covered.
- [x] API contract tests prove the typed catalog, preview, acquisition, manifest, and backtest payloads, including actionable validation errors.
- [x] A real browser test selects a non-`BTC` EUR symbol, inspects its coverage and liquidity context, downloads a bounded production range, runs the backtest, and verifies catalog identity, manifest identity, EUR context, and production-history provenance.
- [x] The complete pre-existing frontend, backend, contract, data, Parquet, deterministic-replay, browser, version, dependency-lock, and reproducibility baselines remain green.

## Answer

Implemented the complete EUR-first manifested production-data tracer. Studio now discovers and fingerprints the bounded official production/Testnet EUR intersection, exposes verified full daily-archive coverage and reproducible liquidity evidence, supports capped multi-day `1m` previews, verifies and normalizes official archives into typed Parquet, persists content-addressed catalogs and manifests, and deterministically replays admitted datasets offline with explicit EUR and production-history provenance.

Verification completed locally:

- Complete baseline: 143 passed, 2 explicitly opt-in tests skipped; version, dependency lock, architecture, static quality, coverage, typed contract, frontend unit/build, and deterministic browser gates accepted.
- Real-network catalog acceptance: passed against bounded official Binance endpoints.
- Real-browser production-data acceptance: passed with a dynamically selected live EUR symbol, verified coverage/liquidity context, catalog and manifest identities, normalized candles, EUR result context, and deterministic fingerprint.
- Final parallel Standards and Spec reviews were run from the Ticket 03 fixed point and their findings were addressed.
