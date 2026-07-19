# Binance Spot historical and Testnet data: primary-source research

Status: research input for the implementation plan  
Research date: 2026-07-19  
Scope: Binance.com Spot production public historical data and the Binance Spot Test Network

## Executive recommendation

Do **not** download every interval for every symbol exposed by Spot Testnet. Testnet is an integration environment with virtual assets and periodic resets; its symbol set is not the authority for the historical strategy-validation universe.

For the MVP:

1. Use production Binance Spot data for research and validation.
2. Use native `1m` klines for the broad 60-month, five-symbol search and walk-forward work.
3. Download raw production `trades` (preferred) or `aggTrades` only for the selected high-fidelity development periods and the locked event-replay holdout. Derive `30s` bars locally only if an experiment needs them.
4. Capture production trades, best bid/ask, and targeted depth prospectively for Production-Data Paper qualification and future replay. Historical Spot trade archives do not reconstruct historical queue position or the complete order book.
5. Discover the current Testnet symbol and filter contract from Testnet `GET /api/v3/exchangeInfo` at runtime. Use those symbols only for protocol and order-lifecycle scenarios, normally choosing one liquid pair that also exists in production and satisfies the MVP's sizing filters.

## Native intervals and historical datasets

Binance Spot does **not** define a native `30s` kline interval. Current Spot kline intervals are `1s`, `1m`, `3m`, `5m`, `15m`, `30m`, `1h`, `2h`, `4h`, `6h`, `8h`, `12h`, `1d`, `3d`, `1w`, and `1M`. Here `30m` means 30 minutes, not 30 seconds. The REST endpoint returns at most 1,000 bars per request. [Official Spot REST kline contract](https://github.com/binance/binance-spot-api-docs/blob/master/rest-api.md#klinecandlestick-data)

The official public archive publishes daily and monthly Spot files for:

- `klines` at the supported intervals;
- individual `trades`, sourced from `/api/v3/historicalTrades`; and
- `aggTrades`, sourced from `/api/v3/aggTrades`.

Binance says all symbols are supported, daily data is normally available the next day, and monthly data is normally available on the first Monday of the month. Every archive file has a SHA-256 checksum companion. Binance also warns through its update history that archived files may later be replaced to correct discovered issues. [Official Binance public-data repository](https://github.com/binance/binance-public-data)

Spot archive timestamps changed from milliseconds to microseconds for data from 2025-01-01 onward. Import must therefore detect the time unit by dataset/date and normalize it explicitly; treating every integer as milliseconds would corrupt post-2024 history. [Official public-data format note](https://github.com/binance/binance-public-data#spot)

### What `1s` means and its coverage boundary

`1s` is a native current kline interval. Binance introduced it as a rolling API change on 2022-08-23, so it cannot provide a uniform five-year history. [Official Spot API changelog, 2022-08-23](https://github.com/binance/binance-spot-api-docs/blob/master/CHANGELOG.md#2022-08-23)

The archive documentation does not promise one common earliest `1s` date for every symbol. Coverage must be discovered and recorded per symbol and file; the downloader must treat absent files as unavailable evidence, not silently replace them. For the accepted 60-month validation horizon, `1m` is therefore the appropriate broad-search resolution.

### Why not store every resolution

All coarser bars can be derived deterministically from a validated lower-resolution source, while storing every native interval duplicates information and checksums. More importantly, even `1s` OHLCV loses the order of trades inside the second and contains no historical bid/ask queue. It is useful for candle sensitivity checks, but it is not the highest-fidelity execution evidence.

Raw `trades` retain trade ID, price, quantity, quote quantity, time, and maker-side flags. `aggTrades` combine fills associated with one taker order at the same price. For replay where event ordering matters, individual trades preserve more information; `aggTrades` are the smaller fallback when the model explicitly accepts aggregation. [Official archive schemas](https://github.com/binance/binance-public-data#data-information), [official aggregate-trade definition](https://github.com/binance/binance-spot-api-docs/blob/master/rest-api.md#compressedaggregate-trades-list)

The public Spot archive documents klines, trades, and aggregate trades, not historical Spot best-bid/ask or depth snapshots. Current production WebSocket streams do expose raw trades, aggregate trades, `bookTicker`, partial depth, and diff depth. Therefore production Paper capture must preserve the live market evidence needed for later replay instead of assuming it can be downloaded retrospectively. [Official Spot WebSocket streams](https://github.com/binance/binance-spot-api-docs/blob/master/web-socket-streams.md#detailed-stream-information)

## Production versus Testnet authority

Spot Testnet is intended to practise Spot trading through API endpoints. Testnet balances are virtual and cannot be transferred in or out. It exposes `/api` but not `/sapi`. Binance says Testnet IP limits, order limits, exchange filters, and symbol filters are *generally* the same as production, while explicitly instructing clients to query current limits and filters. [Official Spot Test Network FAQ](https://testnet.binance.vision/)

That makes Testnet authoritative for the contract observed in the current Testnet generation—available symbols, filters, signing, order admission, order states, fills, cancellation, and reconciliation—not for production liquidity, profitability, production symbol eligibility, or historical-regime coverage.

The runtime must discover symbols and rules independently in each environment with that environment's `GET /api/v3/exchangeInfo`. Production observations select and validate the research/live symbol universe; Testnet observations determine which integration scenarios can be executed during the current Testnet generation. Concrete filter values must never be copied from documentation examples. [Official exchange-information endpoint](https://github.com/binance/binance-spot-api-docs/blob/master/rest-api.md#exchange-information), [official filter contract](https://github.com/binance/binance-spot-api-docs/blob/master/filters.md)

### Reset and retention caveat

Binance resets Spot Testnet to a blank state approximately monthly without advance notice. Pending and executed orders are deleted and virtual asset allowances are replenished; API keys have been preserved during resets since August 2020. Consequently, Testnet order history is temporary venue feedback. Our own append-only journal, reconciliation evidence, and generation identifier must retain the qualifying record, and a reset starts a new Testnet generation/soak rather than changing the production-data Paper clock. [Official Spot Test Network FAQ](https://testnet.binance.vision/)

## MVP data acquisition plan

| Stage | Symbols | Source and granularity | Purpose |
| --- | --- | --- | --- |
| Universe construction | Production USDT Spot candidates | Production metadata plus daily volume/history screening and a `1m` coverage probe | Apply the already accepted 60-month, non-peg/non-leveraged, liquidity and venue-validity criteria without first downloading five years of minute data for every symbol; freeze the five-symbol panel. |
| Broad research | Frozen five-symbol production panel | Official monthly/daily `1m` kline archives | Deterministic 60-month search, walk-forward, expanding-window, regime and cost tests. |
| Fidelity calibration | Selected development windows, then qualifying finalists | Official individual-trade archives; optionally compare derived `1s` and `30s` bars | Calibrate candle versus event replay without consuming the locked holdout. |
| Locked high-fidelity holdout | One frozen finalist/proposed production symbol | Individual trades plus complete native `1s` coverage where available, exact archive identities and checksums; no synthetic gap repair | One-shot event-replay validation under the accepted execution model. |
| Production-Data Paper | One chosen production symbol | Live production trades, `bookTicker`, targeted depth and continuity evidence | Qualifying simulated execution using the real production market path. |
| Testnet Run | One compatible current Testnet symbol | Testnet public/private streams, REST order/account feedback, current Testnet `exchangeInfo` | Venue adapter, recovery, order lifecycle, filter and reconciliation qualification; P&L is diagnostic only. |

Before bulk download, run a manifest/probe step that records symbol, dataset, interval, first/last available file, byte estimate, checksum availability, and gaps. Download only the frozen panel and required fidelity windows. This keeps the MVP bounded, preserves the holdout, and avoids spending disk and processing time on Testnet symbols that have no role in strategy validation.

## Primary sources

- [Binance public-data repository and archive format](https://github.com/binance/binance-public-data)
- [Binance Spot REST API](https://github.com/binance/binance-spot-api-docs/blob/master/rest-api.md)
- [Binance Spot WebSocket streams](https://github.com/binance/binance-spot-api-docs/blob/master/web-socket-streams.md)
- [Binance Spot API changelog](https://github.com/binance/binance-spot-api-docs/blob/master/CHANGELOG.md)
- [Binance Spot filters](https://github.com/binance/binance-spot-api-docs/blob/master/filters.md)
- [Binance Spot Test Network FAQ](https://testnet.binance.vision/)
